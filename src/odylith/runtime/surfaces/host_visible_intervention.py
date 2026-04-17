"""Assistant-rendered fallback for chat-visible Odylith moments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_replay


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def render_visible_intervention(
    *,
    repo_root: Path | str = ".",
    host_family: str,
    phase: str,
    prompt: str = "",
    summary: str = "",
    changed_paths: Sequence[str] = (),
    session_id: str = "",
    include_proposal: bool | None = None,
    include_closeout: bool | None = None,
    record_delivery: bool = False,
) -> str:
    """Render the exact Markdown an assistant should show when hooks are hidden."""

    normalized_phase = " ".join(str(phase or "").split()).strip().lower() or "stop_summary"
    proposal = normalized_phase not in {"prompt_submit", "userpromptsubmit", "stop_summary"}
    if include_proposal is not None:
        proposal = bool(include_proposal)
    closeout = normalized_phase == "stop_summary"
    if include_closeout is not None:
        closeout = bool(include_closeout)
    resolved_session = host_surface_runtime.normalized_session_id(session_id, host_family=host_family)
    replay = visibility_replay.replayable_chat_markdown(
        repo_root=repo_root,
        host_family=host_family,
        session_id=resolved_session,
        include_assist=closeout,
        include_teaser=False,
    )
    if replay:
        return replay
    bundle = host_surface_runtime.compose_host_conversation_bundle(
        repo_root=repo_root,
        host_family=host_family,
        turn_phase=normalized_phase,
        session_id=resolved_session,
        prompt_excerpt=prompt,
        assistant_summary=summary,
        changed_paths=changed_paths,
    )
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=repo_root,
        bundle=bundle,
        host_family=host_family,
        turn_phase=normalized_phase,
        session_id=session_id,
        include_proposal=proposal,
        include_closeout=closeout,
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
    )
    rendered = decision.visible_markdown
    if rendered and record_delivery:
        host_surface_runtime.append_visible_intervention_events(
            repo_root=Path(repo_root).expanduser().resolve(),
            bundle=bundle,
            decision=decision,
            render_surface=f"{_normalize_text(host_family).lower() or 'host'}_visible_intervention",
        )
    return rendered


def main_with_host(host_family: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=f"odylith {host_family} visible-intervention",
        description="Render chat-visible Odylith Markdown when host hook display is hidden.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith context resolution.")
    parser.add_argument(
        "--phase",
        default="stop_summary",
        choices=("prompt_submit", "post_bash_checkpoint", "post_edit_checkpoint", "stop_summary"),
        help="Conversation phase to render.",
    )
    parser.add_argument("--prompt", default="", help="Prompt excerpt to ground the visible moment.")
    parser.add_argument("--summary", default="", help="Assistant summary to ground closeout rendering.")
    parser.add_argument("--session-id", default="", help="Host session id for event-history recovery.")
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Changed repo-relative path. May be repeated.",
    )
    parser.add_argument("--include-proposal", action="store_true", help="Force proposal rendering when eligible.")
    parser.add_argument("--include-closeout", action="store_true", help="Force closeout Assist rendering.")
    args = parser.parse_args(list(argv or sys.argv[1:]))
    rendered = render_visible_intervention(
        repo_root=args.repo_root,
        host_family=host_family,
        phase=args.phase,
        prompt=args.prompt,
        summary=args.summary,
        changed_paths=args.changed_path,
        session_id=args.session_id,
        include_proposal=True if args.include_proposal else None,
        include_closeout=True if args.include_closeout else None,
        record_delivery=True,
    )
    if rendered:
        sys.stdout.write(rendered + "\n")
    return 0
