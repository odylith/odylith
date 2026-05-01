"""Claude Code PreToolUse hook: Bash command guard.

When Claude Code runs a Bash tool call, the ``PreToolUse`` hook fires
with the proposed command in the payload. This baked module mirrors the
legacy ``.claude/hooks/guard-destructive-bash.py`` script. It scans the
proposed command against a small block list of destructive shell forms
(``rm -rf``, ``git reset --hard``, ``git checkout --``, force-push,
``git clean -fdx``) and emits the canonical Claude
``permissionDecision: deny`` payload when one matches.

The guard is intentionally narrow: it blocks patterns that have caused real
damage in past Odylith dogfood runs, plus Claude-specific command
mistranslations where the model turns a strict Odylith CLI enum into prose.
Anything else passes through. The decision is exposed as a pure helper so
tests can drive ``evaluate_bash_command`` directly without going through stdin.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys

from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import bash_guard_policy

_BACKLOG_COMPLEXITY_VALUES = ("Low", "Medium", "High", "VeryHigh")
_BACKLOG_SIZING_VALUES = ("XS", "S", "M", "L", "XL")
_LOWER_COMPLEXITY_VALUES = {value.lower(): value for value in _BACKLOG_COMPLEXITY_VALUES}
_LOWER_SIZING_VALUES = {value.lower(): value for value in _BACKLOG_SIZING_VALUES}


def _shell_tokens(command: str) -> list[str]:
    normalized = str(command or "").replace("\\\n", " ").replace("\n", " ")
    try:
        return shlex.split(normalized)
    except ValueError:
        return []


def _looks_like_odylith_launcher(token: str) -> bool:
    value = str(token or "").strip()
    return value == "odylith" or value.endswith("/odylith")


def _option_value(tokens: list[str], option: str) -> str:
    prefix = f"{option}="
    for index, token in enumerate(tokens):
        if token == option and index + 1 < len(tokens):
            return str(tokens[index + 1]).strip()
        if token.startswith(prefix):
            return str(token[len(prefix) :]).strip()
    return ""


def _claude_backlog_enum_reason(command: str) -> str:
    tokens = _shell_tokens(command)
    if not tokens:
        return ""
    for index, token in enumerate(tokens):
        if not _looks_like_odylith_launcher(token):
            continue
        if tokens[index + 1 : index + 3] != ["backlog", "create"]:
            continue
        complexity = _option_value(tokens, "--complexity")
        if complexity and complexity not in _BACKLOG_COMPLEXITY_VALUES:
            suggested = _LOWER_COMPLEXITY_VALUES.get(complexity.lower(), "Medium")
            return (
                "Claude generated a non-canonical Odylith backlog complexity "
                f"`{complexity}`. Re-run with `--complexity {suggested}`. "
                f"Allowed complexity values: {', '.join(_BACKLOG_COMPLEXITY_VALUES)}."
            )
        sizing = _option_value(tokens, "--sizing")
        if sizing and sizing not in _BACKLOG_SIZING_VALUES:
            suggested = _LOWER_SIZING_VALUES.get(sizing.lower(), "M")
            return (
                "Claude generated a non-canonical Odylith backlog sizing "
                f"`{sizing}`. Re-run with `--sizing {suggested}`. "
                f"Allowed sizing values: {', '.join(_BACKLOG_SIZING_VALUES)}."
            )
    return ""


def evaluate_bash_command(command: str) -> tuple[bool, str]:
    """Return ``(blocked, reason)`` for a proposed bash command.

    A return of ``(False, "")`` means the command is allowed and no
    payload should be emitted. ``(True, reason)`` means the canonical
    deny payload should be emitted with the supplied reason.
    """
    text = str(command or "").strip()
    if not text:
        return (False, "")
    host_specific_reason = _claude_backlog_enum_reason(text)
    if host_specific_reason:
        return (True, host_specific_reason)
    reason = bash_guard_policy.blocked_bash_reason(text)
    return (bool(reason), reason)


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
