"""Outgoing author instructions and the state-only source address contract."""

from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    author_greenfield_intent,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    StructuredAuthoringProvider,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def test_authoring_prompt_requires_every_transaction_material_fact() -> None:
    source = _source()
    provider = StructuredAuthoringProvider(_response(source))

    author_greenfield_intent(
        review_provider_factory=AdmittingReviewProvider,
        evidence_text=source,
        provider=provider,
        clock=lambda: 0.0,
    )
    prompt = " ".join(str(getattr(provider.requests[0], "system_prompt", "")).split())

    for field in (
        "product_story",
        "state_object",
        "first_path",
        "proof_boundary",
        "human_actors",
    ):
        assert field in prompt
    assert "owner_fact_quote" in prompt
    assert "internal_systems fact or title" in prompt
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
    assert "Include the explicit actor with its action and object in the first citation" in prompt
    assert "For state_object only, supply prefix, quote and anchor_occurrence" in prompt
    assert "selected quote is at the end of the anchor" in prompt
    assert "Prefix is only a locator, never state meaning or projected text" in prompt


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
    for field in ("title", "product_story", "proof_boundary"):
        assert set(_AUTHORED_FACTS_SCHEMA["properties"][field]["properties"]) == {"quote", "occurrence"}
