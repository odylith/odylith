from __future__ import annotations

from odylith.runtime.common.prose_grammar import modal_base_form_drift_phrases
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_backlog_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_first_path_carried_subjects import carried_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text


FLOOD_SHELTER_PROMPT = (
    "Build a flood shelter intake coordination system for a city emergency team. "
    "Residents request beds, coordinators verify accessibility needs, shelters publish accepted assignments, "
    "and public officials track capacity evidence without exposing private details. "
    "The first release should handle one region, keep a clear audit trail, and defer predictive routing."
)

DECISION_EVIDENCE_PROMPT = (
    "Create a greenfield proposal for a decision evidence room where multiple teams bring requests, "
    "review supporting facts, decide what is ready, preserve rationale, and publish proof for later governance review."
)


def test_first_path_steps_repair_carried_modal_base_form_drift() -> None:
    steps = first_path_steps(
        "A city emergency team. Residents request beds, coordinators verify accessibility needs, "
        "shelters publish accepted assignments, and public officials track capacity evidence without exposing private details. "
        "The first release should handle one region, keep a clear audit trail, and defer predictive routing."
    )

    assert "A city emergency team" not in steps
    assert steps[0] == "Residents request beds"
    assert "The first release should keep a clear audit trail, and defer predictive routing" in steps
    assert "The first release should keeps a clear audit trail, and defer predictive routing" not in steps
    assert not [
        phrase
        for step in steps
        for phrase in modal_base_form_drift_phrases(step)
    ]


def test_first_path_steps_preserve_plural_actor_can_base_form() -> None:
    steps = first_path_steps(
        "Digestive health patients can log meals and related inputs and prepare a clinician-ready "
        "follow-up summary with safety escalation notes."
    )

    assert steps == (
        "Digestive health patients can log meals and related inputs and prepare a clinician-ready follow-up summary with safety escalation notes",
    )
    assert sequence_event_steps(steps[0]) == [steps[0]]
    assert not any("patients logs" in step.casefold() for step in steps)
    assert not [phrase for step in steps for phrase in modal_base_form_drift_phrases(step)]


def test_first_path_steps_do_not_absorb_unknown_action_into_plural_actor_subject() -> None:
    steps = first_path_steps(
        "Multiple teams bring requests, review supporting facts, decide what is ready, "
        "preserve rationale, and publish proof for later governance review."
    )

    assert carried_subject_prefix("Multiple teams bring requests") == "Multiple teams"
    assert steps == (
        "Multiple teams bring requests",
        "Multiple teams review supporting facts",
        "Multiple teams decide what is ready",
        "Multiple teams preserve rationale",
        "Multiple teams publish proof for later governance review",
    )
    assert not [
        phrase
        for step in steps
        for phrase in modal_base_form_drift_phrases(step)
    ]


def test_first_path_steps_split_carried_subject_finite_group_action() -> None:
    steps = first_path_steps(
        "A case board member opens one agenda item, reviews the parcel map and zoning overlays, "
        "reads the staff recommendation and impact summary, groups public comments by concern, "
        "saves questions for staff, and sees claim-source traceability for the public record."
    )

    assert "A case board member reads the staff recommendation and impact summary" in steps
    assert "A case board member groups public comments by concern" in steps
    assert not any("summary, groups public comments" in step for step in steps)


def test_subjectless_action_chains_do_not_invent_carried_subjects() -> None:
    steps = first_path_steps(
        "ingests observation runs, records instrument state, tracks calibration exceptions, "
        "routes science lead review, and publishes release readiness for validated image products"
    )

    assert steps == (
        "Ingest observation runs",
        "Record instrument state",
        "Track calibration exceptions",
        "Route science lead review",
        "Publish release readiness for validated image products",
    )
    assert sequence_event_steps(", ".join(steps), dedupe=True) == [
        "Ingest observation runs",
        "Record instrument state",
        "Track calibration exceptions",
        "Route science lead review",
        "Publish release readiness for validated image products",
    ]

    carried_steps = first_path_steps(
        "the app records it, advances them along their titration schedule, and shows the next due date"
    )
    assert carried_steps == (
        "The app records it",
        "The app advances them along their titration schedule",
        "The app shows the next due date",
    )


def test_leading_purpose_context_is_preserved_on_first_action_step() -> None:
    steps = first_path_steps(
        "lead service-line abatement; intake household records, prioritize vulnerable sites, "
        "coordinate contractor windows, preserve lab sample evidence"
    )

    assert steps[0] == "Intake household records, prioritize vulnerable sites for lead service-line abatement"
    assert any("lead service-line abatement" in step for step in steps)
    assert "lead service-line abatement" not in steps


