"""Shared helpers for host-specific prompt and stop intervention renderers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import prompt_signal_runtime


def __getattr__(name: str) -> Any:
    """Load renderer-heavy intervention modules only when callers touch them."""

    if name in {
        "alignment_context",
        "conversation_surface",
        "host_surface_runtime",
        "intervention_surface_runtime",
        "visibility_contract",
        "visibility_replay",
    }:
        from importlib import import_module

        module_name = "surface_runtime" if name == "intervention_surface_runtime" else name
        return import_module(f"odylith.runtime.intervention_engine.{module_name}")
    raise AttributeError(name)


_LIVE_BLOCK_LABELS: tuple[str, ...] = (
    "Odylith Observation:",
    "Odylith Proposal:",
    "Odylith Insight:",
    "Odylith History:",
    "Odylith Risks:",
)
_PROMPT_FIRST_FALLBACK = (
    "Odylith prompt-start substrate: alignment unavailable; keep the prompt Odylith-first, "
    "but do not claim full engine coverage without a fresh status check."
)
_PROMPT_FIRST_QUIET_SUFFIX = (
    "No live Odylith note earned; keep chat quiet unless a pending Odylith block needs visible recovery."
)


def _alignment_mapping(alignment: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = alignment.get(key)
    return value if isinstance(value, Mapping) else {}


def _alignment_list(alignment: Mapping[str, Any], key: str) -> list[Any]:
    value = alignment.get(key)
    return value if isinstance(value, list) else []


def _compact_string(value: Any, *, fallback: str = "") -> str:
    return prompt_signal_runtime.normalize_string(value) or fallback


def _format_substrate_alignment(
    alignment: Mapping[str, Any],
    *,
    prefix: str,
    suffix: str = "",
) -> str:
    packet = _alignment_mapping(alignment, "context_packet")
    runtime_summary = _alignment_mapping(packet, "runtime_surface_summary")
    execution = _alignment_mapping(alignment, "execution_engine_summary")
    visibility = _alignment_mapping(alignment, "visibility_summary")
    tribunal = _alignment_mapping(alignment, "tribunal_summary")
    proof = _alignment_mapping(alignment, "alignment_proof")

    packet_kind = _compact_string(packet.get("packet_kind"), fallback="unknown")
    packet_state = _compact_string(packet.get("packet_state"), fallback="unknown")
    memory_backend = _compact_string(
        runtime_summary.get("memory_backend_label"),
        fallback=_compact_string(runtime_summary.get("memory_status"), fallback="unavailable"),
    )
    memory_state = _compact_string(runtime_summary.get("memory_standardization_state"))
    memory = f"{memory_backend} ({memory_state})" if memory_state else memory_backend
    execution_mode = _compact_string(execution.get("execution_engine_mode"), fallback="unavailable")
    execution_next = _compact_string(execution.get("execution_engine_next_move"), fallback="n/a")
    execution_outcome = _compact_string(execution.get("execution_engine_outcome"))
    execution_text = f"{execution_mode}/{execution_next}"
    if execution_outcome:
        execution_text = f"{execution_text} ({execution_outcome})"
    delivery = _compact_string(visibility.get("chat_visible_proof"), fallback="unproven_this_session")
    proof_status = _compact_string(proof.get("status"), fallback="unknown")
    missing_lanes = [
        _compact_string(value)
        for value in _alignment_list(proof, "missing_required_lanes")
        if _compact_string(value)
    ]
    covered_lanes = [
        _compact_string(value)
        for value in _alignment_list(proof, "covered_lanes")[:8]
        if _compact_string(value)
    ]
    tribunal_state = "active" if tribunal else "quiet"
    parts = [
        f"context={packet_kind}/{packet_state}",
        f"memory={memory}",
        f"execution={execution_text}",
        f"tribunal={tribunal_state}",
        f"delivery={delivery}",
        f"proof={proof_status}",
    ]
    if covered_lanes:
        parts.append("lanes=" + ",".join(covered_lanes))
    if missing_lanes:
        parts.append("missing=" + ",".join(missing_lanes))
    rendered = f"{prefix}: " + "; ".join(parts) + "."
    suffix_text = _compact_string(suffix)
    return f"{rendered} {suffix_text}".strip() if suffix_text else rendered


def _host_alignment_context(
    *,
    repo_root: Path | str,
    host_family: str,
    turn_phase: str,
    prompt_excerpt: str = "",
    session_id: str = "",
) -> Mapping[str, Any]:
    from odylith.runtime.intervention_engine import alignment_context

    try:
        return alignment_context.build_host_alignment_context(
            repo_root=repo_root,
            host_family=host_family,
            turn_phase=turn_phase,
            session_id=session_id,
            prompt_excerpt=prompt_excerpt,
        )
    except Exception:
        return {}


def join_sections(*values: Any) -> str:
    """Join unique normalized chat sections with one blank line between them."""
    from odylith.runtime.intervention_engine import visibility_contract

    return visibility_contract.join_blocks(*values)


def contains_assist(value: object) -> bool:
    """Return whether a rendered chat block already carries an Odylith Assist line."""

    return "odylith assist:" in str(value or "").casefold()


def suppress_prompt_live_narration(*, prompt: Any = "", assistant_summary: Any = "") -> bool:
    """Return whether a first-match stdout route should stay narration-free."""
    return prompt_signal_runtime.is_passthrough_prompt(prompt) or prompt_signal_runtime.is_cli_help_output(
        assistant_summary
    )


def session_prefers_assist(
    *,
    repo_root: Path | str = ".",
    session_id: str = "",
    host_family: str = "",
) -> bool:
    """Return whether this session explicitly asked for more Assist coverage."""

    token = prompt_signal_runtime.normalize_string(session_id)
    if not token:
        if not host_family:
            return False
        from odylith.runtime.intervention_engine import host_surface_runtime

        token = host_surface_runtime.normalized_session_id("", host_family=host_family)
    from odylith.runtime.intervention_engine import stream_state

    return any(
        prompt_signal_runtime.assist_cadence_feedback_requested(prompt=row.get("prompt_excerpt", ""))
        for row in stream_state.load_recent_intervention_events(
            repo_root=Path(repo_root).expanduser().resolve(), session_id=token, limit=40
        )
    )


def prompt_needs_live_bundle(
    *, prompt: Any, repo_root: Path | str = ".", session_id: str = "", host_family: str = "",
    bundle_override: Mapping[str, Any] | None = None, intervention_bundle_override: Mapping[str, Any] | None = None,
) -> bool:
    """Return whether prompt-submit should pay for the live intervention bundle."""
    if suppress_prompt_live_narration(prompt=prompt):
        return False
    if prompt_signal_runtime.is_greenfield_governance_prompt(prompt):
        return False
    if isinstance(bundle_override, Mapping) or isinstance(intervention_bundle_override, Mapping):
        return True
    if prompt_signal_runtime.intervention_experience_feedback_requested(prompt=prompt, assistant_summary=""):
        return True
    if session_prefers_assist(
        repo_root=repo_root,
        session_id=session_id,
        host_family=host_family,
    ) and prompt_signal_runtime.has_assist_cadence_signal(prompt):
        return True
    return prompt_signal_runtime.has_prompt_intervention_signal(prompt)


def prompt_first_receipt_eligible(prompt: Any) -> bool:
    """Return whether a quiet prompt should still get a substrate receipt.

    Generic low-signal prompts do not need a hidden receipt on every turn. Keep
    the receipt for Odylith-directed prompts so the user can ask about Odylith
    health without paying for the full intervention bundle.
    """

    if suppress_prompt_live_narration(prompt=prompt):
        return False
    if prompt_signal_runtime.is_greenfield_governance_prompt(prompt):
        return False
    token = prompt_signal_runtime.normalized_passthrough_prompt(prompt)
    return bool(token and "odylith" in token)


def prompt_first_receipt_context(
    *,
    prompt: Any,
    repo_root: Path | str = ".",
    host_family: str = "",
    session_id: str = "",
) -> str:
    """Return a low-latency prompt-start substrate proof for quiet prompts."""

    if suppress_prompt_live_narration(prompt=prompt):
        return ""
    normalized_prompt = prompt_signal_runtime.normalize_string(prompt)
    if not normalized_prompt:
        return ""
    alignment = _host_alignment_context(
        repo_root=repo_root,
        host_family=host_family or "unknown",
        turn_phase="prompt_submit",
        prompt_excerpt=normalized_prompt,
        session_id=session_id,
    )
    if not alignment:
        return f"{_PROMPT_FIRST_FALLBACK} {_PROMPT_FIRST_QUIET_SUFFIX}"
    return _format_substrate_alignment(
        alignment,
        prefix="Odylith prompt-start substrate",
        suffix=_PROMPT_FIRST_QUIET_SUFFIX,
    )


def session_start_substrate_context(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str = "",
) -> str:
    """Return the compact SessionStart substrate proof without shelling out."""

    alignment = _host_alignment_context(
        repo_root=repo_root,
        host_family=host_family,
        turn_phase="session_start",
        prompt_excerpt="session start",
        session_id=session_id,
    )
    if not alignment:
        return "Odylith startup substrate: alignment unavailable; use the next anchored prompt for full grounding."
    return _format_substrate_alignment(
        alignment,
        prefix="Odylith startup substrate",
        suffix="Full grounding stays automatic on anchored prompts; no manual startup command is required.",
    )


def preferred_live_replay_markdown(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    include_assist: bool = False,
) -> str:
    """Return the current pending live replay bundle for prompt and checkpoint recovery."""
    from odylith.runtime.intervention_engine import visibility_replay

    return visibility_replay.preferred_replayable_chat_markdown(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        include_assist=include_assist,
        include_teaser=False,
    )


def confirm_last_assistant_message(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    payload: Mapping[str, Any] | None,
    render_surface: str,
) -> list[dict[str, Any]]:
    """Promote the previous assistant turn to chat-confirmed when the payload carries it."""
    if not isinstance(payload, Mapping):
        return []
    message = str(payload.get("last_assistant_message", "")).strip()
    if not message:
        return []
    from odylith.runtime.intervention_engine import host_surface_runtime

    return host_surface_runtime.confirm_assistant_chat_delivery(
        repo_root=repo_root,
        host_family=host_family,
        session_id=session_id,
        last_assistant_message=message,
        render_surface=render_surface,
    )


def looks_like_teaser_live_text(value: str) -> bool:
    """Return whether the live text is still only a teaser beat."""
    from odylith.runtime.intervention_engine import visibility_contract

    text = str(value or "").strip()
    if not text:
        return False
    body = visibility_contract.strip_live_boundary(text)
    if body.startswith("Odylith Observation:") and "**Odylith Observation:**" not in body:
        return True
    if any(label in body for label in _LIVE_BLOCK_LABELS):
        return False
    return "Odylith" in body


def merge_replay_with_closeout(
    *,
    replay: str,
    closeout_text: str,
    supplemental_inside_live_with_assist: bool = False,
) -> str:
    """Combine replayed live blocks with a closeout without duplicating assists."""
    from odylith.runtime.intervention_engine import visibility_contract

    visible_replay = str(replay or "").strip()
    closeout = str(closeout_text or "").strip()
    if not visible_replay:
        return visibility_contract.compose_visible_markdown(closeout)
    if not closeout or "Odylith Assist:" in visible_replay or "**Odylith Assist:**" in visible_replay:
        return visibility_contract.compose_visible_markdown(visible_replay)
    return visibility_contract.compose_visible_markdown(
        visible_replay,
        closeout,
        supplemental_inside_live_with_assist=supplemental_inside_live_with_assist,
    )


def prompt_visible_assist_text(bundle: Mapping[str, Any] | object) -> tuple[str, str]:
    """Return the signal-specific prompt-submit Assist text."""
    from odylith.runtime.intervention_engine import conversation_surface

    existing_markdown = conversation_surface.render_closeout_text(bundle, markdown=True)
    existing_plain = conversation_surface.render_closeout_text(bundle, markdown=False)
    if not existing_markdown and not prompt_assist_requested(bundle):
        return "", ""
    if not prompt_assist_requested(bundle):
        return existing_markdown, existing_plain
    observation = _alignment_mapping(bundle, "observation") if isinstance(bundle, Mapping) else {}
    summary = prompt_signal_runtime.prompt_assist_summary(observation.get("prompt_excerpt"))
    return (
        f"**Odylith Assist:** {summary}",
        f"Odylith Assist: {summary}",
    )


def prompt_visibility_feedback_requested(bundle: Mapping[str, Any] | object) -> bool:
    """Return whether the prompt explicitly asks for a better Odylith moment."""

    observation = _alignment_mapping(bundle, "observation") if isinstance(bundle, Mapping) else {}
    return prompt_signal_runtime.intervention_experience_feedback_requested(
        prompt=observation.get("prompt_excerpt"),
        assistant_summary=observation.get("assistant_summary", ""),
    )


def prompt_assist_requested(bundle: Mapping[str, Any] | object) -> bool:
    """Return whether a prompt warrants a visible, decision-oriented Assist."""

    observation = _alignment_mapping(bundle, "observation") if isinstance(bundle, Mapping) else {}
    prompt = observation.get("prompt_excerpt")
    return bool(observation.get("assist_cadence_preference")) or prompt_visibility_feedback_requested(
        bundle
    ) or prompt_signal_runtime.has_prompt_intervention_signal(prompt)


def with_assist_cadence_preference(bundle: Mapping[str, Any] | object) -> dict[str, Any]:
    """Mark a rendered prompt bundle for the session's explicit Assist preference."""

    updated = dict(bundle) if isinstance(bundle, Mapping) else {}
    observation = dict(_alignment_mapping(updated, "observation"))
    observation["assist_cadence_preference"] = True
    updated["observation"] = observation
    return updated


