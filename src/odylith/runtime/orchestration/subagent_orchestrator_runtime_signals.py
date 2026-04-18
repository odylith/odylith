"""Adaptive orchestration helpers extracted from the subagent orchestrator."""

from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine import runtime_lane_policy


def _adaptive_batch_mode(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    safety: ParallelSafetyClass,
    groups: Sequence[Sequence[str]],
    tuning: TuningState,
) -> tuple[OrchestrationMode, list[str]]:
    from odylith.runtime.orchestration import subagent_orchestrator as host

    OrchestrationMode = host.OrchestrationMode
    ParallelSafetyClass = host.ParallelSafetyClass
    _mode_reliability_summary = host._mode_reliability_summary
    _tuning_bias = host._tuning_bias
    _critical_path_posture = host._critical_path_posture
    _merge_burden_estimate = host._merge_burden_estimate
    _clamp_confidence = host._clamp_confidence
    _normalize_token = host._normalize_token
    _int_value = host._int_value
    _normalized_rate = host._normalized_rate
    _sanitize_user_facing_lines = host._sanitize_user_facing_lines

    if safety not in {ParallelSafetyClass.READ_ONLY_SAFE, ParallelSafetyClass.DISJOINT_WRITE_SAFE}:
        return OrchestrationMode.SERIAL_BATCH, []
    parallel_summary = _mode_reliability_summary(
        tuning,
        mode=OrchestrationMode.PARALLEL_BATCH.value,
        task_family=assessment.task_family,
    )
    serial_summary = _mode_reliability_summary(
        tuning,
        mode=OrchestrationMode.SERIAL_BATCH.value,
        task_family=assessment.task_family,
    )
    parallel_bias = _tuning_bias(tuning, mode=OrchestrationMode.PARALLEL_BATCH.value, task_family=assessment.task_family)
    critical_path = _critical_path_posture(request, groups=groups)
    merge_burden = _merge_burden_estimate(request, assessment, groups=groups)
    earned_depth = int(assessment.earned_depth or 0)
    delegation_readiness = int(assessment.delegation_readiness or 0)
    notes = [
        (
            "critical_path="
            f"{critical_path} merge_burden={merge_burden} "
            f"parallel_history={parallel_summary['posture']}[{parallel_summary['source']}] "
            f"serial_history={serial_summary['posture']}[{serial_summary['source']}]"
        )
    ]

    def _finish(mode: OrchestrationMode) -> tuple[OrchestrationMode, list[str]]:
        return mode, _sanitize_user_facing_lines(notes)

    context_summary = dict(assessment.context_signal_summary or {})
    governance_guard = runtime_lane_policy.parallelism_guard(context_summary)
    if governance_guard.blocked:
        notes.append(governance_guard.reason)
        return _finish(OrchestrationMode.SERIAL_BATCH)
    odylith_confidence = _clamp_confidence(context_summary.get("odylith_execution_confidence_score", 0) or 0)
    odylith_delegate_preference = _normalize_token(context_summary.get("odylith_execution_delegate_preference", ""))
    odylith_selection_mode = _normalize_token(context_summary.get("odylith_execution_selection_mode", ""))
    odylith_parallel_hint = _normalize_token(context_summary.get("parallelism_hint", ""))
    odylith_route_ready = bool(context_summary.get("route_ready") or context_summary.get("odylith_execution_route_ready"))
    odylith_narrowing_required = bool(
        context_summary.get("narrowing_required") or context_summary.get("odylith_execution_narrowing_required")
    )
    odylith_parallelism_score = _int_value(context_summary.get("parallelism_score", 0))
    odylith_spawn_worthiness = max(
        _int_value(context_summary.get("spawn_worthiness_score", 0)),
        _int_value(context_summary.get("odylith_execution_spawn_worthiness", 0)),
    )
    optimization_within_budget_rate = _normalized_rate(context_summary.get("optimization_within_budget_rate", 0.0))
    optimization_native_spawn_ready_rate = _normalized_rate(
        context_summary.get("optimization_native_spawn_ready_rate", 0.0)
    )
    optimization_delegated_lane_rate = _normalized_rate(context_summary.get("optimization_delegated_lane_rate", 0.0))
    optimization_hold_local_rate = _normalized_rate(context_summary.get("optimization_hold_local_rate", 0.0))
    optimization_runtime_backed_execution_rate = _normalized_rate(
        context_summary.get("optimization_runtime_backed_execution_rate", 0.0)
    )
    optimization_avg_effective_yield_score = max(
        0.0,
        min(1.0, float(context_summary.get("optimization_avg_effective_yield_score", 0.0) or 0.0)),
    )
    optimization_high_yield_rate = _normalized_rate(
        context_summary.get("optimization_high_yield_rate", 0.0)
    )
    optimization_reliable_high_yield_rate = _normalized_rate(
        context_summary.get("optimization_reliable_high_yield_rate", 0.0)
    )
    optimization_yield_state = _normalize_token(context_summary.get("optimization_yield_state", ""))
    optimization_packet_alignment_rate = _normalized_rate(
        context_summary.get("optimization_packet_alignment_rate", 0.0)
    )
    optimization_reliable_packet_alignment_rate = _normalized_rate(
        context_summary.get("optimization_reliable_packet_alignment_rate", 0.0)
    )
    optimization_packet_alignment_state = _normalize_token(
        context_summary.get("optimization_packet_alignment_state", "")
    )
    evaluation_router_acceptance_rate = _normalized_rate(context_summary.get("evaluation_router_acceptance_rate", 0.0))
    evaluation_router_failure_rate = _normalized_rate(context_summary.get("evaluation_router_failure_rate", 0.0))
    evaluation_orchestration_parallel_failure_rate = _normalized_rate(
        context_summary.get("evaluation_orchestration_parallel_failure_rate", 0.0)
    )
    evaluation_orchestration_token_efficiency_rate = _normalized_rate(
        context_summary.get("evaluation_orchestration_token_efficiency_rate", 0.0)
    )
    evaluation_decision_quality_score = _normalized_rate(
        context_summary.get("evaluation_decision_quality_score", 0.0)
    )
    evaluation_decision_quality_state = _normalize_token(
        context_summary.get("evaluation_decision_quality_state", "")
    )
    evaluation_decision_quality_confidence = _clamp_confidence(
        context_summary.get("evaluation_decision_quality_confidence_score", 0) or 0
    )
    evaluation_closeout_observation_rate = _normalized_rate(
        context_summary.get("evaluation_closeout_observation_rate", 0.0)
    )
    evaluation_delegation_regret_rate = _normalized_rate(
        context_summary.get("evaluation_delegation_regret_rate", 0.0)
    )
    evaluation_followup_churn_rate = _normalized_rate(
        context_summary.get("evaluation_followup_churn_rate", 0.0)
    )
    evaluation_merge_underestimate_rate = _normalized_rate(
        context_summary.get("evaluation_merge_underestimate_rate", 0.0)
    )
    evaluation_validation_underestimate_rate = _normalized_rate(
        context_summary.get("evaluation_validation_underestimate_rate", 0.0)
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
    evaluation_control_parallelism = _normalize_token(context_summary.get("evaluation_control_parallelism", ""))
    evaluation_control_delegation = _normalize_token(context_summary.get("evaluation_control_delegation", ""))
    control_advisory_state = _normalize_token(context_summary.get("control_advisory_state", ""))
    control_advisory_confidence = _clamp_confidence(context_summary.get("control_advisory_confidence_score", 0) or 0)
    control_advisory_reasoning_mode = _normalize_token(context_summary.get("control_advisory_reasoning_mode", ""))
    control_advisory_delegation = _normalize_token(context_summary.get("control_advisory_delegation", ""))
    control_advisory_parallelism = _normalize_token(context_summary.get("control_advisory_parallelism", ""))
    control_advisory_budget_mode = _normalize_token(context_summary.get("control_advisory_budget_mode", ""))
    control_advisory_speed_mode = _normalize_token(context_summary.get("control_advisory_speed_mode", ""))
    packet_strategy = _normalize_token(context_summary.get("packet_strategy", ""))
    budget_mode = _normalize_token(context_summary.get("budget_mode", ""))
    speed_mode = _normalize_token(context_summary.get("speed_mode", ""))
    packet_reliability = _normalize_token(context_summary.get("packet_reliability", ""))
    control_advisory_freshness_bucket = _normalize_token(context_summary.get("control_advisory_freshness_bucket", ""))
    control_advisory_evidence_strength = _clamp_confidence(
        context_summary.get("control_advisory_evidence_strength_score", 0) or 0
    )
    control_advisory_signal_conflict = bool(context_summary.get("control_advisory_signal_conflict"))
    advisory_present = bool(
        control_advisory_state
        or control_advisory_reasoning_mode
        or control_advisory_delegation
        or control_advisory_parallelism
        or control_advisory_budget_mode
        or control_advisory_speed_mode
        or control_advisory_freshness_bucket
        or control_advisory_confidence > 0
        or control_advisory_evidence_strength > 0
        or control_advisory_signal_conflict
    )
    advisory_reliable = bool(
        advisory_present
        and control_advisory_confidence >= 3
        and control_advisory_evidence_strength >= 3
        and control_advisory_freshness_bucket in {"fresh", "recent"}
        and not control_advisory_signal_conflict
        and optimization_packet_alignment_state not in {"drifting"}
        and (optimization_reliable_packet_alignment_rate == 0.0 or optimization_reliable_packet_alignment_rate >= 0.7)
    )
    advisory_guarded = bool(
        advisory_present
        and (
            control_advisory_freshness_bucket in {"aging", "stale"}
            or control_advisory_evidence_strength <= 1
            or control_advisory_signal_conflict
            or optimization_packet_alignment_state == "drifting"
            or (
                optimization_reliable_packet_alignment_rate > 0.0
                and optimization_reliable_packet_alignment_rate < 0.7
            )
        )
    )
    packet_profile_guarded = packet_reliability == "guarded"
    packet_profile_reliable = packet_reliability == "reliable"
    if odylith_confidence >= 3 and (
        odylith_selection_mode in {"narrow_first", "guarded_narrowing"}
        or odylith_parallel_hint in {"serial_preferred", "serial_guarded", "support_followup"}
        or (odylith_delegate_preference == "hold_local" and (odylith_narrowing_required or not odylith_route_ready))
    ):
        notes.append(
            "Orchestration stayed serial because the slice still needs narrowing or ordered follow-up."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        optimization_packet_alignment_state == "drifting"
        and safety is not ParallelSafetyClass.READ_ONLY_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because recent execution fit is unstable, so broader fan-out would add avoidable churn."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        optimization_yield_state == "wasteful"
        and safety is not ParallelSafetyClass.READ_ONLY_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because recent packets are low-yield for their spend, so wider fan-out would compound budget waste before evidence density improves"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if control_advisory_confidence >= 3 and (
        control_advisory_reasoning_mode == "guarded_narrowing"
        or (control_advisory_delegation == "hold_local_bias" and (odylith_narrowing_required or not odylith_route_ready))
        or (control_advisory_parallelism == "guarded" and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE)
    ):
        notes.append(
            "Orchestration stayed serial because recent execution evidence still favors guarded narrowing or local-first execution."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if advisory_guarded and safety is not ParallelSafetyClass.READ_ONLY_SAFE:
        notes.append(
            "Orchestration stayed serial because recent execution evidence is stale or conflicted, so staying local or running in order is safer for now."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if packet_profile_guarded and not advisory_present and safety is not ParallelSafetyClass.READ_ONLY_SAFE:
        notes.append(
            "Orchestration stayed serial because write fan-out still needs fresher evidence before widening."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and delegation_readiness <= 1
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because the current slice is still weak on explicit delegation readiness, so fan-out would outrun bounded ownership."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and optimization_hold_local_rate >= 0.6
        and optimization_hold_local_rate > optimization_delegated_lane_rate
        and not request.correctness_critical
    ):
        notes.append(
            "recent optimization history still favors hold-local execution over delegated fan-out for comparable write slices"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        evaluation_control_delegation == "hold_local_bias"
        and evaluation_router_failure_rate >= 0.35
        and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Recent execution evidence currently biases toward staying local or running in order because recent delegated write outcomes are unstable."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        decision_quality_reliable
        and (evaluation_delegation_regret_rate >= 0.25 or evaluation_followup_churn_rate >= 0.25)
        and safety is not ParallelSafetyClass.READ_ONLY_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because recent delegated slices generated regret or follow-up churn after execution, so tighter local coordination is safer until closeout quality improves"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        evaluation_control_parallelism == "guarded"
        and evaluation_orchestration_parallel_failure_rate >= 0.25
        and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
    ):
        notes.append(
            "Recent execution evidence is guarding parallelism because recent orchestration feedback shows merge or false-parallel regressions"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        decision_quality_reliable
        and evaluation_merge_underestimate_rate >= 0.2
        and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because recent execution shows merge burden is being underpredicted, so broad write fan-out is still too optimistic"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        decision_quality_reliable
        and evaluation_validation_underestimate_rate >= 0.25
        and safety is not ParallelSafetyClass.READ_ONLY_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because recent delegated slices are underpredicting validation pressure, so narrower execution is safer until that calibration improves"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        decision_quality_fragile
        and safety is not ParallelSafetyClass.READ_ONLY_SAFE
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because trusted execution-outcome evidence is currently fragile overall, so clean closeout needs to recover before widening coordination again"
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and request.evidence_cone_grounded
        and odylith_route_ready
        and not odylith_narrowing_required
        and delegation_readiness >= 3
        and earned_depth >= 3
        and odylith_spawn_worthiness >= 2
        and merge_burden <= 2
        and parallel_summary["posture"] != "weak"
    ):
        notes.append(
            "Bounded parallel fan-out is allowed because the slice is grounded, delegation-ready, and has already earned deeper reasoning."
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        control_advisory_parallelism == "allow_when_disjoint"
        and advisory_reliable
        and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and merge_burden <= 2
        and odylith_route_ready
        and not odylith_narrowing_required
    ):
        notes.append(
            "Bounded disjoint parallelism is allowed because recent execution evidence is stable on comparable slices."
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        odylith_confidence >= 3
        and odylith_parallel_hint == "bounded_parallel_candidate"
        and odylith_route_ready
        and not odylith_narrowing_required
        and odylith_spawn_worthiness >= 2
    ):
        if safety is ParallelSafetyClass.READ_ONLY_SAFE and parallel_summary["posture"] != "weak":
            notes.append("This read-only slice is a bounded parallel candidate.")
            return _finish(OrchestrationMode.PARALLEL_BATCH)
        if (
            safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
            and parallel_summary["posture"] != "weak"
            and (merge_burden <= 2 or odylith_parallelism_score >= 3)
        ):
            notes.append("This write slice is ready for bounded parallel fan-out.")
            return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        evaluation_control_parallelism == "allow_when_disjoint"
        and evaluation_router_acceptance_rate >= 0.7
        and evaluation_orchestration_token_efficiency_rate >= 0.6
        and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and merge_burden <= 2
        and not odylith_narrowing_required
    ):
        notes.append(
            "Recent execution evidence is improving on disjoint parallel execution, so bounded parallel fan-out is allowed"
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        odylith_route_ready
        and not odylith_narrowing_required
        and optimization_within_budget_rate >= 0.75
        and optimization_native_spawn_ready_rate >= 0.75
        and optimization_runtime_backed_execution_rate >= 0.75
        and optimization_avg_effective_yield_score >= 0.72
        and optimization_high_yield_rate >= 0.6
        and optimization_reliable_high_yield_rate >= 0.5
        and optimization_packet_alignment_rate >= 0.75
        and merge_burden <= 2
        and parallel_summary["posture"] != "weak"
    ):
        notes.append(
            "recent optimization history shows comparable delegated slices stay budget-safe, native-spawn-ready, runtime-backed, and high-yield per token"
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        control_advisory_budget_mode == "tight"
        and merge_burden >= 2
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because current execution evidence is optimizing for tighter budget discipline."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        not advisory_reliable
        and budget_mode == "tight"
        and merge_burden >= 2
        and not request.correctness_critical
    ):
        notes.append(
            "Orchestration stayed serial because the current slice is already operating in tight-budget mode."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        control_advisory_speed_mode == "accelerate_grounded"
        and control_advisory_state in {"improving", "stable"}
        and advisory_reliable
        and odylith_route_ready
        and not odylith_narrowing_required
        and parallel_summary["posture"] != "weak"
        and merge_burden <= 2
    ):
        notes.append(
            "Grounded execution accelerated because recent measured fan-out stayed efficient."
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        not advisory_guarded
        and not advisory_reliable
        and speed_mode == "accelerate_grounded"
        and packet_profile_reliable
        and odylith_route_ready
        and not odylith_narrowing_required
        and parallel_summary["posture"] != "weak"
        and merge_burden <= 2
    ):
        notes.append(
            "Grounded execution accelerated because the current slice is reliable and already tuned for faster bounded fan-out."
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    if (
        not advisory_present
        and packet_strategy == "precision_first"
        and safety is ParallelSafetyClass.DISJOINT_WRITE_SAFE
        and merge_burden >= 2
    ):
        notes.append(
            "Orchestration stayed serial because the current slice is still precision-first and merge-sensitive."
        )
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if safety is ParallelSafetyClass.READ_ONLY_SAFE:
        if parallel_summary["posture"] == "weak":
            notes.append("read-only fan-out stayed serial because parallel history for this family is weak")
            return _finish(OrchestrationMode.SERIAL_BATCH)
        if parallel_summary["posture"] == "strong" or parallel_bias >= -0.25:
            notes.append("read-only fan-out remained parallel because the slice is safe and history supports it")
            return _finish(OrchestrationMode.PARALLEL_BATCH)
        notes.append("read-only fan-out stayed serial until parallel history or bias improves")
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if parallel_summary["posture"] == "weak":
        notes.append("write fan-out stayed serial because prior parallel outcomes show merge or false-parallel risk")
        return _finish(OrchestrationMode.SERIAL_BATCH)
    if merge_burden >= 3 and parallel_summary["posture"] != "strong":
        if request.evidence_cone_grounded and _int_value(assessment.context_signal_summary.get("parallelism_score")) >= 3:
            notes.append("high-confidence grounded parallelism signals offset the elevated merge burden for this bounded slice")
        else:
            notes.append(
                "write fan-out stayed serial because the critical path is implementation-first and merge burden is still high"
            )
            return _finish(OrchestrationMode.SERIAL_BATCH)
    if (
        (request.evidence_cone_grounded or critical_path == "implementation_only")
        and (parallel_summary["posture"] == "strong" or parallel_bias >= -0.2)
    ):
        notes.append(
            "bounded parallel fan-out is allowed because the write slice is narrowly disjoint or grounded and parallel history is not weak"
        )
        return _finish(OrchestrationMode.PARALLEL_BATCH)
    notes.append("write fan-out stayed serial until grounding or parallel reliability improves")
    return _finish(OrchestrationMode.SERIAL_BATCH)


def _subtask_context_signals(
    request: OrchestrationRequest,
    assessment: leaf_router.TaskAssessment,
    *,
    subtask: SubtaskSlice,
    mode: OrchestrationMode,
    all_subtasks: Sequence[SubtaskSlice],
) -> dict[str, Any]:
    from odylith.runtime.orchestration import subagent_orchestrator as host

    OrchestrationMode = host.OrchestrationMode
    _normalize_context_signals = host._normalize_context_signals
    _nested_mapping = host._nested_mapping
    _subtask_intent_profile = host._subtask_intent_profile
    _merge_burden_estimate = host._merge_burden_estimate
    _same_prefix_exception_active = host._same_prefix_exception_active
    _normalize_bool = host._normalize_bool
    _normalize_token = host._normalize_token
    _mapping_lookup = host._mapping_lookup
    _normalize_list = host._normalize_list
    _int_value = host._int_value
    _spawn_worthiness_score = host._spawn_worthiness_score
    _utility_level = host._utility_level
    _float_value = host._float_value
    _score_level = host._score_level
    _routing_confidence_for_subtask = host._routing_confidence_for_subtask
    _clamp_confidence = host._clamp_confidence
    _subtask_odylith_execution_profile = host._subtask_odylith_execution_profile
    _dedupe_strings = host._dedupe_strings
    _merge_context_signals = host._merge_context_signals
    _normalized_rate = host._normalized_rate

    base = _normalize_context_signals(request.context_signals)
    named_contract_keys = {_normalize_token(key) for key in base}
    base_has_named_contracts = bool(
        named_contract_keys.intersection({"routing_handoff", "context_packet", "evidence_pack", "optimization_snapshot"})
    )
    if base and "routing_handoff" not in named_contract_keys and not base_has_named_contracts:
        base = {"routing_handoff": base}
    base_root = _nested_mapping(base, "routing_handoff") or ({} if base_has_named_contracts else dict(base))
    base_context_packet = _nested_mapping(base, "context_packet")
    base_validation_bundle = _nested_mapping(base, "validation_bundle")
    base_governance_obligations = _nested_mapping(base, "governance_obligations")
    base_surface_refs = _nested_mapping(base, "surface_refs")
    base_packet_quality = _nested_mapping(base_root, "packet_quality") or _nested_mapping(base_context_packet, "packet_quality")
    base_utility = _nested_mapping(base_root, "utility") or _nested_mapping(base_context_packet, "optimization")
    base_utility_profile = _nested_mapping(base_packet_quality, "utility_profile")
    base_evidence_pack = _nested_mapping(base, "evidence_pack")
    base_optimization_snapshot = _nested_mapping(base, "optimization_snapshot")
    base_architecture_audit = (
        _nested_mapping(base, "architecture_audit")
        or _nested_mapping(base_root, "architecture_audit")
        or _nested_mapping(base_context_packet, "architecture_audit")
        or _nested_mapping(base_evidence_pack, "architecture_audit")
    )
    base_architecture_execution_hint = _nested_mapping(base_architecture_audit, "execution_hint")
    base_architecture_coverage = _nested_mapping(base_architecture_audit, "coverage")
    base_optimization_overall = _nested_mapping(base_optimization_snapshot, "overall")
    base_optimization_packet_posture = _nested_mapping(base_optimization_snapshot, "packet_posture")
    base_optimization_quality_posture = _nested_mapping(base_optimization_snapshot, "quality_posture")
    base_optimization_orchestration_posture = _nested_mapping(base_optimization_snapshot, "orchestration_posture")
    base_optimization_intent_posture = _nested_mapping(base_optimization_snapshot, "intent_posture")
    base_optimization_latency_posture = _nested_mapping(base_optimization_snapshot, "latency_posture")
    base_optimization_evaluation_posture = _nested_mapping(base_optimization_snapshot, "evaluation_posture")
    base_optimization_learning_loop = _nested_mapping(base_optimization_snapshot, "learning_loop")
    base_optimization_control_advisories = _nested_mapping(base_optimization_snapshot, "control_advisories")
    base_evaluation_packet_posture = _nested_mapping(base_optimization_evaluation_posture, "packet_events")
    base_evaluation_router_posture = _nested_mapping(base_optimization_evaluation_posture, "router_outcomes")
    base_evaluation_orchestration_posture = _nested_mapping(
        base_optimization_evaluation_posture,
        "orchestration_feedback",
    )
    base_evaluation_trend_posture = _nested_mapping(base_optimization_evaluation_posture, "trend_posture")
    base_evaluation_control_posture = _nested_mapping(base_optimization_evaluation_posture, "control_posture")
    base_evaluation_freshness = _nested_mapping(base_optimization_evaluation_posture, "freshness")
    base_evaluation_evidence_strength = _nested_mapping(base_optimization_evaluation_posture, "evidence_strength")
    base_evaluation_control_advisories = _nested_mapping(base_optimization_evaluation_posture, "control_advisories")
    base_learning_freshness = _nested_mapping(base_optimization_learning_loop, "freshness")
    base_learning_evidence_strength = _nested_mapping(base_optimization_learning_loop, "evidence_strength")
    base_learning_control_advisories = _nested_mapping(base_optimization_learning_loop, "control_advisories")
    merged_control_advisories = dict(base_learning_control_advisories)
    for source in (base_evaluation_control_advisories, base_optimization_control_advisories):
        for key, value in source.items():
            if key not in merged_control_advisories or merged_control_advisories[key] in ("", [], {}, None):
                merged_control_advisories[key] = value
    intent_profile = _subtask_intent_profile(
        request=request,
        subtask=subtask,
        all_subtasks=all_subtasks,
        base_root=base_root,
        base_packet_quality=base_packet_quality,
    )
    base_token_efficiency = (
        _nested_mapping(base_utility_profile, "token_efficiency")
        or _nested_mapping(base_utility, "token_efficiency")
    )
    primary_count = sum(1 for planned in all_subtasks if planned.execution_group_kind == "primary")
    support_count = sum(1 for planned in all_subtasks if planned.execution_group_kind == "support")
    all_groups = [planned.owned_paths or planned.read_paths for planned in all_subtasks]
    merge_burden = _merge_burden_estimate(request, assessment, groups=all_groups)
    same_prefix_disjoint_exception = _same_prefix_exception_active(
        request,
        assessment,
        subtask=subtask,
        mode=mode,
        all_subtasks=all_subtasks,
    )
    scope_size = len(subtask.owned_paths or subtask.read_paths)
    dependency_count = len(subtask.dependency_ids)
    plan_binding_required = _normalize_bool(_mapping_lookup(base_validation_bundle, "plan_binding_required"))
    governed_surface_sync_required = _normalize_bool(
        _mapping_lookup(base_validation_bundle, "governed_surface_sync_required")
    )
    strict_gate_commands = _normalize_list(_mapping_lookup(base_validation_bundle, "strict_gate_commands"))
    governance_support_closeout_ready = bool(
        request.evidence_cone_grounded
        and subtask.scope_role == "governance"
        and subtask.execution_group_kind == "support"
        and scope_size >= 1
        and (plan_binding_required or governed_surface_sync_required or strict_gate_commands)
        and (base_governance_obligations or base_surface_refs)
    )
    retained_signal_count = max(
        _int_value(_mapping_lookup(base_utility_profile, "retained_signal_count")),
        scope_size + len(subtask.validation_commands) + (1 if request.evidence_cone_grounded else 0),
    )
    base_utility_score = _int_value(_mapping_lookup(base_utility_profile, "score"))
    if base_utility_score <= 0:
        base_utility_score = max(0, min(100, _int_value(_mapping_lookup(base_utility, "score")) * 25))
    if base_utility_score <= 0:
        base_utility_score = (
            (28 if request.evidence_cone_grounded else 14)
            + min(18, scope_size * 6)
            + min(18, len(subtask.validation_commands) * 7)
            + (10 if subtask.execution_group_kind == "primary" else 0)
            + (8 if subtask.scope_role in {"implementation", "contract"} else 4)
            + (8 if subtask.correctness_critical else 0)
        )
    spawn_worthiness = _spawn_worthiness_score(
        request,
        assessment,
        subtask=subtask,
        mode=mode,
        primary_count=primary_count,
        merge_burden=merge_burden,
        same_prefix_disjoint_exception=same_prefix_disjoint_exception,
    )
    if governance_support_closeout_ready:
        spawn_worthiness = max(spawn_worthiness, 3)
    utility_score = base_utility_score + (spawn_worthiness * 9) - (dependency_count * 6)
    if subtask.execution_group_kind == "support":
        utility_score -= 10
    elif subtask.execution_group_kind == "primary":
        utility_score += 4
    if subtask.scope_role == "validation":
        utility_score -= 2
    if subtask.scope_role == "docs":
        utility_score -= 8
    utility_score = max(0, min(100, utility_score))
    utility_signal_score = max(0, min(4, int(round(utility_score / 25.0))))
    utility_level = (
        str(_mapping_lookup(base_utility_profile, "level") or _mapping_lookup(base_utility, "level")).strip()
        or _utility_level(utility_score)
    )
    density_per_1k_tokens = _float_value(_mapping_lookup(base_utility_profile, "density_per_1k_tokens"))
    token_efficiency_score = _int_value(_mapping_lookup(base_token_efficiency, "score"))
    if token_efficiency_score <= 0:
        if utility_score >= 75 and retained_signal_count >= 4:
            token_efficiency_score = 4
        elif utility_score >= 60 and retained_signal_count >= 3:
            token_efficiency_score = 3
        elif utility_score >= 40:
            token_efficiency_score = 2
        elif utility_score >= 20:
            token_efficiency_score = 1
    token_efficiency_level = (
        str(_mapping_lookup(base_token_efficiency, "level")).strip() or _score_level(token_efficiency_score)
    )
    routing_confidence_score = _routing_confidence_for_subtask(
        request,
        subtask=subtask,
        merge_burden=merge_burden,
        spawn_worthiness=spawn_worthiness,
        same_prefix_disjoint_exception=same_prefix_disjoint_exception,
    )
    route_ready = bool(
        (request.evidence_cone_grounded or not request.needs_write)
        and (spawn_worthiness >= 2 or governance_support_closeout_ready)
        and routing_confidence_score >= (1 if governance_support_closeout_ready else 2)
    )
    parent_narrowing_required = _normalize_bool(_mapping_lookup(base_root, "narrowing_required"), default=False)
    narrowing_required = bool(
        parent_narrowing_required
        and not governance_support_closeout_ready
        and not route_ready
        and (subtask.execution_group_kind != "primary" or spawn_worthiness <= 2)
    )
    validation_pressure = _clamp_confidence(
        len(subtask.validation_commands)
        + (1 if subtask.correctness_critical else 0)
        + (1 if subtask.scope_role == "validation" else 0)
    )
    coordination_complexity = _clamp_confidence(
        (1 if dependency_count >= 1 else 0)
        + (1 if dependency_count >= 2 and subtask.scope_role not in {"validation"} else 0)
        + (1 if merge_burden >= 3 else 0)
        + (1 if subtask.execution_group_kind == "support" and primary_count >= 1 and subtask.scope_role not in {"validation"} else 0)
    )
    actionability_score = _clamp_confidence(
        1
        + (1 if scope_size >= 1 else 0)
        + (1 if subtask.execution_group_kind == "primary" else 0)
        + (1 if subtask.scope_role == "validation" and subtask.validation_commands else 0)
        - (1 if dependency_count >= 2 else 0)
        - (1 if subtask.scope_role == "docs" else 0)
    )
    evidence_quality_score = _clamp_confidence(
        (4 if request.evidence_cone_grounded else 1)
        - (1 if same_prefix_disjoint_exception else 0)
        - (1 if merge_burden >= 3 and subtask.execution_group_kind == "support" else 0)
    )
    parallelism_confidence = (
        4
        if mode is OrchestrationMode.PARALLEL_BATCH and subtask.execution_group_kind == "primary" and not same_prefix_disjoint_exception
        else 3
        if mode is OrchestrationMode.PARALLEL_BATCH and subtask.execution_group_kind == "primary"
        else 2
        if subtask.execution_group_kind == "primary"
        else 1
    )
    if dependency_count >= 1:
        parallelism_confidence -= 1
    if merge_burden >= 3 and subtask.execution_group_kind == "support":
        parallelism_confidence -= 1
    parallelism_confidence = _clamp_confidence(parallelism_confidence)
    parallelism_hint = (
        "bounded_parallel_candidate"
        if mode is OrchestrationMode.PARALLEL_BATCH and subtask.execution_group_kind == "primary" and parallelism_confidence >= 3
        else "support_followup"
        if subtask.execution_group_kind == "support"
        else "serial_guarded"
        if same_prefix_disjoint_exception or dependency_count >= 1 or merge_burden >= 3
        else "serial_preferred"
    )
    reasoning_bias = (
        "guarded_narrowing"
        if not route_ready and subtask.execution_group_kind != "primary"
        else "deep_validation"
        if validation_pressure >= 3 or (subtask.scope_role == "validation" and validation_pressure >= 2)
        else "accuracy_first"
        if subtask.execution_group_kind == "primary"
        else "balanced"
    )
    risk_score = _clamp_confidence(
        (2 if subtask.correctness_critical else 0)
        + (1 if assessment.task_family == "critical_change" else 0)
        + (1 if subtask.scope_role in {"implementation", "contract"} else 0)
        + (1 if merge_burden >= 3 else 0)
        - (1 if subtask.scope_role in {"docs", "governance"} else 0)
    )
    parent_context_density_score = max(
        _int_value(_nested_mapping(base_packet_quality, "context_density").get("score")),
        _int_value(_mapping_lookup(base_optimization_quality_posture, "avg_context_density_score")),
    )
    parent_reasoning_readiness_score = max(
        _int_value(_nested_mapping(base_packet_quality, "reasoning_readiness").get("score")),
        _int_value(_mapping_lookup(base_optimization_quality_posture, "avg_reasoning_readiness_score")),
    )
    parent_evidence_diversity_score = max(
        _int_value(_nested_mapping(base_packet_quality, "evidence_diversity").get("score")),
        _int_value(_mapping_lookup(base_optimization_quality_posture, "avg_evidence_diversity_score")),
    )
    odylith_execution_profile = _subtask_odylith_execution_profile(
        request=request,
        assessment=assessment,
        subtask=subtask,
        intent_profile=intent_profile,
        architecture_audit=base_architecture_audit,
        base_root=base_root,
        base_context_packet=base_context_packet,
        base_optimization_snapshot=base_optimization_snapshot,
        route_ready=route_ready,
        narrowing_required=narrowing_required,
        validation_pressure=validation_pressure,
        utility_score=utility_score,
        token_efficiency_score=token_efficiency_score,
        routing_confidence_score=routing_confidence_score,
        spawn_worthiness=spawn_worthiness,
        merge_burden=merge_burden,
    )
    recommended_commands = _dedupe_strings(
        [
            *_normalize_list(_mapping_lookup(base_validation_bundle, "recommended_commands")),
            *subtask.validation_commands,
        ]
    )
    overlay = {
        "routing_handoff": {
            "grounding": {
                "grounded": request.evidence_cone_grounded,
                "score": 4 if request.evidence_cone_grounded else 0,
            },
            "odylith_execution_profile": odylith_execution_profile,
            "packet_quality": {
                "evidence_quality": evidence_quality_score,
                "actionability": actionability_score,
                "validation_pressure": validation_pressure,
                "reasoning_bias": reasoning_bias,
                "parallelism_hint": parallelism_hint,
                "context_density": {
                    "score": max(parent_context_density_score, 1 if scope_size >= 1 else 0),
                    "level": _score_level(max(parent_context_density_score, 1 if scope_size >= 1 else 0)),
                },
                "reasoning_readiness": {
                    "score": max(parent_reasoning_readiness_score, 2 if route_ready else 1 if spawn_worthiness >= 2 else 0),
                    "level": _score_level(
                        max(parent_reasoning_readiness_score, 2 if route_ready else 1 if spawn_worthiness >= 2 else 0)
                    ),
                    "mode": str(odylith_execution_profile.get("selection_mode", "")).strip(),
                    "deep_reasoning_ready": bool(
                        _nested_mapping(odylith_execution_profile, "constraints").get("reasoning_readiness_score", 0)
                    )
                    >= 3,
                },
                "evidence_diversity": {
                    "score": parent_evidence_diversity_score,
                    "level": _score_level(parent_evidence_diversity_score),
                }
                if parent_evidence_diversity_score
                else {},
                "utility_profile": {
                    "score": utility_score,
                    "level": utility_level,
                    "retained_signal_count": retained_signal_count,
                    "density_per_1k_tokens": density_per_1k_tokens,
                    "token_efficiency": {
                        "score": token_efficiency_score,
                        "level": token_efficiency_level,
                    },
                },
                "intent_profile": intent_profile,
                "native_spawn_ready": True,
            },
            "route_ready": route_ready,
            "narrowing_required": narrowing_required,
            "routing_confidence": _score_level(routing_confidence_score),
            "validation": {
                "burden": validation_pressure,
            },
            "parallelism": {
                "confidence": parallelism_confidence,
                "hint": parallelism_hint,
                "same_prefix_disjoint_exception": same_prefix_disjoint_exception,
                "merge_burden": merge_burden,
            },
            "architecture": {
                "active": bool(base_architecture_audit),
                "confidence_tier": str(_mapping_lookup(base_architecture_coverage, "confidence_tier") or "").strip(),
                "full_scan_recommended": bool(_mapping_lookup(base_architecture_audit, "full_scan_recommended")),
                "execution_mode": str(_mapping_lookup(base_architecture_execution_hint, "mode") or "").strip(),
                "fanout": str(_mapping_lookup(base_architecture_execution_hint, "fanout") or "").strip(),
                "risk_tier": str(_mapping_lookup(base_architecture_execution_hint, "risk_tier") or "").strip(),
            },
            "risk": {
                "score": risk_score,
            },
            "utility": {
                "score": utility_signal_score,
                "level": utility_level,
                "density_per_1k_tokens": density_per_1k_tokens,
                "token_efficiency": {
                    "score": token_efficiency_score,
                    "level": token_efficiency_level,
                },
            },
            "intent": intent_profile,
            "orchestration": {
                "scope_role": subtask.scope_role,
                "group_kind": subtask.execution_group_kind,
                "support_leaf": subtask.execution_group_kind == "support",
                "primary_parallel_safe": mode is OrchestrationMode.PARALLEL_BATCH
                and subtask.execution_group_kind == "primary",
                "same_prefix_disjoint_exception": same_prefix_disjoint_exception,
                "dependency_count": dependency_count,
                "primary_group_count": primary_count,
                "support_group_count": support_count,
                "merge_burden": merge_burden,
                "coordination_complexity": coordination_complexity,
                "spawn_worthiness": spawn_worthiness,
            },
        },
        "context_packet": {
            "contract": str(base_context_packet.get("contract", "")).strip() or "context_packet.v1",
            "packet_kind": str(base_context_packet.get("packet_kind", "")).strip(),
            "packet_state": str(base_context_packet.get("packet_state", "")).strip(),
            "route": {
                "route_ready": route_ready,
                "narrowing_required": narrowing_required,
                "reasoning_bias": reasoning_bias,
                "parallelism_hint": parallelism_hint,
            },
            "execution_profile": {
                key: value
                for key, value in {
                    "profile": str(odylith_execution_profile.get("profile", "")).strip(),
                    "model": str(odylith_execution_profile.get("model", "")).strip(),
                    "reasoning_effort": str(odylith_execution_profile.get("reasoning_effort", "")).strip(),
                    "agent_role": str(odylith_execution_profile.get("agent_role", "")).strip(),
                    "selection_mode": str(odylith_execution_profile.get("selection_mode", "")).strip(),
                    "delegate_preference": str(odylith_execution_profile.get("delegate_preference", "")).strip(),
                    "signals": dict(odylith_execution_profile.get("signals", {}))
                    if isinstance(odylith_execution_profile.get("signals", {}), Mapping)
                    else {},
                }.items()
                if value not in ("", [], {}, None)
            },
            "subtask": {
                "scope_role": subtask.scope_role,
                "group_kind": subtask.execution_group_kind,
                "dependency_count": dependency_count,
                "owned_paths": list(subtask.owned_paths),
                "read_paths": list(subtask.read_paths),
            },
            "optimization": {
                "utility_score": utility_score,
                "utility_level": utility_level,
                "token_efficiency_score": token_efficiency_score,
                "token_efficiency_level": token_efficiency_level,
                "spawn_worthiness": spawn_worthiness,
            },
        },
        "evidence_pack": {
            "contract": str(base_evidence_pack.get("contract", "")).strip() or "evidence_pack.v1",
            "subtask": {
                "scope_role": subtask.scope_role,
                "group_kind": subtask.execution_group_kind,
                "owned_paths": list(subtask.owned_paths),
            },
            "routing_handoff": {
                "route_ready": route_ready,
                "routing_confidence": _score_level(routing_confidence_score),
                "intent": intent_profile,
                "odylith_execution_profile": {
                    key: value
                    for key, value in {
                        "profile": str(odylith_execution_profile.get("profile", "")).strip(),
                        "reasoning_effort": str(odylith_execution_profile.get("reasoning_effort", "")).strip(),
                        "selection_mode": str(odylith_execution_profile.get("selection_mode", "")).strip(),
                        "signals": dict(odylith_execution_profile.get("signals", {}))
                        if isinstance(odylith_execution_profile.get("signals", {}), Mapping)
                        else {},
                    }.items()
                    if value not in ("", [], {}, None)
                },
                "optimization": {
                    "utility_score": utility_signal_score,
                    "utility_level": utility_level,
                    "token_efficiency": {
                        "score": token_efficiency_score,
                        "level": token_efficiency_level,
                    },
                },
            },
        },
        "optimization_snapshot": {
            "contract": str(base_optimization_snapshot.get("contract", "")).strip() or "optimization_snapshot.v1",
            "version": str(base_optimization_snapshot.get("version", "")).strip() or "v1",
            "status": str(base_optimization_snapshot.get("status", "")).strip() or "active",
            "overall": {
                key: value
                for key, value in {
                    "score": _float_value(_mapping_lookup(base_optimization_overall, "score")),
                    "level": str(_mapping_lookup(base_optimization_overall, "level") or "").strip(),
                }.items()
                if value not in ("", [], {}, None, 0, 0.0)
            },
            "packet_posture": {
                key: value
                for key, value in {
                    "avg_bytes": _float_value(_mapping_lookup(base_optimization_packet_posture, "avg_bytes")),
                    "avg_tokens": _float_value(_mapping_lookup(base_optimization_packet_posture, "avg_tokens")),
                    "within_budget_rate": round(_normalized_rate(_mapping_lookup(base_optimization_packet_posture, "within_budget_rate")), 3),
                    "state_distribution": dict(_mapping_lookup(base_optimization_packet_posture, "state_distribution") or {}),
                    "context_richness_distribution": dict(
                        _mapping_lookup(base_optimization_packet_posture, "context_richness_distribution") or {}
                    ),
                }.items()
                if value not in ("", [], {}, None, 0, 0.0)
            },
            "quality_posture": {
                key: value
                for key, value in {
                    "avg_utility_score": _float_value(_mapping_lookup(base_optimization_quality_posture, "avg_utility_score")),
                    "avg_density_per_1k_tokens": _float_value(
                        _mapping_lookup(base_optimization_quality_posture, "avg_density_per_1k_tokens")
                    ),
                    "avg_context_density_score": _float_value(
                        _mapping_lookup(base_optimization_quality_posture, "avg_context_density_score")
                    ),
                    "avg_reasoning_readiness_score": _float_value(
                        _mapping_lookup(base_optimization_quality_posture, "avg_reasoning_readiness_score")
                    ),
                    "avg_evidence_diversity_score": _float_value(
                        _mapping_lookup(base_optimization_quality_posture, "avg_evidence_diversity_score")
                    ),
                    "high_utility_rate": round(_normalized_rate(_mapping_lookup(base_optimization_quality_posture, "high_utility_rate")), 3),
                    "route_ready_rate": round(_normalized_rate(_mapping_lookup(base_optimization_quality_posture, "route_ready_rate")), 3),
                    "native_spawn_ready_rate": round(
                        _normalized_rate(_mapping_lookup(base_optimization_quality_posture, "native_spawn_ready_rate")),
                        3,
                    ),
                    "deep_reasoning_ready_rate": round(
                        _normalized_rate(_mapping_lookup(base_optimization_quality_posture, "deep_reasoning_ready_rate")),
                        3,
                    ),
                    "context_density_distribution": dict(
                        _mapping_lookup(base_optimization_quality_posture, "context_density_distribution") or {}
                    ),
                    "reasoning_readiness_distribution": dict(
                        _mapping_lookup(base_optimization_quality_posture, "reasoning_readiness_distribution") or {}
                    ),
                    "reasoning_mode_distribution": dict(
                        _mapping_lookup(base_optimization_quality_posture, "reasoning_mode_distribution") or {}
                    ),
                    "evidence_diversity_distribution": dict(
                        _mapping_lookup(base_optimization_quality_posture, "evidence_diversity_distribution") or {}
                    ),
                }.items()
                if value not in ("", [], {}, None, 0, 0.0)
            },
            "orchestration_posture": {
                key: value
                for key, value in {
                    "delegated_lane_rate": round(
                        _normalized_rate(_mapping_lookup(base_optimization_orchestration_posture, "delegated_lane_rate")),
                        3,
                    ),
                    "hold_local_rate": round(
                        _normalized_rate(_mapping_lookup(base_optimization_orchestration_posture, "hold_local_rate")),
                        3,
                    ),
                    "high_execution_confidence_rate": round(
                        _normalized_rate(
                            _mapping_lookup(base_optimization_orchestration_posture, "high_execution_confidence_rate")
                        ),
                        3,
                    ),
                    "runtime_backed_execution_rate": round(
                        _normalized_rate(
                            _mapping_lookup(base_optimization_orchestration_posture, "runtime_backed_execution_rate")
                        ),
                        3,
                    ),
                    "odylith_execution_profile_distribution": dict(
                        _mapping_lookup(base_optimization_orchestration_posture, "odylith_execution_profile_distribution")
                        or {}
                    ),
                    "odylith_execution_selection_mode_distribution": dict(
                        _mapping_lookup(
                            base_optimization_orchestration_posture,
                            "odylith_execution_selection_mode_distribution",
                        )
                        or {}
                    ),
                    "odylith_execution_delegate_preference_distribution": dict(
                        _mapping_lookup(
                            base_optimization_orchestration_posture,
                            "odylith_execution_delegate_preference_distribution",
                        )
                        or {}
                    ),
                    "odylith_execution_source_distribution": dict(
                        _mapping_lookup(base_optimization_orchestration_posture, "odylith_execution_source_distribution")
                        or {}
                    ),
                }.items()
                if value not in ("", [], {}, None, 0, 0.0)
            },
            "intent_posture": {
                key: value
                for key, value in {
                    "top_family": str(_mapping_lookup(base_optimization_intent_posture, "top_family") or "").strip(),
                    "explicit_rate": round(_normalized_rate(_mapping_lookup(base_optimization_intent_posture, "explicit_rate")), 3),
                    "high_confidence_rate": round(
                        _normalized_rate(_mapping_lookup(base_optimization_intent_posture, "high_confidence_rate")),
                        3,
                    ),
                    "family_distribution": dict(_mapping_lookup(base_optimization_intent_posture, "family_distribution") or {}),
                    "mode_distribution": dict(_mapping_lookup(base_optimization_intent_posture, "mode_distribution") or {}),
                    "critical_path_distribution": dict(
                        _mapping_lookup(base_optimization_intent_posture, "critical_path_distribution") or {}
                    ),
                }.items()
                if value not in ("", [], {}, None, 0, 0.0)
            },
            "latency_posture": {
                key: value
                for key, value in {
                    operation: dict(metrics)
                    for operation, metrics in base_optimization_latency_posture.items()
                    if isinstance(metrics, Mapping)
                }.items()
                if value not in ("", [], {}, None)
            },
            "evaluation_posture": {
                key: value
                for key, value in {
                    "packet_events": {
                        "benchmark_satisfaction_rate": round(
                            _normalized_rate(_mapping_lookup(base_evaluation_packet_posture, "benchmark_satisfaction_rate")),
                            3,
                        ),
                    },
                    "router_outcomes": {
                        "acceptance_rate": round(
                            _normalized_rate(_mapping_lookup(base_evaluation_router_posture, "acceptance_rate")),
                            3,
                        ),
                        "failure_rate": round(
                            _normalized_rate(_mapping_lookup(base_evaluation_router_posture, "failure_rate")),
                            3,
                        ),
                        "escalation_rate": round(
                            _normalized_rate(_mapping_lookup(base_evaluation_router_posture, "escalation_rate")),
                            3,
                        ),
                    },
                    "orchestration_feedback": {
                        "token_efficiency_rate": round(
                            _normalized_rate(_mapping_lookup(base_evaluation_orchestration_posture, "token_efficiency_rate")),
                            3,
                        ),
                        "parallel_failure_rate": round(
                            _normalized_rate(_mapping_lookup(base_evaluation_orchestration_posture, "parallel_failure_rate")),
                            3,
                        ),
                    },
                    "trend_posture": {
                        "learning_state": str(_mapping_lookup(base_evaluation_trend_posture, "learning_state") or "").strip(),
                        "packet_trend": str(_mapping_lookup(base_evaluation_trend_posture, "packet_trend") or "").strip(),
                        "router_trend": str(_mapping_lookup(base_evaluation_trend_posture, "router_trend") or "").strip(),
                        "orchestration_trend": str(_mapping_lookup(base_evaluation_trend_posture, "orchestration_trend") or "").strip(),
                        "signal_conflict": bool(_mapping_lookup(base_evaluation_trend_posture, "signal_conflict")),
                    },
                    "control_posture": {
                        "depth": str(_mapping_lookup(base_evaluation_control_posture, "depth") or "").strip(),
                        "delegation": str(_mapping_lookup(base_evaluation_control_posture, "delegation") or "").strip(),
                        "parallelism": str(_mapping_lookup(base_evaluation_control_posture, "parallelism") or "").strip(),
                        "packet_strategy": str(
                            _mapping_lookup(base_evaluation_control_posture, "packet_strategy") or ""
                        ).strip(),
                    },
                    "freshness": dict(base_evaluation_freshness),
                    "evidence_strength": dict(base_evaluation_evidence_strength),
                    "control_advisories": {
                        "state": str(merged_control_advisories.get("state", "")).strip(),
                        "confidence": dict(merged_control_advisories.get("confidence", {}))
                        if isinstance(merged_control_advisories.get("confidence", {}), Mapping)
                        else {},
                        "reasoning_mode": str(merged_control_advisories.get("reasoning_mode", "")).strip(),
                        "depth": str(merged_control_advisories.get("depth", "")).strip(),
                        "delegation": str(merged_control_advisories.get("delegation", "")).strip(),
                        "parallelism": str(merged_control_advisories.get("parallelism", "")).strip(),
                        "packet_strategy": str(merged_control_advisories.get("packet_strategy", "")).strip(),
                        "budget_mode": str(merged_control_advisories.get("budget_mode", "")).strip(),
                        "retrieval_focus": str(merged_control_advisories.get("retrieval_focus", "")).strip(),
                        "speed_mode": str(merged_control_advisories.get("speed_mode", "")).strip(),
                        "freshness": dict(merged_control_advisories.get("freshness", {}))
                        if isinstance(merged_control_advisories.get("freshness", {}), Mapping)
                        else {},
                        "evidence_strength": dict(merged_control_advisories.get("evidence_strength", {}))
                        if isinstance(merged_control_advisories.get("evidence_strength", {}), Mapping)
                        else {},
                        "signal_conflict": bool(merged_control_advisories.get("signal_conflict")),
                        "focus_areas": list(merged_control_advisories.get("focus_areas", []))
                        if isinstance(merged_control_advisories.get("focus_areas", []), list)
                        else [],
                        "regressions": list(merged_control_advisories.get("regressions", []))
                        if isinstance(merged_control_advisories.get("regressions", []), list)
                        else [],
                    },
                }.items()
                if value not in ("", [], {}, None)
            },
            "learning_loop": {
                key: value
                for key, value in {
                    "state": str(base_optimization_learning_loop.get("state", "")).strip(),
                    "event_count": _int_value(base_optimization_learning_loop.get("event_count")),
                    "freshness": dict(base_learning_freshness or base_evaluation_freshness),
                    "evidence_strength": dict(base_learning_evidence_strength or base_evaluation_evidence_strength),
                    "control_posture": {
                        "depth": str(_nested_mapping(base_optimization_learning_loop, "control_posture").get("depth", "")).strip(),
                        "delegation": str(
                            _nested_mapping(base_optimization_learning_loop, "control_posture").get("delegation", "")
                        ).strip(),
                        "parallelism": str(
                            _nested_mapping(base_optimization_learning_loop, "control_posture").get("parallelism", "")
                        ).strip(),
                        "packet_strategy": str(
                            _nested_mapping(base_optimization_learning_loop, "control_posture").get("packet_strategy", "")
                        ).strip(),
                    },
                    "control_advisories": {
                        "state": str(merged_control_advisories.get("state", "")).strip(),
                        "confidence": dict(merged_control_advisories.get("confidence", {}))
                        if isinstance(merged_control_advisories.get("confidence", {}), Mapping)
                        else {},
                        "reasoning_mode": str(merged_control_advisories.get("reasoning_mode", "")).strip(),
                        "depth": str(merged_control_advisories.get("depth", "")).strip(),
                        "delegation": str(merged_control_advisories.get("delegation", "")).strip(),
                        "parallelism": str(merged_control_advisories.get("parallelism", "")).strip(),
                        "packet_strategy": str(merged_control_advisories.get("packet_strategy", "")).strip(),
                        "budget_mode": str(merged_control_advisories.get("budget_mode", "")).strip(),
                        "retrieval_focus": str(merged_control_advisories.get("retrieval_focus", "")).strip(),
                        "speed_mode": str(merged_control_advisories.get("speed_mode", "")).strip(),
                        "freshness": dict(merged_control_advisories.get("freshness", {}))
                        if isinstance(merged_control_advisories.get("freshness", {}), Mapping)
                        else {},
                        "evidence_strength": dict(merged_control_advisories.get("evidence_strength", {}))
                        if isinstance(merged_control_advisories.get("evidence_strength", {}), Mapping)
                        else {},
                        "signal_conflict": bool(merged_control_advisories.get("signal_conflict")),
                        "focus_areas": list(merged_control_advisories.get("focus_areas", []))
                        if isinstance(merged_control_advisories.get("focus_areas", []), list)
                        else [],
                        "regressions": list(merged_control_advisories.get("regressions", []))
                        if isinstance(merged_control_advisories.get("regressions", []), list)
                        else [],
                    },
                }.items()
                if value not in ("", [], {}, None, 0, 0.0)
            },
            "control_advisories": {
                key: value
                for key, value in {
                    "state": str(merged_control_advisories.get("state", "")).strip(),
                    "confidence": dict(merged_control_advisories.get("confidence", {}))
                    if isinstance(merged_control_advisories.get("confidence", {}), Mapping)
                    else {},
                    "reasoning_mode": str(merged_control_advisories.get("reasoning_mode", "")).strip(),
                    "depth": str(merged_control_advisories.get("depth", "")).strip(),
                    "delegation": str(merged_control_advisories.get("delegation", "")).strip(),
                    "parallelism": str(merged_control_advisories.get("parallelism", "")).strip(),
                    "packet_strategy": str(merged_control_advisories.get("packet_strategy", "")).strip(),
                    "budget_mode": str(merged_control_advisories.get("budget_mode", "")).strip(),
                    "retrieval_focus": str(merged_control_advisories.get("retrieval_focus", "")).strip(),
                    "speed_mode": str(merged_control_advisories.get("speed_mode", "")).strip(),
                    "freshness": dict(merged_control_advisories.get("freshness", {}))
                    if isinstance(merged_control_advisories.get("freshness", {}), Mapping)
                    else {},
                    "evidence_strength": dict(merged_control_advisories.get("evidence_strength", {}))
                    if isinstance(merged_control_advisories.get("evidence_strength", {}), Mapping)
                    else {},
                    "signal_conflict": bool(merged_control_advisories.get("signal_conflict")),
                    "focus_areas": list(merged_control_advisories.get("focus_areas", []))
                    if isinstance(merged_control_advisories.get("focus_areas", []), list)
                    else [],
                    "regressions": list(merged_control_advisories.get("regressions", []))
                    if isinstance(merged_control_advisories.get("regressions", []), list)
                    else [],
                }.items()
                if value not in ("", [], {}, None)
            },
            "execution_profile": odylith_execution_profile,
            "subtask": {
                "scope_role": subtask.scope_role,
                "group_kind": subtask.execution_group_kind,
                "spawn_worthiness": spawn_worthiness,
                "route_ready": route_ready,
                "utility_score": utility_score,
                "token_efficiency_score": token_efficiency_score,
            },
        },
        "validation_bundle": {
            **{
                key: value
                for key, value in base_validation_bundle.items()
                if key not in {"recommended_commands", "strict_gate_commands"}
            },
            "recommended_commands": recommended_commands,
            "strict_gate_commands": strict_gate_commands,
            "plan_binding_required": bool(_mapping_lookup(base_validation_bundle, "plan_binding_required")),
            "governed_surface_sync_required": bool(
                _mapping_lookup(base_validation_bundle, "governed_surface_sync_required")
            ),
        }
        if (base_validation_bundle or recommended_commands or strict_gate_commands)
        else {},
        "governance_obligations": dict(base_governance_obligations) if base_governance_obligations else {},
        "surface_refs": dict(base_surface_refs) if base_surface_refs else {},
    }
    return _merge_context_signals(base, overlay)
