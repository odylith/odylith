from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.evaluation import odylith_benchmark_execution_engine
from odylith.runtime.evaluation import odylith_benchmark_prompt_family_rules
from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import odylith_benchmark_taxonomy


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_execution_engine_family_is_curated_and_taxonomized() -> None:
    assert odylith_benchmark_prompt_family_rules.family_zero_support_doc_expansion("execution_engine") is True
    assert odylith_benchmark_prompt_family_rules.family_uses_curated_doc_overrides("execution_engine") is True
    assert odylith_benchmark_prompt_family_rules.family_anchors_all_required_docs("execution_engine") is True
    assert (
        odylith_benchmark_prompt_family_rules.support_doc_family_rank(
            path="odylith/registry/source/components/execution-engine/CURRENT_SPEC.md",
            family="execution_engine",
        )
        == 0
    )
    assert odylith_benchmark_taxonomy.family_group_label("execution_engine") == "Grounding / Orchestration Control"


def test_execution_engine_family_prefers_governance_slice_and_bounded_profile() -> None:
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "execution_engine", "workstream": "B-073"}
    ) == "governance_slice"

    profile = odylith_context_engine_hot_path_delivery_runtime._impact_family_profile(  # noqa: SLF001
        hot_path=True,
        family_hint="execution_engine",
        workstream_hint="B-073",
        component_hint="execution-engine",
    )

    assert profile["family"] == "execution_engine"
    assert profile["prefer_explicit_workstream"] is True
    assert profile["prefer_explicit_component"] is True
    assert profile["allow_miss_recovery"] is False
    assert profile["include_notes"] is False
    assert profile["include_bugs"] is False
    assert profile["include_code_neighbors"] is False


