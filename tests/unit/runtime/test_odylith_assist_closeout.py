from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.intervention_engine import delivery_runtime
from odylith.runtime.intervention_engine import conversation_runtime
from odylith.runtime.orchestration import subagent_orchestrator as orchestrator


def _decision(*, mode: str = "local_only", delegated_leaf_count: int = 0) -> orchestrator.OrchestrationDecision:
    subtasks = [
        orchestrator.SubtaskSlice(
            id=f"slice-{index + 1}",
            prompt="Implement the bounded slice.",
            owned_paths=[f"src/example_{index}.py"],
        )
        for index in range(delegated_leaf_count)
    ]
    return orchestrator.OrchestrationDecision(
        mode=mode,
        decision_id="decision-01",
        delegate=delegated_leaf_count > 0,
        parallel_safety="local_only",
        task_family="bounded_bugfix",
        confidence=3,
        rationale="bounded test decision",
        refusal_stage="",
        manual_review_recommended=False,
        merge_owner="main_thread",
        subtasks=subtasks,
        request={},
    )


def _write_delivery_artifact(repo_root: Path, payload: dict[str, object]) -> None:
    artifact_path = repo_root / "odylith" / "runtime" / "delivery_intelligence.v4.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload), encoding="utf-8")


def test_closeout_assist_builds_shortest_safe_path_line_semantically() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Fix the grounded install slice.",
        candidate_paths=[
            "src/odylith/install/agents.py",
            "src/odylith/install/manager.py",
            "tests/unit/install/test_agents.py",
        ],
        validation_commands=[
            "pytest -q tests/unit/install/test_agents.py",
            "pytest -q tests/integration/install/test_manager.py",
        ],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    assist = conversation_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is True
    assert assist["style"] == "shortest_safe_path"
    assert assist["label"] == "Odylith Assist:"
    assert assist["preferred_markdown_label"] == "**Odylith Assist:**"
    assert assist["changed_path_source"] == "request_seed_paths"
    assert assist["updated_artifacts"] == []
    assert assist["markdown_text"].startswith("**Odylith Assist:** kept this on the shortest safe path")
    assert "3 candidate paths" in assist["markdown_text"]
    assert "closing with 2 focused checks" in assist["markdown_text"]
    assert "`odylith_off`" in assist["markdown_text"]
    assert "broader unguided repo hunt" not in assist["markdown_text"]


def test_closeout_assist_includes_linked_updated_governance_artifacts() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Harden the chatter contract.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        validation_commands=["pytest -q tests/unit/runtime/test_odylith_assist_closeout.py"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    assist = conversation_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
        repo_root=Path("/tmp"),
        final_changed_paths=[
            "odylith/radar/source/ideas/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md",
            "odylith/technical-plans/done/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md",
            "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md",
        ],
        changed_path_source="final_changed_paths",
    )

    assert assist["eligible"] is True
    assert assist["style"] == "governed_lane"
    assert assist["changed_path_source"] == "final_changed_paths"
    assert [row["id"] for row in assist["updated_artifacts"]] == ["B-031", "odylith-chatter"]
    assert [row["kind"] for row in assist["updated_artifacts"]] == ["workstream", "component"]
    assert [row["id"] for row in assist["affected_contracts"]] == ["B-031", "odylith-chatter"]
    assert "affected governance contracts" in assist["markdown_text"]
    assert "[B-031](?tab=radar&workstream=B-031)" in assist["markdown_text"]
    assert "[odylith-chatter](?tab=registry&component=odylith-chatter)" in assist["markdown_text"]
    assert "closing with 1 focused check" in assist["markdown_text"]
    assert "governed record" in assist["markdown_text"]


