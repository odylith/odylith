from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    build_greenfield_package_report,
    GreenfieldCompletionPackage,
)
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


ROOT = Path(__file__).resolve().parents[3]
APPLY_PREWRITE_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_prewrite.py"
APPLY_COMPONENTS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_components.py"
APPLY_DIAGRAMS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_diagrams.py"


def test_greenfield_apply_prewrite_component_and_diagram_phases_stay_dedicated() -> None:
    parent_source = APPLY_PREWRITE_PATH.read_text(encoding="utf-8")
    component_source = APPLY_COMPONENTS_PATH.read_text(encoding="utf-8")
    diagram_source = APPLY_DIAGRAMS_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 800
    assert "greenfield_apply_components.render_prewrite_component_specs" in parent_source
    assert "greenfield_apply_components.preview_prewrite_components" in parent_source
    assert "greenfield_apply_diagrams.render_prewrite_atlas_sources" in parent_source
    assert "greenfield_apply_diagrams.allocated_diagram_ids" in parent_source
    for moved in (
        "def render_prewrite_component_specs",
        "def preview_prewrite_components",
        "def component_authoring_prewrite_inputs",
        "def component_dependency_lines",
        "def component_risk_lines",
        "def allocated_diagram_ids",
        "def render_prewrite_atlas_sources",
        "def _dependency_clause_phrase",
        "_COMPONENT_RISK_TOKENS",
    ):
        assert moved not in parent_source
    assert "def render_prewrite_component_specs" in component_source
    assert "def preview_prewrite_components" in component_source
    assert "def component_authoring_prewrite_inputs" in component_source
    assert "def component_dependency_lines" in component_source
    assert "def component_risk_lines" in component_source
    assert "def allocated_diagram_ids" in diagram_source
    assert "def render_prewrite_atlas_sources" in diagram_source


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


def _force_bad_rendered_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        greenfield_apply_components,
        "render_prewrite_component_specs",
        lambda **_kwargs: {"Broken Component": "Broken Component owns maintains state."},
    )


def _prewrite_backlog_result(proposal: dict[str, object]) -> dict[str, object]:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, dict)]
    created = [
        {
            "idea_id": f"B-{index:03d}",
            "title": str(row.get("title", "")),
            "idea_path": f"odylith/radar/source/ideas/test-{index}.md",
        }
        for index, row in enumerate(rows, start=1)
    ]
    return {
        "created": created,
        "idea_files": {
            f"/tmp/test-{index}.md": f"# {row['title']}\n\n{proposal['intent']['first_path']}\n\n{proposal['intent']['proof_boundary']}\n"
            for index, row in enumerate(created, start=1)
        },
        "backlog_index_text": "\n".join(str(row["title"]) for row in created),
        "validation_gate": {"status": "passed"},
    }


def _prewrite_component_preview(proposal: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "component_id": str(row.get("component_id", "")),
            "what_it_is": "Component preview keeps local state, blocked behavior, recovery evidence, release proof, and review context together.",
            "validation_gate": {"status": "passed"},
        }
        for row in proposal.get("components", [])
        if isinstance(row, dict) and str(row.get("release_scope", "")).casefold() not in {"deferred", "out_of_scope", "external"}
    )


