from __future__ import annotations

import datetime as dt
from pathlib import Path

from odylith.runtime.evaluation import odylith_evaluation_ledger as ledger
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator
from odylith.runtime.orchestration import subagent_router as router


def test_evaluation_ledger_summarizes_good_recent_events(tmp_path: Path) -> None:
    ledger.append_event(
        repo_root=tmp_path,
        event_type="packet",
        event_id="packet-1",
        payload=ledger.packet_event_payload(
            packet_summary={
                "session_id": "session-1",
                "packet_state": "expanded",
                "within_budget": True,
                "route_ready": True,
                "native_spawn_ready": True,
                "narrowing_required": False,
                "utility_score": 86,
                "context_density_score": 3,
                "reasoning_readiness_score": 3,
                "deep_reasoning_ready": True,
                "evidence_diversity_score": 3,
                "density_per_1k_tokens": 21.0,
                "estimated_tokens": 2100,
                "odylith_execution_profile": "write_high",
                "odylith_execution_model": "gpt-5.3-codex",
                "odylith_execution_reasoning_effort": "high",
                "odylith_execution_delegate_preference": "delegate",
                "odylith_execution_source": "odylith_runtime_packet",
            },
            benchmark_summary={
                "matched_case_count": 1,
                "satisfied_case_count": 1,
                "matched_case_ids": ["case-1"],
                "drift_case_ids": [],
            },
        ),
    )
    decision = router.RoutingDecision(
        delegate=True,
        profile=router.RouterProfile.CODEX_HIGH.value,
        model="gpt-5.3-codex",
        reasoning_effort="high",
        agent_role="worker",
        close_after_result=True,
        idle_timeout_minutes=10,
        reuse_window="explicit_same_scope_followup_queued_only",
        waiting_policy="send_input_or_close",
        why="bounded delegated slice",
        escalation_profile="",
        hard_gate_hits=[],
        decision_id="router-decision-1",
        task_family="bounded_bugfix",
        routing_confidence=3,
    )
    ledger.append_event(
        repo_root=tmp_path,
        event_type="router_outcome",
        event_id="router-outcome-1",
        payload=ledger.router_outcome_event_payload(
            decision=decision.as_dict(),
            outcome=router.RouteOutcome(accepted=True).as_dict(),
        ),
    )
    orchestration_decision = orchestrator.OrchestrationDecision(
        mode=orchestrator.OrchestrationMode.PARALLEL_BATCH.value,
        decision_id="orchestrator-decision-1",
        delegate=True,
        parallel_safety=orchestrator.ParallelSafetyClass.DISJOINT_WRITE_SAFE.value,
        task_family="bounded_feature",
        confidence=3,
        rationale="disjoint write slice",
        refusal_stage="delegated",
        manual_review_recommended=False,
        merge_owner="main_thread",
        request={"prompt": "Implement the change."},
    )
    ledger.append_event(
        repo_root=tmp_path,
        event_type="orchestration_feedback",
        event_id="orchestration-feedback-1",
        payload=ledger.orchestration_feedback_event_payload(
            decision=orchestration_decision.as_dict(),
            feedback=orchestrator.ExecutionFeedback(accepted=True, token_efficient=True).as_dict(),
        ),
    )

    summary = ledger.summarize(repo_root=tmp_path)

    assert summary["packet_events"]["within_budget_rate"] == 1.0
    assert summary["packet_events"]["benchmark_satisfaction_rate"] == 1.0
    assert summary["router_outcomes"]["acceptance_rate"] == 1.0
    assert summary["orchestration_feedback"]["token_efficiency_rate"] == 1.0
    assert summary["control_posture"]["depth"] == "promote_when_grounded"
    assert summary["control_posture"]["delegation"] == "runtime_backed_delegate"
    assert summary["control_posture"]["yield_state"] == "efficient"
    assert summary["packet_events"]["avg_effective_yield_score"] >= 0.72
    assert summary["packet_events"]["high_yield_rate"] == 1.0
    assert summary["control_advisories"]["depth"] == "promote_when_grounded"
    assert summary["control_advisories"]["reasoning_mode"] == "earn_depth"
    assert summary["control_advisories"]["budget_mode"] == "spend_when_grounded"
    assert summary["control_advisories"]["yield_state"] == "efficient"
    assert summary["freshness"]["overall"]["bucket"] == "fresh"
    assert summary["control_advisories"]["freshness"]["bucket"] == "fresh"
    assert summary["control_advisories"]["evidence_strength"]["level"] in {"low", "medium"}
    assert summary["control_advisories"]["signal_conflict"] is False


