from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_component_contract import public_prose_quality_issues
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import complete_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_sequence_diagram import first_path_flowchart_mermaid
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec


ROOT = Path(__file__).resolve().parents[3]
FIRST_PATH_SEMANTICS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_semantics.py"
FIRST_PATH_CLAUSES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_clauses.py"
FIRST_PATH_TYPES_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_first_path_types.py"


def test_first_path_clause_rendering_stays_in_dedicated_owner() -> None:
    parser_source = FIRST_PATH_SEMANTICS_PATH.read_text(encoding="utf-8")
    clause_source = FIRST_PATH_CLAUSES_PATH.read_text(encoding="utf-8")
    type_source = FIRST_PATH_TYPES_PATH.read_text(encoding="utf-8")

    assert len(parser_source.splitlines()) < 800
    for moved in (
        "def first_path_clauses",
        "def first_path_action_phrase",
        "def first_path_capability_phrase",
        "def first_path_outcome_phrase",
        "def _first_path_capability_text",
        "def _first_path_action_text",
        "def _first_path_outcome_text",
        "def clean_visible_result_phrase",
        "def visible_result_object",
        "def action_chain_fragment",
    ):
        assert moved not in parser_source
    assert "def first_path_model" in parser_source
    assert "def first_path_clauses" in clause_source
    assert "def action_chain_fragment" in clause_source
    assert "def clean_visible_result_phrase" in clause_source
    assert "greenfield_domain_term_index import ordered_terms" in clause_source
    assert "normalize_domain_token" not in clause_source
    assert "class FirstPathModel" in type_source
    assert "class FirstPathClauses" in type_source


def test_confirmed_completion_repairs_actor_and_visible_result_splices() -> None:
    completed = complete_confirmed_intent(
        {
            "title": "Activity Progress Notebook",
            "product_story": (
                "A person needs a private place to record recurring care activity, compare it with a plan, "
                "and decide what needs attention before the next check-in."
            ),
            "state_object": (
                "The core state is a care progress record with active entries, notes, visible prompts, "
                "current status, and a history of changes."
            ),
            "first_path": (
                "A patient signs in. The patient logs a new activity with timing, note, and status. "
                "The product saves the entry, updates the progress view, and renders the visible result: "
                "the patient sees a clear prompt, updated status, and next action."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when one person can save an entry, see the updated progress view, "
                "and correct the entry while the previous state remains reviewable."
            ),
            "problem": (
                "Activity Progress Notebook is not trustworthy when users need an active and decide what to do "
                "from The patient sees a clear prompt."
            ),
            "human_actors": ["Patient", "Reviewer"],
            "internal_systems": ["Activity Capture", "Progress View"],
        }
    )

    encoded = json.dumps(completed, sort_keys=True)

    assert "can own a named responsibility" not in encoded
    assert "cares about" not in encoded
    assert "active and decide" not in encoded
    assert "from the patient sees" not in encoded.casefold()
    assert "reach the patient sees" not in encoded.casefold()
    assert "Patient needs a dependable way" in completed["problem"]
    assert generated_semantic_slop_issues(completed) == []
    assert public_prose_quality_issues(completed) == []


def test_first_path_clauses_compile_actions_outcomes_and_noun_lists() -> None:
    request_path = (
        "A requester opens the product, selects a request type, enters amount, constraints, "
        "and contact details. The product calculates eligibility and displays a decision "
        "with reason notes."
    )
    care_path = (
        "A patient signs in. The patient logs a new activity with timing, note, and status. "
        "The product saves the entry, updates the progress view, and renders the visible result: "
        "the patient sees a clear prompt, updated status, and next action."
    )
    review_path = (
        "A permit coordinator imports one permit application, a zoning reviewer records a zoning check, "
        "the applicant submits one revision, and a supervisor reviews the decision package with traceable "
        "documents, comments, checks, and final status."
    )

    request = first_path_clauses(request_path)
    care = first_path_clauses(care_path)
    review = first_path_clauses(review_path)
    short_actor_path = (
        "The AI reviewer records a decision. The product displays the decision queue. "
        "A reviewer approves final status."
    )
    short_actor = first_path_clauses(short_actor_path)

    assert request.action_chain == "select a request type and enter amount, constraints and contact details"
    assert request.visible_result == "a decision with reason notes"
    assert request.capability_chain == "select a request type, enter amount, constraints and contact details, and see a decision with reason notes"
    assert "review A decision" not in request.capability_chain
    assert "calculates eligibility" not in request.visible_result
    assert care.action_chain == "log a new activity with timing, note and status"
    assert "signs in" not in care.action_chain
    assert care.visible_result == "a clear prompt, updated status, and next action"
    assert review.action_chain == "import one permit application, record a zoning check, and submit one revision"
    assert review.visible_result == "the decision package with traceable documents, comments, checks and final status"
    assert short_actor.action_chain == "record a decision"
    assert short_actor.capability_chain == "record a decision and see the decision queue"
    assert "approve final status" not in short_actor.capability_chain
    assert base_action_clause("logs progress and reviews weekly status") == "log progress and review weekly status"
    assert (
        base_action_clause("requests a slot, receives confirmation, and records next steps")
        == "request a slot, receive confirmation, and record next steps"
    )
    assert base_action_clause("comments, checks, and final status") == "comments, checks, and final status"


