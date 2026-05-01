"""Stable benchmark report tree identity and snapshot-overlay ownership."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine_store as store


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
        "snapshot_overlay_fingerprint": _snapshot_overlay_fingerprint(repo_root=root, snapshot_paths=snapshot_paths),
        "source_posture": _benchmark_source_posture(repo_root=root),
    }


def benchmark_report_matches_current_tree(*, repo_root: Path, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    selection = dict(report.get("selection", {})) if isinstance(report.get("selection"), Mapping) else {}
    snapshot_paths = (
        [str(token).strip() for token in report.get("snapshot_overlay_paths", []) if str(token).strip()]
        if isinstance(report.get("snapshot_overlay_paths"), list)
        else []
    )
    current = benchmark_tree_identity(repo_root=repo_root, selection=selection, snapshot_paths=snapshot_paths)
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


def _snapshot_overlay_fingerprint(*, repo_root: Path, snapshot_paths: Sequence[str]) -> str:
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
