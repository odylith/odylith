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
    "delivery_intelligence",
    "operator_experience",
}
_VISIBILITY_REQUIRED_LANES = {
    *_BASE_REQUIRED_LANES,
    "analysis_engine",
    "domain_intelligence",
    "reasoning_engine",
    "tribunal",
    "proof_state",
    "surface_dags",
    "topology_integrity",
    "governance_engine",
    "turn_gate",
    "discipline_engine",
    "benchmark_harness",
    "taxonomies_fsms",
    "subagent_router",
    "subagent_orchestrator",
    "install_upgrade_migration_runtime",
    "security_trust",
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


def _status_or_policy_deferred(*, present: bool, required: bool) -> str:
    if present:
        return "covered"
    return "policy_deferred" if required else "quiet"


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


def _component_evidence(context_packet: Mapping[str, Any], components: Sequence[str]) -> list[str]:
    return _normalize_string_list(components) + _normalize_string_list(context_packet.get("components"))


def _workstream_evidence(context_packet: Mapping[str, Any], workstreams: Sequence[str]) -> list[str]:
    return _normalize_string_list(workstreams) + _normalize_string_list(context_packet.get("workstreams"))


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
        required=("subagent_router" in required_lanes or "subagent_orchestrator" in required_lanes),
    )
    discipline_summary = _mapping(context.get("discipline_summary")) or _mapping(memory.get("discipline_summary"))
    guidance_summary = _mapping(context.get("guidance_behavior_summary")) or _mapping(
        memory.get("guidance_behavior_summary")
    )
    component_evidence = _component_evidence(context, components)
    workstream_evidence = _workstream_evidence(context, workstreams)
    anchor_diagrams = _normalize_string_list(_mapping(context.get("anchors")).get("diagrams"))
    topology_present = bool(diagrams or anchor_diagrams or _mapping(context.get("topology_integrity")))
    taxonomies_present = bool(
        guidance_summary
        or discipline_summary
        or _mapping(context.get("validation_bundle"))
        or _mapping(context.get("taxonomy_summary"))
        or _mapping(context.get("fsm_summary"))
    )
    greenfield_present = bool(
        "domain-intelligence" in component_evidence
        or any(token == "B-142" for token in workstream_evidence)
        or "greenfield" in _normalize_token(context.get("packet_kind"))
    )
    operator_experience_present = bool(
        _normalize_token(host_family)
        or _normalize_token(turn_phase)
        or _normalize_string(visibility.get("chat_visible_proof"))
    )
    reasoning_present = bool(tribunal_present or greenfield_present)
    proof_state_present = bool(_mapping(context.get("proof_state")) or _mapping(delivery.get("proof_state")))
    turn_gate_present = bool(_mapping(context.get("turn_gate")) or _mapping(execution.get("turn_gate")))
    benchmark_present = bool(_mapping(context.get("benchmark_summary")) or _mapping(memory.get("benchmark_summary")))
    lifecycle_present = bool(
        _mapping(context.get("install_upgrade_migration"))
        or _mapping(context.get("migration_runtime"))
        or _mapping(context.get("lifecycle"))
    )
    security_present = bool(_mapping(context.get("security_trust")) or _mapping(context.get("runtime_integrity")))

    lanes = [
        _lane(
            "analysis_engine",
            "Analysis Engine",
            "benchmark",
            _status_or_policy_deferred(
                present=bool(tribunal_present or guidance_summary),
                required="analysis_engine" in required_lanes,
            ),
            [
                _normalize_string(_mapping(tribunal.get("systemic_brief")).get("headline")),
                f"guidance_status={guidance_summary.get('status')}",
            ],
            required="analysis_engine" in required_lanes,
            note="analysis uses compact Tribunal or guidance summaries on the hot path; it must not start a fresh repo scan",
        ),
        _lane(
            "domain_intelligence",
            "Domain Intelligence",
            "domain-intelligence",
            _status_or_policy_deferred(
                present=greenfield_present,
                required="domain_intelligence" in required_lanes,
            ),
            [
                *[token for token in component_evidence if token == "domain-intelligence"],
                *[token for token in workstream_evidence if token == "B-142"],
                f"packet_kind={context.get('packet_kind')}",
            ],
            required="domain_intelligence" in required_lanes,
            note="domain intelligence is covered for greenfield/project-shape evidence and policy-deferred otherwise",
        ),
        _lane(
            "delivery_intelligence",
            "Delivery Intelligence",
            "delivery-intelligence",
            _status_from_presence(present=delivery_present, required=True),
            [
                f"chat_visible_proof={visibility.get('chat_visible_proof')}",
                f"delivery_events={delivery.get('event_count')}",
                f"visible_events={delivery.get('visible_event_count')}",
            ],
            required="delivery_intelligence" in required_lanes,
        ),
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
            "reasoning_engine",
            "Reasoning Engine",
            "tribunal",
            _status_or_policy_deferred(
                present=reasoning_present,
                required="reasoning_engine" in required_lanes,
            ),
            [
                f"tribunal_source={tribunal.get('source')}",
                f"greenfield_present={greenfield_present}",
            ],
            required="reasoning_engine" in required_lanes,
            note="reasoning is represented through deterministic Tribunal or greenfield adjudication summaries",
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
            "proof_state",
            "Proof State",
            "proof-state",
            _status_or_policy_deferred(
                present=proof_state_present,
                required="proof_state" in required_lanes,
            ),
            [
                f"context_proof_state={bool(_mapping(context.get('proof_state')))}",
                f"delivery_proof_state={bool(_mapping(delivery.get('proof_state')))}",
            ],
            required="proof_state" in required_lanes,
            note="proof-state claims use supplied compact proof posture only; missing proof snapshots are deferred on the hot path",
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
            "surface_dags",
            "Surface DAGs",
            "odylith-projection-bundle",
            _status_or_policy_deferred(
                present=bool(surface_status and surface_status != "unavailable"),
                required="surface_dags" in required_lanes,
            ),
            [
                f"surface_status={surface_status}",
                f"latest_packet_state={runtime_surface.get('latest_packet_state')}",
            ],
            required="surface_dags" in required_lanes,
            note="DAG proof is covered when cached runtime surface summary exists; otherwise visibility recovery defers rather than rescans",
        ),
        _lane(
            "topology_integrity",
            "Topology Integrity",
            "atlas",
            _status_or_policy_deferred(
                present=topology_present,
                required="topology_integrity" in required_lanes,
            ),
            [
                f"diagram_count={len(diagrams)}",
                f"anchor_diagram_count={len(anchor_diagrams)}",
                f"topology_quality={_mapping(context.get('topology_integrity')).get('quality')}",
            ],
            required="topology_integrity" in required_lanes,
            note="topology proof uses supplied diagram/topology summaries only; missing topology evidence is policy-deferred on the hot path",
        ),
        _lane(
            "governance_engine",
            "Governance Engine",
            "registry",
            _status_from_presence(
                present=governance_anchor_count > 0,
                required="governance_engine" in required_lanes,
            ),
            [
                f"anchor_count={governance_anchor_count}",
                *workstreams,
                *components,
                *bugs,
                *diagrams,
            ],
            required="governance_engine" in required_lanes,
        ),
        _lane(
            "turn_gate",
            "Governed Harness / Turn Gate",
            "governed-harness",
            _status_or_policy_deferred(
                present=turn_gate_present,
                required="turn_gate" in required_lanes,
            ),
            [
                f"context_turn_gate={bool(_mapping(context.get('turn_gate')))}",
                f"execution_turn_gate={bool(_mapping(execution.get('turn_gate')))}",
            ],
            required="turn_gate" in required_lanes,
            note="turn-gate proof is covered when compact gate summaries are supplied; visibility recovery does not run gate validation inline",
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
        _lane(
            "subagent_router",
            "Subagent Router",
            "subagent-router",
            subagent_status,
            subagent_evidence,
            required="subagent_router" in required_lanes,
            note="router evidence uses host support and policy hints; active host policy decides whether delegation may run",
        ),
        _lane(
            "subagent_orchestrator",
            "Subagent Orchestrator",
            "subagent-orchestrator",
            subagent_status,
            subagent_evidence,
            required="subagent_orchestrator" in required_lanes,
            note="orchestrator proof shares the same compact delegation-policy evidence as the router on this hot path",
        ),
        _lane(
            "discipline_engine",
            "Discipline Engine",
            "execution-engine",
            _status_or_policy_deferred(
                present=bool(discipline_summary),
                required="discipline_engine" in required_lanes,
            ),
            [
                f"status={discipline_summary.get('status')}",
                f"validation_status={discipline_summary.get('validation_status')}",
            ],
            required="discipline_engine" in required_lanes,
            note="local deterministic discipline summaries stay quiet unless evidence or a visibility-recovery proof needs the lane",
        ),
        _lane(
            "benchmark_harness",
            "Benchmark Harness",
            "benchmark",
            _status_or_policy_deferred(
                present=benchmark_present,
                required="benchmark_harness" in required_lanes,
            ),
            [
                f"context_benchmark={bool(_mapping(context.get('benchmark_summary')))}",
                f"memory_benchmark={bool(_mapping(memory.get('benchmark_summary')))}",
            ],
            required="benchmark_harness" in required_lanes,
            note="benchmark proof is policy-deferred on intervention hot paths unless a compact benchmark summary is already attached",
        ),
        _lane(
            "taxonomies_fsms",
            "Taxonomies and FSMs",
            "casebook",
            _status_or_policy_deferred(
                present=taxonomies_present,
                required="taxonomies_fsms" in required_lanes,
            ),
            [
                f"guidance_status={guidance_summary.get('status')}",
                f"discipline_status={discipline_summary.get('status')}",
                f"validation_bundle={bool(_mapping(context.get('validation_bundle')))}",
            ],
            required="taxonomies_fsms" in required_lanes,
            note="controlled vocabulary/FSM evidence comes from compact validation summaries, not fresh source validation",
        ),
        _lane(
            "install_upgrade_migration_runtime",
            "Install / Upgrade / Migration Runtime",
            "migration-runtime",
            _status_or_policy_deferred(
                present=lifecycle_present,
                required="install_upgrade_migration_runtime" in required_lanes,
            ),
            [
                f"install_upgrade_migration={bool(_mapping(context.get('install_upgrade_migration')))}",
                f"migration_runtime={bool(_mapping(context.get('migration_runtime')))}",
            ],
            required="install_upgrade_migration_runtime" in required_lanes,
            note="lifecycle proof is supplied by compact migration/runtime summaries and otherwise deferred on intervention hot paths",
        ),
        _lane(
            "security_trust",
            "Security and Trust",
            "release",
            _status_or_policy_deferred(
                present=security_present,
                required="security_trust" in required_lanes,
            ),
            [
                f"security_trust={bool(_mapping(context.get('security_trust')))}",
                f"runtime_integrity={bool(_mapping(context.get('runtime_integrity')))}",
            ],
            required="security_trust" in required_lanes,
            note="security/trust proof is covered when compact integrity summaries are attached; it must not verify release assets inline",
        ),
        _lane(
            "operator_experience",
            "Operator Experience",
            "governance-intervention-engine",
            _status_from_presence(
                present=operator_experience_present,
                required="operator_experience" in required_lanes,
            ),
            [
                f"host_family={host_family}",
                f"turn_phase={turn_phase}",
                f"chat_visible_proof={visibility.get('chat_visible_proof')}",
            ],
            required="operator_experience" in required_lanes,
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