def test_first_path_clauses_separate_user_action_from_internal_processing() -> None:
    path = (
        "The requester enters the request type, amount, timing constraints, and contact details. "
        "The workspace checks the request against the team rules, asks for missing information when needed, "
        "and displays a decision summary with reason notes. A reviewer can inspect the request, add follow-up notes, "
        "and keep the next action visible."
    )

    clauses = first_path_clauses(path)

    assert clauses.action_chain.startswith("enter the request type")
    assert "checks the request" not in clauses.action_chain
    assert "asks for missing" not in clauses.action_chain
    assert clauses.visible_result == "a decision summary with reason notes"


def test_unheaded_confirmed_intent_paragraphs_do_not_fall_back_to_mechanistic_copy() -> None:
    markdown = """
# Request Review Workspace

A small team needs one place to turn incoming requests into clear review outcomes. Today request details, reviewer notes, and decisions sit in separate messages, so the person asking cannot tell what is missing and the reviewer cannot see why a request moved forward or stopped.

The central object is a tracked request with submitted details, reviewer notes, missing-information prompts, a decision summary, and a history of corrections.

A requester opens the web app, enters a request type, amount, constraints, and contact details. The product checks the request, asks for missing information when required, and displays a decision summary with reason notes. A reviewer can then inspect the request and follow up from the same record.

Release 0.0.1 succeeds when one requester can submit a complete request, see a decision summary with reason notes, correct a missing field, and leave a reviewable record for a reviewer. Live integrations and multi-team routing are out of scope for the first release.

## Human actors
- Requester
- Reviewer

## Internal product systems
- Request Intake — collects required request details and missing-information corrections.
- Review Workspace — shows reviewer notes, decision summary, reason notes, and follow-up context.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Create a request review workspace.",
        title="Request Review Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["state_object"].startswith("The central object is a tracked request")
    assert intent["first_path"].startswith("A requester opens the web app")
    assert intent["proof_boundary"].startswith("Release 0.0.1 succeeds when one requester")
    assert "Release 0.0.1 succeeds" not in intent["first_path"]
    assert intent["opportunity"] == (
        "Make the first version valuable by proving the smallest complete outcome: "
        "enter a request type, amount, constraints and contact details, ending in a decision summary with reason notes."
    )
    assert "starts one real" not in rendered
    assert "move it through input, review, decision" not in rendered
    assert "can a requester opens" not in rendered
    assert "A decision summary" not in intent["product_view"]
    assert generated_semantic_slop_issues(proposal) == []


def test_confirmed_completion_writes_human_capability_and_visible_result_copy() -> None:
    markdown = """
# RepairDesk - Neighborhood Repair Booking

## Product story
Residents need a simple way to get small home repairs scheduled without making repeated calls, guessing availability, or losing track of what was promised. RepairDesk gives one household a clear booking path for a repair request and gives a local repair coordinator enough detail to accept, schedule, or reject the job.

## State object
The product keeps a repair request with customer contact information, location, repair category, description, preferred appointment windows, quoted status, scheduling status, coordinator decision, and customer-visible confirmation.

## First complete path
A resident opens the web app, describes a repair, chooses appointment windows, and submits the request. RepairDesk checks that the request has enough detail, records it, shows the resident a confirmation with next steps, and places the request in a coordinator queue for scheduling.

## Human actors
- Resident: requests a repair and needs a clear confirmation of what happens next.
- Repair coordinator: reviews new requests, accepts jobs that can be scheduled, and follows up when details are missing.

