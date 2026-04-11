from __future__ import annotations

from odylith.runtime.execution_engine import contradictions
from odylith.runtime.execution_engine import frontier
from odylith.runtime.execution_engine import policy
from odylith.runtime.execution_engine import receipts
from odylith.runtime.execution_engine import resource_closure
from odylith.runtime.execution_engine import runtime_lane_policy
from odylith.runtime.execution_engine import runtime_surface_governance
from odylith.runtime.execution_engine import validation
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ExecutionEvent
from odylith.runtime.execution_engine.contract import detect_execution_host_profile


def _contract(
    *,
    execution_mode: str = "implement",
    host_family: str = "codex_cli",
    model_name: str = "",
) -> ExecutionContract:
    return ExecutionContract.create(
        objective="Deploy authoritative lane rollout",
        authoritative_lane="authoritative_lane",
        target_scope=["cell-01"],
        environment="prod",
        resource_set=["cell-01", "deploy-group-a"],
        success_criteria=["deploy cell-01", "verify rollout"],
        validation_plan=["status", "verification"],
        allowed_moves=["verify_current_frontier", "deploy_cell", "re_anchor"],
        forbidden_moves=["delete_live_scope"],
        external_dependencies=["github_actions"],
        critical_path=["submit", "status", "verification"],
        host_profile=detect_execution_host_profile(host_family, model_name=model_name),
        execution_mode=execution_mode,
    )


def test_promote_user_correction_preserves_detected_host_profile_and_denies_forbidden_move() -> None:
    contract = _contract(model_name="gpt-5.4-mini")

    corrected = policy.promote_user_correction(
        contract,
        constraint_id="HC-1",
        label="Do not use fixture lane",
        forbidden_moves=["deploy_fixture"],
    )
    decision = policy.evaluate_admissibility(corrected, "deploy_fixture")

    assert corrected.host_profile is not None
    assert corrected.host_profile.host_family == "codex"
    assert corrected.host_profile.model_name == "gpt-5.4-mini"
    assert corrected.hard_constraints[0].constraint_id == "HC-1"
    assert decision.outcome == "deny"
    assert "hard_constraint:HC-1" in decision.violated_preconditions


def test_detect_execution_host_profile_reflects_host_capabilities() -> None:
    codex = detect_execution_host_profile("codex_cli", model_name="gpt-5.4")
    claude = detect_execution_host_profile("claude_code", model_name="claude-sonnet")

    assert codex.host_family == "codex"
    assert codex.supports_native_spawn is True
    assert "native_spawn_available" in codex.execution_hints
    assert claude.host_family == "claude"
    assert claude.delegation_style == "task_tool_subagents"
    assert claude.supports_native_spawn is True
    assert "prefer_task_tool_subagents_for_bounded_delegation" in claude.execution_hints


def test_detect_execution_host_profile_does_not_backfill_vendor_model_identity() -> None:
    codex = detect_execution_host_profile("codex_cli")
    claude = detect_execution_host_profile("claude_code")

    assert codex.model_name == ""
    assert codex.model_family == ""
    assert claude.model_name == ""
    assert claude.model_family == ""


def test_evaluate_admissibility_denies_verify_mode_side_exploration_and_requires_reanchor() -> None:
    contract = _contract(execution_mode="verify")

    decision = policy.evaluate_admissibility(
        contract,
        "search_logs",
        denial_count=2,
    )

    assert decision.outcome == "deny"
    assert "mode_budget:verify" in decision.violated_preconditions
    assert decision.nearest_admissible_alternative == "verify_current_frontier"
    assert decision.requires_reanchor is True


def test_derive_execution_frontier_tracks_last_success_blocker_and_resume_handles() -> None:
    external_state = receipts.normalize_external_dependency_state(
        source="github_actions",
        raw_status="running",
        external_id="gha-123",
        detail="build in progress",
    )
    receipt = receipts.emit_semantic_receipt(
        action="deploy_cell",
        scope_fingerprint="cell-01",
        external_state=external_state,
        expected_next_states=["building", "succeeded"],
    )

    result = frontier.derive_execution_frontier(
        [
            ExecutionEvent(event_id="evt-1", event_type="phase", phase="submit", successful=True),
            ExecutionEvent(
                event_id="evt-2",
                event_type="handoff",
                phase="verify",
                blocker="waiting on CI",
                next_move="poll:gha-123",
                execution_mode="verify",
                external_state=external_state,
                receipt=receipt,
            ),
        ]
    )

    assert result.current_phase == "verify"
    assert result.last_successful_phase == "submit"
    assert result.active_blocker == "waiting on CI"
    assert result.truthful_next_move == "poll:gha-123"
    assert result.in_flight_external_ids == ("gha-123",)
    assert result.resume_handles[0].resume_token == "resume:cell-01"
    assert result.execution_mode == "verify"


