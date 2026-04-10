from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_runtime_surface_summary as runtime_summary


def test_load_runtime_surface_summary_merges_split_control_advisories(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_optimization_snapshot",
        lambda *, repo_root: {
            "sample_size": 9,
            "overall": {"level": "high", "score": 3.8},
            "quality_posture": {
                "avg_context_density_score": 2.8,
                "avg_reasoning_readiness_score": 3.1,
                "avg_evidence_diversity_score": 2.4,
                "avg_effective_yield_score": 0.81,
                "high_yield_rate": 0.78,
                "reliable_high_yield_rate": 0.74,
                "yield_state": "efficient",
                "deep_reasoning_ready_rate": 0.78,
                "route_ready_rate": 0.82,
                "native_spawn_ready_rate": 0.68,
            },
            "degraded_fallback_posture": {
                "repo_scan_degraded_fallback_rate": 0.11,
                "repo_scan_degraded_reason_distribution": {"miss_recovery_repo_scan_fallback": 1},
                "hard_grounding_failure_rate": 0.04,
                "hard_grounding_failure_reason_distribution": {"no_grounded_paths": 1},
                "soft_widening_rate": 0.22,
                "soft_widening_reason_distribution": {"broad_shared_paths": 2},
                "visible_fallback_receipt_rate": 0.03,
                "visible_fallback_receipt_reason_distribution": {"fallback_scan_present": 1},
            },
            "governance_runtime_first_posture": {
                "usage_rate": 0.92,
                "fallback_rate": 0.08,
                "fallback_reason_distribution": {"diagram_watch_gaps": 1},
            },
            "orchestration_posture": {
                "delegated_lane_rate": 0.74,
                "hold_local_rate": 0.18,
                "high_execution_confidence_rate": 0.8,
                "runtime_backed_execution_rate": 0.87,
            },
            "latest_packet": {
                "packet_state": "expanded",
                "packet_strategy": "density_first",
                "budget_mode": "spend_when_grounded",
                "retrieval_focus": "balanced",
                "speed_mode": "accelerate_grounded",
                "reliability": "reliable",
                "selection_bias": "grounded_density",
                "advised_packet_strategy": "density_first",
                "advised_budget_mode": "spend_when_grounded",
                "advised_retrieval_focus": "balanced",
                "advised_speed_mode": "accelerate_grounded",
                "intent_family": "implementation",
                "odylith_execution_profile": "frontier_high",
                "odylith_execution_selection_mode": "critical_accuracy",
                "odylith_execution_delegate_preference": "delegate",
                "odylith_execution_source": "odylith_runtime_packet",
                "execution_governance_present": True,
                "execution_governance_outcome": "admit",
                "execution_governance_requires_reanchor": False,
                "execution_governance_mode": "verify",
                "execution_governance_next_move": "verify.selected_matrix",
                "execution_governance_current_phase": "status_synthesis",
                "execution_governance_last_successful_phase": "submit",
                "execution_governance_blocker": "waiting for rollout evidence",
                "execution_governance_closure": "incomplete",
                "execution_governance_wait_status": "building",
                "execution_governance_wait_detail": "deploying cell-01",
                "execution_governance_resume_token": "resume:B-072",
                "execution_governance_validation_archetype": "deploy",
                "execution_governance_validation_minimum_pass_count": 6,
                "execution_governance_contradiction_count": 0,
                "execution_governance_history_rule_count": 2,
                "execution_governance_authoritative_lane": "context_engine.governance_slice.authoritative",
                "execution_governance_host_family": "codex",
                "execution_governance_model_family": "codex",
                "execution_governance_target_lane": "consumer",
                "execution_governance_candidate_target_count": 2,
                "execution_governance_diagnostic_anchor_count": 2,
                "execution_governance_has_writable_targets": False,
                "execution_governance_requires_more_consumer_context": True,
                "execution_governance_consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
                "execution_governance_commentary_mode": "task_first_minimal",
                "execution_governance_suppress_routing_receipts": True,
                "execution_governance_surface_fast_lane": True,
                "turn_intent": 'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
                "turn_surface_count": 1,
                "turn_visible_text_count": 1,
                "turn_active_tab": "releases",
                "turn_user_turn_id": "turn-2",
                "turn_supersedes_turn_id": "turn-1",
            },
            "evaluation_posture": {
                "packet_events": {"benchmark_satisfaction_rate": 0.78},
                "router_outcomes": {"acceptance_rate": 0.81, "failure_rate": 0.09},
                "orchestration_feedback": {
                    "token_efficiency_rate": 0.73,
                    "parallel_failure_rate": 0.02,
                    "delegation_regret_rate": 0.12,
                    "clean_closeout_rate": 0.74,
                    "followup_churn_rate": 0.09,
                },
                "decision_quality": {
                    "aggregate_score": 0.78,
                    "state": "trusted",
                    "confidence": {
                        "score": 4,
                        "level": "high",
                        "sample_balance": "balanced",
                        "closeout_observation_rate": 0.78,
                    },
                    "closeout_observation_rate": 0.78,
                    "delegation_regret_rate": 0.12,
                    "clean_closeout_rate": 0.74,
                    "followup_churn_rate": 0.09,
                    "merge_burden_calibration_rate": 0.68,
                    "validation_pressure_calibration_rate": 0.71,
                    "delegation_value_calibration_rate": 0.77,
                },
                "trend_posture": {"learning_state": "improving"},
                "control_advisories": {
                    "state": "improving",
                    "confidence": {"score": 4, "level": "high"},
                    "reasoning_mode": "earn_depth",
                    "packet_alignment_rate": 0.89,
                    "reliable_packet_alignment_rate": 0.92,
                    "packet_alignment_state": "aligned",
                    "effective_yield_score": 0.81,
                    "high_yield_rate": 0.78,
                    "reliable_high_yield_rate": 0.74,
                    "yield_state": "efficient",
                    "freshness": {"bucket": "fresh", "newest_age_hours": 1.5},
                    "evidence_strength": {"score": 3, "level": "high", "sample_balance": "balanced"},
                    "signal_conflict": False,
                    "focus_areas": ["coverage", "budget"],
                    "regressions": ["none"],
                },
            },
            "learning_loop": {
                "state": "improving",
                "control_advisories": {
                    "depth": "promote_when_grounded",
                    "delegation": "runtime_backed_delegate",
                    "parallelism": "allow_when_disjoint",
                    "packet_strategy": "density_first",
                    "budget_mode": "spend_when_grounded",
                    "retrieval_focus": "balanced",
                    "speed_mode": "accelerate_grounded",
                },
            },
        },
    )
    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_evaluation_snapshot",
        lambda *, repo_root: {
            "status": "active",
            "architecture": {
                "covered_case_count": 3,
                "satisfied_case_count": 3,
                "coverage_rate": 1.0,
                "satisfaction_rate": 1.0,
            },
        },
    )
    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_memory_snapshot",
        lambda *, repo_root, optimization_snapshot, evaluation_snapshot: {
            "status": "active",
            "odylith_switch": {"enabled": True},
            "memory_areas": {
                "headline": "Repo truth and retrieval memory are strong.",
                "gap_count": 3,
                "counts": {"strong": 2, "planned": 3},
            },
            "judgment_memory": {
                "headline": "Decision memory and onboarding memory are durable.",
                "gap_count": 2,
                "counts": {"strong": 5, "partial": 2, "cold": 1},
            },
            "backend_transition": {
                "status": "standardized",
                "actual_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "target_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
            },
            "remote_retrieval": {
                "enabled": True,
                "provider": "vespa",
                "mode": "mirror",
            },
        },
    )

    summary = runtime_summary.load_runtime_surface_summary(repo_root=tmp_path)

    assert summary["status"] == "active"
    assert summary["enabled"] is True
    assert summary["memory_backend_label"] == "Lance / Tantivy"
    assert summary["remote_label"] == "vespa / mirror"
    assert summary["memory_standardization_state"] == "standardized"
    assert summary["memory_backend_actual"] == "lance_local_columnar / tantivy_sparse_recall"
    assert summary["memory_backend_target"] == "lance_local_columnar / tantivy_sparse_recall"
    assert summary["memory_area_headline"] == "Repo truth and retrieval memory are strong."
    assert summary["memory_area_gap_count"] == 3
    assert summary["memory_area_counts"] == {"strong": 2, "planned": 3}
    assert summary["judgment_memory_headline"] == "Decision memory and onboarding memory are durable."
    assert summary["judgment_memory_gap_count"] == 2
    assert summary["judgment_memory_counts"] == {"strong": 5, "partial": 2, "cold": 1}
    assert summary["optimization_level"] == "high"
    assert summary["native_spawn_ready_rate"] == 0.68
    assert summary["repo_scan_degraded_fallback_rate"] == 0.11
    assert summary["repo_scan_degraded_reasons"] == {"miss_recovery_repo_scan_fallback": 1}
    assert summary["hard_grounding_failure_rate"] == 0.04
    assert summary["hard_grounding_failure_reasons"] == {"no_grounded_paths": 1}
    assert summary["soft_widening_rate"] == 0.22
    assert summary["soft_widening_reasons"] == {"broad_shared_paths": 2}
    assert summary["visible_fallback_receipt_rate"] == 0.03
    assert summary["visible_fallback_receipt_reasons"] == {"fallback_scan_present": 1}
    assert summary["governance_runtime_first_usage_rate"] == 0.92
    assert summary["governance_runtime_first_fallback_rate"] == 0.08
    assert summary["governance_runtime_first_fallback_reasons"] == {"diagram_watch_gaps": 1}
    assert summary["evaluation_architecture_covered_case_count"] == 3
    assert summary["evaluation_architecture_satisfied_case_count"] == 3
    assert summary["evaluation_architecture_coverage_rate"] == 1.0
    assert summary["evaluation_architecture_satisfaction_rate"] == 1.0
    assert summary["latest_execution_profile"] == "frontier_high"
    assert summary["latest_packet_strategy"] == "density_first"
    assert summary["latest_budget_mode"] == "spend_when_grounded"
    assert summary["latest_speed_mode"] == "accelerate_grounded"
    assert summary["latest_packet_reliability"] == "reliable"
    assert summary["latest_execution_governance_present"] is True
    assert summary["latest_execution_governance_outcome"] == "admit"
    assert summary["latest_execution_governance_mode"] == "verify"
    assert summary["latest_execution_governance_next_move"] == "verify.selected_matrix"
    assert summary["latest_execution_governance_closure"] == "incomplete"
    assert summary["latest_execution_governance_wait_status"] == "building"
    assert summary["latest_execution_governance_resume_token"] == "resume:B-072"
    assert summary["latest_execution_governance_validation_archetype"] == "deploy"
    assert summary["latest_execution_governance_history_rule_count"] == 2
    assert summary["latest_execution_governance_host_family"] == "codex"
    assert summary["latest_execution_governance_model_family"] == "codex"
    assert summary["latest_execution_governance_target_lane"] == "consumer"
    assert summary["latest_execution_governance_candidate_target_count"] == 2
    assert summary["latest_execution_governance_diagnostic_anchor_count"] == 2
    assert summary["latest_execution_governance_has_writable_targets"] is False
    assert summary["latest_execution_governance_requires_more_consumer_context"] is True
    assert (
        summary["latest_execution_governance_consumer_failover"]
        == "maintainer_ready_feedback_plus_bounded_narrowing"
    )
    assert summary["latest_execution_governance_commentary_mode"] == "task_first_minimal"
    assert summary["latest_execution_governance_suppress_routing_receipts"] is True
    assert summary["latest_execution_governance_surface_fast_lane"] is True
    assert (
        summary["latest_turn_intent"]
        == 'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"'
    )
    assert summary["latest_turn_surface_count"] == 1
    assert summary["latest_turn_visible_text_count"] == 1
    assert summary["latest_turn_active_tab"] == "releases"
    assert summary["latest_turn_user_turn_id"] == "turn-2"
    assert summary["latest_turn_supersedes_turn_id"] == "turn-1"
    assert summary["latest_advised_packet_strategy"] == "density_first"
    assert summary["latest_advised_budget_mode"] == "spend_when_grounded"
    assert summary["effective_yield_score"] == 0.81
    assert summary["high_yield_rate"] == 0.78
    assert summary["reliable_high_yield_rate"] == 0.74
    assert summary["yield_state"] == "efficient"
    assert summary["packet_alignment_rate"] == 0.89
    assert summary["reliable_packet_alignment_rate"] == 0.92
    assert summary["packet_alignment_state"] == "aligned"
    assert summary["advisory_state"] == "improving"
    assert summary["advisory_reasoning_mode"] == "earn_depth"
    assert summary["advisory_depth"] == "promote_when_grounded"
    assert summary["advisory_delegation"] == "runtime_backed_delegate"
    assert summary["advisory_parallelism"] == "allow_when_disjoint"
    assert summary["advisory_budget_mode"] == "spend_when_grounded"
    assert summary["advisory_freshness_bucket"] == "fresh"
    assert summary["advisory_sample_balance"] == "balanced"
    assert summary["advisory_signal_conflict"] is False
    assert summary["advisory_focus_areas"] == ["coverage", "budget"]
    assert summary["evaluation_learning_state"] == "improving"
    assert summary["evaluation_router_acceptance_rate"] == 0.81
    assert summary["evaluation_decision_quality_score"] == 0.78
    assert summary["evaluation_decision_quality_state"] == "trusted"
    assert summary["evaluation_decision_quality_confidence_score"] == 4
    assert summary["evaluation_decision_quality_confidence_level"] == "high"
    assert summary["evaluation_decision_quality_sample_balance"] == "balanced"
    assert summary["evaluation_closeout_observation_rate"] == 0.78
    assert summary["evaluation_delegation_regret_rate"] == 0.12
    assert summary["evaluation_clean_closeout_rate"] == 0.74
    assert summary["evaluation_followup_churn_rate"] == 0.09
    assert summary["evaluation_merge_calibration_rate"] == 0.68
    assert summary["evaluation_validation_calibration_rate"] == 0.71
    assert summary["evaluation_delegation_value_calibration_rate"] == 0.77


