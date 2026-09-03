"""Typed source-custody proof for model-authored Greenfield terminal results."""

from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    authored_semantics_mapping,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoringError,
    author_greenfield_intent,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)
from tests.unit.runtime.test_greenfield_model_path_custody import (
    _LIST_FIELDS,
    _TEXT_FIELDS,
)


def _terminal_intent(*, product_story: str = "", proof_boundary: str) -> dict[str, object]:
    return {
        **_TEXT_FIELDS,
        **_LIST_FIELDS,
        "title": "Pickup Relay",
        "product_story": product_story,
        "state_object": "donation batch",
        "first_path": (
            "Coordinator Nia records each donation and "
            "Pickup Relay releases each batch"
        ),
        "proof_boundary": proof_boundary,
        "success_metrics": ["Each donation batch is released"],
        "component_responsibilities": [],
        "human_actors": ["Coordinator Nia"],
    }


def _author_terminal_intent(
    intent: dict[str, object],
    *,
    result_quote: str,
):  # type: ignore[no-untyped-def]
    source = ". ".join(
        str(row)
        for value in intent.values()
        for row in (value if isinstance(value, list) else [value])
        if str(row)
    )
    result = author_greenfield_intent(
        evidence_text=source,
        provider=StructuredAuthoringProvider(
            authored_response(
                intent,
                evidence_text=source,
                terminal_component_owner="Pickup Relay",
                first_path_relations=[
                    {
                        "actor_kind": "human",
                        "actor_quote": "Coordinator Nia",
                        "event_quote": "Coordinator Nia records each donation",
                        "action_verb_quote": "records",
                        "target_quote": "each donation",
                        "visible_result_quote": "",
                        "recovery_path": False,
                    },
                    {
                        "actor_kind": "product",
                        "actor_quote": "Pickup Relay",
                        "owner_system_quote": "Pickup Relay",
                        "event_quote": "Pickup Relay releases each batch",
                        "action_verb_quote": "releases",
                        "target_quote": "each batch",
                        "visible_result_quote": result_quote,
                        "recovery_path": False,
                    },
                ],
            )
        ),
        clock=lambda: 0.0,
    )
    return result, source


def test_terminal_result_keeps_exact_proof_fact_custody_outside_final_event() -> None:
    result_quote = "pickup readiness"
    proof_boundary = "Verify pickup readiness after each released batch"
    result, source = _author_terminal_intent(
        _terminal_intent(proof_boundary=proof_boundary),
        result_quote=result_quote,
    )

    terminal_event = result.first_path_relations[-1]
    assert result_quote not in terminal_event["event_quote"]
    assert terminal_event["visible_result_quote"] == result_quote
    assert result.component_responsibility_relations[0]["responsibility_path"] == "/proof_boundary"
    visible_claim = next(
        row
        for row in result.atomic_claims
        if row["relation_role"] == "visible_result_quote"
    )
    assert visible_claim["projection_path"] == "/proof_boundary"
    assert visible_claim["projection_start_byte"] == proof_boundary.index(result_quote)
    source_bytes = source.encode("utf-8")
    assert (
        source_bytes[
            visible_claim["source_start_byte"] : visible_claim["source_end_byte"]
        ].decode("utf-8")
        == result_quote
    )


def test_terminal_result_keeps_selected_product_story_custody_across_sealed_validation() -> None:
    result_quote = "pickup readiness visible"
    product_story = "Pickup Relay makes pickup readiness visible to coordinators"
    result, _source = _author_terminal_intent(
        _terminal_intent(
            product_story=product_story,
            proof_boundary="Verify each released donation batch",
        ),
        result_quote=result_quote,
    )
    sealed_intent = {
        **result.intent,
        "authored_semantics": authored_semantics_mapping(
            result.first_path_relations,
            result.component_responsibility_relations,
            first_path_context_relations=result.first_path_context_relations,
        ),
    }

    validated = first_path_relations_from_intent(sealed_intent)

    assert validated[-1]["visible_result_quote"] == result_quote
    assert result.component_responsibility_relations[0]["responsibility_path"] == "/product_story"
    visible_claim = next(
        row for row in result.atomic_claims if row["relation_role"] == "visible_result_quote"
    )
    assert visible_claim["projection_path"] == "/product_story"
    assert visible_claim["projection_start_byte"] == product_story.index(result_quote)


def test_terminal_result_rejects_a_selected_non_output_fact() -> None:
    result_quote = "manual work remains hidden"
    intent = _terminal_intent(proof_boundary="Verify each released donation batch")
    intent["problem"] = f"Today {result_quote} from coordinators"

    with pytest.raises(
        GreenfieldModelAuthoringError,
        match="terminal result outside its selected facts",
    ):
        _author_terminal_intent(intent, result_quote=result_quote)
