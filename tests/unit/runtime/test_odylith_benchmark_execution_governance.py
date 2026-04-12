from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.evaluation import odylith_benchmark_execution_governance
from odylith.runtime.evaluation import odylith_benchmark_prompt_family_rules
from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import odylith_benchmark_taxonomy


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_execution_governance_family_is_curated_and_taxonomized() -> None:
    assert odylith_benchmark_prompt_family_rules.family_zero_support_doc_expansion("execution_governance") is True
    assert odylith_benchmark_prompt_family_rules.family_uses_curated_doc_overrides("execution_governance") is True
    assert odylith_benchmark_prompt_family_rules.family_anchors_all_required_docs("execution_governance") is True
    assert (
        odylith_benchmark_prompt_family_rules.support_doc_family_rank(
            path="odylith/registry/source/components/execution-governance/CURRENT_SPEC.md",
            family="execution_governance",
        )
        == 0
    )
    assert odylith_benchmark_taxonomy.family_group_label("execution_governance") == "Grounding / Orchestration Control"


def test_execution_governance_family_prefers_governance_slice_and_bounded_profile() -> None:
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "execution_governance", "workstream": "B-073"}
    ) == "governance_slice"

    profile = odylith_context_engine_hot_path_delivery_runtime._impact_family_profile(  # noqa: SLF001
        hot_path=True,
        family_hint="execution_governance",
        workstream_hint="B-073",
        component_hint="execution-governance",
    )

    assert profile["family"] == "execution_governance"
    assert profile["prefer_explicit_workstream"] is True
    assert profile["prefer_explicit_component"] is True
    assert profile["allow_miss_recovery"] is False
    assert profile["include_notes"] is False
    assert profile["include_bugs"] is False
    assert profile["include_code_neighbors"] is False


def test_execution_governance_summary_aggregates_family_metrics() -> None:
    summary = runner._mode_summary(  # noqa: SLF001
        mode="odylith_on",
        scenario_rows=[
            {
                "kind": "packet",
                "scenario_family": "execution_governance",
                "latency_ms": 8.0,
                "effective_estimated_tokens": 72,
                "packet": {
                    "execution_governance_present": True,
                    "execution_governance_outcome": "admit",
                    "execution_governance_mode": "verify",
                    "execution_governance_next_move": "verify.selected_matrix",
                    "execution_governance_current_phase": "verify",
                    "execution_governance_last_successful_phase": "verify",
                    "execution_governance_closure": "incomplete",
                    "execution_governance_resume_token": "resume:governance_slice",
                    "execution_governance_validation_archetype": "verify",
                    "execution_governance_authoritative_lane": "context_engine.governance_slice.authoritative",
                    "execution_governance_host_family": "codex",
                    "execution_governance_requires_reanchor": False,
                },
                "expectation_ok": True,
                "expectation_details": {
                    "expected_execution_governance_outcome": ["admit"],
                    "expected_execution_governance_mode": ["verify"],
                    "expected_execution_governance_next_move": ["verify.selected_matrix"],
                    "expected_execution_governance_current_phase": ["verify"],
                    "expected_execution_governance_last_successful_phase": ["verify"],
                    "expected_execution_governance_closure": ["incomplete"],
                    "expected_execution_governance_resume_token": ["resume:governance_slice"],
                    "expected_execution_governance_validation_archetype": ["verify"],
                    "expected_execution_governance_authoritative_lane": [
                        "context_engine.governance_slice.authoritative"
                    ],
                    "expected_execution_governance_host_family": ["codex"],
                    "expected_execution_governance_requires_reanchor": False,
                },
            },
            {
                "kind": "packet",
                "scenario_family": "execution_governance",
                "latency_ms": 9.0,
                "effective_estimated_tokens": 68,
                "packet": {
                    "execution_governance_present": True,
                    "execution_governance_outcome": "admit",
                    "execution_governance_mode": "recover",
                    "execution_governance_next_move": "recover.current_blocker",
                    "execution_governance_current_phase": "status synthesis",
                    "execution_governance_closure": "safe",
                    "execution_governance_resume_token": "resume:impact",
                    "execution_governance_validation_archetype": "recover",
                    "execution_governance_authoritative_lane": "context_engine.impact.authoritative",
                    "execution_governance_host_family": "codex",
                    "execution_governance_requires_reanchor": False,
                },
                "expectation_ok": True,
                "expectation_details": {
                    "expected_execution_governance_outcome": ["admit"],
                    "expected_execution_governance_mode": ["recover"],
                    "expected_execution_governance_next_move": ["recover.current_blocker"],
                    "expected_execution_governance_current_phase": ["status synthesis"],
                    "expected_execution_governance_closure": ["safe"],
                    "expected_execution_governance_resume_token": ["resume:impact"],
                    "expected_execution_governance_validation_archetype": ["recover"],
                    "expected_execution_governance_authoritative_lane": [
                        "context_engine.impact.authoritative"
                    ],
                    "expected_execution_governance_host_family": ["codex"],
                    "expected_execution_governance_requires_reanchor": False,
                },
            },
        ],
    )

    assert summary["execution_governance_backed_scenario_count"] == 2
    assert summary["execution_governance_present_rate"] == 1.0
    assert summary["execution_governance_resume_token_present_rate"] == 1.0
    assert summary["execution_governance_expected_outcome_count"] == 2
    assert summary["execution_governance_expected_mode_count"] == 2
    assert summary["execution_governance_expected_next_move_count"] == 2
    assert summary["execution_governance_expected_closure_count"] == 2
    assert summary["execution_governance_expected_validation_archetype_count"] == 2
    assert summary["execution_governance_expected_current_phase_count"] == 2
    assert summary["execution_governance_expected_last_successful_phase_count"] == 1
    assert summary["execution_governance_expected_authoritative_lane_count"] == 2
    assert summary["execution_governance_expected_resume_token_count"] == 2
    assert summary["execution_governance_expected_host_family_count"] == 2
    assert summary["execution_governance_expected_reanchor_count"] == 2
    assert summary["execution_governance_outcome_accuracy_rate"] == 1.0
    assert summary["execution_governance_mode_accuracy_rate"] == 1.0
    assert summary["execution_governance_next_move_accuracy_rate"] == 1.0
    assert summary["execution_governance_closure_accuracy_rate"] == 1.0
    assert summary["execution_governance_validation_archetype_accuracy_rate"] == 1.0
    assert summary["execution_governance_current_phase_accuracy_rate"] == 1.0
    assert summary["execution_governance_last_successful_phase_accuracy_rate"] == 1.0
    assert summary["execution_governance_authoritative_lane_accuracy_rate"] == 1.0
    assert summary["execution_governance_resume_token_accuracy_rate"] == 1.0
    assert summary["execution_governance_host_family_accuracy_rate"] == 1.0
    assert summary["execution_governance_reanchor_accuracy_rate"] == 1.0


