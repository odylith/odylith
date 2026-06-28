from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.artifact_quality.greenfield_quality_lenses import build_greenfield_quality_lens_report
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_findings import package_review_findings
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
        program_result={},
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
        program_result={},
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
        program_result={},
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
        program_result={},
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


def test_gate_only_quality_lens_check_stays_non_patchable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal: dict[str, Any] = {"intent": {"title": "Gate Only Lens"}}
    package = GreenfieldCompletionPackage(proposal=proposal, release_selector="0.0.1")

    monkeypatch.setattr(
        "odylith.runtime.domain_intelligence.greenfield_post_confirm_findings.build_greenfield_quality_lens_report",
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


def test_quality_lens_repair_contract_has_no_proposal_mutation_engine() -> None:
    source = Path("src/odylith/runtime/domain_intelligence/greenfield_quality_lens_repair.py").read_text(
        encoding="utf-8"
    )

    assert "repair_proposal_for_quality_lens_gaps" not in source
    assert "_ensure_component_topology" not in source
    assert "_ensure_atlas_topology" not in source
    assert "_ensure_measurable_success" not in source
