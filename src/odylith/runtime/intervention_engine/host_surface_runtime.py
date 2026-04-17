from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.intervention_engine import alignment_context
from odylith.runtime.intervention_engine import conversation_runtime
from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.intervention_engine import visibility_broker
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


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


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = _normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _summary_validation_signals(summary: str, *, turn_phase: str) -> list[str]:
    """Recover bounded closeout proof when Stop hooks do not carry tool paths."""

    if _normalize_string(turn_phase) != "stop_summary":
        return []
    text = _normalize_string(summary)
    lowered = text.casefold()
    if not lowered:
        return []
    markers = (
        " passed",
        "validation passed",
        "validator passed",
        "validators passed",
        "contract passed",
        "tests passed",
        "test passed",
        "pytest",
    )
    if not any(marker in lowered for marker in markers):
        return []
    return [text[:160]]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def normalized_session_id(value: Any, *, host_family: str = "") -> str:
    token = _normalize_string(value)
    if token:
        return token
    default = agent_runtime_contract.default_host_session_id()
    if default:
        return default
    family = _normalize_string(host_family).lower() or "host"
    return agent_runtime_contract.fallback_session_token(f"{family}-session")


def compose_host_conversation_bundle(
    *,
    repo_root: Path | str,
    host_family: str,
    turn_phase: str,
    session_id: str = "",
    prompt_excerpt: str = "",
    assistant_summary: str = "",
    changed_paths: Sequence[str] = (),
    workstreams: Sequence[str] = (),
    components: Sequence[str] = (),
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    resolved_root = Path(repo_root).expanduser().resolve()
    normalized_host = _normalize_string(host_family).lower()
    normalized_turn_phase = _normalize_string(turn_phase).lower()
    normalized_session = normalized_session_id(session_id, host_family=normalized_host)
    resolved_prompt = _normalize_string(prompt_excerpt) or intervention_surface_runtime.recent_session_prompt_excerpt(
        repo_root=resolved_root,
        session_id=normalized_session,
    )
    resolved_changed_paths = _normalize_string_list(changed_paths) or intervention_surface_runtime.recent_session_changed_paths(
        repo_root=resolved_root,
        session_id=normalized_session,
    )
    resolved_workstreams = _normalize_string_list(workstreams) or intervention_surface_runtime.recent_session_ids(
        repo_root=resolved_root,
        session_id=normalized_session,
        field="workstreams",
    )
    resolved_components = _normalize_string_list(components) or intervention_surface_runtime.recent_session_ids(
        repo_root=resolved_root,
        session_id=normalized_session,
        field="components",
    )
    summary = _normalize_string(assistant_summary)
    validation_signals = _summary_validation_signals(summary, turn_phase=normalized_turn_phase)
    context_signals = alignment_context.build_host_alignment_context(
        repo_root=resolved_root,
        host_family=normalized_host,
        turn_phase=normalized_turn_phase,
        session_id=normalized_session,
        prompt_excerpt=resolved_prompt,
        assistant_summary=summary,
        changed_paths=resolved_changed_paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
    )
    resolved_workstreams = _normalize_string_list(context_signals.get("workstreams")) or resolved_workstreams
    resolved_components = _normalize_string_list(context_signals.get("components")) or resolved_components
    grounded = bool(summary or resolved_prompt or resolved_changed_paths or resolved_workstreams or resolved_components)
    request = orchestrator.OrchestrationRequest(
        prompt=resolved_prompt or summary,
        candidate_paths=resolved_changed_paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
        validation_commands=validation_signals,
        needs_write=bool(resolved_changed_paths),
        evidence_cone_grounded=grounded,
        latency_sensitive=True,
        task_kind="governance_closeout" if normalized_turn_phase == "stop_summary" else "implementation",
        phase="closeout" if normalized_turn_phase == "stop_summary" else "implementation",
        session_id=normalized_session,
        context_signals=context_signals,
    )
    decision = orchestrator.OrchestrationDecision(
        mode="local_only",
        decision_id=f"{normalized_turn_phase or 'surface'}-{normalized_session or normalized_host or 'host'}",
        delegate=False,
        parallel_safety="local_only",
        task_family="governance_closeout" if normalized_turn_phase == "stop_summary" else "bounded_bugfix",
        confidence=2,
        rationale=f"{normalized_host or 'host'} {normalized_turn_phase or 'surface'} surface",
        refusal_stage="",
        manual_review_recommended=False,
        merge_owner="main_thread",
    )
    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=decision,
        adoption={
            "grounded": grounded,
            "route_ready": grounded,
            "grounded_delegate": False,
            "requires_widening": False,
            "narrowing_required": False,
        },
        repo_root=resolved_root,
        final_changed_paths=resolved_changed_paths,
        changed_path_source="supplied_changed_paths" if resolved_changed_paths else "",
        turn_phase=normalized_turn_phase,
        assistant_summary=summary,
    )
    envelope = intervention_surface_runtime.observation_envelope(
        host_family=normalized_host,
        turn_phase=normalized_turn_phase,
        session_id=normalized_session,
        prompt_excerpt=resolved_prompt,
        assistant_summary=summary,
        changed_paths=resolved_changed_paths,
        workstreams=resolved_workstreams,
        components=resolved_components,
        bugs=_normalize_string_list(context_signals.get("bugs")),
        diagrams=_normalize_string_list(context_signals.get("diagrams")),
        context_packet_summary=_mapping(context_signals.get("context_packet")),
        execution_engine_summary=_mapping(context_signals.get("execution_engine_summary")),
        memory_summary=_mapping(context_signals.get("memory_summary")),
        tribunal_summary=_mapping(context_signals.get("tribunal_summary")),
        visibility_summary=_mapping(context_signals.get("visibility_summary")),
        delivery_snapshot=_mapping(context_signals.get("delivery_snapshot")),
    )
    envelope_payload = dict(envelope)
    existing_observation = _mapping(bundle.get("observation"))
    if existing_observation:
        merged_observation = dict(existing_observation)
        for key, value in envelope_payload.items():
            if value not in ("", [], {}) and merged_observation.get(key) in (None, "", [], {}):
                merged_observation[key] = value
        bundle["observation"] = merged_observation
    else:
        bundle["observation"] = envelope_payload
    return bundle


