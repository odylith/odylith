from __future__ import annotations

from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import odylith_context_engine_hot_path_packet_finalize_runtime as hot_path_packet

hot_path_packet.bind(store.__dict__)


def test_compact_hot_path_runtime_packet_preserves_proof_state_metadata() -> None:
    compact = hot_path_packet._compact_hot_path_runtime_packet(  # noqa: SLF001
        packet_kind="governance_slice",
        payload={
            "context_packet_state": "compact",
            "context_packet": {
                "packet_state": "compact",
                "route": {},
                "packet_quality": {"i": "analysis"},
            },
            "proof_state": {
                "lane_id": "proof-state-control-plane",
                "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                "first_failing_phase": "manifests-deploy",
                "frontier_phase": "status synthesis",
                "clearance_condition": "hosted SIM3 passes beyond manifests-deploy",
                "proof_status": "live_verified",
                "linked_bug_id": "CB-077",
            },
            "proof_state_resolution": {
                "state": "resolved",
                "lane_ids": ["proof-state-control-plane"],
            },
            "claim_guard": {
                "highest_truthful_claim": "fixed live",
                "hosted_frontier_advanced": True,
                "claim_scope": "live",
                "blocked_terms": [],
            },
        },
    )

    assert compact["proof_state"]["lane_id"] == "proof-state-control-plane"
    assert compact["proof_state_resolution"]["state"] == "resolved"
    assert compact["claim_guard"]["highest_truthful_claim"] == "fixed live"
    assert compact["context_packet"]["execution_governance"]["present"] is True
    assert compact["context_packet"]["execution_governance"]["mode"] == "recover"
    assert compact["context_packet"]["execution_governance"]["next_move"] == "recover.current_blocker"


def test_packet_summary_from_compact_payload_exposes_proof_state_fields() -> None:
    summary = store._packet_summary_from_bootstrap_payload(  # noqa: SLF001
        {
            "context_packet_state": "compact",
            "context_packet": {
                "packet_state": "compact",
                "route": {},
                "packet_quality": {"i": "analysis"},
            },
            "proof_state": {
                "lane_id": "proof-state-control-plane",
                "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                "failure_fingerprint": "aws:lambda:Permission doesn't support update",
                "first_failing_phase": "manifests-deploy",
                "frontier_phase": "status synthesis",
                "clearance_condition": "hosted SIM3 passes beyond manifests-deploy",
                "proof_status": "live_verified",
                "linked_bug_id": "CB-077",
            },
            "proof_state_resolution": {
                "state": "resolved",
                "lane_ids": ["proof-state-control-plane"],
            },
            "claim_guard": {
                "highest_truthful_claim": "fixed live",
                "hosted_frontier_advanced": True,
                "same_fingerprint_as_last_falsification": False,
                "claim_scope": "live",
                "gate": {"state": "allow_unqualified_resolution_terms"},
            },
        }
    )

    assert summary["proof_state_present"] is True
    assert summary["proof_resolution_state"] == "resolved"
    assert summary["proof_lane_id"] == "proof-state-control-plane"
    assert summary["proof_status"] == "live_verified"
    assert summary["claim_guard_highest_truthful_claim"] == "fixed live"
    assert summary["claim_guard_hosted_frontier_advanced"] is True
    assert summary["claim_guard_claim_scope"] == "live"
    assert summary["claim_guard_gate_state"] == "allow_unqualified_resolution_terms"
    assert summary["execution_governance_present"] is True
    assert summary["execution_governance_outcome"] == "admit"
    assert summary["execution_governance_mode"] == "recover"
    assert summary["execution_governance_next_move"] == "recover.current_blocker"
    assert summary["execution_governance_blocker"] == "Lambda permission lifecycle on ecs-drift-monitor invoke"
    assert summary["execution_governance_validation_archetype"] == "recover"


def test_packet_expectations_support_proof_state_contract_fields() -> None:
    matched, details = store._packet_satisfies_evaluation_expectations(  # noqa: SLF001
        {
            "packet_state": "compact",
            "within_budget": True,
            "proof_state_present": True,
            "proof_resolution_state": "resolved",
            "proof_status": "live_verified",
            "proof_frontier_phase": "status synthesis",
            "proof_first_failing_phase": "status synthesis",
            "claim_guard_highest_truthful_claim": "fixed live",
            "claim_guard_hosted_frontier_advanced": True,
            "claim_guard_claim_scope": "live",
            "proof_same_fingerprint_reopened": False,
        },
        {
            "packet_state": ["compact"],
            "within_budget": True,
            "proof_state_present": True,
            "proof_resolution_state": ["resolved"],
            "proof_status": ["live_verified"],
            "proof_frontier_phase": ["status synthesis"],
            "proof_first_failing_phase": ["status synthesis"],
            "claim_guard_highest_truthful_claim": ["fixed live"],
            "claim_guard_hosted_frontier_advanced": True,
            "claim_guard_claim_scope": ["live"],
            "proof_same_fingerprint_reopened": False,
        },
    )

    assert matched is True
    assert details["observed_proof_status"] == "live_verified"
    assert details["observed_claim_guard_highest_truthful_claim"] == "fixed live"