def test_execution_engine_summary_aggregates_family_metrics() -> None:
    summary = runner._mode_summary(  # noqa: SLF001
        mode="odylith_on",
        scenario_rows=[
            {
                "kind": "packet",
                "scenario_family": "execution_engine",
                "latency_ms": 8.0,
                "effective_estimated_tokens": 72,
                "packet": {
                    "execution_engine_present": True,
                    "execution_engine_outcome": "admit",
                    "execution_engine_mode": "verify",
                    "execution_engine_next_move": "verify.selected_matrix",
                    "execution_engine_current_phase": "verify",
                    "execution_engine_last_successful_phase": "verify",
                    "execution_engine_closure": "incomplete",
                    "execution_engine_resume_token": "resume:governance_slice",
                    "execution_engine_validation_archetype": "verify",
                    "execution_engine_authoritative_lane": "context_engine.governance_slice.authoritative",
                    "execution_engine_host_family": "codex",
                    "execution_engine_requires_reanchor": False,
                },
                "expectation_ok": True,
                "expectation_details": {
                    "expected_execution_engine_outcome": ["admit"],
                    "expected_execution_engine_mode": ["verify"],
                    "expected_execution_engine_next_move": ["verify.selected_matrix"],
                    "expected_execution_engine_current_phase": ["verify"],
                    "expected_execution_engine_last_successful_phase": ["verify"],
                    "expected_execution_engine_closure": ["incomplete"],
                    "expected_execution_engine_resume_token": ["resume:governance_slice"],
                    "expected_execution_engine_validation_archetype": ["verify"],
                    "expected_execution_engine_authoritative_lane": [
                        "context_engine.governance_slice.authoritative"
                    ],
                    "expected_execution_engine_host_family": ["codex"],
                    "expected_execution_engine_requires_reanchor": False,
                },
            },
            {
                "kind": "packet",
                "scenario_family": "execution_engine",
                "latency_ms": 9.0,
                "effective_estimated_tokens": 68,
                "packet": {
                    "execution_engine_present": True,
                    "execution_engine_outcome": "admit",
                    "execution_engine_mode": "recover",
                    "execution_engine_next_move": "recover.current_blocker",
                    "execution_engine_current_phase": "status synthesis",
                    "execution_engine_closure": "safe",
                    "execution_engine_resume_token": "resume:impact",
                    "execution_engine_validation_archetype": "recover",
                    "execution_engine_authoritative_lane": "context_engine.impact.authoritative",
                    "execution_engine_host_family": "codex",
                    "execution_engine_requires_reanchor": False,
                },
                "expectation_ok": True,
                "expectation_details": {
                    "expected_execution_engine_outcome": ["admit"],
                    "expected_execution_engine_mode": ["recover"],
                    "expected_execution_engine_next_move": ["recover.current_blocker"],
                    "expected_execution_engine_current_phase": ["status synthesis"],
                    "expected_execution_engine_closure": ["safe"],
                    "expected_execution_engine_resume_token": ["resume:impact"],
                    "expected_execution_engine_validation_archetype": ["recover"],
                    "expected_execution_engine_authoritative_lane": [
                        "context_engine.impact.authoritative"
                    ],
                    "expected_execution_engine_host_family": ["codex"],
                    "expected_execution_engine_requires_reanchor": False,
                    "expected_execution_engine_delegation_guard_blocked": True,
                    "expected_execution_engine_parallelism_guard_blocked": True,
                },
            },
        ],
    )

    assert summary["execution_engine_backed_scenario_count"] == 2
    assert summary["execution_engine_present_rate"] == 1.0
    assert summary["execution_engine_resume_token_present_rate"] == 1.0
    assert summary["execution_engine_expected_outcome_count"] == 2
    assert summary["execution_engine_expected_mode_count"] == 2
    assert summary["execution_engine_expected_next_move_count"] == 2
    assert summary["execution_engine_expected_closure_count"] == 2
    assert summary["execution_engine_expected_validation_archetype_count"] == 2
    assert summary["execution_engine_expected_current_phase_count"] == 2
    assert summary["execution_engine_expected_last_successful_phase_count"] == 1
    assert summary["execution_engine_expected_authoritative_lane_count"] == 2
    assert summary["execution_engine_expected_resume_token_count"] == 2
    assert summary["execution_engine_expected_host_family_count"] == 2
    assert summary["execution_engine_expected_reanchor_count"] == 2
    assert summary["execution_engine_expected_delegation_guard_count"] == 1
    assert summary["execution_engine_expected_parallelism_guard_count"] == 1
    assert summary["execution_engine_false_admit_rate"] == 0.0
    assert summary["execution_engine_false_deny_rate"] == 0.0
    assert summary["execution_engine_outcome_accuracy_rate"] == 1.0
    assert summary["execution_engine_mode_accuracy_rate"] == 1.0
    assert summary["execution_engine_next_move_accuracy_rate"] == 1.0
    assert summary["execution_engine_closure_accuracy_rate"] == 1.0
    assert summary["execution_engine_validation_archetype_accuracy_rate"] == 1.0
    assert summary["execution_engine_current_phase_accuracy_rate"] == 1.0
    assert summary["execution_engine_last_successful_phase_accuracy_rate"] == 1.0
    assert summary["execution_engine_authoritative_lane_accuracy_rate"] == 1.0
    assert summary["execution_engine_resume_token_accuracy_rate"] == 1.0
    assert summary["execution_engine_host_family_accuracy_rate"] == 1.0
    assert summary["execution_engine_reanchor_accuracy_rate"] == 1.0
    assert summary["execution_engine_delegation_guard_accuracy_rate"] == 1.0
    assert summary["execution_engine_parallelism_guard_accuracy_rate"] == 1.0


def test_execution_engine_family_alias_tracks_false_admit_and_false_deny_rates() -> None:
    summary = odylith_benchmark_execution_engine.summary_from_rows(
        [
            {
                "scenario_family": "execution_engine",
                "packet": {
                    "execution_engine_present": True,
                    "execution_engine_outcome": "admit",
                },
                "expectation_details": {
                    "expected_execution_engine_outcome": ["deny"],
                },
            },
            {
                "scenario_family": "execution-engine",
                "packet": {
                    "execution_engine_present": True,
                    "execution_engine_outcome": "deny",
                },
                "expectation_details": {
                    "expected_execution_engine_outcome": ["admit"],
                },
            },
        ]
    )

    assert summary["execution_engine_backed_scenario_count"] == 2
    assert summary["execution_engine_false_admit_rate"] == 0.5
    assert summary["execution_engine_false_deny_rate"] == 0.5
    assert summary["execution_engine_outcome_accuracy_rate"] == 0.0


