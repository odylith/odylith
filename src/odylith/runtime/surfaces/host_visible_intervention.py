"""Assistant-rendered fallback for chat-visible Odylith moments."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import stream_state


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _operator_reports_visibility_failure(*, prompt: str, summary: str) -> bool:
    text = f"{prompt} {summary}".casefold()
    if not text.strip():
        return False
    direct_markers = (
        "not seeing",
        "do not see",
        "don't see",
        "cannot see",
        "can't see",
        "not visible",
        "no hook output",
        "no hook outputs",
        "hook output hidden",
        "hidden hook",
        "assist stopped",
        "assist is not",
        "intervention is not",
        "interventions are not",
        "observation is not",
        "proposal is not",
        "not rendering",
        "not showing",
    )
    if any(marker in text for marker in direct_markers):
        return True
    if "not working" in text and any(token in text for token in ("odylith", "intervention", "assist", "hook", "chat", "ux")):
        return True
    if _normalize_text(prompt).casefold() in {"i do not think it is working", "i don't think it is working"}:
        return True
    return False


def _operator_visibility_failure_observation(*, host_family: str) -> str:
    host = _normalize_text(host_family).capitalize() or "This host"
    return (
        "**Odylith Observation:** This is a visibility failure, not a quiet moment. "
        f"{host} may be computing intervention payloads, but this chat has not proven "
        "that hooks are actually rendering them, so the assistant has to show the "
        "Odylith Markdown directly until the host path is visibly proven."
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
) -> str:
    """Render the exact Markdown an assistant should show when hooks are hidden."""

    normalized_phase = " ".join(str(phase or "").split()).strip().lower() or "stop_summary"
    proposal = normalized_phase not in {"prompt_submit", "userpromptsubmit", "stop_summary"}
    if include_proposal is not None:
        proposal = bool(include_proposal)
    closeout = normalized_phase == "stop_summary"
    if include_closeout is not None:
        closeout = bool(include_closeout)
    bundle = host_surface_runtime.compose_host_conversation_bundle(
        repo_root=repo_root,
        host_family=host_family,
        turn_phase=normalized_phase,
        session_id=session_id,
        prompt_excerpt=prompt,
        assistant_summary=summary,
        changed_paths=changed_paths,
    )
    parts: list[str] = []
    live = host_surface_runtime.render_visible_live_intervention(
        bundle,
        markdown=True,
        include_proposal=proposal,
    )
    closeout_text = (
        conversation_surface.render_closeout_text(bundle, markdown=True)
        if closeout
        else ""
    )
    for text in (live, closeout_text):
        token = str(text or "").strip()
        if token and token not in parts:
            parts.append(token)
    rendered = "\n\n".join(parts).strip()
    if _operator_reports_visibility_failure(prompt=prompt, summary=summary) and "**Odylith Observation:**" not in rendered:
        fallback = _operator_visibility_failure_observation(host_family=host_family)
        if record_delivery:
            stream_state.append_intervention_event(
                repo_root=Path(repo_root).expanduser().resolve(),
                kind="intervention_card",
                summary="Visibility failure fallback rendered.",
                session_id=session_id,
                host_family=host_family,
                intervention_key=f"visible-fallback-{_normalize_text(host_family).lower() or 'host'}",
                turn_phase=normalized_phase,
                display_markdown=fallback,
                display_plain=fallback.replace("**", ""),
                prompt_excerpt=prompt,
                assistant_summary=summary,
                moment_kind="visibility",
                semantic_signature=("visibility", "fallback"),
                delivery_channel="manual_visible_command",
                delivery_status="manual_visible",
                render_surface=f"{_normalize_text(host_family).lower() or 'host'}_visible_intervention",
            )
        return fallback
    if rendered and record_delivery:
        conversation_surface.append_intervention_events(
            repo_root=Path(repo_root).expanduser().resolve(),
            bundle=bundle,
            include_proposal=proposal,
            include_closeout=closeout,
            delivery_channel="manual_visible_command",
            delivery_status="manual_visible",
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