def test_evaluation_ledger_degrades_confidence_for_stale_and_conflicted_history(tmp_path: Path) -> None:
    stale_time = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=8)).replace(microsecond=0)
    ledger.append_event(
        repo_root=tmp_path,
        event_type="packet",
        event_id="packet-stale-1",
        recorded_at=stale_time.isoformat().replace("+00:00", "Z"),
        payload=ledger.packet_event_payload(
            packet_summary={
                "session_id": "session-stale-1",
                "packet_state": "expanded",
                "within_budget": True,
                "route_ready": True,
                "native_spawn_ready": True,
                "narrowing_required": False,
                "utility_score": 80,
                "context_density_score": 3,
                "reasoning_readiness_score": 3,
                "deep_reasoning_ready": True,
                "evidence_diversity_score": 3,
                "odylith_execution_profile": "write_high",
            },
            benchmark_summary={
                "matched_case_count": 1,
                "satisfied_case_count": 1,
                "matched_case_ids": ["case-1"],
                "drift_case_ids": [],
            },
        ),
    )
    ledger.append_event(
        repo_root=tmp_path,
        event_type="router_outcome",
        event_id="router-stale-1",
        recorded_at=stale_time.isoformat().replace("+00:00", "Z"),
        payload={
            "accepted": False,
            "blocked": True,
            "odylith_execution_delegate_preference": "hold_local",
        },
    )

    summary = ledger.summarize(repo_root=tmp_path)

    assert summary["freshness"]["overall"]["bucket"] == "stale"
    assert summary["evidence_strength"]["sample_balance"] in {"thin", "partial"}
    assert summary["control_advisories"]["state"] in {"bootstrap", "stale"}
    assert summary["control_advisories"]["confidence"]["score"] <= 1
    assert summary["control_advisories"]["freshness"]["bucket"] == "stale"
    assert "stale_learning_history" in summary["regressions"]
    assert any("stale" in line.lower() for line in summary["recommendations"])


def test_optimization_snapshot_exposes_learning_loop(tmp_path: Path) -> None:
    ledger.append_event(
        repo_root=tmp_path,
        event_type="packet",
        event_id="packet-1",
        payload=ledger.packet_event_payload(
            packet_summary={
                "session_id": "session-1",
                "packet_state": "expanded",
                "within_budget": True,
                "route_ready": True,
                "native_spawn_ready": True,
                "narrowing_required": False,
                "utility_score": 74,
                "context_density_score": 3,
                "reasoning_readiness_score": 3,
                "deep_reasoning_ready": True,
                "evidence_diversity_score": 2,
                "density_per_1k_tokens": 2.1,
                "estimated_tokens": 1800,
                "odylith_execution_profile": "write_high",
            },
            benchmark_summary={
                "matched_case_count": 1,
                "satisfied_case_count": 1,
                "matched_case_ids": ["case-1"],
                "drift_case_ids": [],
            },
        ),
    )
    ledger.append_event(
        repo_root=tmp_path,
        event_type="router_outcome",
        event_id="router-outcome-1",
        payload={
            "accepted": True,
            "profile": router.RouterProfile.CODEX_HIGH.value,
            "task_family": "bounded_bugfix",
        },
    )
    snapshot = store.load_runtime_optimization_snapshot(repo_root=tmp_path)

    assert snapshot["evaluation_posture"]["packet_events"]["benchmark_satisfaction_rate"] == 1.0
    assert snapshot["evaluation_posture"]["packet_events"]["avg_effective_yield_score"] > 0.0
    assert snapshot["evaluation_posture"]["router_outcomes"]["acceptance_rate"] == 1.0
    assert snapshot["learning_loop"]["control_posture"]["depth"] == "promote_when_grounded"
    assert snapshot["learning_loop"]["control_posture"]["budget_mode"] == "spend_when_grounded"
    assert snapshot["learning_loop"]["control_posture"]["yield_state"] == "efficient"
    assert "event_count" in snapshot["learning_loop"]
    assert snapshot["control_advisories"]["depth"] == "promote_when_grounded"
    assert snapshot["evaluation_posture"]["control_advisories"]["reasoning_mode"] == "earn_depth"
    assert snapshot["learning_loop"]["control_advisories"]["budget_mode"] == "spend_when_grounded"
    assert snapshot["quality_posture"]["avg_effective_yield_score"] > 0.0
    assert snapshot["quality_posture"]["yield_state"] == "efficient"
    assert snapshot["evaluation_posture"]["freshness"]["overall"]["bucket"] == "fresh"
    assert snapshot["evaluation_posture"]["evidence_strength"]["level"] in {"low", "medium"}
    assert snapshot["learning_loop"]["freshness"]["overall"]["bucket"] == "fresh"


