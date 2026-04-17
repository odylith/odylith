"""Extracted assessment and context-signal helpers for the subagent router."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.consumer_profile import load_consumer_profile
from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.orchestration import subagent_router_execution_engine_runtime


def _host():
    from odylith.runtime.orchestration import subagent_router as host

    return host


def _bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if token in {"1", "true", "yes", "on"}:
        return True
    if token in {"", "0", "false", "no", "off"}:
        return False
    return bool(value)


def _preferred_value(summary: Mapping[str, Any], key: str, *fallbacks: Any) -> Any:
    if key in summary:
        return summary.get(key)
    for fallback in fallbacks:
        if fallback not in ("", [], {}, None):
            return fallback
    return None


def request_with_consumer_write_policy(
    request: RouteRequest,
    *,
    repo_root: Path | None,
) -> RouteRequest:
    if repo_root is None or not request.needs_write:
        return request
    profile = load_consumer_profile(repo_root=Path(repo_root).resolve())
    policy = dict(profile.get("odylith_write_policy", {})) if isinstance(profile.get("odylith_write_policy"), Mapping) else {}
    if not policy:
        return request
    host = _host()
    _normalize_context_signals = host._normalize_context_signals
    RouteRequest = host.RouteRequest
    merged_context = _normalize_context_signals(request.context_signals)
    if merged_context.get("odylith_write_policy") == policy:
        return request
    merged_context["odylith_write_policy"] = policy
    payload = request.as_dict()
    payload["context_signals"] = merged_context
    return RouteRequest(**payload)


def _context_signal_summary(request: RouteRequest) -> dict[str, Any]:
    host = _host()
    _normalize_context_signals = host._normalize_context_signals
    _context_signal_root = host._context_signal_root
    _mapping_value = host._mapping_value
    _validation_bundle_from_context = host._validation_bundle_from_context
    _governance_obligations_from_context = host._governance_obligations_from_context
    _surface_refs_from_context = host._surface_refs_from_context
    _execution_profile_mapping = host._execution_profile_mapping
    _preferred_router_profile_from_execution_profile = host._preferred_router_profile_from_execution_profile
    _context_signal_score = host._context_signal_score
    _context_lookup = host._context_lookup
    _normalize_token = host._normalize_token
    _context_signal_bool = host._context_signal_bool
    _normalize_list = host._normalize_list
    _count_or_list_len = host._count_or_list_len
    _normalize_string = host._normalize_string
    _dedupe_strings = host._dedupe_strings
    _int_value = host._int_value
    _clamp_score = host._clamp_score
    _normalized_rate = host._normalized_rate
    _latency_pressure_signal = host._latency_pressure_signal
    _scaled_numeric_signal = host._scaled_numeric_signal
    _context_signal_level = host._context_signal_level
    _SCORE_MAX = host._SCORE_MAX
    _SCORE_MIN = host._SCORE_MIN

    context_signals = _normalize_context_signals(request.context_signals)
    root = _context_signal_root(context_signals)
    context_packet = _mapping_value(context_signals, "context_packet")
    if not isinstance(context_packet, Mapping):
        context_packet = {}
    execution_engine_payload = _mapping_value(context_signals, "execution_engine")
    if not isinstance(execution_engine_payload, Mapping):
        execution_engine_payload = _mapping_value(context_packet, "execution_engine")
    if not isinstance(execution_engine_payload, Mapping):
        execution_engine_payload = _mapping_value(root, "execution_engine")
    if not isinstance(execution_engine_payload, Mapping):
        execution_engine_payload = {}
    execution_engine_summary = (
        subagent_router_execution_engine_runtime.execution_engine_summary_from_context_sources(
            context_signals=context_signals,
            root=root,
            context_packet=context_packet,
            execution_engine_payload=execution_engine_payload,
        )
    )
    validation_bundle = _validation_bundle_from_context(context_signals, context_packet=context_packet)
    governance_obligations = _governance_obligations_from_context(context_signals, context_packet=context_packet)
    surface_refs = _surface_refs_from_context(context_signals, context_packet=context_packet)
    evidence_pack = _mapping_value(context_signals, "evidence_pack")
    if not isinstance(evidence_pack, Mapping):
        evidence_pack = {}
    optimization_snapshot = _mapping_value(context_signals, "optimization_snapshot")
    if not isinstance(optimization_snapshot, Mapping):
        optimization_snapshot = {}
    optimization_overall = (
        dict(optimization_snapshot.get("overall", {}))
        if isinstance(optimization_snapshot.get("overall", {}), Mapping)
        else {}
    )
    optimization_packet_posture = (
        dict(optimization_snapshot.get("packet_posture", {}))
        if isinstance(optimization_snapshot.get("packet_posture", {}), Mapping)
        else {}
    )
    optimization_quality_posture = (
        dict(optimization_snapshot.get("quality_posture", {}))
        if isinstance(optimization_snapshot.get("quality_posture", {}), Mapping)
        else {}
    )
    optimization_orchestration_posture = (
        dict(optimization_snapshot.get("orchestration_posture", {}))
        if isinstance(optimization_snapshot.get("orchestration_posture", {}), Mapping)
        else {}
    )
    optimization_intent_posture = (
        dict(optimization_snapshot.get("intent_posture", {}))
        if isinstance(optimization_snapshot.get("intent_posture", {}), Mapping)
        else {}
    )
    optimization_evaluation_posture = (
        dict(optimization_snapshot.get("evaluation_posture", {}))
        if isinstance(optimization_snapshot.get("evaluation_posture", {}), Mapping)
        else {}
    )
    optimization_latency_posture = (
        dict(optimization_snapshot.get("latency_posture", {}))
        if isinstance(optimization_snapshot.get("latency_posture", {}), Mapping)
        else {}
    )
    optimization_learning_loop = (
        dict(optimization_snapshot.get("learning_loop", {}))
        if isinstance(optimization_snapshot.get("learning_loop", {}), Mapping)
        else {}
    )
    optimization_control_advisories = (
        dict(optimization_snapshot.get("control_advisories", {}))
        if isinstance(optimization_snapshot.get("control_advisories", {}), Mapping)
        else {}
    )
    odylith_write_policy = (
        dict(_mapping_value(context_signals, "odylith_write_policy"))
        if isinstance(_mapping_value(context_signals, "odylith_write_policy"), Mapping)
        else {}
    )
    odylith_fix_mode = _normalize_token(odylith_write_policy.get("odylith_fix_mode"))
    allow_odylith_mutations = _context_signal_bool(odylith_write_policy.get("allow_odylith_mutations"))
    odylith_write_protected_roots = [
        str(token).strip().strip("/")
        for token in _normalize_list(odylith_write_policy.get("protected_roots"))
        if str(token).strip().strip("/")
    ]
    normalized_allowed_paths = [str(path).strip().lstrip("./") for path in request.allowed_paths if str(path).strip()]
    consumer_odylith_write_blocked = bool(
        request.needs_write
        and odylith_fix_mode == "feedback_only"
        and not allow_odylith_mutations
        and any(
            path == root or path.startswith(f"{root}/")
            for path in normalized_allowed_paths
            for root in odylith_write_protected_roots
        )
    )
    evaluation_packet_posture = (
        dict(optimization_evaluation_posture.get("packet_events", {}))
        if isinstance(optimization_evaluation_posture.get("packet_events", {}), Mapping)
        else {}
    )
    evaluation_router_posture = (
        dict(optimization_evaluation_posture.get("router_outcomes", {}))
        if isinstance(optimization_evaluation_posture.get("router_outcomes", {}), Mapping)
        else {}
    )
    evaluation_orchestration_posture = (
        dict(optimization_evaluation_posture.get("orchestration_feedback", {}))
        if isinstance(optimization_evaluation_posture.get("orchestration_feedback", {}), Mapping)
        else {}
    )
    evaluation_decision_quality = (
        dict(optimization_evaluation_posture.get("decision_quality", {}))
        if isinstance(optimization_evaluation_posture.get("decision_quality", {}), Mapping)
        else {}
    )
    evaluation_trend_posture = (
        dict(optimization_evaluation_posture.get("trend_posture", {}))
        if isinstance(optimization_evaluation_posture.get("trend_posture", {}), Mapping)
        else {}
    )
    evaluation_control_posture = (
        dict(optimization_evaluation_posture.get("control_posture", {}))
        if isinstance(optimization_evaluation_posture.get("control_posture", {}), Mapping)
        else {}
    )
    evaluation_freshness = (
        dict(optimization_evaluation_posture.get("freshness", {}))
        if isinstance(optimization_evaluation_posture.get("freshness", {}), Mapping)
        else {}
    )
    evaluation_evidence_strength = (
        dict(optimization_evaluation_posture.get("evidence_strength", {}))
        if isinstance(optimization_evaluation_posture.get("evidence_strength", {}), Mapping)
        else {}
    )
    evaluation_control_advisories = (
        dict(optimization_evaluation_posture.get("control_advisories", {}))
        if isinstance(optimization_evaluation_posture.get("control_advisories", {}), Mapping)
        else {}
    )
    learning_control_advisories = (
        dict(optimization_learning_loop.get("control_advisories", {}))
        if isinstance(optimization_learning_loop.get("control_advisories", {}), Mapping)
        else {}
    )
    learning_freshness = (
        dict(optimization_learning_loop.get("freshness", {}))
        if isinstance(optimization_learning_loop.get("freshness", {}), Mapping)
        else {}
    )
    learning_evidence_strength = (
        dict(optimization_learning_loop.get("evidence_strength", {}))
        if isinstance(optimization_learning_loop.get("evidence_strength", {}), Mapping)
        else {}
    )
    control_advisories: dict[str, Any] = {}
    for source in (learning_control_advisories, evaluation_control_advisories, optimization_control_advisories):
        for key, value in source.items():
            if key not in control_advisories or control_advisories[key] in ("", [], {}, None):
                control_advisories[key] = value
    advisory_confidence = (
        dict(control_advisories.get("confidence", {}))
        if isinstance(control_advisories.get("confidence", {}), Mapping)
        else {}
    )
    advisory_freshness = (
        dict(control_advisories.get("freshness", {}))
        if isinstance(control_advisories.get("freshness", {}), Mapping)
        else dict(learning_freshness or evaluation_freshness)
    )
    advisory_evidence_strength = (
        dict(control_advisories.get("evidence_strength", {}))
        if isinstance(control_advisories.get("evidence_strength", {}), Mapping)
        else dict(learning_evidence_strength or evaluation_evidence_strength)
    )
    evaluation_overall_freshness = (
        dict(evaluation_freshness.get("overall", {}))
        if isinstance(evaluation_freshness.get("overall"), Mapping)
        else dict(evaluation_freshness)
    )
    execution_profile = _execution_profile_mapping(
        root=root,
        context_packet=context_packet,
        evidence_pack=evidence_pack,
        optimization_snapshot=optimization_snapshot,
    )
    preferred_execution_profile = _preferred_router_profile_from_execution_profile(execution_profile)
    host_runtime = host_runtime_contract.resolve_host_runtime(
        _context_lookup(root, "host_runtime"),
        _context_lookup(context_signals, "host_runtime"),
        _context_lookup(execution_profile, "host_runtime"),
    )
    native_spawn_supported = host_runtime_contract.native_spawn_supported(
        host_runtime,
        default_when_unknown=False,
    )
    execution_confidence = (
        dict(execution_profile.get("confidence", {}))
        if isinstance(execution_profile.get("confidence", {}), Mapping)
        else {}
    )
    execution_constraints = (
        dict(execution_profile.get("constraints", {}))
        if isinstance(execution_profile.get("constraints", {}), Mapping)
        else {}
    )
    execution_signals = (
        dict(execution_profile.get("signals", {}))
        if isinstance(execution_profile.get("signals", {}), Mapping)
        else {}
    )
    execution_grounding_score = _context_signal_score(_context_lookup(execution_signals, "grounding"))
    execution_ambiguity_score = _context_signal_score(_context_lookup(execution_signals, "ambiguity"))
    execution_density_score = _context_signal_score(_context_lookup(execution_signals, "density"))
    execution_actionability_score = _context_signal_score(_context_lookup(execution_signals, "actionability"))
    execution_validation_score = _context_signal_score(_context_lookup(execution_signals, "validation_pressure"))
    execution_merge_burden_score = _context_signal_score(_context_lookup(execution_signals, "merge_burden"))
    execution_expected_delegation_value_score = _context_signal_score(
        _context_lookup(execution_signals, "expected_delegation_value")
    )

    group_kind = _normalize_token(_context_lookup(root, "orchestration", "group_kind") or "")
    support_leaf = _context_signal_bool(_context_lookup(root, "orchestration", "support_leaf")) or group_kind == "support"
    primary_leaf = _context_signal_bool(_context_lookup(root, "orchestration", "primary_parallel_safe")) or group_kind in {
        "primary",
        "implementation",
    }
    same_prefix_disjoint_exception = _context_signal_bool(
        _context_lookup(root, "parallelism", "same_prefix_disjoint_exception")
        or _context_lookup(root, "orchestration", "same_prefix_disjoint_exception")
    )
    reasoning_bias = _normalize_token(
        _context_lookup(root, "reasoning_bias")
        or _context_lookup(root, "packet_quality", "reasoning_bias")
        or _context_lookup(context_packet, "route", "reasoning_bias")
    )
    parallelism_hint = _normalize_token(
        _context_lookup(root, "parallelism_hint")
        or _context_lookup(root, "parallelism", "hint")
        or _context_lookup(root, "packet_quality", "parallelism_hint")
        or _context_lookup(context_packet, "route", "parallelism_hint")
    )
    routing_confidence = _normalize_token(
        _context_lookup(root, "routing_confidence")
        or _context_lookup(context_packet, "packet_quality", "routing_confidence")
        or packet_quality_codec.packet_quality_value(_context_lookup(context_packet, "packet_quality"), "routing_confidence")
        or ""
    )
    intent_family = _normalize_token(
        _context_lookup(root, "intent", "family")
        or _context_lookup(root, "packet_quality", "intent_profile", "family")
        or _context_lookup(context_packet, "packet_quality", "intent_family")
        or packet_quality_codec.packet_quality_value(_context_lookup(context_packet, "packet_quality"), "intent_family")
    )
    intent_mode = _normalize_token(
        _context_lookup(root, "intent", "mode")
        or _context_lookup(root, "packet_quality", "intent_profile", "mode")
        or _context_lookup(context_packet, "packet_quality", "intent_mode")
        or packet_quality_codec.packet_quality_value(_context_lookup(context_packet, "packet_quality"), "intent_mode")
    )
    intent_critical_path = _normalize_token(
        _context_lookup(root, "intent", "critical_path")
        or _context_lookup(root, "packet_quality", "intent_profile", "critical_path")
    )
    intent_confidence_score = max(
        _context_signal_score(_context_lookup(root, "intent", "confidence")),
        _context_signal_score(_context_lookup(root, "packet_quality", "intent_profile", "confidence")),
    )
    recommended_commands = _normalize_list(_mapping_value(validation_bundle, "recommended_commands"))
    strict_gate_command_count = _count_or_list_len(
        validation_bundle,
        list_key="strict_gate_commands",
        count_key="strict_gate_command_count",
    )
    plan_binding_required = _context_signal_bool(_mapping_value(validation_bundle, "plan_binding_required"))
    governed_surface_sync_required = _context_signal_bool(
        _mapping_value(validation_bundle, "governed_surface_sync_required")
    )
    touched_workstream_count = _count_or_list_len(
        governance_obligations,
        list_key="touched_workstreams",
        count_key="touched_workstream_count",
    )
    primary_governance_workstream = _normalize_string(_mapping_value(governance_obligations, "primary_workstream_id"))
    if touched_workstream_count <= 0 and primary_governance_workstream:
        touched_workstream_count = 1
    touched_component_count = _count_or_list_len(
        governance_obligations,
        list_key="touched_components",
        count_key="touched_component_count",
    )
    primary_governance_component = _normalize_string(_mapping_value(governance_obligations, "primary_component_id"))
    if touched_component_count <= 0 and primary_governance_component:
        touched_component_count = 1
    linked_bug_count = _count_or_list_len(
        governance_obligations,
        list_key="linked_bugs",
        count_key="linked_bug_count",
    )
    required_diagram_count = _count_or_list_len(
        governance_obligations,
        list_key="required_diagrams",
        count_key="required_diagram_count",
    )
    closeout_doc_count = _count_or_list_len(
        governance_obligations,
        list_key="closeout_docs",
        count_key="closeout_doc_count",
    )
    workstream_state_action_count = _count_or_list_len(
        governance_obligations,
        list_key="workstream_state_actions",
        count_key="workstream_state_action_count",
    )
    impacted_surfaces = _mapping_value(surface_refs, "impacted_surfaces")
    governance_reason_refs = _mapping_value(surface_refs, "reasons")
    compact_reason_groups = _mapping_value(surface_refs, "reason_groups")
    compact_surface_list = _normalize_list(_mapping_value(surface_refs, "surfaces"))
    compact_reason_surfaces = (
        _dedupe_strings(
            surface
            for row in compact_reason_groups
            if isinstance(compact_reason_groups, list) and isinstance(row, Mapping)
            for surface in _normalize_list(_mapping_value(row, "surfaces"))
        )
        if isinstance(compact_reason_groups, list)
        else []
    )
    impacted_surface_count = (
        len([key for key, value in impacted_surfaces.items() if key and value not in ("", [], {}, None, False)])
        if isinstance(impacted_surfaces, Mapping)
        else len(compact_surface_list)
        if compact_surface_list
        else len(compact_reason_surfaces)
        if compact_reason_surfaces
        else _int_value(_mapping_value(surface_refs, "surface_count"))
    )
    governance_reason_count = (
        len([key for key, value in governance_reason_refs.items() if key and value not in ("", [], {}, None, False)])
        if isinstance(governance_reason_refs, Mapping)
        else len([row for row in compact_reason_groups if row not in ("", [], {}, None, False)])
        if isinstance(compact_reason_groups, list)
        else _int_value(_mapping_value(surface_refs, "reason_group_count"))
    )
    governance_closeout_score = _clamp_score(
        (1 if recommended_commands or strict_gate_command_count > 0 else 0)
        + (1 if plan_binding_required or governed_surface_sync_required else 0)
        + (1 if touched_workstream_count or closeout_doc_count > 0 or workstream_state_action_count > 0 else 0)
        + (1 if touched_component_count or impacted_surface_count or required_diagram_count or linked_bug_count else 0)
    )
    bounded_governance_delegate_candidate = bool(
        governance_closeout_score >= 3
        and (
            strict_gate_command_count > 0
            or plan_binding_required
            or governed_surface_sync_required
        )
        and (
            touched_workstream_count > 0
            or touched_component_count > 0
            or closeout_doc_count > 0
            or impacted_surface_count > 0
        )
    )
    context_packet_state = _normalize_token(
        _context_lookup(context_packet, "packet_state")
        or _context_lookup(root, "packet_state")
    )
    narrowing_required = _context_signal_bool(
        _context_lookup(root, "narrowing_required")
        or _context_lookup(context_packet, "route", "narrowing_required")
        or (
            context_packet_state.startswith("gated_")
            and not bounded_governance_delegate_candidate
        )
    )
    provenance = _mapping_value(evidence_pack, "provenance") if isinstance(evidence_pack, Mapping) else {}
    provenance_summary = _mapping_value(context_packet, "provenance_summary") if isinstance(context_packet, Mapping) else {}
    contract_count = len(
        [
            key
            for key in ("routing_handoff", "context_packet", "evidence_pack", "optimization_snapshot")
            if isinstance(_mapping_value(context_signals, key), Mapping)
        ]
    )
    optimization_within_budget_rate = _normalized_rate(_mapping_value(optimization_packet_posture, "within_budget_rate"))
    optimization_route_ready_rate = _normalized_rate(_mapping_value(optimization_quality_posture, "route_ready_rate"))
    optimization_native_spawn_ready_rate = _normalized_rate(
        _mapping_value(optimization_quality_posture, "native_spawn_ready_rate")
    )
    optimization_deep_reasoning_ready_rate = _normalized_rate(
        _mapping_value(optimization_quality_posture, "deep_reasoning_ready_rate")
    )
    optimization_high_utility_rate = _normalized_rate(_mapping_value(optimization_quality_posture, "high_utility_rate"))
    optimization_avg_context_density_score = round(
        _normalized_rate(_mapping_value(optimization_quality_posture, "avg_context_density_score")) * _SCORE_MAX,
        2,
    )
    if _mapping_value(optimization_quality_posture, "avg_context_density_score") not in (None, ""):
        optimization_avg_context_density_score = round(
            min(float(_mapping_value(optimization_quality_posture, "avg_context_density_score") or 0.0), float(_SCORE_MAX)),
            2,
        )
    optimization_avg_reasoning_readiness_score = round(
        min(float(_mapping_value(optimization_quality_posture, "avg_reasoning_readiness_score") or 0.0), float(_SCORE_MAX)),
        2,
    )
    optimization_avg_evidence_diversity_score = round(
        min(float(_mapping_value(optimization_quality_posture, "avg_evidence_diversity_score") or 0.0), float(_SCORE_MAX)),
        2,
    )
    optimization_delegated_lane_rate = _normalized_rate(
        _mapping_value(optimization_orchestration_posture, "delegated_lane_rate")
    )
    optimization_hold_local_rate = _normalized_rate(
        _mapping_value(optimization_orchestration_posture, "hold_local_rate")
    )
    optimization_runtime_backed_execution_rate = _normalized_rate(
        _mapping_value(optimization_orchestration_posture, "runtime_backed_execution_rate")
    )
    optimization_high_execution_confidence_rate = _normalized_rate(
        _mapping_value(optimization_orchestration_posture, "high_execution_confidence_rate")
    )
    optimization_explicit_intent_rate = _normalized_rate(_mapping_value(optimization_intent_posture, "explicit_rate"))
    optimization_packet_alignment_rate = _normalized_rate(
        _mapping_value(optimization_packet_posture, "advisory_alignment_rate")
    )
    optimization_reliable_packet_alignment_rate = _normalized_rate(
        _mapping_value(optimization_packet_posture, "reliable_advisory_alignment_rate")
    )
    optimization_packet_alignment_state = _normalize_token(
        _mapping_value(optimization_packet_posture, "packet_alignment_state")
    )
    optimization_avg_effective_yield_score = round(
        min(
            float(
                _mapping_value(optimization_quality_posture, "avg_effective_yield_score")
                or _mapping_value(optimization_packet_posture, "avg_effective_yield_score")
                or 0.0
            ),
            1.0,
        ),
        3,
    )
    optimization_high_yield_rate = _normalized_rate(
        _mapping_value(optimization_quality_posture, "high_yield_rate")
        or _mapping_value(optimization_packet_posture, "high_yield_rate")
    )
    optimization_reliable_high_yield_rate = _normalized_rate(
        _mapping_value(optimization_quality_posture, "reliable_high_yield_rate")
        or _mapping_value(optimization_packet_posture, "reliable_high_yield_rate")
    )
    optimization_yield_state = _normalize_token(
        _mapping_value(optimization_quality_posture, "yield_state")
        or _mapping_value(optimization_packet_posture, "yield_state")
    )
    optimization_latency_pressure_score = max(
        _latency_pressure_signal(_context_lookup(optimization_latency_posture, "impact", "avg_ms")),
        _latency_pressure_signal(_context_lookup(optimization_latency_posture, "session_brief", "avg_ms")),
        _latency_pressure_signal(_context_lookup(optimization_latency_posture, "bootstrap_session", "avg_ms")),
    )
    optimization_health_score = max(
        _context_signal_score(_context_lookup(root, "optimization", "utility_level")),
        _context_signal_score(_context_lookup(root, "optimization", "within_budget")),
        _scaled_numeric_signal(_context_lookup(context_packet, "optimization", "utility_score")),
        _context_signal_score(_context_lookup(context_packet, "optimization", "utility_level")),
        _context_signal_score(_context_lookup(context_packet, "optimization", "within_budget")),
        _scaled_numeric_signal(_mapping_value(optimization_overall, "score")),
        _context_signal_score(_mapping_value(optimization_overall, "level")),
        _scaled_numeric_signal(_mapping_value(optimization_packet_posture, "within_budget_rate")),
        _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "high_utility_rate")),
        _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "route_ready_rate")),
        _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "native_spawn_ready_rate")),
        _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "deep_reasoning_ready_rate")),
        _scaled_numeric_signal(_mapping_value(optimization_orchestration_posture, "runtime_backed_execution_rate")),
        _scaled_numeric_signal(_mapping_value(optimization_orchestration_posture, "high_execution_confidence_rate")),
    )
    provenance_score = max(
        2 if isinstance(_context_lookup(provenance, "source_classes"), Mapping) and _context_lookup(provenance, "source_classes") else 0,
        2
        if isinstance(_context_lookup(provenance_summary, "source_classes"), Mapping) and _context_lookup(provenance_summary, "source_classes")
        else 0,
        _context_signal_score(_context_lookup(provenance, "projection_fingerprint")),
    )
    execution_engine_present = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_present",
            _context_lookup(root, "execution_engine_present"),
            _context_lookup(context_signals, "execution_engine_present"),
            _context_lookup(context_signals, "latest_execution_engine_present"),
        )
    )
    execution_engine_outcome = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_outcome",
            _context_lookup(root, "execution_engine_outcome"),
            _context_lookup(context_signals, "execution_engine_outcome"),
            _context_lookup(context_signals, "latest_execution_engine_outcome"),
        )
    )
    execution_engine_requires_reanchor = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_requires_reanchor",
            _context_lookup(root, "execution_engine_requires_reanchor"),
            _context_lookup(context_signals, "execution_engine_requires_reanchor"),
            _context_lookup(context_signals, "latest_execution_engine_requires_reanchor"),
        )
    )
    execution_engine_mode = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_mode",
            _context_lookup(root, "execution_engine_mode"),
            _context_lookup(context_signals, "execution_engine_mode"),
            _context_lookup(context_signals, "latest_execution_engine_mode"),
        )
    )
    execution_engine_next_move = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_next_move",
            _context_lookup(root, "execution_engine_next_move"),
            _context_lookup(context_signals, "execution_engine_next_move"),
            _context_lookup(context_signals, "latest_execution_engine_next_move"),
        )
    )
    execution_engine_current_phase = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_current_phase",
            _context_lookup(root, "execution_engine_current_phase"),
            _context_lookup(context_signals, "execution_engine_current_phase"),
            _context_lookup(context_signals, "latest_execution_engine_current_phase"),
        )
    )
    execution_engine_last_successful_phase = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_last_successful_phase",
            _context_lookup(root, "execution_engine_last_successful_phase"),
            _context_lookup(context_signals, "execution_engine_last_successful_phase"),
            _context_lookup(context_signals, "latest_execution_engine_last_successful_phase"),
        )
    )
    execution_engine_blocker = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_blocker",
            _context_lookup(root, "execution_engine_blocker"),
            _context_lookup(context_signals, "execution_engine_blocker"),
            _context_lookup(context_signals, "latest_execution_engine_blocker"),
        )
    )
    execution_engine_closure = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_closure",
            _context_lookup(root, "execution_engine_closure"),
            _context_lookup(context_signals, "execution_engine_closure"),
            _context_lookup(context_signals, "latest_execution_engine_closure"),
        )
    )
    execution_engine_wait_status = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_wait_status",
            _context_lookup(root, "execution_engine_wait_status"),
            _context_lookup(context_signals, "execution_engine_wait_status"),
            _context_lookup(context_signals, "latest_execution_engine_wait_status"),
        )
    )
    execution_engine_wait_detail = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_wait_detail",
            _context_lookup(root, "execution_engine_wait_detail"),
            _context_lookup(context_signals, "execution_engine_wait_detail"),
            _context_lookup(context_signals, "latest_execution_engine_wait_detail"),
        )
    )
    execution_engine_resume_token = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_resume_token",
            _context_lookup(root, "execution_engine_resume_token"),
            _context_lookup(context_signals, "execution_engine_resume_token"),
            _context_lookup(context_signals, "latest_execution_engine_resume_token"),
        )
    )
    execution_engine_validation_archetype = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_validation_archetype",
            _context_lookup(root, "execution_engine_validation_archetype"),
            _context_lookup(context_signals, "execution_engine_validation_archetype"),
            _context_lookup(context_signals, "latest_execution_engine_validation_archetype"),
        )
    )
    execution_engine_validation_minimum_pass_count = _int_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_validation_minimum_pass_count",
            _context_lookup(root, "execution_engine_validation_minimum_pass_count"),
            _context_lookup(context_signals, "execution_engine_validation_minimum_pass_count"),
            _context_lookup(context_signals, "latest_execution_engine_validation_minimum_pass_count"),
        )
    )
    execution_engine_contradiction_count = _int_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_contradiction_count",
            _context_lookup(root, "execution_engine_contradiction_count"),
            _context_lookup(context_signals, "execution_engine_contradiction_count"),
            _context_lookup(context_signals, "latest_execution_engine_contradiction_count"),
        )
    )
    execution_engine_history_rule_count = _int_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_history_rule_count",
            _context_lookup(root, "execution_engine_history_rule_count"),
            _context_lookup(context_signals, "execution_engine_history_rule_count"),
            _context_lookup(context_signals, "latest_execution_engine_history_rule_count"),
        )
    )
    execution_engine_event_count = _int_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_event_count",
            _context_lookup(root, "execution_engine_event_count"),
            _context_lookup(context_signals, "execution_engine_event_count"),
            _context_lookup(context_signals, "latest_execution_engine_event_count"),
        )
    )
    execution_engine_authoritative_lane = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_authoritative_lane",
            _context_lookup(root, "execution_engine_authoritative_lane"),
            _context_lookup(context_signals, "execution_engine_authoritative_lane"),
            _context_lookup(context_signals, "latest_execution_engine_authoritative_lane"),
        )
    )
    execution_engine_host_family = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_host_family",
            _context_lookup(root, "execution_engine_host_family"),
            _context_lookup(context_signals, "execution_engine_host_family"),
            _context_lookup(context_signals, "latest_execution_engine_host_family"),
        )
    )
    execution_engine_model_family = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_model_family",
            _context_lookup(root, "execution_engine_model_family"),
            _context_lookup(context_signals, "execution_engine_model_family"),
            _context_lookup(context_signals, "latest_execution_engine_model_family"),
        )
    )
    execution_engine_host_supports_native_spawn = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_host_supports_native_spawn",
            _context_lookup(root, "execution_engine_host_supports_native_spawn"),
            _context_lookup(context_signals, "execution_engine_host_supports_native_spawn"),
            _context_lookup(context_signals, "latest_execution_engine_host_supports_native_spawn"),
        )
    )
    execution_engine_component_id = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_component_id",
            _context_lookup(root, "execution_engine_component_id"),
            _context_lookup(context_signals, "execution_engine_component_id"),
            _context_lookup(context_signals, "latest_execution_engine_component_id"),
        )
    )
    execution_engine_canonical_component_id = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_canonical_component_id",
            _context_lookup(root, "execution_engine_canonical_component_id"),
            _context_lookup(context_signals, "execution_engine_canonical_component_id"),
            _context_lookup(context_signals, "latest_execution_engine_canonical_component_id"),
        )
    )
    execution_engine_identity_status = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_identity_status",
            _context_lookup(root, "execution_engine_identity_status"),
            _context_lookup(context_signals, "execution_engine_identity_status"),
            _context_lookup(context_signals, "latest_execution_engine_identity_status"),
        )
    )
    execution_engine_target_component_id = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_target_component_id",
            _context_lookup(root, "execution_engine_target_component_id"),
            _context_lookup(context_signals, "execution_engine_target_component_id"),
            _context_lookup(context_signals, "latest_execution_engine_target_component_id"),
        )
    )
    execution_engine_target_component_ids = _normalize_list(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_target_component_ids",
            _context_lookup(root, "execution_engine_target_component_ids"),
            _context_lookup(context_signals, "execution_engine_target_component_ids"),
            _context_lookup(context_signals, "latest_execution_engine_target_component_ids"),
        )
    )[:4]
    execution_engine_target_component_status = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_target_component_status",
            _context_lookup(root, "execution_engine_target_component_status"),
            _context_lookup(context_signals, "execution_engine_target_component_status"),
            _context_lookup(context_signals, "latest_execution_engine_target_component_status"),
        )
    )
    execution_engine_snapshot_reuse_status = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_snapshot_reuse_status",
            _context_lookup(root, "execution_engine_snapshot_reuse_status"),
            _context_lookup(context_signals, "execution_engine_snapshot_reuse_status"),
            _context_lookup(context_signals, "latest_execution_engine_snapshot_reuse_status"),
        )
    )
    execution_engine_target_lane = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_target_lane",
            _context_lookup(root, "execution_engine_target_lane"),
            _context_lookup(context_signals, "execution_engine_target_lane"),
            _context_lookup(context_signals, "latest_execution_engine_target_lane"),
        )
    )
    execution_engine_has_writable_targets = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_has_writable_targets",
            _context_lookup(root, "execution_engine_has_writable_targets"),
            _context_lookup(context_signals, "execution_engine_has_writable_targets"),
            _context_lookup(context_signals, "latest_execution_engine_has_writable_targets"),
        )
    )
    execution_engine_requires_more_consumer_context = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_requires_more_consumer_context",
            _context_lookup(root, "execution_engine_requires_more_consumer_context"),
            _context_lookup(context_signals, "execution_engine_requires_more_consumer_context"),
            _context_lookup(context_signals, "latest_execution_engine_requires_more_consumer_context"),
        )
    )
    execution_engine_consumer_failover = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_consumer_failover",
            _context_lookup(root, "execution_engine_consumer_failover"),
            _context_lookup(context_signals, "execution_engine_consumer_failover"),
            _context_lookup(context_signals, "latest_execution_engine_consumer_failover"),
        )
    )
    execution_engine_commentary_mode = _normalize_token(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_commentary_mode",
            _context_lookup(root, "execution_engine_commentary_mode"),
            _context_lookup(context_signals, "execution_engine_commentary_mode"),
            _context_lookup(context_signals, "latest_execution_engine_commentary_mode"),
        )
    )
    execution_engine_suppress_routing_receipts = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_suppress_routing_receipts",
            _context_lookup(root, "execution_engine_suppress_routing_receipts"),
            _context_lookup(context_signals, "execution_engine_suppress_routing_receipts"),
            _context_lookup(context_signals, "latest_execution_engine_suppress_routing_receipts"),
        )
    )
    execution_engine_surface_fast_lane = _bool_value(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_surface_fast_lane",
            _context_lookup(root, "execution_engine_surface_fast_lane"),
            _context_lookup(context_signals, "execution_engine_surface_fast_lane"),
            _context_lookup(context_signals, "latest_execution_engine_surface_fast_lane"),
        )
    )
    execution_engine_validation_derived_from = _normalize_list(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_validation_derived_from",
            _context_lookup(root, "execution_engine_validation_derived_from"),
            _context_lookup(context_signals, "execution_engine_validation_derived_from"),
            _context_lookup(context_signals, "latest_execution_engine_validation_derived_from"),
        )
    )[:4]
    execution_engine_history_rule_hits = _normalize_list(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_history_rule_hits",
            _context_lookup(root, "execution_engine_history_rule_hits"),
            _context_lookup(context_signals, "execution_engine_history_rule_hits"),
            _context_lookup(context_signals, "latest_execution_engine_history_rule_hits"),
        )
    )[:4]
    execution_engine_pressure_signals = _normalize_list(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_pressure_signals",
            _context_lookup(root, "execution_engine_pressure_signals"),
            _context_lookup(context_signals, "execution_engine_pressure_signals"),
            _context_lookup(context_signals, "latest_execution_engine_pressure_signals"),
        )
    )[:4]
    execution_engine_nearby_denial_actions = _normalize_list(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_nearby_denial_actions",
            _context_lookup(root, "execution_engine_nearby_denial_actions"),
            _context_lookup(context_signals, "execution_engine_nearby_denial_actions"),
            _context_lookup(context_signals, "latest_execution_engine_nearby_denial_actions"),
        )
    )[:4]
    execution_engine_runtime_invalidated_by_step = _normalize_string(
        _preferred_value(
            execution_engine_summary,
            "execution_engine_runtime_invalidated_by_step",
            _context_lookup(root, "execution_engine_runtime_invalidated_by_step"),
            _context_lookup(context_signals, "execution_engine_runtime_invalidated_by_step"),
            _context_lookup(context_signals, "latest_execution_engine_runtime_invalidated_by_step"),
        )
    )
    return {
        "grounding_score": max(
            execution_grounding_score,
            _context_signal_score(_context_lookup(root, "grounding")),
            _context_signal_score(_context_lookup(root, "grounding", "grounded")),
            _context_signal_score(_context_lookup(root, "groundedness")),
            _context_signal_score(_context_lookup(context_packet, "anchors", "has_non_shared_anchor")),
            _context_signal_score(_context_lookup(evidence_pack, "anchors", "workstream_ids")),
            _SCORE_MAX if request.evidence_cone_grounded else _SCORE_MIN,
        ),
        "evidence_quality_score": max(
            _context_signal_score(_context_lookup(root, "packet_quality", "evidence_quality")),
            _context_signal_score(_context_lookup(root, "evidence_quality")),
            _context_signal_score(_context_lookup(root, "evidence")),
            _scaled_numeric_signal(_context_lookup(evidence_pack, "evidence_summary", "precision_score")),
            _scaled_numeric_signal(_context_lookup(context_packet, "retrieval_plan", "precision_score")),
        ),
        "actionability_score": max(
            execution_actionability_score,
            _context_signal_score(_context_lookup(root, "packet_quality", "actionability")),
            _context_signal_score(_context_lookup(root, "actionability")),
            _context_signal_score(_context_lookup(evidence_pack, "documents")),
            _context_signal_score(_context_lookup(evidence_pack, "commands")),
            _context_signal_score(_context_lookup(evidence_pack, "guidance")),
        ),
        "validation_burden_score": max(
            execution_validation_score,
            _context_signal_score(_context_lookup(root, "validation", "burden")),
            _context_signal_score(_context_lookup(root, "validation", "verification_rigor")),
            _context_signal_score(_context_lookup(root, "validation_burden")),
            _context_signal_score(_context_lookup(evidence_pack, "tests")),
            _context_signal_score(_context_lookup(evidence_pack, "commands")),
        ),
        "coordination_score": max(
            _context_signal_score(_context_lookup(root, "orchestration", "coordination_complexity")),
            _context_signal_score(_context_lookup(root, "coordination_cost")),
            _context_signal_score(_context_lookup(root, "parallelism", "merge_burden")),
        ),
        "parallelism_score": max(
            _context_signal_score(_context_lookup(root, "parallelism", "confidence")),
            _context_signal_score(_context_lookup(root, "parallelism", "safety")),
        ),
        "risk_score": max(
            _context_signal_score(_context_lookup(root, "risk")),
            _context_signal_score(_context_lookup(root, "correctness_risk")),
            _context_signal_score(_context_lookup(root, "orchestration", "risk")),
        ),
        "utility_score": max(
            _context_signal_score(_context_lookup(root, "utility")),
            _context_signal_score(_context_lookup(root, "packet_quality", "utility_profile")),
            _context_signal_score(_context_lookup(root, "utility_profile")),
            _scaled_numeric_signal(_context_lookup(context_packet, "packet_quality", "utility_score")),
            _scaled_numeric_signal(_context_lookup(context_packet, "optimization", "utility_score")),
            _context_signal_score(_context_lookup(context_packet, "optimization", "utility_level")),
            _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "avg_utility_score")),
        ),
        "token_efficiency_score": max(
            _context_signal_score(_context_lookup(root, "utility", "token_efficiency")),
            _context_signal_score(_context_lookup(root, "packet_quality", "utility_profile", "token_efficiency")),
            _context_signal_score(_context_lookup(root, "token_efficiency")),
            _context_signal_score(_context_lookup(context_packet, "optimization", "token_efficiency_level")),
            _scaled_numeric_signal(_context_lookup(context_packet, "optimization", "token_efficiency_score")),
        ),
        "context_density_score": max(
            execution_density_score,
            _context_signal_score(_context_lookup(root, "packet_quality", "context_density")),
            _context_signal_score(_context_lookup(root, "context_density")),
            _context_signal_score(_context_lookup(root, "optimization", "context_density")),
            _context_signal_score(_context_lookup(context_packet, "optimization", "context_density")),
            _context_signal_score(_context_lookup(context_packet, "packet_quality", "context_density_level")),
            _scaled_numeric_signal(_context_lookup(context_packet, "optimization", "avg_context_density_score")),
            _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "avg_context_density_score")),
        ),
        "reasoning_readiness_score": max(
            _context_signal_score(_context_lookup(root, "packet_quality", "reasoning_readiness")),
            _context_signal_score(_context_lookup(root, "reasoning_readiness")),
            _context_signal_score(_context_lookup(root, "optimization", "reasoning_readiness")),
            _context_signal_score(_context_lookup(context_packet, "optimization", "reasoning_readiness")),
            _context_signal_score(_context_lookup(context_packet, "packet_quality", "reasoning_readiness_level")),
            _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "avg_reasoning_readiness_score")),
        ),
        "evidence_diversity_score": max(
            _context_signal_score(_context_lookup(root, "packet_quality", "evidence_diversity")),
            _context_signal_score(_context_lookup(root, "evidence_diversity")),
            _context_signal_score(_context_lookup(root, "optimization", "evidence_diversity")),
            _context_signal_score(_context_lookup(context_packet, "optimization", "evidence_diversity")),
            _scaled_numeric_signal(_mapping_value(optimization_quality_posture, "avg_evidence_diversity_score")),
        ),
        "spawn_worthiness_score": _context_signal_score(
            _context_lookup(root, "orchestration", "spawn_worthiness")
        ),
        "dependency_depth_score": _context_signal_score(
            _context_lookup(root, "orchestration", "dependency_count")
        ),
        "merge_burden_score": max(
            execution_merge_burden_score,
            _context_signal_score(_context_lookup(root, "parallelism", "merge_burden")),
            _context_signal_score(_context_lookup(root, "orchestration", "merge_burden")),
        ),
        "expected_delegation_value_score": execution_expected_delegation_value_score,
        "odylith_execution_ambiguity_score": execution_ambiguity_score,
        "intent_family": intent_family,
        "intent_mode": intent_mode,
        "intent_critical_path": intent_critical_path,
        "intent_confidence_score": intent_confidence_score,
        "intent_confidence_level": _context_signal_level(intent_confidence_score),
        "intent_explicit": _context_signal_bool(
            _context_lookup(root, "intent", "explicit")
            or _context_lookup(root, "packet_quality", "intent_profile", "explicit")
        ),
        "support_leaf": support_leaf,
        "primary_leaf": primary_leaf,
        "same_prefix_disjoint_exception": same_prefix_disjoint_exception,
        "host_runtime": host_runtime,
        "native_spawn_supported": native_spawn_supported,
        "native_spawn_ready": _context_signal_bool(
            native_spawn_supported
            and (
                _context_lookup(root, "native_spawn_ready")
                or _context_lookup(root, "spawn", "native_ready")
                or _context_lookup(root, "packet_quality", "native_spawn_ready")
            )
        ),
        "route_ready": _context_signal_bool(
            _context_lookup(root, "route_ready")
            or _context_lookup(context_packet, "route", "route_ready")
        ),
        "narrowing_required": narrowing_required,
        "reasoning_bias": reasoning_bias,
        "parallelism_hint": parallelism_hint,
        "routing_confidence_level": routing_confidence,
        "odylith_execution_profile": preferred_execution_profile.value if preferred_execution_profile is not None else "",
        "odylith_execution_model": str(execution_profile.get("model", "")).strip(),
        "odylith_execution_reasoning_effort": str(execution_profile.get("reasoning_effort", "")).strip(),
        "odylith_execution_agent_role": str(execution_profile.get("agent_role", "")).strip(),
        "odylith_execution_source": str(execution_profile.get("source", "")).strip(),
        "odylith_execution_selection_mode": str(execution_profile.get("selection_mode", "")).strip(),
        "odylith_execution_delegate_preference": str(execution_profile.get("delegate_preference", "")).strip(),
        "odylith_execution_host_runtime": host_runtime,
        "odylith_execution_confidence_score": max(
            _context_signal_score(execution_confidence),
            _context_signal_score(_context_lookup(execution_profile, "confidence", "level")),
        ),
        "odylith_execution_confidence_level": _context_signal_level(
            max(
                _context_signal_score(execution_confidence),
                _context_signal_score(_context_lookup(execution_profile, "confidence", "level")),
            )
        ),
        "odylith_execution_route_ready": _context_signal_bool(
            _context_lookup(execution_constraints, "route_ready")
            or _context_lookup(execution_profile, "route_ready")
        ),
        "odylith_execution_narrowing_required": _context_signal_bool(
            _context_lookup(execution_constraints, "narrowing_required")
        ),
        "odylith_execution_spawn_worthiness": _context_signal_score(
            _context_lookup(execution_constraints, "spawn_worthiness")
        ),
        "odylith_execution_merge_burden": _context_signal_score(
            _context_lookup(execution_constraints, "merge_burden")
        ),
        "odylith_execution_reasoning_mode": _normalize_token(
            _context_lookup(execution_constraints, "reasoning_mode")
        ),
        "evidence_consensus": _normalize_token(_context_lookup(root, "evidence_consensus") or ""),
        "group_kind": group_kind,
        "scope_role": _normalize_token(_context_lookup(root, "orchestration", "scope_role") or ""),
        "context_packet_state": context_packet_state,
        "optimization_health_score": optimization_health_score,
        "optimization_within_budget_rate": optimization_within_budget_rate,
        "optimization_route_ready_rate": optimization_route_ready_rate,
        "optimization_native_spawn_ready_rate": optimization_native_spawn_ready_rate,
        "optimization_deep_reasoning_ready_rate": optimization_deep_reasoning_ready_rate,
        "optimization_high_utility_rate": optimization_high_utility_rate,
        "optimization_avg_effective_yield_score": optimization_avg_effective_yield_score,
        "optimization_high_yield_rate": optimization_high_yield_rate,
        "optimization_reliable_high_yield_rate": optimization_reliable_high_yield_rate,
        "optimization_yield_state": optimization_yield_state,
        "optimization_avg_context_density_score": optimization_avg_context_density_score,
        "optimization_avg_reasoning_readiness_score": optimization_avg_reasoning_readiness_score,
        "optimization_avg_evidence_diversity_score": optimization_avg_evidence_diversity_score,
        "optimization_delegated_lane_rate": optimization_delegated_lane_rate,
        "optimization_hold_local_rate": optimization_hold_local_rate,
        "optimization_runtime_backed_execution_rate": optimization_runtime_backed_execution_rate,
        "optimization_high_execution_confidence_rate": optimization_high_execution_confidence_rate,
        "optimization_explicit_intent_rate": optimization_explicit_intent_rate,
        "optimization_packet_alignment_rate": optimization_packet_alignment_rate,
        "optimization_reliable_packet_alignment_rate": optimization_reliable_packet_alignment_rate,
        "optimization_packet_alignment_state": optimization_packet_alignment_state,
        "optimization_latency_pressure_score": optimization_latency_pressure_score,
        "evaluation_benchmark_satisfaction_rate": _normalized_rate(
            evaluation_packet_posture.get("benchmark_satisfaction_rate")
        ),
        "evaluation_router_acceptance_rate": _normalized_rate(
            evaluation_router_posture.get("acceptance_rate")
        ),
        "evaluation_router_failure_rate": _normalized_rate(
            evaluation_router_posture.get("failure_rate")
        ),
        "evaluation_router_escalation_rate": _normalized_rate(
            evaluation_router_posture.get("escalation_rate")
        ),
        "evaluation_orchestration_token_efficiency_rate": _normalized_rate(
            evaluation_orchestration_posture.get("token_efficiency_rate")
        ),
        "evaluation_orchestration_parallel_failure_rate": _normalized_rate(
            evaluation_orchestration_posture.get("parallel_failure_rate")
        ),
        "evaluation_decision_quality_score": _normalized_rate(
            evaluation_decision_quality.get("aggregate_score")
        ),
        "evaluation_decision_quality_state": _normalize_token(
            evaluation_decision_quality.get("state")
        ),
        "evaluation_decision_quality_confidence_score": _clamp_score(
            evaluation_decision_quality.get("confidence", {}).get("score")
            if isinstance(evaluation_decision_quality.get("confidence"), Mapping)
            else 0
        ),
        "evaluation_closeout_observation_rate": _normalized_rate(
            evaluation_decision_quality.get("closeout_observation_rate")
            or (
                evaluation_decision_quality.get("confidence", {}).get("closeout_observation_rate")
                if isinstance(evaluation_decision_quality.get("confidence"), Mapping)
                else 0.0
            )
        ),
        "evaluation_delegation_regret_rate": _normalized_rate(
            evaluation_decision_quality.get("delegation_regret_rate")
            or evaluation_orchestration_posture.get("delegation_regret_rate")
        ),
        "evaluation_clean_closeout_rate": _normalized_rate(
            evaluation_decision_quality.get("clean_closeout_rate")
            or evaluation_orchestration_posture.get("clean_closeout_rate")
        ),
        "evaluation_followup_churn_rate": _normalized_rate(
            evaluation_decision_quality.get("followup_churn_rate")
            or evaluation_orchestration_posture.get("followup_churn_rate")
        ),
        "evaluation_merge_calibration_rate": _normalized_rate(
            evaluation_decision_quality.get("merge_burden_calibration_rate")
        ),
        "evaluation_merge_underestimate_rate": _normalized_rate(
            evaluation_decision_quality.get("merge_burden_underestimate_rate")
        ),
        "evaluation_validation_calibration_rate": _normalized_rate(
            evaluation_decision_quality.get("validation_pressure_calibration_rate")
        ),
        "evaluation_validation_underestimate_rate": _normalized_rate(
            evaluation_decision_quality.get("validation_pressure_underestimate_rate")
        ),
        "evaluation_delegation_value_calibration_rate": _normalized_rate(
            evaluation_decision_quality.get("delegation_value_calibration_rate")
        ),
        "evaluation_delegation_overreach_rate": _normalized_rate(
            evaluation_decision_quality.get("delegation_overreach_rate")
        ),
        "evaluation_learning_state": _normalize_token(
            evaluation_trend_posture.get("learning_state")
            or optimization_learning_loop.get("state")
        ),
        "evaluation_control_depth": _normalize_token(evaluation_control_posture.get("depth")),
        "evaluation_control_delegation": _normalize_token(evaluation_control_posture.get("delegation")),
        "evaluation_control_parallelism": _normalize_token(evaluation_control_posture.get("parallelism")),
        "evaluation_control_packet_strategy": _normalize_token(
            evaluation_control_posture.get("packet_strategy")
        ),
        "evaluation_freshness_bucket": _normalize_token(
            evaluation_overall_freshness.get("bucket")
        ),
        "evaluation_evidence_strength_score": _context_signal_score(
            evaluation_evidence_strength.get("score")
        ),
        "evaluation_evidence_strength_level": _normalize_token(
            evaluation_evidence_strength.get("level")
        ),
        "control_advisory_state": _normalize_token(
            control_advisories.get("state")
            or optimization_learning_loop.get("state")
        ),
        "control_advisory_confidence_score": max(
            _context_signal_score(advisory_confidence),
            _context_signal_score(_context_lookup(control_advisories, "confidence", "level")),
        ),
        "control_advisory_confidence_level": _context_signal_level(
            max(
                _context_signal_score(advisory_confidence),
                _context_signal_score(_context_lookup(control_advisories, "confidence", "level")),
            )
        ),
        "control_advisory_reasoning_mode": _normalize_token(control_advisories.get("reasoning_mode")),
        "control_advisory_depth": _normalize_token(control_advisories.get("depth")),
        "control_advisory_delegation": _normalize_token(control_advisories.get("delegation")),
        "control_advisory_parallelism": _normalize_token(control_advisories.get("parallelism")),
        "control_advisory_packet_strategy": _normalize_token(control_advisories.get("packet_strategy")),
        "control_advisory_budget_mode": _normalize_token(control_advisories.get("budget_mode")),
        "control_advisory_retrieval_focus": _normalize_token(control_advisories.get("retrieval_focus")),
        "control_advisory_speed_mode": _normalize_token(control_advisories.get("speed_mode")),
        "control_advisory_freshness_bucket": _normalize_token(advisory_freshness.get("bucket")),
        "control_advisory_evidence_strength_score": _context_signal_score(
            advisory_evidence_strength.get("score")
        ),
        "control_advisory_evidence_strength_level": _normalize_token(
            advisory_evidence_strength.get("level")
        ),
        "control_advisory_sample_balance": _normalize_token(
            advisory_evidence_strength.get("sample_balance")
        ),
        "control_advisory_signal_conflict": _context_signal_bool(
            control_advisories.get("signal_conflict")
            or advisory_evidence_strength.get("signal_conflict")
            or evaluation_trend_posture.get("signal_conflict")
        ),
        "control_advisory_focus_areas": _normalize_list(control_advisories.get("focus_areas"))[:4],
        "control_advisory_regressions": _normalize_list(control_advisories.get("regressions"))[:4],
        "packet_strategy": _normalize_token(
            _context_lookup(root, "optimization", "packet_strategy")
            or _context_lookup(root, "routing_handoff", "optimization", "packet_strategy")
            or _context_lookup(root, "adaptive_packet_profile", "packet_strategy")
        ),
        "budget_mode": _normalize_token(
            _context_lookup(root, "optimization", "budget_mode")
            or _context_lookup(root, "routing_handoff", "optimization", "budget_mode")
            or _context_lookup(root, "adaptive_packet_profile", "budget_mode")
        ),
        "retrieval_focus": _normalize_token(
            _context_lookup(root, "optimization", "retrieval_focus")
            or _context_lookup(root, "routing_handoff", "optimization", "retrieval_focus")
            or _context_lookup(root, "adaptive_packet_profile", "retrieval_focus")
        ),
        "speed_mode": _normalize_token(
            _context_lookup(root, "optimization", "speed_mode")
            or _context_lookup(root, "routing_handoff", "optimization", "speed_mode")
            or _context_lookup(root, "adaptive_packet_profile", "speed_mode")
        ),
        "packet_reliability": _normalize_token(
            _context_lookup(root, "optimization", "reliability")
            or _context_lookup(root, "routing_handoff", "optimization", "reliability")
            or _context_lookup(root, "adaptive_packet_profile", "reliability")
        ),
        "selection_bias": _normalize_token(
            _context_lookup(root, "optimization", "selection_bias")
            or _context_lookup(root, "routing_handoff", "optimization", "selection_bias")
            or _context_lookup(root, "adaptive_packet_profile", "selection_bias")
        ),
        "evaluation_regression_count": len(
            [
                token
                for token in optimization_evaluation_posture.get("regressions", [])
                if _normalize_string(token)
            ]
        )
        if isinstance(optimization_evaluation_posture.get("regressions"), list)
        else 0,
        "recommended_command_count": len(recommended_commands),
        "strict_gate_command_count": strict_gate_command_count,
        "plan_binding_required": plan_binding_required,
        "governed_surface_sync_required": governed_surface_sync_required,
        "touched_workstream_count": touched_workstream_count,
        "touched_component_count": touched_component_count,
        "linked_bug_count": linked_bug_count,
        "required_diagram_count": required_diagram_count,
        "closeout_doc_count": closeout_doc_count,
        "workstream_state_action_count": workstream_state_action_count,
        "impacted_surface_count": impacted_surface_count,
        "governance_reason_count": governance_reason_count,
        "governance_closeout_score": governance_closeout_score,
        "bounded_governance_delegate_candidate": bounded_governance_delegate_candidate,
        "provenance_score": provenance_score,
        "contract_count": contract_count,
        "redacted_sensitive_count": max(
            _context_signal_score(_context_lookup(provenance, "redacted_sensitive_count")),
            _context_signal_score(_context_lookup(provenance_summary, "redacted_sensitive_count")),
        ),
        "execution_engine_present": execution_engine_present,
        "execution_engine_outcome": execution_engine_outcome,
        "execution_engine_requires_reanchor": execution_engine_requires_reanchor,
        "execution_engine_mode": execution_engine_mode,
        "execution_engine_next_move": execution_engine_next_move,
        "execution_engine_current_phase": execution_engine_current_phase,
        "execution_engine_last_successful_phase": execution_engine_last_successful_phase,
        "execution_engine_blocker": execution_engine_blocker,
        "execution_engine_closure": execution_engine_closure,
        "execution_engine_wait_status": execution_engine_wait_status,
        "execution_engine_wait_detail": execution_engine_wait_detail,
        "execution_engine_resume_token": execution_engine_resume_token,
        "execution_engine_validation_archetype": execution_engine_validation_archetype,
        "execution_engine_validation_minimum_pass_count": execution_engine_validation_minimum_pass_count,
        "execution_engine_validation_derived_from": execution_engine_validation_derived_from,
        "execution_engine_contradiction_count": execution_engine_contradiction_count,
        "execution_engine_history_rule_count": execution_engine_history_rule_count,
        "execution_engine_history_rule_hits": execution_engine_history_rule_hits,
        "execution_engine_pressure_signals": execution_engine_pressure_signals,
        "execution_engine_nearby_denial_actions": execution_engine_nearby_denial_actions,
        "execution_engine_event_count": execution_engine_event_count,
        "execution_engine_authoritative_lane": execution_engine_authoritative_lane,
        "execution_engine_host_family": execution_engine_host_family,
        "execution_engine_model_family": execution_engine_model_family,
        "execution_engine_host_supports_native_spawn": execution_engine_host_supports_native_spawn,
        "execution_engine_component_id": execution_engine_component_id,
        "execution_engine_canonical_component_id": execution_engine_canonical_component_id,
        "execution_engine_identity_status": execution_engine_identity_status,
        "execution_engine_target_component_id": execution_engine_target_component_id,
        "execution_engine_target_component_ids": execution_engine_target_component_ids,
        "execution_engine_target_component_status": execution_engine_target_component_status,
        "execution_engine_snapshot_reuse_status": execution_engine_snapshot_reuse_status,
        "execution_engine_target_lane": execution_engine_target_lane,
        "execution_engine_has_writable_targets": execution_engine_has_writable_targets,
        "execution_engine_requires_more_consumer_context": execution_engine_requires_more_consumer_context,
        "execution_engine_consumer_failover": execution_engine_consumer_failover,
        "execution_engine_commentary_mode": execution_engine_commentary_mode,
        "execution_engine_suppress_routing_receipts": execution_engine_suppress_routing_receipts,
        "execution_engine_surface_fast_lane": execution_engine_surface_fast_lane,
        "execution_engine_runtime_invalidated_by_step": execution_engine_runtime_invalidated_by_step,
        "odylith_fix_mode": odylith_fix_mode,
        "allow_odylith_mutations": allow_odylith_mutations,
        "odylith_write_protected_roots": odylith_write_protected_roots,
        "consumer_odylith_write_blocked": consumer_odylith_write_blocked,
    }


def assess_request(request: RouteRequest) -> TaskAssessment:
    host = _host()
    _normalize_string = host._normalize_string
    _normalize_list = host._normalize_list
    infer_prompt_semantics = host.infer_prompt_semantics
    infer_explicit_paths = host.infer_explicit_paths
    surface_prefixes_for_path = host.surface_prefixes_for_path
    _infer_phase_tokens = host._infer_phase_tokens
    _contains_any = host._contains_any
    _keyword_score = host._keyword_score
    _clamp_score = host._clamp_score
    _normalized_rate = host._normalized_rate
    _normalize_token = host._normalize_token
    _router_profile_from_token = host._router_profile_from_token
    _classify_task_family = host._classify_task_family
    TaskAssessment = host.TaskAssessment
    RouterProfile = host.RouterProfile
    _FEATURE_KEYWORDS = host._FEATURE_KEYWORDS
    _WRITE_KEYWORDS = host._WRITE_KEYWORDS
    _AMBIGUITY_KEYWORDS = host._AMBIGUITY_KEYWORDS
    _RISK_KEYWORDS = host._RISK_KEYWORDS
    _COORDINATION_KEYWORDS = host._COORDINATION_KEYWORDS
    _REVERSIBILITY_KEYWORDS = host._REVERSIBILITY_KEYWORDS
    _MECHANICAL_KEYWORDS = host._MECHANICAL_KEYWORDS
    _VALIDATION_KEYWORDS = host._VALIDATION_KEYWORDS
    _LATENCY_KEYWORDS = host._LATENCY_KEYWORDS
    _DEPTH_KEYWORDS = host._DEPTH_KEYWORDS
    _RUNTIME_EARNED_DEPTH_SELECTION_MODES = host._RUNTIME_EARNED_DEPTH_SELECTION_MODES

    prompt = _normalize_string(request.prompt)
    criteria = " ".join(_normalize_list(request.acceptance_criteria))
    validation_commands = _normalize_list(request.validation_commands)
    text = f"{prompt} {criteria}".strip().lower()
    semantic_signals = infer_prompt_semantics(prompt, request.acceptance_criteria)
    context_signal_summary = _context_signal_summary(request)
    has_structured_handoff = any(
        (
            context_signal_summary["support_leaf"],
            context_signal_summary["primary_leaf"],
            context_signal_summary["route_ready"],
            bool(context_signal_summary["routing_confidence_level"]),
            bool(context_signal_summary["parallelism_hint"]),
            bool(context_signal_summary["scope_role"]),
            context_signal_summary["spawn_worthiness_score"] > 0,
            context_signal_summary["merge_burden_score"] > 0,
            context_signal_summary["dependency_depth_score"] > 0,
        )
    )
    explicit_paths = [*request.allowed_paths, *infer_explicit_paths(f"{prompt} {criteria}".strip())]
    explicit_path_count = len({token for token in explicit_paths if token})
    explicit_prefixes = {
        prefix
        for path in explicit_paths
        for prefix in surface_prefixes_for_path(path)
        if prefix
    }
    explicit_component_count = len({token for token in request.components if token})
    explicit_workstream_count = len({token for token in request.workstreams if token})
    feature_reasons: dict[str, list[str]] = {}

    phase_tokens = _infer_phase_tokens(text, task_kind=request.task_kind, phase=request.phase)
    mixed_phase = len(phase_tokens.intersection({"implementation", "analysis", "review", "planning"})) >= 2
    bounded_scope_hits = len(semantic_signals.get("bounded_scope", []))
    open_ended_scope_hits = len(semantic_signals.get("open_ended_scope", []))
    diagnostic_hits = len(semantic_signals.get("diagnostic", []))
    synthesis_required = bool(semantic_signals.get("synthesis_required"))
    docs_surface_prefixes = {"docs", "skills", "agents-guidelines"}
    docs_only_scope = bool(explicit_prefixes.intersection(docs_surface_prefixes)) and explicit_prefixes.difference(
        {"odylith"}
    ).issubset(docs_surface_prefixes)
    tests_only_scope = bool(explicit_prefixes) and explicit_prefixes.issubset({"tests", "mocks"})
    governance_only_scope = "odylith" in explicit_prefixes and explicit_prefixes.issubset(
        {"odylith", "docs", "skills", "agents-guidelines"}
    )
    high_risk_prefix_scope = bool(explicit_prefixes.intersection({"infra", "contracts"}))

    task_kind = request.task_kind or ("feature_implementation" if _contains_any(text, _FEATURE_KEYWORDS) else "")
    if not task_kind:
        if "implementation" in phase_tokens and "review" not in phase_tokens and "planning" not in phase_tokens:
            task_kind = "implementation"
        elif "planning" in phase_tokens:
            task_kind = "planning"
        elif "review" in phase_tokens:
            task_kind = "review"
        elif "analysis" in phase_tokens:
            task_kind = "analysis"
        else:
            task_kind = "analysis"

    feature_implementation = task_kind == "feature_implementation" or _contains_any(text, _FEATURE_KEYWORDS)
    analysis_only_hint = request.task_kind in {"analysis", "review"} and not request.needs_write
    needs_write = bool(
        request.needs_write
        or (
            not analysis_only_hint
            and ("implementation" in phase_tokens or _contains_any(text, _WRITE_KEYWORDS))
        )
    )
    if analysis_only_hint:
        phase_tokens.discard("implementation")
    if (
        request.task_kind in {"analysis", "review"}
        and not needs_write
        and phase_tokens.issubset({"analysis", "review", "planning"})
        and not _contains_any(text, ("coordinate", "rollout", "merge", "handoff", "integrate"))
    ):
        mixed_phase = False
    ambiguity = _keyword_score(text, _AMBIGUITY_KEYWORDS)
    if needs_write and not request.acceptance_criteria:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("write task lacks explicit acceptance criteria")
    if "?" in prompt:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("prompt is framed as an open question")
    if open_ended_scope_hits >= 2:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("prompt uses open-ended architecture or redesign language")

    blast_radius = _keyword_score(text, _RISK_KEYWORDS)
    if explicit_path_count >= 4:
        blast_radius = _clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("many explicit paths broaden the slice")
    if explicit_component_count >= 2 or explicit_workstream_count >= 2:
        blast_radius = _clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("multiple components or workstreams widen the blast radius")
    if docs_only_scope or tests_only_scope:
        blast_radius = _clamp_score(blast_radius - 1)
        feature_reasons.setdefault("blast_radius", []).append("owned paths stay in docs/tests scope, which caps runtime blast radius")
    if high_risk_prefix_scope:
        blast_radius = _clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("infra/contracts ownership raises blast radius")
    if (docs_only_scope or tests_only_scope) and not request.correctness_critical:
        blast_radius = min(blast_radius, 2)
        feature_reasons.setdefault("blast_radius", []).append("docs/tests-only scope prevents runtime-risk nouns from forcing critical escalation")

    context_breadth = _clamp_score(
        (1 if explicit_path_count >= 2 else 0)
        + (1 if explicit_path_count >= 4 else 0)
        + (1 if explicit_component_count >= 2 else 0)
        + (1 if explicit_workstream_count >= 2 else 0)
        + (1 if len(request.acceptance_criteria) >= 3 else 0)
        + (1 if mixed_phase else 0)
        + (1 if _contains_any(text, ("cross-file", "cross repo", "repo-wide", "multiple files")) else 0)
        + (1 if open_ended_scope_hits >= 2 else 0)
    )
    if context_breadth:
        feature_reasons.setdefault("context_breadth", []).append("slice spans multiple paths, phases, or acceptance targets")

    coordination_cost = _keyword_score(text, _COORDINATION_KEYWORDS)
    if mixed_phase:
        coordination_cost = _clamp_score(coordination_cost + 2)
        feature_reasons.setdefault("coordination_cost", []).append("prompt mixes planning/review/integration phases")
    if explicit_path_count >= 5:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("many touched paths imply coordination overhead")
    if explicit_component_count >= 2 or explicit_workstream_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("multiple components or workstreams increase coordination cost")
    if request.requires_multi_agent_adjudication:
        coordination_cost = _clamp_score(coordination_cost + 2)
        feature_reasons.setdefault("coordination_cost", []).append("request explicitly needs multi-agent adjudication")
    if open_ended_scope_hits >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("open-ended scope language increases coordination risk")
    if governance_only_scope and request.needs_write:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("governed artifact updates often require main-thread integration")

    reversibility_risk = _keyword_score(text, _REVERSIBILITY_KEYWORDS)
    if request.correctness_critical:
        reversibility_risk = _clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("reversibility_risk", []).append("request explicitly marks correctness as critical")
    if docs_only_scope or tests_only_scope:
        reversibility_risk = _clamp_score(reversibility_risk - 1)
        feature_reasons.setdefault("reversibility_risk", []).append("docs/tests-only ownership lowers reversibility risk")
    if high_risk_prefix_scope:
        reversibility_risk = _clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("reversibility_risk", []).append("infra/contracts ownership raises reversibility risk")
    if (docs_only_scope or tests_only_scope) and not request.correctness_critical:
        reversibility_risk = min(reversibility_risk, 2)
        feature_reasons.setdefault("reversibility_risk", []).append(
            "docs/tests-only scope prevents runtime-risk nouns from forcing critical escalation"
        )

    mechanicalness = _keyword_score(text, _MECHANICAL_KEYWORDS)
    if explicit_path_count == 1:
        mechanicalness = _clamp_score(mechanicalness + 1)
        feature_reasons.setdefault("mechanicalness", []).append("single explicit path suggests a bounded slice")
    if bounded_scope_hits and explicit_path_count <= 3:
        mechanicalness = _clamp_score(mechanicalness + 1)
        feature_reasons.setdefault("mechanicalness", []).append("prompt uses bounded-scope language")
    mechanicalness = _clamp_score(
        mechanicalness
        - (1 if ambiguity >= 3 else 0)
        - (1 if blast_radius >= 3 else 0)
        - (1 if feature_implementation else 0)
        - (1 if open_ended_scope_hits >= 2 else 0)
    )

    write_scope_clarity = host._SCORE_MAX if not needs_write else 0
    if needs_write:
        if explicit_path_count >= 1:
            write_scope_clarity += 2
        if explicit_path_count >= 3:
            write_scope_clarity += 1
        if request.acceptance_criteria:
            write_scope_clarity += 1
        if bounded_scope_hits:
            write_scope_clarity += 1
        if _contains_any(text, ("repo-wide", "broad refactor", "sweeping")):
            write_scope_clarity -= 2
        if mixed_phase:
            write_scope_clarity -= 1
        if open_ended_scope_hits >= 2:
            write_scope_clarity -= 1
        write_scope_clarity = _clamp_score(write_scope_clarity)
    if write_scope_clarity < 2 and needs_write:
        feature_reasons.setdefault("write_scope_clarity", []).append("write ownership is weak or unbounded")

    acceptance_signal_count = sum(1 for token in _VALIDATION_KEYWORDS if token in criteria.lower())
    acceptance_clarity = _clamp_score(
        (1 if request.acceptance_criteria else 0)
        + (1 if len(request.acceptance_criteria) >= 2 else 0)
        + (1 if len(request.acceptance_criteria) >= 4 else 0)
        + (1 if acceptance_signal_count >= 1 else 0)
    )
    if needs_write and acceptance_clarity <= 1:
        feature_reasons.setdefault("acceptance_clarity", []).append("write slice lacks a strong acceptance contract")

    artifact_specificity = _clamp_score(
        (1 if explicit_path_count or request.artifacts else 0)
        + (1 if 1 <= explicit_path_count <= 3 else 0)
        + (1 if request.artifacts else 0)
        + (1 if explicit_component_count or explicit_workstream_count else 0)
        + (1 if bounded_scope_hits else 0)
        - (1 if explicit_path_count >= 6 else 0)
        - (1 if open_ended_scope_hits >= 2 else 0)
    )
    if needs_write and artifact_specificity <= 1:
        feature_reasons.setdefault("artifact_specificity", []).append("few explicit artifacts or paths anchor the slice")

    validation_text = " ".join([criteria, *validation_commands]).lower()
    validation_signal_count = sum(1 for token in _VALIDATION_KEYWORDS if token in validation_text)
    validation_clarity = _clamp_score(
        (1 if validation_signal_count >= 1 else 0)
        + (1 if validation_commands else 0)
        + (1 if len(validation_commands) >= 2 or validation_signal_count >= 2 else 0)
        + (
            1
            if any(
                command.startswith(("pytest", "make ", "python -m pytest", "hatch run pytest"))
                for command in validation_commands
            )
            else 0
        )
    )

    latency_pressure = _keyword_score(text, _LATENCY_KEYWORDS)
    if request.latency_sensitive:
        latency_pressure = _clamp_score(latency_pressure + 2)
        feature_reasons.setdefault("latency_pressure", []).append("request explicitly prefers low latency")

    requested_depth = _keyword_score(text, _DEPTH_KEYWORDS)
    accuracy_bias = 0
    if request.accuracy_preference in {"accuracy", "max_accuracy", "maximum_accuracy"}:
        accuracy_bias += 1
    if request.accuracy_preference in {"max_accuracy", "maximum_accuracy"}:
        requested_depth = _clamp_score(requested_depth + 2)
        accuracy_bias += 1
    if feature_implementation:
        accuracy_bias += 2
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "feature implementation leans toward stronger coding-optimized or GPT-5.4 profiles"
        )
    elif task_kind == "implementation":
        accuracy_bias += 1
    if request.correctness_critical:
        accuracy_bias += 1
        requested_depth = _clamp_score(requested_depth + 1)
    if diagnostic_hits >= 2:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append("diagnostic language suggests deeper synthesis or failure analysis")
    if synthesis_required:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append("prompt requires synthesis instead of isolated lookups")
    if request.accuracy_preference in {"max_accuracy", "maximum_accuracy"} and needs_write:
        accuracy_bias += 1
        feature_reasons.setdefault("requested_depth", []).append("operator explicitly prefers maximum accuracy for this write slice")

    base_confidence_boost = False
    if context_signal_summary["grounding_score"] >= 3 and context_signal_summary["evidence_quality_score"] >= 3:
        ambiguity = _clamp_score(ambiguity - 1)
        feature_reasons.setdefault("grounding", []).append(
            "routing_handoff reported grounded high-quality evidence, so ambiguity was reduced"
        )
    if context_signal_summary["actionability_score"] >= 3:
        if needs_write:
            write_scope_clarity = _clamp_score(write_scope_clarity + 1)
            acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported actionable bounded context for this slice"
        )
    if context_signal_summary["validation_burden_score"] >= 3:
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "routing_handoff reported a heavier validation burden that merits deeper reasoning"
        )
    if context_signal_summary["coordination_score"] >= 3:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append(
            "routing_handoff reported higher coordination or merge burden than the prompt alone exposed"
        )
    if context_signal_summary["risk_score"] >= 3:
        blast_radius = _clamp_score(blast_radius + 1)
        reversibility_risk = _clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported elevated correctness or change risk"
        )
    if context_signal_summary["utility_score"] >= 3:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported a high-value retained context set for this slice"
        )
    if context_signal_summary["token_efficiency_score"] >= 3:
        latency_pressure = _clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported strong evidence value per retained token"
        )
    if context_signal_summary["optimization_health_score"] >= 3:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime optimization posture shows the retained packet is compact and healthy"
        )
    history_budget_reliable = bool(
        context_signal_summary["optimization_within_budget_rate"] >= 0.75
        and context_signal_summary["optimization_high_utility_rate"] >= 0.5
    )
    history_execution_reliable = bool(
        context_signal_summary["optimization_route_ready_rate"] >= 0.5
        and context_signal_summary["optimization_native_spawn_ready_rate"] >= 0.5
        and context_signal_summary["optimization_runtime_backed_execution_rate"] >= 0.5
    )
    history_deep_reasoning_reliable = bool(
        context_signal_summary["optimization_deep_reasoning_ready_rate"] >= 0.5
        and context_signal_summary["optimization_avg_context_density_score"] >= 2.0
        and context_signal_summary["optimization_avg_reasoning_readiness_score"] >= 2.0
    )
    history_prefers_local = bool(
        context_signal_summary["optimization_hold_local_rate"] >= 0.5
        and context_signal_summary["optimization_hold_local_rate"]
        > context_signal_summary["optimization_delegated_lane_rate"]
    )
    history_effective_yield_score = max(
        0.0,
        min(1.0, float(context_signal_summary["optimization_avg_effective_yield_score"] or 0.0)),
    )
    history_high_yield_rate = _normalized_rate(context_signal_summary["optimization_high_yield_rate"])
    history_reliable_high_yield_rate = _normalized_rate(
        context_signal_summary["optimization_reliable_high_yield_rate"]
    )
    history_yield_state = _normalize_token(context_signal_summary["optimization_yield_state"])
    control_advisory_state = context_signal_summary["control_advisory_state"]
    control_advisory_confidence_score = context_signal_summary["control_advisory_confidence_score"]
    control_advisory_reasoning_mode = context_signal_summary["control_advisory_reasoning_mode"]
    control_advisory_depth = context_signal_summary["control_advisory_depth"]
    control_advisory_delegation = context_signal_summary["control_advisory_delegation"]
    control_advisory_parallelism = context_signal_summary["control_advisory_parallelism"]
    control_advisory_packet_strategy = context_signal_summary["control_advisory_packet_strategy"]
    control_advisory_budget_mode = context_signal_summary["control_advisory_budget_mode"]
    control_advisory_retrieval_focus = context_signal_summary["control_advisory_retrieval_focus"]
    control_advisory_speed_mode = context_signal_summary["control_advisory_speed_mode"]
    packet_strategy = context_signal_summary["packet_strategy"]
    budget_mode = context_signal_summary["budget_mode"]
    retrieval_focus = context_signal_summary["retrieval_focus"]
    speed_mode = context_signal_summary["speed_mode"]
    packet_reliability = context_signal_summary["packet_reliability"]
    selection_bias = context_signal_summary["selection_bias"]
    control_advisory_freshness_bucket = context_signal_summary["control_advisory_freshness_bucket"]
    control_advisory_evidence_strength_score = context_signal_summary["control_advisory_evidence_strength_score"]
    control_advisory_signal_conflict = bool(context_signal_summary["control_advisory_signal_conflict"])
    control_advisory_sample_balance = context_signal_summary["control_advisory_sample_balance"]
    control_advisory_present = bool(
        control_advisory_state
        or control_advisory_reasoning_mode
        or control_advisory_depth
        or control_advisory_delegation
        or control_advisory_parallelism
        or control_advisory_packet_strategy
        or control_advisory_budget_mode
        or control_advisory_retrieval_focus
        or control_advisory_speed_mode
        or control_advisory_freshness_bucket
        or control_advisory_confidence_score > 0
        or control_advisory_evidence_strength_score > 0
        or control_advisory_signal_conflict
        or control_advisory_sample_balance not in {"", "none"}
    )
    control_advisory_reliable = bool(
        control_advisory_present
        and control_advisory_confidence_score >= 3
        and control_advisory_evidence_strength_score >= 3
        and control_advisory_freshness_bucket in {"fresh", "recent"}
        and not control_advisory_signal_conflict
    )
    control_advisory_guarded = bool(
        control_advisory_present
        and (
            control_advisory_freshness_bucket in {"aging", "stale"}
            or control_advisory_evidence_strength_score <= 1
            or control_advisory_signal_conflict
            or control_advisory_sample_balance in {"thin", "none"}
        )
    )
    packet_profile_present = bool(
        packet_strategy
        or budget_mode
        or retrieval_focus
        or speed_mode
        or packet_reliability
        or selection_bias
    )
    packet_profile_reliable = packet_reliability == "reliable"
    packet_profile_guarded = packet_reliability == "guarded"
    if control_advisory_guarded:
        coordination_cost = _clamp_score(coordination_cost + 1)
        if not request.correctness_critical and requested_depth >= 2:
            requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are fresh-evidence guarded, so the router reduced trust in historical promotion signals until newer or better-balanced outcomes accumulate"
        )
    elif packet_profile_guarded and not control_advisory_present:
        coordination_cost = _clamp_score(coordination_cost + 1)
        if not request.correctness_critical and requested_depth >= 2:
            requested_depth = _clamp_score(requested_depth - 1)
        if accuracy_bias >= 2:
            accuracy_bias = _clamp_score(accuracy_bias - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet was assembled under guarded reliability, so the router stayed conservative until fresher packet evidence lands"
        )
    if history_budget_reliable:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "optimization history shows recent packets stay within budget while retaining useful evidence"
        )
    if history_execution_reliable:
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "optimization history shows recent route-ready slices also stay native-spawn-ready under runtime-backed control"
        )
    if (
        history_deep_reasoning_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["reasoning_readiness_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "optimization history shows deeper delegated reasoning stays grounded, budget-safe, and runtime-backed on similar slices"
        )
    elif (
        not request.correctness_critical
        and requested_depth >= 3
        and 0.0 < context_signal_summary["optimization_deep_reasoning_ready_rate"] < 0.5
        and context_signal_summary["optimization_within_budget_rate"] < 0.5
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "recent optimization history shows deeper delegated reasoning still overruns budget or lacks readiness on similar slices"
        )
    if history_prefers_local and (context_signal_summary["narrowing_required"] or not context_signal_summary["route_ready"]):
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent optimization history still trends toward hold-local execution while narrowing remains unresolved"
        )
    if (
        context_signal_summary["optimization_packet_alignment_state"] == "drifting"
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        accuracy_bias = _clamp_score(accuracy_bias - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent packetizer alignment is drifting from the measured advisory loop, so the router reduced depth until packet shaping stabilizes again"
        )
    evaluation_depth_promote = context_signal_summary["evaluation_control_depth"] == "promote_when_grounded"
    evaluation_narrow_first = context_signal_summary["evaluation_control_depth"] == "narrow_first"
    evaluation_hold_local_bias = context_signal_summary["evaluation_control_delegation"] == "hold_local_bias"
    evaluation_parallel_guarded = context_signal_summary["evaluation_control_parallelism"] == "guarded"
    evaluation_precision_first = context_signal_summary["evaluation_control_packet_strategy"] == "precision_first"
    evaluation_decision_quality_score = _normalized_rate(
        context_signal_summary["evaluation_decision_quality_score"]
    )
    evaluation_decision_quality_state = _normalize_token(
        context_signal_summary["evaluation_decision_quality_state"]
    )
    evaluation_decision_quality_confidence = _clamp_score(
        context_signal_summary["evaluation_decision_quality_confidence_score"]
    )
    evaluation_closeout_observation_rate = _normalized_rate(
        context_signal_summary["evaluation_closeout_observation_rate"]
    )
    evaluation_delegation_regret_rate = _normalized_rate(
        context_signal_summary["evaluation_delegation_regret_rate"]
    )
    evaluation_followup_churn_rate = _normalized_rate(
        context_signal_summary["evaluation_followup_churn_rate"]
    )
    evaluation_merge_underestimate_rate = _normalized_rate(
        context_signal_summary["evaluation_merge_underestimate_rate"]
    )
    evaluation_validation_underestimate_rate = _normalized_rate(
        context_signal_summary["evaluation_validation_underestimate_rate"]
    )
    decision_quality_reliable = bool(
        evaluation_decision_quality_confidence >= 3
        and evaluation_closeout_observation_rate >= 0.34
        and evaluation_decision_quality_state not in {"bootstrap", "insufficient"}
    )
    decision_quality_fragile = bool(
        decision_quality_reliable
        and (
            evaluation_decision_quality_state == "fragile"
            or evaluation_decision_quality_score < 0.55
        )
    )
    decision_quality_trusted = bool(
        decision_quality_reliable
        and evaluation_decision_quality_state == "trusted"
        and evaluation_decision_quality_score >= 0.72
    )
    if (
        control_advisory_depth == "promote_when_grounded"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and not context_signal_summary["narrowing_required"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently endorse deeper reasoning on grounded route-ready slices"
        )
    if control_advisory_depth == "narrow_first" and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently prefer narrow-first execution because recent outcomes are still unstable"
        )
    if (
        decision_quality_reliable
        and evaluation_validation_underestimate_rate >= 0.25
        and not request.correctness_critical
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is still underpredicting validation pressure on recent delegated slices, so the router tightened depth until validation calibration improves"
        )
    elif (
        not decision_quality_reliable
        and (
            evaluation_delegation_regret_rate >= 0.25
            or evaluation_followup_churn_rate >= 0.25
            or evaluation_merge_underestimate_rate >= 0.2
            or evaluation_validation_underestimate_rate >= 0.25
        )
    ):
        feature_reasons.setdefault("context_signals", []).append(
            "decision-quality outcome evidence is still thin or only partially closed out, so the router kept regret and calibration metrics advisory-only for now"
        )
    if (
        control_advisory_reasoning_mode == "earn_depth"
        and control_advisory_reliable
        and context_signal_summary["grounding_score"] >= 3
        and context_signal_summary["context_density_score"] >= 3
        and context_signal_summary["reasoning_readiness_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "Control advisories say deeper reasoning has to be earned, and this slice currently meets that bar"
        )
    elif control_advisory_reasoning_mode == "guarded_narrowing" and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories still want guarded narrowing before spending extra depth"
        )
    if (
        control_advisory_delegation == "hold_local_bias"
        and (context_signal_summary["narrowing_required"] or ambiguity >= 2)
    ):
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently bias toward hold-local or tighter delegated slices"
        )
    elif (
        control_advisory_delegation == "runtime_backed_delegate"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["expected_delegation_value_score"] >= 3
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently trust runtime-backed delegation on slices with strong delegation value"
        )
    if (
        decision_quality_reliable
        and (
            evaluation_delegation_regret_rate >= 0.25
            or evaluation_followup_churn_rate >= 0.25
        )
    ):
        coordination_cost = _clamp_score(coordination_cost + 1)
        if not request.correctness_critical:
            requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence shows delegation regret or follow-up churn after execution, so the router is biasing toward tighter delegated scope"
        )
    if control_advisory_parallelism == "guarded" and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are guarding parallelism because recent execution still shows merge risk"
        )
    if decision_quality_reliable and evaluation_merge_underestimate_rate >= 0.2 and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is still underpredicting merge burden on recent delegated slices, so the router is staying conservative on fan-out"
        )
    if decision_quality_fragile and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "trusted execution-outcome evidence is currently fragile overall, so the router reduced depth and coordination until closeout quality improves"
        )
    elif (
        decision_quality_trusted
        and context_signal_summary["route_ready"]
        and context_signal_summary["expected_delegation_value_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "trusted recent execution outcomes show delegated slices are closing cleanly, so the router kept the route confident on this grounded slice"
        )
    if control_advisory_packet_strategy == "precision_first" and context_signal_summary["context_density_score"] <= 2:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently prefer precision-first packets over spending depth on shallow evidence cones"
        )
    if (
        control_advisory_budget_mode == "tight"
        and not request.correctness_critical
        and requested_depth >= 2
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        latency_pressure = _clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are in tight-budget mode, so the router reduced early reasoning spend"
        )
    elif (
        control_advisory_budget_mode == "spend_when_grounded"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "Control advisories allow extra depth when the slice is grounded and route-ready"
        )
    if control_advisory_speed_mode == "accelerate_grounded" and control_advisory_reliable and context_signal_summary["route_ready"]:
        latency_pressure = _clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently favor faster execution on grounded slices"
        )
    elif control_advisory_speed_mode == "conserve" and not request.correctness_critical:
        latency_pressure = _clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently conserve spend because recent packets are not paying back extra speed/depth"
        )
    if (
        history_effective_yield_score >= 0.72
        and history_high_yield_rate >= 0.6
        and history_reliable_high_yield_rate >= 0.5
        and context_signal_summary["route_ready"]
        and context_signal_summary["context_density_score"] >= 3
        and context_signal_summary["reasoning_readiness_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("requested_depth", []).append(
            "recent packets are earning strong grounded signal per budget, so the router allowed extra depth on this route-ready slice"
        )
    elif history_yield_state == "wasteful" and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        latency_pressure = _clamp_score(latency_pressure + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent packets are still low-yield for their spend, so the router reduced depth until denser grounded evidence returns"
        )
    if control_advisory_retrieval_focus == "expand_coverage" and artifact_specificity <= 2:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories want broader evidence coverage before the router commits to a narrow delegated slice"
        )
    elif control_advisory_retrieval_focus == "precision_repair" and artifact_specificity <= 2:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories want tighter anchor repair before extra reasoning depth"
        )
    if (
        not control_advisory_present
        and packet_profile_present
        and packet_strategy == "precision_first"
        and context_signal_summary["context_density_score"] <= 2
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained packet is already in precision-first mode, so the router avoided spending extra depth on a still-shallow evidence cone"
        )
    if (
        not control_advisory_reliable
        and budget_mode == "tight"
        and not request.correctness_critical
        and requested_depth >= 2
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        latency_pressure = _clamp_score(latency_pressure + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is already budget-tight, so the router reduced early reasoning spend"
        )
    if not control_advisory_reliable and speed_mode == "conserve" and not request.correctness_critical:
        latency_pressure = _clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is in conserve mode, so the router kept execution spend disciplined"
        )
    elif (
        not control_advisory_guarded
        and speed_mode == "accelerate_grounded"
        and packet_profile_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["grounding_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        latency_pressure = _clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is reliable and accelerate-grounded, so the router allowed faster execution posture"
        )
    if (
        not control_advisory_present
        and retrieval_focus == "expand_coverage"
        and artifact_specificity <= 2
    ):
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained packet still wants broader evidence coverage before the router narrows into a specialized delegated slice"
        )
    if (
        control_advisory_state in {"improving", "stable"}
        and control_advisory_reliable
        and not context_signal_summary["narrowing_required"]
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are confident and stable enough to raise router trust in the current bounded slice"
        )
    if (
        evaluation_depth_promote
        and context_signal_summary["route_ready"]
        and not context_signal_summary["narrowing_required"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is improving and currently endorses deeper reasoning on grounded route-ready slices"
        )
    if evaluation_narrow_first and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence currently prefers narrow-first control because recent benchmark or execution outcomes are not stable enough"
        )
    if evaluation_hold_local_bias and (context_signal_summary["narrowing_required"] or ambiguity >= 2):
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent evaluated delegation outcomes are not yet stable, so the router biased toward hold-local or tighter delegated slices"
        )
    if evaluation_parallel_guarded and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is guarding parallelism because recent orchestration outcomes showed merge or false-parallel regressions"
        )
    if evaluation_precision_first and context_signal_summary["context_density_score"] <= 2:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence currently prefers precision-first packets, so the router avoided spending extra depth on a still-shallow evidence cone"
        )
    if (
        context_signal_summary["evaluation_router_acceptance_rate"] >= 0.7
        and context_signal_summary["evaluation_benchmark_satisfaction_rate"] >= 0.6
        and context_signal_summary["evaluation_learning_state"] == "improving"
    ):
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent benchmark-linked execution outcomes are improving, so the router trusted the current bounded slice more strongly"
        )
    elif (
        context_signal_summary["evaluation_router_failure_rate"] >= 0.35
        or context_signal_summary["evaluation_router_escalation_rate"] >= 0.25
    ) and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        base_confidence_boost = False
        feature_reasons.setdefault("context_signals", []).append(
            "Recent evaluated router outcomes are still unstable, so the router stayed more conservative on first-pass delegation depth"
        )
    if (
        request.latency_sensitive
        and context_signal_summary["optimization_latency_pressure_score"] >= 3
        and not request.correctness_critical
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent timing history is already under latency pressure, so the router avoided spending extra depth early"
        )
    if (
        context_signal_summary["optimization_high_execution_confidence_rate"] >= 0.5
        and context_signal_summary["odylith_execution_confidence_score"] >= 3
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "recent runtime-backed execution recommendations have been consistently high-confidence"
        )
    if context_signal_summary["provenance_score"] >= 2:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime memory contracts carried explicit provenance for the retained evidence set"
        )
    if context_signal_summary["contract_count"] >= 3:
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "multiple typed runtime contracts were available, which reduced interpretation ambiguity"
        )
    if (
        context_signal_summary["bounded_governance_delegate_candidate"]
        and not request.correctness_critical
    ):
        coordination_cost = _clamp_score(coordination_cost - 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        validation_clarity = _clamp_score(validation_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained governance closeout contract kept this bounded slice execution-ready despite the broader packet staying conservative"
        )
    if (
        context_signal_summary["context_packet_state"].startswith("gated_")
        and not context_signal_summary["bounded_governance_delegate_candidate"]
    ):
        ambiguity = _clamp_score(ambiguity + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime context packet remained gated, so the router preserved a narrower posture"
        )
    if context_signal_summary["redacted_sensitive_count"] >= 1:
        feature_reasons.setdefault("context_signals", []).append(
            "runtime contracts already redacted sensitive paths from the retained evidence pack"
        )
    if context_signal_summary["intent_confidence_score"] >= 2:
        intent_family = context_signal_summary["intent_family"]
        if intent_family == "implementation" and needs_write:
            artifact_specificity = _clamp_score(artifact_specificity + 1)
            if context_signal_summary["intent_explicit"]:
                write_scope_clarity = _clamp_score(write_scope_clarity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried an implementation-first intent profile for this bounded write slice"
            )
        elif intent_family == "validation":
            validation_clarity = _clamp_score(validation_clarity + 1)
            requested_depth = _clamp_score(requested_depth + 1)
            accuracy_bias = _clamp_score(accuracy_bias + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "runtime handoff carried a validation-first intent profile for this slice"
            )
        elif intent_family in {"diagnosis", "analysis", "architecture", "review"} and not needs_write:
            requested_depth = _clamp_score(requested_depth + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "runtime handoff carried an analysis-heavy intent profile that benefits from deeper synthesis"
            )
        elif intent_family == "docs" and not request.correctness_critical:
            mechanicalness = _clamp_score(mechanicalness + 1)
            blast_radius = _clamp_score(blast_radius - 1)
            reversibility_risk = _clamp_score(reversibility_risk - 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried a docs-alignment intent profile, so the router treated the slice as more mechanical"
            )
        elif intent_family == "governance" and not request.correctness_critical:
            mechanicalness = _clamp_score(mechanicalness + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried a governance-closeout intent profile for this slice"
                if not context_signal_summary["bounded_governance_delegate_candidate"]
                else "runtime handoff carried an explicit governance closeout contract, so the router treated bounded delegation as execution-ready"
            )
    if context_signal_summary["intent_critical_path"] == "narrow_first":
        ambiguity = _clamp_score(ambiguity + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as narrow-first, so the router stayed conservative"
        )
    elif context_signal_summary["intent_critical_path"] == "implementation_first" and needs_write:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked implementation as the critical path for this slice"
        )
    elif context_signal_summary["intent_critical_path"] == "analysis_first" and not needs_write:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff marked analysis as the critical path for this read-heavy slice"
        )
    elif context_signal_summary["intent_critical_path"] == "docs_after_write" and not request.correctness_critical:
        mechanicalness = _clamp_score(mechanicalness + 1)
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked docs alignment as a post-write follow-up, which favors lighter support routing"
        )
    elif context_signal_summary["intent_critical_path"] == "governance_local":
        if context_signal_summary["bounded_governance_delegate_candidate"]:
            acceptance_clarity = _clamp_score(acceptance_clarity + 1)
            validation_clarity = _clamp_score(validation_clarity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff marked governance closeout as the critical path, but the retained validation and closeout contract was explicit enough to keep bounded delegation safe"
            )
        else:
            coordination_cost = _clamp_score(coordination_cost + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff marked governance closeout as the critical path, so the router preserved coordination margin"
            )
    if context_signal_summary["primary_leaf"]:
        if needs_write:
            write_scope_clarity = _clamp_score(write_scope_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this as a primary implementation leaf with explicit owned paths"
        )
    if context_signal_summary["support_leaf"] and not request.correctness_critical:
        mechanicalness = _clamp_score(mechanicalness + 1)
        blast_radius = _clamp_score(blast_radius - 1)
        reversibility_risk = _clamp_score(reversibility_risk - 1)
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this as a support leaf, so the router downshifted toward lighter support tiers"
        )
    if context_signal_summary["reasoning_bias"] == "deep_validation":
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff requested deep validation reasoning for this bounded slice"
        )
    elif context_signal_summary["reasoning_bias"] == "accuracy_first" and needs_write:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff preferred an accuracy-first reasoning posture for this write slice"
        )
    elif (
        context_signal_summary["reasoning_bias"] == "guarded_narrowing"
        and not context_signal_summary["bounded_governance_delegate_candidate"]
    ):
        ambiguity = _clamp_score(ambiguity + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff stayed in guarded narrowing mode, so the router treated the slice as less settled"
        )
    if (
        context_signal_summary["reasoning_readiness_score"] >= 3
        and context_signal_summary["context_density_score"] >= 2
        and context_signal_summary["route_ready"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported dense grounded context with high reasoning readiness, so the router allowed deeper bounded reasoning"
        )
    elif context_signal_summary["context_density_score"] <= 1 and context_signal_summary["narrowing_required"]:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported shallow context density while narrowing is still required, so the router avoided spending extra depth early"
        )
    if context_signal_summary["evidence_diversity_score"] >= 2:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff retained evidence from multiple distinct domains, which improved confidence in the bounded evidence cone"
        )
    if has_structured_handoff and context_signal_summary["spawn_worthiness_score"] >= 3:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this leaf as highly spawn-worthy relative to its merge cost"
        )
    elif (
        has_structured_handoff
        and context_signal_summary["support_leaf"]
        and context_signal_summary["spawn_worthiness_score"] <= 1
        and not request.correctness_critical
    ):
        mechanicalness = _clamp_score(mechanicalness + 1)
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this support slice as low spawn-worthiness, so the router stayed light"
        )
    if context_signal_summary["routing_confidence_level"] == "high":
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported high routing confidence for the retained evidence set"
        )
    elif context_signal_summary["routing_confidence_level"] == "low":
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported low routing confidence, which increases routing conservatism"
        )
    if context_signal_summary["parallelism_hint"] == "bounded_parallel_candidate":
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as a bounded parallel candidate"
        )
    elif context_signal_summary["parallelism_hint"] == "support_followup":
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as follow-up support work rather than critical-path execution"
        )
    if context_signal_summary["parallelism_hint"] in {"serial_preferred", "serial_guarded"} and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff preferred serial execution for this multi-path slice"
        )
    if has_structured_handoff and context_signal_summary["merge_burden_score"] >= 3:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported elevated merge burden for this slice"
        )
    odylith_recommended_profile = _router_profile_from_token(context_signal_summary["odylith_execution_profile"])
    odylith_execution_confidence = int(context_signal_summary["odylith_execution_confidence_score"] or 0)
    if odylith_recommended_profile is not None and odylith_execution_confidence >= 2:
        if odylith_recommended_profile in {
            RouterProfile.CODEX_HIGH,
            RouterProfile.GPT54_HIGH,
            RouterProfile.GPT54_XHIGH,
        }:
            requested_depth = _clamp_score(requested_depth + 1)
            accuracy_bias = _clamp_score(accuracy_bias + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "odylith execution profile recommended a deeper coding or GPT-5.4 tier for this bounded slice"
            )
        elif odylith_recommended_profile in {
            RouterProfile.MINI_MEDIUM,
            RouterProfile.SPARK_MEDIUM,
        } and context_signal_summary["support_leaf"] and not request.correctness_critical:
            mechanicalness = _clamp_score(mechanicalness + 1)
            requested_depth = _clamp_score(requested_depth - 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile marked this slice as a lighter support or scout lane"
            )
        if (
            context_signal_summary["odylith_execution_delegate_preference"] == "hold_local"
            and (
                needs_write
                or odylith_recommended_profile is RouterProfile.MAIN_THREAD
                or context_signal_summary["odylith_execution_selection_mode"] in {"narrow_first", "guarded_narrowing"}
            )
        ):
            coordination_cost = _clamp_score(coordination_cost + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile still preferred local narrowing before bounded spawn"
            )
        if odylith_execution_confidence >= 3:
            base_confidence_boost = True
            artifact_specificity = _clamp_score(artifact_specificity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile carried a high-confidence runtime recommendation for the delegated tier"
            )
    runtime_narrowing_required = bool(context_signal_summary["narrowing_required"] and not request.evidence_cone_grounded)
    if context_signal_summary["route_ready"]:
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff was already route-ready for native delegation"
        )
        if context_signal_summary["bounded_governance_delegate_candidate"]:
            validation_clarity = _clamp_score(validation_clarity + 1)
            acceptance_clarity = _clamp_score(acceptance_clarity + 1)
            base_confidence_boost = True
            feature_reasons.setdefault("context_signals", []).append(
                "governance closeout stayed route-ready with explicit plan-binding, validation, and sync obligations"
            )
    elif has_structured_handoff and context_signal_summary["spawn_worthiness_score"] <= 1:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff treated the slice as only conditionally route-ready, so the router stayed conservative"
        )

    correctness_critical = bool(
        request.correctness_critical
        or (reversibility_risk >= 3 and blast_radius >= 3)
        or _contains_any(text, ("correctness", "must be right", "no regression"))
    )
    if needs_write and correctness_critical and validation_clarity == 0:
        feature_reasons.setdefault("validation_clarity", []).append("critical write slice lacks explicit validation commands or checks")
    task_family = _classify_task_family(
        task_kind=task_kind,
        needs_write=needs_write,
        correctness_critical=correctness_critical,
        feature_implementation=feature_implementation,
        mixed_phase=mixed_phase,
        ambiguity=ambiguity,
        blast_radius=blast_radius,
        reversibility_risk=reversibility_risk,
        mechanicalness=mechanicalness,
        coordination_cost=coordination_cost,
    )
    runtime_selection_mode = _normalize_token(context_signal_summary["odylith_execution_selection_mode"])
    route_ready_now = bool(context_signal_summary["route_ready"] and not context_signal_summary["narrowing_required"])
    strong_grounding = bool(
        route_ready_now
        and context_signal_summary["grounding_score"] >= 3
        and context_signal_summary["evidence_quality_score"] >= 3
    )
    density_ready = bool(
        context_signal_summary["context_density_score"] >= 3
        and context_signal_summary["reasoning_readiness_score"] >= 3
    )
    expected_high_value = bool(
        context_signal_summary["expected_delegation_value_score"] >= 3
        or context_signal_summary["spawn_worthiness_score"] >= 3
    )
    earned_depth = _clamp_score(
        (1 if requested_depth >= 2 else 0)
        + (1 if accuracy_bias >= 2 or request.correctness_critical else 0)
        + (1 if strong_grounding else 0)
        + (1 if density_ready else 0)
        + (1 if runtime_selection_mode in _RUNTIME_EARNED_DEPTH_SELECTION_MODES else 0)
        + (1 if expected_high_value else 0)
        + (
            1
            if history_effective_yield_score >= 0.72
            and history_high_yield_rate >= 0.6
            and history_reliable_high_yield_rate >= 0.5
            else 0
        )
        - (1 if context_signal_summary["narrowing_required"] else 0)
        - (1 if ambiguity >= 3 and not request.correctness_critical else 0)
        - (1 if control_advisory_guarded or packet_profile_guarded else 0)
        - (1 if history_yield_state == "wasteful" and not request.correctness_critical else 0)
    )
    delegation_readiness = _clamp_score(
        (1 if route_ready_now else 0)
        + (1 if context_signal_summary["native_spawn_ready"] else 0)
        + (1 if expected_high_value else 0)
        + (1 if write_scope_clarity >= 3 or not needs_write else 0)
        + (1 if acceptance_clarity >= 2 else 0)
        + (1 if artifact_specificity >= 2 else 0)
        + (1 if context_signal_summary["parallelism_score"] >= 3 and explicit_path_count >= 2 else 0)
        - (1 if ambiguity >= 3 else 0)
        - (1 if coordination_cost >= 3 else 0)
        - (1 if context_signal_summary["narrowing_required"] else 0)
        - (1 if context_signal_summary["merge_burden_score"] >= 3 and not request.correctness_critical else 0)
        - (1 if control_advisory_guarded or packet_profile_guarded else 0)
    )
    high_coordination_delegate_candidate = bool(
        context_signal_summary["route_ready"]
        and context_signal_summary["native_spawn_ready"]
        and not context_signal_summary["narrowing_required"]
        and earned_depth >= 3
        and delegation_readiness >= 3
        and context_signal_summary["spawn_worthiness_score"] >= 2
        and context_signal_summary["merge_burden_score"] <= 2
        and explicit_path_count <= 3
    )
    if high_coordination_delegate_candidate and coordination_cost >= 3:
        coordination_cost = _clamp_score(coordination_cost - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "The retained runtime contract kept this high-signal slice delegable despite elevated coordination language because the retained runtime contract is already bounded and route-ready"
        )
    base_confidence = _clamp_score(
        1
        + (1 if acceptance_clarity >= 2 else 0)
        + (1 if artifact_specificity >= 2 else 0)
        + (1 if validation_clarity >= 2 or not needs_write else 0)
        + (1 if write_scope_clarity >= 3 else 0)
        - (1 if ambiguity >= 3 else 0)
        - (1 if mixed_phase else 0)
        - (1 if coordination_cost >= 3 else 0)
    )
    if earned_depth >= 3:
        base_confidence = _clamp_score(base_confidence + 1)
    if delegation_readiness >= 3:
        base_confidence = _clamp_score(base_confidence + 1)
    elif delegation_readiness <= 1 and needs_write and not request.correctness_critical:
        base_confidence = _clamp_score(base_confidence - 1)
    if context_signal_summary["routing_confidence_level"] == "high":
        base_confidence = _clamp_score(base_confidence + 1)
    elif context_signal_summary["routing_confidence_level"] == "low":
        base_confidence = _clamp_score(base_confidence - 1)
    if base_confidence_boost:
        base_confidence = _clamp_score(base_confidence + 1)

    hard_gate_hits: list[str] = []
    if runtime_narrowing_required:
        hard_gate_hits.append("runtime-narrowing-required")
    if coordination_cost >= 4 and not (
        (
            context_signal_summary["bounded_governance_delegate_candidate"]
            or high_coordination_delegate_candidate
        )
        and context_signal_summary["route_ready"]
        and context_signal_summary["native_spawn_ready"]
        and not context_signal_summary["narrowing_required"]
    ):
        hard_gate_hits.append("coordination-cost-high")
    if request.requires_multi_agent_adjudication:
        hard_gate_hits.append("multi-agent-adjudication")
    if mixed_phase and needs_write and coordination_cost >= 4:
        hard_gate_hits.append("mixed-phase-write-slice")
    if needs_write and write_scope_clarity <= 1:
        hard_gate_hits.append("unclear-write-scope")
    if needs_write and correctness_critical and acceptance_clarity <= 1 and validation_clarity == 0:
        hard_gate_hits.append("critical-write-under-specified")
    if needs_write and explicit_component_count >= 2 and explicit_path_count == 0:
        hard_gate_hits.append("cross-surface-ownership-unclear")
    if request.evolving_context_required and not request.evidence_cone_grounded:
        hard_gate_hits.append("evolving-context-required")
    if context_signal_summary["consumer_odylith_write_blocked"]:
        hard_gate_hits.append("consumer-odylith-diagnosis-and-handoff-only")
        feature_reasons.setdefault("context_signals", []).append(
            "consumer write policy keeps Odylith product issues in diagnosis-and-handoff mode instead of local mutation"
        )
    if request.evolving_context_required and request.evidence_cone_grounded:
        feature_reasons.setdefault("grounding", []).append(
            "the evidence cone was already grounded locally, so evolving context does not stay a hard delegation refusal"
        )
    if context_signal_summary["parallelism_score"] >= 3:
        base_confidence = _clamp_score(base_confidence + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported high parallel-safety confidence for the bounded slice"
        )
    if context_signal_summary["utility_score"] >= 3 and context_signal_summary["route_ready"]:
        base_confidence = _clamp_score(base_confidence + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "utility-aware handoff indicated the retained context is both high-value and route-ready"
        )
    if context_signal_summary["native_spawn_ready"]:
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff marked the slice as ready for native spawn payload emission"
        )
    if context_signal_summary["same_prefix_disjoint_exception"]:
        feature_reasons.setdefault("context_signals", []).append(
            "same-prefix disjointness was asserted in structured orchestration metadata"
        )
    if earned_depth >= 3:
        feature_reasons.setdefault("requested_depth", []).append(
            "The retained runtime contract judged that this slice earned stronger reasoning because the retained evidence is grounded, dense, and high-value"
        )
    if delegation_readiness >= 3:
        feature_reasons.setdefault("context_signals", []).append(
            "The retained runtime contract judged the current slice as delegation-ready because ownership, validation, and runtime readiness are all strong"
        )

    return TaskAssessment(
        prompt=prompt,
        task_kind=task_kind,
        task_family=task_family,
        phase=request.phase or ("mixed" if mixed_phase else next(iter(phase_tokens), "")),
        needs_write=needs_write,
        correctness_critical=correctness_critical,
        feature_implementation=feature_implementation,
        mixed_phase=mixed_phase,
        requires_multi_agent_adjudication=request.requires_multi_agent_adjudication,
        evolving_context_required=request.evolving_context_required,
        evidence_cone_grounded=request.evidence_cone_grounded,
        ambiguity=ambiguity,
        blast_radius=blast_radius,
        context_breadth=context_breadth,
        coordination_cost=coordination_cost,
        reversibility_risk=reversibility_risk,
        mechanicalness=mechanicalness,
        write_scope_clarity=write_scope_clarity,
        acceptance_clarity=acceptance_clarity,
        artifact_specificity=artifact_specificity,
        validation_clarity=validation_clarity,
        latency_pressure=latency_pressure,
        requested_depth=requested_depth,
        accuracy_bias=_clamp_score(accuracy_bias),
        earned_depth=earned_depth,
        delegation_readiness=delegation_readiness,
        base_confidence=base_confidence,
        accuracy_preference=request.accuracy_preference,
        phase_tokens=sorted(phase_tokens),
        semantic_signals=semantic_signals,
        hard_gate_hits=hard_gate_hits,
        feature_reasons=feature_reasons,
        context_signal_summary=context_signal_summary,
    )
