"""Shared context-signal summary and consumer-write policy helpers for routing."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.consumer_profile import load_consumer_profile
from odylith.runtime.common import host_runtime as host_runtime_contract
from odylith.runtime.context_engine import packet_quality_codec
from odylith.runtime.orchestration import subagent_router
from odylith.runtime.orchestration import subagent_router_context_support
from odylith.runtime.orchestration import subagent_router_execution_engine_runtime

_context_signal_root = subagent_router_context_support._context_signal_root
_mapping_value = subagent_router_context_support._mapping_value
_validation_bundle_from_context = subagent_router_context_support._validation_bundle_from_context
_governance_obligations_from_context = subagent_router_context_support._governance_obligations_from_context
_surface_refs_from_context = subagent_router_context_support._surface_refs_from_context
_execution_profile_mapping = subagent_router_context_support._execution_profile_mapping
_preferred_router_profile_from_execution_profile = (
    subagent_router_context_support._preferred_router_profile_from_execution_profile
)
_context_signal_score = subagent_router_context_support._context_signal_score
_context_lookup = subagent_router_context_support._context_lookup
_normalize_token = subagent_router_context_support._normalize_token
_context_signal_bool = subagent_router_context_support._context_signal_bool
_normalize_list = subagent_router_context_support._normalize_list
_count_or_list_len = subagent_router_context_support._count_or_list_len
_normalize_string = subagent_router_context_support._normalize_string
_dedupe_strings = subagent_router_context_support._dedupe_strings
_int_value = subagent_router_context_support._int_value
_clamp_score = subagent_router_context_support._clamp_score
_normalized_rate = subagent_router_context_support._normalized_rate
_latency_pressure_signal = subagent_router_context_support._latency_pressure_signal
_scaled_numeric_signal = subagent_router_context_support._scaled_numeric_signal
_context_signal_level = subagent_router_context_support._context_signal_level
_SCORE_MAX = subagent_router_context_support._SCORE_MAX
_SCORE_MIN = subagent_router_context_support._SCORE_MIN

_infer_prompt_semantics = subagent_router.infer_prompt_semantics
_infer_explicit_paths = subagent_router.infer_explicit_paths
_surface_prefixes_for_path = subagent_router.surface_prefixes_for_path
_infer_phase_tokens = subagent_router._infer_phase_tokens
_contains_any = subagent_router._contains_any
_keyword_score = subagent_router._keyword_score
_router_profile_from_token = subagent_router._router_profile_from_token
_classify_task_family = subagent_router._classify_task_family
TaskAssessment = subagent_router.TaskAssessment
RouterProfile = subagent_router.RouterProfile
_FEATURE_KEYWORDS = subagent_router._FEATURE_KEYWORDS
_WRITE_KEYWORDS = subagent_router._WRITE_KEYWORDS
_AMBIGUITY_KEYWORDS = subagent_router._AMBIGUITY_KEYWORDS
_RISK_KEYWORDS = subagent_router._RISK_KEYWORDS
_COORDINATION_KEYWORDS = subagent_router._COORDINATION_KEYWORDS
_REVERSIBILITY_KEYWORDS = subagent_router._REVERSIBILITY_KEYWORDS
_MECHANICAL_KEYWORDS = subagent_router._MECHANICAL_KEYWORDS
_VALIDATION_KEYWORDS = subagent_router._VALIDATION_KEYWORDS
_LATENCY_KEYWORDS = subagent_router._LATENCY_KEYWORDS
_DEPTH_KEYWORDS = subagent_router._DEPTH_KEYWORDS
_RUNTIME_EARNED_DEPTH_SELECTION_MODES = subagent_router._RUNTIME_EARNED_DEPTH_SELECTION_MODES


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
    request: subagent_router.RouteRequest,
    *,
    repo_root: Path | None,
) -> subagent_router.RouteRequest:
    if repo_root is None or not request.needs_write:
        return request
    profile = load_consumer_profile(repo_root=Path(repo_root).resolve())
    policy = dict(profile.get("odylith_write_policy", {})) if isinstance(profile.get("odylith_write_policy"), Mapping) else {}
    if not policy:
        return request
    merged_context = subagent_router_context_support._normalize_context_signals(request.context_signals)
    if merged_context.get("odylith_write_policy") == policy:
        return request
    merged_context["odylith_write_policy"] = policy
    payload = request.as_dict()
    payload["context_signals"] = merged_context
    return subagent_router.RouteRequest(**payload)


def _context_signal_summary(request: subagent_router.RouteRequest) -> dict[str, Any]:
    context_signals = subagent_router_context_support._normalize_context_signals(request.context_signals)
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
    execution_engine_fields = subagent_router_execution_engine_runtime.router_execution_engine_fields(
        context_signals=context_signals,
        root=root,
        execution_engine_summary=execution_engine_summary,
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
        **execution_engine_fields,
        "odylith_fix_mode": odylith_fix_mode,
        "allow_odylith_mutations": allow_odylith_mutations,
        "odylith_write_protected_roots": odylith_write_protected_roots,
        "consumer_odylith_write_blocked": consumer_odylith_write_blocked,
    }