def test_learning_summary_tracks_packetizer_alignment_drift(tmp_path: Path) -> None:
    control_advisories = {
        "state": "stable",
        "confidence": {"score": 4, "level": "high"},
        "reasoning_mode": "earn_depth",
        "packet_strategy": "density_first",
        "budget_mode": "spend_when_grounded",
        "retrieval_focus": "balanced",
        "speed_mode": "accelerate_grounded",
        "freshness": {"bucket": "fresh", "newest_age_hours": 1.0},
        "evidence_strength": {"score": 4, "level": "high", "sample_balance": "balanced"},
        "signal_conflict": False,
    }
    for index in range(3):
        ledger.append_event(
            repo_root=tmp_path,
            event_type="packet",
            event_id=f"packet-{index}",
            payload=ledger.packet_event_payload(
                packet_summary={
                    "session_id": f"session-{index}",
                    "packet_state": "expanded",
                    "within_budget": index == 0,
                    "route_ready": True,
                    "native_spawn_ready": True,
                    "narrowing_required": False,
                    "utility_score": 70,
                    "context_density_score": 3,
                    "reasoning_readiness_score": 3,
                    "deep_reasoning_ready": True,
                    "evidence_diversity_score": 2,
                    "estimated_tokens": 1600,
                    "adaptive_packet_strategy": "precision_first",
                    "adaptive_budget_mode": "tight",
                    "adaptive_retrieval_focus": "precision_repair",
                    "adaptive_speed_mode": "conserve",
                    "adaptive_reliability": "guarded",
                },
                benchmark_summary={"matched_case_count": 1, "satisfied_case_count": 0},
                control_advisories=control_advisories,
            ),
        )

    summary = ledger.summarize(repo_root=tmp_path)

    assert summary["packet_events"]["alignment_state"] == "drifting"
    assert summary["packet_events"]["yield_state"] in {"mixed", "wasteful"}
    assert summary["packet_events"]["advisory_alignment_coverage"] == 3
    assert summary["packet_events"]["reliable_advisory_alignment_count"] == 3
    assert summary["control_posture"]["packet_alignment_state"] == "drifting"
    assert summary["control_advisories"]["packet_alignment_state"] == "drifting"
    assert "packetizer_alignment_drift" in summary["regressions"]
    assert any("Packetizer alignment is drifting" in line for line in summary["recommendations"])


