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
    assert lanes["governance"]["status"] == "covered"
    assert lanes["delivery"]["status"] == "covered"
    assert lanes["memory_substrate"]["status"] == "covered"
    assert lanes["subagent_orchestration"]["status"] == "policy_deferred"
    assert lanes["subagent_orchestration"]["satisfied"] is True
    assert lanes["discipline"]["status"] == "covered"
    assert lanes["surface_dags"]["status"] == "covered"
    assert lanes["analysis"]["status"] == "covered"
    assert lanes["topology"]["status"] == "covered"
    assert lanes["taxonomies_fsms"]["status"] == "covered"
    assert lanes["greenfield_domain_intelligence"]["status"] == "covered"
    assert lanes["overall_ux"]["status"] == "covered"
    assert proof["lane_count"] == 15
    assert set(lanes) == {
        "context_engine",
        "execution_engine",
        "intervention_engine",
        "tribunal",
        "governance",
        "subagent_orchestration",
        "discipline",
        "surface_dags",
        "delivery",
        "analysis",
        "memory_substrate",
        "topology",
        "taxonomies_fsms",
        "greenfield_domain_intelligence",
        "overall_ux",
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
        "governance",
        "memory_substrate",
        "subagent_orchestration",
        "tribunal",
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
    assert lanes["governance"]["status"] == "quiet"
    assert lanes["subagent_orchestration"]["required"] is False
    assert lanes["surface_dags"]["status"] == "quiet"
    assert lanes["analysis"]["status"] == "quiet"
    assert lanes["topology"]["status"] == "quiet"
    assert lanes["taxonomies_fsms"]["status"] == "quiet"
    assert lanes["greenfield_domain_intelligence"]["status"] == "quiet"
    assert lanes["overall_ux"]["status"] == "covered"
