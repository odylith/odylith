from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import intent_hypothesis_from_operator_evidence
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import external_boundary_facts
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import is_external_dependency_clause
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import source_boundary_rows_from_evidence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import ranked_first_path_evidence


_FIRST_PATH = (
    "County emergency coordinators ingest shelter capacity reports, road closure feeds, "
    "medical transport constraints, and animal evacuation needs, then publish a reviewed "
    "evacuation readiness state with accountable assignments and public update proof."
)


def _intent() -> dict[str, object]:
    return {
        "title": "Wildfire Mutual Aid Evacuation Operations",
        "product_story": (
            "County emergency coordinators need one reviewable workspace that turns changing evacuation "
            "inputs into a trusted readiness state with assignments, blockers, and public update proof visible."
        ),
        "state_object": (
            "An evacuation readiness state tracks shelter capacity, road availability, transport limits, "
            "animal evacuation needs, accountable assignments, blockers, evidence, and public update proof."
        ),
        "first_path": _FIRST_PATH,
        "proof_boundary": (
            "Release 0.0.1 succeeds when coordinators can ingest the named source inputs, publish the "
            "reviewed readiness state, inspect assignment proof, and see clear blockers when input is missing."
        ),
        "human_actors": [
            "County emergency coordinators - review evacuation readiness and publish accountable assignments.",
        ],
        "external_systems": [],
        "internal_systems": [
            "Evacuation Input Register - records accepted source inputs and blocked input gaps.",
            "Readiness Review Board - publishes the reviewed readiness state and assignment proof.",
        ],
        "assumptions": [],
        "ambiguities": [],
        "non_goals": [],
    }


def test_external_boundary_facts_identify_named_source_inputs_without_domain_rules() -> None:
    facts = external_boundary_facts(_FIRST_PATH)

    source_labels = {fact.label for fact in facts if fact.confidence == "source"}
    ambiguous_labels = {fact.label for fact in facts if fact.confidence == "ambiguous"}

    assert "Shelter capacity reports" in source_labels
    assert "Road closure feeds" in source_labels
    assert "Medical transport constraints" in ambiguous_labels
    assert "Animal evacuation needs" in ambiguous_labels


def test_confirmed_completion_preserves_external_boundary_into_semantic_model() -> None:
    completed = complete_confirmed_intent(_intent())
    proposal = build_confirmed_greenfield_proposal(
        prompt="Create a wildfire mutual-aid evacuation operations workspace.",
        title=str(completed["title"]),
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=completed,
    )

    external_rows = completed["external_systems"]
    ontology = proposal["semantic_model"]["domain_ontology"]

    assert any("Shelter capacity reports" in row for row in external_rows)
    assert any("Road closure feeds" in row for row in external_rows)
    assert any("medical transport constraints" in row.casefold() for row in completed["ambiguities"])
    assert ontology["external_systems"] == external_rows


@pytest.mark.parametrize(
    ("evidence", "expected"),
    (
        ("Room availability is read from the Hall Calendar.", "Hall Calendar"),
        ("Object codes come from Collection Shelf.", "Collection Shelf"),
        ("Tide Ledger supplies berth assignments; the product cannot edit it.", "Tide Ledger"),
        ("Stripe provides the accepted payment status.", "Stripe"),
        ("Customer Billing System supplies the account balance.", "Customer Billing System"),
        ("The first path depends on the mapping gateway.", "mapping gateway"),
        ("It relies on the mapping gateway.", "mapping gateway"),
        ("Route stewards read the forecast service before review.", "forecast service"),
        ("Reviewers cross-reference the seismic registry with every bore log.", "seismic registry"),
        ("A courier collects labeled specimens for the regional laboratory.", "regional laboratory"),
        ('{"path":["scan tag","show due date"],"source":"Tool Shelf Index"}', "Tool Shelf Index"),
    ),
)
def test_source_boundary_rows_preserve_named_sources_across_evidence_shapes(evidence: str, expected: str) -> None:
    assert source_boundary_rows_from_evidence(evidence) == [expected]


@pytest.mark.parametrize(
    "evidence",
    (
        "It relies on the mapping gateway.",
        "The first path depends on the Hall Calendar.",
        "Harbor Slate relies on Tide Ledger.",
    ),
)
def test_external_dependency_clause_identifies_non_human_boundary_statements(evidence: str) -> None:
    assert is_external_dependency_clause(evidence)


@pytest.mark.parametrize(
    "evidence",
    (
        "A coordinator relies on the mapping gateway to review a site.",
        "The archive relies on the Hall Calendar to prepare a receipt.",
        "The product records a site and relies on the mapping gateway.",
        "The product displays the accepted mapping result.",
    ),
)
def test_external_dependency_clause_does_not_absorb_human_or_mixed_workflows(evidence: str) -> None:
    assert not is_external_dependency_clause(evidence)


def test_dependency_with_action_tail_remains_eligible_first_path_evidence() -> None:
    evidence = "The archive relies on the Hall Calendar to prepare a receipt."

    assert ranked_first_path_evidence(evidence) == evidence.rstrip(".")


