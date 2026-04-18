"""Compact end-to-end evidence extraction for visible interventions.

The visible intervention hot path receives several already-local summaries:
Context Engine packet data, Execution Engine snapshot fields, session memory,
Tribunal delivery signals, and the delivery ledger. This module makes those
inputs look like one small evidence model so lower layers do not have to know
which surface populated which field.
"""

from __future__ import annotations

import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.character import runtime as character_runtime
from odylith.runtime.governance import guidance_behavior_runtime
from odylith.runtime.intervention_engine.contract import GovernanceFact
from odylith.runtime.intervention_engine.contract import ObservationEnvelope
from odylith.runtime.intervention_engine import visibility_contract


_ANCHOR_KEYS: tuple[tuple[str, str], ...] = (
    ("workstreams", "workstream"),
    ("components", "component"),
    ("bugs", "bug"),
    ("diagrams", "diagram"),
)
_LIST_MEMORY_KEYS: tuple[str, ...] = (
    "recent_signatures",
    "recent_teaser_signatures",
    "recent_card_signatures",
    "recent_moment_kinds",
)
_COUNT_MEMORY_KEYS: tuple[str, ...] = (
    "recent_event_count",
    "delivery_event_count",
    "visible_event_count",
    "chat_confirmed_event_count",
    "unconfirmed_event_count",
)
_WORKSTREAM_RE = re.compile(r"\bB-\d{3,}\b")
_BUG_RE = re.compile(r"\bCB-\d{3,}\b")
_DIAGRAM_RE = re.compile(r"\bD-\d{3,}\b")
_GUIDANCE_BEHAVIOR_PROBLEM_STATUSES = {
    "failed",
    "malformed",
    "unavailable",
    "error",
}
_CHARACTER_PROBLEM_STATUSES = _GUIDANCE_BEHAVIOR_PROBLEM_STATUSES


def _normalize_string(value: Any) -> str:
    return visibility_contract.normalize_string(value)


def _normalize_token(value: Any) -> str:
    return visibility_contract.normalize_token(value)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _string_list(value: Any, *, limit: int = 12) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for item in _sequence(value):
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if len(rows) >= max(1, int(limit)):
            return rows
    token = _normalize_string(value) if isinstance(value, str) else ""
    return [token] if token else rows


def _merge_lists(*values: Any, limit: int = 12) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        for token in _string_list(value, limit=limit):
            if token in seen:
                continue
            seen.add(token)
            rows.append(token)
            if len(rows) >= max(1, int(limit)):
                return rows
    return rows


def _guidance_behavior_summary_from_observation(observation: ObservationEnvelope) -> dict[str, Any]:
    summary = guidance_behavior_runtime.summary_from_sources(
        observation.context_packet_summary,
        observation.packet_summary,
        observation.memory_summary,
        observation.tribunal_summary,
        limit=6,
    )
    if summary:
        return summary
    packet = merged_packet_summary(observation)
    status = _normalize_token(packet.get("guidance_behavior_status"))
    if not status:
        return {}
    return {
        key: value
        for key, value in {
            "family": "guidance_behavior",
            "status": status,
            "validation_status": packet.get("guidance_behavior_validation_status"),
            "case_count": _int(packet.get("guidance_behavior_case_count")),
            "critical_or_high_case_count": _int(packet.get("guidance_behavior_critical_or_high_case_count")),
            "failed_check_ids": _string_list(packet.get("guidance_behavior_failed_check_ids"), limit=8),
        }.items()
        if value not in ("", [], {}, None, 0)
    }


def _character_summary_from_observation(observation: ObservationEnvelope) -> dict[str, Any]:
    summary = character_runtime.summary_from_sources(
        observation.context_packet_summary,
        observation.packet_summary,
        observation.memory_summary,
        observation.tribunal_summary,
        limit=6,
    )
    if summary:
        return summary
    packet = merged_packet_summary(observation)
    status = _normalize_token(packet.get("character_status"))
    if not status:
        return {}
    return {
        key: value
        for key, value in {
            "family": "agent_operating_character",
            "status": status,
            "validation_status": packet.get("character_validation_status"),
            "case_count": _int(packet.get("character_case_count")),
            "selected_case_ids": _string_list(packet.get("character_selected_case_ids"), limit=8),
            "validator_command": packet.get("character_validator_command"),
        }.items()
        if value not in ("", [], {}, None, 0)
    }