def test_load_runtime_surface_summary_uses_disabled_remote_and_repo_scan_labels(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_optimization_snapshot",
        lambda *, repo_root: {
            "overall": {"level": "medium", "score": 2.2},
            "quality_posture": {},
            "orchestration_posture": {},
            "latest_packet": {},
            "evaluation_posture": {},
            "learning_loop": {},
        },
    )
    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_evaluation_snapshot",
        lambda *, repo_root: {"status": "idle"},
    )
    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_memory_snapshot",
        lambda *, repo_root, optimization_snapshot, evaluation_snapshot: {
            "status": "degraded",
            "odylith_switch": {"enabled": True},
            "backend_transition": {
                "status": "degraded",
                "actual_local_backend": {
                    "storage": "compiler_projection_snapshot",
                    "sparse_recall": "repo_scan_fallback",
                },
                "target_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
            },
            "remote_retrieval": {"enabled": False},
        },
    )

    summary = runtime_summary.load_runtime_surface_summary(repo_root=tmp_path)

    assert summary["memory_status"] == "degraded"
    assert summary["memory_backend_label"] == "Compiler Snapshot / Repo Scan"
    assert summary["memory_standardization_state"] == "degraded"
    assert summary["memory_backend_actual"] == "compiler_projection_snapshot / repo_scan_fallback"
    assert summary["memory_backend_target"] == "lance_local_columnar / tantivy_sparse_recall"
    assert summary["remote_label"] == "Disabled"
    assert summary["memory_area_headline"] == ""
    assert summary["memory_area_gap_count"] == 0
    assert summary["memory_area_counts"] == {}
    assert summary["judgment_memory_headline"] == ""
    assert summary["judgment_memory_gap_count"] == 0
    assert summary["judgment_memory_counts"] == {}
    assert summary["latest_packet_strategy"] == ""
    assert summary["effective_yield_score"] == 0.0
    assert summary["yield_state"] == ""
    assert summary["packet_alignment_rate"] == 0.0
    assert summary["packet_alignment_state"] == ""
    assert summary["advisory_state"] == ""
    assert summary["evaluation_decision_quality_score"] == 0.0
    assert summary["evaluation_decision_quality_state"] == ""
    assert summary["evaluation_decision_quality_confidence_score"] == 0
    assert summary["evaluation_delegation_regret_rate"] == 0.0
    assert summary["evaluation_merge_calibration_rate"] == 0.0
    assert summary["evaluation_recommendations"] == []


