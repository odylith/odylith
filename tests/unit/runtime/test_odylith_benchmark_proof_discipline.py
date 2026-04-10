from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.evaluation import odylith_benchmark_prompt_family_rules
from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import odylith_benchmark_taxonomy


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_live_proof_discipline_family_uses_governance_packet_lane() -> None:
    assert runner._packet_source_for_scenario({"family": "live_proof_discipline", "workstream": "B-062"}) == "governance_slice"  # noqa: SLF001


def test_live_proof_discipline_family_profile_prefers_explicit_governance_truth() -> None:
    profile = odylith_context_engine_hot_path_delivery_runtime._impact_family_profile(  # noqa: SLF001
        hot_path=True,
        family_hint="live_proof_discipline",
        workstream_hint="B-062",
        component_hint="proof-state",
    )

    assert profile["family"] == "live_proof_discipline"
    assert profile["prefer_explicit_workstream"] is True
    assert profile["prefer_explicit_component"] is True
    assert profile["include_notes"] is False
    assert profile["include_bugs"] is False
    assert profile["include_tests"] is False


def test_live_proof_discipline_family_is_curated_and_taxonomized() -> None:
    assert odylith_benchmark_prompt_family_rules.family_zero_support_doc_expansion("live_proof_discipline") is True
    assert odylith_benchmark_prompt_family_rules.family_uses_curated_doc_overrides("live_proof_discipline") is True
    assert odylith_benchmark_prompt_family_rules.family_anchors_all_required_docs("live_proof_discipline") is True
    assert (
        odylith_benchmark_prompt_family_rules.support_doc_family_rank(
            path="odylith/registry/source/components/proof-state/CURRENT_SPEC.md",
            family="live_proof_discipline",
        )
        == 0
    )
    assert odylith_benchmark_taxonomy.family_group_label("live_proof_discipline") == "Governance / Release Integrity"


def test_mode_summary_aggregates_proof_discipline_metrics() -> None:
    summary = runner._mode_summary(  # noqa: SLF001
        mode="odylith_on",
        scenario_rows=[
            {
                "kind": "packet",
                "scenario_family": "live_proof_discipline",
                "latency_ms": 8.0,
                "effective_estimated_tokens": 80,
                "packet": {
                    "within_budget": True,
                    "route_ready": False,
                    "proof_state_present": True,
                    "proof_status": "live_verified",
                    "proof_first_failing_phase": "status synthesis",
                    "proof_frontier_phase": "status synthesis",
                    "claim_guard_highest_truthful_claim": "fixed live",
                    "claim_guard_hosted_frontier_advanced": True,
                    "claim_guard_same_fingerprint_as_last_falsification": False,
                    "proof_same_fingerprint_reopened": False,
                },
                "expectation_ok": True,
                "orchestration": {"odylith_adoption": {}},
            },
            {
                "kind": "packet",
                "scenario_family": "live_proof_discipline",
                "latency_ms": 9.0,
                "effective_estimated_tokens": 75,
                "packet": {
                    "within_budget": True,
                    "route_ready": False,
                    "proof_state_present": False,
                    "proof_resolution_state": "none",
                },
                "expectation_ok": True,
                "orchestration": {"odylith_adoption": {}},
            },
        ],
    )

    assert summary["proof_discipline_backed_scenario_count"] == 2
    assert summary["proof_state_backed_scenario_count"] == 1
    assert summary["proof_state_present_rate"] == 0.5
    assert summary["false_clearance_rate"] == 0.0
    assert summary["proof_frontier_gate_accuracy_rate"] == 1.0
    assert summary["proof_claim_guard_accuracy_rate"] == 1.0


