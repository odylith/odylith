from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.artifact_quality.greenfield_quality_lenses import build_greenfield_quality_lens_report
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import greenfield_apply_semantic_input
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_findings import package_review_findings
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_GATE_ONLY_CHECKS,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_PLAN_REPAIR_CHECKS,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_REPAIR_OWNER_BY_CHECK,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_SEMANTIC_REPAIR_CHECKS,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    quality_lens_repair_owner,
)


def _all_lens_check_names() -> set[str]:
    package = SimpleNamespace(
        proposal={},
        release_selector="0.0.1",
        release_workstream_ids=(),
        rendered_atlas_sources={},
        rendered_component_specs={},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )
    report = build_greenfield_quality_lens_report(package)
    return {
        str(check.get("name"))
        for lens in report["lenses"].values()
        for check in lens["checks"]
        if str(check.get("name")).strip()
    }


def test_quality_lens_repair_declares_every_reviewer_check() -> None:
    check_names = _all_lens_check_names()
    repairable_checks = QUALITY_LENS_SEMANTIC_REPAIR_CHECKS | QUALITY_LENS_PLAN_REPAIR_CHECKS

    assert set(QUALITY_LENS_REPAIR_OWNER_BY_CHECK) == check_names
    assert repairable_checks | QUALITY_LENS_GATE_ONLY_CHECKS == check_names
    assert QUALITY_LENS_SEMANTIC_REPAIR_CHECKS.isdisjoint(QUALITY_LENS_PLAN_REPAIR_CHECKS)
    assert repairable_checks.isdisjoint(QUALITY_LENS_GATE_ONLY_CHECKS)
    assert {quality_lens_repair_owner(check) for check in QUALITY_LENS_SEMANTIC_REPAIR_CHECKS} == {
        "semantic_model_compiler"
    }
    assert {quality_lens_repair_owner(check) for check in QUALITY_LENS_PLAN_REPAIR_CHECKS} == {
        "artifact_plan_projector"
    }
    assert {quality_lens_repair_owner(check) for check in QUALITY_LENS_GATE_ONLY_CHECKS} == {"prewrite_gate"}


def test_apply_semantic_input_records_deferred_external_boundary_when_missing() -> None:
    compiler_input = greenfield_apply_semantic_input(
        {
            "intent": {
                "title": "Local Review Workspace",
                "state_object": "A local review file records one submitted item, reviewer notes, and final status.",
                "first_path": "A reviewer opens a local draft, records a decision, and sees the accepted result.",
                "proof_boundary": "Release succeeds when the reviewer can inspect the decision and supporting evidence.",
            },
            "components": [{"component_id": "review-file", "label": "Review File"}],
            "backlog": [
                {
                    "title": "Prove local review path",
                    "product_view": "The product records one local review decision and evidence trail.",
                }
            ],
        }
    )

    assert compiler_input.external_systems
    assert "No live external system is accepted" in compiler_input.external_systems[0]
    assert dict(compiler_input.source_paths)["external_systems"] == "semantic_inference.deferred_external_boundary"


