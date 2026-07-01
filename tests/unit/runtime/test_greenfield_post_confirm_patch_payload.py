from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import Mapping

import pytest

from odylith.runtime.domain_intelligence import greenfield_post_confirm_patch_apply
from odylith.runtime.domain_intelligence import greenfield_post_confirm_rescue_planner
from odylith.runtime.domain_intelligence import greenfield_post_confirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionReport,
)


def test_repair_payload_enriches_rescue_patchset_with_structured_planner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = SimpleNamespace(
        provider_name="fake-provider",
        last_failure_code="",
        last_failure_detail="",
        last_request_model="",
        last_request_reasoning_effort="",
    )
    config = SimpleNamespace(
        model="planner-model",
        codex_reasoning_effort="high",
        claude_reasoning_effort="high",
    )

    monkeypatch.setattr(
        greenfield_post_confirm_rescue_planner.odylith_reasoning,
        "reasoning_config_from_env",
        lambda *, repo_root: config,
    )

    def fake_provider_from_config(
        resolved_config: Any,
        *,
        repo_root: Path,
        allow_implicit_local_provider: bool,
    ) -> Any:
        assert resolved_config is config
        assert repo_root == tmp_path.resolve()
        assert allow_implicit_local_provider is True
        return provider

    monkeypatch.setattr(
        greenfield_post_confirm_rescue_planner.odylith_reasoning,
        "provider_from_config",
        fake_provider_from_config,
    )

    def fake_plan_structured_patch(**kwargs: Any) -> dict[str, Any]:
        assert kwargs["provider"] is provider
        assert kwargs["patchset_request"]["operations"][0]["operation_id"] == "GF-PATCH-001"
        assert kwargs["evidence"]["intent"]["title"] == "Structured Repair"
        assert kwargs["model"] == "planner-model"
        assert kwargs["reasoning_effort"] == ""
        assert kwargs["timeout_seconds"] == 45.0
        return {
            "version": greenfield_post_confirm_rescue_planner.tribunal_patch_planner.TRIBUNAL_PATCH_PLAN_VERSION,
            "status": "planned",
            "operation_count": 1,
            "decision_summary": "Repair the first path fact.",
            "operations": [
                {
                    "operation_id": "GF-PATCH-001",
                    "replacement_fact": {
                        "first_path": "A reviewer checks the submitted record and sees the saved decision."
                    },
                    "decision_ledger_entry": {"chosen_interpretation": "first path is a user-visible decision"},
                    "proof_obligation_delta": {"visible_result_required": True},
                    "rejected_interpretation": "first path as a title-only noun phrase",
                    "confidence": 0.91,
                }
            ],
            "rejections": [],
            "provider": {},
        }

    monkeypatch.setattr(
        greenfield_post_confirm_rescue_planner.tribunal_patch_planner,
        "plan_structured_patch",
        fake_plan_structured_patch,
    )
    captured: dict[str, Any] = {}

    def fake_apply(
        proposal: Mapping[str, Any],
        *,
        release_selector: str,
        repair_context: engine.GreenfieldPostConfirmRepairContext | None,
    ) -> Mapping[str, Any]:
        captured["proposal"] = proposal
        captured["release_selector"] = release_selector
        captured["repair_context"] = repair_context
        return proposal

    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_patchset_repairs", fake_apply)
    context = engine.GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=10.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("typed first path finding",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-001",
                    "target_layer": "semantic_model",
                    "target_path": "semantic_model.first_path_contract",
                    "semantic_node_id": "SemanticModelIR.first_path_contract",
                    "issue_code": "semantic_alignment",
                    "source_finding": "semantic_workstream_alignment",
                    "affected_projections": ["radar", "project_brief"],
                    "requested_action": "Return a semantic patch.",
                    "replacement_fact": "",
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={"status": "failed"},
        repair_tier="rescue",
        rescue_activated=True,
    )

    greenfield_proposals._repair_confirmed_apply_payload(
        {"intent": {"title": "Structured Repair"}},
        release_selector="0.0.1",
        repair_context=context,
        repo_root=tmp_path,
    )

    enriched_context = captured["repair_context"]
    operation = enriched_context.patchset_request["operations"][0]
    assert operation["replacement_fact"]["first_path"].startswith("A reviewer checks")
    assert operation["decision_ledger_entry"]["chosen_interpretation"] == "first path is a user-visible decision"
    assert enriched_context.patchset_request["tribunal_patch_plan"]["status"] == "planned"


def test_repair_payload_skips_structured_planner_on_standard_tier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        greenfield_post_confirm_rescue_planner.tribunal_patch_planner,
        "plan_structured_patch",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("standard path called host planner")),
    )
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        greenfield_proposals,
        "apply_greenfield_patchset_repairs",
        lambda proposal, *, release_selector, repair_context: captured.setdefault("repair_context", repair_context)
        or proposal,
    )
    context = engine.GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=60.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("typed first path finding",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-001",
                    "target_layer": "semantic_model",
                    "target_path": "semantic_model.first_path_contract",
                    "semantic_node_id": "SemanticModelIR.first_path_contract",
                    "replacement_fact": "",
                }
            ],
        },
        quality_lenses={},
        semantic_compiler={},
        repair_tier="standard",
        rescue_activated=False,
    )

    greenfield_proposals._repair_confirmed_apply_payload(
        {"intent": {"title": "Standard Repair"}},
        release_selector="0.0.1",
        repair_context=context,
        repo_root=tmp_path,
    )

    assert captured["repair_context"] is context