def test_summary_comparison_includes_proof_discipline_deltas() -> None:
    comparison = runner._summary_comparison(  # noqa: SLF001
        candidate_mode="odylith_on",
        baseline_mode="raw_agent_baseline",
        mode_summaries={
            "odylith_on": {
                "proof_state_present_rate": 1.0,
                "false_clearance_rate": 0.0,
                "proof_frontier_gate_accuracy_rate": 1.0,
                "proof_claim_guard_accuracy_rate": 1.0,
                "proof_same_fingerprint_reuse_rate": 1.0,
            },
            "raw_agent_baseline": {
                "proof_state_present_rate": 0.0,
                "false_clearance_rate": 0.5,
                "proof_frontier_gate_accuracy_rate": 0.0,
                "proof_claim_guard_accuracy_rate": 0.0,
                "proof_same_fingerprint_reuse_rate": 0.0,
            },
        },
    )

    assert comparison["proof_state_present_rate_delta"] == 1.0
    assert comparison["false_clearance_rate_delta"] == -0.5
    assert comparison["proof_frontier_gate_accuracy_delta"] == 1.0
    assert comparison["proof_claim_guard_accuracy_delta"] == 1.0
    assert comparison["proof_same_fingerprint_reuse_delta"] == 1.0


def test_acceptance_holds_on_false_live_clearance_claims() -> None:
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
                "proof_discipline_backed_scenario_count": 1,
                "proof_state_backed_scenario_count": 1,
                "proof_same_fingerprint_backed_scenario_count": 1,
                "proof_state_present_rate": 1.0,
                "false_clearance_rate": 1.0,
                "proof_frontier_gate_accuracy_rate": 0.0,
                "proof_claim_guard_accuracy_rate": 0.0,
                "proof_same_fingerprint_reuse_rate": 0.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "proof_discipline_backed_scenario_count": 1,
                "proof_state_backed_scenario_count": 1,
                "proof_same_fingerprint_backed_scenario_count": 1,
                "proof_state_present_rate": 0.0,
                "false_clearance_rate": 0.0,
                "proof_frontier_gate_accuracy_rate": 1.0,
                "proof_claim_guard_accuracy_rate": 1.0,
                "proof_same_fingerprint_reuse_rate": 1.0,
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
            "proof_state_present_rate_delta": 1.0,
            "false_clearance_rate_delta": 1.0,
            "proof_frontier_gate_accuracy_delta": -1.0,
            "proof_claim_guard_accuracy_delta": -1.0,
            "proof_same_fingerprint_reuse_delta": -1.0,
        },
        family_summaries={
            "live_proof_discipline": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "odylith_packet_present_rate": 1.0,
                    "proof_state_backed_scenario_count": 1,
                    "proof_same_fingerprint_backed_scenario_count": 1,
                    "false_clearance_rate": 1.0,
                    "proof_frontier_gate_accuracy_rate": 0.0,
                    "proof_claim_guard_accuracy_rate": 0.0,
                    "proof_same_fingerprint_reuse_rate": 0.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "false_clearance_rate": 0.0,
                    "proof_frontier_gate_accuracy_rate": 1.0,
                    "proof_claim_guard_accuracy_rate": 1.0,
                    "proof_same_fingerprint_reuse_rate": 1.0,
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
    assert acceptance["checks"]["proof_false_clearance_healthy"] is False
    assert acceptance["checks"]["proof_frontier_gate_accurate"] is False
    assert acceptance["checks"]["proof_claim_guard_accurate"] is False
    assert acceptance["checks"]["proof_same_fingerprint_reuse_accurate"] is False
    assert "live_proof_discipline" in acceptance["weak_families"]


def test_live_proof_family_packet_exposes_real_repo_proof_state() -> None:
    scenario = {
        "scenario_id": "probe-live-proof",
        "family": "live_proof_discipline",
        "changed_paths": [
            "src/odylith/runtime/governance/proof_state/contract.py",
            "odylith/registry/source/components/proof-state/CURRENT_SPEC.md",
            "odylith/casebook/bugs/2026-04-08-live-proof-lanes-do-not-pin-the-primary-blocker-frontier-or-falsification-memory.md",
        ],
        "workstream": "B-062",
        "component": "proof-state",
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

    assert packet_source == "governance_slice"
    assert summary["proof_state_present"] is True
    assert summary["proof_resolution_state"] == "resolved"
    assert summary["proof_lane_id"] == "proof-state-control-plane"
    assert summary["proof_status"] == "live_verified"
    assert summary["claim_guard_highest_truthful_claim"] == "fixed live"
    assert summary["claim_guard_hosted_frontier_advanced"] is True
