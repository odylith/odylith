from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import collect_rendered_package_artifacts
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import proposal_memory
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import (
    build_greenfield_package_report,
    GreenfieldCompletionPackage,
    _component_preview_path_fidelity_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_package_hygiene import prewrite_path_leak_issues
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from tests.unit.runtime.greenfield_proposal_fixtures import _canonical_model_authored_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import commit_precompiled_greenfield_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


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
    assert parent_source.count("seal_staged_greenfield_create(") == 1
    assert "greenfield_source_casing" not in parent_source
    assert "proposal_with_component_brief_gate" not in parent_source
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
    for retired in (
        "def component_dependency_lines",
        "def component_risk_lines",
        "def _dependency_clause_phrase",
        "_COMPONENT_RISK_TOKENS",
    ):
        assert retired not in component_source
    assert "def allocated_diagram_ids" in diagram_source
    assert "def render_prewrite_atlas_sources" in diagram_source


def test_prewrite_safety_evidence_records_dry_run_preview_before_commit() -> None:
    evidence = greenfield_apply_prewrite.prewrite_safety_evidence(
        validation_gate={"status": "passed"},
        release_target_result={"dry_run": True, "release_id": "release-0-0-1", "selector": "0.0.1"},
        release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
        release_selector="0.0.1",
    )

    assert evidence["status"] == "passed"
    assert evidence["checks"] == {
        "validation_gate_passed": True,
        "release_target_dry_run": True,
        "release_assignment_dry_run": True,
    }


def _proposal(tmp_path: Path) -> dict[str, object]:
    return _canonical_model_authored_greenfield_fixture(tmp_path)


def test_greenfield_prewrite_rejects_unsealed_proposal_before_staging(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="prewrite accepts only sealed model-authored proposals",
    ):
        greenfield_apply_prewrite.build_prewrite_completion_package(
            root=tmp_path,
            proposal={},
            release_selector="0.0.1",
            backlog_args=(),
            validation_gate={"status": "passed"},
            release_assignment_note="unused",
        )

    assert list(tmp_path.iterdir()) == []


def test_greenfield_prewrite_builds_complete_authored_surface_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)
    proposal = _proposal(tmp_path)
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")

    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_prewrite.release_assignment_note(selector="0.0.1"),
    )

    assert prewrite.package.prewrite_safety_preview["status"] == "passed"
    assert prewrite.package.prewrite_safety_preview["checks"] == {
        "validation_gate_passed": True,
        "release_target_dry_run": True,
        "release_assignment_dry_run": True,
    }
    assert prewrite.package.surface_refresh_preview["status"] == "passed"
    assert prewrite.package.surface_refresh_preview["surfaces"] == [
        "radar",
        "registry",
        "atlas",
        "compass",
        "tooling_shell",
    ]
    assert prewrite.package.component_registry_preview
    assert prewrite.package.traceability_plan is not None
    assert prewrite.package.traceability_plan.workstreams
    assert prewrite.package.traceability_plan.workstreams[0].idea_id == "B-001"
    assert prewrite.package.traceability_plan.component_workstreams
    assert len(prewrite.package.atlas_review_date) == len("2026-07-07")
    assert len(prewrite.package.atlas_diagram_ids) == len(prewrite.package.rendered_atlas_sources)
    assert len(prewrite.package.atlas_catalog_rows) == len(prewrite.package.rendered_atlas_sources)
    assert {
        str(row.get("diagram_id", "")).strip()
        for row in prewrite.package.atlas_catalog_rows
    } == set(prewrite.package.atlas_diagram_ids)
    assert all(
        not Path(path).is_absolute()
        for row in prewrite.package.atlas_catalog_rows
        for path in row.get("related_backlog", [])
    )
    assert "odylith-greenfield-prewrite" not in json.dumps(prewrite.package.atlas_catalog_rows)
    accepted_at = str(prewrite.package.accepted_project_preview.get("accepted_at", "")).strip()
    assert accepted_at and accepted_at != "prewrite"
    assert prewrite.package.compass_memory_preview["ts_iso"] == accepted_at
    title = str(proposal["intent"]["title"])
    assert prewrite.package.project_brief_record_text.startswith(f"# {title} Project Brief")
    assert f"- accepted_at: {accepted_at}" in prewrite.package.project_brief_record_text
    assert all(not Path(str(token)).is_absolute() for token in prewrite.package.compass_memory_preview["artifacts"])
    assert all(
        isinstance(row.get("implementation_handoff"), dict) and row["implementation_handoff"]
        for row in prewrite.package.component_registry_preview
    )