def test_quality_lens_report_emits_typed_tribunal_repair_targets() -> None:
    package = SimpleNamespace(
        proposal={},
        release_selector="0.0.1",
        release_workstream_ids=(),
        rendered_atlas_sources={},
        rendered_component_specs={},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    product_checks = {
        check["name"]: check
        for check in report["lenses"]["product_manager"]["checks"]
    }
    architect_checks = {
        check["name"]: check
        for check in report["lenses"]["architect"]["checks"]
    }
    all_checks = {
        check["name"]: check
        for lens in report["lenses"].values()
        for check in lens["checks"]
    }

    assert report["lenses"]["product_manager"]["role"] == "Product manager"
    assert product_checks["complete_first_path"]["target_path"] == "semantic_model.first_path_contract"
    assert product_checks["decision_boundary"]["semantic_node_id"] == "ArtifactPlanIR.assumptions"
    assert product_checks["decision_boundary"]["repairability"] == "plan_patch"
    assert architect_checks["component_topology"]["surface"] == "registry"
    assert architect_checks["component_topology"]["owner"] == "artifact_plan_projector"
    assert architect_checks["component_topology"]["repairability"] == "plan_patch"
    assert all_checks["component_specs"]["owner"] == "prewrite_gate"
    assert all_checks["component_specs"]["repairability"] == "unrepairable"
    assert all_checks["validation_evidence"]["owner"] == "prewrite_gate"
    assert all_checks["validation_evidence"]["repairability"] == "unrepairable"
    assert all_checks["prewrite_safety"]["owner"] == "prewrite_gate"
    assert all_checks["prewrite_safety"]["repairability"] == "unrepairable"
    assert {
        name: check["owner"]
        for name, check in all_checks.items()
        if name in QUALITY_LENS_REPAIR_OWNER_BY_CHECK
    } == QUALITY_LENS_REPAIR_OWNER_BY_CHECK


def test_quality_lens_accepts_two_component_confirmed_create_when_systems_are_covered() -> None:
    package = SimpleNamespace(
        proposal={
            "write_policy": "confirmed_intent_before_confirmed_create",
            "intent": {
                "reasoning_mode": "odylith_confirmed_governed_proposal",
                "state_object": "An evidence case records packet, decision, blocker, readiness proof, and review history.",
                "internal_systems": [
                    "Evidence Intake Log: records submitted packets and missing input blockers.",
                    "Readiness Review Board: records supervisor decision and readiness proof.",
                ],
            },
            "components": [
                {
                    "component_id": "evidence-intake-log",
                    "label": "Evidence Intake Log Service",
                    "release_scope": "first_path_required",
                },
                {
                    "component_id": "readiness-review-board",
                    "label": "Readiness Review Board",
                    "release_scope": "first_path_required",
                },
            ],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={
            "Evidence Intake Log Service": "# Evidence Intake Log Service\n",
            "Readiness Review Board": "# Readiness Review Board\n",
        },
        component_registry_preview=(
            {"component_id": "evidence-intake-log", "validation_gate": {"status": "passed"}},
            {"component_id": "readiness-review-board", "validation_gate": {"status": "passed"}},
        ),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    architect_checks = {
        check["name"]: check
        for check in report["lenses"]["architect"]["checks"]
    }
    engineer_checks = {
        check["name"]: check
        for check in report["lenses"]["engineer"]["checks"]
    }

    assert architect_checks["component_topology"]["status"] == "passed"
    assert engineer_checks["component_specs"]["status"] == "passed"
    assert "2 active component(s), 2 component row(s), 2 internal system(s)" in architect_checks["component_topology"]["evidence"]
    assert "2 spec or preview evidence row(s) for 2 active component(s)" in engineer_checks["component_specs"]["evidence"]


def test_quality_lens_accepts_deferred_component_topology_when_all_systems_are_covered() -> None:
    package = SimpleNamespace(
        proposal={
            "write_policy": "confirmed_intent_before_confirmed_create",
            "intent": {
                "reasoning_mode": "odylith_confirmed_governed_proposal",
                "state_object": "A communication run records configuration, execution, telemetry, verification, and saved history.",
                "internal_systems": [
                    "Run Configuration and Validation supports E91 parameters and endpoints.",
                    "Hardware Control and Run Execution sequences the hardware run.",
                    "Live Telemetry Stream exposes CHSH and QBER while the run progresses.",
                    "Security and Verification Logic computes secure-link verdicts.",
                    "Results Store and Run History keeps persisted comparison evidence.",
                ],
            },
            "components": [
                {
                    "component_id": "run-configuration-and-validation",
                    "label": "Run Configuration and Validation Service",
                    "release_scope": "supporting",
                },
                {
                    "component_id": "hardware-control-and-run-execution",
                    "label": "Hardware Control and Run Execution Service",
                    "release_scope": "first_path_required",
                },
                {
                    "component_id": "live-telemetry-stream",
                    "label": "Live Telemetry Stream Service",
                    "release_scope": "deferred",
                },
                {
                    "component_id": "security-and-verification-logic",
                    "label": "Security and Verification Logic Service",
                    "release_scope": "supporting",
                },
                {
                    "component_id": "results-store-and-run-history",
                    "label": "Results Store and Run History",
                    "release_scope": "supporting",
                },
            ],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={
            "Run Configuration and Validation Service": "# Run Configuration and Validation Service\n",
            "Hardware Control and Run Execution Service": "# Hardware Control and Run Execution Service\n",
            "Security and Verification Logic Service": "# Security and Verification Logic Service\n",
            "Results Store and Run History": "# Results Store and Run History\n",
        },
        component_registry_preview=(
            {"component_id": "run-configuration-and-validation", "validation_gate": {"status": "passed"}},
            {"component_id": "hardware-control-and-run-execution", "validation_gate": {"status": "passed"}},
            {"component_id": "security-and-verification-logic", "validation_gate": {"status": "passed"}},
            {"component_id": "results-store-and-run-history", "validation_gate": {"status": "passed"}},
        ),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    architect_checks = {
        check["name"]: check
        for check in report["lenses"]["architect"]["checks"]
    }
    engineer_checks = {
        check["name"]: check
        for check in report["lenses"]["engineer"]["checks"]
    }

    assert architect_checks["component_topology"]["status"] == "passed"
    assert engineer_checks["component_specs"]["status"] == "passed"
    assert "4 active component(s), 5 component row(s), 5 internal system(s)" in architect_checks["component_topology"]["evidence"]
    assert "4 spec or preview evidence row(s) for 4 active component(s)" in engineer_checks["component_specs"]["evidence"]


def test_quality_lens_does_not_use_proof_boundary_as_visible_result() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "first_path_contract": {
                    "capability": "Reviewer accepts one record and sees the accepted state.",
                    "events": [{"action": "accept"}, {"action": "review"}, {"action": "publish"}],
                }
            },
            "intent": {
                "proof_boundary": "Release succeeds when evidence is reviewed and accepted.",
            },
            "backlog": [{"success_metrics": ["Accepted state appears", "Review evidence is saved"]}],
            "assumptions": [{"statement": "One record is enough."}, {"statement": "Review owner is known."}],
            "open_questions": [{"question": "Who owns final publication?"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["product_manager"]["checks"]}

    assert checks["complete_first_path"]["status"] == "failed"
    assert "visible result" in checks["complete_first_path"]["issue"]


def test_domain_expert_lens_fails_when_scientific_source_terms_disappear() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": "Release succeeds when assay input, calibration baseline, and uncertainty interval are visible.",
                },
                "first_path_contract": {
                    "capability": "Researcher runs an assay simulation with calibration baseline and uncertainty interval.",
                    "visible_result": "Simulation result with uncertainty interval and baseline comparison.",
                },
            },
            "intent": {
                "state_object": "An assay simulation run records dataset identity, calibration baseline, model version, and uncertainty interval.",
            },
            "assumptions": [],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={"Generic Review Service": "Review service records status and approval evidence."},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["domain_expert"]["checks"]}

    assert checks["domain_term_coverage"]["status"] == "failed"
    assert "domain term coverage" in checks["domain_term_coverage"]["issue"]


def test_product_manager_lens_requires_explicit_first_release_requirements_in_scored_surfaces() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": (
                        "Release succeeds when the release brief is reviewable. "
                        "The first release includes one workspace per extension and a review queue."
                    ),
                },
                "first_path_contract": {
                    "capability": "Extension publishers assemble one release brief.",
                    "visible_result": "A reviewable release brief.",
                    "events": [{"action": "assemble"}, {"action": "review"}],
                },
            },
            "intent": {"state_object": "Release brief record"},
            "assumptions": [{"statement": "Use one workspace per extension."}],
            "open_questions": [{"question": "Which release channel is first?"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        project_brief_preview={"purpose": "Extension publishers assemble a release brief."},
        rendered_atlas_sources={},
        rendered_component_specs={},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["product_manager"]["checks"]}

    assert checks["first_release_requirements_project_brief"]["status"] == "failed"
    assert checks["first_release_requirements_implementation_handoff"]["status"] == "failed"
    assert "accepted first-release requirements" in checks["first_release_requirements_project_brief"]["issue"]
    assert "accepted first-release requirements" in checks["first_release_requirements_implementation_handoff"]["issue"]


def test_product_manager_lens_accepts_article_free_release_requirement_copy() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": (
                        "Release succeeds when the release brief is reviewable. "
                        "The first release includes one workspace per extension and a review queue."
                    ),
                },
                "first_path_contract": {
                    "capability": "Extension publishers assemble one release brief.",
                    "visible_result": "A reviewable release brief.",
                    "events": [{"action": "assemble"}, {"action": "review"}],
                },
            },
            "intent": {"state_object": "Release brief record"},
            "assumptions": [{"statement": "Use one workspace per extension."}],
            "open_questions": [{"question": "Which release channel is first?"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        project_brief_preview={"boundary": "The first release includes one workspace per extension and review queue."},
        next_steps_preview={"implementation_prompt": "Keep one workspace per extension and review queue in the first coding scope."},
        rendered_atlas_sources={},
        rendered_component_specs={},
        component_registry_preview=(),
        backlog_result={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["product_manager"]["checks"]}

    assert checks["first_release_requirements_project_brief"]["status"] == "passed"
    assert checks["first_release_requirements_implementation_handoff"]["status"] == "passed"


def test_domain_expert_lens_fails_when_high_risk_assumption_is_not_rendered() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": "Release succeeds when assay input, calibration baseline, and uncertainty interval are visible.",
                },
                "first_path_contract": {
                    "capability": "Researcher runs an assay simulation with calibration baseline and uncertainty interval.",
                    "visible_result": "Simulation result with uncertainty interval and baseline comparison.",
                },
            },
            "intent": {
                "state_object": "An assay simulation run records dataset identity, calibration baseline, model version, and uncertainty interval.",
            },
            "assumptions": [
                {
                    "tier": "user_intent",
                    "statement": "Only authorized reviewers may approve safety-sensitive simulation outputs.",
                }
            ],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={
            "Assay Simulation Service": (
                "The assay simulation run records dataset identity, calibration baseline, model version, "
                "uncertainty interval, and baseline comparison for researcher review."
            )
        },
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["domain_expert"]["checks"]}

    assert checks["domain_term_coverage"]["status"] == "passed"
    assert checks["high_risk_assumptions"]["status"] == "failed"
    assert "high-risk accepted assumption coverage" in checks["high_risk_assumptions"]["issue"]