def test_execution_governance_summary_comparison_includes_family_deltas() -> None:
    comparison = runner._summary_comparison(  # noqa: SLF001
        candidate_mode="odylith_on",
        baseline_mode="raw_agent_baseline",
        mode_summaries={
            "odylith_on": {
                "execution_governance_present_rate": 1.0,
                "execution_governance_resume_token_present_rate": 1.0,
                "execution_governance_outcome_accuracy_rate": 1.0,
                "execution_governance_mode_accuracy_rate": 1.0,
                "execution_governance_next_move_accuracy_rate": 1.0,
                "execution_governance_closure_accuracy_rate": 1.0,
                "execution_governance_validation_archetype_accuracy_rate": 1.0,
                "execution_governance_current_phase_accuracy_rate": 1.0,
                "execution_governance_authoritative_lane_accuracy_rate": 1.0,
                "execution_governance_resume_token_accuracy_rate": 1.0,
                "execution_governance_host_family_accuracy_rate": 1.0,
                "execution_governance_reanchor_accuracy_rate": 1.0,
            },
            "raw_agent_baseline": {
                "execution_governance_present_rate": 0.0,
                "execution_governance_resume_token_present_rate": 0.0,
                "execution_governance_outcome_accuracy_rate": 0.0,
                "execution_governance_mode_accuracy_rate": 0.0,
                "execution_governance_next_move_accuracy_rate": 0.0,
                "execution_governance_closure_accuracy_rate": 0.0,
                "execution_governance_validation_archetype_accuracy_rate": 0.0,
                "execution_governance_current_phase_accuracy_rate": 0.0,
                "execution_governance_authoritative_lane_accuracy_rate": 0.0,
                "execution_governance_resume_token_accuracy_rate": 0.0,
                "execution_governance_host_family_accuracy_rate": 0.0,
                "execution_governance_reanchor_accuracy_rate": 0.0,
            },
        },
    )

    assert comparison["execution_governance_present_rate_delta"] == 1.0
    assert comparison["execution_governance_resume_token_present_delta"] == 1.0
    assert comparison["execution_governance_outcome_accuracy_delta"] == 1.0
    assert comparison["execution_governance_mode_accuracy_delta"] == 1.0
    assert comparison["execution_governance_next_move_accuracy_delta"] == 1.0
    assert comparison["execution_governance_closure_accuracy_delta"] == 1.0
    assert comparison["execution_governance_validation_archetype_accuracy_delta"] == 1.0
    assert comparison["execution_governance_current_phase_accuracy_delta"] == 1.0
    assert comparison["execution_governance_authoritative_lane_accuracy_delta"] == 1.0
    assert comparison["execution_governance_resume_token_accuracy_delta"] == 1.0
    assert comparison["execution_governance_host_family_accuracy_delta"] == 1.0
    assert comparison["execution_governance_reanchor_accuracy_delta"] == 1.0


