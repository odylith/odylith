"""Conversation Surface helpers for the Odylith intervention engine layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import conversation_surface_signal_selection as signal_selection
from odylith.runtime.intervention_engine import engine
from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine import value_engine
from odylith.runtime.intervention_engine import value_engine_event_metadata
from odylith.runtime.intervention_engine import visibility_contract
from odylith.runtime.intervention_engine.contract import ObservationEnvelope


_normalize_string = visibility_contract.normalize_string
_normalize_block_string = visibility_contract.normalize_block_string
_normalize_token = visibility_contract.normalize_token
_mapping = visibility_contract.mapping_copy


def build_conversation_bundle(
    *,
    repo_root: Path,
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_observation = ObservationEnvelope.from_mapping(observation)
    normalized_payload = normalized_observation.as_dict()
    intervention_bundle = engine.build_intervention_bundle(
        repo_root=repo_root,
        observation=normalized_payload,
    )
    ambient = {
        "insight": signal_selection.empty_signal("insight"),
        "history": signal_selection.empty_signal("history"),
        "risks": signal_selection.empty_signal("risks"),
        "selected_signal": "",
        "selected_signals": [],
        "selected_signal_ids": [],
        "ambient_signal_payloads": {},
        "render_policy": {
            "owner": "governance_intervention_engine",
            "live_mid_turn_only": True,
            "prompt_submit_teaser_only": True,
            "explicit_labels_rare": True,
            "one_signal_at_a_time": False,
            "max_signals_per_turn": signal_selection.AMBIENT_MAX_SELECTED_SIGNALS,
            "min_signal_strength": signal_selection.AMBIENT_SIGNAL_STRENGTH_FLOOR,
            "dedupe_by_signal_kind": False,
            "same_label_distinct_signals_allowed": True,
            "dedupe_by_semantic_signature": True,
            "value_engine": value_engine.VALUE_ENGINE_VERSION,
            "runtime_posture": value_engine.RUNTIME_POSTURE,
        },
    }
    ambient_payloads = signal_selection.ambient_payload_candidates(
        observation=normalized_observation,
        intervention=intervention_bundle,
    )
    value_decision = signal_selection.value_selection_decision(
        intervention=intervention_bundle,
        ambient_payloads=ambient_payloads,
    )
    selected_candidate_by_id = {
        _normalize_string(row.get("candidate_id")): dict(row)
        for row in value_decision.selected_candidates
    }
    suppressed_candidate_by_id = {
        _normalize_string(row.get("candidate_id")): dict(row)
        for row in value_decision.suppressed_candidates
    }
    selected_payloads: list[dict[str, Any]] = []
    ambient_payload_rows: dict[str, dict[str, Any]] = {}
    for payload in ambient_payloads:
        candidate_id = signal_selection.ambient_candidate_id(payload)
        signal_name = _normalize_token(payload.get("signal_name")) or "insight"
        row = dict(payload)
        row["candidate_id"] = candidate_id
        if candidate_id in selected_candidate_by_id:
            row.update(
                signal_selection.value_payload_fields(
                    selected_candidate_by_id[candidate_id],
                    selected=True,
                )
            )
            selected_payloads.append(row)
            ambient_payload_rows[candidate_id] = row
            continue
        if candidate_id in suppressed_candidate_by_id:
            row.update(
                {
                    "eligible": False,
                    "render_hint": "silent",
                    "suppressed_reason": _normalize_string(
                        suppressed_candidate_by_id[candidate_id].get("suppressed_reason")
                    ),
                }
            )
            row.update(
                signal_selection.value_payload_fields(
                    suppressed_candidate_by_id[candidate_id],
                    selected=False,
                )
            )
            ambient_payload_rows[candidate_id] = row
            current_reason = _normalize_string(_mapping(ambient.get(signal_name)).get("suppressed_reason"))
            if current_reason in {"", "not_selected"}:
                ambient[signal_name] = row
    ambient["ambient_signal_payloads"] = ambient_payload_rows
    if selected_payloads:
        selected_names: list[str] = []
        selected_ids: list[str] = []
        selected_primary_labels: set[str] = set()
        for selected_payload in selected_payloads:
            signal_name = _normalize_token(selected_payload.get("signal_name")) or "insight"
            candidate_id = _normalize_string(selected_payload.get("candidate_id"))
            if signal_name not in selected_primary_labels:
                ambient[signal_name] = selected_payload
                selected_primary_labels.add(signal_name)
            selected_names.append(signal_name)
            selected_ids.append(candidate_id)
        ambient["selected_signal"] = selected_names[0]
        ambient["selected_signals"] = selected_names
        ambient["selected_signal_ids"] = selected_ids
    ambient["visible_signal_decision"] = value_decision.as_dict()
    return {
        "observation": normalized_payload,
        "ambient_signals": ambient,
        "visible_signal_decision": value_decision.as_dict(),
        "intervention_bundle": intervention_bundle,
        "pending_state": _mapping(intervention_bundle.get("pending_state")),
        "render_policy": {
            "owner": "governance_intervention_engine",
            "mid_turn_surface": True,
            "closeout_owned_by_chatter": True,
            "cross_host_shared": True,
        },
    }


def _visible_signal_decision(bundle: Mapping[str, Any]) -> value_engine.VisibleSignalSelectionDecision:
    ambient = _mapping(bundle.get("live_ambient_signals")) or _mapping(bundle.get("ambient_signals"))
    payload = _mapping(bundle.get("visible_signal_decision")) or _mapping(ambient.get("visible_signal_decision"))
    return value_engine.VisibleSignalSelectionDecision.from_mapping(payload)


def _selected_ambient_payloads(bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    ambient = _mapping(bundle.get("live_ambient_signals")) or _mapping(bundle.get("ambient_signals"))
    selected_ids = ambient.get("selected_signal_ids")
    payloads_by_id = _mapping(ambient.get("ambient_signal_payloads"))
    selected_rows = selected_ids if isinstance(selected_ids, list) and payloads_by_id else ambient.get("selected_signals")
    use_candidate_ids = isinstance(selected_ids, list) and payloads_by_id
    if not isinstance(selected_rows, list):
        selected_rows = [_normalize_token(ambient.get("selected_signal"))]
    payloads: list[dict[str, Any]] = []
    seen: set[str] = set()
    for selected in selected_rows:
        if len(payloads) >= signal_selection.AMBIENT_MAX_SELECTED_SIGNALS:
            break
        if use_candidate_ids:
            candidate_id = _normalize_string(selected)
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            payload = _mapping(payloads_by_id.get(candidate_id))
        else:
            signal_name = _normalize_token(selected)
            if not signal_name or signal_name in seen:
                continue
            seen.add(signal_name)
            payload = _mapping(ambient.get(signal_name))
        if not payload.get("eligible"):
            continue
        if _normalize_token(payload.get("render_hint")) != "explicit_label":
            continue
        if signal_selection.duplicates_existing_payload(payload, payloads):
            continue
        payloads.append(payload)
    return payloads


def _ranked_intervention_payload(
    bundle: Mapping[str, Any],
    *,
    include_proposal: bool,
) -> dict[str, Any]:
    intervention = signal_selection.intervention_payload(bundle)
    decision = _visible_signal_decision(bundle)
    if not decision.selected_candidates and not decision.suppressed_candidates:
        return intervention
    selected_ids = decision.selected_ids()
    ranked = dict(intervention)
    candidate = _mapping(ranked.get("candidate"))
    proposal = _mapping(ranked.get("proposal"))
    observation_id = f"observation:{_normalize_string(candidate.get('key')) or 'live'}"
    proposal_id = f"proposal:{_normalize_string(proposal.get('key')) or 'live'}"
    selected_by_id = {
        _normalize_string(row.get("candidate_id")): dict(row)
        for row in decision.selected_candidates
    }
    suppressed_by_id = {
        _normalize_string(row.get("candidate_id")): dict(row)
        for row in decision.suppressed_candidates
    }
    if _normalize_token(candidate.get("stage")) == "card":
        if observation_id not in selected_ids:
            candidate["suppressed_reason"] = (
                _normalize_string(suppressed_by_id.get(observation_id, {}).get("suppressed_reason"))
                or "value_engine_suppressed"
            )
        else:
            candidate.update(signal_selection.value_payload_fields(selected_by_id[observation_id], selected=True))
    if proposal and (not include_proposal or proposal_id not in selected_ids):
        proposal["suppressed_reason"] = (
            _normalize_string(suppressed_by_id.get(proposal_id, {}).get("suppressed_reason"))
            or "value_engine_suppressed"
        )
    elif proposal_id in selected_ids:
        proposal.update(signal_selection.value_payload_fields(selected_by_id[proposal_id], selected=True))
    ranked["candidate"] = candidate
    ranked["proposal"] = proposal
    return ranked


def render_live_text(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
    prefer_ambient_over_teaser: bool = True,
) -> str:
    intervention = _ranked_intervention_payload(bundle, include_proposal=include_proposal)
    rendered = surface_runtime.render_blocks(
        intervention,
        markdown=markdown,
        include_proposal=include_proposal,
    )
    ambient_texts = [
        _normalize_string(payload.get("markdown_text" if markdown else "plain_text"))
        for payload in _selected_ambient_payloads(bundle)
    ]
    ambient_text = "\n\n".join(text for text in ambient_texts if text)
    if rendered:
        return surface_runtime.wrap_live_text("\n\n".join(text for text in [ambient_text, rendered] if text))
    teaser_text = surface_runtime.teaser_text(intervention)
    if prefer_ambient_over_teaser and ambient_text:
        return surface_runtime.wrap_live_text(ambient_text)
    if teaser_text:
        return surface_runtime.wrap_live_text(teaser_text)
    return surface_runtime.wrap_live_text(ambient_text)


def render_closeout_text(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
) -> str:
    closeout = _mapping(bundle.get("closeout_bundle"))
    return _normalize_block_string(closeout.get("markdown_text" if markdown else "plain_text"))


def append_intervention_events(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    include_proposal: bool,
    include_closeout: bool = False,
    delivery_channel: str = "",
    delivery_status: str = "",
    render_surface: str = "",
    delivery_latency_ms: float | None = None,
) -> list[str]:
    events: list[str] = []
    intervention = _ranked_intervention_payload(bundle, include_proposal=include_proposal)
    ambient_payloads = _selected_ambient_payloads(bundle)
    observation = _mapping(bundle.get("observation"))
    event_metadata = value_engine_event_metadata.value_decision_event_metadata(
        decision=_visible_signal_decision(bundle),
        delivery_channel=delivery_channel,
        delivery_status=delivery_status,
        render_surface=render_surface,
    )
    if intervention:
        event_bundle = dict(intervention)
        event_bundle.setdefault("observation", observation)
        events.extend(
            surface_runtime.append_bundle_events(
                repo_root=repo_root,
                bundle=event_bundle,
                include_proposal=include_proposal,
                include_teaser=not bool(ambient_payloads),
                delivery_channel=delivery_channel,
                delivery_status=delivery_status,
                render_surface=render_surface,
                delivery_latency_ms=delivery_latency_ms,
                metadata=event_metadata,
            )
        )
    for ambient in ambient_payloads:
        if not _normalize_string(ambient.get("markdown_text")):
            continue
        candidate = _mapping(intervention.get("candidate"))
        moment = _mapping(candidate.get("moment"))
        ambient_signature = ambient.get("semantic_signature")
        semantic_signature = ambient_signature if isinstance(ambient_signature, list) else moment.get("semantic_signature")
        ambient_key = _normalize_string(ambient.get("candidate_id")) or signal_selection.ambient_candidate_id(ambient)
        surface_runtime.stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="ambient_signal",
            summary=_normalize_string(ambient.get("plain_text")) or "Odylith ambient signal.",
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key=ambient_key,
            turn_phase=_normalize_string(observation.get("turn_phase")),
            artifacts=observation.get("changed_paths") if isinstance(observation.get("changed_paths"), list) else (),
            display_markdown=_normalize_block_string(ambient.get("markdown_text")),
            display_plain=_normalize_block_string(ambient.get("plain_text")),
            prompt_excerpt=_normalize_string(observation.get("prompt_excerpt")),
            assistant_summary=_normalize_string(observation.get("assistant_summary")),
            moment_kind=_normalize_string(ambient.get("source_kind")),
            semantic_signature=semantic_signature if isinstance(semantic_signature, list) else (),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
            metadata={**event_metadata, "event_candidate_id": ambient_key}
            if event_metadata
            else {"event_candidate_id": ambient_key},
        )
        events.append("ambient_signal")
    closeout_text = render_closeout_text(bundle, markdown=True) if include_closeout else ""
    if closeout_text:
        surface_runtime.stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="assist_closeout",
            summary=_normalize_string(closeout_text),
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key="assist",
            turn_phase=_normalize_string(observation.get("turn_phase")),
            artifacts=observation.get("changed_paths") if isinstance(observation.get("changed_paths"), list) else (),
            display_markdown=closeout_text,
            display_plain=render_closeout_text(bundle, markdown=False),
            prompt_excerpt=_normalize_string(observation.get("prompt_excerpt")),
            assistant_summary=_normalize_string(observation.get("assistant_summary")),
            moment_kind="assist",
            semantic_signature=("assist",),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
            metadata=event_metadata,
        )
        events.append("assist_closeout")
    return events
