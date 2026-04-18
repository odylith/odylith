"""Fast-path guards for generated artifact rebuilds."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache

_CACHE_VERSION = "v1"


def _normalize_watch_tokens(watched_paths: Sequence[str | Path]) -> tuple[str, ...]:
    """Normalize watched path tokens into stable, de-duplicated POSIX strings."""
    rows: list[str] = []
    seen: set[str] = set()
    for raw in watched_paths:
        token = str(raw or "").strip()
        if not token:
            continue
        normalized = PurePosixPath(token).as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(normalized)
    return tuple(rows)


def _resolve_watch_path(*, repo_root: Path, token: str) -> Path:
    """Resolve watched-path tokens relative to the repo root when needed."""
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _update_tree_digest(hasher: hashlib._Hash, path: Path, *, root: Path) -> None:
    """Add filesystem shape and mtimes for one path subtree into the digest."""
    try:
        stat = path.stat()
    except OSError:
        hasher.update(f"missing\0{path}\0".encode("utf-8"))
        return
    if path.is_file():
        rel = path.relative_to(root).as_posix()
        hasher.update(f"file\0{rel}\0{int(stat.st_size)}\0{int(stat.st_mtime_ns)}\0".encode("utf-8"))
        return
    if not path.is_dir():
        rel = path.relative_to(root).as_posix()
        hasher.update(f"other\0{rel}\0{int(stat.st_size)}\0{int(stat.st_mtime_ns)}\0".encode("utf-8"))
        return
    rel = path.relative_to(root).as_posix() if path != root else "."
    hasher.update(f"dir\0{rel}\0{int(stat.st_mtime_ns)}\0".encode("utf-8"))
    try:
        entries = sorted(os.scandir(path), key=lambda entry: entry.name)
    except OSError:
        hasher.update(f"unreadable\0{rel}\0".encode("utf-8"))
        return
    for entry in entries:
        _update_tree_digest(hasher, Path(entry.path), root=root)


def _path_fingerprint(path: Path) -> str:
    """Fingerprint a file or directory tree rooted at the given path."""
    target = Path(path).resolve()
    hasher = hashlib.sha256()
    _update_tree_digest(hasher, target, root=target if target.is_dir() else target.parent)
    return hasher.hexdigest()


def _resolved_output_paths(output_paths: Sequence[Path]) -> tuple[Path, ...]:
    """Resolve output paths once before reading or recording cache state."""
    return tuple(Path(path).resolve() for path in output_paths)


def compute_input_fingerprint(
    *,
    repo_root: Path,
    watched_paths: Sequence[str | Path],
    extra: Mapping[str, Any] | None = None,
) -> str:
    """Fingerprint the watched inputs and extra cache-invalidating metadata."""
    root = Path(repo_root).resolve()
    normalized = _normalize_watch_tokens(watched_paths)
    payload: dict[str, Any] = {
        "version": _CACHE_VERSION,
        "extra": dict(extra) if isinstance(extra, Mapping) else {},
        "watched_paths": normalized,
        "signatures": {
            token: _path_fingerprint(_resolve_watch_path(repo_root=root, token=token))
            for token in normalized
        },
    }
    return odylith_context_cache.fingerprint_payload(payload)


def _output_signatures(output_paths: Sequence[Path]) -> dict[str, Any]:
    """Capture current output path signatures for rebuild-skip comparisons."""
    return {
        str(Path(path).resolve()): odylith_context_cache.path_signature(Path(path).resolve())
        for path in output_paths
    }


def should_skip_rebuild(
    *,
    repo_root: Path,
    namespace: str,
    key: str,
    watched_paths: Sequence[str | Path],
    output_paths: Sequence[Path],
    extra: Mapping[str, Any] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Return whether a generated rebuild can be skipped safely."""
    root = Path(repo_root).resolve()
    fingerprint = compute_input_fingerprint(
        repo_root=root,
        watched_paths=watched_paths,
        extra=extra,
    )
    cache_path = odylith_context_cache.cache_path(repo_root=root, namespace=namespace, key=key)
    cached = odylith_context_cache.read_json_object(cache_path)
    if (
        cached.get("version") != _CACHE_VERSION
        or str(cached.get("input_fingerprint", "")).strip() != fingerprint
        or not isinstance(cached.get("outputs"), Mapping)
    ):
        return False, fingerprint, {}
    outputs = _resolved_output_paths(output_paths)
    current_outputs = _output_signatures(outputs)
    if dict(cached.get("outputs", {})) != current_outputs:
        return False, fingerprint, {}
    metadata = dict(cached.get("metadata", {})) if isinstance(cached.get("metadata"), Mapping) else {}
    return True, fingerprint, metadata


def record_rebuild(
    *,
    repo_root: Path,
    namespace: str,
    key: str,
    input_fingerprint: str,
    output_paths: Sequence[Path],
    metadata: Mapping[str, Any] | None = None,
) -> None:
    """Persist the cache entry that proves a rebuild just refreshed outputs."""
    root = Path(repo_root).resolve()
    cache_path = odylith_context_cache.cache_path(repo_root=root, namespace=namespace, key=key)
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=cache_path,
        payload={
            "version": _CACHE_VERSION,
            "input_fingerprint": str(input_fingerprint or "").strip(),
            "outputs": _output_signatures(_resolved_output_paths(output_paths)),
            "metadata": dict(metadata) if isinstance(metadata, Mapping) else {},
        },
        lock_key=str(cache_path),
    )


__all__ = [
    "compute_input_fingerprint",
    "record_rebuild",
    "should_skip_rebuild",
]
