from __future__ import annotations

from pathlib import Path

from odylith.runtime.execution_engine import contradictions
from odylith.runtime.execution_engine import frontier
from odylith.runtime.execution_engine import policy
from odylith.runtime.execution_engine import receipts
from odylith.runtime.execution_engine import resource_closure
from odylith.runtime.execution_engine import runtime_lane_policy
from odylith.runtime.execution_engine import runtime_surface_governance
from odylith.runtime.execution_engine import validation
from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ExecutionEvent
from odylith.runtime.execution_engine.contract import detect_execution_host_profile
from odylith.runtime.governance import sync_session


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
            "execution_engine_present": True,
            "execution_engine_wait_status": "building",
            "execution_engine_wait_detail": "deploying cell-01",
        }
    )
    unknown_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "unknown",
            "execution_engine_host_supports_native_spawn": False,
        }
    )
    claude_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "claude",
            "execution_engine_host_supports_native_spawn": True,
        }
    )

    assert wait_guard.blocked is True
    assert "resume the active external dependency" in wait_guard.reason
    assert unknown_guard.blocked is True
    assert "detected host" in unknown_guard.reason
    assert claude_guard.blocked is False


def test_runtime_lane_policy_blocks_invalidated_or_history_pressured_slices() -> None:
    invalidated_guard = runtime_lane_policy.delegation_guard(
        {
            "execution_engine_present": True,
            "execution_engine_runtime_invalidated_by_step": "render_compass_dashboard",
        }
    )
    history_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_engine_present": True,
            "execution_engine_history_rule_hits": [
                "user_correction_requires_promotion",
            ],
            "execution_engine_pressure_signals": ["denials:2"],
        }
    )
    deny_guard = runtime_lane_policy.delegation_guard(
        {
            "execution_engine_present": True,
            "execution_engine_outcome": "deny",
            "execution_engine_next_move": "verify.selected_matrix",
            "execution_engine_nearby_denial_actions": [
                "explore.broad_reset",
            ],
        }
    )

    assert invalidated_guard.blocked is True
    assert "render_compass_dashboard" in invalidated_guard.reason
    assert history_guard.blocked is True
    assert "hard user constraints" in history_guard.reason
    assert deny_guard.blocked is True
    assert "explore.broad_reset" in deny_guard.reason


def test_execution_engine_snapshot_carries_turn_target_and_presentation_policy() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
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

    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)

    assert summary["execution_engine_target_lane"] == "consumer"
    assert summary["execution_engine_has_writable_targets"] is False
    assert summary["execution_engine_requires_more_consumer_context"] is True
    assert summary["execution_engine_consumer_failover"] == "maintainer_ready_feedback_plus_bounded_narrowing"
    assert summary["execution_engine_commentary_mode"] == "task_first_minimal"
    assert summary["execution_engine_suppress_routing_receipts"] is True
    assert summary["execution_engine_surface_fast_lane"] is True


def test_execution_engine_snapshot_treats_guidance_behavior_validator_as_validation_command() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "governance_slice",
            "guidance_behavior_summary": {
                "family": "guidance_behavior",
                "status": "available",
                "validation_status": "not_run",
                "validator_command": (
                    "odylith validate guidance-behavior --repo-root ."
                ),
            },
            "context_packet": {
                "packet_kind": "governance_slice",
                "route": {"route_ready": True},
            },
        }
    )

    assert "commands" in snapshot["contract"]["validation_plan"]


def test_execution_engine_guidance_behavior_narrowing_snapshot_avoids_host_probe(monkeypatch) -> None:
    def _unexpected_host_probe(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("guidance behavior narrowing snapshots should not probe host capabilities")

    monkeypatch.setattr(runtime_surface_governance, "detect_execution_host_profile", _unexpected_host_probe)

    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "impact",
            "guidance_behavior_summary": {
                "family": "guidance_behavior",
                "status": "available",
                "validator_command": "odylith validate guidance-behavior --repo-root .",
            },
            "context_packet": {
                "packet_kind": "impact",
                "packet_state": "gated_ambiguous",
                "route": {"route_ready": False, "narrowing_required": True},
            },
        }
    )

    assert snapshot["contract"]["host_profile"]["host_family"] == "unknown"
    assert snapshot["contract"]["host_profile"]["supports_native_spawn"] is False
    assert "commands" in snapshot["contract"]["validation_plan"]


def test_runtime_lane_policy_blocks_consumer_lane_without_writable_targets() -> None:
    guard = runtime_lane_policy.delegation_guard(
        {
            "execution_engine_present": True,
            "execution_engine_target_lane": "consumer",
            "execution_engine_has_writable_targets": False,
            "execution_engine_requires_more_consumer_context": True,
            "execution_engine_consumer_failover": "maintainer_ready_feedback_plus_bounded_narrowing",
        }
    )

    assert guard.blocked is True
    assert guard.code == "execution-engine-consumer-fence"
    assert "does not yet have writable consumer targets" in guard.reason


def test_runtime_lane_policy_blocks_noncanonical_identity_even_if_outcome_admits() -> None:
    guard = runtime_lane_policy.delegation_guard(
        {
            "execution_engine_present": True,
            "execution_engine_outcome": "admit",
            "execution_engine_component_id": "execution-engine",
            "execution_engine_canonical_component_id": "execution-engine",
            "execution_engine_identity_status": "blocked_noncanonical_target",
            "execution_engine_target_component_id": "execution-" + "governance",
            "execution_engine_target_component_status": "blocked_noncanonical_execution_engine",
            "execution_engine_snapshot_reuse_status": "fail_closed_identity",
        }
    )

    assert guard.blocked is True
    assert guard.code == "execution-engine-identity"
    assert "noncanonical execution-engine identity" in guard.reason