def test_execution_engine_summary_comparison_includes_family_deltas() -> None:
    comparison = runner._summary_comparison(  # noqa: SLF001
        candidate_mode="odylith_on",
        baseline_mode="raw_agent_baseline",
        mode_summaries={
            "odylith_on": {
                "execution_engine_present_rate": 1.0,
                "execution_engine_resume_token_present_rate": 1.0,
                "execution_engine_false_admit_rate": 0.0,
                "execution_engine_false_deny_rate": 0.0,
                "execution_engine_outcome_accuracy_rate": 1.0,
                "execution_engine_mode_accuracy_rate": 1.0,
                "execution_engine_next_move_accuracy_rate": 1.0,
                "execution_engine_closure_accuracy_rate": 1.0,
                "execution_engine_validation_archetype_accuracy_rate": 1.0,
                "execution_engine_current_phase_accuracy_rate": 1.0,
                "execution_engine_authoritative_lane_accuracy_rate": 1.0,
                "execution_engine_resume_token_accuracy_rate": 1.0,
                "execution_engine_host_family_accuracy_rate": 1.0,
                "execution_engine_reanchor_accuracy_rate": 1.0,
                "execution_engine_delegation_guard_accuracy_rate": 1.0,
                "execution_engine_parallelism_guard_accuracy_rate": 1.0,
            },
            "raw_agent_baseline": {
                "execution_engine_present_rate": 0.0,
                "execution_engine_resume_token_present_rate": 0.0,
                "execution_engine_false_admit_rate": 1.0,
                "execution_engine_false_deny_rate": 1.0,
                "execution_engine_outcome_accuracy_rate": 0.0,
                "execution_engine_mode_accuracy_rate": 0.0,
                "execution_engine_next_move_accuracy_rate": 0.0,
                "execution_engine_closure_accuracy_rate": 0.0,
                "execution_engine_validation_archetype_accuracy_rate": 0.0,
                "execution_engine_current_phase_accuracy_rate": 0.0,
                "execution_engine_authoritative_lane_accuracy_rate": 0.0,
                "execution_engine_resume_token_accuracy_rate": 0.0,
                "execution_engine_host_family_accuracy_rate": 0.0,
                "execution_engine_reanchor_accuracy_rate": 0.0,
                "execution_engine_delegation_guard_accuracy_rate": 0.0,
                "execution_engine_parallelism_guard_accuracy_rate": 0.0,
            },
        },
    )

    assert comparison["execution_engine_present_rate_delta"] == 1.0
    assert comparison["execution_engine_resume_token_present_delta"] == 1.0
    assert comparison["execution_engine_false_admit_rate_delta"] == -1.0
    assert comparison["execution_engine_false_deny_rate_delta"] == -1.0
    assert comparison["execution_engine_outcome_accuracy_delta"] == 1.0
    assert comparison["execution_engine_mode_accuracy_delta"] == 1.0
    assert comparison["execution_engine_next_move_accuracy_delta"] == 1.0
    assert comparison["execution_engine_closure_accuracy_delta"] == 1.0
    assert comparison["execution_engine_validation_archetype_accuracy_delta"] == 1.0
    assert comparison["execution_engine_current_phase_accuracy_delta"] == 1.0
    assert comparison["execution_engine_authoritative_lane_accuracy_delta"] == 1.0
    assert comparison["execution_engine_resume_token_accuracy_delta"] == 1.0
    assert comparison["execution_engine_host_family_accuracy_delta"] == 1.0
    assert comparison["execution_engine_reanchor_accuracy_delta"] == 1.0
    assert comparison["execution_engine_delegation_guard_accuracy_delta"] == 1.0
    assert comparison["execution_engine_parallelism_guard_accuracy_delta"] == 1.0


