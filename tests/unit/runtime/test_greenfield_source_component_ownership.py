"""Source ownership is optional; proposed design never creates accepted facts."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_component_relation_facts,
    validate_component_responsibility_relations,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import (
    build_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.proposal_validation import (
    validate_host_reasoned_proposal,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    StructuredAuthoringProvider,
    authored_response,
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
    response = authored_response(intent, evidence_text=source, first_path_relations=events,
        component_responsibility_owners=[explicit_owner] if explicit_owner else None,
        )
    if not explicit_owner:
        response["result"]["components"] = []
    return source, response, events


def _author(source, response):
    provider = StructuredAuthoringProvider(response)
    result = author_greenfield_intent(evidence_text=source, provider=provider, clock=lambda: 0, review_provider_factory=AdmittingReviewProvider)
    assert provider.calls == 1
    return result


@pytest.mark.parametrize("kind", ["human", "product", "mixed", "external"])
def test_no_source_capability_does_not_promote_terminal_ownership(kind):
    source, response, events = _scenario(kind)
    result = _author(source, response)

    assert result.intent["component_responsibilities"] == []
    assert result.component_responsibility_relations == ()
    assert [(row["actor_kind"], row["actor_fact_quote"], row["event_quote"])
            for row in result.first_path_relations] == [
        (row["actor_kind"], row["actor_fact_quote"], row["event_quote"]) for row in events
    ]
    assert result.provisional_design == response["result"]["provisional_design"]
    assert validate_component_responsibility_relations((), intent=result.intent,
        first_path_relations=result.first_path_relations) == ()
    contracts = authored_component_relation_facts(title="Draft Desk", internal_systems=(),
        relations=result.first_path_relations, component_responsibility_relations=())
    product_events = [row["event_quote"] for row in events if row["actor_kind"] == "product"]
    assert [row["responsibility_facts"] for row in contracts] == ([product_events] if product_events else [])


@pytest.mark.parametrize("kind", ["human", "product", "mixed", "external"])
def test_empty_owner_group_is_not_an_implicit_terminal_capability(kind):
    source, response, _ = _scenario(kind)
    response["result"]["components"] = [{"owner_fact_quote": "Draft Desk", "responsibilities": []}]
    with pytest.raises(GreenfieldModelAuthoringError, match="component ownership"):
        _author(source, response)


@pytest.mark.parametrize("owner", ["Draft Desk", "Receipt Store"])
def test_explicit_non_path_source_capability_keeps_its_owner(owner):
    source, response, _ = _scenario("human", explicit_owner=owner)
    result = _author(source, response)

    relation, = result.component_responsibility_relations
    assert relation["owner_system_quote"] == owner
    assert relation["responsibility_quote"] == f"{owner} retains receipts for seven years"
    assert relation["responsibility_source"] == "accepted_fact"
    assert relation["first_path_event_order"] == 0


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

    with pytest.raises(GreenfieldAuthoredSemanticsError, match="without typed owners"):
        validate_component_responsibility_relations([], intent=result.intent,
            first_path_relations=result.first_path_relations)
    bad = deepcopy(response)
    bad["result"]["components"][0]["owner_fact_quote"] = "Mara"
    with pytest.raises(GreenfieldModelAuthoringError):
        _author(source, bad)


def test_human_path_retains_source_story_and_complete_proposed_package(tmp_path):
    source, response, events = _scenario("human")
    candidate = materialize_model_authored_intent(prompt=source, repo_root=tmp_path,
        authoring_provider=StructuredAuthoringProvider(response), review_provider_factory=AdmittingReviewProvider)
    proposal = build_greenfield_proposal(repo_root=tmp_path, prompt=source,
        release_selector="0.0.1", confirmed_intent=candidate, require_completion_ready=False)
    validate_host_reasoned_proposal(proposal)

    assert candidate.get("component_responsibilities", []) == []
    assert candidate["authored_semantics"]["component_responsibility_relations"] == []
    assert proposal["project_intelligence"]["purpose"] == candidate["product_story"]
    assert 4 <= len(proposal["components"]) <= 5
    assert 4 <= len(proposal["backlog"]) <= 5
    assert len(proposal["diagrams"]) == 5
    context = proposal["diagrams"][0]
    assert 'subgraph product[' not in context["mermaid_source"]
    context_labels = context["mermaid_source"].replace("<br/>", " ")
    assert candidate["product_story"] in context_labels
    product_box = next(box for box in context["diagram_boxes"] if box["node_id"] == "product")
    assert product_box["role"] == "Product description"
    assert product_box["description"] == candidate["product_story"]
    for event in events:
        assert event["event_quote"] in context_labels
    assert not any(box["role"] == "Product-owned component" for box in context["diagram_boxes"])