def test_runtime_lane_policy_identity_guard_blocks_each_malformed_identity_field() -> None:
    base = {
        "execution_engine_present": True,
        "execution_engine_outcome": "admit",
        "execution_engine_mode": "implement",
        "execution_engine_closure": "safe",
        "execution_engine_host_family": "codex",
        "execution_engine_host_supports_native_spawn": True,
    }
    cases = (
        {"execution_engine_component_id": "execution-" + "governance"},
        {"execution_engine_canonical_component_id": "execution-" + "governance"},
        {"execution_engine_identity_status": "blocked_noncanonical_target"},
        {"execution_engine_target_component_id": "execution-" + "governance"},
        {"execution_engine_target_component_status": "blocked_noncanonical_execution_engine"},
        {"execution_engine_snapshot_reuse_status": "fail_closed_identity"},
    )

    for overrides in cases:
        guard = runtime_lane_policy.parallelism_guard({**base, **overrides})
        assert guard.blocked is True, overrides
        assert guard.code == "execution-engine-identity"


def test_context_execution_handshake_carries_stable_shape_without_aliasing() -> None:
    handshake = execution_engine_handshake.normalize_execution_engine_handshake(
        payload={
            "component": "execution-engine",
            "packet_kind": "governance_slice",
            "turn_context": {"intent": "verify", "surfaces": ["compass"]},
            "target_resolution": {
                "lane": "consumer",
                "candidate_targets": [{"path": "src/app.py", "writable": True}],
            },
            "presentation_policy": {"commentary_mode": "task_first"},
            "recommended_commands": ["pytest -q"],
        },
        context_packet={
            "packet_quality": {"rc": "high"},
            "route": {"route_ready": True, "native_spawn_ready": True},
        },
        routing_handoff={"route_ready": True, "native_spawn_ready": True},
    )

    assert handshake["version"] == "v1"
    assert handshake["component_id"] == "execution-engine"
    assert handshake["canonical_component_id"] == "execution-engine"
    assert handshake["identity_status"] == "canonical"
    assert handshake["target_component_id"] == "execution-engine"
    assert handshake["target_component_status"] == "execution_engine"
    assert handshake["packet_kind"] == "governance_slice"
    assert handshake["turn_context"]["intent"] == "verify"
    assert handshake["target_resolution"]["lane"] == "consumer"
    assert handshake["presentation_policy"]["commentary_mode"] == "task_first"
    assert handshake["recommended_validation"]["recommended_commands"] == ["pytest -q"]
    assert handshake["route_readiness"]["route_ready"] is True

    stale = execution_engine_handshake.normalize_execution_engine_handshake(
        payload={"component": "execution-" + "governance", "packet_kind": "governance_slice"},
        context_packet={},
    )
    assert stale["component_id"] == "execution-engine"
    assert stale["canonical_component_id"] == "execution-engine"
    assert stale["identity_status"] == "blocked_noncanonical_target"
    assert stale["target_component_id"] == "execution-" + "governance"
    assert stale["target_component_status"] == "blocked_noncanonical_execution_engine"


def test_context_execution_handshake_reads_related_component_truth() -> None:
    context_packet = {
        "related_entities": {
            "component": [
                {"entity_id": "execution-engine", "title": "Execution Engine"},
                {"entity_id": "odylith", "title": "Odylith"},
            ]
        }
    }
    handshake = execution_engine_handshake.normalize_execution_engine_handshake(
        payload={"packet_kind": "context_dossier"},
        context_packet=context_packet,
    )
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={"packet_kind": "context_dossier"},
        context_packet=context_packet,
        host_candidates=("codex",),
    )

    assert handshake["target_component_id"] == "execution-engine"
    assert handshake["target_component_ids"] == ["execution-engine", "odylith"]
    assert handshake["target_component_status"] == "execution_engine_plus_related"
    assert compact["target_component_id"] == "execution-engine"
    assert compact["target_component_ids"] == ["execution-engine", "odylith"]
    assert compact["target_component_status"] == "execution_engine_plus_related"


def test_context_execution_handshake_fail_closes_nested_historical_identity() -> None:
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={
            "target_resolution": {
                "lane": "consumer",
                "candidate_targets": [
                    {
                        "path": "src/odylith/runtime/execution_engine/policy.py",
                        "component_id": "execution-" + "governance",
                    }
                ],
            }
        },
        context_packet={"route": {"route_ready": True, "native_spawn_ready": True}},
    )

    assert compact["outcome"] == "deny"
    assert compact["identity_status"] == "blocked_noncanonical_target"
    assert compact["target_component_id"] == "execution-" + "governance"
    assert compact["target_component_status"] == "blocked_noncanonical_execution_engine"
    assert compact["snapshot_reuse_status"] == "fail_closed_identity"


def test_context_execution_handshake_fail_closes_diagnostic_anchor_component_values() -> None:
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={
            "target_resolution": {
                "diagnostic_anchors": [
                    {"kind": "component", "value": "execution-" + "governance"},
                    {"kind": "workstream", "value": "B-099"},
                ]
            },
            "execution_engine": {
                "present": True,
                "outcome": "admit",
                "mode": "verify",
                "next_move": "verify.selected_matrix",
            },
        },
        context_packet={"route": {"route_ready": True, "native_spawn_ready": True}},
    )

    assert compact["outcome"] == "deny"
    assert compact["mode"] == "recover"
    assert compact["target_component_id"] == "execution-" + "governance"
    assert compact["identity_status"] == "blocked_noncanonical_target"
    assert compact["snapshot_reuse_status"] == "fail_closed_identity"
    assert compact["snapshot_duration_ms"] == 0.0