## Internal product systems
- Repair intake: captures the request and validates required detail.
- Scheduling queue: keeps accepted requests visible for coordinator review.
- Customer confirmation: shows the resident the submitted request, status, and next step.

## Proof boundary
The release is good enough when a resident can submit a complete repair request, see a confirmation, and a coordinator can find the same request with the details needed to schedule or ask for corrections. Emergency dispatch, payment, technician routing, and live calendar integration are deferred.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Neighborhood repair booking web app.",
        title="RepairDesk - Neighborhood Repair Booking",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    posture_text = json.dumps(
        {
            "opportunity": intent.get("opportunity"),
            "product_view": intent.get("product_view"),
            "success_metrics": intent.get("success_metrics"),
            "project_brief": proposal.get("project_brief"),
        },
        sort_keys=True,
    ).casefold()

    assert "can a resident opens" not in rendered
    assert "a user can resident" not in rendered
    assert "user can resident submits" not in rendered
    assert "resident a confirmation" not in posture_text
    assert "visible outcome from" not in posture_text
    assert "description" in intent["state_object"].casefold()
    assert "describe a repair" in intent["product_view"].casefold()
    assert "open the web app" not in intent["product_view"].casefold()
    assert "a confirmation with next steps" in intent["product_view"].casefold()
    assert "Keep Repair Request Clear and Reviewable" in [row["title"] for row in proposal["backlog"]]
    assert all("Product Keeps" not in row["title"] for row in proposal["backlog"])
    assert all(len(row["title"].split()) <= 12 for row in proposal["backlog"])
    assert "contrastive domain drift" not in rendered
    assert generated_semantic_slop_issues(proposal) == []


def test_component_spec_narration_filters_action_fragments_from_artifact_phrases() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Coordinator Review Queue",
            "source_system_description": (
                "the coordinator can find the request with the details needed to schedule or reject it"
            ),
        },
        proposal={
            "intent": {
                "title": "Neighborhood Repair Booking",
                "first_path": (
                    "A resident describes a repair, submits the request, and sees a confirmation with next steps. "
                    "The coordinator can find the request with the details needed to schedule or reject it."
                ),
                "proof_boundary": (
                    "The release is good enough when the request can be scheduled or rejected from the saved details."
                ),
            }
        },
        sibling={
            "label": "Customer Confirmation and Status View Service",
            "source_system_description": "shows the submitted request, status, and next step",
        },
        previous_label="Repair Request Intake Service",
        next_label="Customer Confirmation and Status View Service",
        state_label="Repair Request",
    ).fields
    spec = build_narrative_component_spec(
        component_id="coordinator-review-queue",
        label="Coordinator Review Queue",
        path="src/example/coordinator_review_queue",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility="keeps accepted repair requests visible for coordinator review",
        implementation_handoff={"workstream_id": "B-002", "workstream_title": "Keep Requests Reviewable"},
        component_contract=contract,
    ).casefold()

    assert "coordinator find" not in spec
    assert "request needed" not in spec
    assert "state for customer confirmation" not in spec
    assert "responsibilities not named by this component boundary" not in spec
    assert "correction marker travels" not in spec
    assert "scheduled rejected" not in spec
    assert "travel with enough context from" in spec
    assert generated_semantic_slop_issues(contract) == []


def test_component_spec_narration_rejects_derived_system_description_debris() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Request Workflow Planner Surface",
            "source_system_description": (
                "captures user actions, explains blocked states, and keeps the next visible step tied to: "
                "a requester opens the web app, enters a request, and sees a decision summary"
            ),
        },
        proposal={
            "intent": {
                "title": "Request Review Workspace",
                "first_path": (
                    "A requester opens the web app, enters a request, corrects missing information, "
                    "and sees a decision summary with reason notes."
                ),
                "state_object": "The product keeps a tracked request with status, reason notes, and correction history.",
                "proof_boundary": "The release works when the request can be submitted, corrected, and reviewed.",
            }
        },
        sibling={
            "label": "Request Evidence Log",
            "source_system_description": "records the result, validation status, and reviewable proof",
        },
        previous_label="Request Intake",
        next_label="Request Evidence Log",
        state_label="Tracked Request",
    ).fields
    spec = build_narrative_component_spec(
        component_id="request-workflow-planner",
        label="Request Workflow Planner Surface",
        path="src/example/request_workflow_planner",
        kind="client",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-003",),
        diagrams=("D-002",),
        responsibility="shows the request status and next step",
        implementation_handoff={"workstream_id": "B-003", "workstream_title": "Keep Request State Understandable"},
        component_contract=contract,
    ).casefold()

    assert "user actions, explains" not in spec
    assert "tied to:" not in spec
    assert "opens the web" not in spec
    assert "owns identity" not in spec
    assert "blocked states, and next visible step" not in spec
    assert "run one request workflow planner" not in spec
    assert "run one blocked" not in spec
    assert "a replay of request workflow planner surface still connects" in spec
    assert generated_semantic_slop_issues(contract) == []


