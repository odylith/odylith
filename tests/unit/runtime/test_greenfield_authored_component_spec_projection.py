from __future__ import annotations

import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_authored_component_spec
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)


def _authored_proposal(tmp_path: Path) -> dict[str, object]:
    first_path = (
        "Planner submits a berth request. "
        "Berth map records the assigned berth and shows Berth 7."
    )
    first_event = "Planner submits a berth request"
    second_event = "Berth map records the assigned berth and shows Berth 7"
    responsibility_fact = "Keep selected route evidence with the recorded berth assignment"
    relations = (
        {
            "actor_kind": "human",
            "actor_quote": "Planner",
            "event_quote": first_event,
            "action_verb_quote": "submits",
            "target_quote": "berth request",
            "visible_result_quote": "",
            "recovery_path": False,
        },
        {
            "actor_kind": "product",
            "actor_quote": "Berth map",
            "owner_system_quote": "Berth map",
            "event_quote": second_event,
            "action_verb_quote": "records",
            "target_quote": "assigned berth",
            "visible_result_quote": "Berth 7",
            "recovery_path": False,
        },
    )
    proof_boundary = "A planner can replay the recorded assignment and verify Berth 7."
    intent = {
        "title": "Harbor Planner",
        "product_story": "Planners need a reviewable berth assignment.",
        "state_object": "assigned berth",
        "first_path": first_path,
        "proof_boundary": proof_boundary,
        "problem": "Berth requests and assignments are hard to review.",
        "customer": "Planners",
        "opportunity": "Keep one reviewable berth assignment path.",
        "product_view": "Harbor Planner records and shows assigned berths.",
        "success_metrics": ["A planner sees Berth 7."],
        "evidence_requirements": [proof_boundary],
        "operational_constraints": ["Retain the recorded berth assignment."],
        "component_responsibilities": [responsibility_fact],
        "human_actors": ["Planner"],
        "external_systems": ["Harbor Ledger"],
        "internal_systems": ["Berth map"],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": ["Automated vessel dispatch"],
    }
    source = ". ".join(
        str(item)
        for value in intent.values()
        for item in (value if isinstance(value, list) else [value])
        if str(item)
    )
    candidate = materialize_model_authored_intent(
        prompt=source,
        repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                first_path_relations=relations,
                component_responsibility_owners=["Berth map"],
            )
        ),
        authoring_timeout_seconds=60,
        authoring_profile_id=STANDARD_PROFILE_ID,
    )
    proposal = build_authored_greenfield_proposal(
        observed_source={"source_posture": "operator prompt evidence"},
        release_selector="0.0.1",
        confirmed_intent=candidate,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = candidate[PRODUCT_INTENT_AUTHORITY_KEY]
    return proposal


def _backlog_result() -> dict[str, object]:
    return {
        "created": [
            {
                "idea_id": "B-001",
                "title": "Harbor Planner First Release",
            },
            {
                "idea_id": "B-002",
                "title": "Harbor Planner Boundaries",
            },
        ]
    }


def test_authored_component_spec_is_structural_and_bypasses_legacy_owners(
    tmp_path: Path,
) -> None:
    for retired_owner in (
        "build_component_spec",
        "ensure_component_contract",
        "component_risk_lines",
        "greenfield_programs",
        "greenfield_traceability",
        "greenfield_experience",
        "component_authoring",
    ):
        assert not hasattr(greenfield_apply_components, retired_owner)

    proposal = _authored_proposal(tmp_path)
    specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(),
    )
    previews = greenfield_apply_components.preview_prewrite_components(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(),
    )

    spec = specs["Berth map"]
    authoring_input = previews[0]["authoring_input"]
    assert "source_custody" not in authoring_input
    assert "Planned path: `src/harbor-planner/berth-map`" in spec
    assert "## Source boundary" in spec
    assert "## Trace links" in spec
    assert "## Feature History" in spec
    assert "(Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))" in spec
    assert "## Source-custodied owner relations" in spec
    assert "### Owner system" in spec
    assert "### Owner-bound events" in spec
    assert "### Event targets" in spec
    assert "### Visible results" in spec
    assert "### Recovery events" in spec
    assert "### State context" in spec
    assert "### External dependencies" in spec
    assert "### Operational constraints" in spec
    assert "> Berth map records the assigned berth and shows Berth 7" in spec
    assert "> Keep selected route evidence with the recorded berth assignment" in spec
    assert "> assigned berth" in spec
    assert "> Berth 7" in spec
    assert "> assigned berth" in spec
    assert "> Harbor Ledger" in spec
    assert "> Retain the recorded berth assignment." in spec
    assert "> No source-custodied recovery event was authored for this component." in spec
    assert "- Workstream: `B-001`" in spec
    assert "- Diagram: `D-001`" in spec
    assert set(authoring_input["component_contract"]) == {
        "owner_system",
        "responsibility_facts",
        "owner_bound_events",
        "event_targets",
        "visible_results",
        "recovery_events",
        "state_context",
        "external_dependencies",
        "operational_constraints",
    }
    for key in ("boundary", "interfaces", "risks"):
        assert not authoring_input[key]
    assert authoring_input["dependencies"] == ("Harbor Ledger",)
    assert authoring_input["validation"] == (
        "Retain the recorded berth assignment.",
    )
    for forbidden in (
        "Owned state",
        "Accepted inputs",
        "Produced outputs",
        "States or transitions",
        "Excluded scope facts",
        "Upstream truth",
        "Downstream consumers",
        "Proof obligations",
        "Successful path evidence",
        "Blocked input evidence",
        "Replay evidence",
        "Automated vessel dispatch",
        "Harbor schedule",
        "A planner can replay the recorded assignment and verify Berth 7.",
    ):
        assert forbidden not in spec
    assert "TBD" not in spec
    assert "accessibility, privacy, audit, and safety" not in spec
    assert previews[0]["validation_gate"]["status"] == "passed"
    assert previews[0]["registry_entry"]["sources"] == ["intent.authored_semantics"]
    assert previews[0]["registry_entry"]["workstreams"] == ["B-001", "B-002"]