def _disable_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        lambda **_kwargs: surface_refresh_preview_fixture(),
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "test_refresh_stub": True},
    )
    monkeypatch.setattr(
        greenfield_component_commit.component_compiled_commit.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
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
    first_path = str(proposal["intent"]["first_path"])
    proof_boundary = str(proposal["intent"]["proof_boundary"])
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
            f"/tmp/test-{index}.md": (
                f"# {row['title']}\n\n"
                f"{_fixture_first_path_line(row['title'], first_path, index=index)}\n\n"
                f"{_fixture_proof_line(row['title'], proof_boundary, index=index, total=len(created))}\n"
            )
            for index, row in enumerate(created, start=1)
        },
        "backlog_index_text": "\n".join(str(row["title"]) for row in created),
        "validation_gate": {"status": "passed"},
    }


def _fixture_first_path_line(title: object, first_path: str, *, index: int) -> str:
    if index == 1:
        return f"Accepted first path: {first_path}"
    return f"{title} supports the accepted first path through its scoped state, handoff, or evidence responsibility."


def _fixture_proof_line(title: object, proof_boundary: str, *, index: int, total: int) -> str:
    if index == total:
        return f"Release proof for {title}: {proof_boundary}"
    return f"{title} contributes evidence toward the accepted proof boundary without restating every release condition."


def _prewrite_component_preview(proposal: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "component_id": str(row.get("component_id", "")),
            "label": str(row.get("label", "")),
            "what_it_is": "Component preview keeps local state, blocked behavior, recovery evidence, release proof, and review context together.",
            "implementation_handoff": {
                "workstream_id": "B-001",
                "workstream_title": "Prove the accepted first path",
                "implementation_prompt": "Implement the accepted first path from the compiled transaction package.",
            },
            "authoring_input": {
                "component_id": str(row.get("component_id", "")),
                "label": str(row.get("label", "")),
                "path": str(row.get("intended_path", "")),
                "kind": str(row.get("kind", "service") or "service"),
                "category": "application",
                "qualification": str(row.get("qualification", "candidate") or "candidate"),
                "owner": "repo",
                "status": str(row.get("status", "planned") or "planned"),
                "product_layer": "application",
                "sources": ("user_intent",),
                "workstreams": ("B-001",),
                "diagrams": (),
                "responsibility": str(row.get("responsibility", "") or row.get("boundary", "")),
                "boundary": str(row.get("boundary", "")),
                "dependencies": (),
                "interfaces": (),
                "validation": tuple(row.get("validation", ()) if isinstance(row.get("validation"), list) else ()),
                "risks": (),
                "implementation_handoff": {
                    "workstream_id": "B-001",
                    "workstream_title": "Prove the accepted first path",
                    "implementation_prompt": "Implement the accepted first path from the compiled transaction package.",
                },
                "component_contract": row.get("component_contract") if isinstance(row.get("component_contract"), dict) else {},
            },
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
        "start_workstream_title": "Municipal Permit Review First Slice",
        "release_selector": "0.0.1",
        "implementation_prompt": (
            "Start B-001 Municipal Permit Review First Slice from the accepted first-path workstream. Implement the "
            "smallest source-backed path where a coordinator imports one permit application, a zoning reviewer records "
            "a zoning check, the applicant submits one revision, and a supervisor reviews the traceable decision package "
            "with proof gates, blocked-input behavior, and replayable validation evidence."
        ),
        "operator_sequence": [
            "Review the accepted project brief.",
            "Open the first implementation workstream.",
            "Author the first technical plan from its proof obligations.",
        ],
        "coding_readiness_gates": [
            "Accepted first-path contract is understood.",
            "Release boundary is acknowledged.",
            "Verification commands are known.",
            "Excluded scope is explicitly preserved.",
        ],
        "verification_commands": [
            "./.odylith/bin/odylith context --repo-root . B-001",
            "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
        ],
    }


def _project_dashboard_preview(
    proposal: dict[str, object],
    *,
    accepted_project_preview: dict[str, object],
    source_launch_context: dict[str, object],
) -> dict[str, object]:
    dashboard_proposal = dict(proposal)
    dashboard_proposal["_accepted_project"] = accepted_project_preview
    dashboard_proposal["_source_launch"] = source_launch_context
    return build_greenfield_payload(proposal=dashboard_proposal, repo_root=ROOT)