def test_context_execution_handshake_does_not_treat_workstream_entities_as_components() -> None:
    handshake = execution_engine_handshake.normalize_execution_engine_handshake(
        payload={
            "entity_id": "B-099",
            "packet_kind": "context_dossier",
            "target_resolution": {
                "diagnostic_anchors": [
                    {"kind": "workstream", "value": "B-099"},
                    {"kind": "release", "value": "release-0-1-11"},
                ]
            },
        },
        context_packet={
            "related_entities": {
                "plan": [{"entity_id": "odylith/technical-plans/in-progress/x.md"}],
                "release": [{"entity_id": "release-0-1-11"}],
            }
        },
    )

    assert handshake["target_component_id"] == ""
    assert handshake["target_component_ids"] == []
    assert handshake["target_component_status"] == "missing"
    assert handshake["identity_status"] == "canonical"


def test_execution_engine_snapshot_helper_reuses_existing_compact_snapshot() -> None:
    existing = {
        "present": True,
        "outcome": "admit",
        "mode": "verify",
        "next_move": "verify.selected_matrix",
    }

    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={},
        context_packet={"execution_engine": existing},
    )

    assert compact["outcome"] == "admit"
    assert compact["snapshot_reuse_status"] == "reused_context_packet_snapshot"
    assert compact["handshake_version"] == "v1"
    assert compact["snapshot_estimated_tokens"] > 0


def test_execution_engine_snapshot_helper_compacts_reused_full_snapshot() -> None:
    full_snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "component": "execution-engine",
            "packet_kind": "governance_slice",
            "context_packet_state": "compact",
            "changed_paths": ["src/odylith/runtime/execution_engine/policy.py"],
            "context_packet": {
                "packet_kind": "governance_slice",
                "packet_state": "compact",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
        },
        host_candidates=["codex_cli"],
    )

    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={"component": "execution-engine"},
        context_packet={"execution_engine": full_snapshot},
    )

    assert "contract" not in compact
    assert compact["present"] is True
    assert compact["host_family"] == "codex"
    assert compact["snapshot_reuse_status"] == "reused_context_packet_snapshot"
    assert compact["runtime_contract_estimated_tokens"] > 0


