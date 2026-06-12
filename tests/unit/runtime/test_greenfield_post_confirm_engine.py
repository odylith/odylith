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