def _staged_component_preview(proposal: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for index, row in enumerate(_prewrite_component_preview(proposal), start=1):
        payload = dict(row)
        payload["registry_path"] = (
            f"/tmp/odylith-greenfield-prewrite-test/repo/odylith/registry/source/component_registry.v1.json"
        )
        payload["spec_path"] = (
            f"/tmp/odylith-greenfield-prewrite-test/repo/odylith/registry/source/components/c-{index}/CURRENT_SPEC.md"
        )
        rows.append(payload)
    return tuple(rows)


def _accepted_preview(proposal: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "odylith.accepted_project.v1",
        "origin": "greenfield",
        "proposal": {"semantic_model": proposal["semantic_model"]},
        "validation_gate": {"status": "passed"},
        "created": {
            "workstreams": _prewrite_backlog_result(proposal)["created"],
            "components": list(_prewrite_component_preview(proposal)),
            "diagrams": [f"D-{index:03d}" for index, _row in enumerate(proposal["diagrams"], start=1)],
            "release_selector": "0.0.1",
        },
    }


def _compass_preview(
    proposal: dict[str, object],
    *,
    component_preview: tuple[dict[str, object], ...] | None = None,
) -> dict[str, object]:
    components = component_preview or _prewrite_component_preview(proposal)
    return {
        "kind": "decision",
        "summary": "Accepted greenfield proposal",
        "evidence_tier": "user_intent",
        "work_category": "governance",
        "workstreams": [str(row["idea_id"]) for row in _prewrite_backlog_result(proposal)["created"]],
        "components": [str(row["component_id"]) for row in components],
        "artifacts": [str(row["spec_path"]) for row in components if str(row.get("spec_path", "")).strip()],
    }


def _tribunal_preview() -> dict[str, object]:
    return {
        "status": "passed",
        "version": "greenfield-validation-gate-v1",
        "summary": "Accepted product direction is coherent enough to create project records.",
        "dimensions": {
            "semantic_model": "complete",
            "first_path": "covered",
            "component_contracts": "covered",
            "diagram_graph": "covered",
        },
        "issues": [],
    }


def _next_steps_preview() -> dict[str, object]:
    return {
        "project_workstream_id": "B-001",
        "start_workstream_id": "B-001",
        "release_selector": "0.0.1",
        "implementation_prompt": "Implement the accepted first-path workstream from the semantic model with proof gates.",
        "operator_sequence": [
            "Review the accepted project brief.",
            "Open the first implementation workstream.",
            "Author the first technical plan from its proof obligations.",
        ],
        "coding_readiness_gates": [
            "Accepted first-path contract is understood.",
            "Release boundary is acknowledged.",
            "Verification commands are known.",
        ],
        "verification_commands": ["./.odylith/bin/odylith context --repo-root . B-001"],
    }


def test_greenfield_package_gate_requires_prewrite_atlas_sources(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "rendered Atlas Mermaid sources" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_component_authoring_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_component_specs={"Detached": "# Detached\n"},
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "component authoring previews" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_accepted_project_memory_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "accepted-project memory preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_compass_memory_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            accepted_project_preview=_accepted_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "Compass memory event preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_project_brief_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "project brief preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_tribunal_evidence_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "Tribunal evidence preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_operator_next_steps_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "operator next-steps preview" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_operator_next_steps(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    next_steps = _next_steps_preview()
    next_steps["implementation_prompt"] = (
        "Implement the first slice by accepting actor identity, validation context, and upstream handoff "
        "and producing blocker signal, review rationale, and downstream handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=next_steps,
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "operator next-steps preview leaked Registry contract tuple prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_radar_gate_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    backlog_result["idea_files"] = {
        path: (
            f"{text}\n\nGate: Validate that Build Visit Capture First Path satisfies its local success criteria: "
            "Visit Capture accepts actor identity, validation context, and upstream handoff.\n"
        )
        for path, text in backlog_result["idea_files"].items()
    }

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=backlog_result,
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "prewrite Radar package leaked raw success-metric gate prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_registry_preview_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component_preview = [dict(row) for row in _prewrite_component_preview(proposal)]
    component_preview[0]["what_it_is"] = (
        "Broken preview accepts actor identity, validation context, and upstream handoff and "
        "produces blocker signal, review rationale, and downstream handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=tuple(component_preview),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "prewrite Registry preview leaked Registry contract tuple prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_accepted_project_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    accepted = _accepted_preview(proposal)
    accepted["created"]["components"][0]["summary"] = (
        "Generated memory accepts actor identity, validation context, and upstream handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=accepted,
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "accepted-project memory preview leaked Registry contract tuple prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_staged_paths_in_accepted_project_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component_preview = _staged_component_preview(proposal)
    accepted = _accepted_preview(proposal)
    accepted["created"]["components"] = list(component_preview)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=component_preview,
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=accepted,
            compass_memory_preview=_compass_preview(proposal, component_preview=component_preview),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "accepted-project memory preview contains staged prewrite temp path" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_staged_paths_in_compass_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component_preview = _prewrite_component_preview(proposal)
    compass = _compass_preview(proposal)
    compass["artifacts"] = [
        "/tmp/odylith-greenfield-prewrite-test/repo/odylith/registry/source/components/c-1/CURRENT_SPEC.md"
    ]

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=component_preview,
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=compass,
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "Compass memory event preview contains staged prewrite temp path" in "\n".join(report.issues)


def test_greenfield_prewrite_remaps_component_preview_paths_to_target_repo(tmp_path: Path) -> None:
    staged_root = tmp_path / "stage" / "repo"
    target_root = tmp_path / "target"
    component_items = (
        {
            "component_id": "c-001",
            "registry_path": staged_root / "odylith/registry/source/component_registry.v1.json",
            "spec_path": staged_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md",
        },
    )

    remapped = greenfield_apply_prewrite.remap_prewrite_component_items(
        component_items,
        source_root=staged_root,
        target_root=target_root,
    )

    assert remapped[0]["registry_path"] == str(
        (target_root / "odylith/registry/source/component_registry.v1.json").resolve()
    )
    assert remapped[0]["spec_path"] == str(
        (target_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md").resolve()
    )


def test_greenfield_package_gate_rejects_workstream_preview_without_semantic_proof(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    backlog_result["idea_files"] = {path: "# Detached\n\nUnrelated placeholder text.\n" for path in backlog_result["idea_files"]}

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            backlog_result=backlog_result,
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "prewrite Radar package missing semantic coverage" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_atlas_preview_without_proof_checkpoint(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    atlas_sources = {
        path: "flowchart LR\n  A[Detached placeholder]\n"
        for path in greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal)
    }

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=atlas_sources,
            component_registry_preview=_prewrite_component_preview(proposal),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "proof checkpoint" in "\n".join(report.issues)


def test_greenfield_apply_blocks_bad_rendered_specs_before_governed_writes(tmp_path: Path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _proposal(tmp_path)
    _force_bad_rendered_specs(monkeypatch)

    with pytest.raises(ValueError, match="post-confirm completion"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")) == []
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd")) == []


def test_greenfield_apply_rerenders_prewrite_package_after_repairable_package_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    original = greenfield_apply_components.render_prewrite_component_specs
    calls = 0

    def flaky_render(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"Broken Component": "Broken Component owns maintains state."}
        return original(**kwargs)

    monkeypatch.setattr(greenfield_apply_components, "render_prewrite_component_specs", flaky_render)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert calls >= 2
    assert result["validation_gate"]["status"] == "passed"
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))


def test_greenfield_apply_prewrite_failure_does_not_bootstrap_target_repo(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _force_bad_rendered_specs(monkeypatch)

    with pytest.raises(ValueError, match="post-confirm completion"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not (tmp_path / "odylith").exists()


def test_greenfield_apply_blocks_bad_accepted_project_preview_before_governed_writes(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    monkeypatch.setattr(
        greenfield_apply_prewrite,
        "preview_accepted_project_memory",
        lambda **_kwargs: {"schema_version": "broken", "validation_gate": {"status": "failed"}},
    )

    with pytest.raises(ValueError, match="post-confirm completion"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not (tmp_path / "odylith").exists()


def test_greenfield_apply_uses_dry_run_release_target_preview_before_target_writes(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    original = greenfield_apply_prewrite.release_planning_authoring.ensure_release_selector
    dry_run_calls: list[bool] = []

    def capture_release_selector(**kwargs):
        dry_run_calls.append(bool(kwargs.get("dry_run")))
        return original(**kwargs)

    monkeypatch.setattr(greenfield_apply_prewrite.release_planning_authoring, "ensure_release_selector", capture_release_selector)

    greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert dry_run_calls[:2] == [True, False]


def test_greenfield_apply_bootstraps_target_repo_only_after_package_gate(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert result["validation_gate"]["status"] == "passed"
    assert (tmp_path / "odylith/radar/source/INDEX.md").is_file()
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
