from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from odylith.runtime.artifact_quality.greenfield_quality_lenses import build_greenfield_quality_lens_report
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_GATE_ONLY_CHECKS,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_PROPOSAL_REPAIR_CHECKS,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    QUALITY_LENS_REPAIR_OWNER_BY_CHECK,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    quality_lens_repair_owner,
)
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import (
    repair_proposal_for_quality_lens_gaps,
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


def _failed_lens_report(checks: set[str]) -> dict[str, Any]:
    return {
        "lenses": {
            "all": {
                "checks": [{"name": check, "status": "failed"} for check in sorted(checks)],
            }
        }
    }


def test_quality_lens_repair_declares_every_reviewer_check() -> None:
    check_names = _all_lens_check_names()

    assert set(QUALITY_LENS_REPAIR_OWNER_BY_CHECK) == check_names
    assert QUALITY_LENS_PROPOSAL_REPAIR_CHECKS | QUALITY_LENS_GATE_ONLY_CHECKS == check_names
    assert QUALITY_LENS_PROPOSAL_REPAIR_CHECKS.isdisjoint(QUALITY_LENS_GATE_ONLY_CHECKS)
    assert {quality_lens_repair_owner(check) for check in QUALITY_LENS_PROPOSAL_REPAIR_CHECKS} == {"proposal_repair"}
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

    assert report["lenses"]["product_manager"]["role"] == "Product manager"
    assert product_checks["complete_first_path"]["target_path"] == "semantic_model.first_path_contract"
    assert product_checks["decision_boundary"]["semantic_node_id"] == "SemanticModelIR.decision_boundary"
    assert architect_checks["component_topology"]["surface"] == "registry"
    assert architect_checks["component_topology"]["owner"] == "semantic_model_compiler"


def test_quality_lens_repair_rehydrates_proposal_owned_surface() -> None:
    proposal: dict[str, Any] = {
        "intent": {
            "title": "Field Review Workspace",
            "product_story": "A team needs a clear review path before work expands.",
        },
        "backlog": [{"title": "Review first request"}],
        "components": [],
        "diagrams": [],
        "release_plan": {},
        "validation_strategy": [],
        "project_brief": {},
    }

    changed = repair_proposal_for_quality_lens_gaps(
        proposal,
        quality_lenses=_failed_lens_report(set(QUALITY_LENS_PROPOSAL_REPAIR_CHECKS)),
        release_selector="0.0.1",
    )

    assert changed is True
    assert proposal["intent"]["state_object"]
    assert proposal["intent"]["first_path"]
    assert proposal["intent"]["proof_boundary"]
    assert len(proposal["assumptions"]) >= 2
    assert len(proposal["open_questions"]) >= 1
    assert len(proposal["intent"]["internal_systems"]) >= 2
    assert proposal["intent"]["external_systems"] == []
    assert len(proposal["backlog"][0]["success_metrics"]) >= 3
    assert proposal["release_plan"]["selector"] == "0.0.1"
    assert proposal["release_plan"]["target_workstream_titles"] == ["Review first request"]
    assert len(proposal["components"]) >= 3
    assert all(row["release_scope"] == "first_release" for row in proposal["components"][:3])
    assert len(proposal["diagrams"]) >= 4
    assert all(row.get("mermaid_source", "").startswith("flowchart ") for row in proposal["diagrams"][:4])
    assert len(proposal["project_brief"]["coding_readiness_gates"]) >= 3
    assert proposal["project_brief"]["customization_options"]
    assert any("assumption proof" in row.casefold() for row in proposal["validation_strategy"])


def test_quality_lens_repair_does_not_mutate_gate_only_checks() -> None:
    proposal: dict[str, Any] = {"intent": {"title": "Gate Only"}, "backlog": []}

    changed = repair_proposal_for_quality_lens_gaps(
        proposal,
        quality_lenses=_failed_lens_report(set(QUALITY_LENS_GATE_ONLY_CHECKS)),
        release_selector="0.0.1",
    )

    assert changed is False
    assert proposal == {"intent": {"title": "Gate Only"}, "backlog": []}
