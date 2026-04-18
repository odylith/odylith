"""Stable repo-state tokens for projection cache invalidation.

Projection reads should reuse cached work when the repository state is
effectively unchanged, but the invalidation signal has to notice both git head
movement and meaningful workspace edits. This module builds a compact token for
that purpose and keeps a short process-local TTL cache around it.
"""

from __future__ import annotations

from functools import lru_cache
import subprocess
import time
from pathlib import Path
from typing import Any

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.governance import component_registry_intelligence as component_registry
from odylith.runtime.governance import workstream_inference as ws_inference

_PROCESS_REPO_STATE_CACHE_TTL_SECONDS = 5.0
_PROCESS_REPO_STATE_TOKEN_CACHE: dict[str, tuple[float, str, str]] = {}


@lru_cache(maxsize=64)
def _git_dir(repo_root_token: str) -> Path | None:
    """Resolve the git directory for a repo root token, including gitdir files."""
    root = Path(repo_root_token).resolve()
    dot_git = root / ".git"
    if dot_git.is_dir():
        return dot_git.resolve()
    if not dot_git.is_file():
        return None
    try:
        first_line = dot_git.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return None
    prefix = "gitdir:"
    if not first_line.lower().startswith(prefix):
        return None
    raw_target = first_line[len(prefix) :].strip()
    if not raw_target:
        return None
    target = Path(raw_target)
    if not target.is_absolute():
        target = (root / target).resolve()
    return target.resolve()


def _read_first_line(path: Path) -> str:
    """Return the first line of a file or an empty string on read failure."""
    try:
        return path.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return ""


def _packed_ref_oid(*, git_dir: Path, ref_token: str) -> str:
    """Resolve one ref from `packed-refs` when it is not present as a loose ref."""
    packed_refs_path = git_dir / "packed-refs"
    if not packed_refs_path.is_file():
        return ""
    try:
        lines = packed_refs_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    suffix = f" {str(ref_token).strip()}"
    for line in lines:
        stripped = str(line or "").strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("^"):
            continue
        if stripped.endswith(suffix):
            return stripped.partition(" ")[0].strip()
    return ""


def _git_head_oid_subprocess(*, repo_root: Path) -> str:
    """Fallback to `git rev-parse HEAD` when direct gitdir reads are unavailable."""
    root = Path(repo_root).resolve()
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return ""
    return str(completed.stdout or "").strip()


def _git_head_oid(*, repo_root: Path) -> str:
    """Resolve the current HEAD object id using cheap filesystem reads first."""
    root = Path(repo_root).resolve()
    git_dir = _git_dir(str(root))
    if git_dir is not None:
        head_token = _read_first_line(git_dir / "HEAD")
        if head_token.startswith("ref:"):
            ref_token = head_token.partition(":")[2].strip()
            if ref_token:
                direct_ref = _read_first_line(git_dir / ref_token)
                if direct_ref:
                    return direct_ref
                packed_ref = _packed_ref_oid(git_dir=git_dir, ref_token=ref_token)
                if packed_ref:
                    return packed_ref
        elif head_token:
            return head_token
    return _git_head_oid_subprocess(repo_root=root)


def workspace_activity_fingerprint(*, repo_root: Path) -> str:
    """Fingerprint meaningful changed workspace artifacts for projection invalidation."""
    root = Path(repo_root).resolve()
    rows: list[dict[str, Any]] = []
    for raw in governance.collect_git_changed_paths(repo_root=root):
        normalized = ws_inference.normalize_repo_token(str(raw), repo_root=root)
        if not normalized or not component_registry.is_meaningful_workspace_artifact(normalized):
            continue
        candidate = (root / normalized).resolve()
        rows.append(
            {
                "path": normalized,
                "signature": odylith_context_cache.path_signature(candidate),
            }
        )
    return odylith_context_cache.fingerprint_payload(rows)


def projection_repo_state_token(*, repo_root: Path) -> str:
    """Return the current repo-state token, reusing the sync-session cache when active."""
    root = Path(repo_root).resolve()
    try:
        from odylith.runtime.governance import sync_session as governed_sync_session
    except ImportError:  # pragma: no cover - defensive bootstrap fallback
        governed_sync_session = None
    if governed_sync_session is not None:
        session = governed_sync_session.active_sync_session()
        if session is not None and session.repo_root == root:
            return str(
                session.get_or_compute(
                    namespace="projection_repo_state",
                    key="token",
                    builder=lambda: _projection_repo_state_token_uncached(repo_root=root),
                )
            ).strip()
    return _projection_repo_state_token_uncached(repo_root=root)


def _projection_repo_state_token_uncached(*, repo_root: Path) -> str:
    """Build the repo-state token without consulting the governed sync session."""
    root = Path(repo_root).resolve()
    cache_key = str(root)
    head_oid = _git_head_oid(repo_root=root)
    now = time.monotonic()
    cached = _PROCESS_REPO_STATE_TOKEN_CACHE.get(cache_key)
    if cached is not None and cached[1] == head_oid and now - cached[0] <= _PROCESS_REPO_STATE_CACHE_TTL_SECONDS:
        return cached[2]
    workspace_fingerprint = workspace_activity_fingerprint(repo_root=root)
    state_token = odylith_context_cache.fingerprint_payload(
        {
            "repo_root": str(root),
            "head_oid": head_oid,
            "workspace_activity": workspace_fingerprint,
        }
    )
    _PROCESS_REPO_STATE_TOKEN_CACHE[cache_key] = (now, head_oid, state_token)
    return state_token


def clear_projection_repo_state_cache(*, repo_root: Path | None = None) -> None:
    """Clear the short-lived process cache for one repo or for all repos."""
    if repo_root is None:
        _PROCESS_REPO_STATE_TOKEN_CACHE.clear()
        return
    root = str(Path(repo_root).resolve())
    _PROCESS_REPO_STATE_TOKEN_CACHE.pop(root, None)


__all__ = [
    "clear_projection_repo_state_cache",
    "projection_repo_state_token",
    "workspace_activity_fingerprint",
]