def ensure_prompt_visible_assist_bundle(bundle: Mapping[str, Any] | object) -> dict[str, Any]:
    """Add a prompt-submit Assist for explicit feedback or a concrete governed request.

    Prompt hooks may be the only visible Odylith lane in a host session. Keep
    low-signal conversational turns quiet, but expose the decision or proof
    boundary early when a request enters the intervention hot path.
    """
    from odylith.runtime.intervention_engine import conversation_surface

    updated = dict(bundle) if isinstance(bundle, Mapping) else {}
    if not prompt_assist_requested(updated):
        return updated
    markdown_text, plain_text = prompt_visible_assist_text(updated)
    if conversation_surface.render_closeout_text(updated, markdown=True) == markdown_text:
        return updated
    updated["closeout_bundle"] = {
        "eligible": True,
        "style": "prompt_visible_feedback" if prompt_visibility_feedback_requested(updated) else "prompt_signal",
        "label": "Odylith Assist:",
        "preferred_markdown_label": "**Odylith Assist:**",
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "proof": markdown_text.removeprefix("**Odylith Assist:** ").rstrip("."),
    }
    return updated


def compose_prompt_visible_markdown(*, visible_markdown: str, bundle: Mapping[str, Any] | object) -> str:
    """Append prompt-submit Assist to visible Markdown, or return Assist alone."""
    from odylith.runtime.intervention_engine import conversation_surface
    from odylith.runtime.intervention_engine import visibility_contract

    visible = visibility_contract.normalize_block_string(visible_markdown)
    if contains_assist(visible):
        return visibility_contract.compose_visible_markdown(visible)
    assisted_bundle = ensure_prompt_visible_assist_bundle(bundle)
    assist_markdown = conversation_surface.render_closeout_text(assisted_bundle, markdown=True)
    if not assist_markdown:
        return visibility_contract.compose_visible_markdown(visible)
    return visibility_contract.compose_visible_markdown(visible, assist_markdown)


