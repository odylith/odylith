from __future__ import annotations

import copy

import pytest

from odylith.runtime.domain_intelligence.greenfield_semantic_source_candidate_adjudication import (
    require_semantic_source_candidate_adjudication,
    select_semantic_source_claims,
    semantic_source_candidate_adjudication_contract,
    semantic_source_candidate_adjudication_schema,
)


_ACTION_QUOTE = "The coordinator selects one ready intake card and marks it claimed."
_RESULT_QUOTE = (
    "The card moves from ready to claimed, and the coordinator sees a claim receipt."
)


def _ref(quote: str) -> list[dict[str, object]]:
    return [{"source_id": "operator_prompt", "quote": quote, "occurrence": 1}]


def _fact(
    fact_id: str,
    kind: str,
    label: str,
    order: int,
    quote: str,
    *,
    owner_kind: str = "none",
) -> dict[str, object]:
    attributes = []
    if kind == "identity":
        attributes = [{"name": "source_title", "value": label}]
    elif kind == "actor":
        attributes = [{"name": "responsibility", "value": "select and claim one card"}]
    elif kind == "workflow_step":
        attributes = [
            {"name": "action", "value": label.lower()},
            {"name": "action_phrase", "value": label.lower()},
        ]
    elif kind == "state_object":
        attributes = [{"name": "object", "value": "intake card"}]
    row: dict[str, object] = {
        "fact_id": fact_id,
        "kind": kind,
        "label": label,
        "statement": label + ".",
        "order": order,
        "owner_kind": owner_kind,
        "custody": "source_fact",
        "attributes": attributes,
        "source_refs": _ref(quote),
    }
    if kind == "state_object":
        row["transition"] = {"from_state": "ready", "to_state": "claimed"}
    return row


def _relation(
    relation_id: str,
    kind: str,
    subject: str,
    object_id: str,
    order: int,
    quote: str,
) -> dict[str, object]:
    return {
        "relation_id": relation_id,
        "kind": kind,
        "subject_id": subject,
        "object_id": object_id,
        "order": order,
        "custody": "source_fact",
        "source_refs": _ref(quote),
    }


def _claims() -> dict[str, object]:
    facts = [
        ("identity", _fact("identity", "identity", "Handoff board", 0, _ACTION_QUOTE)),
        ("role", _fact("actor", "actor", "Shift coordinator", 0, _ACTION_QUOTE)),
        (
            "first_path",
            _fact(
                "select",
                "workflow_step",
                "Select a ready intake card",
                0,
                _ACTION_QUOTE,
                owner_kind="actor",
            ),
        ),
        (
            "first_path",
            _fact(
                "mark",
                "workflow_step",
                "Mark the card claimed",
                1,
                _ACTION_QUOTE,
                owner_kind="actor",
            ),
        ),
        (
            "first_path",
            _fact(
                "see",
                "workflow_step",
                "See a claim receipt",
                2,
                _RESULT_QUOTE,
                owner_kind="actor",
            ),
        ),
        ("state_object", _fact("state", "state_object", "Intake card", 0, _RESULT_QUOTE)),
        (
            "visible_result",
            _fact("receipt", "visible_output", "Claim receipt", 0, _RESULT_QUOTE),
        ),
    ]
    relations = [
        (["first_path", "role"], _relation("owner-select", "owned_by", "select", "actor", 0, _ACTION_QUOTE)),
        (["first_path", "role"], _relation("owner-mark", "owned_by", "mark", "actor", 1, _ACTION_QUOTE)),
        (["first_path", "role"], _relation("owner-see", "owned_by", "see", "actor", 2, _RESULT_QUOTE)),
        (["first_path", "state_object"], _relation("mark-state", "changes", "mark", "state", 0, _RESULT_QUOTE)),
        (["first_path", "visible_result"], _relation("mark-receipt", "produces", "mark", "receipt", 0, _RESULT_QUOTE)),
    ]
    return {
        "version": "odylith.greenfield.semantic-source-candidates.v1",
        "facts": [{"field": field, "fact": fact} for field, fact in facts],
        "relations": [
            {"fields": fields, "relation": relation} for fields, relation in relations
        ],
    }