def test_closeout_assist_names_contract_ids_without_changed_governance_paths() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Keep intervention UX visible across hosts.",
        workstreams=["B-096"],
        components=["governance-intervention-engine"],
        validation_commands=["pytest -q tests/unit/runtime/test_intervention_engine.py"],
        needs_write=False,
        evidence_cone_grounded=True,
    )

    assist = conversation_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
        repo_root=Path("/tmp"),
    )

    assert assist["eligible"] is True
    assert assist["style"] == "governed_lane"
    assert assist["updated_artifacts"] == []
    assert [row["id"] for row in assist["affected_contracts"]] == ["B-096", "governance-intervention-engine"]
    assert "staying inside affected governance contracts" in assist["markdown_text"]
    assert "[B-096](?tab=radar&workstream=B-096)" in assist["markdown_text"]
    assert "[governance-intervention-engine](?tab=registry&component=governance-intervention-engine)" in assist["markdown_text"]
    assert "1 workstream" not in assist["markdown_text"]
    assert "1 component" not in assist["markdown_text"]


def test_closeout_assist_recovers_high_signal_visibility_feedback_without_paths_or_ids() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt=(
            "I still do not see any Odylith ambient highlights or interventions "
            "visible in chat."
        ),
        needs_write=False,
        evidence_cone_grounded=True,
    )

    assist = conversation_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is True
    assert assist["style"] == "visibility_continuity"
    assert assist["updated_artifacts"] == []
    assert assist["affected_contracts"] == []
    assert "kept the UX signal from disappearing" in assist["markdown_text"]
    assert "intervention visibility feedback" in assist["markdown_text"]
    assert "candidate path" not in assist["markdown_text"]
    assert "focused check" not in assist["markdown_text"]


def test_closeout_assist_stays_silent_for_low_signal_grounded_turn_without_paths() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Thanks, that makes sense.",
        needs_write=False,
        evidence_cone_grounded=True,
    )

    assist = conversation_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is False
    assert assist["suppressed_reason"] == "missing_user_facing_delta"


def test_closeout_assist_suppresses_routing_receipts_for_task_first_fast_lane() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt='Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion".',
        candidate_paths=[
            "src/app/release_card.tsx",
            "src/app/release_card.css",
        ],
        validation_commands=["pytest -q tests/unit/app/test_release_card.py"],
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "execution_engine_commentary_mode": "task_first_minimal",
            "execution_engine_suppress_routing_receipts": True,
            "execution_engine_surface_fast_lane": True,
        },
    )

    assist = conversation_runtime.compose_closeout_assist(
        request=request,
        decision=_decision(mode="parallel_write", delegated_leaf_count=2),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": True,
            "requires_widening": False,
        },
    )

    assert assist["eligible"] is True
    assert assist["metrics"]["commentary_mode"] == "task_first_minimal"
    assert assist["metrics"]["suppress_routing_receipts"] is True
    assert assist["metrics"]["surface_fast_lane"] is True
    assert "routing 2 bounded leaves" not in assist["markdown_text"]
    assert "bounded leaves" not in assist["markdown_text"]
    assert "keeping execution bounded across 2 focused slices" in assist["markdown_text"]


def test_conversation_bundle_prefers_real_risks_over_other_labeled_signals() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten the governed slice.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        candidate_paths=["src/odylith/runtime/intervention_engine/conversation_runtime.py"],
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "context_packet": {
                "governance_obligations": {
                    "plan_binding_required": True,
                    "validation_obligation_count": 1,
                }
            }
        },
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
            "narrowing_required": False,
        },
        repo_root=Path("/tmp"),
        final_changed_paths=[
            "odylith/technical-plans/done/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md",
            "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md",
        ],
        changed_path_source="final_changed_paths",
    )

    ambient = dict(bundle["ambient_signals"])
    closeout = dict(bundle["closeout_bundle"])
    intervention = dict(bundle["intervention_bundle"])

    assert ambient["selected_signal"] == "risks"
    assert ambient["risks"]["eligible"] is True
    assert ambient["risks"]["render_hint"] == "explicit_label"
    assert "Odylith Risks:" in ambient["risks"]["markdown_text"]
    assert intervention["render_policy"]["voice_contract"]["templated_or_mechanical_forbidden"] is True
    assert closeout["selected_supplemental"] == "risks"
    assert closeout["risks"]["render_hint"] == "supplemental_line"
    assert closeout["render_policy"]["max_lines"] == 2
    assert closeout["render_policy"]["benchmark_safe"] is True


