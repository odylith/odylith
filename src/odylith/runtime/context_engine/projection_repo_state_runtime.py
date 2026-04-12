from __future__ import annotations

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


def _git_head_oid(*, repo_root: Path) -> str:
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


def workspace_activity_fingerprint(*, repo_root: Path) -> str:
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
