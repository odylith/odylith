"""Local-only cache and atomic-write helpers for the Odylith Context Engine.

The upkeep commands in this repository are invoked repeatedly from local coding
agent sessions, pre-commit, and CI. Those callers often share a worktree, so the
tooling layer needs two guarantees:

- local compiled caches must be safe to reuse across processes without making
  source markdown or tracked artifacts authoritative; and
- generated/cache writes must be atomic and no-op when the rendered content is
  unchanged so concurrent sessions do not create avoidable churn.

This module intentionally keeps the contract small:

- cache state lives under `.odylith/cache/odylith-context-engine/` and remains local-only;
- advisory lock files live under `.odylith/locks/odylith-context-engine/`;
- cache and lock filenames stay bounded with digest-backed suffixes so temp
  snapshots and relocated repos remain portable across NAME_MAX-constrained
  filesystems;
- writes use temp-file + `os.replace()` in the target directory so readers never
  observe partial content;
- callers can fingerprint source inputs with metadata-only hashes when reparsing
  full content would be more expensive than scanning file stats.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Iterator, Sequence


_NON_ALNUM_RE = re.compile(r"[^a-z0-9._-]+")
_MAX_CACHE_TOKEN_LENGTH = 180
_MAX_LOCK_TOKEN_LENGTH = 120
_TRUNCATED_DIGEST_LENGTH = 16


def cache_root(*, repo_root: Path) -> Path:
    """Return the local-only Odylith Context Engine cache root."""

    return (Path(repo_root).resolve() / ".odylith" / "cache" / "odylith-context-engine").resolve()


def lock_root(*, repo_root: Path) -> Path:
    """Return the Odylith Context Engine advisory-lock directory."""

    return (Path(repo_root).resolve() / ".odylith" / "locks" / "odylith-context-engine").resolve()


def cache_path(*, repo_root: Path, namespace: str, key: str) -> Path:
    """Return a stable JSON cache path below `.odylith/cache/odylith-context-engine/`."""

    namespace_token = str(namespace or "").strip().strip("/")
    key_token = _bounded_file_token(
        str(key or "").strip(),
        default="cache",
        max_length=_MAX_CACHE_TOKEN_LENGTH,
    )
    root = cache_root(repo_root=repo_root)
    if namespace_token:
        return (root / namespace_token / f"{key_token}.json").resolve()
    return (root / f"{key_token}.json").resolve()


def _slug_token(value: str, *, default: str) -> str:
    token = _NON_ALNUM_RE.sub("-", str(value or "").strip().lower()).strip("-")
    return token or default


def _bounded_file_token(value: str, *, default: str, max_length: int) -> str:
    """Return a readable filesystem token that remains portable on long inputs."""

    raw = str(value or "").strip()
    token = _slug_token(raw, default=default)
    if len(token) <= max_length:
        return token
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:_TRUNCATED_DIGEST_LENGTH]
    prefix_budget = max(max_length - len(digest) - 1, len(default))
    prefix = token[:prefix_budget].rstrip("-.") or default
    return f"{prefix}-{digest}"


def path_signature(path: Path) -> dict[str, Any]:
    """Return a JSON-safe metadata signature for one path."""

    target = Path(path)
    if not target.exists():
        return {"exists": False, "kind": "missing", "size": 0, "mtime_ns": 0}
    try:
        stat = target.stat()
    except OSError:
        return {"exists": False, "kind": "unreadable", "size": 0, "mtime_ns": 0}
    kind = "dir" if target.is_dir() else "file"
    size = int(stat.st_size) if kind == "file" else 0
    return {
        "exists": True,
        "kind": kind,
        "size": size,
        "mtime_ns": int(stat.st_mtime_ns),
    }


def fingerprint_paths(paths: Sequence[Path]) -> str:
    """Return a deterministic fingerprint across the given paths."""

    payload = [
        {
            "path": str(Path(path)),
            "signature": path_signature(Path(path)),
        }
        for path in paths
    ]
    return fingerprint_payload(payload)


def fingerprint_tree(path: Path, *, glob: str = "*") -> str:
    """Return a metadata-only fingerprint for a file or directory tree.

    Directory fingerprints include descendant file signatures in lexicographic
    order. This is still `O(n files)`, but avoids reparsing every file body when
    callers only need a stable invalidation token.
    """

    target = Path(path)
    if not target.exists():
        return fingerprint_payload({"path": str(target), "signature": path_signature(target)})
    if target.is_file():
        return fingerprint_payload({"path": str(target), "signature": path_signature(target)})

    rows: list[dict[str, Any]] = []
    try:
        nodes = sorted(node for node in target.rglob(glob) if node.is_file())
    except OSError:
        nodes = []
    for node in nodes:
        try:
            rel = node.relative_to(target).as_posix()
        except ValueError:
            rel = str(node)
        rows.append({"path": rel, "signature": path_signature(node)})
    return fingerprint_payload(
        {
            "root": str(target),
            "signature": path_signature(target),
            "files": rows,
        }
    )


def fingerprint_payload(payload: Any) -> str:
    """Return a SHA-256 digest for a JSON-serializable payload."""

    rendered = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    """Return a JSON object from disk, or `{}` when the file is absent/invalid."""

    target = Path(path)
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


@contextmanager
def advisory_lock(*, repo_root: Path, key: str) -> Iterator[Path]:
    """Serialize writes for one logical Odylith Context Engine resource."""

    token = _bounded_file_token(
        str(key or "").strip(),
        default="odylith-context-engine",
        max_length=_MAX_LOCK_TOKEN_LENGTH,
    )
    lock_path = (lock_root(repo_root=repo_root) / f"{token}.lock").resolve()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield lock_path
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_text_if_changed(
    *,
    repo_root: Path,
    path: Path,
    content: str,
    lock_key: str | None = None,
) -> bool:
    """Atomically write text when the on-disk content differs.

    Returns `True` when a write occurred and `False` for a semantic no-op.
    """

    target = Path(path).resolve()
    token = str(lock_key or target)
    with advisory_lock(repo_root=repo_root, key=token):
        existing = None
        if target.is_file():
            try:
                existing = target.read_text(encoding="utf-8")
            except OSError:
                existing = None
        if existing == content:
            return False

        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
            os.replace(temp_path, target)
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
        return True


def write_json_if_changed(
    *,
    repo_root: Path,
    path: Path,
    payload: Any,
    lock_key: str | None = None,
    indent: int = 2,
    sort_keys: bool = True,
) -> bool:
    """Atomically write formatted JSON when the semantic content changed."""

    rendered = json.dumps(payload, indent=indent, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    return write_text_if_changed(
        repo_root=repo_root,
        path=path,
        content=rendered,
        lock_key=lock_key,
    )


__all__ = [
    "advisory_lock",
    "cache_path",
    "cache_root",
    "fingerprint_paths",
    "fingerprint_payload",
    "fingerprint_tree",
    "lock_root",
    "path_signature",
    "read_json_object",
    "write_json_if_changed",
    "write_text_if_changed",
]
