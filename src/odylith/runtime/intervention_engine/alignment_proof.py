"""Engine-lane proof summaries for host-visible intervention alignment.

Host prompt and checkpoint hooks must stay cheap, so this module only inspects
the compact summaries already assembled by ``alignment_context``. The result is
an explicit, JSON-friendly proof object that says which Odylith engines are
actually represented in a visible-intervention decision and which lanes are
quiet or deferred.
"""

from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.value_coercion import int_value as _int
from odylith.runtime.common.value_coercion import mapping_copy as _mapping
from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_string_list as _normalize_string_list
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token


_SATISFYING_STATUSES = {"covered", "policy_deferred"}
_BASE_REQUIRED_LANES = {
    "context_engine",
    "execution_engine",
    "intervention_engine",
    "memory_substrate",
    "delivery",
}
_VISIBILITY_REQUIRED_LANES = {
    *_BASE_REQUIRED_LANES,
    "tribunal",
    "governance",
    "subagent_orchestration",
}


def _string_map(value: Any) -> dict[str, Any]:
    return _mapping(value)


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _evidence(*values: Any, limit: int = 8) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            candidates = value
        else:
            candidates = (value,)
        for item in candidates:
            token = _normalize_string(item)
            if not token or token in seen:
                continue
            seen.add(token)
            rows.append(token)
            if len(rows) >= max(1, int(limit)):
                return rows
    return rows


def _count_fields(*values: Any) -> int:
    total = 0
    for value in values:
        if isinstance(value, Mapping):
            total += len([key for key, item in value.items() if item not in ("", [], {}, None, False)])
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            total += len(value)
        elif _normalize_string(value):
            total += 1
    return total


def _lane(
    lane_id: str,
    label: str,
    registry_component_id: str,
    status: str,
    evidence: Sequence[str],
    *,
    required: bool,
    note: str = "",
) -> dict[str, Any]:
    normalized_status = _normalize_token(status) or "quiet"
    return {
        "lane_id": lane_id,
        "label": label,
        "registry_component_id": registry_component_id,
        "status": normalized_status,
        "required": bool(required),
        "satisfied": (not required) or normalized_status in _SATISFYING_STATUSES,
        "evidence": _evidence(evidence, limit=8),
        "note": _normalize_string(note),
    }


def _status_from_presence(*, present: bool, required: bool) -> str:
    if present:
        return "covered"
    return "missing" if required else "quiet"


def _anchor_count(
    *,
    context_packet: Mapping[str, Any],
    components: Sequence[str],
    workstreams: Sequence[str],
    bugs: Sequence[str],
    diagrams: Sequence[str],
) -> int:
    anchors = _mapping(context_packet.get("anchors"))
    return sum(
        len(_normalize_string_list(value))
        for value in (
            components,
            workstreams,
            bugs,
            diagrams,
            context_packet.get("components"),
            context_packet.get("workstreams"),
            context_packet.get("bugs"),
            context_packet.get("diagrams"),
            anchors.get("components"),
            anchors.get("workstreams"),
            anchors.get("bugs"),
            anchors.get("diagrams"),
        )
    )


def _subagent_status(execution_summary: Mapping[str, Any], *, required: bool) -> tuple[str, list[str]]:
    hints = _normalize_string_list(execution_summary.get("execution_engine_host_execution_hints"))
    supports_native_spawn = bool(execution_summary.get("execution_engine_host_supports_native_spawn"))
    if any("native_spawn_policy:host_policy_gated" in hint for hint in hints):
        return "policy_deferred", hints
    if supports_native_spawn or hints:
        return "covered", hints or ["native_spawn_transport_available"]
    return ("missing" if required else "quiet"), []