def test_unheaded_confirmation_preserves_story_state_path_and_proof_boundaries() -> None:
    markdown = """
# Neighborhood Repair Booking

Residents need a simple way to get small home repairs scheduled without making repeated calls, guessing availability, or losing track of what was promised. The product gives one household a clear booking path for a repair request and gives a local repair coordinator enough detail to accept, schedule, or reject the job.

The product keeps a repair request with customer contact information, location, repair category, description, preferred appointment windows, quoted status, scheduling status, coordinator decision, and customer-visible confirmation.

A resident opens the web app, describes a repair, chooses appointment windows, and submits the request. The product checks that the request has enough detail, records it, shows the resident a confirmation with next steps, and places the request in a coordinator queue for scheduling.

The release is good enough when a resident can submit a complete repair request, see a confirmation, and a coordinator can find the same request with the details needed to schedule or ask for corrections.
"""

    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Neighborhood repair booking web app.",
        title="Neighborhood Repair Booking",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert intent["product_story"].startswith("Residents need a simple way")
    assert intent["state_object"].startswith("The product keeps a repair request")
    assert intent["first_path"].startswith("A resident opens the web app")
    assert intent["proof_boundary"].startswith("The release is good enough")
    assert "The release is good enough" not in intent["first_path"]
    assert "Customer:" not in " ".join(intent["human_actors"])
    assert "operator:" not in " ".join(intent["human_actors"]).casefold()
    assert "request with the details needed to schedule" not in proposal["backlog"][0]["recommended_first_slice"]
    assert "shows the resident:" not in rendered
    assert "resident and shows the resident" not in rendered
    assert "customer, local repair coordinator" not in rendered
    assert "neighborhood repair booking operator" not in rendered
    assert "dispatch payment technician" not in rendered
    assert "user can resident" not in rendered
    assert "coordinator find" not in rendered
    assert "user actions, explains" not in rendered
    assert "tied to:" not in rendered
    assert "needed for a resident opens" not in rendered
    assert "produce and review a confirmation with next steps" in rendered
    assert generated_semantic_slop_issues(proposal) == []


def test_unheaded_intent_without_actor_section_derives_stable_roles_and_short_workstream_titles() -> None:
    markdown = """
# Request Review Workspace

A small operations team receives important requests through scattered messages and shared notes. They need one place where a requester can send a complete request, see whether it is accepted or blocked, and understand what happens next without chasing the team for status.

The central state is a tracked request with requester identity, requested amount, requested timing, constraints, decision summary, reason notes, follow-up owner, and visible blocked-state history.

The requester enters the request type, amount, timing constraints, and contact details. The workspace checks the request against the team rules, asks for missing information when needed, and displays a decision summary with reason notes. A reviewer can inspect the request, add follow-up notes, and keep the next action visible.

The first release succeeds when one requester can submit a complete request and one reviewer can confidently decide whether to accept it, return it for missing information, or keep it visible for follow-up. Multi-team routing, external integrations, automated approvals, and long-term analytics stay outside the first release.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Create a request review workspace.",
        title="Request Review Workspace",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)
    titles = [row["title"] for row in proposal["backlog"]]
    actor_labels = [row.split(":", 1)[0] for row in intent["human_actors"]]

    assert "Requester" in actor_labels
    assert "Reviewer" in actor_labels
    assert "Where a Requester" not in rendered
    assert "Chasing the Team" not in rendered
    assert "Notes a Reviewer" not in rendered
    assert "And One Reviewer" not in rendered
    assert "other accepted items" not in rendered.casefold()
    assert "other accepted actors" not in rendered.casefold()
    generated_backlog_text = json.dumps(
        [
            {
                "problem": row.get("problem"),
                "opportunity": row.get("opportunity"),
                "product_view": row.get("product_view"),
                "recommended_first_slice": row.get("recommended_first_slice"),
                "success_metrics": row.get("success_metrics"),
                "rationale_lines": row.get("rationale_lines"),
            }
            for row in proposal["backlog"]
        ],
        sort_keys=True,
    )
    assert "checks the request against the team rules, asks" not in generated_backlog_text
    assert "inspect the request, and add follow-up notes" not in generated_backlog_text
    assert "the team can prove Release 0.0.1 is trusted only" not in rendered
    assert "Release 0.0.1 is trusted only when the accepted path" not in rendered
    assert "accepted path can be replayed from input through state change" not in rendered
    assert "operating reality clear enough" not in rendered
    assert "The weak inputs are the request type and add follow-up notes" not in rendered
    assert "guide path capture allowed command" not in rendered.casefold()
    assert "capture allowed command" not in rendered.casefold()
    assert "responsibilities not named by this component boundary" not in rendered.casefold()
    assert "before this component can guide" not in rendered.casefold()
    assert all("Multi-team Routing" not in title for title in titles)
    assert all(len(title.split()) <= 12 for title in titles)
    assert any(title.startswith("Let Requester Reach A Decision Summary") for title in titles)
    assert "long-term analytics" not in proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()
    assert generated_semantic_slop_issues(proposal) == []


def test_plain_participants_section_does_not_poison_radar_titles_or_first_path() -> None:
    markdown = """
