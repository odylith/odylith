"""Stable benchmark report tree identity and snapshot-overlay ownership."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
import hashlib
import json
from pathlib import Path, PureWindowsPath
import stat
import subprocess
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store as store

_CONTENT_OVERLAY_VERSION = "content-v1"
_LEGACY_OVERLAY_VERSION = "legacy-metadata"


def stable_snapshot_overlay_path(token: object) -> str:
    path = str(token).strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if not path or path == ".odylith" or path.startswith(".odylith/"):
        return ""
    return path


def stable_snapshot_overlay_paths(tokens: Iterable[object]) -> list[str]:
    return [path for token in tokens if (path := stable_snapshot_overlay_path(token))]


def dedupe_path_strings(values: Sequence[object]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for raw in values:
        token = stable_snapshot_overlay_path(raw)
        if not token:
            continue
        normalized = Path(token).as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(normalized)
    return rows


def dirty_repo_paths(repo_root: Path) -> list[str]:
    root = Path(repo_root).resolve()
    rows: list[str] = []
    for command in (
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        completed = subprocess.run(
            command,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
        )
        if int(completed.returncode or 0) != 0:
            continue
        rows.extend(str(line).strip() for line in str(completed.stdout or "").splitlines() if str(line).strip())
    return dedupe_path_strings(rows)


def report_snapshot_overlay_paths(scenario_reports: Sequence[Mapping[str, Any]]) -> list[str]:
    rows: list[str] = []
    for scenario_report in scenario_reports:
        if not isinstance(scenario_report, Mapping):
            continue
        results = scenario_report.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, Mapping):
                continue
            live_execution = result.get("live_execution", {})
            if not isinstance(live_execution, Mapping):
                continue
            effective_paths = live_execution.get("effective_snapshot_paths", [])
            if isinstance(effective_paths, list):
                rows.extend(stable_snapshot_overlay_paths(effective_paths))
    return dedupe_path_strings(rows)


def benchmark_tree_identity(
    *,
    repo_root: Path,
    selection: Mapping[str, Any],
    snapshot_paths: Sequence[str] = (),
    overlay_fingerprint_version: str = _CONTENT_OVERLAY_VERSION,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    dirty_paths = dirty_repo_paths(root)
    return {
        "git_branch": str(store._git_branch_name(repo_root=root) or "").strip(),  # noqa: SLF001
        "git_commit": str(store._git_head_oid(repo_root=root) or "").strip(),  # noqa: SLF001
        "git_dirty": bool(dirty_paths),
        "repo_dirty_paths": dirty_paths,
        "selection_fingerprint": _fingerprint_json_payload(selection),
        "corpus_fingerprint": odylith_context_cache.fingerprint_paths(
            [store.optimization_evaluation_corpus_path(repo_root=root)]
        ),
        "snapshot_overlay_fingerprint": _snapshot_overlay_fingerprint(
            repo_root=root, snapshot_paths=snapshot_paths, version=overlay_fingerprint_version,
        ),
        "source_posture": _benchmark_source_posture(repo_root=root),
    }


def benchmark_report_matches_current_tree(*, repo_root: Path, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    fingerprint = report.get("snapshot_overlay_fingerprint")
    if not isinstance(fingerprint, str):
        return False
    prefix = f"{_CONTENT_OVERLAY_VERSION}:"
    if fingerprint.startswith(prefix):
        version = _CONTENT_OVERLAY_VERSION
        digest = fingerprint[len(prefix):]
        if len(digest) != 64 or any(token not in "0123456789abcdef" for token in digest):
            return False
        if not isinstance(report.get("snapshot_overlay_paths"), list):
            return False
        snapshot_paths = report["snapshot_overlay_paths"]
    elif not fingerprint or (len(fingerprint) == 64 and all(token in "0123456789abcdef" for token in fingerprint)):
        version = _LEGACY_OVERLAY_VERSION
        snapshot_paths = (
            [str(token).strip() for token in report.get("snapshot_overlay_paths", []) if str(token).strip()]
            if isinstance(report.get("snapshot_overlay_paths"), list)
            else []
        )
    else:
        return False
    selection = dict(report.get("selection", {})) if isinstance(report.get("selection"), Mapping) else {}
    try:
        current = benchmark_tree_identity(
            repo_root=repo_root, selection=selection, snapshot_paths=snapshot_paths,
            overlay_fingerprint_version=version,
        )
    except (OSError, RuntimeError, ValueError):
        return False
    for key in (
        "git_branch",
        "git_commit",
        "git_dirty",
        "repo_dirty_paths",
        "selection_fingerprint",
        "corpus_fingerprint",
        "snapshot_overlay_fingerprint",
        "source_posture",
    ):
        if report.get(key) != current.get(key):
            return False
    return True


def _fingerprint_json_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _safe_resolve_path(path: Path) -> Path | None:
    with contextlib.suppress(OSError, RuntimeError):
        return Path(path).resolve()
    return None


def _canonical_overlay_paths(snapshot_paths: Sequence[str]) -> list[str]:
    paths: set[str] = set()
    for raw in snapshot_paths:
        if not isinstance(raw, str):
            raise ValueError("benchmark overlay paths must be relative strings")
        token = raw.strip().replace("\\", "/")
        while token.startswith("./"):
            token = token[2:]
        path = Path(token)
        if not token or path.is_absolute() or PureWindowsPath(token).drive or ".." in path.parts or path == Path("."):
            raise ValueError(f"unsafe benchmark overlay path: {raw!r}")
        if token == ".odylith" or token.startswith(".odylith/"):
            continue
        paths.add(path.as_posix())
    return sorted(paths)


def _content_overlay_fingerprint(*, repo_root: Path, snapshot_paths: Sequence[str]) -> str:
    root = Path(repo_root).resolve()
    inputs = _canonical_overlay_paths(snapshot_paths)
    entries: dict[str, dict[str, Any]] = {}

    def visit(path: Path, relative: str, ancestors: frozenset[Path]) -> None:
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"benchmark overlay path escapes the repo: {relative}")
        try:
            source_stat = path.lstat()
        except FileNotFoundError:
            entries[relative] = {"path": relative, "kind": "absent"}
            return
        metadata = resolved.stat() if stat.S_ISLNK(source_stat.st_mode) else source_stat
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISDIR(metadata.st_mode):
            if resolved in ancestors:
                raise ValueError(f"cyclic benchmark overlay directory: {relative}")
            entries[relative] = {"path": relative, "kind": "directory", "mode": mode}
            for child in sorted(path.iterdir(), key=lambda item: item.name):
                visit(child, f"{relative}/{child.name}", ancestors | {resolved})
        elif stat.S_ISREG(metadata.st_mode):
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(131072), b""):
                    digest.update(chunk)
            entries[relative] = {"path": relative, "kind": "file", "mode": mode, "sha256": digest.hexdigest()}
        else:
            raise ValueError(f"unsupported benchmark overlay source: {relative}")

    for token in inputs:
        visit(root / token, token, frozenset())
    encoded = json.dumps(
        {"inputs": inputs, "entries": [entries[path] for path in sorted(entries)]},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")
    return f"{_CONTENT_OVERLAY_VERSION}:{hashlib.sha256(encoded).hexdigest()}"


def _snapshot_overlay_fingerprint(*, repo_root: Path, snapshot_paths: Sequence[str], version: str = _CONTENT_OVERLAY_VERSION) -> str:
    if version == _CONTENT_OVERLAY_VERSION:
        return _content_overlay_fingerprint(repo_root=repo_root, snapshot_paths=snapshot_paths)
    if version != _LEGACY_OVERLAY_VERSION:
        raise ValueError(f"unknown benchmark overlay fingerprint version: {version}")
    root = Path(repo_root).resolve()
    for token in _canonical_overlay_paths(snapshot_paths):
        if not (root / token).resolve().is_relative_to(root):
            raise ValueError(f"benchmark overlay path escapes the repo: {token}")
    normalized_paths = dedupe_path_strings(stable_snapshot_overlay_paths(snapshot_paths))
    if not normalized_paths:
        return ""
    existing_paths = [
        str(path)
        for path in (
            _safe_resolve_path(Path(repo_root).resolve() / token)
            for token in normalized_paths
        )
        if path is not None and path.exists()
    ]
    if not existing_paths:
        return ""
    return odylith_context_cache.fingerprint_paths(existing_paths)


def _benchmark_source_posture(*, repo_root: Path) -> str:
    with contextlib.suppress(Exception):
        from odylith.install.manager import version_status

        status = version_status(repo_root=repo_root)
        posture = str(getattr(status, "posture", "") or "").strip()
        runtime_source = str(getattr(status, "runtime_source", "") or "").strip()
        if posture and runtime_source:
            return f"{posture}:{runtime_source}"
        if posture:
            return posture
        if runtime_source:
            return runtime_source
    return "unknown"