def build_alignment_proof(
    *,
    host_family: str,
    turn_phase: str,
    visibility_failure: bool,
    context_packet: Mapping[str, Any] | None = None,
    execution_engine_summary: Mapping[str, Any] | None = None,
    memory_summary: Mapping[str, Any] | None = None,
    tribunal_summary: Mapping[str, Any] | None = None,
    visibility_summary: Mapping[str, Any] | None = None,
    delivery_snapshot: Mapping[str, Any] | None = None,
    components: Sequence[str] = (),
    workstreams: Sequence[str] = (),
    bugs: Sequence[str] = (),
    diagrams: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a compact proof that the visible host lane carries engine context."""

    context = _string_map(context_packet)
    execution = _string_map(execution_engine_summary)
    memory = _string_map(memory_summary)
    tribunal = _string_map(tribunal_summary)
    visibility = _string_map(visibility_summary)
    delivery = _string_map(delivery_snapshot)
    required_lanes = set(_VISIBILITY_REQUIRED_LANES if visibility_failure else _BASE_REQUIRED_LANES)

    context_present = bool(
        _normalize_string(context.get("packet_state"))
        or _normalize_string(context.get("packet_kind"))
        or _mapping(context.get("route"))
    )
    execution_present = bool(
        execution.get("execution_engine_present")
        or _normalize_string(execution.get("execution_engine_next_move"))
        or _normalize_string(execution.get("execution_engine_outcome"))
    )
    intervention_present = bool(
        _normalize_string(context.get("component_id")) == "governance-intervention-engine"
        or "governance-intervention-engine" in _normalize_string_list(context.get("components"))
    )
    memory_present = bool(
        memory.get("visibility_complaint")
        or _normalize_string(memory.get("host_family"))
        or _normalize_string(memory.get("session_id"))
        or _int(memory.get("recent_event_count")) > 0
        or _int(memory.get("visible_event_count")) > 0
    )
    delivery_present = bool(
        _normalize_string(visibility.get("chat_visible_proof"))
        or delivery
        or _int(visibility.get("event_count")) > 0
        or _int(delivery.get("event_count")) > 0
    )
    tribunal_present = bool(
        _sequence(tribunal.get("scope_signals"))
        or _sequence(tribunal.get("case_queue"))
        or _mapping(tribunal.get("systemic_brief"))
        or _normalize_string(tribunal.get("source"))
    )
    governance_anchor_count = _anchor_count(
        context_packet=context,
        components=components,
        workstreams=workstreams,
        bugs=bugs,
        diagrams=diagrams,
    )
    runtime_surface = _mapping(context.get("runtime_surface_summary"))
    surface_status = _normalize_token(runtime_surface.get("status"))
    subagent_status, subagent_evidence = _subagent_status(
        execution,
        required="subagent_orchestration" in required_lanes,
    )
    discipline_summary = _mapping(context.get("discipline_summary")) or _mapping(memory.get("discipline_summary"))
    guidance_summary = _mapping(context.get("guidance_behavior_summary")) or _mapping(
        memory.get("guidance_behavior_summary")
    )

    lanes = [
        _lane(
            "context_engine",
            "Context Engine",
            "odylith-context-engine",
            _status_from_presence(present=context_present, required=True),
            [
                f"packet_state={context.get('packet_state')}",
                f"packet_kind={context.get('packet_kind')}",
            ],
            required="context_engine" in required_lanes,
        ),
        _lane(
            "execution_engine",
            "Execution Engine",
            "execution-engine",
            _status_from_presence(present=execution_present, required=True),
            [
                f"next_move={execution.get('execution_engine_next_move')}",
                f"outcome={execution.get('execution_engine_outcome')}",
                f"mode={execution.get('execution_engine_mode')}",
            ],
            required="execution_engine" in required_lanes,
        ),
        _lane(
            "intervention_engine",
            "Intervention Engine",
            "governance-intervention-engine",
            _status_from_presence(present=intervention_present, required=True),
            ["host_intervention_alignment_context"],
            required="intervention_engine" in required_lanes,
        ),
        _lane(
            "tribunal",
            "Tribunal",
            "tribunal",
            _status_from_presence(
                present=tribunal_present,
                required="tribunal" in required_lanes,
            ),
            [
                f"source={tribunal.get('source')}",
                f"case_count={len(_sequence(tribunal.get('case_queue')))}",
                f"scope_signal_count={len(_sequence(tribunal.get('scope_signals')))}",
            ],
            required="tribunal" in required_lanes,
        ),
        _lane(
            "governance",
            "Governance",
            "registry",
            _status_from_presence(
                present=governance_anchor_count > 0,
                required="governance" in required_lanes,
            ),
            [
                f"anchor_count={governance_anchor_count}",
                *workstreams,
                *components,
                *bugs,
                *diagrams,
            ],
            required="governance" in required_lanes,
        ),
        _lane(
            "subagent_orchestration",
            "Subagent Orchestration",
            "subagent-orchestrator",
            subagent_status,
            subagent_evidence,
            required="subagent_orchestration" in required_lanes,
            note="transport known; active host policy decides whether delegation may run",
        ),
        _lane(
            "discipline",
            "Discipline",
            "execution-engine",
            "covered" if discipline_summary else "quiet",
            [
                f"status={discipline_summary.get('status')}",
                f"validation_status={discipline_summary.get('validation_status')}",
            ],
            required=False,
        ),
        _lane(
            "surface_dags",
            "Surface DAGs",
            "odylith-projection-bundle",
            "covered" if surface_status and surface_status != "unavailable" else "quiet",
            [
                f"surface_status={surface_status}",
                f"latest_packet_state={runtime_surface.get('latest_packet_state')}",
            ],
            required=False,
        ),
        _lane(
            "delivery",
            "Delivery",
            "delivery-intelligence",
            _status_from_presence(present=delivery_present, required=True),
            [
                f"chat_visible_proof={visibility.get('chat_visible_proof')}",
                f"delivery_events={delivery.get('event_count')}",
                f"visible_events={delivery.get('visible_event_count')}",
            ],
            required="delivery" in required_lanes,
        ),
        _lane(
            "analysis",
            "Analysis",
            "benchmark",
            "covered" if tribunal_present or guidance_summary else "quiet",
            [
                _normalize_string(_mapping(tribunal.get("systemic_brief")).get("headline")),
                f"guidance_status={guidance_summary.get('status')}",
            ],
            required=False,
        ),
        _lane(
            "memory_substrate",
            "Memory Substrate",
            "odylith-memory-backend",
            _status_from_presence(present=memory_present, required=True),
            [
                f"session_id={memory.get('session_id')}",
                f"recent_event_count={memory.get('recent_event_count')}",
                f"visible_event_count={memory.get('visible_event_count')}",
            ],
            required="memory_substrate" in required_lanes,
        ),
    ]
    missing_required = [
        row["lane_id"]
        for row in lanes
        if row["required"] and row["status"] not in _SATISFYING_STATUSES
    ]
    covered_lanes = [row["lane_id"] for row in lanes if row["status"] in _SATISFYING_STATUSES]
    if missing_required:
        status = "degraded"
    elif visibility_failure:
        status = "ready"
    elif covered_lanes:
        status = "quiet"
    else:
        status = "empty"
    return {
        "schema_version": 1,
        "proof_kind": "visibility_recovery" if visibility_failure else "host_intervention_alignment",
        "status": status,
        "host_family": _normalize_token(host_family),
        "turn_phase": _normalize_token(turn_phase),
        "visibility_failure": bool(visibility_failure),
        "required_lanes": sorted(required_lanes),
        "covered_lanes": covered_lanes,
        "missing_required_lanes": missing_required,
        "lane_count": len(lanes),
        "covered_lane_count": len(covered_lanes),
        "observed_field_count": _count_fields(context, execution, memory, tribunal, visibility, delivery),
        "hot_path_constraints": {
            "local_summaries_only": True,
            "provider_calls": False,
            "repo_scan": False,
        },
        "lanes": lanes,
    }


__all__ = ["build_alignment_proof"]
