"""Shared chat-visible intervention decision broker.

This module is intentionally small and local-only. Host adapters pass in an
already-built conversation bundle, and the broker decides the visible Markdown,
developer continuity, delivery proof status, and event-recording posture in one
place.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import delivery_ledger
from odylith.runtime.intervention_engine import stream_state

VISIBLE_DELIVERY_STATUSES: frozenset[str] = frozenset(
    {
        "assistant_chat_confirmed",
        "best_effort_visible",
        "manual_visible",
        "stop_continuation_ready",
    }
)
VISIBLE_DELIVERY_CHANNELS: frozenset[str] = frozenset(
    {
        "assistant_chat_transcript",
        "manual_visible_command",
        "stdout_teaser",
        "stop_one_shot_guard",
    }
)
ASSISTANT_RENDER_REQUIRED_STATUS = "assistant_render_required"
ASSISTANT_RENDER_REQUIRED_CHANNEL = "assistant_visible_fallback"
LIVE_BOUNDARY_REQUIRED_KINDS: frozenset[str] = frozenset(
    {
        "ambient_signal",
        "capture_proposed",
        "intervention_card",
        "intervention_teaser",
    }
)


@dataclass(frozen=True)
class VisibleInterventionDecision:
    visible_markdown: str = ""
    developer_context: str = ""
    delivery_channel: str = ""
    delivery_status: str = ""
    proof_required: bool = False
    no_output_reason: str = ""
    latency_ms: float = 0.0
    source_fingerprints: dict[str, str] | None = None
    visibility_summary: dict[str, Any] | None = None
    include_proposal: bool = False
    include_closeout: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "visible_markdown": self.visible_markdown,
            "developer_context": self.developer_context,
            "delivery_channel": self.delivery_channel,
            "delivery_status": self.delivery_status,
            "proof_required": self.proof_required,
            "no_output_reason": self.no_output_reason,
            "latency_ms": self.latency_ms,
            "source_fingerprints": dict(self.source_fingerprints or {}),
            "visibility_summary": dict(self.visibility_summary or {}),
            "include_proposal": self.include_proposal,
            "include_closeout": self.include_closeout,
        }


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _normalize_block_string(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    rows: list[str] = []
    blank_run = 0
    for raw_line in text.split("\n"):
        line = str(raw_line).rstrip()
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            rows.append("")
            continue
        blank_run = 0
        rows.append(line)
    return "\n".join(rows).strip()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _hash_payload(value: Any) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    except (TypeError, ValueError):
        encoded = repr(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _parts(*values: str) -> str:
    rows: list[str] = []
    for value in values:
        token = _normalize_block_string(value)
        if token and token not in rows:
            rows.append(token)
    return "\n\n".join(rows).strip()


def _operator_reports_visibility_failure(*, prompt: str, summary: str) -> bool:
    text = f"{prompt} {summary}".casefold()
    if not text.strip():
        return False
    benign_suppression_markers = (
        "assist is not needed",
        "assist is not necessary",
        "intervention is not needed",
        "intervention is not necessary",
        "interventions are not needed",
        "interventions are not necessary",
        "observation is not needed",
        "observation is not necessary",
        "proposal is not needed",
        "proposal is not necessary",
    )
    explicit_visibility_markers = (
        "zero ambient",
        "zero intervention",
        "zero signal",
        "zero signals",
        "no ambient highlight",
        "no ambient highlights",
        "no intervention block",
        "no intervention blocks",
        "no intervention in chat",
        "no interventions in chat",
        "no signal in chat",
        "no signals in chat",
        "not visible",
        "not rendering",
        "not showing",
        "inside the chat",
        "in my chat",
        "hook output hidden",
        "hidden hook",
    )
    if (
        any(marker in text for marker in benign_suppression_markers)
        and not any(marker in text for marker in explicit_visibility_markers)
    ):
        return False
    direct_markers = (
        "zero ambient",
        "zero intervention",
        "zero signal",
        "zero signals",
        "no ambient highlight",
        "no ambient highlights",
        "no intervention block",
        "no intervention blocks",
        "no intervention in chat",
        "no interventions in chat",
        "no signal in chat",
        "no signals in chat",
        "zero assis",
        "zero assist",
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
        "only assist works",
        "only assit works",
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
    visibility_terms = (
        "visible",
        "visibility",
        "rendering",
        "showing",
        "chat output",
        "hook output",
        "ux",
        "inside the chat",
        "in my chat",
        "need to be visible",
        "needs to be visible",
        "must be visible",
    )
    odylith_terms = ("odylith", "intervention", "assist", "assit", "observation", "proposal", "hook", "ambient")
    uncertainty_terms = ("not sure", "unsure", "still not sure")
    if (
        any(marker in text for marker in uncertainty_terms)
        and any(marker in text for marker in visibility_terms)
        and any(marker in text for marker in odylith_terms)
    ):
        return True
    prompt_token = _normalize_string(prompt).casefold()
    if prompt_token in {"i do not think it is working", "i don't think it is working"}:
        return True
    return "not working" in text and any(token in text for token in ("odylith", "intervention", "assist", "hook", "chat", "ux"))


def reports_visibility_failure(*, prompt: str = "", summary: str = "") -> bool:
    """Return whether an operator complaint requires hard chat-visible fallback."""

    return _operator_reports_visibility_failure(prompt=prompt, summary=summary)


def _wrap_live_text(value: str) -> str:
    text = _normalize_block_string(value)
    if not text:
        return ""
    if text.startswith("---\n") and text.endswith("\n---"):
        text = _normalize_block_string(text[4:-4])
    return f"---\n\n{text}\n\n---"


def _visibility_failure_observation(*, host_family: str) -> str:
    host = _normalize_string(host_family).capitalize() or "This host"
    return _wrap_live_text(
        "**Odylith Observation:** This is a visibility failure, not a quiet moment. "
        f"{host} may be computing intervention payloads, but this chat has not proven "
        "that hooks are actually rendering them, so the assistant has to show the "
        "Odylith Markdown directly until the host path is visibly proven."
    )


def _render_visible(
    bundle: Mapping[str, Any],
    *,
    include_proposal: bool,
    include_closeout: bool,
) -> str:
    live = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=include_proposal,
    )
    closeout = (
        conversation_surface.render_closeout_text(bundle, markdown=True)
        if include_closeout
        else ""
    )
    return _parts(live, closeout)


def _render_developer_context(
    bundle: Mapping[str, Any],
    *,
    include_proposal: bool,
    include_closeout: bool,
) -> str:
    return _render_visible(
        bundle,
        include_proposal=include_proposal,
        include_closeout=include_closeout,
    )


def _delivery_is_visible(*, channel: str, status: str) -> bool:
    return _normalize_token(status) in VISIBLE_DELIVERY_STATUSES or _normalize_token(channel) in VISIBLE_DELIVERY_CHANNELS


def _default_delivery(
    *,
    visible_markdown: str,
    host_family: str,
    turn_phase: str,
    visibility_proven: bool,
    unconfirmed_event_count: int,
    visibility_failure: bool,
) -> tuple[str, str]:
    if not visible_markdown:
        return "", ""
    phase = _normalize_token(turn_phase)
    host = _normalize_token(host_family)
    if phase == "stop_summary":
        return "stop_one_shot_guard", "stop_continuation_ready"
    if host == "claude" and phase in {"prompt_submit", "userpromptsubmit"}:
        return "stdout_teaser", "best_effort_visible"
    if visibility_proven and not visibility_failure and int(unconfirmed_event_count) <= 0:
        return "system_message_and_assistant_fallback", "assistant_fallback_ready"
    return ASSISTANT_RENDER_REQUIRED_CHANNEL, ASSISTANT_RENDER_REQUIRED_STATUS


def build_visible_intervention_decision(
    *,
    repo_root: Path | str,
    bundle: Mapping[str, Any],
    host_family: str,
    turn_phase: str,
    session_id: str = "",
    include_proposal: bool,
    include_closeout: bool,
    developer_include_closeout: bool | None = None,
    delivery_channel: str = "",
    delivery_status: str = "",
    visible_markdown_override: str = "",
) -> VisibleInterventionDecision:
    started = time.perf_counter()
    root = Path(repo_root).expanduser().resolve()
    normalized_host = _normalize_token(host_family)
    normalized_phase = _normalize_token(turn_phase)
    observation = _mapping(bundle.get("observation"))
    normalized_session = _normalize_string(session_id) or _normalize_string(observation.get("session_id"))
    ledger = delivery_ledger.delivery_snapshot(
        repo_root=root,
        host_family=normalized_host,
        session_id=normalized_session,
    )
    visibility_proven = int(ledger.get("visible_event_count") or 0) > 0
    unconfirmed_event_count = int(ledger.get("unconfirmed_event_count") or 0)
    visible = _normalize_block_string(visible_markdown_override) or _render_visible(
        bundle,
        include_proposal=include_proposal,
        include_closeout=include_closeout,
    )
    forced_visible = False
    visibility_failure = _operator_reports_visibility_failure(
        prompt=_normalize_string(observation.get("prompt_excerpt")),
        summary=_normalize_string(observation.get("assistant_summary")),
    )
    if (
        visibility_failure
        and "**Odylith Observation:**" not in visible
    ):
        visible = _visibility_failure_observation(host_family=normalized_host)
        forced_visible = True
    developer_context = _render_developer_context(
        bundle,
        include_proposal=include_proposal,
        include_closeout=include_closeout if developer_include_closeout is None else developer_include_closeout,
    )
    if forced_visible and visible and visible not in developer_context:
        developer_context = _parts(visible, developer_context)
    if visible and not developer_context:
        developer_context = visible
    channel = _normalize_token(delivery_channel)
    status = _normalize_token(delivery_status)
    if not channel or not status:
        default_channel, default_status = _default_delivery(
            visible_markdown=visible,
            host_family=normalized_host,
            turn_phase=normalized_phase,
            visibility_proven=visibility_proven,
            unconfirmed_event_count=unconfirmed_event_count,
            visibility_failure=visibility_failure,
        )
        channel = channel or default_channel
        status = status or default_status
    no_output_reason = "" if visible or developer_context else "no_visible_intervention_earned"
    proof_required = bool(visible) and not _delivery_is_visible(channel=channel, status=status)
    observation_fingerprints = {
        "bundle": _hash_payload(bundle),
        "observation": _hash_payload(observation),
        "context_packet": _hash_payload(observation.get("context_packet_summary")),
        "execution_engine": _hash_payload(observation.get("execution_engine_summary")),
        "memory": _hash_payload(observation.get("memory_summary")),
        "tribunal": _hash_payload(observation.get("tribunal_summary")),
        "visibility": _hash_payload(ledger),
    }
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return VisibleInterventionDecision(
        visible_markdown=visible,
        developer_context=developer_context,
        delivery_channel=channel,
        delivery_status=status,
        proof_required=proof_required,
        no_output_reason=no_output_reason,
        latency_ms=round(max(0.0, elapsed_ms), 3),
        source_fingerprints=observation_fingerprints,
        visibility_summary={
            "host_family": normalized_host,
            "session_id": normalized_session,
            "turn_phase": normalized_phase,
            "event_count": int(ledger.get("event_count") or 0),
            "visible_event_count": int(ledger.get("visible_event_count") or 0),
            "unconfirmed_event_count": unconfirmed_event_count,
            "visibility_proven_before_decision": visibility_proven,
            "proof_required": proof_required,
        },
        include_proposal=include_proposal,
        include_closeout=include_closeout,
    )


def append_decision_events(
    *,
    repo_root: Path | str,
    bundle: Mapping[str, Any],
    decision: VisibleInterventionDecision,
    render_surface: str,
) -> list[str]:
    if not decision.visible_markdown and not decision.developer_context:
        return []
    root = Path(repo_root).expanduser().resolve()
    events = conversation_surface.append_intervention_events(
        repo_root=Path(repo_root).expanduser().resolve(),
        bundle=bundle,
        include_proposal=decision.include_proposal,
        include_closeout=decision.include_closeout,
        delivery_channel=decision.delivery_channel,
        delivery_status=decision.delivery_status,
        render_surface=render_surface,
        delivery_latency_ms=decision.latency_ms,
    )
    if decision.visible_markdown and (
        not events
        or "This is a visibility failure, not a quiet moment" in decision.visible_markdown
    ):
        observation = _mapping(bundle.get("observation"))
        stream_state.append_intervention_event(
            repo_root=root,
            kind="intervention_card",
            summary="Visibility failure fallback requires assistant-rendered Markdown.",
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key=f"visible-fallback-{_normalize_token(observation.get('host_family')) or 'host'}",
            turn_phase=_normalize_string(observation.get("turn_phase")),
            artifacts=observation.get("changed_paths") if isinstance(observation.get("changed_paths"), list) else (),
            display_markdown=decision.visible_markdown,
            display_plain=decision.visible_markdown.replace("**", ""),
            prompt_excerpt=_normalize_string(observation.get("prompt_excerpt")),
            assistant_summary=_normalize_string(observation.get("assistant_summary")),
            moment_kind="visibility",
            semantic_signature=("visibility", "fallback"),
            delivery_channel=decision.delivery_channel,
            delivery_status=decision.delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=decision.latency_ms,
            metadata={
                "visibility_summary": dict(decision.visibility_summary or {}),
                "source_fingerprints": dict(decision.source_fingerprints or {}),
                "manual_visible": decision.delivery_status == "manual_visible",
            },
        )
        events.append("visibility_fallback")
    return events


def append_manual_visible_text(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    turn_phase: str,
    visible_markdown: str,
    prompt_excerpt: str = "",
    assistant_summary: str = "",
    render_surface: str = "",
) -> dict[str, Any]:
    visible = _normalize_block_string(visible_markdown)
    if not visible:
        return {}
    return stream_state.append_intervention_event(
        repo_root=Path(repo_root).expanduser().resolve(),
        kind="intervention_card",
        summary="Visibility fallback rendered.",
        session_id=session_id,
        host_family=host_family,
        intervention_key=f"visible-fallback-{_normalize_token(host_family) or 'host'}",
        turn_phase=turn_phase,
        display_markdown=visible,
        display_plain=visible.replace("**", ""),
        prompt_excerpt=prompt_excerpt,
        assistant_summary=assistant_summary,
        moment_kind="visibility",
        semantic_signature=("visibility", "fallback"),
        delivery_channel="manual_visible_command",
        delivery_status="manual_visible",
        render_surface=render_surface or f"{_normalize_token(host_family) or 'host'}_visible_intervention",
        metadata={"manual_visible": True},
    )


def _strip_live_boundary(value: str) -> str:
    text = _normalize_block_string(value)
    if text.startswith("---\n") and text.endswith("\n---"):
        return _normalize_block_string(text[4:-4])
    return text


def _requires_live_boundary(row: Mapping[str, Any]) -> bool:
    return _normalize_token(row.get("kind")) in LIVE_BOUNDARY_REQUIRED_KINDS


def _live_boundary_blocks(value: str) -> list[str]:
    blocks: list[str] = []
    active: list[str] = []
    in_block = False
    for raw_line in _normalize_block_string(value).splitlines():
        line = raw_line.rstrip()
        if line == "---":
            if in_block:
                active.append(line)
                blocks.append("\n".join(active).strip())
                active = []
                in_block = False
                continue
            active = [line]
            in_block = True
            continue
        if in_block:
            active.append(line)
    return blocks


def _live_boundary_contains(*, display: str, message: str) -> bool:
    display_text = _normalize_block_string(display)
    display_body = _strip_live_boundary(display_text)
    candidates = [token for token in (display_text, display_body) if token]
    if not candidates:
        return False
    return any(
        any(candidate in block for candidate in candidates)
        for block in _live_boundary_blocks(message)
    )


def _confirmed_display_present(*, row: Mapping[str, Any], display: str, message: str) -> bool:
    display_body = _strip_live_boundary(display)
    if _requires_live_boundary(row):
        return (
            _live_boundary_contains(display=display, message=message)
            or display in message
            or bool(display_body and display_body in message)
        )
    return display in message or bool(display_body and display_body in message)


def _confirmed_display_markdown(*, row: Mapping[str, Any], display: str) -> str:
    if _requires_live_boundary(row):
        return _wrap_live_text(display)
    return display


def confirm_assistant_chat_delivery(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    last_assistant_message: str,
    render_surface: str,
    limit: int = 120,
) -> list[dict[str, Any]]:
    message = _normalize_block_string(last_assistant_message)
    normalized_session = _normalize_string(session_id)
    if not message or not normalized_session:
        return []
    root = Path(repo_root).expanduser().resolve()
    rows = stream_state.load_recent_intervention_events(
        repo_root=root,
        limit=max(1, int(limit)),
        session_id=normalized_session,
    )
    normalized_host = _normalize_token(host_family)
    confirmed: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in reversed(rows):
        if normalized_host and _normalize_token(row.get("host_family")) != normalized_host:
            continue
        if _delivery_is_visible(
            channel=_normalize_string(row.get("delivery_channel")),
            status=_normalize_string(row.get("delivery_status")),
        ):
            continue
        display = _normalize_block_string(row.get("display_markdown")) or _normalize_block_string(row.get("display_plain"))
        if not display:
            continue
        if not _confirmed_display_present(row=row, display=display, message=message):
            continue
        event_key = _normalize_string(row.get("intervention_key")) or _hash_payload(_strip_live_boundary(display))
        if event_key in seen_keys:
            continue
        seen_keys.add(event_key)
        display_markdown = _confirmed_display_markdown(row=row, display=display)
        confirmed.append(
            stream_state.append_intervention_event(
                repo_root=root,
                kind=_normalize_token(row.get("kind")) or "intervention_card",
                summary=_normalize_string(row.get("summary")) or "Odylith chat-visible delivery confirmed.",
                session_id=normalized_session,
                host_family=host_family,
                intervention_key=event_key,
                turn_phase=_normalize_string(row.get("turn_phase")) or "stop_summary",
                workstreams=row.get("workstreams") if isinstance(row.get("workstreams"), list) else (),
                artifacts=row.get("artifacts") if isinstance(row.get("artifacts"), list) else (),
                components=row.get("components") if isinstance(row.get("components"), list) else (),
                action_surfaces=row.get("action_surfaces") if isinstance(row.get("action_surfaces"), list) else (),
                display_markdown=display_markdown,
                display_plain=_normalize_block_string(row.get("display_plain")),
                prompt_excerpt=_normalize_string(row.get("prompt_excerpt")),
                assistant_summary=message[:500],
                moment_kind=_normalize_string(row.get("moment_kind")),
                semantic_signature=row.get("semantic_signature") if isinstance(row.get("semantic_signature"), list) else (),
                delivery_channel="assistant_chat_transcript",
                delivery_status="assistant_chat_confirmed",
                render_surface=render_surface,
                metadata=row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {},
            )
        )
    return confirmed


__all__ = [
    "ASSISTANT_RENDER_REQUIRED_CHANNEL",
    "ASSISTANT_RENDER_REQUIRED_STATUS",
    "VISIBLE_DELIVERY_CHANNELS",
    "VISIBLE_DELIVERY_STATUSES",
    "VisibleInterventionDecision",
    "append_decision_events",
    "append_manual_visible_text",
    "build_visible_intervention_decision",
    "confirm_assistant_chat_delivery",
    "reports_visibility_failure",
]
