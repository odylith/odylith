from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_post_confirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionReport,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_repair import repair_greenfield_package_once
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    repair_proposal_for_quality_lens_gaps,
)
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


class _PassingTribunal:
    status = "passed"
    issues: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "passed",
            "version": "greenfield-validation-gate-v1",
            "issues": [],
            "summary": "Passed.",
            "dimensions": {"intent": {}, "artifacts": {}, "governance": {}, "release": {}},
        }


def _disable_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_write.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )


def _proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(
            CONFIRMED_INTENT_TEXT,
            prompt="Draft a greenfield proposal for a municipal permit review workspace",
        ),
    )


def test_post_confirm_issue_classifier_returns_typed_repair_owner() -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"next_steps_previews": 1},
        tribunal_status="passed",
        issues=("Operator next steps `next_steps` has modal/base-form grammar drift near `can submits`",),
    )

    issue = engine.classify_greenfield_post_confirm_issues(report)[0]

    assert issue.code == "generated_copy_quality"
    assert issue.surface == "Operator next steps"
    assert issue.path == "next_steps"
    assert issue.repairability == "safe_package_repair"
    assert issue.owner == "operator_experience_renderer"
    assert issue.severity == "medium"


def test_post_confirm_issue_classifier_marks_malformed_copy_as_package_repair() -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"component_registry_previews": 1},
        tribunal_status="passed",
        issues=("`Episode Capture` generated prose uses malformed ownership verb pair at root",),
    )

    issue = engine.classify_greenfield_post_confirm_issues(report)[0]

    assert issue.code == "generated_copy_quality"
    assert issue.repairability == "safe_package_repair"
    assert issue.owner == "generated_copy_quality_kernel"
    assert issue.severity == "medium"


def test_post_confirm_issue_classifier_marks_quality_lens_gaps() -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"next_steps_previews": 1},
        tribunal_status="passed",
        issues=("quality lens engineer missing rendered component specs",),
    )

    issue = engine.classify_greenfield_post_confirm_issues(report)[0]

    assert issue.code == "quality_lens_gap"
    assert issue.repairability == "proposal_repair"
    assert issue.owner == "quality_lens_contract"
    assert issue.severity == "high"


def test_post_confirm_engine_stops_on_repeated_failure_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    package = GreenfieldCompletionPackage(proposal={}, release_selector="0.0.1")

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: None)

    def build_prewrite(_proposal: dict[str, object], _tribunal: Any) -> SimpleNamespace:
        return SimpleNamespace(package=package, backlog_result={})

    with pytest.raises(engine.GreenfieldPostConfirmEngineError) as exc:
        engine.run_greenfield_post_confirm_engine(
            proposal={},
            release_selector="0.0.1",
            build_prewrite=build_prewrite,
            repair_proposal=lambda current: current,
            proposal_ready=True,
            max_passes=3,
        )

    manifest = exc.value.manifest
    assert manifest["status"] == "failed"
    assert manifest["stop_reason"] == "no_progress"
    assert "missing_semantic_model" in manifest["issue_codes"]
    assert manifest["hard_blocker"] is None
    assert len(manifest["pass_records"]) == 2


def test_post_confirm_engine_passes_quality_lens_context_to_proposal_repair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = [
        GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={"next_steps_previews": 1},
            tribunal_status="passed",
            issues=("quality lens product_manager missing assumptions or ambiguity boundary",),
        ),
        GreenfieldCompletionReport(
            status="passed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={"next_steps_previews": 1},
            tribunal_status="passed",
            issues=(),
        ),
    ]
    repair_contexts: list[engine.GreenfieldPostConfirmRepairContext] = []

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: None)

    def build_prewrite(current: dict[str, object], _tribunal: Any) -> SimpleNamespace:
        return SimpleNamespace(
            package=GreenfieldCompletionPackage(proposal=current, release_selector="0.0.1"),
            backlog_result={},
        )

    def fake_package_repair(package: GreenfieldCompletionPackage) -> SimpleNamespace:
        report = reports[min(len(repair_contexts), len(reports) - 1)]
        return SimpleNamespace(
            package=package,
            initial_report=report,
            report=report,
            passes=0,
            changed=False,
        )

    def repair_callback(
        current: dict[str, object],
        context: engine.GreenfieldPostConfirmRepairContext,
    ) -> dict[str, object]:
        repair_contexts.append(context)
        return {**current, "repaired": True}

    monkeypatch.setattr(engine, "repair_greenfield_package_until_clean", fake_package_repair)

    result = engine.run_greenfield_post_confirm_engine(
        proposal={"intent": {"title": "Context Test"}},
        release_selector="0.0.1",
        build_prewrite=build_prewrite,
        repair_proposal=repair_callback,
        proposal_ready=True,
        max_passes=3,
    )

    assert result.proposal["repaired"] is True
    assert len(repair_contexts) == 1
    context = repair_contexts[0]
    assert context.pass_index == 0
    assert context.report.status == "failed"
    assert context.issues[0].code == "quality_lens_gap"
    assert context.quality_lenses["status"] == "failed"
    assert context.quality_lenses["lenses"]["product_manager"]["status"] == "failed"
    assert context.semantic_compiler["version"] == "odylith.greenfield.semantic_compiler.v1"