def build_prompt_conversation_bundle(
    *,
    repo_root: Path | str,
    host_family: str,
    prompt: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the prompt-submit bundle shared by Codex and Claude hooks."""
    from odylith.runtime.intervention_engine import alignment_context
    from odylith.runtime.intervention_engine import conversation_surface
    from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
    from odylith.runtime.intervention_engine import visibility_contract

    if suppress_prompt_live_narration(prompt=prompt):
        return {}
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    if isinstance(intervention_bundle_override, Mapping):
        return {"intervention_bundle": dict(intervention_bundle_override)}
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    alignment = alignment_context.build_host_alignment_context(
        repo_root=root,
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        prompt_excerpt=prompt,
    )
    observation = intervention_surface_runtime.observation_envelope(
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        prompt_excerpt=prompt,
        workstreams=_alignment_list(alignment, "workstreams"),
        components=_alignment_list(alignment, "components"),
        bugs=_alignment_list(alignment, "bugs"),
        diagrams=_alignment_list(alignment, "diagrams"),
        context_packet_summary=_alignment_mapping(alignment, "context_packet"),
        execution_engine_summary=_alignment_mapping(alignment, "execution_engine_summary"),
        memory_summary=_alignment_mapping(alignment, "memory_summary"),
        tribunal_summary=_alignment_mapping(alignment, "tribunal_summary"),
        visibility_summary=_alignment_mapping(alignment, "visibility_summary"),
        delivery_snapshot=_alignment_mapping(alignment, "delivery_snapshot"),
        alignment_proof=_alignment_mapping(alignment, "alignment_proof"),
    )
    bundle = conversation_surface.build_conversation_bundle(
        repo_root=root,
        observation=observation,
    )
    if session_prefers_assist(
        repo_root=root,
        session_id=session_id,
        host_family=normalized_host,
    ) and prompt_signal_runtime.has_assist_cadence_signal(prompt):
        bundle = with_assist_cadence_preference(bundle)
    return bundle


def render_prompt_system_message(
    *,
    repo_root: Path | str,
    host_family: str,
    prompt: str,
    session_id: str = "",
    conversation_bundle_override: Mapping[str, Any] | None = None,
    intervention_bundle_override: Mapping[str, Any] | None = None,
) -> str:
    """Render the host-visible prompt-submit fallback/system-message text."""
    from odylith.runtime.intervention_engine import conversation_surface
    from odylith.runtime.intervention_engine import host_surface_runtime
    from odylith.runtime.intervention_engine import visibility_contract

    if suppress_prompt_live_narration(prompt=prompt):
        return ""
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    bundle = ensure_prompt_visible_assist_bundle(
        build_prompt_conversation_bundle(
            repo_root=root,
            host_family=normalized_host,
            prompt=prompt,
            session_id=session_id,
            bundle_override=conversation_bundle_override,
            intervention_bundle_override=intervention_bundle_override,
        )
    )
    include_closeout = True
    decision = host_surface_runtime.visible_intervention_decision(
        repo_root=root,
        bundle=bundle,
        host_family=normalized_host,
        turn_phase="prompt_submit",
        session_id=session_id,
        include_proposal=False,
        include_closeout=include_closeout,
        developer_include_closeout=include_closeout,
    )
    replay = preferred_live_replay_markdown(
        repo_root=root,
        host_family=normalized_host,
        session_id=session_id,
        include_assist=True,
    )
    if replay:
        closeout_text = conversation_surface.render_closeout_text(bundle, markdown=True)
        return merge_replay_with_closeout(
            replay=replay,
            closeout_text=closeout_text,
            supplemental_inside_live_with_assist=True,
        )
    visible = decision.visible_markdown or conversation_surface.render_live_text(
        bundle,
        markdown=False,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
    return compose_prompt_visible_markdown(visible_markdown=visible, bundle=bundle)


def render_prompt_bundle_text(
    *,
    bundle: Mapping[str, Any] | dict[str, Any],
    anchor_summary: str = "",
    markdown: bool = False,
) -> str:
    """Render prompt-context text from an anchor summary plus live conversation state."""
    from odylith.runtime.intervention_engine import conversation_surface
    from odylith.runtime.intervention_engine import visibility_contract

    observation = bundle.get("observation") if isinstance(bundle, Mapping) else {}
    if isinstance(observation, Mapping) and suppress_prompt_live_narration(
        prompt=observation.get("prompt_excerpt")
    ):
        return visibility_contract.normalize_string(anchor_summary)
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=markdown,
        include_proposal=False,
        prefer_ambient_over_teaser=True,
    )
    return join_sections(anchor_summary, live_text)


def build_stop_conversation_bundle(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    assistant_summary: str,
    prompt_excerpt: str,
    changed_paths: list[str],
    workstreams: list[str],
    components: list[str],
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stop-summary bundle shared by Codex and Claude hooks."""
    from odylith.runtime.intervention_engine import host_surface_runtime
    from odylith.runtime.intervention_engine import visibility_contract

    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    if suppress_prompt_live_narration(prompt=prompt_excerpt, assistant_summary=assistant_summary) and not any(
        (changed_paths, workstreams, components)
    ):
        return {}
    if not any((assistant_summary, prompt_excerpt, changed_paths, workstreams, components)):
        return {}
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=root,
        host_family=normalized_host,
        turn_phase="stop_summary",
        session_id=session_id,
        prompt_excerpt=prompt_excerpt,
        assistant_summary=assistant_summary,
        changed_paths=changed_paths,
        workstreams=workstreams,
        components=components,
    )