def test_domain_expert_lens_accepts_short_high_risk_assumption_when_all_terms_rendered() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "proof_boundary": "Release succeeds when evidence custody and decision proof are visible.",
                },
                "first_path_contract": {
                    "capability": "Owner reviews evidence custody and decision proof.",
                    "visible_result": "Decision proof.",
                },
            },
            "intent": {
                "state_object": "A report records evidence custody, decision proof, and review status.",
            },
            "assumptions": [
                {
                    "tier": "user_intent",
                    "statement": "The first release records evidence only.",
                }
            ],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={
            "Evidence Review Service": "Evidence custody and decision proof are visible for review."
        },
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={
            "critical_assumptions": ["The first release records evidence only."],
        },
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["domain_expert"]["checks"]}

    assert checks["domain_term_coverage"]["status"] == "passed"
    assert checks["high_risk_assumptions"]["status"] == "passed"


def test_quality_lens_requires_non_empty_external_boundary() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "state_object": "A case record",
                    "internal_systems": [
                        "Case Intake Register records submitted cases.",
                        "Review Decision Board records accepted decisions.",
                    ],
                    "external_systems": [],
                }
            },
            "intent": {"state_object": "A case record", "external_systems": []},
            "components": [
                {"component_id": "case-intake-register", "label": "Case Intake Register"},
                {"component_id": "review-decision-board", "label": "Review Decision Board"},
            ],
            "diagrams": [{"slug": "one"}, {"slug": "two"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={"one": "flowchart TD\nA-->B\n", "two": "flowchart TD\nA-->B\n"},
        rendered_component_specs={},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["architect"]["checks"]}

    assert checks["system_boundary"]["status"] == "failed"
    assert "0 of 0 external system boundary row(s) rendered" in checks["system_boundary"]["evidence"]


def test_quality_lens_requires_each_accepted_external_boundary_in_rendered_artifacts() -> None:
    package = SimpleNamespace(
        proposal={
            "semantic_model": {
                "domain_ontology": {
                    "state_object": "A room request",
                    "internal_systems": ["Room Request Register", "Availability Review Board"],
                    "external_systems": ["Hall Calendar"],
                }
            },
            "intent": {"state_object": "A room request", "external_systems": ["Hall Calendar"]},
            "components": [
                {"component_id": "room-request-register", "label": "Room Request Register"},
                {"component_id": "availability-review-board", "label": "Availability Review Board"},
            ],
            "diagrams": [{"slug": "one"}, {"slug": "two"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={"one": "flowchart TD\nA-->B\n", "two": "flowchart TD\nA-->B\n"},
        rendered_component_specs={},
        component_registry_preview=(),
        next_steps_preview={},
        backlog_result={},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    missing = build_greenfield_quality_lens_report(package)
    missing_check = {row["name"]: row for row in missing["lenses"]["architect"]["checks"]}["system_boundary"]
    assert missing_check["status"] == "failed"

    package.backlog_result = {"idea_files": ["Hall Calendar is an external dependency."]}
    non_architectural = build_greenfield_quality_lens_report(package)
    non_architectural_check = {
        row["name"]: row for row in non_architectural["lenses"]["architect"]["checks"]
    }["system_boundary"]
    assert non_architectural_check["status"] == "failed"

    package.rendered_atlas_sources["one"] = 'flowchart TD\nH["Hall Calendar"]-->A\n'
    covered = build_greenfield_quality_lens_report(package)
    covered_check = {row["name"]: row for row in covered["lenses"]["architect"]["checks"]}["system_boundary"]
    assert covered_check["status"] == "passed"


def test_quality_lens_requires_explicit_prewrite_safety_evidence() -> None:
    package = SimpleNamespace(
        proposal={
            "components": [{"component_id": "case-intake-register", "label": "Case Intake Register"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={"case-intake-register": "# Case Intake Register\n"},
        component_registry_preview=({"component_id": "case-intake-register", "validation_gate": {"status": "passed"}},),
        next_steps_preview={
            "implementation_prompt": "Start B-001 from the accepted product direction with tests and proof.",
            "start_workstream_id": "B-001",
            "verification_commands": ["pytest", "odylith validate plan-workstream-binding"],
            "coding_readiness_gates": ["semantic", "release", "proof", "excluded"],
        },
        backlog_result={"validation_gate": {"status": "passed"}},
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["engineer"]["checks"]}

    assert checks["prewrite_safety"]["status"] == "failed"
    assert checks["component_specs"]["status"] == "passed"
    assert checks["validation_evidence"]["status"] == "passed"


def test_quality_lens_accepts_explicit_prewrite_safety_preview_after_commit() -> None:
    package = SimpleNamespace(
        proposal={
            "components": [{"component_id": "case-intake-register", "label": "Case Intake Register"}],
        },
        release_selector="0.0.1",
        release_workstream_ids=("B-001",),
        rendered_atlas_sources={},
        rendered_component_specs={"case-intake-register": "# Case Intake Register\n"},
        component_registry_preview=({"component_id": "case-intake-register", "validation_gate": {"status": "passed"}},),
        next_steps_preview={
            "implementation_prompt": "Start B-001 from the accepted product direction with tests and proof.",
            "start_workstream_id": "B-001",
            "verification_commands": ["pytest", "odylith validate plan-workstream-binding"],
            "coding_readiness_gates": ["semantic", "release", "proof", "excluded"],
        },
        backlog_result={"validation_gate": {"status": "passed"}},
        prewrite_safety_preview={
            "status": "passed",
            "checks": {
                "validation_gate_passed": True,
                "release_target_dry_run": True,
                "release_assignment_dry_run": True,
            },
        },
        project_brief_preview={},
        accepted_project_preview={},
        compass_memory_preview={},
        release_target_result={},
        release_assignment_result={},
    )

    report = build_greenfield_quality_lens_report(package)
    checks = {check["name"]: check for check in report["lenses"]["engineer"]["checks"]}

    assert checks["prewrite_safety"]["status"] == "passed"
    assert "3 of 3 prewrite safety check(s) passed" in checks["prewrite_safety"]["evidence"]


def test_gate_only_quality_lens_check_stays_non_patchable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal: dict[str, Any] = {"intent": {"title": "Gate Only Lens"}}
    package = GreenfieldCompletionPackage(proposal=proposal, release_selector="0.0.1")

    monkeypatch.setattr(
        "odylith.runtime.domain_intelligence.greenfield_preconfirm_findings.build_greenfield_quality_lens_report",
        lambda _package: {
            "lenses": {
                "engineer": {
                    "checks": [
                        {
                            "name": "validation_evidence",
                            "status": "failed",
                            "issue": "quality lens engineer missing passed validation evidence",
                            "target_path": "prewrite_package.validation",
                            "semantic_node_id": "ArtifactDraftSet.validation",
                            "repairability": "plan_patch",
                            "owner": "prewrite_gate",
                        }
                    ]
                }
            }
        },
    )

    finding = next(
        finding
        for finding in package_review_findings(package, package_issues=())
        if finding.code == "quality_lens_gap"
    )

    assert finding.owner == "prewrite_gate"
    assert finding.target_path == "prewrite_package.validation"
    assert finding.repairability == "unrepairable"


def test_not_applicable_quality_lens_check_does_not_emit_a_blocking_finding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = GreenfieldCompletionPackage(
        proposal={"intent": {"title": "No Explicit Release Requirements"}},
        release_selector="0.0.1",
    )
    monkeypatch.setattr(
        "odylith.runtime.domain_intelligence.greenfield_preconfirm_findings.build_greenfield_quality_lens_report",
        lambda _package: {
            "lenses": {
                "product_manager": {
                    "checks": [
                        {
                            "name": "first_release_requirements_project_brief",
                            "status": "not_applicable",
                            "evidence": "no explicit first-release requirements were accepted",
                            "issue": "",
                        }
                    ]
                }
            }
        },
    )

    findings = package_review_findings(package, package_issues=())

    assert not any(finding.code == "quality_lens_gap" for finding in findings)


def test_quality_lens_repair_contract_has_no_proposal_mutation_engine() -> None:
    source = Path("src/odylith/runtime/domain_intelligence/greenfield_quality_lens_repair.py").read_text(
        encoding="utf-8"
    )

    assert "repair_proposal_for_quality_lens_gaps" not in source
    assert "_ensure_component_topology" not in source
    assert "_ensure_atlas_topology" not in source
    assert "_ensure_measurable_success" not in source
