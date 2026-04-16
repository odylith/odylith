"""Shared compact Odylith runtime summary for shell-owned surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from odylith.runtime.evaluation import odylith_benchmark_runner
from odylith.runtime.context_engine import odylith_context_engine_store


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _strings(value: Any, *, limit: int = 4) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def _merge_control_advisories(*sources: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key, value in source.items():
            if key not in merged or merged[key] in ("", [], {}, None):
                merged[key] = value
    return merged


def load_runtime_surface_summary(*, repo_root: Path) -> dict[str, Any]:
    """Return one bounded Odylith posture summary for Compass/Registry/shells."""

    try:
        optimization = odylith_context_engine_store.load_runtime_optimization_snapshot(repo_root=repo_root)
        evaluation = odylith_context_engine_store.load_runtime_evaluation_snapshot(repo_root=repo_root)
        memory = odylith_context_engine_store.load_runtime_memory_snapshot(
            repo_root=repo_root,
            optimization_snapshot=optimization,
            evaluation_snapshot=evaluation,
        )
    except Exception:
        return {
            "status": "unavailable",
            "enabled": False,
            "memory_status": "unavailable",
            "memory_backend_label": "Unavailable",
            "remote_label": "Unavailable",
            "memory_area_headline": "",
            "memory_area_gap_count": 0,
            "memory_area_counts": {},
            "judgment_memory_headline": "",
            "judgment_memory_gap_count": 0,
            "judgment_memory_counts": {},
            "sample_size": 0,
            "optimization_level": "",
            "optimization_score": 0.0,
            "avg_context_density_score": 0.0,
            "avg_reasoning_readiness_score": 0.0,
            "avg_evidence_diversity_score": 0.0,
            "deep_reasoning_ready_rate": 0.0,
            "route_ready_rate": 0.0,
            "native_spawn_ready_rate": 0.0,
            "memory_standardization_state": "",
            "memory_backend_actual": "",
            "memory_backend_target": "",
            "repo_scan_degraded_fallback_rate": 0.0,
            "repo_scan_degraded_reasons": {},
            "hard_grounding_failure_rate": 0.0,
            "hard_grounding_failure_reasons": {},
            "soft_widening_rate": 0.0,
            "soft_widening_reasons": {},
            "visible_fallback_receipt_rate": 0.0,
            "visible_fallback_receipt_reasons": {},
            "governance_runtime_first_usage_rate": 0.0,
            "governance_runtime_first_fallback_rate": 0.0,
            "governance_runtime_first_fallback_reasons": {},
            "evaluation_architecture_covered_case_count": 0,
            "evaluation_architecture_satisfied_case_count": 0,
            "evaluation_architecture_coverage_rate": 0.0,
            "evaluation_architecture_satisfaction_rate": 0.0,
            "delegated_lane_rate": 0.0,
            "hold_local_rate": 0.0,
            "high_execution_confidence_rate": 0.0,
            "runtime_backed_execution_rate": 0.0,
            "latest_packet_state": "",
            "latest_intent_family": "",
            "latest_packet_strategy": "",
            "latest_budget_mode": "",
            "latest_retrieval_focus": "",
            "latest_speed_mode": "",
            "latest_packet_reliability": "",
            "latest_selection_bias": "",
            "latest_advised_packet_strategy": "",
            "latest_advised_budget_mode": "",
            "latest_advised_retrieval_focus": "",
            "latest_advised_speed_mode": "",
            "effective_yield_score": 0.0,
            "high_yield_rate": 0.0,
            "reliable_high_yield_rate": 0.0,
            "yield_state": "",
            "packet_alignment_rate": 0.0,
            "reliable_packet_alignment_rate": 0.0,
            "packet_alignment_state": "",
            "latest_execution_profile": "",
            "latest_execution_mode": "",
            "latest_execution_delegate_preference": "",
            "latest_execution_source": "",
            "latest_execution_engine_present": False,
            "latest_execution_engine_outcome": "",
            "latest_execution_engine_requires_reanchor": False,
            "latest_execution_engine_mode": "",
            "latest_execution_engine_next_move": "",
            "latest_execution_engine_current_phase": "",
            "latest_execution_engine_last_successful_phase": "",
            "latest_execution_engine_blocker": "",
            "latest_execution_engine_closure": "",
            "latest_execution_engine_wait_status": "",
            "latest_execution_engine_wait_detail": "",
            "latest_execution_engine_resume_token": "",
            "latest_execution_engine_validation_archetype": "",
            "latest_execution_engine_validation_minimum_pass_count": 0,
            "latest_execution_engine_validation_derived_from": [],
            "latest_execution_engine_contradiction_count": 0,
            "latest_execution_engine_history_rule_count": 0,
            "latest_execution_engine_history_rule_hits": [],
            "latest_execution_engine_pressure_signals": [],
            "latest_execution_engine_nearby_denial_actions": [],
            "latest_execution_engine_authoritative_lane": "",
            "latest_execution_engine_host_family": "",
            "latest_execution_engine_model_family": "",
            "latest_execution_engine_host_supports_native_spawn": False,
            "latest_execution_engine_target_lane": "",
            "latest_execution_engine_candidate_target_count": 0,
            "latest_execution_engine_diagnostic_anchor_count": 0,
            "latest_execution_engine_has_writable_targets": False,
            "latest_execution_engine_requires_more_consumer_context": False,
            "latest_execution_engine_consumer_failover": "",
            "latest_execution_engine_commentary_mode": "",
            "latest_execution_engine_suppress_routing_receipts": False,
            "latest_execution_engine_surface_fast_lane": False,
            "latest_execution_engine_runtime_invalidated_by_step": "",
            "latest_turn_intent": "",
            "latest_turn_surface_count": 0,
            "latest_turn_visible_text_count": 0,
            "latest_turn_active_tab": "",
            "latest_turn_user_turn_id": "",
            "latest_turn_supersedes_turn_id": "",
            "advisory_state": "unavailable",
            "advisory_confidence_score": 0,
            "advisory_confidence_level": "",
            "advisory_reasoning_mode": "",
            "advisory_depth": "",
            "advisory_delegation": "",
            "advisory_parallelism": "",
            "advisory_packet_strategy": "",
            "advisory_budget_mode": "",
            "advisory_retrieval_focus": "",
            "advisory_speed_mode": "",
            "advisory_freshness_bucket": "",
            "advisory_freshness_age_hours": 0.0,
            "advisory_evidence_strength_score": 0,
            "advisory_evidence_strength_level": "",
            "advisory_sample_balance": "",
            "advisory_signal_conflict": False,
            "advisory_focus_areas": [],
            "advisory_regressions": [],
            "evaluation_learning_state": "",
            "evaluation_benchmark_satisfaction_rate": 0.0,
            "evaluation_router_acceptance_rate": 0.0,
            "evaluation_router_failure_rate": 0.0,
            "evaluation_orchestration_token_efficiency_rate": 0.0,
            "evaluation_orchestration_parallel_failure_rate": 0.0,
            "evaluation_decision_quality_score": 0.0,
            "evaluation_decision_quality_state": "",
            "evaluation_decision_quality_confidence_score": 0,
            "evaluation_decision_quality_confidence_level": "",
            "evaluation_decision_quality_sample_balance": "",
            "evaluation_closeout_observation_rate": 0.0,
            "evaluation_delegation_regret_rate": 0.0,
            "evaluation_clean_closeout_rate": 0.0,
            "evaluation_followup_churn_rate": 0.0,
            "evaluation_merge_calibration_rate": 0.0,
            "evaluation_validation_calibration_rate": 0.0,
            "evaluation_delegation_value_calibration_rate": 0.0,
            "evaluation_recommendations": [],
            "benchmark_status": "",
            "benchmark_scenario_count": 0,
            "benchmark_candidate_mode": "",
            "benchmark_baseline_mode": "",
            "benchmark_latency_delta_ms": 0.0,
            "benchmark_token_delta": 0.0,
            "benchmark_prompt_token_delta": 0.0,
            "benchmark_total_payload_token_delta": 0.0,
            "benchmark_runtime_contract_token_delta": 0.0,
            "benchmark_operator_diag_token_delta": 0.0,
            "benchmark_required_path_recall_delta": 0.0,
            "benchmark_validation_success_delta": 0.0,
        }

    odylith_switch = _mapping(memory.get("odylith_switch"))
    backend_transition = _mapping(memory.get("backend_transition"))
    memory_areas = _mapping(memory.get("memory_areas"))
    judgment_memory = _mapping(memory.get("judgment_memory"))
    actual_backend = _mapping(backend_transition.get("actual_local_backend"))
    remote_retrieval = _mapping(memory.get("remote_retrieval"))
    degraded_fallback_posture = _mapping(optimization.get("degraded_fallback_posture"))
    governance_runtime_first = _mapping(optimization.get("governance_runtime_first_posture"))
    overall = _mapping(optimization.get("overall"))
    quality_posture = _mapping(optimization.get("quality_posture"))
    orchestration_posture = _mapping(optimization.get("orchestration_posture"))
    packet_posture = _mapping(optimization.get("packet_posture"))
    latest_packet = _mapping(optimization.get("latest_packet"))
    evaluation_posture = _mapping(optimization.get("evaluation_posture"))
    evaluation_packet_posture = _mapping(evaluation_posture.get("packet_events"))
    evaluation_router_posture = _mapping(evaluation_posture.get("router_outcomes"))
    evaluation_orchestration_posture = _mapping(evaluation_posture.get("orchestration_feedback"))
    evaluation_decision_quality = _mapping(evaluation_posture.get("decision_quality"))
    evaluation_decision_quality_confidence = _mapping(evaluation_decision_quality.get("confidence"))
    evaluation_trend_posture = _mapping(evaluation_posture.get("trend_posture"))
    learning_loop = _mapping(optimization.get("learning_loop"))
    architecture_evaluation = _mapping(evaluation.get("architecture"))
    benchmark_report = odylith_benchmark_runner.compact_report_summary(
        odylith_benchmark_runner.load_latest_benchmark_report(repo_root=repo_root)
    )
    control_advisories = _merge_control_advisories(
        _mapping(optimization.get("control_advisories")),
        _mapping(evaluation_posture.get("control_advisories")),
        _mapping(learning_loop.get("control_advisories")),
    )
    advisory_confidence = _mapping(control_advisories.get("confidence"))
    advisory_freshness = _mapping(control_advisories.get("freshness"))
    advisory_evidence_strength = _mapping(control_advisories.get("evidence_strength"))

    storage = _string(actual_backend.get("storage"))
    sparse = _string(actual_backend.get("sparse_recall"))
    storage_label = {
        "lance_local_columnar": "Lance",
        "compiler_projection_snapshot": "Compiler Snapshot",
    }.get(storage, storage or "Unknown")
    sparse_label = {
        "tantivy_sparse_recall": "Tantivy",
        "repo_scan_fallback": "Repo Scan",
    }.get(sparse, sparse or "")
    remote_label = (
        "Disabled"
        if not bool(remote_retrieval.get("enabled"))
        else " / ".join(
            token
            for token in (
                _string(remote_retrieval.get("provider")),
                _string(remote_retrieval.get("mode")),
            )
            if token
        )
        or "Attached"
    )

    return {
        "status": _string(memory.get("status")) or "unknown",
        "enabled": bool(odylith_switch.get("enabled", True)),
        "memory_status": _string(backend_transition.get("status")) or _string(memory.get("status")),
        "memory_backend_label": " / ".join(token for token in (storage_label, sparse_label) if token) or "Unknown",
        "memory_standardization_state": _string(backend_transition.get("status")),
        "memory_backend_actual": " / ".join(
            token for token in (_string(actual_backend.get("storage")), _string(actual_backend.get("sparse_recall"))) if token
        ),
        "memory_backend_target": " / ".join(
            token
            for token in (
                _string(_mapping(backend_transition.get("target_local_backend")).get("storage")),
                _string(_mapping(backend_transition.get("target_local_backend")).get("sparse_recall")),
            )
            if token
        ),
        "remote_label": remote_label,
        "memory_area_headline": _string(memory_areas.get("headline")),
        "memory_area_gap_count": _int(memory_areas.get("gap_count")),
        "memory_area_counts": dict(memory_areas.get("counts", {}))
        if isinstance(memory_areas.get("counts"), Mapping)
        else {},
        "judgment_memory_headline": _string(judgment_memory.get("headline")),
        "judgment_memory_gap_count": _int(judgment_memory.get("gap_count")),
        "judgment_memory_counts": dict(judgment_memory.get("counts", {}))
        if isinstance(judgment_memory.get("counts"), Mapping)
        else {},
        "sample_size": _int(optimization.get("sample_size")),
        "optimization_level": _string(overall.get("level")),
        "optimization_score": _float(overall.get("score")),
        "avg_context_density_score": _float(quality_posture.get("avg_context_density_score")),
        "avg_reasoning_readiness_score": _float(quality_posture.get("avg_reasoning_readiness_score")),
        "avg_evidence_diversity_score": _float(quality_posture.get("avg_evidence_diversity_score")),
        "deep_reasoning_ready_rate": _float(quality_posture.get("deep_reasoning_ready_rate")),
        "route_ready_rate": _float(quality_posture.get("route_ready_rate")),
        "native_spawn_ready_rate": _float(quality_posture.get("native_spawn_ready_rate")),
        "repo_scan_degraded_fallback_rate": _float(
            degraded_fallback_posture.get("repo_scan_degraded_fallback_rate")
        ),
        "repo_scan_degraded_reasons": dict(
            degraded_fallback_posture.get("repo_scan_degraded_reason_distribution", {})
        )
        if isinstance(degraded_fallback_posture.get("repo_scan_degraded_reason_distribution"), Mapping)
        else {},
        "hard_grounding_failure_rate": _float(
            degraded_fallback_posture.get("hard_grounding_failure_rate")
        ),
        "hard_grounding_failure_reasons": dict(
            degraded_fallback_posture.get("hard_grounding_failure_reason_distribution", {})
        )
        if isinstance(degraded_fallback_posture.get("hard_grounding_failure_reason_distribution"), Mapping)
        else {},
        "soft_widening_rate": _float(degraded_fallback_posture.get("soft_widening_rate")),
        "soft_widening_reasons": dict(
            degraded_fallback_posture.get("soft_widening_reason_distribution", {})
        )
        if isinstance(degraded_fallback_posture.get("soft_widening_reason_distribution"), Mapping)
        else {},
        "visible_fallback_receipt_rate": _float(
            degraded_fallback_posture.get("visible_fallback_receipt_rate")
        ),
        "visible_fallback_receipt_reasons": dict(
            degraded_fallback_posture.get("visible_fallback_receipt_reason_distribution", {})
        )
        if isinstance(degraded_fallback_posture.get("visible_fallback_receipt_reason_distribution"), Mapping)
        else {},
        "governance_runtime_first_usage_rate": _float(governance_runtime_first.get("usage_rate")),
        "governance_runtime_first_fallback_rate": _float(governance_runtime_first.get("fallback_rate")),
        "governance_runtime_first_fallback_reasons": dict(
            governance_runtime_first.get("fallback_reason_distribution", {})
        )
        if isinstance(governance_runtime_first.get("fallback_reason_distribution"), Mapping)
        else {},
        "evaluation_architecture_covered_case_count": _int(architecture_evaluation.get("covered_case_count")),
        "evaluation_architecture_satisfied_case_count": _int(architecture_evaluation.get("satisfied_case_count")),
        "evaluation_architecture_coverage_rate": _float(architecture_evaluation.get("coverage_rate")),
        "evaluation_architecture_satisfaction_rate": _float(architecture_evaluation.get("satisfaction_rate")),
        "delegated_lane_rate": _float(orchestration_posture.get("delegated_lane_rate")),
        "hold_local_rate": _float(orchestration_posture.get("hold_local_rate")),
        "high_execution_confidence_rate": _float(orchestration_posture.get("high_execution_confidence_rate")),
        "runtime_backed_execution_rate": _float(orchestration_posture.get("runtime_backed_execution_rate")),
        "latest_packet_state": _string(latest_packet.get("packet_state")),
        "latest_intent_family": _string(latest_packet.get("intent_family")),
        "latest_packet_strategy": _string(latest_packet.get("packet_strategy")),
        "latest_budget_mode": _string(latest_packet.get("budget_mode")),
        "latest_retrieval_focus": _string(latest_packet.get("retrieval_focus")),
        "latest_speed_mode": _string(latest_packet.get("speed_mode")),
        "latest_packet_reliability": _string(latest_packet.get("reliability")),
        "latest_selection_bias": _string(latest_packet.get("selection_bias")),
        "latest_advised_packet_strategy": _string(latest_packet.get("advised_packet_strategy")),
        "latest_advised_budget_mode": _string(latest_packet.get("advised_budget_mode")),
        "latest_advised_retrieval_focus": _string(latest_packet.get("advised_retrieval_focus")),
        "latest_advised_speed_mode": _string(latest_packet.get("advised_speed_mode")),
        "effective_yield_score": _float(
            control_advisories.get("effective_yield_score")
            or quality_posture.get("avg_effective_yield_score")
            or packet_posture.get("avg_effective_yield_score")
        ),
        "high_yield_rate": _float(
            control_advisories.get("high_yield_rate")
            or quality_posture.get("high_yield_rate")
            or packet_posture.get("high_yield_rate")
        ),
        "reliable_high_yield_rate": _float(
            control_advisories.get("reliable_high_yield_rate")
            or quality_posture.get("reliable_high_yield_rate")
            or packet_posture.get("reliable_high_yield_rate")
        ),
        "yield_state": _string(
            control_advisories.get("yield_state")
            or quality_posture.get("yield_state")
            or packet_posture.get("yield_state")
        ),
        "packet_alignment_rate": _float(
            control_advisories.get("packet_alignment_rate")
            or packet_posture.get("advisory_alignment_rate")
        ),
        "reliable_packet_alignment_rate": _float(
            control_advisories.get("reliable_packet_alignment_rate")
            or packet_posture.get("reliable_advisory_alignment_rate")
        ),
        "packet_alignment_state": _string(
            control_advisories.get("packet_alignment_state")
            or packet_posture.get("packet_alignment_state")
        ),
        "latest_execution_profile": _string(latest_packet.get("odylith_execution_profile")),
        "latest_execution_mode": _string(latest_packet.get("odylith_execution_selection_mode")),
        "latest_execution_delegate_preference": _string(latest_packet.get("odylith_execution_delegate_preference")),
        "latest_execution_source": _string(latest_packet.get("odylith_execution_source")),
        "latest_execution_engine_present": bool(latest_packet.get("execution_engine_present")),
        "latest_execution_engine_outcome": _string(latest_packet.get("execution_engine_outcome")),
        "latest_execution_engine_requires_reanchor": bool(
            latest_packet.get("execution_engine_requires_reanchor")
        ),
        "latest_execution_engine_mode": _string(latest_packet.get("execution_engine_mode")),
        "latest_execution_engine_next_move": _string(latest_packet.get("execution_engine_next_move")),
        "latest_execution_engine_current_phase": _string(
            latest_packet.get("execution_engine_current_phase")
        ),
        "latest_execution_engine_last_successful_phase": _string(
            latest_packet.get("execution_engine_last_successful_phase")
        ),
        "latest_execution_engine_blocker": _string(latest_packet.get("execution_engine_blocker")),
        "latest_execution_engine_closure": _string(latest_packet.get("execution_engine_closure")),
        "latest_execution_engine_wait_status": _string(
            latest_packet.get("execution_engine_wait_status")
        ),
        "latest_execution_engine_wait_detail": _string(
            latest_packet.get("execution_engine_wait_detail")
        ),
        "latest_execution_engine_resume_token": _string(
            latest_packet.get("execution_engine_resume_token")
        ),
        "latest_execution_engine_validation_archetype": _string(
            latest_packet.get("execution_engine_validation_archetype")
        ),
        "latest_execution_engine_validation_minimum_pass_count": _int(
            latest_packet.get("execution_engine_validation_minimum_pass_count")
        ),
        "latest_execution_engine_validation_derived_from": _strings(
            latest_packet.get("execution_engine_validation_derived_from")
        ),
        "latest_execution_engine_contradiction_count": _int(
            latest_packet.get("execution_engine_contradiction_count")
        ),
        "latest_execution_engine_history_rule_count": _int(
            latest_packet.get("execution_engine_history_rule_count")
        ),
        "latest_execution_engine_history_rule_hits": _strings(
            latest_packet.get("execution_engine_history_rule_hits")
        ),
        "latest_execution_engine_pressure_signals": _strings(
            latest_packet.get("execution_engine_pressure_signals")
        ),
        "latest_execution_engine_nearby_denial_actions": _strings(
            latest_packet.get("execution_engine_nearby_denial_actions")
        ),
        "latest_execution_engine_authoritative_lane": _string(
            latest_packet.get("execution_engine_authoritative_lane")
        ),
        "latest_execution_engine_host_family": _string(
            latest_packet.get("execution_engine_host_family")
        ),
        "latest_execution_engine_model_family": _string(
            latest_packet.get("execution_engine_model_family")
        ),
        "latest_execution_engine_host_supports_native_spawn": bool(
            latest_packet.get("execution_engine_host_supports_native_spawn")
        ),
        "latest_execution_engine_target_lane": _string(
            latest_packet.get("execution_engine_target_lane")
        ),
        "latest_execution_engine_candidate_target_count": _int(
            latest_packet.get("execution_engine_candidate_target_count")
        ),
        "latest_execution_engine_diagnostic_anchor_count": _int(
            latest_packet.get("execution_engine_diagnostic_anchor_count")
        ),
        "latest_execution_engine_has_writable_targets": bool(
            latest_packet.get("execution_engine_has_writable_targets")
        ),
        "latest_execution_engine_requires_more_consumer_context": bool(
            latest_packet.get("execution_engine_requires_more_consumer_context")
        ),
        "latest_execution_engine_consumer_failover": _string(
            latest_packet.get("execution_engine_consumer_failover")
        ),
        "latest_execution_engine_commentary_mode": _string(
            latest_packet.get("execution_engine_commentary_mode")
        ),
        "latest_execution_engine_suppress_routing_receipts": bool(
            latest_packet.get("execution_engine_suppress_routing_receipts")
        ),
        "latest_execution_engine_surface_fast_lane": bool(
            latest_packet.get("execution_engine_surface_fast_lane")
        ),
        "latest_execution_engine_runtime_invalidated_by_step": _string(
            latest_packet.get("execution_engine_runtime_invalidated_by_step")
        ),
        "latest_turn_intent": _string(latest_packet.get("turn_intent")),
        "latest_turn_surface_count": _int(latest_packet.get("turn_surface_count")),
        "latest_turn_visible_text_count": _int(latest_packet.get("turn_visible_text_count")),
        "latest_turn_active_tab": _string(latest_packet.get("turn_active_tab")),
        "latest_turn_user_turn_id": _string(latest_packet.get("turn_user_turn_id")),
        "latest_turn_supersedes_turn_id": _string(latest_packet.get("turn_supersedes_turn_id")),
        "advisory_state": _string(control_advisories.get("state")) or _string(learning_loop.get("state")),
        "advisory_confidence_score": _int(advisory_confidence.get("score")),
        "advisory_confidence_level": _string(advisory_confidence.get("level")),
        "advisory_reasoning_mode": _string(control_advisories.get("reasoning_mode")),
        "advisory_depth": _string(control_advisories.get("depth")),
        "advisory_delegation": _string(control_advisories.get("delegation")),
        "advisory_parallelism": _string(control_advisories.get("parallelism")),
        "advisory_packet_strategy": _string(control_advisories.get("packet_strategy")),
        "advisory_budget_mode": _string(control_advisories.get("budget_mode")),
        "advisory_retrieval_focus": _string(control_advisories.get("retrieval_focus")),
        "advisory_speed_mode": _string(control_advisories.get("speed_mode")),
        "advisory_freshness_bucket": _string(advisory_freshness.get("bucket")),
        "advisory_freshness_age_hours": _float(advisory_freshness.get("newest_age_hours")),
        "advisory_evidence_strength_score": _int(advisory_evidence_strength.get("score")),
        "advisory_evidence_strength_level": _string(advisory_evidence_strength.get("level")),
        "advisory_sample_balance": _string(advisory_evidence_strength.get("sample_balance")),
        "advisory_signal_conflict": bool(control_advisories.get("signal_conflict")),
        "advisory_focus_areas": _strings(control_advisories.get("focus_areas")),
        "advisory_regressions": _strings(control_advisories.get("regressions")),
        "evaluation_learning_state": _string(evaluation_trend_posture.get("learning_state")) or _string(learning_loop.get("state")),
        "evaluation_benchmark_satisfaction_rate": _float(evaluation_packet_posture.get("benchmark_satisfaction_rate")),
        "evaluation_router_acceptance_rate": _float(evaluation_router_posture.get("acceptance_rate")),
        "evaluation_router_failure_rate": _float(evaluation_router_posture.get("failure_rate")),
        "evaluation_orchestration_token_efficiency_rate": _float(
            evaluation_orchestration_posture.get("token_efficiency_rate")
        ),
        "evaluation_orchestration_parallel_failure_rate": _float(
            evaluation_orchestration_posture.get("parallel_failure_rate")
        ),
        "evaluation_decision_quality_score": _float(evaluation_decision_quality.get("aggregate_score")),
        "evaluation_decision_quality_state": _string(evaluation_decision_quality.get("state")),
        "evaluation_decision_quality_confidence_score": _int(
            evaluation_decision_quality_confidence.get("score")
        ),
        "evaluation_decision_quality_confidence_level": _string(
            evaluation_decision_quality_confidence.get("level")
        ),
        "evaluation_decision_quality_sample_balance": _string(
            evaluation_decision_quality_confidence.get("sample_balance")
        ),
        "evaluation_closeout_observation_rate": _float(
            evaluation_decision_quality.get("closeout_observation_rate")
            or evaluation_decision_quality_confidence.get("closeout_observation_rate")
        ),
        "evaluation_delegation_regret_rate": _float(
            evaluation_decision_quality.get("delegation_regret_rate")
            or evaluation_orchestration_posture.get("delegation_regret_rate")
        ),
        "evaluation_clean_closeout_rate": _float(
            evaluation_decision_quality.get("clean_closeout_rate")
            or evaluation_orchestration_posture.get("clean_closeout_rate")
        ),
        "evaluation_followup_churn_rate": _float(
            evaluation_decision_quality.get("followup_churn_rate")
            or evaluation_orchestration_posture.get("followup_churn_rate")
        ),
        "evaluation_merge_calibration_rate": _float(
            evaluation_decision_quality.get("merge_burden_calibration_rate")
        ),
        "evaluation_validation_calibration_rate": _float(
            evaluation_decision_quality.get("validation_pressure_calibration_rate")
        ),
        "evaluation_delegation_value_calibration_rate": _float(
            evaluation_decision_quality.get("delegation_value_calibration_rate")
        ),
        "evaluation_recommendations": _strings(evaluation_posture.get("recommendations")),
        "benchmark_status": _string(benchmark_report.get("status")),
        "benchmark_scenario_count": _int(benchmark_report.get("scenario_count")),
        "benchmark_candidate_mode": _string(benchmark_report.get("candidate_mode")),
        "benchmark_baseline_mode": _string(benchmark_report.get("baseline_mode")),
        "benchmark_latency_delta_ms": _float(benchmark_report.get("latency_delta_ms")),
        "benchmark_token_delta": _float(benchmark_report.get("token_delta")),
        "benchmark_prompt_token_delta": _float(benchmark_report.get("prompt_token_delta")),
        "benchmark_total_payload_token_delta": _float(benchmark_report.get("total_payload_token_delta")),
        "benchmark_runtime_contract_token_delta": _float(benchmark_report.get("runtime_contract_token_delta")),
        "benchmark_operator_diag_token_delta": _float(benchmark_report.get("operator_diag_token_delta")),
        "benchmark_required_path_recall_delta": _float(benchmark_report.get("required_path_recall_delta")),
        "benchmark_validation_success_delta": _float(benchmark_report.get("validation_success_delta")),
    }


__all__ = ["load_runtime_surface_summary"]
