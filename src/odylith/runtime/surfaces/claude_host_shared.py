"""Shared helpers for Claude Code host surfaces rendered from Odylith state.

The Claude Code host surfaces (statusline, PreCompact snapshot) all read the
same Compass runtime snapshot and resolve the same Claude project memory
directory. This module keeps those helpers in one place so the individual
surface modules stay focused on rendering.

This module is deliberately narrow: it reads state and computes paths, but
does not render, write, or raise into the caller. Callers are expected to
degrade to their own safe-fallback shapes on missing or partial state.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping


_COMPASS_RUNTIME_RELATIVE = Path("odylith") / "compass" / "runtime" / "current.v1.json"
_CLAUDE_CONFIG_DIR_ENV = "CLAUDE_CONFIG_DIR"
_CLAUDE_CONFIG_DIR_DEFAULT = "~/.claude"
_CLAUDE_PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"
_SLUG_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def resolve_repo_root(repo_root: Path | str = ".") -> Path:
    """Resolve a caller-supplied repo root hint to an absolute path."""
    return Path(repo_root).expanduser().resolve()


def canonical_repo_root(project_dir: Path | str) -> Path:
    """Return the canonical Git repo root for a project directory if resolvable.

    Falls back to the resolved project directory on any Git failure. Used to
    compute the stable Claude project slug so that worktrees, symlinks, and
    nested Git common dirs all map to the same project memory directory.
    """
    root = Path(project_dir).expanduser().resolve()
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return root
    token = str(completed.stdout or "").strip()
    if completed.returncode != 0 or not token:
        return root
    common_dir = Path(token)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    parts = common_dir.parts
    if ".git" not in parts:
        return root
    index = parts.index(".git")
    if index <= 0:
        return root
    repo = Path(parts[0])
    for part in parts[1:index]:
        repo /= part
    return repo.resolve()


def claude_config_dir() -> Path:
    """Return the resolved Claude config directory (``$CLAUDE_CONFIG_DIR`` or default)."""
    token = str(os.environ.get(_CLAUDE_CONFIG_DIR_ENV, _CLAUDE_CONFIG_DIR_DEFAULT)).strip()
    return Path(token or _CLAUDE_CONFIG_DIR_DEFAULT).expanduser().resolve()


def project_slug(project_dir: Path | str) -> str:
    """Return the stable Claude project slug derived from the canonical repo root."""
    normalized = canonical_repo_root(project_dir).as_posix()
    slug = _SLUG_UNSAFE_RE.sub("-", normalized)
    return slug if slug.startswith("-") else f"-{slug.lstrip('-')}"


def project_memory_dir(project_dir: Path | str) -> Path:
    """Return the Claude project auto-memory directory for the given repo root."""
    return claude_config_dir() / "projects" / project_slug(project_dir) / "memory"


def load_compass_runtime(repo_root: Path | str = ".") -> Mapping[str, Any] | None:
    """Return the parsed Compass runtime snapshot or ``None`` on any failure."""
    root = resolve_repo_root(repo_root)
    path = root / _COMPASS_RUNTIME_RELATIVE
    try:
        if not path.is_file():
            return None
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, Mapping) else None


def active_workstream_from_runtime(payload: Mapping[str, Any] | None) -> str:
    """Extract the first active workstream id from a Compass runtime snapshot."""
    if not isinstance(payload, Mapping):
        return ""
    focus = payload.get("execution_focus")
    if not isinstance(focus, Mapping):
        return ""
    scope = focus.get("global")
    if not isinstance(scope, Mapping):
        return ""
    workstreams = scope.get("workstreams")
    if not isinstance(workstreams, list):
        return ""
    for token in workstreams:
        candidate = str(token or "").strip().upper()
        if candidate:
            return candidate
    return ""


def active_workstream_headline(payload: Mapping[str, Any] | None) -> str:
    """Extract the global execution-focus headline from the Compass runtime."""
    if not isinstance(payload, Mapping):
        return ""
    focus = payload.get("execution_focus")
    if not isinstance(focus, Mapping):
        return ""
    scope = focus.get("global")
    if not isinstance(scope, Mapping):
        return ""
    return " ".join(str(scope.get("headline") or "").split()).strip()


def brief_generated_at(payload: Mapping[str, Any] | None) -> dt.datetime | None:
    """Parse the ``generated_utc`` timestamp from a Compass runtime snapshot."""
    if not isinstance(payload, Mapping):
        return None
    stamp = str(payload.get("generated_utc") or "").strip()
    if not stamp:
        return None
    try:
        parsed = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def freshness_label(
    payload: Mapping[str, Any] | None,
    *,
    now: dt.datetime | None = None,
) -> str:
    """Return a compact freshness label for a Compass runtime snapshot."""
    parsed = brief_generated_at(payload)
    if parsed is None:
        return "no snapshot"
    current = now if now is not None else dt.datetime.now(tz=dt.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=dt.timezone.utc)
    delta = current - parsed
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        return "fresh"
    if total_seconds < 120:
        return "fresh"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h"
    days = hours // 24
    return f"{days}d"


def detect_host_family() -> str:
    """Return a compact host-family token for the active runtime."""
    explicit = str(os.environ.get("ODYLITH_HOST_FAMILY") or "").strip().lower()
    if explicit in {"codex", "claude"}:
        return explicit
    if os.environ.get(_CLAUDE_PROJECT_DIR_ENV):
        return "claude"
    if os.environ.get("CODEX_HOME") or os.environ.get("CODEX_HOST_RUNTIME"):
        return "codex"
    return "unknown"


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with ``Z`` suffix."""
    return dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def collapse_whitespace(value: object, *, limit: int = 220) -> str:
    """Normalize whitespace for single-line rendering and truncate past ``limit``."""
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