def test_evaluation_ledger_tracks_decision_quality_and_calibration(tmp_path: Path) -> None:
    decision = orchestrator.OrchestrationDecision(
        mode=orchestrator.OrchestrationMode.PARALLEL_BATCH.value,
        decision_id="orchestrator-decision-calibration",
        delegate=True,
        parallel_safety=orchestrator.ParallelSafetyClass.DISJOINT_WRITE_SAFE.value,
        task_family="bounded_feature",
        confidence=3,
        rationale="bounded write fan-out",
        refusal_stage="delegated",
        manual_review_recommended=False,
        merge_owner="main_thread",
        subtasks=[
            orchestrator.SubtaskSlice(
                id="leaf-1",
                prompt="Implement the primary slice.",
                execution_group_kind="primary",
                scope_role="implementation",
                route_odylith_execution_profile={
                    "signals": {
                        "grounding": {"score": 4, "level": "high"},
                        "density": {"score": 3, "level": "high"},
                        "actionability": {"score": 4, "level": "high"},
                        "validation_pressure": {"score": 1, "level": "low"},
                        "merge_burden": {"score": 1, "level": "low"},
                        "expected_delegation_value": {"score": 4, "level": "high"},
                    },
                    "constraints": {"route_ready": True},
                },
            )
        ],
        request={"prompt": "Implement the bounded change."},
    )
    decision_ledger = {
        "subtasks": [
            {
                "subtask_id": "leaf-1",
                "inspection_state": {
                    "status": "waiting_on_instruction",
                    "result_handoff": {"status": "reported"},
                    "followup": {"status": "queued"},
                    "closeout": {"status": "open"},
                },
            }
        ]
    }
    ledger.append_event(
        repo_root=tmp_path,
        event_type="orchestration_feedback",
        event_id="orchestration-feedback-calibration",
        payload=ledger.orchestration_feedback_event_payload(
            decision=decision.as_dict(),
            feedback=orchestrator.ExecutionFeedback(
                accepted=True,
                rescope_required=True,
                token_efficient=False,
            ).as_dict(),
            decision_ledger=decision_ledger,
        ),
    )

    summary = ledger.summarize(repo_root=tmp_path)

    assert summary["decision_quality"]["aggregate_score"] < 0.55
    assert summary["decision_quality"]["state"] == "bootstrap"
    assert summary["decision_quality"]["confidence"]["score"] <= 1
    assert summary["decision_quality"]["closeout_observation_rate"] == 1.0
    assert summary["decision_quality"]["delegation_regret_rate"] == 1.0
    assert summary["decision_quality"]["followup_churn_rate"] == 1.0
    assert summary["decision_quality"]["clean_closeout_rate"] == 0.0
    assert summary["decision_quality"]["merge_burden_underestimate_rate"] == 1.0
    assert summary["decision_quality"]["validation_pressure_underestimate_rate"] == 1.0
    assert summary["decision_quality"]["delegation_overreach_rate"] == 1.0
    assert summary["control_posture"]["delegation"] == "balanced"
    assert summary["control_posture"]["parallelism"] == "guarded"
    assert summary["decision_quality"]["confidence"]["state"] == "bootstrap"
    assert any("Decision-quality evidence is still thin" in line for line in summary["recommendations"])


def test_evaluation_ledger_only_hardens_control_when_decision_quality_is_reliable(tmp_path: Path) -> None:
    for index in range(5):
        decision = orchestrator.OrchestrationDecision(
            mode=orchestrator.OrchestrationMode.PARALLEL_BATCH.value,
            decision_id=f"orchestrator-decision-calibration-{index}",
            delegate=True,
            parallel_safety=orchestrator.ParallelSafetyClass.DISJOINT_WRITE_SAFE.value,
            task_family="bounded_feature",
            confidence=3,
            rationale="bounded write fan-out",
            refusal_stage="delegated",
            manual_review_recommended=False,
            merge_owner="main_thread",
            subtasks=[
                orchestrator.SubtaskSlice(
                    id=f"leaf-{index}",
                    prompt="Implement the primary slice.",
                    execution_group_kind="primary",
                    scope_role="implementation",
                    route_odylith_execution_profile={
                        "signals": {
                            "grounding": {"score": 4, "level": "high"},
                            "density": {"score": 3, "level": "high"},
                            "actionability": {"score": 4, "level": "high"},
                            "validation_pressure": {"score": 1, "level": "low"},
                            "merge_burden": {"score": 1, "level": "low"},
                            "expected_delegation_value": {"score": 4, "level": "high"},
                        },
                        "constraints": {"route_ready": True},
                    },
                )
            ],
            request={"prompt": "Implement the bounded change."},
        )
        decision_ledger = {
            "subtasks": [
                {
                    "subtask_id": f"leaf-{index}",
                    "inspection_state": {
                        "status": "waiting_on_instruction",
                        "result_handoff": {"status": "reported"},
                        "followup": {"status": "queued"},
                        "closeout": {"status": "open"},
                    },
                }
            ]
        }
        ledger.append_event(
            repo_root=tmp_path,
            event_type="orchestration_feedback",
            event_id=f"orchestration-feedback-calibration-{index}",
            payload=ledger.orchestration_feedback_event_payload(
                decision=decision.as_dict(),
                feedback=orchestrator.ExecutionFeedback(
                    accepted=True,
                    rescope_required=True,
                    token_efficient=False,
                ).as_dict(),
                decision_ledger=decision_ledger,
            ),
        )

    summary = ledger.summarize(repo_root=tmp_path)

    assert summary["decision_quality"]["state"] == "fragile"
    assert summary["decision_quality"]["confidence"]["score"] >= 3
    assert summary["control_posture"]["delegation"] == "hold_local_bias"
    assert "delegation_regret_high" in summary["regressions"]
    assert "merge_burden_underestimated" in summary["regressions"]
    assert "validation_pressure_underestimated" in summary["regressions"]
    assert "decision_quality_fragile" in summary["regressions"]
    assert any("underpredicting merge burden" in line for line in summary["recommendations"])


