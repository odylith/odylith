"""Codex UserPromptSubmit hook renderer for explicit Odylith anchors."""

from __future__ import annotations

import argparse
import json
import sys

from odylith.runtime.surfaces import codex_host_shared


def render_codex_prompt_context(
    repo_root: str = ".",
    *,
    prompt: str,
    summary_override: str = "",
) -> str:
    ref = codex_host_shared.prompt_anchor(prompt)
    if not ref:
        return ""
    return summary_override or codex_host_shared.context_summary(project_dir=repo_root, ref=ref)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex prompt-context",
        description="Render the Odylith-grounded UserPromptSubmit hook output for Codex.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for context resolution.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    payload = codex_host_shared.load_payload()
    summary = render_codex_prompt_context(args.repo_root, prompt=str(payload.get("prompt", "")).strip())
    if not summary:
        return 0
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": summary,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
