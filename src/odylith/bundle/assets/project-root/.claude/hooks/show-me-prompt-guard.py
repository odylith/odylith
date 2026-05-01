#!/usr/bin/env python3
# ruff: noqa
"""Claude prompt hook that routes first-match show-me and help requests."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


_ODYLITH_SHOW_ME_PHRASES: tuple[str, ...] = (
    "show me what you can do",
    "what can you do",
    "what can odylith do",
    "show odylith",
)
_CAPABILITY_INVENTORY_PHRASES: tuple[str, ...] = (
    "capabilities and engines",
    "capability and engine",
    "capability map",
    "product architecture",
    "show capabilities",
    "odylith capabilities",
)
_REPO_SHOW_ME_PHRASES: tuple[str, ...] = (
    "what can you do for this repo",
    "what can you do in this repo",
    "show me what you can do for this repo",
    "show me what you can do in this repo",
)
_HELP_PHRASES: tuple[str, ...] = (
    "odylith help",
    "odylith, help",
    "help odylith",
    "help, odylith",
)


def _load_payload(raw: str | None = None) -> dict[str, Any]:
    text = raw if raw is not None else sys.stdin.read()
    try:
        payload = json.loads(text or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _is_show_me_prompt(prompt: object) -> bool:
    text = _normalize(prompt)
    if not text:
        return False
    if "odylith" in text and any(phrase in text for phrase in _ODYLITH_SHOW_ME_PHRASES):
        return True
    return any(phrase in text for phrase in _REPO_SHOW_ME_PHRASES)


def _is_help_prompt(prompt: object) -> bool:
    return _normalize(prompt).rstrip(".!?") in _HELP_PHRASES


def _is_capability_inventory_prompt(prompt: object) -> bool:
    text = _normalize(prompt)
    return "odylith" in text and any(phrase in text for phrase in _CAPABILITY_INVENTORY_PHRASES)


def _additional_context(project_dir: Path) -> str:
    del project_dir
    return (
        "Odylith show-me first-match route lock: this prompt asks for the advisory "
        "`odylith show` repo-capability demo. You must not answer as generic Claude "
        "Code, list Claude tool, skill, or memory inventories, inspect docs, list "
        "repository files, "
        "report branch cleanliness, or ask what the user wants. Use the "
        "`odylith-show-me` skill if it is available. Otherwise run the first command "
        "that works from the repo root and capture stdout only: "
        "`./.odylith/bin/odylith show --repo-root .`; "
        "`odylith show --repo-root .`. Return that stdout directly. Do not run "
        "`start`, `doctor`, `version`, `intervention-status`, `visible-intervention`, "
        "host compatibility checks, or launcher-state explanations unless the user "
        "explicitly asks for diagnostics. If neither command can run, report only "
        "the shortest actionable Odylith show blocker."
    )


def _help_additional_context(project_dir: Path) -> str:
    del project_dir
    return (
        "Odylith help first-match route lock: this prompt asks for the CLI help surface, "
        "not generic Claude capabilities, install, runtime, intervention, launcher, or "
        "repo diagnosis. Run the first command that works from the repo root and capture stdout only: "
        "`./.odylith/bin/odylith --help`; `odylith --help`. Return that stdout "
        "directly. Do not run `start`, `show`, `doctor`, `version`, "
        "`intervention-status`, `visible-intervention`, host compatibility checks, "
        "or launcher-state explanations unless the user explicitly asks for diagnostics."
    )


def _capability_inventory_context(project_dir: Path) -> str:
    del project_dir
    return (
        "Odylith capability-inventory route lock: this prompt asks for Odylith's "
        "product-owned capabilities, engines, and architecture map. Do not infer "
        "the taxonomy from `odylith --help`, `odylith show`, Claude tools, skills, "
        "memory, local files, or generic Claude Code capability prose. Run the "
        "first command that works from the repo root and capture stdout only: "
        "`./.odylith/bin/odylith capabilities --repo-root .`; "
        "`odylith capabilities --repo-root .`. Return that stdout directly."
    )


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    payload = _load_payload()
    prompt = payload.get("prompt", "")
    if _is_capability_inventory_prompt(prompt):
        additional_context = _capability_inventory_context(project_dir)
    elif _is_show_me_prompt(prompt):
        additional_context = _additional_context(project_dir)
    elif _is_help_prompt(prompt):
        additional_context = _help_additional_context(project_dir)
    else:
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": additional_context,
                }
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