def test_router_uses_evaluation_control_posture_to_guard_depth(tmp_path: Path) -> None:
    base_context = {
        "routing_handoff": {
            "grounding": {"grounded": True, "score": 4},
            "routing_confidence": "high",
            "route_ready": True,
            "narrowing_required": False,
            "packet_quality": {
                "evidence_quality": {"score": 4, "level": "high"},
                "actionability": {"score": 4, "level": "high"},
                "validation_pressure": {"score": 3, "level": "high"},
                "context_density": {"score": 3, "level": "high"},
                "reasoning_readiness": {
                    "score": 3,
                    "level": "high",
                    "mode": "analysis_synthesis",
                    "deep_reasoning_ready": True,
                },
                "evidence_diversity": {"score": 3, "level": "high"},
                "utility_profile": {
                    "score": 80,
                    "level": "high",
                    "token_efficiency": {"score": 3, "level": "high"},
                },
                "native_spawn_ready": True,
                "reasoning_bias": "accuracy_first",
                "parallelism_hint": "serial_preferred",
            },
        }
    }
    request_promote = router.route_request_from_mapping(
        {
            "prompt": "Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Update the implementation", "Keep validation green"],
            "allowed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_router.py"],
            "task_kind": "implementation",
            "needs_write": True,
            "accuracy_preference": "balanced",
            "context_signals": {
                **base_context,
                "optimization_snapshot": {
                    "evaluation_posture": {
                        "packet_events": {"benchmark_satisfaction_rate": 0.8},
                        "router_outcomes": {"acceptance_rate": 0.8, "failure_rate": 0.1, "escalation_rate": 0.0},
                        "orchestration_feedback": {"token_efficiency_rate": 0.7, "parallel_failure_rate": 0.0},
                        "trend_posture": {"learning_state": "improving"},
                        "control_posture": {
                            "depth": "promote_when_grounded",
                            "delegation": "runtime_backed_delegate",
                            "parallelism": "balanced",
                            "packet_strategy": "density_first",
                        },
                    },
                    "learning_loop": {"state": "improving"},
                },
            },
        }
    )
    request_guarded = router.route_request_from_mapping(
        {
            "prompt": "Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Update the implementation", "Keep validation green"],
            "allowed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_router.py"],
            "task_kind": "implementation",
            "needs_write": True,
            "accuracy_preference": "balanced",
            "context_signals": {
                **base_context,
                "optimization_snapshot": {
                    "evaluation_posture": {
                        "packet_events": {"benchmark_satisfaction_rate": 0.2},
                        "router_outcomes": {"acceptance_rate": 0.2, "failure_rate": 0.5, "escalation_rate": 0.3},
                        "orchestration_feedback": {"token_efficiency_rate": 0.2, "parallel_failure_rate": 0.3},
                        "trend_posture": {"learning_state": "regressing"},
                        "control_posture": {
                            "depth": "narrow_first",
                            "delegation": "hold_local_bias",
                            "parallelism": "guarded",
                            "packet_strategy": "precision_first",
                        },
                    },
                    "learning_loop": {"state": "regressing"},
                },
            },
        }
    )

    promote = router.route_request(request_promote, repo_root=tmp_path)
    guarded = router.route_request(request_guarded, repo_root=tmp_path)

    assert router._PROFILE_PRIORITY[promote.profile] >= router._PROFILE_PRIORITY[guarded.profile]  # noqa: SLF001
    assert any("Recent execution evidence is improving" in line for line in promote.assessment["feature_reasons"]["context_signals"])
    assert any("prefers narrow-first control" in line for line in guarded.assessment["feature_reasons"]["context_signals"])


