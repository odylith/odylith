"""Shared lightweight runtime support for the Odylith context engine.

This module owns small cross-cutting helpers that need to stay available to
focused runtime slices without pulling them back through the full context-engine
store module.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Mapping

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_control_state

SCHEMA_VERSION = "v6"

BASE_PROJECTION_NAMES = (
    "workstreams",
    "releases",
    "plans",
    "bugs",
    "diagrams",
    "components",
    "codex_events",
    "traceability",
    "delivery",
)
FULL_ONLY_PROJECTION_NAMES = (
    "engineering_graph",
    "code_graph",
    "test_graph",
)
REASONING_PROJECTION_NAMES = (
    "workstreams",
    "releases",
    "plans",
    "bugs",
    "diagrams",
    "components",
    "codex_events",
    "traceability",
    *FULL_ONLY_PROJECTION_NAMES,
)


def utc_now() -> str:
    """Return the canonical UTC timestamp shape used by runtime artifacts."""
    from odylith.runtime.context_engine import odylith_architecture_mode

    return odylith_architecture_mode._utc_now()  # noqa: SLF001


def projection_names_for_scope(scope: str) -> tuple[str, ...]:
    """Return the projection tables required for a given runtime scope."""
    token = str(scope or "default").strip().lower()
    if token == "full":
        return (*BASE_PROJECTION_NAMES, *FULL_ONLY_PROJECTION_NAMES)
    if token == "reasoning":
        return REASONING_PROJECTION_NAMES
    return BASE_PROJECTION_NAMES


def _watchdog_available() -> bool:
    try:
        import watchdog.observers  # type: ignore  # pragma: no cover
    except ImportError:  # pragma: no cover - optional dependency
        return False
    return True


def git_fsmonitor_status(*, repo_root: Path) -> dict[str, Any]:
    """Return availability and activation status for Git's fsmonitor daemon."""
    root = Path(repo_root).resolve()
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "fsmonitor--daemon", "status"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return {
            "supported": False,
            "active": False,
            "detail": "",
            "returncode": 127,
        }
    detail = "\n".join(
        token
        for token in (
            str(completed.stdout or "").strip(),
            str(completed.stderr or "").strip(),
        )
        if token
    ).strip()
    normalized = detail.lower()
    supported = "fsmonitor-daemon" in normalized and "not a git command" not in normalized
    active = supported and " is watching " in normalized
    return {
        "supported": supported,
        "active": active,
        "detail": detail,
        "returncode": int(completed.returncode),
    }


def bootstrap_git_fsmonitor(*, repo_root: Path) -> dict[str, Any]:
    """Start Git fsmonitor when supported, keeping the operation local-only."""
    root = Path(repo_root).resolve()
    before = git_fsmonitor_status(repo_root=root)
    if not bool(before.get("supported")):
        return {
            "supported": False,
            "active": False,
            "started": False,
            "status": "unsupported",
            "detail": str(before.get("detail", "")).strip(),
        }
    if bool(before.get("active")):
        return {
            "supported": True,
            "active": True,
            "started": False,
            "status": "already-active",
            "detail": str(before.get("detail", "")).strip(),
        }
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "fsmonitor--daemon", "start"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as exc:
        return {
            "supported": True,
            "active": False,
            "started": False,
            "status": "failed",
            "detail": str(exc),
        }
    after = git_fsmonitor_status(repo_root=root)
    if bool(after.get("active")):
        detail = str(after.get("detail", "")).strip() or str(completed.stdout or "").strip()
        return {
            "supported": True,
            "active": True,
            "started": True,
            "status": "started",
            "detail": detail,
        }
    detail = "\n".join(
        token
        for token in (
            str(completed.stdout or "").strip(),
            str(completed.stderr or "").strip(),
            str(after.get("detail", "")).strip(),
        )
        if token
    ).strip()
    return {
        "supported": True,
        "active": False,
        "started": False,
        "status": "failed",
        "detail": detail,
    }


def watcher_backend_report(*, repo_root: Path) -> dict[str, Any]:
    """Describe watcher capability and the best local backend currently usable."""
    root = Path(repo_root).resolve()
    watchman_available = bool(shutil.which("watchman"))
    watchdog_available = _watchdog_available()
    git_fsmonitor = git_fsmonitor_status(repo_root=root)
    preferred = "poll"
    if watchman_available:
        preferred = "watchman"
    elif watchdog_available:
        preferred = "watchdog"
    elif bool(git_fsmonitor.get("active")):
        preferred = "git-fsmonitor"
    best_bootstrappable = (
        "watchman"
        if watchman_available
        else "watchdog"
        if watchdog_available
        else "git-fsmonitor"
        if bool(git_fsmonitor.get("supported"))
        else "poll"
    )
    bootstrap_recommended = preferred == "poll" and best_bootstrappable == "git-fsmonitor"
    return {
        "watchman_available": watchman_available,
        "watchdog_available": watchdog_available,
        "git_fsmonitor_supported": bool(git_fsmonitor.get("supported")),
        "git_fsmonitor_active": bool(git_fsmonitor.get("active")),
        "git_fsmonitor_detail": str(git_fsmonitor.get("detail", "")).strip(),
        "preferred_backend": preferred,
        "best_bootstrappable_backend": best_bootstrappable,
        "bootstrap_recommended": bootstrap_recommended,
    }


def preferred_watcher_backend(*, repo_root: Path | None = None) -> str:
    """Return the preferred local invalidation backend available in this env."""
    if shutil.which("watchman"):
        return "watchman"
    if _watchdog_available():
        return "watchdog"
    if repo_root is not None and bool(git_fsmonitor_status(repo_root=Path(repo_root).resolve()).get("active")):
        return "git-fsmonitor"
    return "poll"


def record_runtime_timing(
    *,
    repo_root: Path,
    category: str,
    operation: str,
    duration_ms: float,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    """Append one structured runtime timing row using the shared JSONL ledger."""
    ts_iso = utc_now()
    odylith_control_state.append_timing(
        repo_root=Path(repo_root).resolve(),
        row={
            "timing_id": odylith_context_cache.fingerprint_payload(
                {
                    "ts_iso": ts_iso,
                    "pid": os.getpid(),
                    "category": str(category or "").strip(),
                    "operation": str(operation or "").strip(),
                    "duration_ms": round(float(duration_ms or 0.0), 3),
                    "metadata": dict(metadata or {}),
                }
            ),
            "ts_iso": ts_iso,
            "category": str(category or "").strip() or "runtime",
            "operation": str(operation or "").strip() or "unknown",
            "duration_ms": round(float(duration_ms or 0.0), 3),
            "metadata": dict(metadata or {}),
        },
    )


__all__ = [
    "BASE_PROJECTION_NAMES",
    "FULL_ONLY_PROJECTION_NAMES",
    "REASONING_PROJECTION_NAMES",
    "SCHEMA_VERSION",
    "bootstrap_git_fsmonitor",
    "git_fsmonitor_status",
    "preferred_watcher_backend",
    "projection_names_for_scope",
    "record_runtime_timing",
    "utc_now",
    "watcher_backend_report",
]
