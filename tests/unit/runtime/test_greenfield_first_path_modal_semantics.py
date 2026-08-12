from __future__ import annotations

import copy
import json
from pathlib import Path

from odylith.runtime.common.prose_grammar import modal_base_form_drift_phrases
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_backlog_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    workstream_subject as backlog_workstream_subject,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import greenfield_apply_semantic_input
from odylith.runtime.domain_intelligence.greenfield_first_path_carried_subjects import carried_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_action_split import split_action_pieces
from odylith.runtime.domain_intelligence.greenfield_actor_led_open_action import actor_led_open_action_parts
from odylith.runtime.domain_intelligence.greenfield_sequence_steps import sequence_event_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_action_homonym_actor_role
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import workstream_subject
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import repair_greenfield_semantic_projections
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

ROOT = Path(__file__).resolve().parents[3]
PORT_OPERATIONS_PROMPT = json.loads(
    (ROOT / "tests/fixtures/greenfield-volume/logistics-infrastructure.v1.json").read_text(encoding="utf-8")
)["cases"][0]["prompt"]


def test_actor_role_context_resolves_action_homonym_compounds_without_global_role_expansion() -> None:
    assert has_action_homonym_actor_role("dispatch drivers", "hand out parcels")
    assert has_action_homonym_actor_role("support engineers", "investigate failures")
    assert not has_action_homonym_actor_role("residents", "request beds")
    assert not has_action_homonym_actor_role("purchase orders", "arrive for review")
    assert not has_action_homonym_actor_role("workflow routers", "send records")


def test_first_path_steps_drop_release_boundary_without_modal_drift() -> None:
    steps = first_path_steps(
        "A city emergency team. Residents request beds, coordinators verify accessibility needs, "
        "shelters publish accepted assignments, and public officials track capacity evidence without exposing private details. "
        "The first release should handle one region, keep a clear audit trail, and defer predictive routing."
    )

    assert "A city emergency team" not in steps
    assert steps == (
        "Residents request beds",
        "Coordinators verify accessibility needs",
        "Shelters publish accepted assignments",
        "Public officials track capacity evidence without exposing private details",
    )
    assert not any("first release" in step.casefold() for step in steps)
    assert not [
        phrase
        for step in steps
        for phrase in modal_base_form_drift_phrases(step)
    ]


def test_capability_keeps_capitalized_human_actor_actions() -> None:
    first_path = (
        "Researchers record a spectral graph question, run one analysis, review the derivation, and save a "
        "reproducible result."
    )

    assert first_path_capability_phrase(first_path, gerund=True) == (
        "recording a spectral graph question, running one analysis, reviewing the derivation, and saving a "
        "reproducible result"
    )


def test_capability_does_not_append_an_actor_led_visible_step_twice() -> None:
    first_path = (
        "A case manager creates an eligibility record, routes a service decision, "
        "and verifies a resolution notice."
    )

    assert first_path_capability_phrase(first_path, gerund=True) == (
        "creating an eligibility record, routing a service decision, and verifying a resolution notice"
    )


def test_first_path_steps_drop_workflow_requirement_control_clause_after_real_actions() -> None:
    first_path = (
        "Physicists tune magnetic confinement parameters, impurity injection timing, sensor channels, "
        "baseline shots, confidence limits, and saved experiment state before reviewing disruption prediction results. "
        "The workflow must distinguish record as an action from record as evidence and show which owner can grant the next path."
    )
    model = first_path_model(first_path)

    assert model.steps == (
        "Physicists tune magnetic confinement parameters, impurity injection timing, sensor channels, baseline shots, confidence limits and saved experiment state",
        "Review disruption prediction results",
    )
    assert model.visible_outcome == "Disruption prediction results"
    assert not any("Workflow" in step for step in model.steps)
    assert "next path" not in model.visible_outcome.casefold()