def test_conversation_bundle_suppresses_history_when_no_strong_prior_exists() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Patch the bounded slice.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
    )

    assert bundle["ambient_signals"]["history"]["eligible"] is False
    assert bundle["ambient_signals"]["history"]["suppressed_reason"] == "no_strong_prior"


def test_conversation_bundle_reads_precomputed_tribunal_risk_signal(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-031",
                    "scope_key": "workstream:B-031",
                    "scope_label": "B-031",
                    "case_refs": ["case-workstream-B-031"],
                    "operator_readout": {
                        "primary_scenario": "unsafe_closeout",
                        "severity": "watch",
                        "issue": "Closeout confidence is ahead of trusted proof.",
                        "action": "Capture the final reviewed checkpoint before closeout.",
                        "proof_refs": [{"kind": "workstream", "value": "B-031", "label": "B-031", "surface": "radar"}],
                        "requires_approval": True,
                    },
                    "claim_guard": {
                        "highest_truthful_claim": "fixed in code",
                        "blocked_terms": ["fixed", "cleared", "resolved"],
                    },
                    "surface_contributions": [{"surface": "Radar"}],
                    "evidence_bundle": {
                        "evidence_refs": [{"kind": "component", "value": "component:odylith-chatter", "label": "odylith-chatter"}]
                    },
                }
            ],
            "case_queue": [{"id": "case-workstream-B-031", "scope_key": "workstream:B-031", "headline": "Unsafe closeout", "brief": "Proof first."}],
            "systemic_brief": {"headline": "A few causes dominate.", "latent_causes": ["authority"], "summary": "Proof is the real bottleneck."},
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-031.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == "risks"
    assert "Tribunal already has B-031 in unsafe closeout" in bundle["ambient_signals"]["risks"]["markdown_text"]
    assert bundle["ambient_signals"]["claim_lint"]["highest_truthful_claim"] == "fixed in code"
    assert bundle["closeout_bundle"]["render_policy"]["claim_terms_require_lint"] is True
    assert bundle["closeout_bundle"]["selected_supplemental"] == "risks"