def test_acceptance_holds_on_execution_engine_regressions() -> None:
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
                "execution_engine_backed_scenario_count": 1,
                "execution_engine_present_rate": 0.0,
                "execution_engine_resume_token_present_rate": 0.0,
                "execution_engine_expected_outcome_count": 1,
                "execution_engine_expected_mode_count": 1,
                "execution_engine_expected_next_move_count": 1,
                "execution_engine_expected_closure_count": 1,
                "execution_engine_expected_validation_archetype_count": 1,
                "execution_engine_expected_current_phase_count": 1,
                "execution_engine_expected_authoritative_lane_count": 1,
                "execution_engine_expected_resume_token_count": 1,
                "execution_engine_expected_host_family_count": 1,
                "execution_engine_expected_reanchor_count": 1,
                "execution_engine_outcome_accuracy_rate": 0.0,
                "execution_engine_mode_accuracy_rate": 0.0,
                "execution_engine_next_move_accuracy_rate": 0.0,
                "execution_engine_closure_accuracy_rate": 0.0,
                "execution_engine_validation_archetype_accuracy_rate": 0.0,
                "execution_engine_current_phase_accuracy_rate": 0.0,
                "execution_engine_authoritative_lane_accuracy_rate": 0.0,
                "execution_engine_resume_token_accuracy_rate": 0.0,
                "execution_engine_host_family_accuracy_rate": 0.0,
                "execution_engine_reanchor_accuracy_rate": 0.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "execution_engine_backed_scenario_count": 1,
                "execution_engine_present_rate": 1.0,
                "execution_engine_resume_token_present_rate": 1.0,
                "execution_engine_expected_outcome_count": 1,
                "execution_engine_expected_mode_count": 1,
                "execution_engine_expected_next_move_count": 1,
                "execution_engine_expected_closure_count": 1,
                "execution_engine_expected_validation_archetype_count": 1,
                "execution_engine_expected_current_phase_count": 1,
                "execution_engine_expected_authoritative_lane_count": 1,
                "execution_engine_expected_resume_token_count": 1,
                "execution_engine_expected_host_family_count": 1,
                "execution_engine_expected_reanchor_count": 1,
                "execution_engine_outcome_accuracy_rate": 1.0,
                "execution_engine_mode_accuracy_rate": 1.0,
                "execution_engine_next_move_accuracy_rate": 1.0,
                "execution_engine_closure_accuracy_rate": 1.0,
                "execution_engine_validation_archetype_accuracy_rate": 1.0,
                "execution_engine_current_phase_accuracy_rate": 1.0,
                "execution_engine_authoritative_lane_accuracy_rate": 1.0,
                "execution_engine_resume_token_accuracy_rate": 1.0,
                "execution_engine_host_family_accuracy_rate": 1.0,
                "execution_engine_reanchor_accuracy_rate": 1.0,
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
            "execution_engine": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "execution_engine_backed_scenario_count": 1,
                    "execution_engine_present_rate": 0.0,
                    "execution_engine_resume_token_present_rate": 0.0,
                    "execution_engine_expected_outcome_count": 1,
                    "execution_engine_expected_mode_count": 1,
                    "execution_engine_expected_next_move_count": 1,
                    "execution_engine_expected_closure_count": 1,
                    "execution_engine_expected_validation_archetype_count": 1,
                    "execution_engine_expected_current_phase_count": 1,
                    "execution_engine_expected_authoritative_lane_count": 1,
                    "execution_engine_expected_resume_token_count": 1,
                    "execution_engine_expected_host_family_count": 1,
                    "execution_engine_expected_reanchor_count": 1,
                    "execution_engine_outcome_accuracy_rate": 0.0,
                    "execution_engine_mode_accuracy_rate": 0.0,
                    "execution_engine_next_move_accuracy_rate": 0.0,
                    "execution_engine_closure_accuracy_rate": 0.0,
                    "execution_engine_validation_archetype_accuracy_rate": 0.0,
                    "execution_engine_current_phase_accuracy_rate": 0.0,
                    "execution_engine_authoritative_lane_accuracy_rate": 0.0,
                    "execution_engine_resume_token_accuracy_rate": 0.0,
                    "execution_engine_host_family_accuracy_rate": 0.0,
                    "execution_engine_reanchor_accuracy_rate": 0.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "execution_engine_backed_scenario_count": 1,
                    "execution_engine_present_rate": 1.0,
                    "execution_engine_resume_token_present_rate": 1.0,
                    "execution_engine_expected_outcome_count": 1,
                    "execution_engine_expected_mode_count": 1,
                    "execution_engine_expected_next_move_count": 1,
                    "execution_engine_expected_closure_count": 1,
                    "execution_engine_expected_validation_archetype_count": 1,
                    "execution_engine_expected_current_phase_count": 1,
                    "execution_engine_expected_authoritative_lane_count": 1,
                    "execution_engine_expected_resume_token_count": 1,
                    "execution_engine_expected_host_family_count": 1,
                    "execution_engine_expected_reanchor_count": 1,
                    "execution_engine_outcome_accuracy_rate": 1.0,
                    "execution_engine_mode_accuracy_rate": 1.0,
                    "execution_engine_next_move_accuracy_rate": 1.0,
                    "execution_engine_closure_accuracy_rate": 1.0,
                    "execution_engine_validation_archetype_accuracy_rate": 1.0,
                    "execution_engine_current_phase_accuracy_rate": 1.0,
                    "execution_engine_authoritative_lane_accuracy_rate": 1.0,
                    "execution_engine_resume_token_accuracy_rate": 1.0,
                    "execution_engine_host_family_accuracy_rate": 1.0,
                    "execution_engine_reanchor_accuracy_rate": 1.0,
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
    assert acceptance["checks"]["execution_engine_present"] is False
    assert acceptance["checks"]["execution_engine_resume_token_present"] is False
    assert acceptance["checks"]["execution_engine_outcome_accurate"] is False
    assert acceptance["checks"]["execution_engine_mode_accurate"] is False
    assert acceptance["checks"]["execution_engine_next_move_accurate"] is False
    assert acceptance["checks"]["execution_engine_closure_accurate"] is False
    assert acceptance["checks"]["execution_engine_validation_accurate"] is False
    assert acceptance["checks"]["execution_engine_current_phase_accurate"] is False
    assert acceptance["checks"]["execution_engine_authoritative_lane_accurate"] is False
    assert acceptance["checks"]["execution_engine_resume_token_accurate"] is False
    assert acceptance["checks"]["execution_engine_host_family_accurate"] is False
    assert acceptance["checks"]["execution_engine_reanchor_accurate"] is False
    assert "execution_engine" in acceptance["weak_families"]


