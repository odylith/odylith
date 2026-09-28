"""Split-schema contract for participant-first Greenfield authoring."""

from odylith.runtime.domain_intelligence.greenfield_candidate_review import (
    TITLE_ROLE_DEFINITION,
)
from odylith.runtime.domain_intelligence.greenfield_participant_first_authoring import (
    author_greenfield_intent,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    RemainingCandidateProvider,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def test_authoring_schema_structurally_separates_participants_authored_and_clarification_results() -> None:
    source = _source()
    provider = RemainingCandidateProvider(_response(source))
    participant = provider.participant_provider()
    authored = author_greenfield_intent(
        review_provider_factory=lambda: AdmittingReviewProvider(
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
        participant_provider_factory=lambda: participant,
        clock=lambda: 0.0,
    )
    assert authored.intent["component_responsibilities"].count(
        "Retain source notes for seven years"
    ) == 1

    authoring_schema = provider.requests[0].output_schema
    authored_branch, clarification_branch = authoring_schema["properties"]["result"]["anyOf"]
    typed_facts = authored_branch["properties"]["facts"]
    assert typed_facts["additionalProperties"] is False
    title_role = typed_facts["properties"]["title"]["description"]
    assert title_role == TITLE_ROLE_DEFINITION
    assert "requested product, workflow, or product state" in title_role
    assert "metadata alongside a distinct requested workflow" in title_role
    assert "title the requested workflow instead" in title_role
    assert "repository or artifact name remains valid" in title_role
    assert "itself the requested product identity" in title_role
    assert typed_facts["properties"]["state_object"]["type"] == "object"
    assert "subject may be a person" in typed_facts["properties"]["state_object"]["description"]
    assert "An activity, workflow stage, goal, product label" in typed_facts["properties"]["proof_boundary"]["description"]
    assert "user's unmet need" in typed_facts["properties"]["problem"]["description"]
    assert "improvement or benefit" in typed_facts["properties"]["opportunity"]["description"]
    assert "title or product-category label is not an experience" in typed_facts["properties"]["product_view"]["description"]
    assert typed_facts["properties"]["first_path"]["type"] == "array"
    assert typed_facts["properties"]["first_path"]["minItems"] == 1
    assert "human_actors" not in typed_facts["properties"]
    participant_schema = participant.requests[0].output_schema
    assert participant_schema["properties"]["human_actors"]["type"] == "array"
    assert "minItems" not in participant_schema["properties"]["human_actors"]

    authored_properties = authored_branch["properties"]
    workstream_problem = authored_properties["provisional_design"]["properties"][
        "workstreams"
    ]["items"]["properties"]["problem"]
    assert workstream_problem["type"] == "string"
    assert "consumer-facing difficulty" in workstream_problem["description"]
    assert "opaque event identifier" in workstream_problem["description"]
    terminal, absent_terminal = authored_properties["terminal"]["anyOf"]
    assert absent_terminal == {"type": "null"}
    assert "terminal" in authored_branch["required"]
    assert terminal["type"] == "object"
    assert terminal["additionalProperties"] is False
    assert set(terminal["properties"]) == {"event_order", "result_fact", "result_quote", "result_occurrence"}
    assert set(terminal["required"]) == set(terminal["properties"])
    result_fact = terminal["properties"]["result_fact"]
    assert result_fact["additionalProperties"] is False
    assert set(result_fact["required"]) == set(result_fact["properties"]) == {"field", "row"}
    assert result_fact["properties"]["row"]["minimum"] == 1
    assert set(result_fact["properties"]["field"]["enum"]) == {
        "first_path", "product_story", "opportunity", "product_view", "success_metrics", "proof_boundary",
    }
    assert terminal["properties"]["event_order"]["type"] == "integer"
    assert "workflow stage" in terminal["properties"]["result_quote"]["description"]
    assert "inside the selected fact quote, not the source document" in terminal["properties"]["result_occurrence"]["description"]
    assert authored_properties["events"]["type"] == "array"
    assert authored_properties["events"]["minItems"] == 1
    assert set(authored_properties["events"]["items"]["properties"]) == {
        "actor_fact", "action_quote", "target_quote",
    }
    actor_fact = authored_properties["events"]["items"]["properties"]["actor_fact"]
    assert actor_fact["additionalProperties"] is False
    assert set(actor_fact["required"]) == {"field", "row"}
    assert set(actor_fact["properties"]["field"]["enum"]) == {
        "title", "human_actors", "internal_systems", "external_systems",
    }
    assert authored_properties["components"]["minItems"] == 0
    assert authored_properties["components"]["items"]["properties"]["responsibilities"]["minItems"] == 1
    component_description = authored_properties["components"]["description"]
    responsibility_description = authored_properties["components"]["items"]["properties"][
        "responsibilities"
    ]["description"]
    assert "Operational constraints remain global until independent review" in component_description
    assert "classifies and projects product-owned custody" in component_description
    assert "Operational constraints remain global during authoring" in responsibility_description
    assert "independent review alone may project a product-owned constraint" in responsibility_description
    component = authored_properties["components"]["items"]
    assert set(component["properties"]) == {"owner_fact_quote", "responsibilities"}
    assert set(component["properties"]["responsibilities"]["items"]["properties"]) == {"quote", "occurrence"}
    assert "component_responsibilities" not in typed_facts["properties"]
    assert "clarification" not in authored_properties
    assert set(clarification_branch["properties"]) == {"status", "consistency", "clarification"}
    assert "facts" not in clarification_branch["properties"]