def test_orchestrator_uses_evaluation_control_posture_to_guard_parallelism(tmp_path: Path) -> None:
    request = orchestrator.orchestration_request_from_mapping(
        {
            "prompt": "Implement the bounded feature changes in scripts/example.py and services/example.py.",
            "acceptance_criteria": ["Update scripts/example.py", "Update services/example.py", "Keep behavior compatible"],
            "candidate_paths": ["scripts/example.py", "services/example.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_example.py"],
            "task_kind": "feature_implementation",
            "phase": "implementation",
            "needs_write": True,
            "evidence_cone_grounded": True,
            "context_signals": {
                "optimization_snapshot": {
                    "evaluation_posture": {
                        "router_outcomes": {"acceptance_rate": 0.2, "failure_rate": 0.5},
                        "orchestration_feedback": {"token_efficiency_rate": 0.2, "parallel_failure_rate": 0.4},
                        "control_posture": {
                            "depth": "narrow_first",
                            "delegation": "hold_local_bias",
                            "parallelism": "guarded",
                            "packet_strategy": "precision_first",
                        },
                    }
                },
                "routing_handoff": {
                    "route_ready": True,
                    "narrowing_required": False,
                    "packet_quality": {
                        "evidence_quality": {"score": 4, "level": "high"},
                        "actionability": {"score": 4, "level": "high"},
                        "context_density": {"score": 3, "level": "high"},
                        "reasoning_readiness": {"score": 3, "level": "high", "mode": "bounded_write", "deep_reasoning_ready": True},
                        "native_spawn_ready": True,
                    },
                    "odylith_execution_profile": {
                        "confidence": {"score": 3, "level": "high"},
                        "selection_mode": "bounded_write",
                        "delegate_preference": "delegate",
                        "constraints": {"route_ready": True, "narrowing_required": False, "spawn_worthiness": 3},
                    },
                    "parallelism": {"hint": "bounded_parallel_candidate", "confidence": 3},
                },
            },
        }
    )

    decision = orchestrator.orchestrate_prompt(request, repo_root=tmp_path)

    assert decision.mode == orchestrator.OrchestrationMode.SERIAL_BATCH.value
    assert any("staying local or running in order" in note for note in decision.budget_notes)
    assert all("advisory loop" not in note for note in decision.budget_notes)
    assert all("hold-local" not in note for note in decision.budget_notes)


def test_router_promotes_grounded_bounded_write_when_depth_is_earned(tmp_path: Path) -> None:
    request = router.route_request_from_mapping(
        {
            "prompt": "Update the bounded implementation in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Update the implementation", "Keep validation green"],
            "allowed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_router.py"],
            "task_kind": "implementation",
            "needs_write": True,
            "accuracy_preference": "balanced",
            "context_signals": {
                "routing_handoff": {
                    "grounding": {"grounded": True, "score": 4},
                    "routing_confidence": "high",
                    "route_ready": True,
                    "narrowing_required": False,
                    "packet_quality": {
                        "evidence_quality": {"score": 4, "level": "high"},
                        "actionability": {"score": 4, "level": "high"},
                        "validation_pressure": {"score": 3, "level": "high"},
                        "context_density": {"score": 3, "level": "high"},
                        "reasoning_readiness": {
                            "score": 3,
                            "level": "high",
                            "mode": "bounded_write",
                            "deep_reasoning_ready": True,
                        },
                        "evidence_diversity": {"score": 3, "level": "high"},
                        "utility_profile": {
                            "score": 86,
                            "level": "high",
                            "token_efficiency": {"score": 3, "level": "high"},
                        },
                        "native_spawn_ready": True,
                        "reasoning_bias": "accuracy_first",
                        "parallelism_hint": "serial_preferred",
                    },
                    "odylith_execution_profile": {
                        "profile": "write_high",
                        "model": "gpt-5.3-codex",
                        "reasoning_effort": "high",
                        "agent_role": "worker",
                        "selection_mode": "bounded_write",
                        "delegate_preference": "delegate",
                        "confidence": {"score": 3, "level": "high"},
                        "constraints": {
                            "route_ready": True,
                            "narrowing_required": False,
                            "spawn_worthiness": 4,
                            "merge_burden": 1,
                            "reasoning_mode": "bounded_write",
                        },
                    },
                },
                "optimization_snapshot": {
                    "quality_posture": {
                        "within_budget_rate": 0.9,
                        "route_ready_rate": 0.85,
                        "native_spawn_ready_rate": 0.85,
                        "deep_reasoning_ready_rate": 0.8,
                        "high_utility_rate": 0.7,
                        "avg_effective_yield_score": 0.82,
                        "high_yield_rate": 0.7,
                        "reliable_high_yield_rate": 0.6,
                        "runtime_backed_execution_rate": 0.8,
                        "high_execution_confidence_rate": 0.75,
                        "packet_alignment_rate": 0.8,
                        "reliable_packet_alignment_rate": 0.75,
                    },
                    "control_advisories": {
                        "state": "stable",
                        "confidence": {"score": 3, "level": "high"},
                        "evidence_strength": {"score": 3, "level": "high"},
                        "reasoning_mode": "earn_depth",
                        "depth": "promote_when_grounded",
                        "delegation": "runtime_backed_delegate",
                    },
                    "learning_loop": {"state": "stable"},
                },
            },
        }
    )

    decision = router.route_request(request, repo_root=tmp_path)

    assert decision.profile == router.RouterProfile.CODEX_HIGH.value
    assert decision.routing_confidence >= 3
    assert int(decision.assessment["earned_depth"]) >= 3
    assert int(decision.assessment["delegation_readiness"]) >= 3
    assert any("earned_depth=" in line for line in decision.explanation_lines)