def test_first_path_prefers_a_real_actor_action_over_a_review_ready_result_adjective() -> None:
    first_path = "Extension publishers assemble approved changelog fragments into release notes and see a review-ready package."
    model = first_path_model(first_path)

    assert model.material_action == "Extension publishers assemble approved changelog fragments into release notes and see a review-ready package"
    assert model.visible_outcome == "A review-ready package"
    assert first_path_capability_phrase(first_path, gerund=True) == (
        "assembling approved changelog fragments into release notes and seeing a review-ready package"
    )


def test_first_path_steps_drop_role_led_architecture_and_delivery_requirements() -> None:
    first_path = (
        "Process safety engineer can turn an ambiguous batch into a review-ready record using readings, "
        "condition checks, pressure logs, safety evidence, expert review, decision ledger, and final release recommendation. "
        "The request mentions review, approval, and release in the same sentence, so the workflow must keep those states separate. "
        "An architect must see bounded components, state ownership, events, and projection boundaries. "
        "The post-confirm create must finish all project and governance artifacts under the standard budget."
    )
    model = first_path_model(first_path)

    assert model.steps[0] == (
        "Process safety engineer turns an ambiguous batch into a review-ready record using readings, "
        "condition checks, pressure logs, safety evidence, expert review, decision ledger and final release recommendation"
    )
    assert len(model.steps) == 1
    assert model.material_action.startswith("Turn an ambiguous batch into a review-ready record")
    assert model.visible_outcome == "Final release recommendation"
    rendered = " ".join(model.steps).casefold()
    assert "bounded components" not in rendered
    assert "governance artifacts" not in rendered


def test_first_path_steps_preserve_actor_modal_obligation() -> None:
    steps = first_path_steps("A reviewer must approve one request and publish proof for later review.")

    assert steps == ("A reviewer must approve one request and publish proof for later review",)


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


def test_modal_actor_with_action_homonym_keeps_its_complete_subject() -> None:
    path = (
        "Oceanographic watch officers can verify sensor epochs, monitor buoy alert runs, "
        "and receive an alert disposition log."
    )

    model = first_path_model(path)

    assert model.steps == (
        "Oceanographic watch officers can verify sensor epochs",
        "Oceanographic watch officers monitor buoy alert runs",
        "Oceanographic watch officers receive an alert disposition log",
    )
    assert "oceanographic monitors" not in " ".join(model.steps).casefold()


def test_modal_actor_with_action_homonym_inside_domain_label_keeps_its_complete_subject() -> None:
    path = (
        "A package supply chain exception desk user can receive vulnerable dependency reports, "
        "track provenance evidence, coordinate reviewer decisions, preserve readiness proof, "
        "and block shipment until exceptions are approved."
    )

    model = first_path_model(path)

    assert model.steps == (
        "Package supply chain exception desk user receives vulnerable dependency reports",
        "A package supply chain exception desk user tracks provenance evidence",
        "A package supply chain exception desk user coordinates reviewer decisions",
        "A package supply chain exception desk user preserves readiness proof",
        "A package supply chain exception desk user blocks shipment until exceptions are approved",
    )
    assert "a package tracks" not in " ".join(model.steps).casefold()


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


def test_carried_subject_does_not_absorb_visible_result_object_before_next_action() -> None:
    steps = first_path_steps(
        "Researchers load orthopedic implant fatigue-test measurements, compare finite-element simulations "
        "against bench-test controls, track mesh and material parameters, capture tolerance bands and failure modes, "
        "and let a review board approve an evidence package without making clinical safety claims."
    )

    assert carried_subject_prefix("Researchers compare finite-element simulations against bench-test controls") == "Researchers"
    assert steps == (
        "Researchers load orthopedic implant fatigue-test measurements",
        "Researchers compare finite-element simulations against bench-test controls",
        "Researchers track mesh and material parameters",
        "Researchers capture tolerance bands and failure modes",
        "Researchers let a review board approve an evidence package without making clinical safety claims",
    )
    assert not any("bench-test tracks" in step.casefold() for step in steps)