def render_developer_context(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
    include_closeout: bool,
) -> str:
    if not isinstance(bundle, Mapping):
        return ""
    parts: list[str] = []
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=markdown,
        include_proposal=include_proposal,
    )
    closeout_text = (
        conversation_surface.render_closeout_text(bundle, markdown=markdown)
        if include_closeout
        else ""
    )
    for part in (live_text, closeout_text):
        token = _normalize_block_string(part)
        if token and token not in parts:
            parts.append(token)
    return "\n\n".join(parts).strip()


def render_visible_live_intervention(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
) -> str:
    if not isinstance(bundle, Mapping):
        return ""
    return _normalize_block_string(
        conversation_surface.render_live_text(
            bundle,
            markdown=markdown,
            include_proposal=include_proposal,
        )
    )


def visible_intervention_decision(
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
) -> visibility_broker.VisibleInterventionDecision:
    return visibility_broker.build_visible_intervention_decision(
        repo_root=repo_root,
        bundle=bundle,
        host_family=host_family,
        turn_phase=turn_phase,
        session_id=session_id,
        include_proposal=include_proposal,
        include_closeout=include_closeout,
        developer_include_closeout=developer_include_closeout,
        delivery_channel=delivery_channel,
        delivery_status=delivery_status,
        visible_markdown_override=visible_markdown_override,
    )


def append_visible_intervention_events(
    *,
    repo_root: Path | str,
    bundle: Mapping[str, Any],
    decision: visibility_broker.VisibleInterventionDecision,
    render_surface: str,
) -> list[str]:
    return visibility_broker.append_decision_events(
        repo_root=repo_root,
        bundle=bundle,
        decision=decision,
        render_surface=render_surface,
    )