def _execution_engine_probe_summary(*, component: str, family: str = "execution_engine") -> dict[str, object]:
    scenario = {
        "scenario_id": "probe-execution-engine-core",
        "family": family,
        "packet_source": "governance_slice",
        "changed_paths": [
            "src/odylith/runtime/execution_engine/policy.py",
            "src/odylith/runtime/execution_engine/runtime_lane_policy.py",
            "tests/unit/runtime/test_execution_engine.py",
        ],
        "workstream": "B-073",
        "component": component,
        "validation_commands": [
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_execution_engine.py"
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
    return summary


def test_execution_engine_probe_packet_exposes_current_repo_contract() -> None:
    summary = _execution_engine_probe_summary(component="execution-engine")

    assert summary["execution_engine_present"] is True
    assert summary["execution_engine_outcome"] == "admit"
    assert summary["execution_engine_mode"] == "verify"
    assert summary["execution_engine_next_move"] == "verify.selected_matrix"
    assert summary["execution_engine_closure"] == "incomplete"
    assert summary["execution_engine_validation_archetype"] == "verify"
    assert summary["execution_engine_resume_token"] == "resume:governance_slice"
    assert summary["execution_engine_host_family"] == "codex"


def test_execution_engine_historical_component_id_fails_closed() -> None:
    summary = _execution_engine_probe_summary(component="execution-" + "governance")

    assert summary["route_ready"] is False
    assert summary["native_spawn_ready"] is False
    assert summary["execution_engine_mode"] == "recover"
    assert summary["execution_engine_next_move"] == "recover.current_blocker"


def test_execution_engine_probe_broad_scope_stays_fail_closed() -> None:
    scenario = {
        "scenario_id": "probe-execution-engine-broad-scope",
        "family": "execution_engine",
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
    assert summary["execution_engine_mode"] == "recover"
    assert summary["execution_engine_next_move"] == "recover.current_blocker"
    assert summary["execution_engine_closure"] == "safe"
    assert summary["execution_engine_resume_token"] == "resume:impact"


def test_execution_engine_module_comparison_smoke() -> None:
    comparison = odylith_benchmark_execution_engine.comparison(
        candidate={"execution_engine_present_rate": 1.0},
        baseline={"execution_engine_present_rate": 0.0},
    )

    assert comparison["execution_engine_present_rate_delta"] == 1.0