def test_execution_engine_snapshot_helper_exposes_cost_metrics() -> None:
    compact = execution_engine_handshake.compact_execution_engine_snapshot_for_packet(
        payload={
            "component": "execution-engine",
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["codex_cli"],
        reuse_existing=False,
    )

    assert compact["snapshot_reuse_status"] == "built"
    assert compact["snapshot_duration_ms"] >= 0.0
    assert compact["snapshot_estimated_tokens"] > 0
    assert compact["runtime_contract_estimated_tokens"] > 0
    assert compact["handshake_estimated_tokens"] > 0

    summary = runtime_surface_governance.summary_fields_from_execution_engine(compact)
    assert summary["execution_engine_snapshot_duration_ms"] >= 0.0
    assert summary["execution_engine_snapshot_estimated_tokens"] > 0
    assert summary["execution_engine_runtime_contract_estimated_tokens"] > 0
    assert summary["execution_engine_snapshot_reuse_status"] == "built"


def test_codex_and_claude_snapshots_keep_same_policy_semantics() -> None:
    payload = {
        "packet_kind": "governance_slice",
        "context_packet_state": "compact",
        "changed_paths": ["src/odylith/runtime/execution_engine/policy.py"],
        "component": "execution-engine",
        "recommended_tests": [{"path": "tests/unit/runtime/test_execution_engine.py"}],
        "context_packet": {
            "packet_kind": "governance_slice",
            "packet_state": "compact",
            "route": {"route_ready": True, "native_spawn_ready": True},
        },
        "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
    }

    codex = runtime_surface_governance.summary_fields_from_execution_engine(
        runtime_surface_governance.build_packet_execution_engine_snapshot(
            payload,
            host_candidates=["codex_cli"],
        )
    )
    claude = runtime_surface_governance.summary_fields_from_execution_engine(
        runtime_surface_governance.build_packet_execution_engine_snapshot(
            payload,
            host_candidates=["claude_code"],
        )
    )

    semantic_keys = (
        "execution_engine_outcome",
        "execution_engine_mode",
        "execution_engine_next_move",
        "execution_engine_closure",
        "execution_engine_validation_archetype",
        "execution_engine_authoritative_lane",
        "execution_engine_requires_reanchor",
    )
    for key in semantic_keys:
        assert claude[key] == codex[key]

    assert codex["execution_engine_host_family"] == "codex"
    assert claude["execution_engine_host_family"] == "claude"
    assert codex["execution_engine_host_delegation_style"] == "routed_spawn"
    assert claude["execution_engine_host_delegation_style"] == "task_tool_subagents"
    assert codex["execution_engine_host_supports_interrupt"] is True
    assert claude["execution_engine_host_supports_interrupt"] is False
    assert codex["execution_engine_host_supports_artifact_paths"] is True
    assert claude["execution_engine_host_supports_artifact_paths"] is False


def test_promote_instruction_constraints_hardens_inline_user_corrections() -> None:
    contract = policy.promote_instruction_constraints(
        _contract(),
        instructions=[
            "do not use fixture",
            "only use authoritative lane",
        ],
    )

    decision = policy.evaluate_admissibility(
        contract,
        "deploy_fixture",
        requested_scope=["fixture"],
    )

    assert len(contract.hard_constraints) == 2
    assert decision.outcome == "deny"
    assert any(item.startswith("hard_constraint:") for item in decision.violated_preconditions)


def test_promote_instruction_constraints_understands_natural_language_variants() -> None:
    contract = policy.promote_instruction_constraints(
        _contract(),
        instructions=[
            "don't use fixture lane",
            "stay on authoritative lane",
            "only touch cell-01",
        ],
    )

    forbidden = policy.evaluate_admissibility(contract, "deploy_fixture")
    wrong_scope = policy.evaluate_admissibility(contract, "deploy_cell", requested_scope=["cell-02"])

    assert len(contract.hard_constraints) == 3
    assert forbidden.outcome == "deny"
    assert wrong_scope.outcome == "deny"
    assert any(item.startswith("required_scope:") for item in wrong_scope.violated_preconditions)


def test_evaluate_admissibility_defers_for_active_external_wait_and_denies_resume_without_receipt() -> None:
    contract = _contract(execution_mode="recover")
    external_state = receipts.normalize_external_dependency_state(
        source="github_actions",
        raw_status="building",
        external_id="gha-999",
        detail="deploying cell-01",
    )

    deferred = policy.evaluate_admissibility(
        contract,
        "implement.target_scope",
        external_state=external_state,
    )
    denied_resume = policy.evaluate_admissibility(
        contract,
        "resume.external_dependency",
        external_state=None,
        receipt=None,
    )

    assert deferred.outcome == "defer"
    assert "wait_status:building" in deferred.violated_preconditions
    assert deferred.nearest_admissible_alternative == "resume.external_dependency"
    assert denied_resume.outcome == "deny"
    assert "resume_handle:missing" in denied_resume.violated_preconditions


def test_evaluate_admissibility_blocks_carried_history_failure_classes() -> None:
    contract = _contract()

    lane_drift = policy.evaluate_admissibility(
        contract,
        "implement.local_fixture",
        history_rule_hits=["lane drift", "CB-104"],
    )
    correction = policy.evaluate_admissibility(
        contract,
        "delegate.parallel_workers",
        history_rule_hits=["user correction decay"],
    )

    assert lane_drift.outcome == "deny"
    assert "history_rule:lane_drift_preflight" in lane_drift.violated_preconditions
    assert correction.outcome == "defer"
    assert "history_rule:user_correction_requires_promotion" in correction.violated_preconditions


def test_resource_closure_infers_generated_surface_domains_and_missing_truth_roots() -> None:
    closure = resource_closure.classify_resource_closure(["odylith/compass/compass.html"])

    assert closure.classification == "incomplete"
    assert "generated_surface_cone" in closure.domains
    assert "odylith/radar/source/" in closure.missing_dependencies
    assert "odylith/registry/source/" in closure.missing_dependencies


def test_validation_matrix_tracks_recover_mode_and_external_resume_requirement() -> None:
    contract = _contract(execution_mode="recover")
    external_state = receipts.normalize_external_dependency_state(
        source="agent_stream",
        raw_status="awaiting_callback",
        external_id="agent-42",
    )
    closure = resource_closure.classify_resource_closure(["cell-01"], dependency_graph={"cell-01": ["deploy-group-a"]})

    matrix = validation.synthesize_validation_matrix(
        contract,
        resource_closure=closure,
        external_state=external_state,
    )

    assert matrix.archetype == "recover"
    assert "resume" in matrix.checks
    assert "derived_from" in matrix.to_dict()
    assert "mode:recover" in matrix.derived_from


def test_execution_engine_snapshot_carries_sync_runtime_contract(tmp_path: Path) -> None:
    session = sync_session.GovernedSyncSession(repo_root=tmp_path)
    payload = {
        "repo_root": str(tmp_path),
        "packet_kind": "bootstrap_session",
        "context_packet_state": "compact",
        "changed_paths": ["odylith/compass/compass.html"],
        "context_packet": {
            "packet_kind": "bootstrap_session",
            "packet_state": "compact",
            "route": {"route_ready": True, "native_spawn_ready": True},
        },
        "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
    }

    with sync_session.activate_sync_session(session):
        snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(payload)

    runtime_contract = snapshot["runtime_contract"]
    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)

    assert runtime_contract["reuse_scope"] == "sync_scoped"
    assert runtime_contract["settled_sync_session"] is True
    assert runtime_contract["repo_root"] == str(tmp_path.resolve())
    assert summary["execution_engine_runtime_reuse_scope"] == "sync_scoped"
    assert summary["execution_engine_runtime_settled_sync_session"] is True


def test_execution_engine_snapshot_carries_history_and_summary_reason_fields() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet_state": "compact",
            "changed_paths": ["odylith/compass/compass.html"],
            "known_failure_classes": [
                "partial scope requires closure",
                {"failure_class": "lane drift"},
            ],
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "packet_state": "compact",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
            "proof_state": {"current_blocker": "awaiting callback", "history_rule_hits": ["user correction decay"]},
        }
    )

    compact = runtime_surface_governance.compact_execution_engine_snapshot(snapshot)
    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)

    assert "partial_scope_requires_closure" in snapshot["history_rule_hits"]
    assert "lane_drift_preflight" in snapshot["history_rule_hits"]
    assert "user_correction_requires_promotion" in snapshot["history_rule_hits"]
    assert "execution_engine_pressure_signals" in summary
    assert "wait:awaiting_callback" in summary["execution_engine_pressure_signals"]
    assert "execution_engine_history_rule_hits" in summary
    assert "execution_engine_nearby_denial_actions" in summary
    assert "execution_engine_runtime_invalidated_by_step" in summary
    assert compact["nearby_denial_actions"]