def _guidance_behavior_is_material(summary: Mapping[str, Any]) -> bool:
    if not summary:
        return False
    status = _normalize_token(summary.get("status"))
    validation_status = _normalize_token(summary.get("validation_status"))
    return bool(
        status in _GUIDANCE_BEHAVIOR_PROBLEM_STATUSES
        or validation_status in _GUIDANCE_BEHAVIOR_PROBLEM_STATUSES
        or _int(summary.get("case_count")) > 0
        or _string_list(summary.get("failed_check_ids"), limit=1)
        or _normalize_string(summary.get("validator_command"))
    )


def _character_is_material(summary: Mapping[str, Any]) -> bool:
    if not summary:
        return False
    status = _normalize_token(summary.get("status"))
    validation_status = _normalize_token(summary.get("validation_status"))
    return bool(
        status in _CHARACTER_PROBLEM_STATUSES
        or validation_status in _CHARACTER_PROBLEM_STATUSES
        or _int(summary.get("case_count")) > 0
        or _normalize_string(summary.get("validator_command"))
    )


def _ref(kind: str, item_id: Any, *, path: Any = "", label: Any = "") -> dict[str, str]:
    return {
        "kind": _normalize_token(kind),
        "id": _normalize_string(item_id),
        "path": _normalize_string(path),
        "label": _normalize_string(label) or _normalize_string(item_id),
    }


