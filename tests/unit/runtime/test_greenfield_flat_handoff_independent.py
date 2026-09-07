"""Independent controls for flat delivery selection and consumer handoff scope.

The synthetic provider design changes before custody is sealed. These tests prove
allocation and projection integrity, not live-provider semantic quality.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import (
    greenfield_cli_output,
    greenfield_experience,
    greenfield_programs,
    greenfield_traceability,
)
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import (
    preview_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_completion_types import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import GreenfieldModelAuthoringError
from odylith.runtime.domain_intelligence.greenfield_preconfirm_handoff_quality import (
    next_steps_preview_issues,
    project_dashboard_preview_issues,
)
from tests.unit.runtime import greenfield_model_authoring_fixtures as authoring_fixtures
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
)


IDS_BY_KEY = {
    "test-work-1": "B-041", "test-work-2": "B-009",
    "test-work-3": "B-120", "test-work-4": "B-007",
}
EXPECTED_TARGET = {
    "workstream_id": "B-120",
    "workstream_title": "Implement structural test boundary 3",
    "deliverable": "Implement the exact-value boundary 3.",
    "verification": "An independent read returns the test value from boundary 3.",
    "component_refs": ("test-boundary-3",),
}


def _allocated_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, cyclic_design: bool = False,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    original_design = authoring_fixtures.structural_design_fixture

    def forward_fork_design(*args: Any, **kwargs: Any) -> dict[str, Any]:
        design = original_design(*args, **kwargs)
        rows = design["workstreams"]
        rows[2]["depends_on"] = []
        rows[3]["depends_on"] = ["test-work-2"]
        if cyclic_design:
            rows[0]["depends_on"] = ["test-work-4"]
        design["workstreams"] = list(reversed(rows))
        return design

    monkeypatch.setattr(authoring_fixtures, "structural_design_fixture", forward_fork_design)
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    created = []
    for row in proposal["backlog"]:
        key = row["provisional_workstream_contract"]["provisional_workstream"]["key"]
        idea_id = IDS_BY_KEY[key]
        created.append({
            "idea_id": idea_id, "title": row["title"],
            "idea_path": str(tmp_path / f"{idea_id}.md"),
        })
    return proposal, created


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("allocation_order", [(0, 1, 2, 3), (3, 2, 1, 0), (2, 0, 3, 1)])
@pytest.mark.parametrize("release_order", [
    ("B-007", "B-009", "B-041", "B-120"),
    ("B-041", "B-120", "B-007", "B-009"),
])
def test_dependency_root_is_not_an_allocation_position_or_numeric_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    allocation_order: tuple[int, ...], release_order: tuple[str, ...],
) -> None:
    proposal, created = _allocated_fixture(tmp_path, monkeypatch)
    before = _files(tmp_path)
    selected = greenfield_traceability.first_executable_workstream(
        proposal=proposal, created_backlog=[created[index] for index in allocation_order],
        first_release_workstreams=release_order,
    )
    assert selected.idea_id == "B-120"
    assert selected.title == "Implement structural test boundary 3"
    assert selected.row["provisional_workstream_contract"]["provisional_workstream"]["depends_on"] == []
    assert _files(tmp_path) == before


def test_closed_release_subset_selects_its_own_dependency_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal, created = _allocated_fixture(tmp_path, monkeypatch)
    selected = greenfield_traceability.first_executable_workstream(
        proposal=proposal, created_backlog=created,
        first_release_workstreams=("B-009", "B-041"),
    )
    assert selected.idea_id == "B-041"
    assert selected.title == "Implement structural test boundary 1"


def test_release_membership_does_not_reinsert_the_first_allocated_workstream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal, created = _allocated_fixture(tmp_path, monkeypatch)
    proposal["release_plan"]["target_workstream_titles"] = [
        "Implement structural test boundary 2", "Implement structural test boundary 1",
    ]
    before = _files(tmp_path)
    release_ids = greenfield_programs.first_release_workstream_ids(
        proposal=proposal, created_backlog=created,
    )
    assert created[0]["idea_id"] == "B-007"
    assert release_ids == ["B-009", "B-041"]
    assert greenfield_traceability.first_executable_workstream(
        proposal=proposal, created_backlog=created, first_release_workstreams=release_ids,
    ).idea_id == "B-041"
    assert _files(tmp_path) == before


def test_cyclic_provider_design_cannot_reach_a_sealed_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(GreenfieldModelAuthoringError, match="prerequisites contain a cycle"):
        _allocated_fixture(tmp_path, monkeypatch, cyclic_design=True)
    assert not (tmp_path / "odylith").exists()


@pytest.mark.parametrize("corruption", [
    "missing_allocation", "duplicate_allocation", "duplicate_id", "duplicate_path",
    "unknown_title", "duplicate_title", "empty_release", "unknown_release_id",
    "duplicate_release_id", "prerequisite_outside_release",
])
def test_invalid_allocation_or_open_release_rejects_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str,
) -> None:
    proposal, created = _allocated_fixture(tmp_path, monkeypatch)
    release_ids = list(IDS_BY_KEY.values())
    if corruption == "missing_allocation":
        created.pop()
    elif corruption == "duplicate_allocation":
        created.append(dict(created[0]))
    elif corruption in {"duplicate_id", "duplicate_path", "duplicate_title"}:
        key = {"duplicate_id": "idea_id", "duplicate_path": "idea_path", "duplicate_title": "title"}[corruption]
        created[-1][key] = created[0][key]
    elif corruption == "unknown_title":
        created[-1]["title"] = "Implement an unallocated boundary"
    elif corruption == "empty_release":
        release_ids = []
    elif corruption == "unknown_release_id":
        release_ids.append("B-999")
    elif corruption == "duplicate_release_id":
        release_ids.append("B-041")
    else:
        release_ids = ["B-007", "B-120"]
    before = _files(tmp_path)
    with pytest.raises(ValueError):
        greenfield_traceability.first_executable_workstream(
            proposal=proposal, created_backlog=created, first_release_workstreams=release_ids,
        )
    assert _files(tmp_path) == before


def _project_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[GreenfieldCompletionPackage, dict[str, Any], dict[str, Any]]:
    proposal, created = _allocated_fixture(tmp_path, monkeypatch)
    created = [created[index] for index in (2, 0, 3, 1)]
    release_ids = ("B-009", "B-041", "B-007", "B-120")
    next_steps = greenfield_experience.build_next_steps(
        proposal=proposal, backlog_result={"created": created},
        first_release_workstreams=release_ids, release_selector="0.0.1",
    )
    dashboard = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal,
        accepted_project_preview={"created": {"workstreams": created}},
        source_launch_context=next_steps,
    )
    return GreenfieldCompletionPackage(
        proposal=proposal, release_selector="0.0.1", backlog_result={"created": created},
        release_workstream_ids=release_ids, next_steps_preview=next_steps,
        project_dashboard_preview=dashboard,
    ), next_steps, dashboard


def test_project_and_cli_bind_one_selected_slice_separately_from_full_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    package, next_steps, dashboard = _project_package(tmp_path, monkeypatch)
    assert next_steps["implementation_target"] == EXPECTED_TARGET
    assert next_steps["first_release_workstream_ids"] == ["B-009", "B-041", "B-007", "B-120"]
    assert "project_workstream_id" not in next_steps
    assert "project_first_prompt" not in next_steps
    assert package.proposal["intent"]["proof_boundary"] in next_steps["release_validation_gates"]
    assert EXPECTED_TARGET["verification"] in next_steps["validation_gates"]
    expected_titles = {
        "B-041": "Implement structural test boundary 1",
        "B-009": "Implement structural test boundary 2",
        "B-120": "Implement structural test boundary 3",
        "B-007": "Implement structural test boundary 4",
    }
    assert {row[3]: row[0] for row in dashboard["jobs"]} == expected_titles
    assert {key: dashboard["governance_titles"][key] for key in expected_titles} == expected_titles
    for prompt in dashboard["host_handoff_prompts"]:
        bindings = prompt["contract"]["fact_bindings"]
        assert bindings["implementation_target"] == EXPECTED_TARGET
        assert tuple(bindings["first_release_workstream_refs"]) == package.release_workstream_ids
        if prompt["step_id"] in {"create_plan", "build_slice", "prove_behavior"}:
            assert "B-120" in prompt["prompt"]
    greenfield_cli_output._print_next_steps(next_steps)
    output = capsys.readouterr().out
    assert "B-120 Implement structural test boundary 3" in output
    assert EXPECTED_TARGET["deliverable"] in output
    assert "project umbrella" not in output.lower()
    assert "child workstream" not in output.lower()
    assert next_steps_preview_issues(package, next_steps, semantic_checks=False) == []
    assert project_dashboard_preview_issues(package, dashboard, model_authored=True) == []


@pytest.mark.parametrize("corruption", [
    "other_ready_root", "title", "deliverable", "verification", "component_refs",
])
def test_preconfirm_rejects_correlated_target_drift_even_when_producer_copies_agree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str,
) -> None:
    package, next_steps, dashboard = _project_package(tmp_path, monkeypatch)
    assert next_steps_preview_issues(package, next_steps, semantic_checks=False) == []
    assert project_dashboard_preview_issues(package, dashboard, model_authored=True) == []
    wrong_target = deepcopy(EXPECTED_TARGET)
    if corruption == "other_ready_root":
        wrong_target = {
            "workstream_id": "B-041", "workstream_title": "Implement structural test boundary 1",
            "deliverable": "Implement the exact-value boundary 1.",
            "verification": "An independent read returns the test value from boundary 1.",
            "component_refs": ("test-boundary-1",),
        }
    elif corruption == "component_refs":
        wrong_target["component_refs"] = ("test-boundary-1",)
    else:
        key = "workstream_title" if corruption == "title" else corruption
        wrong_target[key] = "Implement an unselected delivery boundary."
    next_steps["implementation_target"] = wrong_target
    next_steps["start_workstream_id"] = wrong_target["workstream_id"]
    next_steps["start_workstream_title"] = wrong_target["workstream_title"]
    readiness_target = next_steps["coding_readiness_contract"]["implementation_target"]
    readiness_target["workstream_id"] = wrong_target["workstream_id"]
    readiness_target["workstream_title"] = wrong_target["workstream_title"]
    next_steps["verification_commands"] = [
        command.replace("B-120", wrong_target["workstream_id"])
        for command in next_steps["verification_commands"]
    ]
    for field in ("implementation_prompt", "project_review_prompt"):
        for key in ("workstream_id", "workstream_title", "deliverable", "verification"):
            next_steps[field] = next_steps[field].replace(EXPECTED_TARGET[key], wrong_target[key])
    for prompt in dashboard["host_handoff_prompts"]:
        bindings = prompt["contract"]["fact_bindings"]
        bindings["implementation_target"] = deepcopy(wrong_target)
        bindings["verification_commands"] = tuple(next_steps["verification_commands"])
        for key in ("workstream_id", "workstream_title", "deliverable", "verification"):
            prompt["prompt"] = prompt["prompt"].replace(EXPECTED_TARGET[key], wrong_target[key])
    before = _files(tmp_path)
    assert any("canonical implementation target" in issue for issue in next_steps_preview_issues(
        package, next_steps, semantic_checks=False,
    ))
    assert any("canonical implementation target" in issue for issue in project_dashboard_preview_issues(
        package, dashboard, model_authored=True,
    ))
    assert _files(tmp_path) == before


@pytest.mark.parametrize("surface", ["create_plan", "build_slice", "prove_behavior", "cli"])
@pytest.mark.parametrize("field", ["workstream_id", "deliverable", "verification"])
@pytest.mark.parametrize("damage", ["remove", "replace"])
def test_preconfirm_rejects_prompt_only_selected_scope_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    surface: str, field: str, damage: str,
) -> None:
    package, next_steps, dashboard = _project_package(tmp_path, monkeypatch)
    assert next_steps_preview_issues(package, next_steps, semantic_checks=False) == []
    assert project_dashboard_preview_issues(package, dashboard, model_authored=True) == []
    binding_snapshots = [
        deepcopy(row["contract"]["fact_bindings"])
        for row in dashboard["host_handoff_prompts"]
    ]
    replacements = {
        "workstream_id": "B-041",
        "deliverable": "Implement the exact-value boundary 1.",
        "verification": "An independent read returns the test value from boundary 1.",
    }
    replacement = "" if damage == "remove" else replacements[field]
    before = _files(tmp_path)
    if surface == "cli":
        original = next_steps["implementation_prompt"]
        assert EXPECTED_TARGET[field] in original
        next_steps["implementation_prompt"] = original.replace(EXPECTED_TARGET[field], replacement)
        issues = next_steps_preview_issues(package, next_steps, semantic_checks=False)
    else:
        row = next(row for row in dashboard["host_handoff_prompts"] if row["step_id"] == surface)
        assert EXPECTED_TARGET[field] in row["prompt"]
        row["prompt"] = row["prompt"].replace(EXPECTED_TARGET[field], replacement)
        issues = project_dashboard_preview_issues(package, dashboard, model_authored=True)
    assert next_steps["implementation_target"] == EXPECTED_TARGET
    assert [row["contract"]["fact_bindings"] for row in dashboard["host_handoff_prompts"]] == binding_snapshots
    assert any("lost its exact selected implementation scope copy" in issue for issue in issues)
    assert _files(tmp_path) == before


@pytest.mark.parametrize("surface", ["create_plan", "cli"])
def test_first_visible_target_cannot_disagree_with_a_later_canonical_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, surface: str,
) -> None:
    package, next_steps, dashboard = _project_package(tmp_path, monkeypatch)
    assert next_steps_preview_issues(package, next_steps, semantic_checks=False) == []
    assert project_dashboard_preview_issues(package, dashboard, model_authored=True) == []
    if surface == "cli":
        next_steps["implementation_prompt"] = next_steps["implementation_prompt"].replace(
            "B-120", "B-041", 1,
        )
        issues = next_steps_preview_issues(package, next_steps, semantic_checks=False)
    else:
        prompt = next(row for row in dashboard["host_handoff_prompts"] if row["step_id"] == surface)
        prompt["prompt"] = prompt["prompt"].replace("B-120", "B-041", 1)
        issues = project_dashboard_preview_issues(package, dashboard, model_authored=True)
    assert next_steps["implementation_target"] == EXPECTED_TARGET
    assert all(
        row["contract"]["fact_bindings"]["implementation_target"] == EXPECTED_TARGET
        for row in dashboard["host_handoff_prompts"]
    )
    assert any("lost its exact selected implementation scope copy" in issue for issue in issues)