def test_execution_engine_snapshot_infers_external_dependency_id_from_partial_proof_state() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet_state": "compact",
            "proof_state": {"current_blocker": "awaiting callback"},
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "packet_state": "compact",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        }
    )

    assert snapshot["external_dependency"]["semantic_status"] == "awaiting_callback"
    assert snapshot["external_dependency"]["external_id"] == "bootstrap_session"


def test_execution_engine_snapshot_accepts_external_mapping_without_explicit_id() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "governance_slice",
            "context_packet_state": "compact",
            "external_dependency": {
                "status": "queued",
                "detail": "gha workflow pending",
            },
            "context_packet": {
                "packet_kind": "governance_slice",
                "packet_state": "compact",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        }
    )

    assert snapshot["external_dependency"]["semantic_status"] == "queued"
    assert snapshot["external_dependency"]["external_id"] == "gha workflow pending"


def test_detect_execution_host_profile_captures_interrupt_and_artifact_paths() -> None:
    codex = detect_execution_host_profile("codex_cli")
    claude = detect_execution_host_profile("claude_code")
    unknown = detect_execution_host_profile("unsupported")

    assert codex.supports_interrupt is True
    assert codex.supports_artifact_paths is True
    assert claude.supports_interrupt is False
    assert claude.supports_artifact_paths is False
    assert unknown.supports_interrupt is False
    assert unknown.supports_artifact_paths is False


def test_evaluate_admissibility_claude_delegation_denial_carries_bounded_subagent_hint() -> None:
    contract = _contract(execution_mode="verify", host_family="claude_code")

    decision = policy.evaluate_admissibility(contract, "delegate.parallel_workers")

    assert decision.outcome == "deny"
    assert "prefer_task_tool_subagents_for_bounded_delegation" in decision.host_hints
    assert "delegation_style:task_tool_subagents" in decision.host_hints


def test_evaluate_admissibility_no_interrupt_pressure_signal_on_frontier_blocker() -> None:
    contract = _contract(execution_mode="verify", host_family="claude_code")
    frontier_obj = frontier.derive_execution_frontier(
        [
            ExecutionEvent(
                event_id="evt-1",
                event_type="phase",
                phase="verify",
                blocker="waiting on subagent",
                next_move="recover.current_blocker",
                execution_mode="verify",
            )
        ]
    )

    decision = policy.evaluate_admissibility(
        contract,
        "implement.target_scope",
        frontier=frontier_obj,
    )

    assert decision.outcome == "defer"
    assert "frontier:blocker_active" in decision.pressure_signals
    assert "host:no_interrupt" in decision.pressure_signals


def test_canonicalize_history_rule_recognizes_claude_specific_failure_classes() -> None:
    from odylith.runtime.execution_engine.history_rules import canonicalize_history_rule

    assert canonicalize_history_rule("context_exhaustion_detected") == "context_exhaustion_detected"
    assert canonicalize_history_rule("subagent_timeout_detected") == "subagent_timeout_detected"
    assert canonicalize_history_rule("context pressure compaction") == "context_exhaustion_detected"
    assert canonicalize_history_rule("subagent timeout on task tool") == "subagent_timeout_detected"
    assert canonicalize_history_rule("context exhaustion warning") == "context_exhaustion_detected"


def test_build_execution_event_stream_emits_context_pressure_event() -> None:
    from odylith.runtime.execution_engine.event_stream import build_execution_event_stream

    contract = _contract(host_family="claude_code")
    admissibility = policy.evaluate_admissibility(contract, "implement.target_scope")

    events_high = build_execution_event_stream(
        current_phase="implement",
        last_successful_phase="",
        blocker="",
        next_move="implement.target_scope",
        execution_mode="implement",
        admissibility=admissibility,
        context_pressure="high",
    )
    events_none = build_execution_event_stream(
        current_phase="implement",
        last_successful_phase="",
        blocker="",
        next_move="implement.target_scope",
        execution_mode="implement",
        admissibility=admissibility,
    )

    pressure_types = {e.event_type for e in events_high}
    assert "context_pressure" in pressure_types
    pressure_event = next(e for e in events_high if e.event_type == "context_pressure")
    assert "context_pressure:high" in pressure_event.pressure_signals
    assert "context_pressure" not in {e.event_type for e in events_none}


def test_runtime_lane_policy_artifact_path_guard_blocks_unsafe_parallel_fanout() -> None:
    no_artifact_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "claude",
            "execution_engine_host_supports_native_spawn": True,
            "execution_engine_host_supports_artifact_paths": False,
            "execution_engine_closure": "incomplete",
        }
    )
    safe_closure_guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "claude",
            "execution_engine_host_supports_native_spawn": True,
            "execution_engine_host_supports_artifact_paths": False,
            "execution_engine_closure": "safe",
        }
    )

    assert no_artifact_guard.blocked is True
    assert no_artifact_guard.code == "execution-engine-no-artifact-paths"
    assert "artifact paths" in no_artifact_guard.reason
    assert safe_closure_guard.blocked is False