def test_first_path_steps_keep_compound_review_outcomes_inside_object_list() -> None:
    path = (
        "correlates robot telemetry, operator commands, safety envelopes, obstacle detections, "
        "replay timelines, and engineering review outcomes before a fix is approved"
    )
    model = first_path_model(path)

    assert model.steps == (
        "Correlate robot telemetry, operator commands, safety envelopes, obstacle detections, replay timelines and engineering review outcomes before a fix is approved",
    )
    assert model.material_action.startswith("Correlate robot telemetry")
    assert model.visible_outcome.startswith("Robot telemetry")
    assert model.material_action != "Review a fix is approved"


def test_short_action_shaped_compound_remains_an_action_outside_an_object_list() -> None:
    assert first_path_model("replay timelines").steps == ("Replay timelines",)


def test_action_after_list_inputs_starts_a_new_step() -> None:
    path = (
        "open the planner, enter roof details, usage, shading concerns, financing preferences and timeline, "
        "review ranked installation plans, and check cost assumptions and blockers, then see a saved plan record"
    )

    assert first_path_model(path).steps == (
        "Open the planner",
        "Enter roof details, usage, shading concerns, financing preferences and timeline",
        "Review ranked installation plans",
        "Check cost assumptions and blockers",
        "See a saved plan record",
    )


def test_actor_led_actions_are_not_absorbed_by_result_object_heads() -> None:
    assert split_action_pieces(
        "Researchers inspect evidence, exceptions, rationale notes, "
        "reviewers record findings, and auditors publish proof"
    ) == [
        "Researchers inspect evidence, exceptions, rationale notes",
        "reviewers record findings",
        "auditors publish proof",
    ]


def test_action_homonym_state_items_keep_the_established_object_list() -> None:
    assert split_action_pieces(
        "Operators inspect request metadata, validation notes, routing rules, "
        "export state, return state, and display state"
    ) == [
        "Operators inspect request metadata, validation notes, routing rules, "
        "export state, return state, and display state"
    ]


def test_short_compound_carry_does_not_absorb_follow_on_actor_actions() -> None:
    operator_path = "Operators audit evidence, record state changes, and publish proof"
    assert split_action_pieces(operator_path) == [
        "Operators audit evidence",
        "Operators record state changes",
        "Operators publish proof",
    ]
    assert first_path_model(operator_path).steps == (
        "Operators record state changes",
        "Operators publish proof",
    )
    assert first_path_model("Researchers review evidence, notes, record findings, and publish proof").steps == (
        "Researchers review evidence, notes",
        "Researchers record findings",
        "Researchers publish proof",
    )


def test_nominal_signoff_tail_stays_in_the_coordinated_object_list() -> None:
    assert split_action_pieces(
        "Researchers compare evidence, exceptions, and signoff before release"
    ) == ["Researchers compare evidence, exceptions, and signoff before release"]
    assert split_action_pieces(
        "Researchers compare evidence, then reviewers approve release"
    ) == ["Researchers compare evidence", "reviewers approve release"]
    assert split_action_pieces(
        "Researchers compare evidence, exceptions, and reviewers approve release"
    ) == ["Researchers compare evidence, exceptions", "reviewers approve release"]


def test_action_shaped_nouns_stay_in_an_established_object_list() -> None:
    model = first_path_model(
        "Safety engineers replay robot paths, human proximity events, intervention thresholds, "
        "sensor occlusion, baseline routes, and operator notes before releasing a safety result"
    )

    assert model.steps == (
        "Safety engineers replay robot paths, human proximity events, intervention thresholds, sensor occlusion, baseline routes and operator notes",
        "Safety engineers release a safety result",
    )