def test_orchestrator_keeps_disjoint_write_serial_when_delegation_readiness_is_weak() -> None:
    assessment = router.TaskAssessment(
        prompt="Implement the bounded change across scripts/example.py and services/example.py.",
        task_kind="implementation",
        task_family="bounded_feature",
        phase="implementation",
        needs_write=True,
        correctness_critical=False,
        feature_implementation=True,
        mixed_phase=False,
        requires_multi_agent_adjudication=False,
        evolving_context_required=False,
        evidence_cone_grounded=True,
        ambiguity=1,
        blast_radius=1,
        context_breadth=2,
        coordination_cost=1,
        reversibility_risk=1,
        mechanicalness=0,
        write_scope_clarity=2,
        acceptance_clarity=1,
        artifact_specificity=1,
        validation_clarity=1,
        latency_pressure=0,
        requested_depth=2,
        accuracy_bias=2,
        earned_depth=2,
        delegation_readiness=1,
        base_confidence=2,
        accuracy_preference="balanced",
        context_signal_summary={
            "route_ready": True,
            "odylith_execution_route_ready": True,
            "narrowing_required": False,
            "odylith_execution_narrowing_required": False,
            "native_spawn_ready": True,
            "spawn_worthiness_score": 2,
            "odylith_execution_spawn_worthiness": 2,
            "merge_burden_score": 1,
            "odylith_execution_confidence_score": 3,
            "odylith_execution_delegate_preference": "delegate",
            "odylith_execution_selection_mode": "bounded_write",
            "parallelism_hint": "",
        },
    )

    mode, notes = orchestrator._adaptive_batch_mode(  # noqa: SLF001
        orchestrator.OrchestrationRequest(
            prompt="Implement the bounded change across scripts/example.py and services/example.py.",
            candidate_paths=["scripts/example.py", "services/example.py"],
            needs_write=True,
            evidence_cone_grounded=True,
        ),
        assessment,
        safety=orchestrator.ParallelSafetyClass.DISJOINT_WRITE_SAFE,
        groups=[["scripts/example.py"], ["services/example.py"]],
        tuning=orchestrator.TuningState(),
    )

    assert mode == orchestrator.OrchestrationMode.SERIAL_BATCH
    assert any("delegation readiness" in note for note in notes)


def test_orchestrator_keeps_read_only_narrowing_slice_local() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Review the shared guidance slice.",
        candidate_paths=["AGENTS.md", "agents-guidelines/TOOLING.MD"],
        needs_write=False,
        evidence_cone_grounded=True,
    )
    assessment = router.TaskAssessment(
        prompt=request.prompt,
        task_kind="analysis",
        task_family="analysis",
        phase="analysis",
        needs_write=False,
        correctness_critical=False,
        feature_implementation=False,
        mixed_phase=False,
        requires_multi_agent_adjudication=False,
        evolving_context_required=False,
        evidence_cone_grounded=True,
        ambiguity=2,
        blast_radius=2,
        context_breadth=2,
        coordination_cost=1,
        reversibility_risk=0,
        mechanicalness=1,
        write_scope_clarity=0,
        acceptance_clarity=2,
        artifact_specificity=1,
        validation_clarity=0,
        latency_pressure=0,
        requested_depth=1,
        accuracy_bias=1,
        earned_depth=1,
        delegation_readiness=0,
        base_confidence=1,
        accuracy_preference="balanced",
        context_signal_summary={
            "route_ready": False,
            "odylith_execution_route_ready": False,
            "narrowing_required": True,
            "odylith_execution_narrowing_required": True,
            "native_spawn_ready": False,
            "odylith_execution_delegate_preference": "hold_local",
            "odylith_execution_selection_mode": "narrow_first",
        },
    )

    reasons, notes = orchestrator._should_keep_local(request, assessment)  # noqa: SLF001

    assert "odylith-local-narrowing" in reasons
    assert "odylith-read-only-local-narrowing" in reasons
    assert any("narrowing" in note for note in notes)
    assert all("runtime handoff" not in note for note in notes)


