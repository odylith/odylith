"""Provisional proof decisions never become accepted source terminals."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    authored_semantics_mapping,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
    GreenfieldModelAuthoredIntent,
    greenfield_authoring_schema,
    validate_greenfield_authoring_response,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import authored_response


_PROOF_ASSUMPTION = {
    "applies_to": "proof_boundary",
    "statement": "Use recorded occupancy as the first reviewable proof checkpoint.",
}
_INTENT = {
    "title": "Harbor Desk",
    "product_story": "Harbor Desk coordinates berth intake, recorded occupancy, and exception review",
    "state_object": "berth records",
    "first_path": "Harbor Desk coordinates berth intake, recorded occupancy, and exception review",
    "proof_boundary": "",
    "problem": "",
    "customer": "",
    "opportunity": "",
    "product_view": "",
    "success_metrics": [],
    "evidence_requirements": [],
    "operational_constraints": [],
    "component_responsibilities": [],
    "human_actors": [],
    "external_systems": [],
    "internal_systems": [],
    "assumptions": [
        {"applies_to": "problem", "statement": "Berth coordination needs one reviewable workspace."},
        {"applies_to": "customer", "statement": "Harbor operations teams are the primary users."},
        {"applies_to": "opportunity", "statement": "One workspace can make berth coordination easier to review."},
        {"applies_to": "product_view", "statement": "Teams can review coordinated berth records in one place."},
        _PROOF_ASSUMPTION,
    ],
    "ambiguities": [],
    "non_goals": [],
}


def _source() -> str:
    return (
        "Harbor Desk. Harbor Desk coordinates berth intake, recorded occupancy, "
        "and exception review. The workspace maintains berth records."
    )


def _source_terminal_response() -> dict[str, Any]:
    response = authored_response(
        _INTENT,
        evidence_text=_source(),
        first_path_relations=[
            {
                "actor_kind": "product",
                "actor_fact_quote": "Harbor Desk",
                "owner_system_quote": "Harbor Desk",
                "event_quote": _INTENT["first_path"],
                "action_verb_quote": "coordinates",
                "target_quote": "berth intake, recorded occupancy, and exception review",
                "visible_result_quote": "recorded occupancy",
            }
        ],
    )
    return response


def provisional_proof_response() -> tuple[str, dict[str, Any]]:
    """Return one generic source/candidate pair with no unique proof relation."""

    response = _source_terminal_response()
    result = response["result"]
    result["facts"]["proof_boundary"] = None
    result["terminal"] = None
    return _source(), response


def _validate(response: dict[str, Any]) -> GreenfieldModelAuthoredIntent:
    authored = validate_greenfield_authoring_response(
        response,
        evidence_text=_source(),
        elapsed_seconds=1.0,
        provider={"provider": "fixture"},
        profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=10.0,
        semantic_model_call_count=2,
    )
    assert isinstance(authored, GreenfieldModelAuthoredIntent)
    return authored


def provisional_proof_authored() -> tuple[str, GreenfieldModelAuthoredIntent]:
    """Return the canonical validated form of the disclosed provisional fixture."""

    source, response = provisional_proof_response()
    return source, _validate(response)


def test_schema_and_validator_keep_provisional_proof_out_of_source_truth() -> None:
    schema = greenfield_authoring_schema()
    authored_schema = schema["properties"]["result"]["anyOf"][0]
    facts_schema = authored_schema["properties"]["facts"]["properties"]
    assert GREENFIELD_INTENT_AUTHORING_VERSION.endswith(".v70")
    assert {row["type"] for row in facts_schema["proof_boundary"]["anyOf"]} == {
        "object",
        "null",
    }
    assert {row["type"] for row in authored_schema["properties"]["terminal"]["anyOf"]} == {
        "object",
        "null",
    }

    source_text, authored = provisional_proof_authored()

    assert _PROOF_ASSUMPTION["statement"] not in source_text
    assert authored.intent["proof_boundary"] == ""
    assert _PROOF_ASSUMPTION in authored.intent["assumptions"]
    assert all(not row["visible_result_quote"] for row in authored.first_path_relations)
    assert all(row["field"] != "proof_boundary" for row in authored.atomic_claims)
    assert all(row["relation_role"] != "visible_result_quote" for row in authored.atomic_claims)

    sealed = {
        **authored.intent,
        "authored_semantics": authored_semantics_mapping(
            authored.first_path_relations,
            authored.component_responsibility_relations,
            first_path_context_relations=authored.first_path_context_relations,
            source_precedence=authored.source_precedence,
            provisional_design=authored.provisional_design,
        ),
    }
    assert all(
        not row["visible_result_quote"] for row in first_path_relations_from_intent(sealed)
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda response: response["result"].update(
                {"terminal": _source_terminal_response()["result"]["terminal"]}
            ),
            "mixed source terminal and provisional proof authority",
        ),
        (
            lambda response: response["result"].update(
                {
                    "assumptions": [
                        row
                        for row in response["result"]["assumptions"]
                        if row["applies_to"] != "proof_boundary"
                    ]
                }
            ),
            "one source fact or one assumption",
        ),
        (
            lambda response: response["result"]["facts"].update(
                {
                    "proof_boundary": {
                        "quote": "recorded occupancy",
                        "occurrence": 1,
                    }
                }
            ),
            "one source fact or one assumption",
        ),
    ],
)
def test_provisional_proof_rejects_mixed_or_missing_authority(mutate, message) -> None:
    _source_text, response = provisional_proof_response()
    mutate(response)
    with pytest.raises(GreenfieldModelAuthoringError, match=message):
        _validate(response)


def test_source_proof_still_requires_a_source_terminal() -> None:
    response = _source_terminal_response()
    response["result"]["facts"]["proof_boundary"] = {
        "quote": "recorded occupancy",
        "occurrence": 1,
    }
    response["result"]["assumptions"] = [
        row
        for row in response["result"]["assumptions"]
        if row["applies_to"] != "proof_boundary"
    ]
    response["result"]["terminal"] = None

    with pytest.raises(
        GreenfieldModelAuthoringError,
        match="mixed source terminal and provisional proof authority",
    ):
        _validate(response)