def test_resource_closure_receipts_validation_and_contradictions_cover_execution_failure_modes() -> None:
    closure = resource_closure.classify_resource_closure(
        ["cell-01"],
        dependency_graph={"cell-01": ["deploy-group-a"]},
        destructive_groups=[("cell-01", "cell-02")],
    )
    safe_closure = resource_closure.classify_resource_closure(
        ["deploy-group-a", "cell-01"],
        dependency_graph={"cell-01": ["deploy-group-a"]},
    )
    contract = _contract(host_family="unsupported")
    deploy_decision = policy.evaluate_admissibility(contract, "delegate_verification")
    matrix = validation.synthesize_validation_matrix(contract)
    contradiction_rows = contradictions.detect_contradictions(
        contract,
        intended_action="deploy local fixture",
        user_instructions=["do not use fixture", "only use authoritative lane"],
        live_state=["blocked on token refresh"],
    )

    assert closure.classification == "destructive"
    assert closure.destructive_overlap == ("cell-01",)
    assert safe_closure.classification == "safe"
    assert deploy_decision.outcome == "deny"
    assert "host_capability:native_spawn" in deploy_decision.violated_preconditions
    assert matrix.archetype == "deploy"
    assert matrix.checks == ("submit", "progress", "status", "verification", "logs", "recovery")
    assert any(row.blocks_execution for row in contradiction_rows)
    assert any("local fixture" in row.conflicting_evidence for row in contradiction_rows)


def test_runtime_lane_policy_blocks_wait_state_and_unknown_host_parallelism() -> None:
    wait_guard = runtime_lane_policy.delegation_guard(
        {
            "execution_governance_present": True,
            "execution_governance_wait_status": "building",
            "execution_governance_wait_detail": "deploying cell-01",
        }
    )
    unknown_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_governance_present": True,
            "execution_governance_host_family": "unknown",
            "execution_governance_host_supports_native_spawn": False,
        }
    )
    claude_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_governance_present": True,
            "execution_governance_host_family": "claude",
            "execution_governance_host_supports_native_spawn": True,
        }
    )

    assert wait_guard.blocked is True
    assert "resume the active external dependency" in wait_guard.reason
    assert unknown_guard.blocked is True
    assert "detected host" in unknown_guard.reason
    assert claude_guard.blocked is False


def test_execution_governance_snapshot_carries_turn_target_and_presentation_policy() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_governance_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet_state": "compact",
            "changed_paths": ["odylith/compass/compass.html"],
            "session": {
                "session_id": "sess-1",
                "workstream": "B-082",
                "turn_context": {
                    "intent": "Move the current release label next to 0.1.11 title",
                    "surfaces": ["compass"],
                    "active_tab": "releases",
                    "user_turn_id": "turn-2",
                    "supersedes_turn_id": "turn-1",
                },
            },
            "turn_context": {
                "intent": "Move the current release label next to 0.1.11 title",
                "surfaces": ["compass"],
                "active_tab": "releases",
                "user_turn_id": "turn-2",
                "supersedes_turn_id": "turn-1",
            },
            "target_resolution": {
                "lane": "consumer",
                "candidate_targets": [
                    {
                        "path": "odylith/compass/compass.html",
                        "source": "path_scope",
                        "writable": False,
                    }
                ],
                "diagnostic_anchors": [
                    {
                        "kind": "workstream",
                        "value": "B-073",
                        "label": "Task Contract, Event Ledger, and Hard-Constraint Promotion",
                    }
                ],
                "has_writable_targets": False,
                "requires_more_consumer_context": True,
                "consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
            },
            "presentation_policy": {
                "commentary_mode": "task_first_minimal",
                "suppress_routing_receipts": True,
                "surface_fast_lane": True,
            },
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "packet_state": "compact",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        }
    )

    contract = snapshot["contract"]
    assert contract["turn_context"]["supersedes_turn_id"] == "turn-1"
    assert contract["target_resolution"]["lane"] == "consumer"
    assert contract["presentation_policy"]["commentary_mode"] == "task_first_minimal"

    summary = runtime_surface_governance.summary_fields_from_execution_governance(snapshot)

    assert summary["execution_governance_target_lane"] == "consumer"
    assert summary["execution_governance_has_writable_targets"] is False
    assert summary["execution_governance_requires_more_consumer_context"] is True
    assert summary["execution_governance_consumer_failover"] == "maintainer_ready_feedback_plus_bounded_narrowing"
    assert summary["execution_governance_commentary_mode"] == "task_first_minimal"
    assert summary["execution_governance_suppress_routing_receipts"] is True
    assert summary["execution_governance_surface_fast_lane"] is True


def test_runtime_lane_policy_blocks_consumer_lane_without_writable_targets() -> None:
    guard = runtime_lane_policy.delegation_guard(
        {
            "execution_governance_present": True,
            "execution_governance_target_lane": "consumer",
            "execution_governance_has_writable_targets": False,
            "execution_governance_requires_more_consumer_context": True,
            "execution_governance_consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
        }
    )

    assert guard.blocked is True
    assert guard.code == "execution-governance-consumer-fence"
    assert "does not yet have writable consumer targets" in guard.reason
