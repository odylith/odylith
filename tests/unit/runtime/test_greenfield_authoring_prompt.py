"""Outgoing author instructions and the state-only source address contract."""

from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    TITLE_ROLE_DEFINITION,
)
from odylith.runtime.domain_intelligence.greenfield_participant_first_authoring import (
    author_greenfield_intent,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    RemainingCandidateProvider,
    component_custody_for_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def test_authoring_prompt_requires_every_transaction_material_fact() -> None:
    source = _source()
    response = _response(source)
    provider = RemainingCandidateProvider(response)
    participant_provider = provider.participant_provider()

    authored = author_greenfield_intent(
        review_provider_factory=lambda: AdmittingReviewProvider(
            component_custody=component_custody_for_response(response),
            constraint_custody=[
                {
                    "constraint_index": 1,
                    "kind": "product_owned",
                    "owner_fact": {"field": "title", "row": 1},
                },
            ],
        ),
        evidence_text=source,
        provider=provider,
        participant_provider_factory=lambda: participant_provider,
        clock=lambda: 0.0,
    )
    assert authored.intent["component_responsibilities"].count(
        "Retain source notes for seven years"
    ) == 1
    assert participant_provider.requests[0].schema_name == "greenfield_participant_selection"
    prompt = " ".join(str(getattr(provider.requests[0], "system_prompt", "")).split())

    for field in (
        "product_story",
        "state_object",
        "first_path",
        "proof_boundary",
        "human_actors",
    ):
        assert field in prompt
    assert "Do not return the accepted-source components field" in prompt
    assert "Independent review alone classifies exact source-supported event" in prompt
    assert "assigns product ownership, and projects accepted components" in prompt
    assert "facts.operational_constraints" in prompt
    assert "remains only in facts.operational_constraints during authoring" in prompt
    assert "Do not copy any constraint into component responsibilities" in prompt
    assert "Independent review classifies every accepted constraint" in prompt
    assert "alone may project product-owned custody after admission" in prompt
    assert "explicitly source-stated operational exchange" in str(provider.requests[0].output_schema)
    assert "product_story is the shortest complete source span" in prompt
    assert "excluding the operator's request to create a proposal" in prompt
    assert "target_quote must occur within that event" in prompt
    assert "stage, artifact or status label alone is not an event" in prompt
    assert "one conservative assumption targeted to that field" in prompt
    assert "practical need this product should address" in prompt
    assert "improvement worth pursuing" in prompt
    assert "concrete experience" in prompt
    assert "Give the decision itself, not commentary" in prompt
    assert "distinct, consumer-facing problem" in prompt
    assert "do not describe implementation status" in prompt
    assert "opaque event identifiers" in prompt
    assert "Include the explicit actor with its action and object in the first citation" in prompt
    assert "For state_object only, supply prefix, quote and anchor_occurrence" in prompt
    assert "selected quote is at the end of the anchor" in prompt
    assert "Prefix is only a locator, never state meaning or projected text" in prompt
    assert "Select title, product_story, state_object and first_path according to their schema" in prompt
    title_schema = provider.requests[0].output_schema["properties"]["result"]["anyOf"][0][
        "properties"
    ]["facts"]["properties"]["title"]
    assert title_schema["description"] == TITLE_ROLE_DEFINITION
    assert "metadata alongside a distinct requested workflow" in title_schema["description"]
    assert "repository or artifact name remains valid" in title_schema["description"]


def test_only_state_object_uses_the_anchored_address_schema() -> None:
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
        _AUTHORED_FACTS_SCHEMA,
        _CITATION_SCHEMA,
    )

    state = _AUTHORED_FACTS_SCHEMA["properties"]["state_object"]
    assert set(state["properties"]) == {"quote", "prefix", "anchor_occurrence"}
    assert set(state["required"]) == set(state["properties"])
    assert state["additionalProperties"] is False
    assert _CITATION_SCHEMA["required"] == ["quote", "occurrence"]
    assert set(_CITATION_SCHEMA["properties"]) == {"quote", "occurrence"}
    for field in ("title", "product_story"):
        assert set(_AUTHORED_FACTS_SCHEMA["properties"][field]["properties"]) == {"quote", "occurrence"}
    proof_citation, absent_proof = _AUTHORED_FACTS_SCHEMA["properties"]["proof_boundary"]["anyOf"]
    assert proof_citation == _CITATION_SCHEMA
    assert proof_citation["additionalProperties"] is False
    assert absent_proof == {"type": "null"}
