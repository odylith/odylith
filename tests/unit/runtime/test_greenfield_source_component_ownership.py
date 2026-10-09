"""Source ownership is optional; proposed design never creates accepted facts."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_component_relation_facts,
    authored_semantics_mapping,
    validate_component_responsibility_relations,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import (
    build_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.proposal_validation import (
    validate_host_reasoned_proposal,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    authored_response,
    admit_complete_host_candidate,
    host_candidate_response,
    materialize_complete_host_candidate,
    source_duty_fixture,
)


def _scenario(kind: str, *, explicit_owner: str = ""):
    first_actor = "Draft Desk" if kind == "product" else "Mara"
    last_actor = {
        "human": "Mara", "product": "Draft Desk", "mixed": "Draft Desk",
        "external": "Archive Service",
    }[kind]
    first_kind = "product" if first_actor == "Draft Desk" else "human"
    last_kind = {
        "human": "human", "product": "product", "mixed": "product",
        "external": "external_system",
    }[kind]
    events = [
        dict(actor_kind=first_kind, actor_fact_quote=first_actor,
             owner_system_quote=first_actor if first_kind == "product" else "",
             event_quote=f"{first_actor} stores one draft", action_verb_quote="stores",
             target_quote="one draft", visible_result_quote=""),
        dict(actor_kind=last_kind, actor_fact_quote=last_actor,
             owner_system_quote=last_actor if last_kind == "product" else "",
             event_quote=f"{last_actor} returns the review receipt", action_verb_quote="returns",
             target_quote="the review receipt", visible_result_quote="the review receipt"),
    ]
    intent = dict(
        title="Draft Desk", product_story="Draft Desk supports the draft review workflow",
        state_object="one draft", first_path=". ".join(row["event_quote"] for row in events),
        proof_boundary="the review receipt", problem="Scattered drafts delay reviews",
        customer="Mara", opportunity="A shared receipt would reduce rework",
        product_view="Draft Desk keeps a complete review trail",
        human_actors=["Mara"], external_systems=["Archive Service"] if kind == "external" else [],
        internal_systems=[explicit_owner] if explicit_owner and explicit_owner != "Draft Desk" else [],
        component_responsibilities=[f"{explicit_owner} retains receipts for seven years"] if explicit_owner else [],
        assumptions=[], ambiguities=[], success_metrics=[], evidence_requirements=[],
        operational_constraints=[], non_goals=[],
    )
    source = ". ".join(str(row) for value in intent.values()
                       for row in (value if isinstance(value, list) else [value]) if row)
    supporting = [dict(
        actor_kind="product", actor_fact_quote=explicit_owner, owner_system_quote=explicit_owner,
        event_quote=f"{explicit_owner} retains receipts for seven years",
        action_verb_quote="retains", target_quote="receipts", visible_result_quote="",
    )] if explicit_owner else []
    response = authored_response(intent, evidence_text=source, first_path_relations=events,
        supporting_event_relations=supporting,
        component_responsibility_owners=[explicit_owner] if explicit_owner else None,
        )
    response["result"]["provisional_design"]["project_summary"] = intent["product_story"] + "."
    if not explicit_owner:
        response["result"]["components"] = []
    return source, response, events


def _author(source, response):
    candidate = host_candidate_response(response, evidence_text=source)
    result = admit_complete_host_candidate(evidence_text=source, host_candidate=candidate)
    result.intent["authored_semantics"] = authored_semantics_mapping(
        result.first_path_relations, result.component_responsibility_relations,
        first_path_context_relations=result.first_path_context_relations,
        provisional_design=result.provisional_design,
        source_duty=source_duty_fixture(candidate, evidence_text=source),
    )
    return result


@pytest.mark.parametrize("kind", ["human", "product", "mixed", "external"])
def test_no_source_capability_does_not_promote_terminal_ownership(kind):
    source, response, events = _scenario(kind)
    result = _author(source, response)

    product_events = [row for row in events if row["actor_kind"] == "product"]
    assert result.intent["component_responsibilities"] == [row["event_quote"] for row in product_events]
    assert [row["responsibility_quote"] for row in result.component_responsibility_relations] == [
        row["event_quote"] for row in product_events
    ]
    assert all(row["responsibility_source"] == "accepted_fact"
               and row["first_path_event_order"] in {index for index, event in enumerate(events, 1)
                                                    if event["actor_kind"] == "product"}
               for row in result.component_responsibility_relations)
    assert all(row["responsibility_quote"] != "the review receipt"
               for row in result.component_responsibility_relations)
    assert [(row["actor_kind"], row["actor_fact_quote"], row["event_quote"])
            for row in result.first_path_relations] == [
        (row["actor_kind"], row["actor_fact_quote"], row["event_quote"]) for row in events
    ]
    assert result.provisional_design == response["result"]["provisional_design"]
    assert validate_component_responsibility_relations(
        result.component_responsibility_relations,
        intent=result.intent,
        first_path_relations=result.first_path_relations,
    ) == result.component_responsibility_relations
    contracts = authored_component_relation_facts(title=result.intent["title"], internal_systems=result.intent["internal_systems"],
        relations=result.first_path_relations,
        component_responsibility_relations=result.component_responsibility_relations)
    product_events = [
        row["event_quote"] for row in events if row["actor_kind"] == "product"
    ]
    assert [row["responsibility_facts"] for row in contracts] == (
        [product_events] if product_events else []
    )


@pytest.mark.parametrize("owner", ["Draft Desk", "Receipt Store"])
def test_explicit_non_path_source_capability_keeps_its_owner(owner):
    source, response, _ = _scenario("human", explicit_owner=owner)
    result = _author(source, response)

    relation, = result.component_responsibility_relations
    assert relation["owner_system_quote"] == owner
    assert relation["responsibility_quote"] == f"{owner} retains receipts for seven years"
    assert relation["responsibility_source"] == "accepted_fact"
    assert relation["first_path_event_order"] == 3
    assert relation["source_duty_id"] == "fixture-system-3"
    duty = result.intent["authored_semantics"]["source_duty"]
    assert duty["binding"]["system_duties"] == [{"duty_id": "fixture-system-3", "event_order": 3}]
    assert result.provisional_design["first_run"]["event_orders"] == [1, 2]
    assert result.intent["supporting_events"] == [relation["responsibility_quote"]]


def test_terminal_result_relation_is_rejected_at_the_typed_boundary():
    source, response, _ = _scenario("human", explicit_owner="Draft Desk")
    result = _author(source, response)
    intent = deepcopy(result.intent)
    intent["component_responsibilities"] = []
    invented = dict(responsibility_path="/proof_boundary", responsibility_quote="the review receipt",
        owner_system_path="/title", owner_system_quote="Draft Desk", first_path_event_order=2,
        responsibility_source="terminal_visible_result")

    with pytest.raises(GreenfieldAuthoredSemanticsError):
        validate_component_responsibility_relations([invented], intent=intent,
            first_path_relations=result.first_path_relations)


def test_optional_inventory_does_not_waive_explicit_citation_bindings():
    source, response, _ = _scenario("human", explicit_owner="Receipt Store")
    result = _author(source, response)

    bad_relation = deepcopy(result.component_responsibility_relations[0])
    bad_relation["owner_system_path"] = "/human_actors/0"
    bad_relation["owner_system_quote"] = "Mara"
    with pytest.raises(GreenfieldAuthoredSemanticsError, match="invalid system owner"):
        validate_component_responsibility_relations(
            [bad_relation],
            intent=result.intent,
            first_path_relations=result.first_path_relations,
        )


def test_human_path_retains_source_story_and_complete_proposed_package(tmp_path):
    source, response, events = _scenario("human")
    candidate = materialize_complete_host_candidate(
        prompt=source,
        repo_root=tmp_path,
        host_candidate=host_candidate_response(response, evidence_text=source),
    )
    proposal = build_greenfield_proposal(repo_root=tmp_path, prompt=source,
        release_selector="0.0.1", confirmed_intent=candidate, require_completion_ready=False)
    validate_host_reasoned_proposal(proposal)

    assert candidate.get("component_responsibilities", []) == []
    assert candidate["authored_semantics"]["component_responsibility_relations"] == []
    evidence_excerpt = f'Accepted evidence excerpt: “{candidate["product_story"]}”'
    assert proposal["project_intelligence"]["purpose"] == evidence_excerpt
    assert proposal["intent"]["product_story"] == candidate["product_story"]
    assert 4 <= len(proposal["components"]) <= 5
    assert 4 <= len(proposal["backlog"]) <= 5
    assert len(proposal["diagrams"]) == 5
    context = proposal["diagrams"][0]
    assert 'subgraph product[' not in context["mermaid_source"]
    context_labels = context["mermaid_source"].replace("<br/>", " ")
    assert candidate["product_story"] not in context_labels
    assert f'product["{candidate["title"]}"]' in context_labels
    product_box = next(box for box in context["diagram_boxes"] if box["node_id"] == "product")
    assert product_box["role"] == "Accepted evidence excerpt"
    assert product_box["description"] == ""
    assert product_box["details"] == [
        {"label": "Accepted evidence excerpt", "text": candidate["product_story"]},
    ]
    assert proposal["intent"]["authored_semantics"]["provisional_design"]["project_summary"] == response["result"]["provisional_design"]["project_summary"]
    for event in events:
        assert event["event_quote"] in context_labels
    assert not any(box["role"] == "Product-owned component" for box in context["diagram_boxes"])