def test_authored_component_projection_fails_closed_without_exact_custody(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    proposal["intent"] = {"title": "Harbor Planner"}

    with pytest.raises(ValueError, match="verified authored semantics"):
        greenfield_apply_components.render_prewrite_component_specs(
            root=tmp_path,
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_backlog_result(),
        )


def test_authored_component_projection_rejects_mutated_relation_authority(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    mutated = copy.deepcopy(proposal)
    intent = mutated["intent"]
    assert isinstance(intent, dict)
    relations = intent["authored_semantics"]["first_path_relations"]
    relations[1]["recovery_path"] = True

    with pytest.raises(ValueError, match="do not match sealed Product Intent authority"):
        greenfield_apply_components.render_prewrite_component_specs(
            root=tmp_path,
            proposal=mutated,
            release_selector="0.0.1",
            backlog_result=_backlog_result(),
        )


def test_authored_component_projection_rejects_raw_custody_mapping(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    rows = greenfield_authored_component_spec.build_authored_component_authoring_inputs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_backlog_result(),
    )
    forged = dict(rows[0])
    forged["source_custody"] = dict(rows[0]["source_custody"])

    with pytest.raises(ValueError, match="exact semantic custody contract"):
        greenfield_authored_component_spec.build_authored_component_spec(forged)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("local_proof", "closed owner-bound component contract"),
        ("dependencies", "dependencies drifted from typed context"),
    ),
)
def test_authored_component_projection_rejects_legacy_semantic_fallbacks(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    proposal = _authored_proposal(tmp_path)
    component = proposal["components"][0]
    if mutation == "local_proof":
        component["component_contract"]["local_proof"] = ["invented proof"]
    else:
        component["dependencies"] = ["invented dependency"]

    with pytest.raises(ValueError, match=message):
        greenfield_apply_components.render_prewrite_component_specs(
            root=tmp_path,
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_backlog_result(),
        )