def test_execution_engine_snapshot_applies_claude_presentation_defaults() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
    )

    contract = snapshot["contract"]
    assert contract["presentation_policy"]["commentary_mode"] == "task_first"
    assert contract["presentation_policy"]["suppress_routing_receipts"] is True

    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)
    assert summary["execution_engine_commentary_mode"] == "task_first"
    assert summary["execution_engine_suppress_routing_receipts"] is True
    assert summary["execution_engine_host_supports_artifact_paths"] is False
    assert summary["execution_engine_host_supports_interrupt"] is False


def test_runtime_lane_policy_artifact_path_guard_does_not_fire_for_delegation() -> None:
    delegation_guard = runtime_lane_policy.delegation_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "claude",
            "execution_engine_host_supports_native_spawn": True,
            "execution_engine_host_supports_artifact_paths": False,
            "execution_engine_closure": "incomplete",
        }
    )

    assert delegation_guard.code != "execution-engine-no-artifact-paths"


def test_build_execution_event_stream_emits_critical_context_pressure() -> None:
    from odylith.runtime.execution_engine.event_stream import build_execution_event_stream

    admissibility = policy.evaluate_admissibility(
        _contract(host_family="claude_code"), "implement.target_scope"
    )
    events = build_execution_event_stream(
        current_phase="implement",
        last_successful_phase="",
        blocker="",
        next_move="implement.target_scope",
        execution_mode="implement",
        admissibility=admissibility,
        context_pressure="critical",
    )
    pressure_event = next(e for e in events if e.event_type == "context_pressure")
    assert "context_pressure:critical" in pressure_event.pressure_signals

    events_low = build_execution_event_stream(
        current_phase="implement",
        last_successful_phase="",
        blocker="",
        next_move="implement.target_scope",
        execution_mode="implement",
        admissibility=admissibility,
        context_pressure="low",
    )
    assert "context_pressure" not in {e.event_type for e in events_low}


def test_execution_engine_snapshot_surfaces_context_pressure() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
        context_pressure="high",
    )

    assert snapshot["context_pressure"] == "high"
    compact = runtime_surface_governance.compact_execution_engine_snapshot(snapshot)
    assert compact["context_pressure"] == "high"
    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)
    assert summary["execution_engine_context_pressure"] == "high"


def test_execution_engine_snapshot_explicit_empty_presentation_policy_skips_claude_defaults() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "presentation_policy": {},
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
    )

    assert "presentation_policy" not in snapshot["contract"]


# ---------------------------------------------------------------------------
# Hardening: end-to-end regression and edge-case coverage
# ---------------------------------------------------------------------------


def test_execution_host_profile_from_capabilities_round_trips_new_fields() -> None:
    from odylith.runtime.execution_engine.contract import ExecutionHostProfile

    claude_caps = {
        "host_family": "claude",
        "model_family": "claude",
        "delegation_style": "task_tool_subagents",
        "supports_native_spawn": True,
        "supports_local_structured_reasoning": True,
        "supports_explicit_model_selection": True,
        "supports_interrupt": False,
        "supports_artifact_paths": False,
    }
    profile = ExecutionHostProfile.from_capabilities(claude_caps, model_name="claude-opus-4-6")

    assert profile.supports_interrupt is False
    assert profile.supports_artifact_paths is False
    assert profile.model_name == "claude-opus-4-6"

    roundtrip = profile.to_dict()
    assert roundtrip["supports_interrupt"] is False
    assert roundtrip["supports_artifact_paths"] is False

    codex_caps = dict(claude_caps, host_family="codex", delegation_style="routed_spawn",
                      supports_interrupt=True, supports_artifact_paths=True)
    codex_profile = ExecutionHostProfile.from_capabilities(codex_caps)
    assert codex_profile.supports_interrupt is True
    assert codex_profile.supports_artifact_paths is True


def test_execution_host_profile_unknown_host_defaults_are_safe() -> None:
    from odylith.runtime.execution_engine.contract import ExecutionHostProfile

    unknown = ExecutionHostProfile.detected(host_family="")
    assert unknown.host_family == "unknown"
    assert unknown.supports_native_spawn is False
    assert unknown.supports_interrupt is False
    assert unknown.supports_artifact_paths is False
    assert unknown.delegation_style == "none"
    assert "unknown_host_fail_closed" in unknown.execution_hints


def test_evaluate_admissibility_codex_delegation_denied_uses_main_thread_followup() -> None:
    """Codex host without native spawn (hypothetical) gets main_thread_followup, not bounded_task_subagent."""
    from odylith.runtime.execution_engine.contract import ExecutionHostProfile

    codex_no_spawn = ExecutionHostProfile(
        host_family="codex", host_display_name="Codex",
        model_family="gpt", model_name="gpt-5.4",
        delegation_style="routed_spawn",
        supports_native_spawn=False,
        supports_local_structured_reasoning=True,
        supports_explicit_model_selection=True,
        supports_interrupt=True, supports_artifact_paths=True,
    )
    contract = ExecutionContract.create(
        objective="test", authoritative_lane="test", target_scope=["a"],
        environment="test", resource_set=["a"], success_criteria=["pass"],
        validation_plan=["check"], allowed_moves=["verify", "re_anchor"],
        forbidden_moves=[], external_dependencies=[], critical_path=["a"],
        host_profile=codex_no_spawn,
    )

    decision = policy.evaluate_admissibility(contract, "delegate.something")
    assert decision.outcome == "deny"
    assert decision.nearest_admissible_alternative == "main_thread_followup"


