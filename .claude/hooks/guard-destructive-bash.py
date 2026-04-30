#!/usr/bin/env python3
# ruff: noqa
"""Claude hook that blocks destructive Bash commands."""

from __future__ import annotations

import json
import re
import sys


_UNINSTALL_COMMAND = "./.odylith/bin/odylith uninstall --repo-root ."
_UNINSTALL_REMOVAL_REASON = (
    "Odylith-managed paths must be removed with "
    f"`{_UNINSTALL_COMMAND}`; raw deletion and hook bypasses are blocked."
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
_BLOCK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"git\s+reset\s+--hard(\s|$)"), "Hard reset is blocked by repo policy."),
    (re.compile(r"git\s+checkout\s+--(\s|$)"), "Discarding tracked changes with checkout is blocked by repo policy."),
    (re.compile(r"git\s+push\s+--force(?:-with-lease)?(\s|$)"), "Force-push is blocked by repo policy."),
    (re.compile(r"git\s+clean\s+-fdx(\s|$)"), "Full working-tree cleanup is blocked by repo policy."),
)


def _references_odylith_managed_removal_target(command: str) -> bool:
    return bool(_MANAGED_PATH_RE.search(str(command or "")))


def _blocked_bash_reason(command: str) -> str:
    token = str(command or "").strip()
    if not token:
        return ""
    if _PYTHON_RMTREE_RE.search(token) and _references_odylith_managed_removal_target(token):
        return _UNINSTALL_REMOVAL_REASON
    if _RM_RECURSIVE_FORCE_RE.search(token):
        if _references_odylith_managed_removal_target(token):
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
