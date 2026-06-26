from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_post_confirm_patch_apply
from odylith.runtime.domain_intelligence import greenfield_post_confirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import confirmation_from_operator_intent
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import first_path_has_action_signal
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    build_greenfield_package_report,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionReport,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_patchset import patchset_request_from_findings
from odylith.runtime.domain_intelligence.greenfield_post_confirm_findings import package_review_findings
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import review_finding
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


def test_recovered_confirmed_intent_turns_product_noun_phrase_into_action_path() -> None:
    prompt = "Draft a greenfield proposal for a shelter capacity coordination workspace for municipal emergency operations teams."

    recovered = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    intent = parse_confirmed_intent_text(recovered, prompt=prompt)

    first_path = str(intent["first_path"])
    assert first_path_has_action_signal(first_path)
    assert "municipal emergency operations teams review shelter capacity coordination details" in first_path.casefold()
    assert "teams review" in first_path.casefold()
    assert "teams reviews" not in first_path.casefold()
    assert "teams records" not in first_path.casefold()


@pytest.mark.parametrize(
    ("prompt", "expected_phrase", "forbidden_phrase"),
    (
        (
            "Draft a greenfield proposal for an invoice anomaly review queue for finance operations analysts.",
            "finance operations analysts review invoice anomaly review details",
            "a invoice anomaly",
        ),
        (
            "Draft a greenfield proposal for a sleep routine reflection journal that avoids medical advice and only helps users prepare discussion notes.",
            "representative user reviews sleep routine reflection details",
            "avoids medical advice",
        ),
    ),
)
def test_recovered_confirmed_intent_repairs_constraints_and_container_labels(
    prompt: str,
    expected_phrase: str,
    forbidden_phrase: str,
) -> None:
    recovered = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    intent = parse_confirmed_intent_text(recovered, prompt=prompt)

    first_path = str(intent["first_path"])
    assert first_path_has_action_signal(first_path)
    assert expected_phrase in first_path.casefold()
    assert forbidden_phrase not in first_path.casefold()


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


def test_post_confirm_issue_classifier_prefers_typed_findings_over_message_text() -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"workstreams": 1},
        tribunal_status="passed",
        issues=("This prose intentionally contains no classifiable keywords.",),
        findings=(
            review_finding(
                code="semantic_alignment",
                surface="radar",
                target_path="proposal.backlog[0]",
                projection_id="radar",
                semantic_node_id="SemanticModelIR.workstream_contracts[0]",
                severity="high",
                repairability="semantic_patch",
                owner="semantic_model_compiler",
                source="semantic_workstream_alignment",
                message="This prose intentionally contains no classifiable keywords.",
            ),
        ),
    )

    issue = engine.classify_greenfield_post_confirm_issues(report)[0]

    assert issue.code == "semantic_alignment"
    assert issue.surface == "radar"
    assert issue.path == "proposal.backlog[0]"
    assert issue.projection_id == "radar"
    assert issue.semantic_node_id == "SemanticModelIR.workstream_contracts[0]"
    assert issue.repairability == "semantic_patch"
    assert issue.owner == "semantic_model_compiler"
    assert issue.source == "semantic_workstream_alignment"


def test_completion_report_serializes_typed_review_report() -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={},
        tribunal_status="passed",
        issues=("typed finding",),
        findings=(
            review_finding(
                code="artifact_shape_drift",
                surface="atlas",
                target_path="rendered_atlas_sources",
                projection_id="atlas",
                severity="high",
                repairability="plan_patch",
                owner="atlas_renderer",
                source="package_artifact_gate",
                message="typed finding",
            ),
        ),
    )

    payload = report.to_dict()

    assert payload["review_report"]["version"] == "odylith.greenfield.post_confirm.review_report.v1"
    assert payload["review_report"]["status"] == "failed"
    assert payload["review_report"]["findings"][0]["code"] == "artifact_shape_drift"
    assert payload["review_report"]["findings"][0]["repairability"] == "plan_patch"


