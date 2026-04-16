"""Claude Code UserPromptSubmit hook for best-effort Odylith teasers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.surfaces import claude_host_prompt_context
from odylith.runtime.surfaces import claude_host_shared


def render_prompt_teaser(
    *,
    repo_root: Path | str = ".",
    prompt: str,
    session_id: str = "",
    conversation_bundle_override: dict[str, object] | None = None,
) -> str:
    """Render only the one-line prompt teaser, if one is earned."""

    return claude_host_prompt_context.render_prompt_system_message(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=conversation_bundle_override,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude prompt-teaser",
        description="Render the best-effort Odylith Claude UserPromptSubmit teaser.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith context resolution.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude UserPromptSubmit payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    prompt = str(payload.get("prompt", "")).strip()
    session_id = claude_host_shared.hook_session_id(payload)
    bundle = claude_host_prompt_context._prompt_conversation_bundle(  # noqa: SLF001
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
    )
    teaser = render_prompt_teaser(
        repo_root=repo_root,
        prompt=prompt,
        session_id=session_id,
        conversation_bundle_override=bundle,
    )
    if teaser:
        conversation_surface.append_intervention_events(
            repo_root=Path(repo_root).expanduser().resolve(),
            bundle=bundle,
            include_proposal=False,
        )
        sys.stdout.write(teaser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
