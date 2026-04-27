"""Claude Code PreToolUse hook: destructive-bash guard.

When Claude Code runs a Bash tool call, the ``PreToolUse`` hook fires
with the proposed command in the payload. This baked module mirrors the
legacy ``.claude/hooks/guard-destructive-bash.py`` script. It scans the
proposed command against a small block list of destructive shell forms
(``rm -rf``, ``git reset --hard``, ``git checkout --``, force-push,
``git clean -fdx``) and emits the canonical Claude
``permissionDecision: deny`` payload when one matches.

The guard is intentionally narrow: it only blocks the patterns that have
caused real damage in past Odylith dogfood runs. Anything else passes
through. The decision is exposed as a pure helper so tests can drive
``evaluate_bash_command`` directly without going through stdin.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

from odylith.runtime.surfaces import claude_host_shared


_BLOCK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(^|\s)rm\s+-rf(\s|$)"), "Destructive recursive deletion is blocked by repo policy."),
    (re.compile(r"git\s+reset\s+--hard(\s|$)"), "Hard reset is blocked by repo policy."),
    (re.compile(r"git\s+checkout\s+--(\s|$)"), "Discarding tracked changes with checkout is blocked by repo policy."),
    (re.compile(r"git\s+push\s+--force(?:-with-lease)?(\s|$)"), "Force-push is blocked by repo policy."),
    (re.compile(r"git\s+clean\s+-fdx(\s|$)"), "Full working-tree cleanup is blocked by repo policy."),
)


def evaluate_bash_command(command: str) -> tuple[bool, str]:
    """Return ``(blocked, reason)`` for a proposed bash command.

    A return of ``(False, "")`` means the command is allowed and no
    payload should be emitted. ``(True, reason)`` means the canonical
    deny payload should be emitted with the supplied reason.
    """
    text = str(command or "").strip()
    if not text:
        return (False, "")
    for pattern, reason in _BLOCK_PATTERNS:
        if pattern.search(text):
            return (True, reason)
    return (False, "")


def render_deny_payload(reason: str) -> dict[str, dict[str, str]]:
    """Render the canonical Claude PreToolUse deny payload."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude bash-guard",
        description="Evaluate the Odylith destructive-command guard for Claude Bash hooks.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith context.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude PreToolUse payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    command = str(tool_input.get("command", "")).strip()
    blocked, reason = evaluate_bash_command(command)
    if not blocked:
        return 0
    sys.stdout.write(json.dumps(render_deny_payload(reason)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