def _decisions() -> dict[str, object]:
    return {
        "version": "odylith.greenfield.semantic-source-candidate-adjudication.v1",
        "workflow_decisions": [
            {
                "fact_id": "select",
                "decision": "retain_material_action",
                "material_effect": "accepts_or_selects_input",
            },
            {
                "fact_id": "mark",
                "decision": "retain_material_action",
                "material_effect": "mutates_domain_object",
            },
            {
                "fact_id": "see",
                "decision": "fold_into_visible_result",
                "target_fact_id": "receipt",
            },
        ],
    }


def test_candidate_adjudication_removes_result_observation_without_rewriting_claims() -> None:
    source = _claims()
    decisions, adjudicated = select_semantic_source_claims(
        source,
        _decisions(),
    )

    assert [
        row["fact"]["fact_id"]
        for row in adjudicated["facts"]
        if row["fact"]["kind"] == "workflow_step"
    ] == ["select", "mark"]
    assert [row["relation"]["relation_id"] for row in adjudicated["relations"]] == [
        "owner-select",
        "owner-mark",
        "mark-state",
        "mark-receipt",
    ]
    original = {row["fact"]["fact_id"]: row["fact"] for row in source["facts"]}
    projected = {row["fact"]["fact_id"]: row["fact"] for row in adjudicated["facts"]}
    assert projected["mark"] == original["mark"]
    assert projected["receipt"] == original["receipt"]


def test_every_locked_workflow_candidate_requires_one_decision() -> None:
    decisions = _decisions()
    decisions["workflow_decisions"].pop()
    with pytest.raises(ValueError, match="do not cover locked candidates"):
        require_semantic_source_candidate_adjudication(
            decisions, source_candidates=_claims()
        )


def test_fold_target_must_share_exact_source_custody() -> None:
    source = _claims()
    receipt = next(row["fact"] for row in source["facts"] if row["fact"]["fact_id"] == "receipt")
    receipt["source_refs"] = _ref(_ACTION_QUOTE)
    with pytest.raises(ValueError, match="shared exact source custody"):
        require_semantic_source_candidate_adjudication(
            _decisions(), source_candidates=source
        )


def test_candidate_with_independent_material_relation_cannot_be_folded() -> None:
    source = _claims()
    source["relations"].append(
        {
            "fields": ["first_path", "state_object"],
            "relation": _relation("see-state", "changes", "see", "state", 1, _RESULT_QUOTE),
        }
    )
    with pytest.raises(ValueError, match="independent material relation"):
        require_semantic_source_candidate_adjudication(
            _decisions(), source_candidates=source
        )


def test_duplicate_decisions_fail_closed() -> None:
    decisions = _decisions()
    decisions["workflow_decisions"][2] = copy.deepcopy(
        decisions["workflow_decisions"][1]
    )
    with pytest.raises(ValueError, match="incomplete or duplicated"):
        require_semantic_source_candidate_adjudication(
            decisions, source_candidates=_claims()
        )


def test_provider_schema_is_candidate_bound_and_has_no_text_rewrite_surface() -> None:
    schema = semantic_source_candidate_adjudication_schema(_claims())
    encoded = repr(schema)
    assert "select" in encoded and "mark" in encoded and "see" in encoded
    assert "label" not in encoded and "statement" not in encoded and "source_refs" not in encoded
    contract = semantic_source_candidate_adjudication_contract()
    assert "third_model_call" in contract["forbidden"]
    assert "regex_or_token_role_inference" in contract["forbidden"]


def test_generic_packet_schema_allows_a_first_path_clarification_without_candidates() -> None:
    schema = semantic_source_candidate_adjudication_schema()
    assert schema["properties"]["workflow_decisions"]["minItems"] == 0

    source = _claims()
    workflow_ids = {
        row["fact"]["fact_id"]
        for row in source["facts"]
        if row["fact"]["kind"] == "workflow_step"
    }
    source["facts"] = [
        row for row in source["facts"] if row["fact"]["fact_id"] not in workflow_ids
    ]
    source["relations"] = [
        row
        for row in source["relations"]
        if row["relation"]["subject_id"] not in workflow_ids
        and row["relation"]["object_id"] not in workflow_ids
    ]
    selected, claims = select_semantic_source_claims(
        source,
        {
            "version": "odylith.greenfield.semantic-source-candidate-adjudication.v1",
            "workflow_decisions": [],
        },
    )
    assert selected["workflow_decisions"] == []
    assert all(row["fact"]["kind"] != "workflow_step" for row in claims["facts"])