def _package_for_quality_report(
    proposal: dict[str, object],
    **overrides: object,
) -> GreenfieldCompletionPackage:
    next_steps_preview = (
        overrides.get("next_steps_preview")
        if isinstance(overrides.get("next_steps_preview"), dict)
        else _next_steps_preview()
    )
    accepted_project_preview = (
        overrides.get("accepted_project_preview")
        if isinstance(overrides.get("accepted_project_preview"), dict)
        else _accepted_preview(proposal)
    )
    values: dict[str, object] = {
        "release_selector": "0.0.1",
        "rendered_atlas_sources": greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
        "atlas_review_date": "2026-07-07",
        "atlas_diagram_ids": tuple(
            f"D-{index:03d}"
            for index, row in enumerate(proposal.get("diagrams", []), start=1)
            if isinstance(row, dict)
        ),
        "component_registry_preview": _prewrite_component_preview(proposal),
        "project_brief_preview": proposal["project_brief"],
        "tribunal_preview": _tribunal_preview(),
        "accepted_project_preview": accepted_project_preview,
        "project_dashboard_preview": _project_dashboard_preview(
            proposal,
            accepted_project_preview=accepted_project_preview,
            source_launch_context=next_steps_preview,
        ),
        "compass_memory_preview": _compass_preview(proposal),
        "next_steps_preview": next_steps_preview,
        "backlog_result": _prewrite_backlog_result(proposal),
        "surface_refresh_preview": surface_refresh_preview_fixture(),
        "prewrite_safety_preview": {
            "status": "passed",
            "checks": {
                "validation_gate_passed": True,
                "release_target_dry_run": True,
                "release_assignment_dry_run": True,
            },
        },
        "release_target_result": {"dry_run": True, "release": {"release_id": "release-test"}},
        "release_assignment_result": {"dry_run": True, "workstream_ids": ["B-001"]},
        "release_workstream_ids": ("B-001",),
    }
    values["atlas_catalog_rows"] = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=ROOT,
        rows=tuple(row for row in proposal.get("diagrams", []) if isinstance(row, dict)),
        diagram_ids=values["atlas_diagram_ids"],  # type: ignore[arg-type]
        traceability_plan=SimpleNamespace(diagram_links=()),
        review_date=str(values["atlas_review_date"]),
    )
    values.update(overrides)
    if "project_dashboard_preview" not in overrides:
        values["project_dashboard_preview"] = _project_dashboard_preview(
            proposal,
            accepted_project_preview=values["accepted_project_preview"],  # type: ignore[arg-type]
            source_launch_context=values["next_steps_preview"],  # type: ignore[arg-type]
        )
    return GreenfieldCompletionPackage(proposal=proposal, **values)


def test_greenfield_package_report_rejects_missing_surface_refresh_proof(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, surface_refresh_preview=None)
    )

    assert report.status == "failed"
    assert "missing compiled pre-confirm surface refresh proof" in report.issues