def test_patchset_maps_typed_copy_findings_to_affected_artifact_projections() -> None:
    patchset = patchset_request_from_findings(
        (
            review_finding(
                code="generated_copy_quality",
                surface="Operator next steps",
                target_path="next_steps",
                severity="medium",
                repairability="safe_package_repair",
                owner="artifact_draft_cleaner",
                source="generated_copy_quality",
                message="Operator next steps has modal/base-form grammar drift near can submits.",
            ),
            review_finding(
                code="generated_copy_quality",
                surface="registry",
                target_path="rendered_component_specs",
                severity="medium",
                repairability="safe_package_repair",
                owner="artifact_draft_cleaner",
                source="rendered_component_spec_quality",
                message="Rendered component specs repeat adjacent words.",
            ),
        )
    ).to_dict()

    by_path = {operation["target_path"]: operation for operation in patchset["operations"]}

    assert by_path["next_steps"]["target_layer"] == "artifact_draft_set"
    assert by_path["next_steps"]["affected_projections"] == ("next_steps",)
    assert by_path["rendered_component_specs"]["target_layer"] == "artifact_draft_set"
    assert by_path["rendered_component_specs"]["affected_projections"] == ("registry",)


def test_patchset_preserves_semantic_field_target_and_rejected_interpretation() -> None:
    patchset = patchset_request_from_findings(
        (
            review_finding(
                code="quality_lens_gap",
                surface="product_manager",
                target_path="quality_lenses.product_manager.decision_boundary",
                projection_id="review_report",
                semantic_node_id="ReviewReport.quality_lenses",
                severity="high",
                repairability="semantic_patch",
                owner="quality_lens_contract",
                source="quality_lens",
                lens="product_manager",
                message="quality lens product_manager missing assumptions or ambiguity boundary",
            ),
        )
    ).to_dict()

    operation = patchset["operations"][0]

    assert operation["target_layer"] == "semantic_model"
    assert operation["target_path"] == "quality_lenses.product_manager.decision_boundary"
    assert operation["semantic_node_id"] == "ReviewReport.quality_lenses"
    assert operation["rejected_interpretation"] == (
        "quality lens product_manager missing assumptions or ambiguity boundary"
    )
    assert operation["replacement_fact"] == ""
    assert operation["decision_ledger_entry"] == ""
    assert operation["proof_obligation_delta"] == ""
    assert operation["affected_projections"] == ("project_brief", "radar", "release")


def test_semantic_coverage_package_findings_route_to_first_path_semantic_patch() -> None:
    findings = package_review_findings(
        GreenfieldCompletionPackage(proposal={"intent": {"title": "Coverage Route"}}),
        package_issues=(
            "prewrite Radar package missing semantic coverage for first path",
            "project brief preview missing semantic coverage for FirstPathContract",
        ),
    )

    semantic_findings = [finding for finding in findings if finding.source == "package_artifact_gate"]
    assert semantic_findings
    assert {finding.code for finding in semantic_findings} == {"semantic_alignment"}
    assert {finding.repairability for finding in semantic_findings} == {"semantic_patch"}
    assert {finding.semantic_node_id for finding in semantic_findings} == {"SemanticModelIR.first_path_contract"}
    assert {finding.owner for finding in semantic_findings} == {"semantic_model_compiler"}

    patchset = patchset_request_from_findings(semantic_findings).to_dict()
    operations = patchset["operations"]
    assert {operation["target_layer"] for operation in operations} == {"semantic_model"}
    assert {operation["target_path"] for operation in operations} == {"semantic_model.first_path_contract"}
    assert sorted({projection for operation in operations for projection in operation["affected_projections"]}) == [
        "project_brief",
        "radar",
    ]


def test_package_report_emits_structured_quality_lens_findings() -> None:
    package = GreenfieldCompletionPackage(
        proposal={
            "intent": {"title": "Typed Lens Test"},
            "semantic_model": {
                "schema_version": "odylith.greenfield.semantic_model.v1",
                "domain_ontology": {},
                "first_path_contract": {},
                "component_contracts": [],
                "workstream_contracts": [],
                "diagram_event_graph": {},
            },
        },
        release_selector="0.0.1",
    )

    report = build_greenfield_package_report(package)
    lens_findings = [finding for finding in report.findings if finding.code == "quality_lens_gap"]

    assert lens_findings
    assert any(finding.lens == "product_manager" for finding in lens_findings)
    assert all(finding.source == "quality_lens" for finding in lens_findings)
    assert all(finding.projection_id == "review_report" for finding in lens_findings)
    assert any(finding.code == "release_package_drift" and finding.projection_id == "release" for finding in report.findings)
    assert not any(
        finding.code == "artifact_shape_drift" and finding.message.startswith("quality lens ")
        for finding in report.findings
    )


