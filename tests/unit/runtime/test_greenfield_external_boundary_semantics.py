from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import external_boundary_facts


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
