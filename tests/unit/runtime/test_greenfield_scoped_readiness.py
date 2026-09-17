"""Scoped proposed decisions survive projection without becoming source facts."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import (
    preview_accepted_project_memory, preview_project_dashboard_payload,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import authored_projection_parity_issues
from odylith.runtime.domain_intelligence.greenfield_completion_types import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_experience import build_next_steps
from odylith.runtime.domain_intelligence.greenfield_preconfirm_handoff_quality import (
    next_steps_preview_issues, project_dashboard_preview_issues,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import validate_provisional_design
from odylith.runtime.domain_intelligence.proposal_memory import build_project_brief_source_markdown
from tests.unit.runtime.greenfield_model_authoring_fixtures import structural_design_fixture
from tests.unit.runtime.test_greenfield_project_safeguard_carriers import _backlog_result, _proposal


DECISION = {
    "key": "shared-value-boundary",
    "status": "unresolved",
    "decision": "Decide which inputs the shared boundary may retain.",
    "affected_workstream_keys": ["test-work-1", "test-work-3"],
    "conditional_verification": "Once the boundary is agreed, submit an excluded input and verify it is not retained.",
}


def test_decision_scope_survives_brief_radar_registry_and_handoff(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path, readiness_decisions=[deepcopy(DECISION)])
    backlog = _backlog_result(proposal)
    brief = build_project_brief_source_markdown(
        proposal=proposal, backlog_items=backlog["created"], component_items=proposal["components"],
        diagram_ids=[row["slug"] for row in proposal["diagrams"]],
        release_selector="0.0.1", release_id="0.0.1",
    )
    specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=backlog,
    )
    assert brief.count(DECISION["decision"]) == 1
    assert DECISION["conditional_verification"] in brief
    assert "unresolved" in brief.lower()
    for index, workstream in enumerate(proposal["backlog"], 1):
        affected = index in (1, 3)
        rows = workstream["provisional_workstream_contract"]["readiness_decisions"]
        assert rows == ([DECISION] if affected else [])
        assert (DECISION["decision"] in workstream["radar_sections"]["Open Questions"]) is affected
        assert (DECISION["conditional_verification"] in workstream["radar_sections"]["Validation"]) is affected
        assert (DECISION["decision"] in specs[f"Structural test boundary {index}"]) is affected
    next_steps = build_next_steps(
        proposal=proposal, backlog_result=backlog,
        first_release_workstreams=[row["idea_id"] for row in backlog["created"]], release_selector="0.0.1",
    )
    assert next_steps["coding_readiness_contract"]["provisional_readiness_decisions"] == [DECISION]
    assert DECISION["decision"] in next_steps["implementation_prompt"]
    assert DECISION["conditional_verification"] in next_steps["implementation_prompt"]
    assert "unresolved" in next_steps["implementation_prompt"].lower()
    assert DECISION["decision"] not in json.dumps(next_steps["coding_readiness_contract"]["source_facts"])
    assert not authored_projection_parity_issues(proposal)
    delivery = next(row for row in proposal["diagrams"] if row["title"] == "Proposed Delivery Dependencies and Acceptance")
    decision_boxes = [box for box in delivery["diagram_boxes"] if box["role"] == "Unresolved proposed decision"]
    assert len(decision_boxes) == 1
    assert DECISION["conditional_verification"] in decision_boxes[0]["description"]


def test_unaffected_selected_workstream_has_no_foreign_gate(tmp_path: Path) -> None:
    decision = {**DECISION, "affected_workstream_keys": ["test-work-3"]}
    proposal = _proposal(tmp_path, readiness_decisions=[decision])
    backlog = _backlog_result(proposal)
    next_steps = build_next_steps(
        proposal=proposal, backlog_result=backlog,
        first_release_workstreams=[row["idea_id"] for row in backlog["created"]], release_selector="0.0.1",
    )
    assert next_steps["coding_readiness_contract"]["provisional_readiness_decisions"] == []
    assert DECISION["decision"] not in next_steps["implementation_prompt"]
    assert not any(DECISION["decision"] in gate for gate in next_steps["coding_readiness_gates"])


@pytest.mark.parametrize("field,value", [
    ("status", "resolved"), ("decision", " "), ("conditional_verification", ""),
    ("affected_workstream_keys", []), ("affected_workstream_keys", ["absent"]),
    ("affected_workstream_keys", ["test-work-1", "test-work-1"]),
])
def test_invalid_decision_is_rejected(field: str, value: object) -> None:
    design = structural_design_fixture([1])
    decision = deepcopy(DECISION)
    decision[field] = value
    design["readiness_decisions"] = [decision]
    with pytest.raises(ValueError, match="Greenfield"):
        validate_provisional_design(design, event_orders=[1], result_event_order=1)


def test_duplicate_decisions_are_rejected() -> None:
    design = structural_design_fixture([1])
    design["readiness_decisions"] = [deepcopy(DECISION), deepcopy(DECISION)]
    with pytest.raises(ValueError, match="readiness"):
        validate_provisional_design(design, event_orders=[1], result_event_order=1)


@pytest.mark.parametrize("field", ["project_brief", "backlog", "components", "semantic_model", "diagrams"])
def test_projection_omission_is_rejected(tmp_path: Path, field: str) -> None:
    proposal = _proposal(tmp_path, readiness_decisions=[deepcopy(DECISION)])
    if field == "project_brief":
        proposal[field]["coding_readiness_gates"] = []
    elif field == "backlog":
        proposal[field][0]["provisional_workstream_contract"]["readiness_decisions"] = []
    elif field == "components":
        proposal[field][0]["component_contract"]["readiness_decisions"] = []
    elif field == "semantic_model":
        proposal[field]["provisional_design"]["readiness_decisions"] = []
    else:
        diagram = next(row for row in proposal[field] if row["title"] == "Proposed Delivery Dependencies and Acceptance")
        diagram["diagram_boxes"] = [row for row in diagram["diagram_boxes"] if row["role"] != "Unresolved proposed decision"]
    assert authored_projection_parity_issues(proposal)


def _package(tmp_path: Path, *, decisions: list[dict[str, object]]) -> GreenfieldCompletionPackage:
    proposal = _proposal(tmp_path, readiness_decisions=decisions)
    backlog = _backlog_result(proposal)
    ids = tuple(row["idea_id"] for row in backlog["created"])
    next_steps = build_next_steps(
        proposal=proposal, backlog_result=backlog, first_release_workstreams=ids, release_selector="0.0.1",
    )
    accepted = preview_accepted_project_memory(
        root=tmp_path, target_root=tmp_path, proposal=proposal, backlog_result=backlog,
        component_items=proposal["components"], release_selector="0.0.1",
        release_target_result=None, release_assignment_result=None, validation_gate=None,
        source_launch_context=next_steps,
    )
    dashboard = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=accepted, source_launch_context=next_steps,
    )
    return GreenfieldCompletionPackage(
        proposal=proposal, backlog_result=backlog, release_selector="0.0.1", release_workstream_ids=ids,
        next_steps_preview=next_steps, accepted_project_preview=accepted, project_dashboard_preview=dashboard,
    )


def test_every_copyable_handoff_retains_selected_decisions(tmp_path: Path) -> None:
    package = _package(tmp_path, decisions=[deepcopy(DECISION)])
    assert not next_steps_preview_issues(package, package.next_steps_preview, semantic_checks=False)
    assert not project_dashboard_preview_issues(package, package.project_dashboard_preview, model_authored=True)
    assert DECISION["decision"] in package.project_dashboard_preview["open"][0]
    for row in package.project_dashboard_preview["host_handoff_prompts"]:
        assert row["contract"]["provisional_readiness_decisions"] == [DECISION]
        assert row["prompt"].count(DECISION["decision"]) == 1
        assert row["prompt"].count(DECISION["conditional_verification"]) == 1
        assert DECISION["decision"] not in json.dumps(row["contract"]["fact_bindings"])


@pytest.mark.parametrize("surface", ["next_steps", "dashboard"])
@pytest.mark.parametrize("damage", ["omit", "status", "scope", "check", "duplicate", "visible_copy"])
def test_handoff_drift_is_rejected(tmp_path: Path, surface: str, damage: str) -> None:
    package = _package(tmp_path, decisions=[deepcopy(DECISION)])
    preview = deepcopy(package.next_steps_preview if surface == "next_steps" else package.project_dashboard_preview)
    row = preview if surface == "next_steps" else preview["host_handoff_prompts"][0]
    contract = row["coding_readiness_contract" if surface == "next_steps" else "contract"]
    decisions = contract["provisional_readiness_decisions"]
    if damage == "omit":
        decisions.clear()
    elif damage == "duplicate":
        decisions.append(deepcopy(decisions[0]))
    elif damage == "status":
        decisions[0]["status"] = "resolved"
    elif damage == "scope":
        decisions[0]["affected_workstream_keys"] = ["test-work-2"]
    elif damage == "check":
        decisions[0]["conditional_verification"] = "Unrelated check."
    else:
        key = "implementation_prompt" if surface == "next_steps" else "prompt"
        row[key] = row[key].replace(DECISION["decision"], "Ready to implement.")
    issues = (
        next_steps_preview_issues(package, preview, semantic_checks=False) if surface == "next_steps"
        else project_dashboard_preview_issues(package, preview, model_authored=True)
    )
    assert issues


def test_old_design_requires_new_preconfirm_authorship_not_silent_completion() -> None:
    design = structural_design_fixture([1])
    design["version"] = "odylith.greenfield.provisional-design.v2"
    design.pop("readiness_decisions")
    with pytest.raises(ValueError, match="authority contract"):
        validate_provisional_design(design, event_orders=[1], result_event_order=1)
    assert "readiness_decisions" not in design


@pytest.mark.parametrize("malformed", [None, "text", {}, [None], [{}], [{"status": "unresolved"}]])
def test_malformed_dashboard_readiness_stops_before_rendering(tmp_path: Path, malformed: object) -> None:
    package = _package(tmp_path, decisions=[deepcopy(DECISION)])
    context = deepcopy(package.next_steps_preview)
    context["coding_readiness_contract"]["provisional_readiness_decisions"] = malformed
    with pytest.raises(ValueError, match="readiness"):
        preview_project_dashboard_payload(
            root=tmp_path, proposal=package.proposal,
            accepted_project_preview=package.accepted_project_preview, source_launch_context=context,
        )


def test_shared_component_inherits_decision_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.unit.runtime import test_greenfield_project_safeguard_carriers as fixtures

    response = fixtures._response

    def shared_response(source: str) -> dict[str, object]:
        value = response(source)
        value["result"]["provisional_design"]["workstreams"][0]["component_keys"].append("test-boundary-2")
        return value

    monkeypatch.setattr(fixtures, "_response", shared_response)
    proposal = _proposal(tmp_path, readiness_decisions=[deepcopy(DECISION)])
    shared = proposal["components"][1]["component_contract"]
    assert shared["readiness_decisions"] == [DECISION]
    assert len(shared["delivery_workstreams"]) == 2
    specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_backlog_result(proposal),
    )
    assert specs["Structural test boundary 2"].count(DECISION["decision"]) == 1
    assert DECISION["decision"] not in specs["Structural test boundary 4"]