def test_orchestrator_marks_non_repo_work_prompts_local(tmp_path: Path) -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Explain how Odylith's reasoning ladder works across consumer, pinned dogfood, and detached source-local maintainer-dev lanes.",
        repo_work=False,
    )

    decision = orchestrator.orchestrate_prompt(request, repo_root=tmp_path)

    assert decision.mode == orchestrator.OrchestrationMode.LOCAL_ONLY.value
    assert "non-repo-work-prompt" in decision.local_only_reasons


def test_coordination_heavy_write_requires_route_ready_runtime_before_decomposition() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Implement the grounded install-time slice.",
        candidate_paths=[
            "src/odylith/install/agents.py",
            "src/odylith/install/manager.py",
            "tests/unit/install/test_agents.py",
        ],
        needs_write=True,
        evidence_cone_grounded=True,
    )
    blocked_assessment = router.TaskAssessment(
        prompt=request.prompt,
        task_kind="implementation",
        task_family="bounded_feature",
        phase="implementation",
        needs_write=True,
        correctness_critical=False,
        feature_implementation=True,
        mixed_phase=False,
        requires_multi_agent_adjudication=False,
        evolving_context_required=False,
        evidence_cone_grounded=True,
        ambiguity=1,
        blast_radius=1,
        context_breadth=2,
        coordination_cost=4,
        reversibility_risk=1,
        mechanicalness=1,
        write_scope_clarity=4,
        acceptance_clarity=3,
        artifact_specificity=3,
        validation_clarity=2,
        latency_pressure=0,
        requested_depth=2,
        accuracy_bias=2,
        earned_depth=2,
        delegation_readiness=2,
        base_confidence=2,
        accuracy_preference="accuracy",
        context_signal_summary={
            "route_ready": False,
            "odylith_execution_route_ready": False,
            "narrowing_required": True,
            "odylith_execution_narrowing_required": True,
            "native_spawn_ready": False,
        },
    )
    ready_assessment = router.TaskAssessment(
        **{
            **blocked_assessment.__dict__,
            "context_signal_summary": {
                "route_ready": True,
                "odylith_execution_route_ready": True,
                "narrowing_required": False,
                "odylith_execution_narrowing_required": False,
                "native_spawn_ready": True,
            },
        }
    )

    assert orchestrator._can_decompose_coordination_heavy_write(request, blocked_assessment) is False  # noqa: SLF001
    assert orchestrator._can_decompose_coordination_heavy_write(request, ready_assessment) is True  # noqa: SLF001


def test_odylith_consumer_paths_do_not_collapse_into_governance_followups() -> None:
    assert orchestrator._scope_role(["odylith/skills/subagent-router/SKILL.md"], needs_write=True) == "contract"  # noqa: SLF001
    assert orchestrator._scope_role(["odylith/runtime/SUBAGENT_OPERATIONS.md"], needs_write=True) == "contract"  # noqa: SLF001
    assert orchestrator._scope_role(["odylith/index.html"], needs_write=True) == "implementation"  # noqa: SLF001

    assert orchestrator._is_host_local_governance_path("odylith/skills/subagent-router/SKILL.md") is False  # noqa: SLF001
    assert orchestrator._is_host_local_governance_path("odylith/runtime/SUBAGENT_OPERATIONS.md") is False  # noqa: SLF001
    assert orchestrator._is_host_local_governance_path("odylith/index.html") is False  # noqa: SLF001
    assert orchestrator._is_host_local_governance_path("odylith/radar/source/INDEX.md") is True  # noqa: SLF001