def test_actor_led_open_action_beats_homonym_object_fallback() -> None:
    model = first_path_model(
        "Safety engineers replay robot paths, human proximity events, intervention thresholds, sensor occlusion. "
        "Baseline routes and operator notes before releasing a safety result."
    )

    assert model.material_action == (
        "Safety engineers replay robot paths, human proximity events, intervention thresholds, sensor occlusion"
    )
    assert model.material_action != "Baseline routes and operator notes before releasing a safety result"
    assert "can baseline routes" not in model.material_action.casefold()


def test_actor_led_open_action_rejects_bare_final_recommendation_noun() -> None:
    assert actor_led_open_action_parts("a final nutrient plan recommendation") == ("", "")
    assert actor_led_open_action_parts("final lesson explanation") == ("", "")


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


def test_system_subject_carries_across_stream_and_following_actions() -> None:
    steps = first_path_steps(
        "The platform decomposes the work, routes subtasks to agents, streams progress into a live graph, "
        "asks a human for approval, resolves conflicts, and delivers a final artifact."
    )

    assert steps == (
        "The platform decomposes the work",
        "The platform routes subtasks to agents",
        "The platform streams progress into a live graph",
        "The platform asks a human for approval",
        "The platform resolves conflicts",
        "The platform delivers a final artifact",
    )
    assert not any(step.startswith("Streams ") for step in steps)


def test_delegated_human_action_does_not_steal_the_system_subject() -> None:
    steps = first_path_steps(
        "The product ranks alternatives, lets the traveler choose an option, "
        "and stores the comparison evidence."
    )

    assert steps == (
        "The product ranks alternatives",
        "Let the traveler choose an option",
        "The product stores the comparison evidence",
    )


