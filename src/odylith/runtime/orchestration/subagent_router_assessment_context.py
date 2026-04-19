"""Context-driven score adjustments for subagent router assessment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from odylith.runtime.orchestration import subagent_router as router
from odylith.runtime.orchestration import subagent_router_signal_summary as signal_summary


@dataclass
class AssessmentState:
    ambiguity: int
    blast_radius: int
    context_breadth: int
    coordination_cost: int
    reversibility_risk: int
    mechanicalness: int
    write_scope_clarity: int
    acceptance_clarity: int
    artifact_specificity: int
    validation_clarity: int
    latency_pressure: int
    requested_depth: int
    accuracy_bias: int
    feature_reasons: dict[str, list[str]] = field(default_factory=dict)
    base_confidence_boost: bool = False
    history_effective_yield_score: float = 0.0
    history_high_yield_rate: float = 0.0
    history_reliable_high_yield_rate: float = 0.0
    history_yield_state: str = ""
    control_advisory_guarded: bool = False
    packet_profile_guarded: bool = False
    runtime_narrowing_required: bool = False


def apply_context_signal_adjustments(
    *,
    request: router.RouteRequest,
    context_signal_summary: Mapping[str, Any],
    state: AssessmentState,
    explicit_path_count: int,
    has_structured_handoff: bool,
    needs_write: bool,
) -> None:
    ambiguity = state.ambiguity
    blast_radius = state.blast_radius
    context_breadth = state.context_breadth
    coordination_cost = state.coordination_cost
    reversibility_risk = state.reversibility_risk
    mechanicalness = state.mechanicalness
    write_scope_clarity = state.write_scope_clarity
    acceptance_clarity = state.acceptance_clarity
    artifact_specificity = state.artifact_specificity
    validation_clarity = state.validation_clarity
    latency_pressure = state.latency_pressure
    requested_depth = state.requested_depth
    accuracy_bias = state.accuracy_bias
    feature_reasons = state.feature_reasons
    base_confidence_boost = state.base_confidence_boost
    base_confidence_boost = False
    if context_signal_summary["grounding_score"] >= 3 and context_signal_summary["evidence_quality_score"] >= 3:
        ambiguity = signal_summary._clamp_score(ambiguity - 1)
        feature_reasons.setdefault("grounding", []).append(
            "routing_handoff reported grounded high-quality evidence, so ambiguity was reduced"
        )
    if context_signal_summary["actionability_score"] >= 3:
        if needs_write:
            write_scope_clarity = signal_summary._clamp_score(write_scope_clarity + 1)
            acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported actionable bounded context for this slice"
        )
    if context_signal_summary["validation_burden_score"] >= 3:
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "routing_handoff reported a heavier validation burden that merits deeper reasoning"
        )
    if context_signal_summary["coordination_score"] >= 3:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append(
            "routing_handoff reported higher coordination or merge burden than the prompt alone exposed"
        )
    if context_signal_summary["risk_score"] >= 3:
        blast_radius = signal_summary._clamp_score(blast_radius + 1)
        reversibility_risk = signal_summary._clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported elevated correctness or change risk"
        )
    if context_signal_summary["utility_score"] >= 3:
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported a high-value retained context set for this slice"
        )
    if context_signal_summary["token_efficiency_score"] >= 3:
        latency_pressure = signal_summary._clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported strong evidence value per retained token"
        )
    if context_signal_summary["optimization_health_score"] >= 3:
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
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
    history_high_yield_rate = signal_summary._normalized_rate(context_signal_summary["optimization_high_yield_rate"])
    history_reliable_high_yield_rate = signal_summary._normalized_rate(
        context_signal_summary["optimization_reliable_high_yield_rate"]
    )
    history_yield_state = signal_summary._normalize_token(context_signal_summary["optimization_yield_state"])
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
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        if not request.correctness_critical and requested_depth >= 2:
            requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are fresh-evidence guarded, so the router reduced trust in historical promotion signals until newer or better-balanced outcomes accumulate"
        )
    elif packet_profile_guarded and not control_advisory_present:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        if not request.correctness_critical and requested_depth >= 2:
            requested_depth = signal_summary._clamp_score(requested_depth - 1)
        if accuracy_bias >= 2:
            accuracy_bias = signal_summary._clamp_score(accuracy_bias - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet was assembled under guarded reliability, so the router stayed conservative until fresher packet evidence lands"
        )
    if history_budget_reliable:
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "optimization history shows recent packets stay within budget while retaining useful evidence"
        )
    if history_execution_reliable:
        acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
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
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "optimization history shows deeper delegated reasoning stays grounded, budget-safe, and runtime-backed on similar slices"
        )
    elif (
        not request.correctness_critical
        and requested_depth >= 3
        and 0.0 < context_signal_summary["optimization_deep_reasoning_ready_rate"] < 0.5
        and context_signal_summary["optimization_within_budget_rate"] < 0.5
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "recent optimization history shows deeper delegated reasoning still overruns budget or lacks readiness on similar slices"
        )
    if history_prefers_local and (context_signal_summary["narrowing_required"] or not context_signal_summary["route_ready"]):
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent optimization history still trends toward hold-local execution while narrowing remains unresolved"
        )
    if (
        context_signal_summary["optimization_packet_alignment_state"] == "drifting"
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent packetizer alignment is drifting from the measured advisory loop, so the router reduced depth until packet shaping stabilizes again"
        )
    evaluation_depth_promote = context_signal_summary["evaluation_control_depth"] == "promote_when_grounded"
    evaluation_narrow_first = context_signal_summary["evaluation_control_depth"] == "narrow_first"
    evaluation_hold_local_bias = context_signal_summary["evaluation_control_delegation"] == "hold_local_bias"
    evaluation_parallel_guarded = context_signal_summary["evaluation_control_parallelism"] == "guarded"
    evaluation_precision_first = context_signal_summary["evaluation_control_packet_strategy"] == "precision_first"
    evaluation_decision_quality_score = signal_summary._normalized_rate(
        context_signal_summary["evaluation_decision_quality_score"]
    )
    evaluation_decision_quality_state = signal_summary._normalize_token(
        context_signal_summary["evaluation_decision_quality_state"]
    )
    evaluation_decision_quality_confidence = signal_summary._clamp_score(
        context_signal_summary["evaluation_decision_quality_confidence_score"]
    )
    evaluation_closeout_observation_rate = signal_summary._normalized_rate(
        context_signal_summary["evaluation_closeout_observation_rate"]
    )
    evaluation_delegation_regret_rate = signal_summary._normalized_rate(
        context_signal_summary["evaluation_delegation_regret_rate"]
    )
    evaluation_followup_churn_rate = signal_summary._normalized_rate(
        context_signal_summary["evaluation_followup_churn_rate"]
    )
    evaluation_merge_underestimate_rate = signal_summary._normalized_rate(
        context_signal_summary["evaluation_merge_underestimate_rate"]
    )
    evaluation_validation_underestimate_rate = signal_summary._normalized_rate(
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
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently endorse deeper reasoning on grounded route-ready slices"
        )
    if control_advisory_depth == "narrow_first" and not request.correctness_critical:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently prefer narrow-first execution because recent outcomes are still unstable"
        )
    if (
        decision_quality_reliable
        and evaluation_validation_underestimate_rate >= 0.25
        and not request.correctness_critical
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
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
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "Control advisories say deeper reasoning has to be earned, and this slice currently meets that bar"
        )
    elif control_advisory_reasoning_mode == "guarded_narrowing" and not request.correctness_critical:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories still want guarded narrowing before spending extra depth"
        )
    if (
        control_advisory_delegation == "hold_local_bias"
        and (context_signal_summary["narrowing_required"] or ambiguity >= 2)
    ):
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
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
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        if not request.correctness_critical:
            requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence shows delegation regret or follow-up churn after execution, so the router is biasing toward tighter delegated scope"
        )
    if control_advisory_parallelism == "guarded" and explicit_path_count >= 2:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are guarding parallelism because recent execution still shows merge risk"
        )
    if decision_quality_reliable and evaluation_merge_underestimate_rate >= 0.2 and explicit_path_count >= 2:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is still underpredicting merge burden on recent delegated slices, so the router is staying conservative on fan-out"
        )
    if decision_quality_fragile and not request.correctness_critical:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
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
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently prefer precision-first packets over spending depth on shallow evidence cones"
        )
    if (
        control_advisory_budget_mode == "tight"
        and not request.correctness_critical
        and requested_depth >= 2
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        latency_pressure = signal_summary._clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are in tight-budget mode, so the router reduced early reasoning spend"
        )
    elif (
        control_advisory_budget_mode == "spend_when_grounded"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "Control advisories allow extra depth when the slice is grounded and route-ready"
        )
    if control_advisory_speed_mode == "accelerate_grounded" and control_advisory_reliable and context_signal_summary["route_ready"]:
        latency_pressure = signal_summary._clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently favor faster execution on grounded slices"
        )
    elif control_advisory_speed_mode == "conserve" and not request.correctness_critical:
        latency_pressure = signal_summary._clamp_score(latency_pressure + 1)
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
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("requested_depth", []).append(
            "recent packets are earning strong grounded signal per budget, so the router allowed extra depth on this route-ready slice"
        )
    elif history_yield_state == "wasteful" and not request.correctness_critical:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        latency_pressure = signal_summary._clamp_score(latency_pressure + 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent packets are still low-yield for their spend, so the router reduced depth until denser grounded evidence returns"
        )
    if control_advisory_retrieval_focus == "expand_coverage" and artifact_specificity <= 2:
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories want broader evidence coverage before the router commits to a narrow delegated slice"
        )
    elif control_advisory_retrieval_focus == "precision_repair" and artifact_specificity <= 2:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories want tighter anchor repair before extra reasoning depth"
        )
    if (
        not control_advisory_present
        and packet_profile_present
        and packet_strategy == "precision_first"
        and context_signal_summary["context_density_score"] <= 2
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained packet is already in precision-first mode, so the router avoided spending extra depth on a still-shallow evidence cone"
        )
    if (
        not control_advisory_reliable
        and budget_mode == "tight"
        and not request.correctness_critical
        and requested_depth >= 2
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        latency_pressure = signal_summary._clamp_score(latency_pressure + 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is already budget-tight, so the router reduced early reasoning spend"
        )
    if not control_advisory_reliable and speed_mode == "conserve" and not request.correctness_critical:
        latency_pressure = signal_summary._clamp_score(latency_pressure + 1)
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
        latency_pressure = signal_summary._clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is reliable and accelerate-grounded, so the router allowed faster execution posture"
        )
    if (
        not control_advisory_present
        and retrieval_focus == "expand_coverage"
        and artifact_specificity <= 2
    ):
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
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
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is improving and currently endorses deeper reasoning on grounded route-ready slices"
        )
    if evaluation_narrow_first and not request.correctness_critical:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence currently prefers narrow-first control because recent benchmark or execution outcomes are not stable enough"
        )
    if evaluation_hold_local_bias and (context_signal_summary["narrowing_required"] or ambiguity >= 2):
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent evaluated delegation outcomes are not yet stable, so the router biased toward hold-local or tighter delegated slices"
        )
    if evaluation_parallel_guarded and explicit_path_count >= 2:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is guarding parallelism because recent orchestration outcomes showed merge or false-parallel regressions"
        )
    if evaluation_precision_first and context_signal_summary["context_density_score"] <= 2:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence currently prefers precision-first packets, so the router avoided spending extra depth on a still-shallow evidence cone"
        )
    if (
        context_signal_summary["evaluation_router_acceptance_rate"] >= 0.7
        and context_signal_summary["evaluation_benchmark_satisfaction_rate"] >= 0.6
        and context_signal_summary["evaluation_learning_state"] == "improving"
    ):
        acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent benchmark-linked execution outcomes are improving, so the router trusted the current bounded slice more strongly"
        )
    elif (
        context_signal_summary["evaluation_router_failure_rate"] >= 0.35
        or context_signal_summary["evaluation_router_escalation_rate"] >= 0.25
    ) and not request.correctness_critical:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        base_confidence_boost = False
        feature_reasons.setdefault("context_signals", []).append(
            "Recent evaluated router outcomes are still unstable, so the router stayed more conservative on first-pass delegation depth"
        )
    if (
        request.latency_sensitive
        and context_signal_summary["optimization_latency_pressure_score"] >= 3
        and not request.correctness_critical
    ):
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
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
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
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
        coordination_cost = signal_summary._clamp_score(coordination_cost - 1)
        acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
        validation_clarity = signal_summary._clamp_score(validation_clarity + 1)
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained governance closeout contract kept this bounded slice execution-ready despite the broader packet staying conservative"
        )
    if (
        context_signal_summary["context_packet_state"].startswith("gated_")
        and not context_signal_summary["bounded_governance_delegate_candidate"]
    ):
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
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
            artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
            if context_signal_summary["intent_explicit"]:
                write_scope_clarity = signal_summary._clamp_score(write_scope_clarity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried an implementation-first intent profile for this bounded write slice"
            )
        elif intent_family == "validation":
            validation_clarity = signal_summary._clamp_score(validation_clarity + 1)
            requested_depth = signal_summary._clamp_score(requested_depth + 1)
            accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "runtime handoff carried a validation-first intent profile for this slice"
            )
        elif intent_family in {"diagnosis", "analysis", "architecture", "review"} and not needs_write:
            requested_depth = signal_summary._clamp_score(requested_depth + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "runtime handoff carried an analysis-heavy intent profile that benefits from deeper synthesis"
            )
        elif intent_family == "docs" and not request.correctness_critical:
            mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
            blast_radius = signal_summary._clamp_score(blast_radius - 1)
            reversibility_risk = signal_summary._clamp_score(reversibility_risk - 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried a docs-alignment intent profile, so the router treated the slice as more mechanical"
            )
        elif intent_family == "governance" and not request.correctness_critical:
            mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried a governance-closeout intent profile for this slice"
                if not context_signal_summary["bounded_governance_delegate_candidate"]
                else "runtime handoff carried an explicit governance closeout contract, so the router treated bounded delegation as execution-ready"
            )
    if context_signal_summary["intent_critical_path"] == "narrow_first":
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as narrow-first, so the router stayed conservative"
        )
    elif context_signal_summary["intent_critical_path"] == "implementation_first" and needs_write:
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked implementation as the critical path for this slice"
        )
    elif context_signal_summary["intent_critical_path"] == "analysis_first" and not needs_write:
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff marked analysis as the critical path for this read-heavy slice"
        )
    elif context_signal_summary["intent_critical_path"] == "docs_after_write" and not request.correctness_critical:
        mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked docs alignment as a post-write follow-up, which favors lighter support routing"
        )
    elif context_signal_summary["intent_critical_path"] == "governance_local":
        if context_signal_summary["bounded_governance_delegate_candidate"]:
            acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
            validation_clarity = signal_summary._clamp_score(validation_clarity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff marked governance closeout as the critical path, but the retained validation and closeout contract was explicit enough to keep bounded delegation safe"
            )
        else:
            coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff marked governance closeout as the critical path, so the router preserved coordination margin"
            )
    if context_signal_summary["primary_leaf"]:
        if needs_write:
            write_scope_clarity = signal_summary._clamp_score(write_scope_clarity + 1)
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this as a primary implementation leaf with explicit owned paths"
        )
    if context_signal_summary["support_leaf"] and not request.correctness_critical:
        mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
        blast_radius = signal_summary._clamp_score(blast_radius - 1)
        reversibility_risk = signal_summary._clamp_score(reversibility_risk - 1)
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this as a support leaf, so the router downshifted toward lighter support tiers"
        )
    if context_signal_summary["reasoning_bias"] == "deep_validation":
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff requested deep validation reasoning for this bounded slice"
        )
    elif context_signal_summary["reasoning_bias"] == "accuracy_first" and needs_write:
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff preferred an accuracy-first reasoning posture for this write slice"
        )
    elif (
        context_signal_summary["reasoning_bias"] == "guarded_narrowing"
        and not context_signal_summary["bounded_governance_delegate_candidate"]
    ):
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff stayed in guarded narrowing mode, so the router treated the slice as less settled"
        )
    if (
        context_signal_summary["reasoning_readiness_score"] >= 3
        and context_signal_summary["context_density_score"] >= 2
        and context_signal_summary["route_ready"]
    ):
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported dense grounded context with high reasoning readiness, so the router allowed deeper bounded reasoning"
        )
    elif context_signal_summary["context_density_score"] <= 1 and context_signal_summary["narrowing_required"]:
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported shallow context density while narrowing is still required, so the router avoided spending extra depth early"
        )
    if context_signal_summary["evidence_diversity_score"] >= 2:
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff retained evidence from multiple distinct domains, which improved confidence in the bounded evidence cone"
        )
    if has_structured_handoff and context_signal_summary["spawn_worthiness_score"] >= 3:
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this leaf as highly spawn-worthy relative to its merge cost"
        )
    elif (
        has_structured_handoff
        and context_signal_summary["support_leaf"]
        and context_signal_summary["spawn_worthiness_score"] <= 1
        and not request.correctness_critical
    ):
        mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
        requested_depth = signal_summary._clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this support slice as low spawn-worthiness, so the router stayed light"
        )
    if context_signal_summary["routing_confidence_level"] == "high":
        artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported high routing confidence for the retained evidence set"
        )
    elif context_signal_summary["routing_confidence_level"] == "low":
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
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
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff preferred serial execution for this multi-path slice"
        )
    if has_structured_handoff and context_signal_summary["merge_burden_score"] >= 3:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported elevated merge burden for this slice"
        )
    odylith_recommended_profile = router._router_profile_from_token(context_signal_summary["odylith_execution_profile"])
    odylith_execution_confidence = int(context_signal_summary["odylith_execution_confidence_score"] or 0)
    if odylith_recommended_profile is not None and odylith_execution_confidence >= 2:
        if odylith_recommended_profile in {
            router.RouterProfile.CODEX_HIGH,
            router.RouterProfile.GPT54_HIGH,
            router.RouterProfile.GPT54_XHIGH,
        }:
            requested_depth = signal_summary._clamp_score(requested_depth + 1)
            accuracy_bias = signal_summary._clamp_score(accuracy_bias + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "odylith execution profile recommended a deeper coding or GPT-5.4 tier for this bounded slice"
            )
        elif odylith_recommended_profile in {
            router.RouterProfile.MINI_MEDIUM,
            router.RouterProfile.SPARK_MEDIUM,
        } and context_signal_summary["support_leaf"] and not request.correctness_critical:
            mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
            requested_depth = signal_summary._clamp_score(requested_depth - 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile marked this slice as a lighter support or scout lane"
            )
        if (
            context_signal_summary["odylith_execution_delegate_preference"] == "hold_local"
            and (
                needs_write
                or odylith_recommended_profile is router.RouterProfile.MAIN_THREAD
                or context_signal_summary["odylith_execution_selection_mode"] in {"narrow_first", "guarded_narrowing"}
            )
        ):
            coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile still preferred local narrowing before bounded spawn"
            )
        if odylith_execution_confidence >= 3:
            base_confidence_boost = True
            artifact_specificity = signal_summary._clamp_score(artifact_specificity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile carried a high-confidence runtime recommendation for the delegated tier"
            )
    runtime_narrowing_required = bool(context_signal_summary["narrowing_required"] and not request.evidence_cone_grounded)
    if context_signal_summary["route_ready"]:
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff was already route-ready for native delegation"
        )
        if context_signal_summary["bounded_governance_delegate_candidate"]:
            validation_clarity = signal_summary._clamp_score(validation_clarity + 1)
            acceptance_clarity = signal_summary._clamp_score(acceptance_clarity + 1)
            base_confidence_boost = True
            feature_reasons.setdefault("context_signals", []).append(
                "governance closeout stayed route-ready with explicit plan-binding, validation, and sync obligations"
            )
    elif has_structured_handoff and context_signal_summary["spawn_worthiness_score"] <= 1:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff treated the slice as only conditionally route-ready, so the router stayed conservative"
        )


    state.ambiguity = ambiguity
    state.blast_radius = blast_radius
    state.context_breadth = context_breadth
    state.coordination_cost = coordination_cost
    state.reversibility_risk = reversibility_risk
    state.mechanicalness = mechanicalness
    state.write_scope_clarity = write_scope_clarity
    state.acceptance_clarity = acceptance_clarity
    state.artifact_specificity = artifact_specificity
    state.validation_clarity = validation_clarity
    state.latency_pressure = latency_pressure
    state.requested_depth = requested_depth
    state.accuracy_bias = accuracy_bias
    state.base_confidence_boost = base_confidence_boost
    state.history_effective_yield_score = history_effective_yield_score
    state.history_high_yield_rate = history_high_yield_rate
    state.history_reliable_high_yield_rate = history_reliable_high_yield_rate
    state.history_yield_state = history_yield_state
    state.control_advisory_guarded = control_advisory_guarded
    state.packet_profile_guarded = packet_profile_guarded
    state.runtime_narrowing_required = runtime_narrowing_required