def test_conversation_bundle_does_not_lint_live_verified_claims(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-062",
                    "scope_key": "workstream:B-062",
                    "scope_label": "B-062",
                    "case_refs": ["case-workstream-B-062"],
                    "operator_readout": {"primary_scenario": "clear_path", "severity": "clear", "proof_refs": []},
                    "proof_state": {
                        "lane_id": "proof-state-control-plane",
                        "current_blocker": "Lambda permission lifecycle on ecs-drift-monitor invoke",
                        "first_failing_phase": "manifests-deploy",
                        "frontier_phase": "post-manifests-smoke",
                        "proof_status": "live_verified",
                    },
                    "claim_guard": {
                        "highest_truthful_claim": "fixed live",
                        "blocked_terms": [],
                        "hosted_frontier_advanced": True,
                    },
                    "surface_contributions": [{"surface": "Compass"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [
                {
                    "id": "case-workstream-B-062",
                    "scope_key": "workstream:B-062",
                    "headline": "Live proof advanced",
                    "brief": "The hosted run moved past the prior failing phase.",
                    "claim_guard": {
                        "highest_truthful_claim": "fixed live",
                        "blocked_terms": [],
                        "hosted_frontier_advanced": True,
                    },
                }
            ],
            "systemic_brief": {},
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-062.",
        workstreams=["B-062"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["claim_lint"]["status"] == "live_ok"
    assert bundle["ambient_signals"]["claim_lint"]["blocked_terms"] == []
    assert bundle["closeout_bundle"]["render_policy"]["claim_terms_require_lint"] is False


def test_conversation_bundle_rewrites_unqualified_resolution_terms_in_closeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-062",
                    "scope_key": "workstream:B-062",
                    "scope_label": "B-062",
                    "case_refs": ["case-workstream-B-062"],
                    "operator_readout": {"primary_scenario": "false_priority", "severity": "watch", "proof_refs": []},
                    "claim_guard": {
                        "highest_truthful_claim": "fixed in code",
                        "blocked_terms": ["fixed", "cleared", "resolved"],
                        "hosted_frontier_advanced": False,
                        "same_fingerprint_as_last_falsification": True,
                        "claim_scope": "code_or_preview",
                    },
                    "surface_contributions": [{"surface": "Compass"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [],
            "systemic_brief": {},
        },
    )

    monkeypatch.setattr(
        conversation_runtime,
        "compose_closeout_assist",
        lambda **_kwargs: {
            "eligible": True,
            "style": "test",
            "label": "Odylith Assist:",
            "preferred_markdown_label": "**Odylith Assist:**",
            "text": "**Odylith Assist:** The blocker is fixed.",
            "plain_text": "Odylith Assist: The blocker is fixed.",
            "markdown_text": "**Odylith Assist:** The blocker is fixed.",
            "user_win": "kept the proof honest",
            "delta": "",
            "proof": "",
            "updated_artifacts": [],
            "changed_path_source": "test",
            "suppressed_reason": "",
            "metrics": {},
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-062.",
        workstreams=["B-062"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["closeout_bundle"]["assist"]["markdown_text"] == "**Odylith Assist:** The blocker is fixed in code."
    assert bundle["closeout_bundle"]["assist"]["plain_text"] == "Odylith Assist: The blocker is fixed in code."
    assert bundle["ambient_signals"]["claim_lint"]["gate"]["state"] == "rewrite_or_block"
    assert bundle["ambient_signals"]["claim_lint"]["forced_checks"][0]["answer"] == "yes"
    assert bundle["closeout_bundle"]["claim_enforcement"]["closeout"]["assist"]["applied"] is True


def test_delivery_signal_snapshot_preserves_scope_proof_state_resolution(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-062",
                    "scope_key": "workstream:B-062",
                    "scope_label": "B-062",
                    "proof_state_resolution": {
                        "state": "ambiguous",
                        "lane_ids": ["lane-a", "lane-b"],
                    },
                    "proof_state": {},
                    "scope_signal": {
                        "rank": 5,
                        "rung": "R5",
                        "token": "blocking_frontier",
                        "label": "Blocking frontier",
                        "budget_class": "escalated_reasoning",
                        "promoted_default": True,
                    },
                    "claim_guard": {},
                    "surface_contributions": [{"surface": "Compass"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [],
            "systemic_brief": {},
        },
    )

    snapshot = delivery_runtime.delivery_signal_snapshot(tmp_path)

    assert snapshot["scopes_by_id"][("workstream", "B-062")]["proof_state_resolution"] == {
        "state": "ambiguous",
        "lane_ids": ["lane-a", "lane-b"],
    }
    assert snapshot["scopes_by_id"][("workstream", "B-062")]["scope_signal"]["rung"] == "R5"
    assert snapshot["scopes_by_id"][("workstream", "B-062")]["scope_signal"]["budget_class"] == "escalated_reasoning"


def test_conversation_bundle_reads_precomputed_tribunal_insight_signal(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-031",
                    "scope_key": "workstream:B-031",
                    "scope_label": "B-031",
                    "case_refs": [],
                    "operator_readout": {"primary_scenario": "clear_path", "severity": "clear", "proof_refs": []},
                    "surface_contributions": [{"surface": "Radar"}, {"surface": "Compass"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [],
            "systemic_brief": {
                "headline": "A small number of latent causes explain most of the queue.",
                "latent_causes": ["authority", "ownership gap"],
                "summary": "The interesting part is governance, not code spread.",
            },
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-031.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == "insight"
    assert "authority and ownership gap" in bundle["ambient_signals"]["insight"]["markdown_text"]
    assert "one more repo lap" in bundle["ambient_signals"]["insight"]["markdown_text"]


def test_conversation_bundle_reads_precomputed_tribunal_history_signal(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-031",
                    "scope_key": "workstream:B-031",
                    "scope_label": "B-031",
                    "case_refs": ["case-workstream-B-031"],
                    "operator_readout": {"primary_scenario": "clear_path", "severity": "clear", "proof_refs": []},
                    "surface_contributions": [{"surface": "Radar"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [{"id": "case-workstream-B-031", "scope_key": "workstream:B-031", "headline": "Queued"}],
            "systemic_brief": {},
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-031.",
        workstreams=["B-031"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == "history"
    assert "diagnosed queue" in bundle["ambient_signals"]["history"]["markdown_text"]


def test_conversation_bundle_prefers_explicit_tribunal_signals_over_cached_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        delivery_runtime,
        "delivery_signal_snapshot",
        lambda repo_root: (_ for _ in ()).throw(AssertionError("explicit Tribunal signals should bypass cached artifact lookup")),
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-031.",
        workstreams=["B-031"],
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "tribunal_delivery_signals": "ignore this malformed field",
            "tribunal_signals": {
                "scope_signals": [
                    {
                        "scope_type": "workstream",
                        "scope_id": "B-031",
                        "scope_label": "B-031",
                        "operator_readout": {
                            "primary_scenario": "unsafe_closeout",
                            "severity": "watch",
                            "action": "Capture the final reviewed checkpoint before closeout.",
                        },
                    }
                ],
                "systemic_brief": {"latent_causes": ["authority gap"]},
            },
        },
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == "risks"
    assert bundle["ambient_signals"]["risks"]["markdown_text"].startswith("**Odylith Risks:** Tribunal already has B-031 in unsafe closeout")
    assert ".." not in bundle["ambient_signals"]["risks"]["markdown_text"]


def test_conversation_bundle_sanitizes_malformed_explicit_tribunal_payload() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten the bounded slice.",
        candidate_paths=["src/example.py"],
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "tribunal_delivery_signals": {
                "scope_signals": "not-a-list",
                "case_queue": "still-not-a-list",
                "systemic_brief": "definitely-not-a-mapping",
            }
        },
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
    )

    assert bundle["ambient_signals"]["selected_signal"] == ""
    assert bundle["ambient_signals"]["insight"]["eligible"] is False
    assert bundle["ambient_signals"]["history"]["eligible"] is False
    assert bundle["ambient_signals"]["risks"]["eligible"] is False


def test_conversation_bundle_normalizes_string_latent_causes_from_delivery_artifact(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-031",
                    "scope_key": "workstream:B-031",
                    "scope_label": "B-031",
                    "case_refs": [],
                    "operator_readout": {"primary_scenario": "clear_path", "severity": "clear", "proof_refs": []},
                    "surface_contributions": [{"surface": "Radar"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [],
            "systemic_brief": {
                "headline": "One cause matters.",
                "latent_causes": "authority gap",
            },
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-031.",
        workstreams=["B-031"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == "insight"
    assert "authority gap" in bundle["ambient_signals"]["insight"]["markdown_text"]
    assert "a, u, t" not in bundle["ambient_signals"]["insight"]["markdown_text"].lower()


def test_conversation_bundle_skips_precomputed_tribunal_lookup_without_anchors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        delivery_runtime,
        "delivery_signal_snapshot",
        lambda repo_root: (_ for _ in ()).throw(AssertionError("delivery artifact lookup should stay skipped")),
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Patch the bounded slice.",
        candidate_paths=["src/odylith/install/agents.py"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == ""


def test_closeout_supplemental_requires_assist_even_when_ambient_risk_is_real(tmp_path: Path) -> None:
    _write_delivery_artifact(
        tmp_path,
        {
            "version": "v4",
            "scopes": [
                {
                    "scope_type": "workstream",
                    "scope_id": "B-031",
                    "scope_key": "workstream:B-031",
                    "scope_label": "B-031",
                    "case_refs": [],
                    "operator_readout": {
                        "primary_scenario": "unsafe_closeout",
                        "severity": "watch",
                        "action": "Capture the final reviewed checkpoint before closeout.",
                    },
                    "surface_contributions": [{"surface": "Radar"}],
                    "evidence_bundle": {},
                }
            ],
            "case_queue": [],
            "systemic_brief": {},
        },
    )
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten B-031.",
        workstreams=["B-031"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": False, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=tmp_path,
    )

    assert bundle["ambient_signals"]["selected_signal"] == "risks"
    assert bundle["closeout_bundle"]["assist"]["eligible"] is False
    assert bundle["closeout_bundle"]["selected_supplemental"] == ""
    assert bundle["closeout_bundle"]["risks"]["eligible"] is False
    assert bundle["closeout_bundle"]["risks"]["suppressed_reason"] == "assist_suppressed"


def test_conversation_bundle_reuses_metrics_and_context_scan_for_closeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    counts = {"metrics": 0, "context_rows": 0}
    original_metrics = conversation_runtime._evidence_metrics
    original_context_rows = conversation_runtime._context_artifact_rows

    def counting_metrics(*, request: object, decision: object, adoption: object) -> dict[str, object]:
        counts["metrics"] += 1
        return original_metrics(request=request, decision=decision, adoption=adoption)

    def counting_context_rows(*, repo_root: Path | None, value: object) -> list[dict[str, object]]:
        counts["context_rows"] += 1
        return original_context_rows(repo_root=repo_root, value=value)

    monkeypatch.setattr(conversation_runtime, "_evidence_metrics", counting_metrics)
    monkeypatch.setattr(conversation_runtime, "_context_artifact_rows", counting_context_rows)
    request = orchestrator.OrchestrationRequest(
        prompt="Tighten the chatter contract.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={"context_packet": {"selected_id": "B-031"}},
    )

    conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={"grounded": True, "route_ready": True, "grounded_delegate": False, "requires_widening": False},
        repo_root=Path("/tmp"),
        final_changed_paths=[
            "odylith/radar/source/ideas/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md",
            "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md",
        ],
        changed_path_source="final_changed_paths",
    )

    assert counts == {"metrics": 1, "context_rows": 1}


def test_conversation_bundle_suppresses_redundant_closeout_insight_when_assist_already_covers_it() -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Refine the chatter contract.",
        workstreams=["B-031"],
        components=["odylith-chatter"],
        validation_commands=["pytest -q tests/unit/runtime/test_odylith_assist_closeout.py"],
        needs_write=True,
        evidence_cone_grounded=True,
    )

    bundle = conversation_runtime.compose_conversation_bundle(
        request=request,
        decision=_decision(),
        adoption={
            "grounded": True,
            "route_ready": True,
            "grounded_delegate": False,
            "requires_widening": False,
        },
        repo_root=Path("/tmp"),
        final_changed_paths=[
            "odylith/radar/source/ideas/2026-03/2026-03-30-odylith-first-turn-bootstrap-and-short-form-grounding-commands.md",
            "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md",
        ],
        changed_path_source="final_changed_paths",
    )

    assert bundle["ambient_signals"]["insight"]["eligible"] is True
    assert bundle["closeout_bundle"]["selected_supplemental"] == ""
    assert bundle["closeout_bundle"]["insight"]["eligible"] is False
    assert bundle["closeout_bundle"]["insight"]["suppressed_reason"] == "overlaps_assist"


def test_orchestrator_threads_conversation_bundle_into_odylith_adoption(tmp_path: Path) -> None:
    request = orchestrator.OrchestrationRequest(
        prompt=(
            "Patch src/odylith/install/agents.py and src/odylith/install/manager.py, "
            "then prove the bounded install slice."
        ),
        acceptance_criteria=[
            "Keep src/odylith/install/agents.py, src/odylith/install/manager.py, and "
            "tests/unit/install/test_agents.py aligned with the grounded install behavior."
        ],
        candidate_paths=[
            "src/odylith/install/agents.py",
            "src/odylith/install/manager.py",
            "tests/unit/install/test_agents.py",
        ],
        validation_commands=[
            "pytest -q tests/unit/install/test_agents.py",
            "pytest -q tests/integration/install/test_manager.py",
        ],
        task_kind="implementation",
        phase="implementation",
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "routing_handoff": {
                "grounding": {"grounded": True, "score": 4},
                "routing_confidence": "high",
                "route_ready": True,
                "native_spawn_ready": True,
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
                    },
                },
            }
        },
    )

    decision = orchestrator.orchestrate_prompt(request, repo_root=tmp_path)

    adoption = dict(decision.odylith_adoption)
    assist = dict(adoption["closeout_assist"])
    bundle = dict(adoption["conversation_bundle"])

    assert assist["eligible"] is True
    assert assist["label"] == "Odylith Assist:"
    assert assist["changed_path_source"] == "request_seed_paths"
    assert assist["markdown_text"].startswith("**Odylith Assist:** kept this")
    assert "odylith_off" in assist["markdown_text"]
    assert adoption["ambient_signals"]["selected_signal"] in {"", "insight", "history", "risks"}
    assert bundle["closeout_bundle"]["assist"]["label"] == "Odylith Assist:"
    assert bundle["closeout_bundle"]["render_policy"]["benchmark_safe"] is True


def test_orchestrator_adoption_carries_execution_engine_targeting_and_presentation_policy(
    tmp_path: Path,
) -> None:
    request = orchestrator.OrchestrationRequest(
        prompt="Patch the consumer-safe UI binding slice.",
        acceptance_criteria=[
            "Keep the release-card UI binding change constrained to src/app/release_card.tsx.",
        ],
        candidate_paths=["src/app/release_card.tsx"],
        validation_commands=["pytest -q tests/unit/app/test_release_card.py"],
        task_kind="implementation",
        phase="implementation",
        needs_write=True,
        evidence_cone_grounded=True,
        context_signals={
            "routing_handoff": {
                "grounding": {"grounded": True, "score": 4},
                "routing_confidence": "high",
                "route_ready": True,
                "native_spawn_ready": True,
                "narrowing_required": False,
            },
            "target_resolution": {
                "lane": "consumer",
                "candidate_targets": [
                    {"path": "src/app/release_card.tsx", "writable": True},
                ],
                "diagnostic_anchors": [
                    {"kind": "workstream", "value": "B-073"},
                ],
                "has_writable_targets": True,
                "requires_more_consumer_context": False,
                "consumer_failover": "",
            },
            "presentation_policy": {
                "commentary_mode": "task_first_minimal",
                "suppress_routing_receipts": True,
                "surface_fast_lane": True,
            },
        },
    )

    decision = orchestrator.orchestrate_prompt(request, repo_root=tmp_path)
    adoption = dict(decision.odylith_adoption)

    assert adoption["execution_engine_target_lane"] == "consumer"
    assert adoption["execution_engine_has_writable_targets"] is True
    assert adoption["execution_engine_requires_more_consumer_context"] is False
    assert adoption["execution_engine_consumer_failover"] == ""
    assert adoption["execution_engine_commentary_mode"] == "task_first_minimal"
    assert adoption["execution_engine_suppress_routing_receipts"] is True
    assert adoption["execution_engine_surface_fast_lane"] is True