def test_structured_patch_planner_uses_medium_effort_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ODYLITH_REASONING_CODEX_REASONING_EFFORT", raising=False)
    provider = SimpleNamespace(
        provider_name="codex-cli",
        last_failure_code="",
        last_failure_detail="",
        last_request_model="",
        last_request_reasoning_effort="",
    )
    config = SimpleNamespace(codex_reasoning_effort="high", claude_reasoning_effort="high")

    assert greenfield_post_confirm_rescue_planner._provider_reasoning_effort(config, provider) == "medium"


def test_structured_patch_planner_honors_explicit_effort_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ODYLITH_REASONING_CODEX_REASONING_EFFORT", "high")
    provider = SimpleNamespace(
        provider_name="codex-cli",
        last_failure_code="",
        last_failure_detail="",
        last_request_model="",
        last_request_reasoning_effort="",
    )
    config = SimpleNamespace(codex_reasoning_effort="high", claude_reasoning_effort="medium")

    assert greenfield_post_confirm_rescue_planner._provider_reasoning_effort(config, provider) == "high"


def test_structured_patch_planner_keeps_rescue_timeout_inside_budget() -> None:
    assert greenfield_post_confirm_rescue_planner._structured_patch_timeout_seconds(85.0) == 45.0
    assert greenfield_post_confirm_rescue_planner._structured_patch_timeout_seconds(40.0) == 30.0
    assert greenfield_post_confirm_rescue_planner._structured_patch_timeout_seconds(12.0) == 0.0


def test_structured_patch_planner_treats_empty_list_semantic_fact_as_executable() -> None:
    assert (
        greenfield_post_confirm_rescue_planner._needs_structured_patch_plan(
            {
                "operations": [
                    {
                        "target_layer": "semantic_model",
                        "target_path": "semantic_model.domain_ontology.external_systems",
                        "operation_kind": "semantic_external_systems",
                        "replacement_fact": {"external_systems": []},
                    }
                ]
            }
        )
        is False
    )
    assert (
        greenfield_post_confirm_rescue_planner._needs_structured_patch_plan(
            {
                "operations": [
                    {
                        "target_layer": "semantic_model",
                        "target_path": "semantic_model.domain_ontology.external_systems",
                        "operation_kind": "semantic_external_systems",
                        "replacement_fact": "",
                    }
                ]
            }
        )
        is True
    )


def test_repair_payload_consumes_structured_semantic_patch_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "normalize_host_reasoned_proposal", lambda proposal: dict(proposal))
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "complete_confirmed_proposal",
        lambda proposal, *, release_selector: {**proposal, "completed_for": release_selector},
    )
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "ensure_apply_semantic_model",
        lambda proposal, **_kwargs: {**proposal, "semantic_target_seen": True},
    )
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "repair_greenfield_semantic_projections", lambda _proposal: False)
    context = engine.GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("quality lens product_manager missing assumptions or ambiguity boundary",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "target_layer": "semantic_model",
                    "target_path": "semantic_model.domain_ontology.state_object",
                    "semantic_node_id": "SemanticModelIR.domain_ontology.state_object",
                    "source_finding": "quality_lens",
                    "replacement_fact": {"state_object": "patchset routed state"},
                },
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_proposals._repair_confirmed_apply_payload(
        {"intent": {"title": "Patchset Routed"}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert repaired["semantic_target_seen"] is True
    assert repaired["intent"]["state_object"] == "patchset routed state"


def test_quality_lens_operation_without_structured_fact_does_not_rehydrate_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "normalize_host_reasoned_proposal", lambda proposal: dict(proposal))
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "complete_confirmed_proposal",
        lambda proposal, *, release_selector: dict(proposal),
    )
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "ensure_apply_semantic_model",
        lambda proposal, **_kwargs: dict(proposal),
    )
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "repair_greenfield_semantic_projections", lambda _proposal: False)
    context = engine.GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("quality lens product_manager missing assumptions or ambiguity boundary",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "target_layer": "semantic_model",
                    "source_finding": "quality_lens",
                    "issue_code": "quality_lens_gap",
                    "replacement_fact": "",
                },
            ],
        },
        quality_lenses={
            "lenses": {
                "product_manager": {
                    "checks": [
                        {"name": "decision_boundary", "status": "failed"},
                    ]
                }
            }
        },
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_proposals._repair_confirmed_apply_payload(
        {"intent": {"title": "Quality Lens Empty Patch"}, "backlog": [{"title": "First path"}]},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert "assumptions" not in repaired
    assert "open_questions" not in repaired
    assert "validation_strategy" not in repaired
