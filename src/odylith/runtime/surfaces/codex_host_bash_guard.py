"""Codex PreToolUse Bash guard for destructive repo-policy violations."""

from __future__ import annotations

import argparse
import json
import sys

from odylith.runtime.surfaces import bash_guard_policy
from odylith.runtime.surfaces import host_hook_payload


def blocked_bash_reason(command: str) -> str:
    return bash_guard_policy.blocked_bash_reason(command)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex bash-guard",
        description="Evaluate Codex Bash tool payloads against the destructive-command guard.",
    )
    parser.add_argument("--repo-root", default=".", help=argparse.SUPPRESS)
    parser.parse_args(list(argv or sys.argv[1:]))
    payload = host_hook_payload.load_payload()
    reason = blocked_bash_reason(host_hook_payload.command_from_hook_payload(payload))
    if not reason:
        return 0
    sys.stdout.write(
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


if __name__ == "__main__":
    raise SystemExit(main())