def test_post_confirm_classifier_preserves_semantic_compiler_counterexamples() -> None:
    issue = engine.classify_greenfield_post_confirm_issues(
        GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=(
                "GreenfieldSemanticCompiler intent.product_view: uses proof-boundary language as a product-result projection",
            ),
        )
    )[0]

    assert issue.code == "semantic_compiler"
    assert issue.severity == "high"
    assert issue.repairability == "proposal_repair"
    assert issue.owner == "semantic_model_compiler"


def test_quality_lens_repair_rehydrates_decision_scope_and_validation() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Permit Desk",
            "state_object": "permit application record",
            "first_path": "A reviewer checks a submitted permit application and records the decision.",
        },
        "backlog": [{"title": "Review submitted permit"}],
        "components": [{"component_id": "review", "label": "Review Workflow"}],
        "release_plan": {},
        "validation_strategy": [],
    }
    quality_lenses = {
        "lenses": {
            "product_manager": {
                "checks": [
                    {"name": "decision_boundary", "status": "failed"},
                    {"name": "first_release_scope", "status": "failed"},
                ],
            },
            "architect": {
                "checks": [
                    {"name": "system_boundary", "status": "failed"},
                    {"name": "component_topology", "status": "failed"},
                ],
            },
            "domain_expert": {
                "checks": [
                    {"name": "proof_boundary", "status": "failed"},
                    {"name": "high_risk_assumptions", "status": "failed"},
                ],
            },
        }
    }

    changed = repair_proposal_for_quality_lens_gaps(
        proposal,
        quality_lenses=quality_lenses,
        release_selector="0.0.1",
    )

    assert changed is True
    assert len(proposal["assumptions"]) >= 2
    assert len(proposal["open_questions"]) == 1
    assert len(proposal["intent"]["internal_systems"]) == 2
    assert proposal["intent"]["external_systems"] == []
    assert proposal["release_plan"]["selector"] == "0.0.1"
    assert proposal["release_plan"]["target_workstream_titles"] == ["Review submitted permit"]
    assert proposal["components"][0]["release_scope"] == "first_release"
    assert "proof" in proposal["intent"]["proof_boundary"].casefold()
    assert any("assumption proof" in row.casefold() for row in proposal["validation_strategy"])


def test_package_repair_collapses_adjacent_duplicate_words() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(package)

    assert repaired.rendered_component_specs == {"spec.md": "The record stays attached to the accepted state."}


def test_greenfield_apply_result_carries_post_confirm_quality_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    _disable_refreshes(monkeypatch)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_proposal(tmp_path),
        confirm=True,
        release_selector="0.0.1",
    )

    manifest = result["post_confirm_quality_manifest"]
    assert manifest["version"] == engine.POST_CONFIRM_QUALITY_MANIFEST_VERSION
    assert manifest["engine"] == engine.POST_CONFIRM_ENGINE_VERSION
    assert manifest["status"] == "passed"
    assert manifest["validation_status"] == "passed"
    assert manifest["stop_reason"] == "passed"
    assert manifest["budget_seconds"] == 60.0
    assert manifest["whole_project_elapsed_seconds"] < 60.0
    assert manifest["passes"] >= 1
    assert manifest["issue_count"] == 0
    assert manifest["issues"] == []
    assert manifest["quality_lenses"]["status"] == "passed"
    assert manifest["semantic_compiler"]["status"] == "passed"
    assert manifest["semantic_compiler"]["quality_scores"]["proof_result_separation"] == 1.0
    assert set(manifest["quality_lenses"]["lenses"]) == {
        "product_manager",
        "architect",
        "engineer",
        "domain_expert",
    }
    assert all(row["status"] == "passed" for row in manifest["quality_lenses"]["lenses"].values())
    assert manifest["write_transaction"]["status"] == "committed"
    assert manifest["write_transaction"]["rollback_guard"] == "enabled"
    assert manifest["write_transaction"]["prewrite_clean_before_commit"] is True
    assert manifest["artifact_counts"]["rendered_workstream_files"] == len(result["backlog"])
    assert manifest["artifact_counts"]["component_registry_previews"] == len(result["components"])


def test_confirmed_create_ignores_cli_prompt_after_intent_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intent = parse_confirmed_intent_text(CONFIRMED_INTENT_TEXT)
    monkeypatch.setattr(
        greenfield_proposals.repo_analysis,
        "summarize_source_inventory",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("post-confirm source scan leaked")),
    )
    first = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a completely unrelated drone marketplace",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    second = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Another unrelated prompt that must not alter confirmed create",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )

    assert first["intent"]["title"] == second["intent"]["title"]
    assert first["intent"]["prompt"] == second["intent"]["prompt"]
    assert first["apply_commands"] == second["apply_commands"]
    assert first["observed_source"]["source_posture"] == "confirmed_intent_only"
    assert "drone marketplace" not in str(first)