def test_evaluate_admissibility_claude_hypothetical_no_spawn_uses_bounded_task_subagent() -> None:
    """Claude host without native spawn (hypothetical) gets bounded_task_subagent."""
    from odylith.runtime.execution_engine.contract import ExecutionHostProfile

    claude_no_spawn = ExecutionHostProfile(
        host_family="claude", host_display_name="Claude Code",
        model_family="claude", model_name="claude-sonnet-4-6",
        delegation_style="task_tool_subagents",
        supports_native_spawn=False,
        supports_local_structured_reasoning=True,
        supports_explicit_model_selection=True,
        supports_interrupt=False, supports_artifact_paths=False,
    )
    contract = ExecutionContract.create(
        objective="test", authoritative_lane="test", target_scope=["a"],
        environment="test", resource_set=["a"], success_criteria=["pass"],
        validation_plan=["check"], allowed_moves=["verify", "re_anchor"],
        forbidden_moves=[], external_dependencies=[], critical_path=["a"],
        host_profile=claude_no_spawn,
    )

    decision = policy.evaluate_admissibility(contract, "delegate.something")
    assert decision.outcome == "deny"
    assert decision.nearest_admissible_alternative == "bounded_task_subagent"
    assert "host_capability:native_spawn" in decision.violated_preconditions


def test_evaluate_admissibility_no_interrupt_signal_absent_on_codex() -> None:
    contract = _contract(execution_mode="verify", host_family="codex_cli")
    frontier_obj = frontier.derive_execution_frontier(
        [
            ExecutionEvent(
                event_id="evt-1", event_type="phase", phase="verify",
                blocker="waiting on CI", next_move="recover.current_blocker",
                execution_mode="verify",
            )
        ]
    )

    decision = policy.evaluate_admissibility(
        contract, "implement.target_scope", frontier=frontier_obj,
    )

    assert "frontier:blocker_active" in decision.pressure_signals
    assert "host:no_interrupt" not in decision.pressure_signals


def test_canonicalize_history_rule_no_false_positives_on_similar_tokens() -> None:
    from odylith.runtime.execution_engine.history_rules import canonicalize_history_rule

    assert canonicalize_history_rule("context_switch_detected") != "context_exhaustion_detected"
    assert canonicalize_history_rule("agent_timeout") != "subagent_timeout_detected"
    assert canonicalize_history_rule("subagent_error") != "subagent_timeout_detected"
    assert canonicalize_history_rule("context_change") != "context_exhaustion_detected"


def test_build_execution_event_stream_context_pressure_ordering() -> None:
    """Context pressure event must appear BEFORE the admissibility_decision event."""
    from odylith.runtime.execution_engine.event_stream import build_execution_event_stream

    admissibility = policy.evaluate_admissibility(
        _contract(host_family="claude_code"), "implement.target_scope"
    )
    events = build_execution_event_stream(
        current_phase="implement", last_successful_phase="",
        blocker="", next_move="implement.target_scope",
        execution_mode="implement", admissibility=admissibility,
        context_pressure="high",
    )
    event_types = [e.event_type for e in events]
    pressure_idx = event_types.index("context_pressure")
    decision_idx = event_types.index("admissibility_decision")
    assert pressure_idx < decision_idx


def test_runtime_lane_policy_artifact_path_guard_does_not_fire_without_presence_key() -> None:
    """When host_supports_artifact_paths is absent from summary, guard stays open (fail-open)."""
    guard = runtime_lane_policy.parallelism_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "claude",
            "execution_engine_host_supports_native_spawn": True,
            "execution_engine_closure": "incomplete",
        }
    )
    assert guard.code != "execution-engine-no-artifact-paths"


def test_runtime_lane_policy_delegation_guard_unaffected_by_artifact_path_fields() -> None:
    """delegation_guard never fires the artifact-path code regardless of field values."""
    guard = runtime_lane_policy.delegation_guard(
        {
            "execution_engine_present": True,
            "execution_engine_host_family": "claude",
            "execution_engine_host_supports_native_spawn": True,
            "execution_engine_host_supports_artifact_paths": False,
            "execution_engine_closure": "destructive",
        }
    )
    assert guard.code != "execution-engine-no-artifact-paths"


def test_execution_engine_snapshot_codex_host_no_presentation_defaults() -> None:
    """Codex host should NOT get Claude presentation defaults."""
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["codex_cli"],
    )
    assert "presentation_policy" not in snapshot["contract"]


def test_execution_engine_snapshot_claude_explicit_policy_overrides_defaults() -> None:
    """Explicit presentation_policy on Claude host takes priority over defaults."""
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "presentation_policy": {
                "commentary_mode": "verbose",
                "suppress_routing_receipts": False,
            },
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
    )

    contract = snapshot["contract"]
    assert contract["presentation_policy"]["commentary_mode"] == "verbose"
    assert contract["presentation_policy"]["suppress_routing_receipts"] is False


def test_execution_engine_snapshot_context_pressure_absent_by_default() -> None:
    """When no context_pressure is passed, it should be empty/absent in snapshot."""
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
    )

    assert snapshot["context_pressure"] == ""
    compact = runtime_surface_governance.compact_execution_engine_snapshot(snapshot)
    assert "context_pressure" not in compact


def test_execution_engine_snapshot_payload_context_pressure_fallback() -> None:
    """context_pressure in the payload dict is used as fallback."""
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_pressure": "critical",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
    )

    assert snapshot["context_pressure"] == "critical"
    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)
    assert summary["execution_engine_context_pressure"] == "critical"