def test_operator_evidence_hypothesis_preserves_named_prompt_source() -> None:
    evidence = (
        "Build a room request workspace. A coordinator records one room request and sees the held time. "
        "Room availability is read from the Hall Calendar."
    )

    hypothesis = intent_hypothesis_from_operator_evidence(evidence, prefer_product_title=True)

    assert hypothesis["external_systems"] == ("Hall Calendar",)


def test_source_boundary_rejects_product_relative_clause_with_input_carrier() -> None:
    evidence = (
        "Create a proposal for an open source security embargo room that receives vulnerability reports, "
        "coordinates maintainer triage, and shows advisory readiness."
    )

    assert source_boundary_rows_from_evidence(evidence) == []


def test_source_boundary_does_not_treat_received_reports_as_a_supplier_action() -> None:
    evidence = (
        "Create a greenfield proposal for a cross-organization disclosure council that receives reports, "
        "coordinates review, records evidence custody, and decides embargo status."
    )

    assert source_boundary_rows_from_evidence(evidence) == []
    assert intent_hypothesis_from_operator_evidence(evidence, prefer_product_title=True)["external_systems"] == ()


def test_source_boundary_preserves_reports_as_a_real_supplier_action() -> None:
    assert source_boundary_rows_from_evidence("Disclosure Registry reports accepted status.") == [
        "Disclosure Registry"
    ]


def test_prompt_prose_does_not_override_an_empty_structured_external_boundary() -> None:
    intent = _intent()
    intent.update(
        {
            "prompt": (
                "A coordinator records one room request and sees the held time. Room availability is read from "
                "the Hall Calendar."
            ),
            "first_path": "A coordinator records one room request and sees the held time.",
            "external_systems": [],
        }
    )

    completed = complete_confirmed_intent(intent)

    assert completed["external_systems"] == []


@pytest.mark.parametrize(
    "evidence",
    (
        "Perch Note returns a shift summary.",
        "The product provides a daily summary.",
        "The service supplies a daily summary.",
        "The system provides a daily summary.",
        "Requirements come from customer interviews.",
        '{"dependencies":["barcode scanner","wifi"]}',
    ),
)
def test_source_boundary_rows_reject_false_external_dependencies(evidence: str) -> None:
    assert source_boundary_rows_from_evidence(evidence) == []


def test_source_boundary_rows_trim_trailing_product_action() -> None:
    evidence = "Room availability is read from Hall Calendar and shown to the coordinator."

    assert source_boundary_rows_from_evidence(evidence) == ["Hall Calendar"]


def test_source_boundary_rows_isolate_supplier_after_prior_action() -> None:
    evidence = "A coordinator checks a request and the Mapping Gateway supplies site context."

    assert source_boundary_rows_from_evidence(evidence) == ["Mapping Gateway"]


def test_source_boundary_rows_isolate_supplier_after_modal_action() -> None:
    evidence = "A coordinator can check a request and Mapping Gateway supplies site context."

    assert source_boundary_rows_from_evidence(evidence) == ["Mapping Gateway"]


def test_source_boundary_rows_exclude_the_known_product_title() -> None:
    evidence = (
        "Orchard Bin Ledger gives Mara a return path. "
        "Mara records a returned crate using Orchard Bin Ledger. "
        "The Grove Roster supplies lot names."
    )

    assert source_boundary_rows_from_evidence(evidence) == ["Orchard Bin Ledger", "Grove Roster"]
    assert source_boundary_rows_from_evidence(
        evidence,
        excluded_labels=("Orchard Bin Ledger",),
    ) == ["Grove Roster"]


def test_operator_evidence_does_not_classify_its_product_as_external() -> None:
    evidence = (
        "Orchard Bin Ledger gives Mara a return path. "
        "Mara records a returned crate using Orchard Bin Ledger. "
        "The Grove Roster supplies lot names."
    )

    hypothesis = intent_hypothesis_from_operator_evidence(evidence, prefer_product_title=True)

    assert hypothesis["external_systems"] == ("Grove Roster",)


@pytest.mark.parametrize("connector", ("because", "if", "that", "when"))
def test_source_boundary_rows_stop_before_conditional_or_relative_tail(connector: str) -> None:
    evidence = f"The release depends on the mapping gateway {connector} weather changes."

    assert source_boundary_rows_from_evidence(evidence) == ["mapping gateway"]


@pytest.mark.parametrize(
    "evidence",
    (
        "Reviewers check the Permit Receipt before approval.",
        "A coordinator routes the request through Alice.",
    ),
)
def test_source_boundary_rows_reject_capitalized_non_system_objects(evidence: str) -> None:
    assert source_boundary_rows_from_evidence(evidence) == []


def test_source_boundary_rows_preserve_device_carriers() -> None:
    assert source_boundary_rows_from_evidence("Operators query the shoreline sensor.") == [
        "shoreline sensor"
    ]