def test_action_shaped_actor_role_still_owns_follow_on_actions() -> None:
    steps = first_path_steps(
        "Support engineers investigate failures, record findings, and publish proof."
    )

    assert steps == (
        "Support engineers investigate failures",
        "Support engineers record findings",
        "Support engineers publish proof",
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
    confirmation_text = format_product_intent_confirmation_text(confirmation)
    confirmed_intent = parse_confirmed_intent_text(
        confirmation_text,
        prompt=FLOOD_SHELTER_PROMPT,
        fallback_title="Flood Shelter Intake Coordination System",
    )
    assert "where a city emergency team" not in str(confirmed_intent["product_story"]).casefold()
    assert "residents request beds coordinators" not in str(confirmed_intent["product_story"]).casefold()
    assert str(confirmed_intent["first_path"]).startswith("Residents request beds")
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


def test_confirmed_completion_keeps_action_title_out_of_sentence_projection() -> None:
    confirmation = build_product_intent_confirmation(
        prompt=PORT_OPERATIONS_PROMPT,
        title="Container Berth Turnaround Control",
        repo_name="container-berth-turnaround-control",
        observed_source={"source_posture": "confirmed_intent_only"},
    )
    confirmed_intent = parse_confirmed_intent_text(
        format_product_intent_confirmation_text(confirmation),
        prompt=PORT_OPERATIONS_PROMPT,
        fallback_title="Container Berth Turnaround Control",
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt=str(confirmed_intent["prompt"]),
        title=str(confirmed_intent["title"]),
        observed_source={"source_posture": "confirmed_intent_only"},
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )
    raw_proposal = copy.deepcopy(proposal)
    raw_workflow = raw_proposal["backlog"][1]
    completed = complete_confirmed_proposal(
        normalize_host_reasoned_proposal(proposal),
        release_selector="0.0.1",
    )

    modal_issues = [
        issue
        for issue in generated_semantic_slop_issues(completed, root="proposal")
        if "modal/base-form grammar drift" in issue
    ]
    workflow = completed["backlog"][1]
    title = str(workflow["title"])
    raw_sentence_projection = "\n".join(
        [
            *[str(line) for line in raw_workflow["rationale_lines"]],
            json.dumps(raw_workflow["domain_intelligence"], sort_keys=True),
        ]
    )
    completed_sentence_projection = "\n".join(
        [
            *[str(line) for line in workflow["rationale_lines"]],
            json.dumps(workflow["domain_intelligence"], sort_keys=True),
        ]
    )
    component_labels = {str(row["component_id"]): str(row["label"]) for row in raw_proposal["components"]}
    workflow_subject = backlog_workstream_subject(component_labels[str(raw_workflow["component_focus"][0])])

    assert modal_issues == []
    assert title.startswith("Let Berth Planner Reconcile Container Discharge")
    assert completed["semantic_model"]["first_path_contract"]["visible_result"] == "whether the vessel can sail"
    assert title.casefold() not in raw_sentence_projection.casefold()
    assert title.casefold() not in completed_sentence_projection.casefold()
    assert workflow_subject in raw_sentence_projection
    assert workflow_subject in completed_sentence_projection
    assert "This workstream" not in raw_sentence_projection
    assert "This workstream" not in completed_sentence_projection


def test_workstream_subject_uses_generic_fallback_only_without_component_ownership() -> None:
    assert workstream_subject(
        {"title": "Let Crane Dispatcher Reconcile Vessel Readiness", "component_focus": []},
        fallback="Container Berth Turnaround Control",
    ) == "This workstream"


def test_confirmed_port_workflow_keeps_specific_operational_site_anchor() -> None:
    confirmation = build_product_intent_confirmation(
        prompt=PORT_OPERATIONS_PROMPT,
        title="Container Berth Turnaround Control",
        repo_name="container-berth-turnaround-control",
        observed_source={"source_posture": "confirmed_intent_only"},
    )
    confirmation_text = format_product_intent_confirmation_text(confirmation)
    confirmed_intent = parse_confirmed_intent_text(
        confirmation_text,
        prompt=PORT_OPERATIONS_PROMPT,
        fallback_title="Container Berth Turnaround Control",
    )
    proposal = build_confirmed_greenfield_proposal(
        prompt=str(confirmed_intent["prompt"]),
        title=str(confirmed_intent["title"]),
        observed_source={"source_posture": "confirmed_intent_only"},
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )

    assert "Pier 7" not in confirmed_intent["evidence_requirements"]
    assert "Pier 7" in confirmed_intent["operational_constraints"]
    assert "Pier 7" in proposal["intent"]["operational_constraints"]
    assert confirmation_text.index("Operational constraints") < confirmation_text.index("Human actors")
    constraint_section = next(
        row
        for row in proposal["project_brief"]["blueprint_sections"]
        if row["section"] == "Operational constraints"
    )
    assert "Pier 7" in constraint_section["must_capture"]
    compiler_input = greenfield_apply_semantic_input(proposal)
    refreshed = ensure_apply_semantic_model(proposal, refresh=True)

    assert "Pier 7" in compiler_input.operational_constraints
    assert compiler_input.source_requirements == tuple(proposal["intent"]["evidence_requirements"])
    assert dict(compiler_input.source_paths)["operational_constraints"] == "intent.operational_constraints"
    assert "Pier 7" in refreshed["semantic_model"]["domain_ontology"]["operational_constraints"]

    refreshed["project_brief"]["project_outcome"] = (
        "Operators should trust the visible result produced by "
        f"{refreshed['intent']['proof_boundary']}"
    )
    assert repair_greenfield_semantic_projections(refreshed) is True
    repaired_constraint_section = next(
        row
        for row in refreshed["project_brief"]["blueprint_sections"]
        if row["section"] == "Operational constraints"
    )
    assert "Pier 7" in repaired_constraint_section["must_capture"]


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
    assert "review can support facts" not in confirmation_text
    assert "decide what is ready" in confirmation_text

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
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    assert "readiness decision record" in rendered
    assert "what is ready workflow support" not in rendered
    assert "is ready state" not in rendered
    assert "when the multiple teams preserve rationale" not in rendered


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