def test_acceptance_holds_on_execution_governance_regressions() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "scenario_count": 1,
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "execution_governance_backed_scenario_count": 1,
                "execution_governance_present_rate": 0.0,
                "execution_governance_resume_token_present_rate": 0.0,
                "execution_governance_expected_outcome_count": 1,
                "execution_governance_expected_mode_count": 1,
                "execution_governance_expected_next_move_count": 1,
                "execution_governance_expected_closure_count": 1,
                "execution_governance_expected_validation_archetype_count": 1,
                "execution_governance_expected_current_phase_count": 1,
                "execution_governance_expected_authoritative_lane_count": 1,
                "execution_governance_expected_resume_token_count": 1,
                "execution_governance_expected_host_family_count": 1,
                "execution_governance_expected_reanchor_count": 1,
                "execution_governance_outcome_accuracy_rate": 0.0,
                "execution_governance_mode_accuracy_rate": 0.0,
                "execution_governance_next_move_accuracy_rate": 0.0,
                "execution_governance_closure_accuracy_rate": 0.0,
                "execution_governance_validation_archetype_accuracy_rate": 0.0,
                "execution_governance_current_phase_accuracy_rate": 0.0,
                "execution_governance_authoritative_lane_accuracy_rate": 0.0,
                "execution_governance_resume_token_accuracy_rate": 0.0,
                "execution_governance_host_family_accuracy_rate": 0.0,
                "execution_governance_reanchor_accuracy_rate": 0.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "execution_governance_backed_scenario_count": 1,
                "execution_governance_present_rate": 1.0,
                "execution_governance_resume_token_present_rate": 1.0,
                "execution_governance_expected_outcome_count": 1,
                "execution_governance_expected_mode_count": 1,
                "execution_governance_expected_next_move_count": 1,
                "execution_governance_expected_closure_count": 1,
                "execution_governance_expected_validation_archetype_count": 1,
                "execution_governance_expected_current_phase_count": 1,
                "execution_governance_expected_authoritative_lane_count": 1,
                "execution_governance_expected_resume_token_count": 1,
                "execution_governance_expected_host_family_count": 1,
                "execution_governance_expected_reanchor_count": 1,
                "execution_governance_outcome_accuracy_rate": 1.0,
                "execution_governance_mode_accuracy_rate": 1.0,
                "execution_governance_next_move_accuracy_rate": 1.0,
                "execution_governance_closure_accuracy_rate": 1.0,
                "execution_governance_validation_archetype_accuracy_rate": 1.0,
                "execution_governance_current_phase_accuracy_rate": 1.0,
                "execution_governance_authoritative_lane_accuracy_rate": 1.0,
                "execution_governance_resume_token_accuracy_rate": 1.0,
                "execution_governance_host_family_accuracy_rate": 1.0,
                "execution_governance_reanchor_accuracy_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "required_path_precision_delta": 0.0,
            "hallucinated_surface_rate_delta": 0.0,
            "validation_success_delta": 0.0,
            "write_surface_precision_delta": 0.0,
            "unnecessary_widening_rate_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": 0.0,
            "median_prompt_token_delta": 0.0,
            "median_total_payload_token_delta": 0.0,
        },
        family_summaries={
            "execution_governance": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "execution_governance_backed_scenario_count": 1,
                    "execution_governance_present_rate": 0.0,
                    "execution_governance_resume_token_present_rate": 0.0,
                    "execution_governance_expected_outcome_count": 1,
                    "execution_governance_expected_mode_count": 1,
                    "execution_governance_expected_next_move_count": 1,
                    "execution_governance_expected_closure_count": 1,
                    "execution_governance_expected_validation_archetype_count": 1,
                    "execution_governance_expected_current_phase_count": 1,
                    "execution_governance_expected_authoritative_lane_count": 1,
                    "execution_governance_expected_resume_token_count": 1,
                    "execution_governance_expected_host_family_count": 1,
                    "execution_governance_expected_reanchor_count": 1,
                    "execution_governance_outcome_accuracy_rate": 0.0,
                    "execution_governance_mode_accuracy_rate": 0.0,
                    "execution_governance_next_move_accuracy_rate": 0.0,
                    "execution_governance_closure_accuracy_rate": 0.0,
                    "execution_governance_validation_archetype_accuracy_rate": 0.0,
                    "execution_governance_current_phase_accuracy_rate": 0.0,
                    "execution_governance_authoritative_lane_accuracy_rate": 0.0,
                    "execution_governance_resume_token_accuracy_rate": 0.0,
                    "execution_governance_host_family_accuracy_rate": 0.0,
                    "execution_governance_reanchor_accuracy_rate": 0.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "execution_governance_backed_scenario_count": 1,
                    "execution_governance_present_rate": 1.0,
                    "execution_governance_resume_token_present_rate": 1.0,
                    "execution_governance_expected_outcome_count": 1,
                    "execution_governance_expected_mode_count": 1,
                    "execution_governance_expected_next_move_count": 1,
                    "execution_governance_expected_closure_count": 1,
                    "execution_governance_expected_validation_archetype_count": 1,
                    "execution_governance_expected_current_phase_count": 1,
                    "execution_governance_expected_authoritative_lane_count": 1,
                    "execution_governance_expected_resume_token_count": 1,
                    "execution_governance_expected_host_family_count": 1,
                    "execution_governance_expected_reanchor_count": 1,
                    "execution_governance_outcome_accuracy_rate": 1.0,
                    "execution_governance_mode_accuracy_rate": 1.0,
                    "execution_governance_next_move_accuracy_rate": 1.0,
                    "execution_governance_closure_accuracy_rate": 1.0,
                    "execution_governance_validation_archetype_accuracy_rate": 1.0,
                    "execution_governance_current_phase_accuracy_rate": 1.0,
                    "execution_governance_authoritative_lane_accuracy_rate": 1.0,
                    "execution_governance_resume_token_accuracy_rate": 1.0,
                    "execution_governance_host_family_accuracy_rate": 1.0,
                    "execution_governance_reanchor_accuracy_rate": 1.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["checks"]["execution_governance_present"] is False
    assert acceptance["checks"]["execution_governance_resume_token_present"] is False
    assert acceptance["checks"]["execution_governance_outcome_accurate"] is False
    assert acceptance["checks"]["execution_governance_mode_accurate"] is False
    assert acceptance["checks"]["execution_governance_next_move_accurate"] is False
    assert acceptance["checks"]["execution_governance_closure_accurate"] is False
    assert acceptance["checks"]["execution_governance_validation_accurate"] is False
    assert acceptance["checks"]["execution_governance_current_phase_accurate"] is False
    assert acceptance["checks"]["execution_governance_authoritative_lane_accurate"] is False
    assert acceptance["checks"]["execution_governance_resume_token_accurate"] is False
    assert acceptance["checks"]["execution_governance_host_family_accurate"] is False
    assert acceptance["checks"]["execution_governance_reanchor_accurate"] is False
    assert "execution_governance" in acceptance["weak_families"]


def test_execution_governance_probe_packet_exposes_current_repo_contract() -> None:
    scenario = {
        "scenario_id": "probe-execution-governance-core",
        "family": "execution_governance",
        "packet_source": "governance_slice",
        "changed_paths": [
            "src/odylith/runtime/execution_engine/policy.py",
            "src/odylith/runtime/execution_engine/runtime_lane_policy.py",
            "tests/unit/runtime/test_execution_governance.py",
        ],
        "workstream": "B-073",
        "component": "execution-governance",
        "validation_commands": [
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_execution_governance.py"
        ],
        "intent": "implementation benchmark",
        "kind": "packet",
        "needs_write": False,
    }

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert summary["execution_governance_present"] is True
    assert summary["execution_governance_outcome"] == "admit"
    assert summary["execution_governance_mode"] == "verify"
    assert summary["execution_governance_next_move"] == "verify.selected_matrix"
    assert summary["execution_governance_closure"] == "incomplete"
    assert summary["execution_governance_validation_archetype"] == "verify"
    assert summary["execution_governance_resume_token"] == "resume:governance_slice"
    assert summary["execution_governance_host_family"] == "codex"


def test_execution_governance_probe_broad_scope_stays_fail_closed() -> None:
    scenario = {
        "scenario_id": "probe-execution-governance-broad-scope",
        "family": "execution_governance",
        "packet_source": "impact",
        "changed_paths": [
            "AGENTS.md",
            "odylith/AGENTS.md",
        ],
        "validation_commands": [],
        "intent": "analysis benchmark",
        "kind": "packet",
        "needs_write": False,
    }

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert summary["packet_state"] == "gated_broad_scope"
    assert summary["selection_state"] == "none"
    assert summary["route_ready"] is False
    assert summary["native_spawn_ready"] is False
    assert summary["execution_governance_mode"] == "recover"
    assert summary["execution_governance_next_move"] == "recover.current_blocker"
    assert summary["execution_governance_closure"] == "safe"
    assert summary["execution_governance_resume_token"] == "resume:impact"


def test_execution_governance_module_comparison_smoke() -> None:
    comparison = odylith_benchmark_execution_governance.comparison(
        candidate={"execution_governance_present_rate": 1.0},
        baseline={"execution_governance_present_rate": 0.0},
    )

    assert comparison["execution_governance_present_rate_delta"] == 1.0