def _dedupe_refs(rows: Sequence[Mapping[str, Any]], *, limit: int = 24) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        normalized = _ref(
            row.get("kind"),
            row.get("id") or row.get("value"),
            path=row.get("path"),
            label=row.get("label"),
        )
        if not normalized["kind"] or not normalized["id"]:
            continue
        key = (normalized["kind"], normalized["id"], normalized["path"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
        if len(deduped) >= max(1, int(limit)):
            break
    return deduped


def _anchor_values(packet: Mapping[str, Any], key: str) -> list[str]:
    anchors = _mapping(packet.get("anchors"))
    return _merge_lists(packet.get(key), anchors.get(key), limit=12)


def _diagnostic_anchor_values(packet: Mapping[str, Any], kind: str) -> list[str]:
    target_resolution = _mapping(packet.get("target_resolution"))
    rows: list[str] = []
    for item in _sequence(target_resolution.get("diagnostic_anchors")):
        row = _mapping(item)
        if _normalize_token(row.get("kind")) != kind:
            continue
        token = _normalize_string(row.get("value") or row.get("id"))
        if token:
            rows.append(token)
    return _merge_lists(rows, limit=12)


def merged_packet_summary(observation: ObservationEnvelope) -> dict[str, Any]:
    """Return packet anchors from legacy and current Context Engine fields."""

    legacy = _mapping(observation.packet_summary)
    context = _mapping(observation.context_packet_summary)
    packet: dict[str, Any] = {**legacy, **context}
    for key, singular in _ANCHOR_KEYS:
        packet[key] = _merge_lists(
            legacy.get(key),
            context.get(key),
            _anchor_values(legacy, key),
            _anchor_values(context, key),
            _diagnostic_anchor_values(legacy, singular),
            _diagnostic_anchor_values(context, singular),
            limit=12,
        )
    route = _mapping(context.get("route"))
    if route:
        packet["route_ready"] = bool(route.get("route_ready"))
        packet["native_spawn_ready"] = bool(route.get("native_spawn_ready"))
        packet["narrowing_required"] = bool(route.get("narrowing_required"))
    return {key: value for key, value in packet.items() if value not in ("", [], {}, None)}


def active_target_refs(observation: ObservationEnvelope) -> list[dict[str, str]]:
    """Return entity refs across packet, execution, Tribunal, and envelope refs."""

    refs: list[dict[str, Any]] = [dict(row) for row in observation.active_target_refs]
    prompt_surface = " ".join(
        token
        for token in (observation.prompt_excerpt, observation.assistant_summary)
        if _normalize_string(token)
    )
    for token in _WORKSTREAM_RE.findall(prompt_surface):
        refs.append(_ref("workstream", token.upper()))
    for token in _BUG_RE.findall(prompt_surface):
        refs.append(_ref("bug", token.upper()))
    for token in _DIAGRAM_RE.findall(prompt_surface):
        refs.append(_ref("diagram", token.upper()))
    packet = merged_packet_summary(observation)
    for key, singular in _ANCHOR_KEYS:
        for token in _string_list(packet.get(key), limit=12):
            refs.append(_ref(singular, token))

    execution = _mapping(observation.execution_engine_summary)
    if _execution_summary_is_material(execution):
        for token in _string_list(execution.get("execution_engine_target_component_ids"), limit=8):
            refs.append(_ref("component", token))
        target_component = _normalize_string(execution.get("execution_engine_target_component_id"))
        if target_component:
            refs.append(_ref("component", target_component))

    tribunal = _mapping(observation.tribunal_summary)
    for scope in _sequence(tribunal.get("scope_signals")):
        row = _mapping(scope)
        refs.append(_ref(row.get("scope_type"), row.get("scope_id"), label=row.get("scope_label")))
    for case in _sequence(tribunal.get("case_queue")):
        row = _mapping(case)
        case_id = _normalize_string(row.get("id"))
        if case_id.startswith("CB-"):
            refs.append(_ref("bug", case_id, label=row.get("headline")))
    guidance_behavior = _guidance_behavior_summary_from_observation(observation)
    guidance_signal = _mapping(guidance_behavior.get("tribunal_signal"))
    if guidance_signal:
        refs.append(
            _ref(
                guidance_signal.get("scope_type") or "component",
                guidance_signal.get("scope_id") or "governance-intervention-engine",
                label=guidance_signal.get("scope_label") or "Guidance Behavior Contract",
            )
        )
    if _character_is_material(_character_summary_from_observation(observation)):
        refs.append(_ref("component", "execution-engine", label="Odylith Discipline Contract"))
    return _dedupe_refs(refs)


def _execution_summary_is_material(execution: Mapping[str, Any]) -> bool:
    next_move = _normalize_string(execution.get("execution_engine_next_move"))
    blocker = _normalize_string(execution.get("execution_engine_blocker"))
    outcome = _normalize_token(execution.get("execution_engine_outcome"))
    return bool(
        blocker
        or next_move.startswith("recover.")
        or outcome in {"deny", "blocked"}
        or _int(execution.get("execution_engine_candidate_target_count")) > 0
        or _int(execution.get("execution_engine_diagnostic_anchor_count")) > 0
    )


def merged_session_memory(
    *,
    observation: ObservationEnvelope,
    stream_memory: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge stream memory with the compact memory carried on the envelope."""

    stream = _mapping(stream_memory)
    envelope = _mapping(observation.memory_summary)
    payload: dict[str, Any] = {**envelope, **stream}
    for key in _LIST_MEMORY_KEYS:
        payload[key] = _merge_lists(stream.get(key), envelope.get(key), limit=12)
    for key in _COUNT_MEMORY_KEYS:
        payload[key] = max(_int(stream.get(key)), _int(envelope.get(key)))
    if bool(stream.get("visibility_complaint")) or bool(envelope.get("visibility_complaint")):
        payload["visibility_complaint"] = True
    payload["host_family"] = _normalize_token(stream.get("host_family") or envelope.get("host_family") or observation.host_family)
    payload["session_id"] = _normalize_string(stream.get("session_id") or envelope.get("session_id") or observation.session_id)
    return {key: value for key, value in payload.items() if value not in ("", [], {}, None, False)}


def runtime_evidence_classes(observation: ObservationEnvelope) -> list[str]:
    rows: list[str] = []
    packet = merged_packet_summary(observation)
    if _packet_summary_is_material(packet):
        rows.append("context_engine_packet")
    if _execution_summary_is_material(_mapping(observation.execution_engine_summary)):
        rows.append("execution_engine_snapshot")
    if _memory_summary_is_material(_mapping(observation.memory_summary)):
        rows.append("session_memory")
    if _tribunal_summary_is_material(_mapping(observation.tribunal_summary)):
        rows.append("tribunal_signal")
    if _guidance_behavior_is_material(_guidance_behavior_summary_from_observation(observation)):
        rows.append("guidance_behavior_contract")
    if _character_is_material(_character_summary_from_observation(observation)):
        rows.append("agent_operating_character_contract")
    if _visibility_summary_is_material(_mapping(observation.visibility_summary)):
        rows.append("visibility_ledger")
    if _delivery_snapshot_is_material(_mapping(observation.delivery_snapshot)):
        rows.append("delivery_ledger")
    return _merge_lists(rows, limit=8)


def _packet_summary_is_material(packet: Mapping[str, Any]) -> bool:
    if _normalize_token(packet.get("packet_state")) == "visibility_recovery":
        return True
    route_ready = bool(packet.get("route_ready"))
    return route_ready or any(_string_list(packet.get(key), limit=1) for key, _kind in _ANCHOR_KEYS)


def _memory_summary_is_material(memory: Mapping[str, Any]) -> bool:
    return bool(
        memory.get("visibility_complaint")
        or _int(memory.get("recent_event_count")) > 0
        or any(_string_list(memory.get(key), limit=1) for key in _LIST_MEMORY_KEYS)
    )


def _tribunal_summary_is_material(tribunal: Mapping[str, Any]) -> bool:
    systemic = _mapping(tribunal.get("systemic_brief"))
    return bool(
        _sequence(tribunal.get("scope_signals"))
        or _sequence(tribunal.get("case_queue"))
        or _normalize_string(systemic.get("headline") or systemic.get("summary"))
    )


def _visibility_summary_is_material(visibility: Mapping[str, Any]) -> bool:
    proof = _normalize_token(visibility.get("chat_visible_proof"))
    return bool(
        proof not in {"", "unproven_this_session"}
        or _int(visibility.get("event_count")) > 0
        or _int(visibility.get("visible_event_count")) > 0
        or _int(visibility.get("chat_confirmed_event_count")) > 0
        or _int(visibility.get("unconfirmed_event_count")) > 0
    )


def _delivery_snapshot_is_material(delivery: Mapping[str, Any]) -> bool:
    return bool(
        _int(delivery.get("event_count")) > 0
        or _int(delivery.get("visible_event_count")) > 0
        or _int(delivery.get("chat_confirmed_event_count")) > 0
        or _int(delivery.get("unconfirmed_event_count")) > 0
    )


def alignment_signal_text(observation: ObservationEnvelope) -> str:
    packet = merged_packet_summary(observation)
    execution = _mapping(observation.execution_engine_summary)
    memory = _mapping(observation.memory_summary)
    tribunal = _mapping(observation.tribunal_summary)
    visibility = _mapping(observation.visibility_summary)
    guidance_behavior = _guidance_behavior_summary_from_observation(observation)
    character = _character_summary_from_observation(observation)
    pieces: list[Any] = [
        packet.get("packet_state"),
        packet.get("packet_kind"),
        execution.get("execution_engine_next_move"),
        execution.get("execution_engine_blocker"),
        "visibility complaint" if memory.get("visibility_complaint") else "",
        visibility.get("chat_visible_proof"),
        guidance_behavior.get("status"),
        guidance_behavior.get("validation_status"),
        character.get("status"),
        character.get("validation_status"),
    ]
    pieces.extend(_string_list(execution.get("execution_engine_pressure_signals"), limit=6))
    pieces.extend(_string_list(guidance_behavior.get("failed_check_ids"), limit=6))
    pieces.extend(_string_list(guidance_behavior.get("selected_case_ids"), limit=6))
    pieces.extend(_string_list(character.get("selected_case_ids"), limit=6))
    systemic = _mapping(tribunal.get("systemic_brief"))
    pieces.extend(
        [
            systemic.get("headline"),
            systemic.get("summary"),
            systemic.get("latent_causes"),
        ]
    )
    for case in _sequence(tribunal.get("case_queue"))[:3]:
        row = _mapping(case)
        pieces.extend([row.get("id"), row.get("headline"), row.get("brief")])
    return " ".join(_merge_lists(pieces, limit=24))


def _fact(
    kind: str,
    headline: str,
    detail: str,
    evidence_classes: Sequence[str],
    refs: Sequence[Mapping[str, Any]],
    priority: int,
) -> GovernanceFact:
    return GovernanceFact(
        kind=_normalize_token(kind),
        headline=_normalize_string(headline),
        detail=_normalize_string(detail),
        evidence_classes=_merge_lists(evidence_classes, runtime_evidence_classes_from_refs(refs), limit=10),
        refs=_dedupe_refs(refs, limit=8),
        priority=max(0, min(100, int(priority))),
    )


def runtime_evidence_classes_from_refs(refs: Sequence[Mapping[str, Any]]) -> list[str]:
    classes: list[str] = []
    for row in refs:
        kind = _normalize_token(row.get("kind")) if isinstance(row, Mapping) else ""
        if kind in {"bug", "workstream", "component", "diagram"}:
            classes.append(f"{kind}_anchor")
    return _merge_lists(classes, limit=6)


def governance_facts_from_alignment(
    *,
    observation: ObservationEnvelope,
    evidence_classes: Sequence[str],
) -> list[GovernanceFact]:
    """Extract only high-signal runtime facts from compact alignment summaries."""

    facts: list[GovernanceFact] = []
    execution = _mapping(observation.execution_engine_summary)
    next_move = _normalize_string(execution.get("execution_engine_next_move"))
    blocker = _normalize_string(execution.get("execution_engine_blocker"))
    outcome = _normalize_token(execution.get("execution_engine_outcome"))
    if blocker or next_move.startswith("recover.") or outcome == "deny":
        detail = blocker or next_move or "Execution Engine is holding the current move behind a recovery posture."
        facts.append(
            _fact(
                "invariant",
                "Execution Engine has an active recovery constraint.",
                detail,
                evidence_classes,
                [_ref("component", "execution-engine", label="Execution Engine")],
                88,
            )
        )

    tribunal = _mapping(observation.tribunal_summary)
    case_refs: list[dict[str, Any]] = []
    for case in _sequence(tribunal.get("case_queue"))[:2]:
        row = _mapping(case)
        case_id = _normalize_string(row.get("id"))
        if not case_id:
            continue
        case_ref: list[dict[str, Any]]
        if case_id.startswith("CB-"):
            case_ref = [_ref("bug", case_id, label=row.get("headline"))]
            case_refs.extend(case_ref)
        else:
            case_ref = [_ref("component", "tribunal", label="Tribunal")]
        facts.append(
            _fact(
                "history",
                f"Tribunal already has {case_id} in the decision path.",
                _normalize_string(row.get("brief") or row.get("headline")) or "A prior adjudicated case is already connected to this slice.",
                evidence_classes,
                case_ref,
                94 if case_id.startswith("CB-") else 86,
            )
        )
    for scope in _sequence(tribunal.get("scope_signals"))[:2]:
        row = _mapping(scope)
        readout = _mapping(row.get("operator_readout"))
        issue = _normalize_string(readout.get("issue"))
        action = _normalize_string(readout.get("action"))
        severity = _normalize_token(readout.get("severity"))
        if not issue and severity not in {"p0", "p1", "blocked", "warning"}:
            continue
        refs = [_ref(row.get("scope_type"), row.get("scope_id"), label=row.get("scope_label"))]
        if case_refs:
            refs.extend(case_refs)
        facts.append(
            _fact(
                "invariant" if severity in {"p0", "p1", "blocked"} else "governance_truth",
                _normalize_string(issue) or "Tribunal has a high-priority scope signal for this slice.",
                action or "Respect the Tribunal signal before spending visible Odylith attention.",
                evidence_classes,
                refs,
                92 if severity in {"p0", "p1", "blocked"} else 84,
            )
        )

    visibility = _mapping(observation.visibility_summary)
    proof = _normalize_token(visibility.get("chat_visible_proof"))
    unconfirmed = _int(visibility.get("unconfirmed_event_count"))
    memory = _mapping(observation.memory_summary)
    packet = merged_packet_summary(observation)
    visibility_recovery = (
        bool(memory.get("visibility_complaint"))
        or _normalize_token(packet.get("packet_state")) == "visibility_recovery"
    )
    if visibility_recovery and (
        proof in {"pending_confirmation", "ledger_visible_with_pending_confirmation", "chat_confirmed_with_pending_confirmation"}
        or unconfirmed
    ):
        facts.append(
            _fact(
                "invariant",
                "Delivery ledger still has Odylith blocks awaiting chat confirmation.",
                "Replay the exact visible Markdown before treating the signal as proven visible.",
                evidence_classes,
                [_ref("component", "governance-intervention-engine", label="Governance Intervention Engine")],
                90,
            )
        )
    guidance_behavior = _guidance_behavior_summary_from_observation(observation)
    guidance_status = _normalize_token(guidance_behavior.get("status"))
    guidance_validation_status = _normalize_token(guidance_behavior.get("validation_status"))
    if (
        guidance_status in _GUIDANCE_BEHAVIOR_PROBLEM_STATUSES
        or guidance_validation_status in _GUIDANCE_BEHAVIOR_PROBLEM_STATUSES
    ):
        failed_checks = _string_list(guidance_behavior.get("failed_check_ids"), limit=4)
        detail = (
            "Failing checks: " + ", ".join(failed_checks)
            if failed_checks
            else "The guidance behavior corpus or validator is not in a usable passing state."
        )
        guidance_signal = _mapping(guidance_behavior.get("tribunal_signal"))
        refs = [
            _ref(
                guidance_signal.get("scope_type") or "component",
                guidance_signal.get("scope_id") or "governance-intervention-engine",
                label=guidance_signal.get("scope_label") or "Guidance Behavior Contract",
            )
        ]
        facts.append(
            _fact(
                "invariant",
                "Guidance behavior validation is not passing.",
                detail,
                _merge_lists(evidence_classes, ["guidance_behavior_contract"], limit=10),
                refs,
                91,
            )
        )
    character = _character_summary_from_observation(observation)
    character_status = _normalize_token(character.get("status"))
    character_validation_status = _normalize_token(character.get("validation_status"))
    if (
        character_status in _CHARACTER_PROBLEM_STATUSES
        or character_validation_status in _CHARACTER_PROBLEM_STATUSES
    ):
        detail = (
            "Run the local Discipline validator before surfacing behavior claims."
            if _normalize_string(character.get("validator_command"))
            else "The Odylith Discipline corpus or validator is not in a usable passing state."
        )
        facts.append(
            _fact(
                "invariant",
                "Odylith Discipline validation is not passing.",
                detail,
                _merge_lists(evidence_classes, ["agent_operating_character_contract"], limit=10),
                [_ref("component", "execution-engine", label="Odylith Discipline Contract")],
                92,
            )
        )
    return _dedupe_facts(facts)


def _dedupe_facts(facts: Sequence[GovernanceFact]) -> list[GovernanceFact]:
    rows: list[GovernanceFact] = []
    seen: set[tuple[str, str, str]] = set()
    for fact in sorted(facts, key=lambda row: int(row.priority), reverse=True):
        ref_key = "|".join(f"{row.get('kind')}:{row.get('id')}" for row in fact.refs)
        key = (_normalize_token(fact.kind), _normalize_string(fact.headline).casefold(), ref_key)
        if key in seen:
            continue
        seen.add(key)
        rows.append(fact)
    return rows


def merge_governance_facts(*groups: Sequence[GovernanceFact], limit: int = 6) -> list[GovernanceFact]:
    return _dedupe_facts([row for group in groups for row in group])[: max(1, int(limit))]


__all__ = [
    "active_target_refs",
    "alignment_signal_text",
    "governance_facts_from_alignment",
    "merge_governance_facts",
    "merged_packet_summary",
    "merged_session_memory",
    "runtime_evidence_classes",
]