def test_execution_engine_snapshot_governance_slice_gated_scope_prefers_recover() -> None:
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "governance_slice",
            "context_packet_state": "gated_broad_scope",
            "routing_handoff": {"route_ready": False, "native_spawn_ready": False},
            "context_packet": {
                "packet_kind": "governance_slice",
                "packet_state": "gated_broad_scope",
                "route": {"route_ready": False, "native_spawn_ready": False},
            },
        },
        host_candidates=["codex_cli"],
    )

    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)
    assert summary["execution_engine_mode"] == "recover"
    assert summary["execution_engine_next_move"] == "recover.current_blocker"
    assert summary["execution_engine_validation_archetype"] == "recover"


def test_execution_engine_compact_new_host_fields_are_additive() -> None:
    """New compact fields do not break the existing compact shape contract."""
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["claude_code"],
    )
    compact = runtime_surface_governance.compact_execution_engine_snapshot(snapshot)

    assert compact["host_supports_native_spawn"] is True
    assert compact.get("host_supports_interrupt", False) is False
    assert compact.get("host_supports_artifact_paths", False) is False
    assert isinstance(compact.get("host_execution_hints"), list)
    assert len(compact.get("host_execution_hints", [])) <= 4

    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)
    assert "execution_engine_host_supports_interrupt" in summary
    assert "execution_engine_host_supports_artifact_paths" in summary
    assert "execution_engine_host_execution_hints" in summary
    assert isinstance(summary["execution_engine_host_execution_hints"], tuple)


def test_execution_engine_summary_fields_are_superset_of_existing_contract() -> None:
    """Existing summary field keys must still be present after the new additions."""
    snapshot = runtime_surface_governance.build_packet_execution_engine_snapshot(
        {
            "packet_kind": "bootstrap_session",
            "context_packet": {
                "packet_kind": "bootstrap_session",
                "route": {"route_ready": True, "native_spawn_ready": True},
            },
            "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        },
        host_candidates=["codex_cli"],
    )
    summary = runtime_surface_governance.summary_fields_from_execution_engine(snapshot)

    required_keys = [
        "execution_engine_present",
        "execution_engine_outcome",
        "execution_engine_mode",
        "execution_engine_host_family",
        "execution_engine_model_family",
        "execution_engine_host_delegation_style",
        "execution_engine_host_supports_native_spawn",
        "execution_engine_host_supports_interrupt",
        "execution_engine_host_supports_artifact_paths",
        "execution_engine_host_execution_hints",
        "execution_engine_commentary_mode",
        "execution_engine_suppress_routing_receipts",
        "execution_engine_surface_fast_lane",
        "execution_engine_context_pressure",
    ]
    for key in required_keys:
        assert key in summary, f"missing required summary key: {key}"


def test_history_rule_collect_includes_new_failure_classes() -> None:
    """collect_history_rule_hits passes through carried Claude-specific failure classes."""
    from odylith.runtime.execution_engine.history_rules import collect_history_rule_hits

    closure = resource_closure.classify_resource_closure(["cell-01"])
    admissibility = policy.evaluate_admissibility(_contract(), "implement.target_scope")
    no_contradictions: list[contradictions.ContradictionRecord] = []

    hits = collect_history_rule_hits(
        closure=closure,
        admissibility=admissibility,
        contradictions=no_contradictions,
        proof_same_fingerprint_reopened=False,
        carried_history=["context exhaustion compaction", "subagent timeout"],
    )

    assert "context_exhaustion_detected" in hits
    assert "subagent_timeout_detected" in hits


# ---------------------------------------------------------------------------
# Integration: governance flows through bootstrap and context dossier delivery
# ---------------------------------------------------------------------------


def test_bootstrap_delivery_includes_execution_engine() -> None:
    """Verify the non-hot-path bootstrap compactor injects execution engine."""
    from odylith.runtime.context_engine import session_bootstrap_payload_compactor

    payload = {
        "context_packet": {
            "packet_kind": "bootstrap_session",
            "route": {"route_ready": True, "native_spawn_ready": True},
        },
        "routing_handoff": {"route_ready": True, "native_spawn_ready": True},
        "changed_paths": ["src/odylith/runtime/execution_engine/contract.py"],
        "selection_state": "selected",
    }
    compact = session_bootstrap_payload_compactor.compact_finalized_bootstrap_payload(payload)

    context_packet = compact.get("context_packet", {})
    eg = context_packet.get("execution_engine", {})
    assert eg, f"execution_engine should be present in bootstrap; got context_packet keys: {sorted(context_packet.keys())}"
    assert "outcome" in eg
    assert "mode" in eg


def test_context_dossier_delivery_includes_execution_engine() -> None:
    from odylith.runtime.context_engine.odylith_context_engine_store import compact_context_dossier_for_delivery

    dossier = {
        "resolved": True,
        "entity": {"id": "execution-engine", "type": "component", "title": "Execution Engine"},
        "lookup": {"query": "execution-engine", "kind": "component"},
        "matches": [],
        "relations": [],
        "related_entities": {},
        "recent_agent_events": [],
        "delivery_scopes": [],
        "full_scan_recommended": False,
        "full_scan_reason": "",
    }

    result = compact_context_dossier_for_delivery(dossier)
    assert result["resolved"] is True
    eg = result.get("execution_engine", {})
    assert eg, "execution_engine should be present in context dossier delivery"
    assert "outcome" in eg
    assert "mode" in eg