def confirm_assistant_chat_delivery(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    last_assistant_message: str,
    render_surface: str,
) -> list[dict[str, Any]]:
    return visibility_broker.confirm_assistant_chat_delivery(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message=last_assistant_message,
        render_surface=render_surface,
    )


def compose_checkpoint_system_message(
    *,
    live_intervention: str = "",
    governance_status: str = "",
) -> str:
    live = _canonical_visible_delivery_text(live_intervention)
    governance = _normalize_block_string(governance_status)
    if live:
        if governance and any(token in governance.lower() for token in ("failed", "skipped")):
            return f"{live}\n\n{governance}".strip()
        return live
    return governance


_VISIBLE_DELIVERY_BEGIN = "<odylith-visible-markdown>"
_VISIBLE_DELIVERY_END = "</odylith-visible-markdown>"
_LIVE_DELIVERY_LABELS: tuple[str, ...] = (
    "**Odylith Observation:**",
    "Odylith Observation:",
    "Odylith Proposal:",
    "**Odylith Insight:**",
    "Odylith Insight:",
    "**Odylith History:**",
    "Odylith History:",
    "**Odylith Risks:**",
    "Odylith Risks:",
)
_ASSIST_LABELS: tuple[str, ...] = (
    "**Odylith Assist:**",
    "Odylith Assist:",
)


def _strip_visible_delivery_boundary(value: str) -> str:
    text = _normalize_block_string(value)
    if text.startswith("---\n") and text.endswith("\n---"):
        return _normalize_block_string(text[4:-4])
    return text


def _split_assist_suffix(value: str) -> tuple[str, str]:
    text = _normalize_block_string(value)
    positions = [
        index
        for label in _ASSIST_LABELS
        if (index := text.find(label)) >= 0
    ]
    if not positions:
        return text, ""
    first = min(positions)
    return _normalize_block_string(text[:first]), _normalize_block_string(text[first:])


def _canonical_live_delivery_text(value: str) -> str:
    text = _normalize_block_string(value)
    if not text:
        return ""
    body = _strip_visible_delivery_boundary(text)
    if text.startswith("---\n") and text.endswith("\n---"):
        return f"---\n\n{body}\n\n---"
    if any(label in text for label in _LIVE_DELIVERY_LABELS):
        return f"---\n\n{text}\n\n---"
    return text


def _canonical_visible_delivery_text(value: str) -> str:
    text = _normalize_block_string(value)
    if not text:
        return ""
    live_part, assist_suffix = _split_assist_suffix(text)
    live = _canonical_live_delivery_text(live_part)
    if live and assist_suffix:
        return f"{live}\n\n{assist_suffix}"
    return live or assist_suffix


def assistant_visible_fallback_context(visible_text: str) -> str:
    """Return model-context instructions that make hook output fail-visible.

    Host hook `systemMessage` support is useful but not a reliable chat-render
    guarantee across Codex Desktop, Codex CLI, and Claude Code builds. This
    context keeps the structured hook payload intact while telling the next
    assistant turn exactly what to speak if the host kept the hook message
    hidden.
    """

    visible = _canonical_visible_delivery_text(visible_text)
    if not visible:
        return ""
    return "\n".join(
        [
            "Odylith visible delivery fallback:",
            "Visible proof is missing or host display is unproven. Render this Markdown once if it is not already visible. Do not mention hooks or use a code fence.",
            "",
            _VISIBLE_DELIVERY_BEGIN,
            visible,
            _VISIBLE_DELIVERY_END,
        ]
    ).strip()


def visible_delivery_already_present(*, last_assistant_message: str, visible_text: str) -> bool:
    last = _normalize_block_string(last_assistant_message)
    visible = _canonical_visible_delivery_text(visible_text)
    if not last or not visible:
        return False
    if visible in last:
        return True
    if visible.startswith("---\n") and visible.endswith("\n---"):
        return False
    visible_body = _strip_visible_delivery_boundary(visible)
    return bool(visible_body and visible_body in last)


