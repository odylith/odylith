from __future__ import annotations

from odylith.runtime.domain_intelligence import (
    greenfield_component_semantic_contract_support as contract_support,
)
from odylith.runtime.domain_intelligence.greenfield_component_narrative_view import component_narrative_view


def test_profile_supplements_do_not_drop_late_semantic_contract_fragments() -> None:
    semantic_fragments = [f"semantic obligation {index}" for index in range(1, 14)]
    merged = contract_support.semantic_field_with_profile_supplements(
        ", ".join(semantic_fragments),
        "identity attachment, required document completeness, missing document blockers",
    )

    for fragment in semantic_fragments:
        assert fragment in merged
    assert "identity attachment" in merged
    assert "required document completeness" in merged
    assert "missing document blockers" in merged


def test_profile_supplements_do_not_reintroduce_generic_recordkeeping_shells() -> None:
    merged = contract_support.semantic_field_with_profile_supplements(
        "result status",
        "status recordkeeping",
    )

    assert merged == "result status"


def test_profile_merge_rejects_action_clauses_from_generated_owned_state() -> None:
    merged = contract_support.merge_profile_contract_fields(
        {
            "owned_state": "referral queue state, blocker state",
            "accepted_inputs": "referral request",
            "produced_outputs": "triage decision",
        },
        {
            "owned_state": "coordinator triage referral, assembles context provenance",
            "accepted_inputs": "coordinator identity",
            "produced_outputs": "review context",
        },
    )

    assert merged["owned_state"] == "referral queue state, blocker state"


def test_profile_obligation_guard_ignores_proof_floor_boilerplate_for_generic_evidence_rows() -> None:
    assert not contract_support.material_profile_obligations_survive(
        label="Evidence Intake Service",
        description="captures evidence context for analyst review",
        contract={
            "owned_state": "evidence queue state",
            "accepted_inputs": "analyst note and source event",
            "produced_outputs": "review packet",
            "states_or_transitions": "received, reviewed",
            "local_proof": [
                "Blocked input evidence for Evidence Intake Service: missing or malformed input stops before a trusted result.",
                "Replay evidence for Evidence Intake Service: actor, input facts, status, explanation, and proof trail.",
            ],
        },
    )


def test_profile_obligation_guard_accepts_material_document_context_obligations() -> None:
    assert contract_support.material_profile_obligations_survive(
        label="Packet Context Service",
        description="handles uploaded files and required documents for a review packet",
        contract={
            "owned_state": "packet identity attachment, required document completeness, uploaded document validation",
            "accepted_inputs": "source actor, uploaded files, and provenance notes",
            "produced_outputs": "validated packet, missing document blockers, and handoff context",
            "states_or_transitions": "incomplete, missing document blocking, uploaded, ready-for-review",
        },
    )


def test_component_narrative_prioritizes_blocker_obligations_over_source_metadata() -> None:
    view = component_narrative_view(
        label="Packet Context Service",
        owns=("packet identity",),
        accepts=("source actor", "document selections", "uploaded files", "provenance notes"),
        produces=(
            "packet identity evidence",
            "source metadata",
            "ready packet state",
            "missing document blockers",
            "uploaded-context metadata",
            "access decisions",
        ),
        transitions=("incomplete", "missing document blocking", "uploaded"),
        outside=(),
        proofs=(),
    )

    assert view.blocker_state_items[0] == "missing document blockers"