def test_post_confirm_failure_signature_changes_when_typed_message_changes() -> None:
    first = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"workstreams": 1},
        tribunal_status="passed",
        issues=("semantic alignment missing first contract",),
        findings=(
            review_finding(
                code="semantic_alignment",
                surface="radar",
                target_path="proposal.backlog",
                projection_id="radar",
                semantic_node_id="SemanticModelIR.workstream_contracts",
                severity="high",
                repairability="semantic_patch",
                owner="semantic_model_compiler",
                source="semantic_workstream_alignment",
                message="semantic alignment missing first contract",
            ),
        ),
    )
    second = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"workstreams": 1},
        tribunal_status="passed",
        issues=("semantic alignment missing second contract",),
        findings=(
            review_finding(
                code="semantic_alignment",
                surface="radar",
                target_path="proposal.backlog",
                projection_id="radar",
                semantic_node_id="SemanticModelIR.workstream_contracts",
                severity="high",
                repairability="semantic_patch",
                owner="semantic_model_compiler",
                source="semantic_workstream_alignment",
                message="semantic alignment missing second contract",
            ),
        ),
    )

    assert engine._failure_signature(first) != engine._failure_signature(second)


def test_post_confirm_engine_stops_on_repeated_failure_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    package = GreenfieldCompletionPackage(proposal={}, release_selector="0.0.1")
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"workstreams": 1},
        tribunal_status="passed",
        issues=("semantic alignment still missing a workstream contract",),
        findings=(
            review_finding(
                code="semantic_alignment",
                surface="radar",
                target_path="proposal.backlog",
                projection_id="radar",
                semantic_node_id="SemanticModelIR.workstream_contracts",
                severity="high",
                repairability="semantic_patch",
                owner="semantic_model_compiler",
                source="semantic_workstream_alignment",
                message="semantic alignment still missing a workstream contract",
            ),
        ),
    )

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        engine,
        "repair_greenfield_package_until_clean",
        lambda current: SimpleNamespace(package=current, initial_report=report, report=report, passes=0, changed=False),
    )

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
    assert "semantic_alignment" in manifest["issue_codes"]
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
            findings=(
                review_finding(
                    code="quality_lens_gap",
                    surface="product_manager",
                    target_path="quality_lenses.product_manager.decision_boundary",
                    projection_id="review_report",
                    semantic_node_id="ReviewReport.quality_lenses",
                    severity="high",
                    repairability="semantic_patch",
                    owner="quality_lens_contract",
                    source="quality_lens",
                    lens="product_manager",
                    message="quality lens product_manager missing assumptions or ambiguity boundary",
                ),
            ),
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
    assert context.repair_tier == "rescue"
    assert context.budget_seconds == 90.0
    assert context.rescue_activated is True
    assert context.review_report["version"] == "odylith.greenfield.post_confirm.review_report.v1"
    assert context.patchset_request["version"] == "odylith.greenfield.post_confirm.patchset_request.v1"
    assert context.patchset_request["operations"][0]["target_layer"] == "semantic_model"
    assert context.quality_lenses["status"] == "failed"
    assert context.quality_lenses["lenses"]["product_manager"]["status"] == "failed"
    assert context.semantic_compiler["version"] == "odylith.greenfield.semantic_compiler.v1"


def test_post_confirm_auto_tier_stays_standard_when_first_pass_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = GreenfieldCompletionReport(
        status="passed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"next_steps_previews": 1},
        tribunal_status="passed",
        issues=(),
    )

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        engine,
        "repair_greenfield_package_until_clean",
        lambda package: SimpleNamespace(package=package, initial_report=report, report=report, passes=0, changed=False),
    )

    result = engine.run_greenfield_post_confirm_engine(
        proposal={"intent": {"title": "Tier Test"}},
        release_selector="0.0.1",
        build_prewrite=lambda current, _tribunal: SimpleNamespace(
            package=GreenfieldCompletionPackage(proposal=current, release_selector="0.0.1"),
            backlog_result={},
        ),
        repair_proposal=lambda current, _context: current,
        proposal_ready=True,
        repair_tier="auto",
    )

    assert result.manifest["repair_tier"] == "standard"
    assert result.manifest["requested_repair_tier"] == "auto"
    assert result.manifest["budget_seconds"] == 60.0
    assert result.manifest["rescue_activated"] is False