def test_greenfield_package_gate_requires_prewrite_atlas_sources(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_prewrite_backlog_result(proposal),
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
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "operator next-steps preview" in "\n".join(report.issues)


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

    assert remapped[0]["registry_path"] == "odylith/registry/source/component_registry.v1.json"
    assert remapped[0]["spec_path"] == "odylith/registry/source/components/c-001/CURRENT_SPEC.md"


def test_greenfield_accepted_project_preview_relativizes_target_paths_against_target_root(tmp_path: Path) -> None:
    staged_root = tmp_path / "stage" / "repo"
    target_root = tmp_path / "target"
    accepted = greenfield_apply_prewrite.preview_accepted_project_memory(
        root=staged_root,
        target_root=target_root,
        proposal=_proposal(staged_root),
        backlog_result={
            "created": [
                {
                    "idea_id": "B-001",
                    "idea_path": target_root / "odylith/radar/source/ideas/2026-08/case-review.md",
                }
            ]
        },
        component_items=(
            {
                "component_id": "case-review",
                "spec_path": target_root
                / "odylith/registry/source/components/case-review/CURRENT_SPEC.md",
            },
        ),
        release_selector="0.0.1",
        release_target_result=None,
        release_assignment_result=None,
        validation_gate={"status": "passed"},
    )

    assert accepted["created"]["workstreams"][0]["idea_path"] == (
        "odylith/radar/source/ideas/2026-08/case-review.md"
    )
    assert accepted["created"]["components"][0]["spec_path"] == (
        "odylith/registry/source/components/case-review/CURRENT_SPEC.md"
    )
    assert prewrite_path_leak_issues("accepted-project memory preview", accepted) == []


def test_greenfield_component_memory_path_fidelity_treats_alias_roots_as_same_path(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    alias_root = tmp_path / "alias"
    real_root.mkdir()
    alias_root.symlink_to(real_root, target_is_directory=True)
    component_id = "c-001"
    expected = (
        {
            "component_id": component_id,
            "registry_path": str(real_root / "odylith/registry/source/component_registry.v1.json"),
            "spec_path": str(real_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md"),
        },
    )
    actual = (
        {
            "component_id": component_id,
            "registry_path": str(alias_root / "odylith/registry/source/component_registry.v1.json"),
            "spec_path": str(alias_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md"),
        },
    )

    assert _component_preview_path_fidelity_issues(
        owner="accepted-project memory preview",
        expected=expected,
        actual=actual,
    ) == []

    foreign_root = tmp_path / "foreign"
    assert _component_preview_path_fidelity_issues(
        owner="accepted-project memory preview",
        expected=expected,
        actual=(
            {
                "component_id": component_id,
                "registry_path": str(foreign_root / "odylith/registry/source/component_registry.v1.json"),
                "spec_path": str(foreign_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md"),
            },
        ),
    ) == [
        "accepted-project memory preview component `c-001` registry_path drifted from Registry prewrite output",
        "accepted-project memory preview component `c-001` spec_path drifted from Registry prewrite output",
    ]


def test_greenfield_accepted_memory_preserves_structural_path_underscores(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component = {
        "component_id": "variant-case-ledger",
        "label": "Variant Case Ledger",
        "registry_path": str(tmp_path / "odylith/registry/source/component_registry.v1.json"),
        "spec_path": str(tmp_path / "odylith/registry/source/components/variant-case-ledger/CURRENT_SPEC.md"),
    }

    accepted = proposal_memory.build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=(),
        component_items=(component,),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-genomic-variant-triage-0-0-1",
        validation_gate={"status": "passed"},
        source_launch_context=None,
        accepted_at="prewrite",
        repo_root=tmp_path,
    )
    event = proposal_memory.build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=(),
        component_items=(component,),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-genomic-variant-triage-0-0-1",
        repo_root=tmp_path,
    )

    created_component = accepted["created"]["components"][0]
    assert created_component["registry_path"] == "odylith/registry/source/component_registry.v1.json"
    assert created_component["spec_path"] == "odylith/registry/source/components/variant-case-ledger/CURRENT_SPEC.md"
    assert created_component["spec_path"] in event["artifacts"]


def test_greenfield_prewrite_hygiene_rejects_all_ephemeral_absolute_paths() -> None:
    issues = prewrite_path_leak_issues(
        "accepted-project memory preview",
        {"source": "/private/tmp/odylith-quality-test/odylith/runtime/source/accepted-project.v1.json"},
    )

    assert issues == [
        "accepted-project memory preview contains staged prewrite temp path(s) instead of durable target paths"
    ]


def test_greenfield_accepted_memory_rebases_staged_workstream_paths(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    accepted = proposal_memory.build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=(
            {
                "idea_id": "B-001",
                "idea_path": str(tmp_path / "odylith/radar/source/ideas/2026-07/release-notes.md"),
            },
        ),
        component_items=(),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-release-notes-0-0-1",
        validation_gate={"status": "passed"},
        accepted_at="prewrite",
        repo_root=tmp_path,
    )

    assert accepted["created"]["workstreams"][0]["idea_path"] == "odylith/radar/source/ideas/2026-07/release-notes.md"


def test_greenfield_apply_blocks_bad_rendered_specs_before_governed_writes(tmp_path: Path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _proposal(tmp_path)
    _force_bad_rendered_specs(monkeypatch)

    with pytest.raises(ValueError, match="could not prepare a creation-ready package"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")) == []
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd")) == []


def test_greenfield_apply_commits_prewrite_atlas_source_not_regenerated_drift(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        model_authoring_receipt=proposal.get("_test_model_authoring_receipt"),
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    original_allocated_diagram_ids = greenfield_apply_diagrams.allocated_diagram_ids
    target_allocation_calls = 0

    def fail_after_prewrite_allocation(*args, **kwargs):
        nonlocal target_allocation_calls
        call_root = Path(args[0]).resolve() if args else Path()
        if call_root == tmp_path.resolve():
            target_allocation_calls += 1
            raise AssertionError("post-confirm write must consume compiled diagram ids")
        return original_allocated_diagram_ids(*args, **kwargs)

    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "validated_mermaid_source",
        lambda _row: 'flowchart LR\n  external1["Optional"]\n',
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "allocated_diagram_ids",
        fail_after_prewrite_allocation,
    )

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    atlas_text = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "odylith/atlas/source").glob("*.mmd"))
    assert result["commit_manifest"]["status"] == "passed"
    assert target_allocation_calls == 0
    assert '["Optional"]' not in atlas_text


def test_greenfield_commit_does_not_rematerialize_component_specs_after_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        model_authoring_receipt=proposal.get("_test_model_authoring_receipt"),
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    materialize_calls = 0

    def fail_materialization(**_kwargs):
        nonlocal materialize_calls
        materialize_calls += 1
        raise AssertionError("post-confirm commit must consume sealed component specs")

    monkeypatch.setattr(
        greenfield_component_commit,
        "materialize_compiled_component_from_preview",
        fail_materialization,
    )

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    specs = list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert result["commit_manifest"]["status"] == "passed"
    assert materialize_calls == 0
    assert specs
    assert all("owns maintains state" not in path.read_text(encoding="utf-8") for path in specs)


def test_greenfield_commit_does_not_regenerate_project_brief_after_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        model_authoring_receipt=proposal.get("_test_model_authoring_receipt"),
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    writer_calls = 0

    def fail_project_brief_writer(**_kwargs):
        nonlocal writer_calls
        writer_calls += 1
        raise AssertionError("post-confirm commit must consume the sealed project brief")

    monkeypatch.setattr(
        proposal_memory,
        "_write_compiled_project_brief_source",
        fail_project_brief_writer,
    )

    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    project_brief_path = tmp_path / "odylith/runtime/source/project-brief.v1.md"
    assert writer_calls == 0
    assert project_brief_path.read_text(encoding="utf-8") == transaction.prewrite_package.project_brief_record_text


def test_greenfield_prewrite_failure_does_not_commit_governed_records(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _force_bad_rendered_specs(monkeypatch)

    with pytest.raises(ValueError, match="could not prepare a creation-ready package"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_blocks_bad_accepted_project_preview_before_governed_writes(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    monkeypatch.setattr(
        greenfield_apply_prewrite,
        "preview_accepted_project_memory",
        lambda **_kwargs: {"schema_version": "broken", "validation_gate": {"status": "failed"}},
    )

    with pytest.raises(ValueError, match="could not prepare a creation-ready package"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_commit_does_not_rebuild_release_target_after_confirmation(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    original = greenfield_apply_prewrite.release_planning_authoring.ensure_release_selector
    preconfirm_calls: list[bool] = []

    def capture_release_selector(**kwargs):
        preconfirm_calls.append(bool(kwargs.get("dry_run")))
        return original(**kwargs)

    monkeypatch.setattr(greenfield_apply_prewrite.release_planning_authoring, "ensure_release_selector", capture_release_selector)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        model_authoring_receipt=proposal.get("_test_model_authoring_receipt"),
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def fail_release_rebuild(**_kwargs):
        raise AssertionError("post-confirm commit must consume the sealed release target")

    monkeypatch.setattr(
        greenfield_apply_prewrite.release_planning_authoring,
        "ensure_release_selector",
        fail_release_rebuild,
    )
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    assert preconfirm_calls


def test_greenfield_apply_bootstraps_target_repo_only_after_package_gate(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert result["validation_gate"]["status"] == "passed"
    assert (tmp_path / "odylith/radar/source/INDEX.md").is_file()
    project_brief_path = tmp_path / "odylith/runtime/source/project-brief.v1.md"
    assert project_brief_path.is_file()
    assert result["memory"]["project_brief"] == str(project_brief_path)
    project_brief_text = project_brief_path.read_text(encoding="utf-8")
    assert "## Brief" in project_brief_text
    assert "outcome:" in project_brief_text
    assert "\n## Brief\n" in project_brief_text
    assert "\n## Project Design Board\n" in project_brief_text
    assert "\n## Governance Package\n" in project_brief_text
    assert len(project_brief_text.splitlines()) >= 20
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
