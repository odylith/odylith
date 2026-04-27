#!/usr/bin/env python3
"""Claude hook that blocks destructive Bash commands."""

from __future__ import annotations

import json
import re
import sys


_BLOCK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|\s)rm\s+-rf(\s|$)"), "Destructive recursive deletion is blocked by repo policy."),
    (re.compile(r"git\s+reset\s+--hard(\s|$)"), "Hard reset is blocked by repo policy."),
    (re.compile(r"git\s+checkout\s+--(\s|$)"), "Discarding tracked changes with checkout is blocked by repo policy."),
    (re.compile(r"git\s+push\s+--force(?:-with-lease)?(\s|$)"), "Force-push is blocked by repo policy."),
    (re.compile(r"git\s+clean\s+-fdx(\s|$)"), "Full working-tree cleanup is blocked by repo policy."),
)


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
    for pattern, reason in _BLOCK_PATTERNS:
        if pattern.search(command):
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