def render_stop_bundle_text(
    *,
    repo_root: Path | str,
    host_family: str,
    session_id: str,
    bundle: Mapping[str, Any] | dict[str, Any],
) -> str:
    """Render stop-summary text from a normalized host conversation bundle."""
    from odylith.runtime.intervention_engine import conversation_surface
    from odylith.runtime.intervention_engine import visibility_contract
    from odylith.runtime.intervention_engine import visibility_replay

    if not bundle:
        return ""
    observation = bundle.get("observation") if isinstance(bundle, Mapping) else {}
    if isinstance(observation, Mapping) and suppress_prompt_live_narration(
        prompt=observation.get("prompt_excerpt"),
        assistant_summary=observation.get("assistant_summary"),
    ):
        return ""
    root = Path(repo_root).expanduser().resolve()
    normalized_host = visibility_contract.normalize_token(host_family)
    live_text = conversation_surface.render_live_text(
        bundle,
        markdown=True,
        include_proposal=False,
    )
    recovered_live_text = visibility_replay.replayable_chat_markdown(
        repo_root=root,
        host_family=normalized_host,
        session_id=session_id,
        max_live_blocks=4,
        ambient_cap=3,
        include_assist=True,
        include_teaser=True,
    )
    if recovered_live_text and (
        not live_text or looks_like_teaser_live_text(live_text)
    ):
        live_text = recovered_live_text
    closeout_text = conversation_surface.render_closeout_text(
        bundle,
        markdown=True,
    )
    return merge_replay_with_closeout(replay=live_text, closeout_text=closeout_text)
