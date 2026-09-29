"""Reviewer-owned component and constraint custody contracts."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_review_custody import (
    candidate_for_pre_review_validation,
    candidate_review_sha256,
    candidate_review_value,
    component_custody_shape_issues,
    constraint_custody_shape_issues,
    finalize_admitted_review,
    project_reviewed_custody,
    source_precedence_custody_shape_issues,
    validated_component_custody,
    validated_constraint_custody,
    validated_source_precedence_custody,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GreenfieldModelAuthoringError,
    validate_greenfield_authoring_response,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


def _review_input() -> dict[str, object]:
    candidate = deepcopy(_response(_source())["result"])
    candidate.pop("components")
    candidate.pop("source_precedence")
    return candidate


def _component_custody() -> dict[str, list[dict[str, object]]]:
    return {
        "event_responsibilities": [
            {
                "event_order": 2,
                "responsibility_citation": {
                    "quote": "the product records berth occupancy",
                    "occurrence": 1,
                },
            },
            {
                "event_order": 3,
                "responsibility_citation": {
                    "quote": "the berth map shows the placement",
                    "occurrence": 1,
                },
            },
        ],
        "additional_responsibilities": [
            {
                "owner_fact": {"field": "internal_systems", "row": 1},
                "responsibility_citation": {
                    "quote": "Record berth occupancy",
                    "occurrence": 1,
                },
            }
        ],
    }


def _constraint_custody(*, product_owned: bool = False) -> list[dict[str, object]]:
    if product_owned:
        return [
            {
                "constraint_index": 1,
                "kind": "product_owned",
                "owner_fact": {"field": "internal_systems", "row": 1},
            }
        ]
    return [
        {
            "constraint_index": 1,
            "kind": "participant_only",
            "actor_fact": {"field": "human_actors", "row": 1},
        }
    ]


def test_review_input_has_no_final_relations_and_final_hash_binds_all_projections() -> None:
    candidate = _review_input()
    review_value = candidate_review_value(candidate)
    assert "components" not in review_value["accepted_source"]
    assert "source_precedence" not in review_value["accepted_source"]
    validation_candidate = candidate_for_pre_review_validation(candidate)
    assert validation_candidate["components"] == []
    assert validation_candidate["source_precedence"] == []
    input_hash = candidate_review_sha256(candidate)

    projected = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=[],
        constraint_custody=_constraint_custody(product_owned=True),
        evidence_text=_source(),
    )
    review = finalize_admitted_review(
        {
            "status": "admitted",
            "review_input_candidate_sha256": input_hash,
        },
        candidate=projected,
    )

    assert review["review_input_candidate_sha256"] == input_hash
    assert review["candidate_sha256"] == candidate_review_sha256(projected)
    assert review["candidate_sha256"] != input_hash
    responsibilities = projected["components"][0]["responsibilities"]
    assert [row["quote"] for row in responsibilities] == [
        "the product records berth occupancy",
        "the berth map shows the placement",
        "Record berth occupancy",
        "Retain source notes for seven years",
    ]


@pytest.mark.parametrize(
    "mutation",
    (
        lambda custody: custody["event_responsibilities"].pop(),
        lambda custody: custody["event_responsibilities"].insert(
            0,
            {
                "event_order": 1,
                "responsibility_citation": {
                    "quote": "Dock attendant Ivo enters a vessel tag",
                    "occurrence": 1,
                },
            },
        ),
    ),
)
def test_component_custody_requires_exact_product_event_coverage(mutation) -> None:
    custody = _component_custody()
    mutation(custody)
    with pytest.raises(RuntimeError, match="invalid component custody"):
        validated_component_custody(
            custody,
            candidate=_review_input(),
            evidence_text=_source(),
        )


def test_event_responsibility_must_be_contained_by_its_exact_event() -> None:
    custody = _component_custody()
    custody["event_responsibilities"][0]["responsibility_citation"] = {
        "quote": (
            "Dock attendant Ivo enters a vessel tag and the product records berth occupancy"
        ),
        "occurrence": 1,
    }
    with pytest.raises(RuntimeError, match="invalid component custody"):
        validated_component_custody(
            custody,
            candidate=_review_input(),
            evidence_text=_source(),
        )


@pytest.mark.parametrize("row", (True, 0, -1, 2))
def test_additional_responsibility_requires_a_strictly_bound_product_owner(row) -> None:
    custody = _component_custody()
    custody["additional_responsibilities"][0]["owner_fact"]["row"] = row
    with pytest.raises(RuntimeError, match="invalid component custody"):
        validated_component_custody(
            custody,
            candidate=_review_input(),
            evidence_text=_source(),
        )


def test_additional_responsibility_requires_exact_source_resolution() -> None:
    custody = _component_custody()
    custody["additional_responsibilities"][0]["responsibility_citation"][
        "occurrence"
    ] = 7
    with pytest.raises(RuntimeError, match="invalid component custody"):
        validated_component_custody(
            custody,
            candidate=_review_input(),
            evidence_text=_source(),
        )


def test_component_custody_rejects_duplicate_and_cross_owner_reuse() -> None:
    candidate = _review_input()
    candidate["facts"]["internal_systems"].append(
        {"quote": "Harbor Desk", "occurrence": 1}
    )
    custody = _component_custody()
    custody["additional_responsibilities"].append(
        {
            "owner_fact": {"field": "internal_systems", "row": 2},
            "responsibility_citation": {
                "quote": "Record berth occupancy",
                "occurrence": 1,
            },
        }
    )
    with pytest.raises(RuntimeError, match="invalid component custody"):
        validated_component_custody(
            custody,
            candidate=candidate,
            evidence_text=_source(),
        )


def test_component_custody_rejects_operational_constraint_overlap() -> None:
    custody = _component_custody()
    custody["additional_responsibilities"][0]["responsibility_citation"] = {
        "quote": "Retain source notes for seven years",
        "occurrence": 1,
    }
    with pytest.raises(RuntimeError, match="invalid component custody"):
        validated_component_custody(
            custody,
            candidate=_review_input(),
            evidence_text=_source(),
        )


def test_product_event_may_also_be_the_exact_product_owned_constraint() -> None:
    candidate = _review_input()
    event_citation = deepcopy(candidate["facts"]["first_path"][1])
    candidate["facts"]["operational_constraints"] = [event_citation]
    custody = _component_custody()
    custody["additional_responsibilities"] = []

    projected = project_reviewed_custody(
        candidate,
        component_custody=custody,
        source_precedence_custody=[],
        constraint_custody=[
            {
                "constraint_index": 1,
                "kind": "product_owned",
                "owner_fact": {"field": "internal_systems", "row": 1},
            }
        ],
        evidence_text=_source(),
    )

    responsibilities = projected["components"][0]["responsibilities"]
    assert responsibilities.count(event_citation) == 1
    validated = validate_greenfield_authoring_response(
        {"version": _response(_source())["version"], "result": projected},
        evidence_text=_source(),
        elapsed_seconds=0.0,
        provider={"provider": "test"},
        profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=1.0,
        semantic_model_call_count=1,
        reviewer_projected_constraints=True,
    )
    assert validated.intent["operational_constraints"] == [event_citation["quote"]]


def test_dual_role_clause_cannot_change_owner_during_constraint_projection() -> None:
    candidate = _review_input()
    event_citation = deepcopy(candidate["facts"]["first_path"][1])
    candidate["facts"]["operational_constraints"] = [event_citation]
    custody = _component_custody()
    custody["additional_responsibilities"] = []

    with pytest.raises(RuntimeError, match="conflicts with component ownership"):
        project_reviewed_custody(
            candidate,
            component_custody=custody,
            source_precedence_custody=[],
            constraint_custody=[
                {
                    "constraint_index": 1,
                    "kind": "product_owned",
                    "owner_fact": {"field": "title", "row": 1},
                }
            ],
            evidence_text=_source(),
        )


def test_component_custody_shape_rejects_bool_indexes() -> None:
    custody = _component_custody()
    custody["event_responsibilities"][0]["event_order"] = True
    assert component_custody_shape_issues(custody) == (
        "component custody event witness shape is invalid",
    )


def test_public_constraint_pattern_projects_only_product_owned_rows() -> None:
    candidate = _review_input()
    constraints = [
        "Harbor Desk requires certification before release",
        "Harbor Desk keeps draft evidence private until publication",
        "Engineering reviewer Mara alone decides whether to publish draft evidence",
    ]
    evidence = _source() + " " + ". ".join(constraints) + "."
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

    projected = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=[],
        constraint_custody=custody,
        evidence_text=evidence,
    )

    title_component = next(
        row for row in projected["components"] if row["owner_fact_quote"] == "Harbor Desk"
    )
    projected_quotes = [row["quote"] for row in title_component["responsibilities"]]
    assert projected_quotes.count(constraints[0]) == 1
    assert projected_quotes.count(constraints[1]) == 1
    assert constraints[2] not in projected_quotes


def test_workflow_order_requires_the_current_constraint_precedence_binding() -> None:
    candidate = _review_input()
    candidate["source_precedence"] = [
        {"before_event": 1, "after_event": 2, "constraint_index": 1}
    ]
    custody = [{"constraint_index": 1, "kind": "workflow_order"}]

    assert validated_constraint_custody(custody, candidate=candidate) == tuple(custody)
    candidate["source_precedence"] = []
    with pytest.raises(RuntimeError, match="invalid constraint custody"):
        validated_constraint_custody(custody, candidate=candidate)


def test_reviewed_precedence_projects_before_workflow_order_custody() -> None:
    candidate = _review_input()
    precedence = [
        {"before_event": 1, "after_event": 2, "constraint_index": 1}
    ]

    projected = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=precedence,
        constraint_custody=[{"constraint_index": 1, "kind": "workflow_order"}],
        evidence_text=_source(),
    )

    assert projected["source_precedence"] == precedence


def test_passive_or_unowned_timing_can_retain_empty_precedence() -> None:
    original_constraint = "Retain source notes for seven years"
    passive_timing = "Harbor Desk keeps draft evidence private until publication"
    evidence = _source().replace(original_constraint, passive_timing)
    candidate = _review_input()
    candidate["facts"]["operational_constraints"] = [
        {"quote": passive_timing, "occurrence": 1}
    ]

    assert all(
        "publication" not in {
            event["action_quote"],
            event["target_quote"],
        }
        for event in candidate["events"]
    )

    projected = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=[],
        constraint_custody=[
            {
                "constraint_index": 1,
                "kind": "product_owned",
                "owner_fact": {"field": "title", "row": 1},
            }
        ],
        evidence_text=evidence,
    )
    validated = validate_greenfield_authoring_response(
        {"version": _response(_source())["version"], "result": projected},
        evidence_text=evidence,
        elapsed_seconds=0.0,
        provider={"provider": "test"},
        profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=1.0,
        semantic_model_call_count=1,
        reviewer_projected_constraints=True,
    )

    assert projected["source_precedence"] == []
    assert validated.source_precedence == ()
    assert validated.intent["operational_constraints"] == [passive_timing]


@pytest.mark.parametrize(
    "precedence",
    (
        [
            {"before_event": 1, "after_event": 2, "constraint_index": 1},
            {"before_event": 1, "after_event": 2, "constraint_index": 1},
        ],
        [
            {"before_event": 1, "after_event": 2, "constraint_index": 1},
            {"before_event": 2, "after_event": 1, "constraint_index": 1},
        ],
        [{"before_event": 4, "after_event": 2, "constraint_index": 1}],
        [{"before_event": 1, "after_event": 2, "constraint_index": 2}],
    ),
)
def test_source_precedence_custody_rejects_invalid_relations(precedence) -> None:
    with pytest.raises(RuntimeError, match="invalid source precedence custody"):
        validated_source_precedence_custody(
            precedence,
            candidate=_review_input(),
        )


def test_source_precedence_custody_rejects_boolean_references() -> None:
    assert source_precedence_custody_shape_issues(
        [{"before_event": True, "after_event": 2, "constraint_index": 1}]
    ) == ("source precedence custody witness shape is invalid",)


def test_workflow_order_without_projected_binding_fails_atomically() -> None:
    candidate = _review_input()

    with pytest.raises(RuntimeError, match="invalid constraint custody"):
        project_reviewed_custody(
            candidate,
            component_custody=_component_custody(),
            source_precedence_custody=[],
            constraint_custody=[
                {"constraint_index": 1, "kind": "workflow_order"}
            ],
            evidence_text=_source(),
        )

    assert "source_precedence" not in candidate
    assert "components" not in candidate


def test_final_hash_separates_review_input_and_precedence_projection() -> None:
    candidate = _review_input()
    left = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=[
            {"before_event": 1, "after_event": 2, "constraint_index": 1}
        ],
        constraint_custody=[{"constraint_index": 1, "kind": "workflow_order"}],
        evidence_text=_source(),
    )
    right = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=[
            {"before_event": 1, "after_event": 3, "constraint_index": 1}
        ],
        constraint_custody=[{"constraint_index": 1, "kind": "workflow_order"}],
        evidence_text=_source(),
    )

    assert candidate_review_sha256(candidate) not in {
        candidate_review_sha256(left),
        candidate_review_sha256(right),
    }
    assert candidate_review_sha256(left) != candidate_review_sha256(right)


def test_final_validation_rejects_first_run_incompatible_with_projected_precedence() -> None:
    candidate = _review_input()
    candidate["provisional_design"]["first_run"]["event_orders"] = [2, 1, 3]
    projected = project_reviewed_custody(
        candidate,
        component_custody=_component_custody(),
        source_precedence_custody=[
            {"before_event": 1, "after_event": 2, "constraint_index": 1}
        ],
        constraint_custody=[{"constraint_index": 1, "kind": "workflow_order"}],
        evidence_text=_source(),
    )

    with pytest.raises(GreenfieldModelAuthoringError, match="violates cited source precedence"):
        validate_greenfield_authoring_response(
            {"version": _response(_source())["version"], "result": projected},
            evidence_text=_source(),
            elapsed_seconds=0.0,
            provider={"provider": "test"},
            profile_id=STANDARD_PROFILE_ID,
            effective_timeout_seconds=1.0,
            semantic_model_call_count=1,
            reviewer_projected_constraints=True,
        )


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


def test_final_canonical_validation_rejects_constraint_component_overlap() -> None:
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
