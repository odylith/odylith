"""Source statements retain their punctuation without sentence-frame joins."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_proposal import _project_brief
from odylith.runtime.domain_intelligence.greenfield_provisional_package import (
    _source_design_duty_text,
    _source_lifecycle_text,
)
from tests.unit.runtime.test_greenfield_authored_atlas_view import (
    _authored_diagrams,
    _source_lifecycle,
)


@pytest.mark.parametrize("terminal", ["", ".", "!", "?", ":", ";"])
def test_lifecycle_copy_keeps_complete_fields_and_citations(terminal: str) -> None:
    transition = {
        "governed_object": "Review dossier",
        "trigger": f"An approval is withdrawn{terminal}",
        "effects": [{
            "field": "availability", "change": f"Remove future eligibility{terminal}",
            "observable_check": f"Affected pending analysis is invalidated{terminal}",
        }],
        "source_refs": [{"quote": f"Withdrawal invalidates pending analysis{terminal}", "occurrence": 1}],
    }
    original = deepcopy(transition)
    text = _source_lifecycle_text(transition)
    assert text.splitlines() == [
        "Source state transition — Review dossier",
        f"Trigger: {transition['trigger']}",
        f"Field availability: {transition['effects'][0]['change']}",
        f"Observable check: {transition['effects'][0]['observable_check']}",
        f"Source citation (occurrence 1): {transition['source_refs'][0]['quote']}",
    ]
    assert transition == original


@pytest.mark.parametrize("terminal", ["", ".", "!", "?", ":", ";"])
def test_guard_and_proof_copy_use_intact_labeled_fields(terminal: str) -> None:
    citation = {"quote": f"Only reviewers may approve{terminal}", "occurrence": 2}
    guard = {
        "trigger": f"An actor attempts approval{terminal}",
        "protected_action": f"Record the decision{terminal}",
        "rule": citation["quote"], "source_refs": [citation],
    }
    proof = {
        "dossier_or_artifact": "Review dossier", "must_show": f"The decision and its bounded evidence{terminal}",
        "source_refs": [citation],
    }
    original = deepcopy((guard, proof))
    assert _source_design_duty_text("conditional_guards", guard).splitlines() == [
        "Source conditional guard", f"Trigger: {guard['trigger']}",
        f"Protected action: {guard['protected_action']}", f"Rule: {guard['rule']}",
        f"Source citation (occurrence 2): {citation['quote']}",
    ]
    assert _source_design_duty_text("proof_duties", proof).splitlines() == [
        "Source proof duty", "Dossier or artifact: Review dossier",
        f"Required evidence: {proof['must_show']}", f"Source citation (occurrence 2): {citation['quote']}",
    ]
    assert (guard, proof) == original


def test_brief_constraints_and_non_goals_keep_each_source_statement_separate() -> None:
    constraints = ["Retain the decision.", "Keep private notes private!", "Recheck eligibility?"]
    non_goals = ["Do not make official decisions.", "Do not infer undisclosed facts."]
    original = deepcopy((constraints, non_goals))
    brief = _project_brief(
        title="Review desk", product_story="People need reviewable evidence.",
        problem="Decisions lose evidence.", product_view="A bounded review dossier.",
        first_path="A reviewer records a decision.", visible_result="The decision is visible.",
        proof_boundary="Verify the decision and evidence.", human_actors=["Reviewer"],
        internal_systems=[], external_systems=[], non_goals=non_goals,
        operational_constraints=constraints, evidence_requirements=[], assumptions=[],
        provisional_design={"first_run": {"rationale": "Record and review the decision."}},
    )
    sections = {row["section"]: row for row in brief["blueprint_sections"]}
    assert sections["Operational constraints"]["must_capture"].splitlines() == constraints
    assert sections["Non-goals"]["must_capture"].splitlines() == non_goals
    assert brief["operational_constraints"] == constraints
    assert (constraints, non_goals) == original


def test_atlas_lifecycle_fields_keep_full_statements_without_punctuation_join() -> None:
    lifecycle = _source_lifecycle()
    transition = lifecycle["off_path_transitions"][0]
    transition["trigger"] = "An approval is withdrawn."
    effect = transition["effects"][0]
    effect["change"] = "Close future access."
    effect["observable_check"] = "Affected unpublished analysis is invalidated."
    original = deepcopy(lifecycle)
    support = _authored_diagrams(source_lifecycle=lifecycle)[-1]
    boxes = {box["node_id"]: box for box in support["diagram_boxes"]}
    assert boxes["off_path_transition1_effect1"]["label"] == "Effect 1.1"
    assert boxes["off_path_transition1"]["description"] == (
        "“Withdrawal closes placement access and erases the cached placement”"
    )
    assert boxes["off_path_transition1"]["details"] == [
        {"label": "Trigger", "text": "An approval is withdrawn."},
        {"label": "Governed object", "text": "berth occupancy"},
    ]
    assert 'off_path_transition1_effect1["Effect 1.1<br/>Close future access."]' in support["mermaid_source"]
    assert boxes["off_path_transition1_effect1"]["description"] == (
        "Trigger: An approval is withdrawn.\nField: access\nChange: Close future access.\n"
        "Observable check: Affected unpublished analysis is invalidated."
    )
    assert boxes["off_path_transition1_effect2"]["description"] == (
        "Trigger: An approval is withdrawn.\nField: cache\nChange: erased\n"
        "Observable check: cache empty"
    )
    assert "withdrawn.." not in str(boxes)
    assert lifecycle == original
