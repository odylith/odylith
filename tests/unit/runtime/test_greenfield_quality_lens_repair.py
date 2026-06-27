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