def stop_visible_delivery_reason(visible_text: str) -> str:
    visible = _canonical_visible_delivery_text(visible_text)
    if not visible:
        return ""
    return "\n\n".join(
        [
            (
                "Before ending, render the Odylith closeout below in the next visible "
                "assistant message if it is not already visible. Keep it as normal "
                "Markdown, do not wrap it in a code fence, and do not mention hook internals."
            ),
            visible,
        ]
    ).strip()


def _developer_context_with_visible_fallback(*, developer_context: str, visible_text: str) -> str:
    context = _normalize_block_string(developer_context)
    fallback = assistant_visible_fallback_context(visible_text)
    if not fallback:
        return context
    visible = _canonical_visible_delivery_text(visible_text)
    if visible and _canonical_visible_delivery_text(context) == visible:
        context = ""
    if visible and visible in context:
        context = _normalize_block_string(context.replace(visible, "", 1))
    if not context:
        return fallback
    return f"{fallback}\n\nOdylith developer continuity:\n{context}".strip()


def codex_post_tool_payload(
    *,
    developer_context: str = "",
    system_message: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    message = _canonical_visible_delivery_text(system_message)
    context = _developer_context_with_visible_fallback(
        developer_context=developer_context,
        visible_text=message,
    )
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "PostToolUse",
            "additionalContext": context,
        }
    if message:
        payload["systemMessage"] = message
    return payload


def codex_prompt_payload(
    *,
    additional_context: str = "",
    system_message: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    message = _canonical_visible_delivery_text(system_message)
    context = _developer_context_with_visible_fallback(
        developer_context=additional_context,
        visible_text=message,
    )
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    if message:
        payload["systemMessage"] = message
    return payload


def stop_payload(*, system_message: str = "", block_for_visible_delivery: bool = False) -> dict[str, Any]:
    message = _canonical_visible_delivery_text(system_message)
    if not message:
        return {}
    payload: dict[str, Any] = {"systemMessage": message}
    if block_for_visible_delivery:
        reason = stop_visible_delivery_reason(message)
        if reason:
            payload["decision"] = "block"
            payload["reason"] = reason
    return payload


def claude_post_tool_payload(
    *,
    developer_context: str = "",
    system_message: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    message = _canonical_visible_delivery_text(system_message)
    context = _developer_context_with_visible_fallback(
        developer_context=developer_context,
        visible_text=message,
    )
    if context:
        payload["additionalContext"] = context
    if message:
        payload["systemMessage"] = message
    return payload


def claude_prompt_payload(
    *,
    additional_context: str = "",
    system_message: str = "",
) -> dict[str, Any]:
    """Return Claude UserPromptSubmit JSON for discreet model context only.

    Claude Code renders plain stdout in the transcript for UserPromptSubmit.
    The structured `additionalContext` lane is intentionally discreet, so live
    teaser text must be printed by the prompt hook itself instead of routed
    through this JSON helper.
    """

    payload: dict[str, Any] = {}
    context = _developer_context_with_visible_fallback(
        developer_context=additional_context,
        visible_text=system_message,
    )
    if context:
        payload["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    return payload


def chat_visible_text(
    payload: Mapping[str, Any],
    *,
    host_family: str,
    turn_phase: str,
    plain_stdout: str = "",
) -> str:
    """Return the text Odylith expects the user to see.

    Hosts may keep hook `systemMessage` hidden. In that case the matching
    assistant-visible fallback context tells the next assistant turn to render
    this same text. Claude `UserPromptSubmit` can also use plain stdout from
    the dedicated teaser hook when the host exposes it.
    """

    normalized_host = _normalize_string(host_family).lower()
    normalized_phase = _normalize_string(turn_phase).lower()
    if normalized_host == "claude" and normalized_phase in {"prompt_submit", "userpromptsubmit"}:
        return _normalize_block_string(plain_stdout)
    return _normalize_block_string(_mapping(payload).get("systemMessage"))
