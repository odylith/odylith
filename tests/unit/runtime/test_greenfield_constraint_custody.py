"""Reviewer-owned operational-constraint custody contracts."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_constraint_custody import (
    candidate_review_sha256,
    constraint_custody_shape_issues,
    finalize_admitted_review,
    project_constraint_custody,
    validated_constraint_custody,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoringError,
    validate_greenfield_authoring_response,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _public_pattern() -> tuple[dict[str, object], list[dict[str, object]]]:
    constraints = [
        "Harbor Desk requires certification before release",
        "Harbor Desk keeps draft evidence private until publication",
        "Engineering reviewer Mara alone decides whether to publish draft evidence",
    ]
    candidate = deepcopy(_response(_source())["result"])
    candidate["facts"]["operational_constraints"] = [
        {"quote": quote, "occurrence": 1} for quote in constraints
    ]
    candidate["facts"]["human_actors"].append(
        {"quote": "Engineering reviewer Mara", "occurrence": 1}
    )
    custody = [
        {
            "constraint_index": 1,
            "kind": "product_owned",
            "owner_fact": {"field": "title", "row": 1},
        },
        {
            "constraint_index": 2,
            "kind": "product_owned",
            "owner_fact": {"field": "title", "row": 1},
        },
        {
            "constraint_index": 3,
            "kind": "participant_only",
            "actor_fact": {"field": "human_actors", "row": 2},
        },
    ]
    return candidate, custody


def test_public_three_constraint_pattern_projects_only_product_owned_and_binds_hashes() -> None:
    candidate, custody = _public_pattern()
    review_input_hash = candidate_review_sha256(candidate)

    projected = project_constraint_custody(candidate, custody=custody)
    review = finalize_admitted_review(
        {
            "status": "admitted",
            "review_input_candidate_sha256": review_input_hash,
            "admission_witness": {"constraint_custody": custody},
        },
        candidate=projected,
    )

    title_component = next(
        row for row in projected["components"] if row["owner_fact_quote"] == "Harbor Desk"
    )
    projected_quotes = [row["quote"] for row in title_component["responsibilities"]]
    assert projected_quotes.count("Harbor Desk requires certification before release") == 1
    assert projected_quotes.count("Harbor Desk keeps draft evidence private until publication") == 1
    assert "Engineering reviewer Mara alone decides whether to publish draft evidence" not in projected_quotes
    assert candidate_review_sha256(candidate) == review["review_input_candidate_sha256"]
    assert candidate_review_sha256(projected) == review["candidate_sha256"]
    assert review["candidate_sha256"] != review["review_input_candidate_sha256"]


def test_workflow_order_requires_the_current_constraint_precedence_binding() -> None:
    candidate = deepcopy(_response(_source())["result"])
    candidate["source_precedence"] = [
        {"before_event": 1, "after_event": 2, "constraint_index": 1}
    ]
    custody = [{"constraint_index": 1, "kind": "workflow_order"}]

    assert validated_constraint_custody(custody, candidate=candidate) == tuple(custody)
    candidate["source_precedence"] = []
    with pytest.raises(RuntimeError, match="invalid constraint custody"):
        validated_constraint_custody(custody, candidate=candidate)


def test_product_projection_rejects_duplicate_canonical_relation() -> None:
    candidate, custody = _public_pattern()
    candidate["facts"]["operational_constraints"][1] = deepcopy(
        candidate["facts"]["operational_constraints"][0]
    )

    with pytest.raises(RuntimeError, match="duplicate a component responsibility"):
        project_constraint_custody(candidate, custody=custody)


@pytest.mark.parametrize(
    "row",
    (
        {
            "constraint_index": True,
            "kind": "product_owned",
            "owner_fact": {"field": "title", "row": 1},
        },
        {
            "constraint_index": True,
            "kind": "participant_only",
            "actor_fact": {"field": "human_actors", "row": 1},
        },
        {"constraint_index": True, "kind": "workflow_order"},
    ),
)
def test_constraint_custody_rejects_boolean_indexes_for_every_variant(row) -> None:
    assert constraint_custody_shape_issues([row]) == (
        "constraint custody witness order is invalid",
    )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda rows: rows.pop(),
        lambda rows: rows.reverse(),
        lambda rows: rows[0].update(
            owner_fact={"field": "human_actors", "row": 1}
        ),
        lambda rows: rows[2].update(
            actor_fact={"field": "internal_systems", "row": 1}
        ),
    ),
)
def test_constraint_custody_rejects_cardinality_order_and_cross_kind_refs(mutation) -> None:
    candidate, custody = _public_pattern()
    mutation(custody)

    with pytest.raises(RuntimeError, match="invalid constraint custody"):
        validated_constraint_custody(custody, candidate=candidate)


def test_canonical_authoring_rejects_author_owned_constraint_copy() -> None:
    source = _source()
    response = _response(source)
    constraint = deepcopy(response["result"]["facts"]["operational_constraints"][0])
    response["result"]["components"][0]["responsibilities"].append(constraint)

    with pytest.raises(GreenfieldModelAuthoringError, match="copied an operational constraint"):
        validate_greenfield_authoring_response(
            response,
            evidence_text=source,
            elapsed_seconds=0.0,
            provider={"provider": "test"},
            profile_id=STANDARD_PROFILE_ID,
            effective_timeout_seconds=1.0,
            semantic_model_call_count=1,
        )