def test_confirmed_completion_repairs_modal_drift_from_recovered_host_guidance_intent() -> None:
    confirmation = build_product_intent_confirmation(
        prompt=FLOOD_SHELTER_PROMPT,
        title="Flood Shelter Intake Coordination System",
        repo_name="flood-shelter",
        observed_source={"source_posture": "docs_only"},
    )
    confirmed_intent = parse_confirmed_intent_text(
        format_product_intent_confirmation_text(confirmation),
        prompt=FLOOD_SHELTER_PROMPT,
        fallback_title="Flood Shelter Intake Coordination System",
    )
    assert "where a city emergency team" not in str(confirmed_intent["product_story"]).casefold()
    assert "residents request beds coordinators" not in str(confirmed_intent["product_story"]).casefold()
    assert str(confirmed_intent["first_path"]).startswith("Residents request beds.")
    assert any(str(row).startswith("Residents:") for row in confirmed_intent["human_actors"])

    proposal = build_confirmed_greenfield_proposal(
        prompt=str(confirmed_intent["prompt"]),
        title=str(confirmed_intent["title"]),
        observed_source={"source_posture": "confirmed_intent_only"},
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )
    proposal = normalize_host_reasoned_proposal(proposal)
    proposal = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    modal_issues = [
        issue
        for issue in generated_semantic_slop_issues(proposal, root="proposal")
        if "modal/base-form grammar drift" in issue
    ]
    assert modal_issues == []


def test_confirmed_completion_preserves_plural_actor_for_ambiguous_decision_evidence_prompt() -> None:
    confirmation = build_product_intent_confirmation(
        prompt=DECISION_EVIDENCE_PROMPT,
        title="Decision Evidence Room",
        repo_name="decision-evidence-room",
        observed_source={"source_posture": "confirmed_intent_only"},
    )
    confirmation_text = format_product_intent_confirmation_text(confirmation)

    assert "Multiple teams bring decides" not in confirmation_text
    assert "Multiple teams bring preserves" not in confirmation_text
    assert "Multiple teams bring publishes" not in confirmation_text
    assert "Multiple teams decide what is ready" in confirmation_text

    confirmed_intent = parse_confirmed_intent_text(
        confirmation_text,
        prompt=DECISION_EVIDENCE_PROMPT,
        fallback_title="Decision Evidence Room",
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt=str(confirmed_intent["prompt"]),
        title=str(confirmed_intent["title"]),
        observed_source={"source_posture": "confirmed_intent_only"},
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )
    proposal = normalize_host_reasoned_proposal(proposal)
    proposal = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    modal_issues = [
        issue
        for issue in generated_semantic_slop_issues(proposal, root="proposal")
        if "modal/base-form grammar drift" in issue
    ]
    assert modal_issues == []


def test_actor_owned_visible_result_is_not_reassigned_to_supporting_actor() -> None:
    rows = confirmed_backlog_rows(
        label="Flood Shelter Intake Coordination System",
        parent_title="Prove One Complete Flood Shelter Intake Coordination System Path",
        workflow_title="Let Residents Request Beds",
        boundary_title="Keep Flood Shelter Intake Coordination System State Clear and Reviewable",
        proof_title="Show Why Flood Shelter Intake Coordination System Can Be Trusted",
        state_object="Flood shelter intake state",
        evidence_record="Flood shelter intake proof record",
        product_story="A city emergency team coordinates shelter intake from resident requests to accepted assignments.",
        first_path=(
            "Residents request beds. Coordinators verify accessibility needs. Shelters publish accepted assignments. "
            "Public officials track capacity evidence without exposing private details. The first release should handle one region. "
            "The first release should keep a clear audit trail, and defer predictive routing."
        ),
        proof_boundary=(
            "Release 0.0.1 succeeds when residents can request beds, coordinators verify accessibility needs, "
            "shelters publish accepted assignments, and officials can review capacity evidence."
        ),
        human_actors=[
            "Residents: request beds.",
            "Coordinators: verify accessibility needs.",
            "Shelters: publish accepted assignments.",
            "Public officials: track capacity evidence.",
        ],
        internal_systems=["Intake workspace", "Assignment state", "Proof ledger"],
        external_systems=[],
        non_goals=["Predictive routing"],
        components=[
            {"component_id": "intake-workspace", "label": "Intake Workspace"},
            {"component_id": "assignment-state", "label": "Assignment State"},
            {"component_id": "proof-ledger", "label": "Proof Ledger"},
        ],
        diagram_slugs={
            "context": "context",
            "sequence": "sequence",
            "state_evidence": "state-evidence",
            "component_boundaries": "component-boundaries",
            "ownership": "ownership",
            "proof_review": "proof-review",
        },
    )

    rendered = "\n".join(str(value) for row in rows for value in row.values()).casefold()

    assert "coordinators can publish accepted assignments" not in rendered
    assert "lets the coordinators publish accepted assignments" not in rendered
    assert "let them publish accepted assignments" not in rendered
    assert "shows that shelters publish accepted assignments" in rendered