# Neighborhood Repair Booking

Residents need a calmer way to turn small home repair problems into confirmed appointments. The product lets a resident describe the repair, add availability, see an estimate window, choose a provider slot, and finish with a booking they can trust.

The core state is one repair request and its booking history: resident contact details, repair description, estimate window, selected appointment slot, provider assignment, booking confirmation, and any blocker that prevents a reliable appointment.

The first complete path starts when a resident opens the web app, describes a repair, provides contact and availability details, reviews an estimate window, selects an appointment slot, and submits the request. The system confirms the booking, records the selected provider slot, shows the resident what happens next, and makes the booking available for provider review.

Participants:
- Resident: needs a clear repair appointment without repeated calls or uncertainty.
- Local provider: receives complete repair bookings with enough context to prepare for the visit.
- Coordinator: maintains provider availability and resolves blocked or unclear bookings.

Internal product systems:
- Repair request intake.
- Estimate and slot selection.
- Booking confirmation.
- Provider review queue.

Assumptions:
- Payments, emergency dispatch, and provider marketplace ranking are later scope.

Proof boundary:
- A resident can create a repair request, choose a slot, receive a confirmed booking, and see the next step.
- A provider-facing queue receives the booking with the required repair context.
- Missing contact details, unavailable slots, or incomplete repair descriptions block confirmation instead of producing a misleading booking.
"""
    intent = parse_confirmed_intent_text(markdown)
    proposal = build_confirmed_greenfield_proposal(
        prompt="Neighborhood repair booking web app.",
        title="Neighborhood Repair Booking",
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)
    titles = [row["title"] for row in proposal["backlog"]]

    assert intent["first_path"].startswith("The first complete path starts when a resident opens")
    assert intent["human_actors"][0].startswith("Resident:")
    assert "Participants Resident" not in rendered
    assert "Resident Resident" not in rendered
    assert "Need A Calmer Way" not in " ".join(titles)
    assert any(title == "Let Resident Reach A Confirmed Booking" for title in titles)
    generated_backlog_text = json.dumps(
        [
            {
                "title": row.get("title"),
                "problem": row.get("problem"),
                "opportunity": row.get("opportunity"),
                "product_view": row.get("product_view"),
                "recommended_first_slice": row.get("recommended_first_slice"),
                "success_metrics": row.get("success_metrics"),
            }
            for row in proposal["backlog"]
        ],
        sort_keys=True,
    )
    workflow = proposal["backlog"][1]
    assert workflow["problem"].startswith("The resident needs the first interaction to end in a confirmed booking")
    assert "where trust can be lost first" not in generated_backlog_text.casefold()
    assert "replaying the whole workflow by hand" not in generated_backlog_text.casefold()
    assert "proof boundary" not in workflow["problem"].casefold()
    assert "the local provider can use the saved context" in " ".join(workflow["success_metrics"]).casefold()
    assert "complete path starts when" not in generated_backlog_text.casefold()
    assert "visible outcome from a confirmed booking" not in rendered.casefold()
    assert "a confirmed booking" in rendered
    assert generated_semantic_slop_issues(proposal) == []

    contract = derive_component_semantic_contract(
        proposal["components"][0],
        proposal=proposal,
        sibling=proposal["components"][1],
        previous_label="",
        next_label=proposal["components"][1]["label"],
        state_label="Repair Request",
    ).fields
    spec = build_narrative_component_spec(
        component_id=proposal["components"][0]["component_id"],
        label=proposal["components"][0]["label"],
        path="src/example/repair_request_intake",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility=proposal["components"][0].get("responsibility", ""),
        implementation_handoff={"workstream_id": "B-002", "workstream_title": workflow["title"]},
        component_contract=contract,
    )
    contract_text = json.dumps(contract, sort_keys=True).casefold()
    spec_text = spec.casefold()

    assert "center of gravity" not in spec_text
    assert "create repair request" not in contract_text
    assert "describe repair" not in contract_text
    assert "booking required" not in contract_text
    assert "intake service state update" not in contract_text
    assert "failure avoided" not in spec_text
    assert "responsible for the first product information" in spec_text
    assert "missing contact detail" in spec_text


def test_component_contract_uses_readable_irregular_lifecycle_verbs() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Progress View",
            "source_system_description": "shows saved entries, sends a correction prompt, and lets the user see the current status",
        },
        proposal={
            "intent": {
                "title": "Activity Progress Notebook",
                "first_path": (
                    "A person records an entry, sees the updated status, sends a correction, and the product shows the final view."
                ),
            }
        },
        sibling={"label": "Entry Capture"},
        previous_label="Entry Capture",
        next_label="Review View",
        state_label="Progress Record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "seed" not in rendered
    assert "keeped" not in rendered
    assert "sended" not in rendered
    assert "showed" not in rendered
    assert "seen" in rendered or "shown" in rendered or "sent" in rendered
    assert generated_semantic_slop_issues(contract) == []
    assert public_prose_quality_issues(contract) == []


def test_first_path_flowchart_drops_launcher_auth_step_and_keeps_domain_routing() -> None:
    mermaid = first_path_flowchart_mermaid(
        label="Activity Progress Notebook",
        actors=["Patient", "Reviewer"],
        components=[
            {"label": "Activity Capture", "release_scope": "first_path_required"},
            {"label": "Progress View", "release_scope": "first_path_required"},
            {"label": "Summary Review", "release_scope": "supporting"},
        ],
        first_path=(
            "A patient signs in. The patient logs a new activity. "
            "The product updates the progress view and the patient sees the result."
        ),
        semantic_model={
            "first_path_contract": {
                "events": [
                    {"text": "A patient signs in."},
                    {"text": "The patient logs a new activity with timing and note."},
                        {"text": "The workspace checks the activity against the saved preferences."},
                        {"text": "The product updates the progress view."},
                        {"text": "A reviewer can inspect the activity."},
                        {"text": "A reviewer can add follow-up notes and keep the next action visible."},
                        {"text": "The patient sees the result and next action."},
                ]
            }
        },
    )

    assert "signs in" not in mermaid.casefold()
    assert "C4" not in mermaid
    assert "Activity Capture" in mermaid
    assert "Progress View" in mermaid
    assert "Done means" not in mermaid
    assert "patient sees" not in mermaid.casefold()
    assert "Activity against" not in mermaid
    assert "workspace checks" in mermaid.casefold()
    assert "Can inspect" not in mermaid
    assert "Reviewer inspects" in mermaid
    assert "and keep the next action" not in mermaid
    assert "Reviewer adds follow-up notes<br/>and keeps the next action" in mermaid


def test_public_quality_gate_rejects_raw_contract_parser_debris() -> None:
    issues = public_prose_quality_issues(
        {
            "component_contract": {
                "outside_boundary": (
                    "responsibilities not named by this component boundary; guide path capture allowed command; "
                    "exposes blocked states"
                ),
                "dependencies": [
                    "Coordinates with Intake Service so upstream state is available before this component can guide the first path."
                ],
            }
        }
    )

    joined = " ".join(issues)
    assert "mechanical boundary placeholder" in joined
    assert "parser action debris" in joined
    assert "mechanical dependency scaffold" in joined