def test_load_runtime_surface_summary_returns_unavailable_payload_on_store_failure(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    def _raise(*, repo_root: Path) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        runtime_summary.odylith_context_engine_store,
        "load_runtime_optimization_snapshot",
        _raise,
    )

    summary = runtime_summary.load_runtime_surface_summary(repo_root=tmp_path)

    assert summary["status"] == "unavailable"
    assert summary["enabled"] is False
    assert summary["memory_backend_label"] == "Unavailable"
    assert summary["memory_area_headline"] == ""
    assert summary["memory_area_gap_count"] == 0
    assert summary["memory_area_counts"] == {}
    assert summary["judgment_memory_headline"] == ""
    assert summary["judgment_memory_gap_count"] == 0
    assert summary["judgment_memory_counts"] == {}
    assert summary["native_spawn_ready_rate"] == 0.0
    assert summary["repo_scan_degraded_fallback_rate"] == 0.0
    assert summary["hard_grounding_failure_rate"] == 0.0
    assert summary["soft_widening_rate"] == 0.0
    assert summary["visible_fallback_receipt_rate"] == 0.0
    assert summary["governance_runtime_first_usage_rate"] == 0.0
    assert summary["evaluation_architecture_covered_case_count"] == 0
    assert summary["remote_label"] == "Unavailable"
    assert summary["effective_yield_score"] == 0.0
    assert summary["yield_state"] == ""
    assert summary["advisory_state"] == "unavailable"
    assert summary["evaluation_learning_state"] == ""
    assert summary["evaluation_decision_quality_score"] == 0.0
    assert summary["evaluation_decision_quality_state"] == ""
    assert summary["evaluation_decision_quality_confidence_score"] == 0
    assert summary["evaluation_followup_churn_rate"] == 0.0