def test_post_confirm_deep_tier_requires_explicit_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = GreenfieldCompletionReport(
        status="passed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"next_steps_previews": 1},
        tribunal_status="passed",
        issues=(),
    )

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        engine,
        "repair_greenfield_package_until_clean",
        lambda package: SimpleNamespace(package=package, initial_report=report, report=report, passes=0, changed=False),
    )

    result = engine.run_greenfield_post_confirm_engine(
        proposal={"intent": {"title": "Deep Tier Test"}},
        release_selector="0.0.1",
        build_prewrite=lambda current, _tribunal: SimpleNamespace(
            package=GreenfieldCompletionPackage(proposal=current, release_selector="0.0.1"),
            backlog_result={},
        ),
        repair_proposal=lambda current, _context: current,
        proposal_ready=True,
        repair_tier="deep",
    )

    assert result.manifest["repair_tier"] == "deep"
    assert result.manifest["requested_repair_tier"] == "deep"
    assert result.manifest["budget_seconds"] == 120.0
    assert result.manifest["rescue_activated"] is True


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


def test_repair_payload_consumes_patchset_request_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

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

    def fake_lens_repair(proposal: dict[str, Any], **_kwargs: Any) -> bool:
        calls.append("quality_lens")
        proposal["quality_lens_target_seen"] = True
        return True

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "repair_proposal_for_quality_lens_gaps", fake_lens_repair)
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
                {"target_layer": "semantic_model", "source_finding": "quality_lens"},
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
    assert repaired["quality_lens_target_seen"] is True
    assert calls == ["quality_lens"]


def test_patchset_semantic_coverage_operation_repairs_first_path_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "complete_confirmed_proposal",
        lambda proposal, *, release_selector: dict(proposal),
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
            issues=("prewrite Radar package missing semantic coverage for first path",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "target_layer": "semantic_model",
                    "target_path": "semantic_model.first_path_contract",
                    "semantic_node_id": "SemanticModelIR.first_path_contract",
                    "issue_code": "semantic_alignment",
                    "affected_projections": ["radar"],
                    "rejected_interpretation": "prewrite Radar package missing semantic coverage for first path",
                },
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )
    proposal = {
        "intent": {
            "title": "Shelter Capacity Coordination Workspace",
            "state_object": "A shelter capacity coordination workspace result record.",
            "first_path": "A shelter capacity coordination workspace for municipal emergency operations teams.",
            "human_actors": [],
        },
        "components": [],
        "backlog": [],
    }

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        proposal,
        release_selector="0.0.1",
        repair_context=context,
    )

    first_path = repaired["intent"]["first_path"]
    first_path_contract = repaired["semantic_model"]["first_path_contract"]
    assert first_path_has_action_signal(first_path)
    assert "municipal emergency operations teams review shelter capacity coordination details" in first_path.casefold()
    assert first_path_contract["raw_path"] == first_path
    assert "shelter" in first_path_contract["capability"].casefold()
    assert "capacity" in first_path_contract["capability"].casefold()


def test_repair_payload_does_not_mutate_proposal_for_artifact_draft_only_patchset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "normalize_host_reasoned_proposal", lambda proposal: dict(proposal))
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)

    def unexpected_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("completion")
        return {}

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", unexpected_completion)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "ensure_apply_semantic_model", unexpected_completion)
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
            issues=("Rendered artifact copy issue",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "target_layer": "artifact_draft_set",
                    "issue_code": "generated_copy_quality",
                    "affected_projections": ["registry"],
                },
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_proposals._repair_confirmed_apply_payload(
        {"intent": {"title": "Artifact Draft Only"}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert repaired == {"intent": {"title": "Artifact Draft Only"}}
    assert calls == []


def test_package_repair_collapses_adjacent_duplicate_words() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(package)

    assert repaired.rendered_component_specs == {"spec.md": "The record stays attached to the accepted state."}


def test_package_repair_requires_artifact_draft_patchset_permission() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={"status": "no_repairable_operations", "operations": []},
    )

    assert repaired == package


def test_package_repair_does_not_mutate_rendered_copy_for_plan_patch() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                {
                    "target_layer": "artifact_plan",
                    "issue_code": "generated_copy_quality",
                    "affected_projections": ["registry"],
                }
            ],
        },
    )

    assert repaired == package


def test_package_repair_only_mutates_patchset_affected_projection() -> None:
    package = GreenfieldCompletionPackage(
        proposal={},
        rendered_component_specs={"spec.md": "The record stays attached attached to the accepted state."},
        next_steps_preview={"implementation_prompt": "The next step stays attached attached to the accepted state."},
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                {
                    "target_layer": "artifact_draft_set",
                    "issue_code": "generated_copy_quality",
                    "affected_projections": ["next_steps"],
                }
            ],
        },
    )

    assert repaired.rendered_component_specs == package.rendered_component_specs
    assert repaired.next_steps_preview == {
        "implementation_prompt": "The next step stays attached to the accepted state."
    }


