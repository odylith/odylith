"""Shared destructive-command policy for Odylith host Bash guards."""

from __future__ import annotations

import re


UNINSTALL_COMMAND = "./.odylith/bin/odylith uninstall --repo-root ."
UNINSTALL_REMOVAL_REASON = (
    "Odylith-managed paths must be removed with "
    f"`{UNINSTALL_COMMAND}`; raw deletion and hook bypasses are blocked."
)

_MANAGED_PATH_RE = re.compile(
    r"(?<![\w./-])(?:\./)?"
    r"(?:\.odylith|odylith|\.agents|\.codex|\.claude|AGENTS\.md|CLAUDE\.md)"
    r"/?(?![\w.-])"
)
_RM_RECURSIVE_FORCE_RE = re.compile(
    r"(^|[;&|()\s])rm\s+-(?:[A-Za-z]*r[A-Za-z]*f|[A-Za-z]*f[A-Za-z]*r)[A-Za-z]*(\s|$)"
)
_PYTHON_RMTREE_RE = re.compile(r"\bshutil\.rmtree\s*\(")
_GIT_RESET_HARD_RE = re.compile(r"git\s+reset\s+--hard(\s|$)")
_GIT_CHECKOUT_DISCARD_RE = re.compile(r"git\s+checkout\s+--(\s|$)")
_GIT_FORCE_PUSH_RE = re.compile(r"git\s+push\s+--force(?:-with-lease)?(\s|$)")
_GIT_CLEAN_FDX_RE = re.compile(r"git\s+clean\s+-fdx(\s|$)")


def references_odylith_managed_removal_target(command: str) -> bool:
    """Return whether a command names repo-local Odylith-managed paths."""
    return bool(_MANAGED_PATH_RE.search(str(command or "")))


def blocked_bash_reason(command: str) -> str:
    """Return the host-facing block reason for a proposed Bash command."""
    token = str(command or "").strip()
    if not token:
        return ""
    if _PYTHON_RMTREE_RE.search(token) and references_odylith_managed_removal_target(token):
        return UNINSTALL_REMOVAL_REASON
    if _RM_RECURSIVE_FORCE_RE.search(token):
        if references_odylith_managed_removal_target(token):
            return UNINSTALL_REMOVAL_REASON
        return "Destructive recursive deletion is blocked by repo policy."
    if _GIT_RESET_HARD_RE.search(token):
        return "Hard reset is blocked by repo policy."
    if _GIT_CHECKOUT_DISCARD_RE.search(token):
        return "Discarding tracked changes with checkout is blocked by repo policy."
    if _GIT_FORCE_PUSH_RE.search(token):
        return "Force-push is blocked by repo policy."
    if _GIT_CLEAN_FDX_RE.search(token):
        return "Full working-tree cleanup is blocked by repo policy."
    return ""
