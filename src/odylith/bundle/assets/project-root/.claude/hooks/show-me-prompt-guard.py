#!/usr/bin/env python3
"""Claude prompt hook that routes show-me capability requests."""

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
    "show capabilities",
)
_REPO_SHOW_ME_PHRASES: tuple[str, ...] = (
    "what can you do for this repo",
    "what can you do in this repo",
    "show me what you can do for this repo",
    "show me what you can do in this repo",
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


def _additional_context(project_dir: Path) -> str:
    del project_dir
    return (
        "Odylith show-me first-match route: this prompt asks for the advisory "
        "`odylith show` repo-capability demo, not install, runtime, intervention, "
        "or visibility diagnostics. Prefer the `odylith-show-me` skill if it is "
        "available. If the skill is not available, run the first command that works "
        "from the repo root and capture stdout only: "
        "`./.odylith/bin/odylith show --repo-root .`; "
        "`odylith show --repo-root .`. Return that stdout directly. Do not run "
        "`start`, `doctor`, `version`, `intervention-status`, `visible-intervention`, "
        "host compatibility checks, or launcher-state explanations unless the user "
        "explicitly asks for diagnostics."
    )


def main() -> int:
    project_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    payload = _load_payload()
    if not _is_show_me_prompt(payload.get("prompt", "")):
        return 0
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": _additional_context(project_dir),
                }
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