def test_package_repair_preserves_structural_metadata_inside_repaired_projections() -> None:
    registry_path = "/tmp/stays attached attached/odylith/registry/source/component_registry.v1.json"
    spec_path = "/tmp/stays attached attached/odylith/registry/source/components/c-001/CURRENT_SPEC.md"
    package = GreenfieldCompletionPackage(
        proposal={},
        component_registry_preview=(
            {
                "component_id": "case-redaction",
                "registry_path": registry_path,
                "spec_path": spec_path,
                "feature_history": [
                    {"summary": "The record stays attached attached to the accepted state."},
                ],
            },
        ),
        accepted_project_preview={
            "schema_version": "odylith.accepted_project.v1",
            "created": {
                "components": [
                    {
                        "component_id": "case-redaction",
                        "registry_path": registry_path,
                        "spec_path": spec_path,
                        "feature_history": [
                            {"summary": "The record stays attached attached to the accepted state."},
                        ],
                    }
                ]
            },
        },
    )

    repaired = repair_greenfield_package_once(
        package,
        patchset_request={
            "status": "repairable",
            "operations": [
                {
                    "target_layer": "artifact_draft_set",
                    "issue_code": "generated_copy_quality",
                    "affected_projections": ["accepted_project", "registry"],
                }
            ],
        },
    )

    assert repaired.component_registry_preview[0]["registry_path"] == registry_path
    assert repaired.component_registry_preview[0]["spec_path"] == spec_path
    repaired_components = repaired.accepted_project_preview["created"]["components"]
    assert repaired_components[0]["registry_path"] == registry_path
    assert repaired_components[0]["spec_path"] == spec_path
    assert (
        repaired.component_registry_preview[0]["feature_history"][0]["summary"]
        == "The record stays attached to the accepted state."
    )
    assert (
        repaired_components[0]["feature_history"][0]["summary"]
        == "The record stays attached to the accepted state."
    )


def test_package_repair_preserves_markdown_plan_link_targets() -> None:
    summary = (
        "2026-06-25: Registered Flood Shelter Intake System Intake Register Service as a planned service from user intent "
        "(Plan: [B-002](odylith/radar/radar.html?view=plan&workstream=B-002))."
    )
    package = GreenfieldCompletionPackage(
        proposal={},
        component_registry_preview=(
            {
                "component_id": "intake-register",
                "feature_history": [{"date": "2026-06-25", "summary": summary}],
            },
        ),
        rendered_component_specs={"spec.md": f"## Feature History\n- {summary}\n"},
    )

    repaired = repair_greenfield_package_once(package)

    repaired_summary = repaired.component_registry_preview[0]["feature_history"][0]["summary"]
    assert "odylith/radar/radar.html?view=plan&workstream=B-002" in repaired_summary
    assert "radar. html? view=plan" not in repaired_summary
    assert "odylith/radar/radar.html?view=plan&workstream=B-002" in repaired.rendered_component_specs["spec.md"]


def test_final_next_steps_repair_matches_prewrite_copy_repair() -> None:
    repaired = greenfield_apply_write._repair_final_next_steps(
        {
            "start_workstream_id": "B-002",
            "validation_gates": [
                "Flood Shelter Intake System Intake Register Service owns flood shelter intake intake register evidence, review rules, and result visibility",
                "Flood Shelter Intake System Intake Register Service blocks incomplete evidence before presenting a result, then explains what has to change for flood shelter intake intake register",
            ],
        }
    )

    rendered = "\n".join(repaired["validation_gates"])
    assert "intake intake" not in rendered.casefold()
    assert "flood shelter intake register evidence" in rendered.casefold()


def test_final_next_steps_repair_preserves_release_selector_tokens() -> None:
    repaired = greenfield_apply_write._repair_final_next_steps(
        {
            "release_selector": "0.0.1",
            "customization_options": [
                "External systems: Confirm whether release 0.0.1 needs these external systems: Browser runtime.",
                "Release ambition: Keep 0.0.1 to the accepted first path.",
            ],
            "coding_readiness_gates": [
                "Release 0.0.1 has proof checks for success, failure, replay, access, and review evidence."
            ],
            "operator_sequence": [
                "Open the progress view and verify the active wave `first proof` plus release `0.0.1` match the accepted project shape."
            ],
        }
    )

    rendered = json.dumps(repaired, sort_keys=True)
    assert "0.0.1" in rendered
    assert "0. 0. 1" not in rendered


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
    assert manifest["patchset_request"]["version"] == "odylith.greenfield.post_confirm.patchset_request.v1"
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
