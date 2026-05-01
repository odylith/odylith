#!/usr/bin/env python3
# ruff: noqa
"""Claude hook that blocks destructive Bash commands."""

from __future__ import annotations

import json
import re
import sys


_UNINSTALL_COMMAND = "./.odylith/bin/odylith uninstall --repo-root ."
_UNINSTALL_PREVIEW_COMMAND = "./.odylith/bin/odylith uninstall --repo-root . --dry-run"
_UNINSTALL_REMOVAL_REASON = (
    "Do not remove Odylith paths or host config directories with raw deletion. "
    f"Use `{_UNINSTALL_COMMAND}` for Odylith uninstall; raw deletion and hook bypasses are blocked. "
    f"Use `{_UNINSTALL_PREVIEW_COMMAND}` only for a scope preview. "
    "The uninstall command removes `.odylith/` runtime state, detaches Odylith hook entries, "
    "and preserves `odylith/` governed source truth. Host config directories such as "
    "`.claude/`, `.codex/`, and `.agents/` stay in place because they may contain user config."
)
_ODYLITH_OWNED_PATH_RE = re.compile(
    r"(?<![\w./-])(?:\./)?"
    r"(?:\.odylith|odylith|AGENTS\.md|CLAUDE\.md)"
    r"/?(?![\w.-])"
)
_HOST_CONFIG_PATH_RE = re.compile(
    r"(?<![\w./-])(?:\./)?"
    r"(?:\.agents|\.codex|\.claude)"
    r"/?(?![\w.-])"
)
_RM_RECURSIVE_FORCE_RE = re.compile(
    r"(^|[;&|()\s])rm\s+-(?:[A-Za-z]*r[A-Za-z]*f|[A-Za-z]*f[A-Za-z]*r)[A-Za-z]*(\s|$)"
)
_PYTHON_RMTREE_RE = re.compile(r"\bshutil\.rmtree\s*\(")
_BLOCK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"git\s+reset\s+--hard(\s|$)"), "Hard reset is blocked by repo policy."),
    (re.compile(r"git\s+checkout\s+--(\s|$)"), "Discarding tracked changes with checkout is blocked by repo policy."),
    (re.compile(r"git\s+push\s+--force(?:-with-lease)?(\s|$)"), "Force-push is blocked by repo policy."),
    (re.compile(r"git\s+clean\s+-fdx(\s|$)"), "Full working-tree cleanup is blocked by repo policy."),
)


def _references_odylith_managed_removal_target(command: str) -> bool:
    return bool(_ODYLITH_OWNED_PATH_RE.search(str(command or "")))


def _references_host_config_removal_target(command: str) -> bool:
    return bool(_HOST_CONFIG_PATH_RE.search(str(command or "")))


def _blocked_bash_reason(command: str) -> str:
    token = str(command or "").strip()
    if not token:
        return ""
    if _PYTHON_RMTREE_RE.search(token) and (
        _references_odylith_managed_removal_target(token)
        or _references_host_config_removal_target(token)
    ):
        return _UNINSTALL_REMOVAL_REASON
    if _RM_RECURSIVE_FORCE_RE.search(token):
        if (
            _references_odylith_managed_removal_target(token)
            or _references_host_config_removal_target(token)
        ):
            return _UNINSTALL_REMOVAL_REASON
        return "Destructive recursive deletion is blocked by repo policy."
    for pattern, reason in _BLOCK_PATTERNS:
        if pattern.search(token):
            return reason
    return ""


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return 0
    command = str(tool_input.get("command", "")).strip()
    if not command:
        return 0
    reason = _blocked_bash_reason(command)
    if reason:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
