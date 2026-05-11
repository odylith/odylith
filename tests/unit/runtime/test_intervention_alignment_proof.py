from __future__ import annotations

from odylith.runtime.intervention_engine import alignment_proof


def _lanes(proof: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(row["lane_id"]): dict(row)
        for row in proof["lanes"]  # type: ignore[index]
        if isinstance(row, dict)
    }


def test_visibility_recovery_alignment_proof_covers_required_engine_lanes() -> None:
    proof = alignment_proof.build_alignment_proof(
        host_family="codex",
        turn_phase="prompt_submit",
        visibility_failure=True,
        context_packet={
            "packet_state": "visibility_recovery",
            "packet_kind": "governance_slice",
            "component_id": "governance-intervention-engine",
            "components": ["governance-intervention-engine", "execution-engine", "domain-intelligence"],
            "workstreams": ["B-096", "B-142"],
            "route": {"route_ready": True, "native_spawn_ready": False},
            "runtime_surface_summary": {
                "status": "ready",
                "latest_packet_state": "visibility_recovery",
            },
            "discipline_summary": {
                "status": "ready",
                "validation_status": "passed",
            },
            "guidance_behavior_summary": {
                "status": "ready",
                "validation_status": "passed",
            },
            "topology_integrity": {"quality": "pass"},
        },
        execution_engine_summary={
            "execution_engine_present": True,
            "execution_engine_next_move": "recover.current_blocker",
            "execution_engine_outcome": "admit",
            "execution_engine_mode": "recover",
            "execution_engine_host_supports_native_spawn": True,
            "execution_engine_host_execution_hints": [
                "native_spawn_transport_available",
                "native_spawn_policy:host_policy_gated",
            ],
        },
        memory_summary={
            "visibility_complaint": True,
            "host_family": "codex",
            "session_id": "proof-session",
        },
        tribunal_summary={
            "source": "intervention_alignment_context",
            "case_queue": [{"id": "CB-122"}],
            "scope_signals": [{"scope_id": "B-096"}],
            "systemic_brief": {"headline": "Odylith must be seen before it counts."},
        },
        visibility_summary={"chat_visible_proof": "unproven_this_session"},
        delivery_snapshot={"event_count": 0, "visible_event_count": 0},
        workstreams=["B-096"],
        components=["governance-intervention-engine", "odylith-context-engine", "domain-intelligence"],
        bugs=["CB-122"],
        diagrams=["D-038"],
    )
    lanes = _lanes(proof)

    assert proof["status"] == "ready"
    assert proof["missing_required_lanes"] == []
    assert proof["hot_path_constraints"] == {
        "local_summaries_only": True,
        "provider_calls": False,
        "repo_scan": False,
    }
    assert lanes["context_engine"]["status"] == "covered"
    assert lanes["execution_engine"]["status"] == "covered"
    assert lanes["intervention_engine"]["status"] == "covered"
    assert lanes["tribunal"]["status"] == "covered"
    assert lanes["governance_engine"]["status"] == "covered"
    assert lanes["delivery_intelligence"]["status"] == "covered"
    assert lanes["memory_substrate"]["status"] == "covered"
    assert lanes["subagent_router"]["status"] == "policy_deferred"
    assert lanes["subagent_router"]["satisfied"] is True
    assert lanes["subagent_orchestrator"]["status"] == "policy_deferred"
    assert lanes["subagent_orchestrator"]["satisfied"] is True
    assert lanes["discipline_engine"]["status"] == "covered"
    assert lanes["surface_dags"]["status"] == "covered"
    assert lanes["analysis_engine"]["status"] == "covered"
    assert lanes["topology_integrity"]["status"] == "covered"
    assert lanes["taxonomies_fsms"]["status"] == "covered"
    assert lanes["domain_intelligence"]["status"] == "covered"
    assert lanes["operator_experience"]["status"] == "covered"
    assert lanes["proof_state"]["status"] == "policy_deferred"
    assert lanes["turn_gate"]["status"] == "policy_deferred"
    assert lanes["benchmark_harness"]["status"] == "policy_deferred"
    assert lanes["install_upgrade_migration_runtime"]["status"] == "policy_deferred"
    assert lanes["security_trust"]["status"] == "policy_deferred"
    assert proof["lane_count"] == 22
    assert set(lanes) == {
        "analysis_engine",
        "domain_intelligence",
        "delivery_intelligence",
        "context_engine",
        "reasoning_engine",
        "execution_engine",
        "proof_state",
        "intervention_engine",
        "tribunal",
        "surface_dags",
        "topology_integrity",
        "governance_engine",
        "turn_gate",
        "memory_substrate",
        "subagent_router",
        "subagent_orchestrator",
        "discipline_engine",
        "benchmark_harness",
        "taxonomies_fsms",
        "install_upgrade_migration_runtime",
        "security_trust",
        "operator_experience",
    }


def test_visibility_recovery_alignment_proof_degrades_when_required_lane_is_missing() -> None:
    proof = alignment_proof.build_alignment_proof(
        host_family="codex",
        turn_phase="prompt_submit",
        visibility_failure=True,
        context_packet={
            "packet_state": "visibility_recovery",
            "packet_kind": "governance_slice",
            "component_id": "governance-intervention-engine",
        },
        execution_engine_summary={"execution_engine_present": True},
        visibility_summary={"chat_visible_proof": "unproven_this_session"},
    )

    assert proof["status"] == "degraded"
    assert set(proof["missing_required_lanes"]) == {
        "memory_substrate",
        "subagent_router",
        "subagent_orchestrator",
        "tribunal",
        "governance_engine",
    }


def test_quiet_alignment_proof_does_not_claim_optional_lanes_without_evidence() -> None:
    proof = alignment_proof.build_alignment_proof(
        host_family="claude",
        turn_phase="post_edit_checkpoint",
        visibility_failure=False,
        context_packet={
            "packet_state": "observing",
            "packet_kind": "host_intervention_context",
            "component_id": "governance-intervention-engine",
        },
        execution_engine_summary={
            "execution_engine_present": True,
            "execution_engine_next_move": "implement.target_scope",
        },
        memory_summary={"host_family": "claude", "session_id": "quiet-session"},
        visibility_summary={"chat_visible_proof": "unproven_this_session"},
        delivery_snapshot={"event_count": 0},
    )
    lanes = _lanes(proof)

    assert proof["status"] == "quiet"
    assert proof["missing_required_lanes"] == []
    assert lanes["tribunal"]["status"] == "quiet"
    assert lanes["governance_engine"]["status"] == "quiet"
    assert lanes["subagent_router"]["required"] is False
    assert lanes["subagent_orchestrator"]["required"] is False
    assert lanes["surface_dags"]["status"] == "quiet"
    assert lanes["analysis_engine"]["status"] == "quiet"
    assert lanes["topology_integrity"]["status"] == "quiet"
    assert lanes["taxonomies_fsms"]["status"] == "quiet"
    assert lanes["domain_intelligence"]["status"] == "quiet"
    assert lanes["operator_experience"]["status"] == "covered"
