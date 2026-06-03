"""Assistant-rendered fallback for chat-visible Odylith moments."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

from odylith.runtime.intervention_engine import conversation_closeout
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import prompt_signal_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import visibility_broker
from odylith.runtime.intervention_engine import visibility_replay
from odylith.runtime.surfaces import host_intervention_support

_PROMPT_SUBMIT_PHASES = {"prompt_submit", "userpromptsubmit"}


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _confirm_rendered_chat(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    rendered: str,
) -> None:
    host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message=rendered,
        render_surface=f"{_normalize_text(host_family).lower() or 'host'}_visible_intervention",
    )


def _stop_summary_assist_text(summary: object, *, forced: bool = False, changed_paths: Sequence[str] = ()) -> str:
    text = _normalize_text(summary)
    if not text:
        return ""
    if not forced and not changed_paths and not _looks_like_completed_work_summary(text):
        return ""
    return (
        "**Odylith Assist:** Closeout reached in chat; no separate Observation or Proposal earned this turn."
    )


def _looks_like_completed_work_summary(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:built|changed|completed|fixed|hardened|implemented|patched|ran|repaired|updated|validated|worked)\b",
            value,
            flags=re.IGNORECASE,
        )
    )


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
    confirm_chat_delivery: bool = False,
) -> str:
    """Render the exact Markdown an assistant should show when hooks are hidden."""

    normalized_phase = " ".join(str(phase or "").split()).strip().lower() or "stop_summary"
    visibility_feedback = conversation_closeout.visibility_feedback_requested(
        prompt=prompt,
        assistant_summary=summary,
    )
    if (
        normalized_phase
        in {"prompt_submit", "userpromptsubmit", "post_bash_checkpoint", "stop_summary"}
        and host_intervention_support.suppress_prompt_live_narration(
            prompt=prompt,
            assistant_summary=summary,
        )
        and not visibility_feedback
        and not changed_paths
        and include_closeout is None
    ):
        return ""
    proposal = normalized_phase not in {"prompt_submit", "userpromptsubmit", "stop_summary"}
    if include_proposal is not None:
        proposal = bool(include_proposal)
    closeout = (
        normalized_phase == "stop_summary"
        or normalized_phase in _PROMPT_SUBMIT_PHASES
        or visibility_feedback
    )
    if include_closeout is not None:
        closeout = bool(include_closeout)
    prompt_visibility_feedback_only = (
        prompt_signal_runtime.assist_visibility_feedback_requested(
            prompt=prompt,
            assistant_summary=summary,
        )
        and normalized_phase in _PROMPT_SUBMIT_PHASES
        and include_proposal is None
        and not changed_paths
    )
    resolved_session = host_surface_runtime.normalized_session_id(session_id, host_family=host_family)
    replay = visibility_replay.replayable_chat_markdown(
        repo_root=repo_root,
        host_family=host_family,
        session_id=resolved_session,
        include_assist=closeout,
        include_teaser=False,
    )
    if replay and not (closeout and normalized_phase != "stop_summary"):
        if confirm_chat_delivery:
            _confirm_rendered_chat(
                repo_root=repo_root,
                host_family=host_family,
                session_id=resolved_session,
                rendered=replay,
            )
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
    if normalized_phase in _PROMPT_SUBMIT_PHASES and closeout:
        bundle = host_intervention_support.ensure_prompt_visible_assist_bundle(bundle)
    visible_override = ""
    if prompt_visibility_feedback_only:
        visible_override = conversation_surface.render_closeout_text(bundle, markdown=True)
    elif replay and closeout:
        visible_override = host_intervention_support.merge_replay_with_closeout(
            replay=replay,
            closeout_text=conversation_surface.render_closeout_text(bundle, markdown=True),
        )
        if visible_override == replay:
            if confirm_chat_delivery:
                _confirm_rendered_chat(
                    repo_root=repo_root,
                    host_family=host_family,
                    session_id=resolved_session,
                    rendered=replay,
                )
            return replay
    delivery_channel = (
        "manual_visible_command"
        if confirm_chat_delivery
        else visibility_broker.ASSISTANT_RENDER_REQUIRED_CHANNEL
    )
    delivery_status = (
        "manual_visible"
        if confirm_chat_delivery
        else visibility_broker.ASSISTANT_RENDER_REQUIRED_STATUS
    )
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=repo_root,
        bundle=bundle,
        host_family=host_family,
        turn_phase=normalized_phase,
        session_id=session_id,
        include_proposal=proposal,
        include_closeout=closeout,
        developer_include_closeout=closeout,
        delivery_channel=delivery_channel,
        delivery_status=delivery_status,
        visible_markdown_override=visible_override,
    )
    rendered = decision.visible_markdown
    if (
        closeout
        and normalized_phase in _PROMPT_SUBMIT_PHASES
        and not host_intervention_support.contains_assist(rendered)
    ):
        rendered = host_intervention_support.compose_prompt_visible_markdown(
            visible_markdown=rendered,
            bundle=bundle,
        )
        decision = host_surface_runtime.visible_intervention_decision(
            repo_root=repo_root,
            bundle=bundle,
            host_family=host_family,
            turn_phase=normalized_phase,
            session_id=session_id,
            include_proposal=proposal,
            include_closeout=True,
            developer_include_closeout=True,
            delivery_channel=decision.delivery_channel,
            delivery_status=decision.delivery_status,
            visible_markdown_override=rendered,
        )
        rendered = decision.visible_markdown
    if not rendered and closeout and normalized_phase == "stop_summary":
        rendered = _stop_summary_assist_text(
            summary,
            forced=include_closeout is True,
            changed_paths=changed_paths,
        )
    if rendered and record_delivery:
        host_surface_runtime.append_visible_intervention_events(
            repo_root=Path(repo_root).expanduser().resolve(),
            bundle=bundle,
            decision=decision,
            render_surface=f"{_normalize_text(host_family).lower() or 'host'}_visible_intervention",
        )
    if rendered and confirm_chat_delivery:
        _confirm_rendered_chat(
            repo_root=repo_root,
            host_family=host_family,
            session_id=resolved_session,
            rendered=rendered,
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
    parser.add_argument(
        "--confirm-chat",
        action="store_true",
        help="Record the rendered fallback as chat-confirmed when stdout will be relayed verbatim into the chat.",
    )
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
        confirm_chat_delivery=bool(args.confirm_chat),
    )
    if rendered:
        sys.stdout.write(rendered + "\n")
    return 0
