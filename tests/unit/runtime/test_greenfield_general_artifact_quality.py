from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_axes import component_axis_key_for_label
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import derive_component_semantic_contract
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import confirmed_components
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import _first_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import _sentence_fragment
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    build_greenfield_package_report,
    build_greenfield_completion_report,
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import (
    generated_semantic_slop_issues,
    material_first_path_action,
    normalize_project_title,
    release_scope_for_component,
)
from odylith.runtime.domain_intelligence.proposal_normalization import _normalize_release_plan
from odylith.runtime.governance.component_spec_rendering import build_component_spec
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


GENERIC_DECISION_REVIEW_INTENT = """# Decision Review Workspace

## Product Story
Decision Review Workspace helps decision reviewers, preparers, record owners, contributors, and outcome recipients keep a complex decision packet reviewable from intake through final outcome.

## State Object
A decision packet tracks item identity, context evidence, recommendation summary, feedback themes, follow-up questions, responses, final outcome, rationale, conditions, source attachments, and audit history.

## First Complete Path
A decision reviewer opens a packet, checks the context evidence, reads the rule and impact summary, compares recommendation with feedback, saves follow-up questions for preparers, reviews responses, records rationale after the final outcome, and the record owner publishes a decision packet with attachments and audit history.

## Human Actors
- Decision reviewers: review materials, compare evidence, ask follow-up questions, decide the outcome, and record rationale.
- Packet preparers: assemble packets, attach source materials, answer follow-up questions, and keep recommendations tied to evidence.
- Record owners: publish the final decision record, attachments, outcome, and audit history.
- Contributors: submit feedback and need confidence that their input is represented accurately.
- Outcome recipients: receive the decision outcome, conditions, and supporting rationale.

## External Systems
- Work intake system: supplies item identity and packet metadata.
- Context source system: supplies location, policy, or evidence context.
- Feedback portal: supplies contributor feedback and attachments.
- Document repository: stores source attachments and published decision packets.

## Internal Product Systems
- Packet Intake and Versioning: owns incoming packet identity, attachment completeness, and version history.
- Location and Context Viewer: owns context display, source freshness markers, and missing-context blockers.
- Feedback Grouping and Theme Summary: owns feedback deduplication, grouping, theme labels, and source provenance.
- Question and Response Tracker: owns follow-up questions, response status, unresolved blockers, and handoff to the decision view.
- Recommendation Comparison and Readiness Dashboard: owns recommendation comparison, readiness state, visible blockers, and next action.
- Decision Rationale and Outcome Record: owns final rationale, decision command, outcome, conditions, abstentions, and publish handoff.
- Source-backed Audit Trail: owns immutable event history, source attachment versions, retention policy, and replay evidence.

## Critical Assumptions
- The first release supports one packet moving from intake through published decision record.
- Attachments and source references must stay tied to the correct packet version.
- Feedback can be grouped without changing original submitted text.
- Follow-up questions and responses must remain visible until resolved.
- Published decisions must show evidence and rationale needed for later review.

## Ambiguities
- Exact live-review integration can be deferred behind exportable packet proof.

## Proof Boundary
Release 0.0.1 succeeds when a representative packet can be imported with attachments, enriched with context and feedback, routed through reviewer questions and preparer responses, compared against a recommendation, finalized with rationale and outcome, published as a decision packet, and replayed through audit history without losing source provenance.
"""


SERVICE_GOAL_PLANNING_INTENT = """# Service Goal Planning Workspace

## Product Story
Service Goal Planning Workspace helps an operations user move one service improvement goal through a simple planning loop: acknowledgement, baseline capture, daily progress logging, weekly status review, target adjustment, and follow-up reminders.

## State Object
A service-planning record tracks acknowledgement, baseline context, user goal, plan target, daily progress logs, status window, weekly review, target adjustments, guardrail flags, reminders, subscription entitlement, export requests, and deletion requests.

## First Complete Path
A user completes onboarding and acknowledgement, enters baseline capacity, current service level, planning preference, and goal, receives a starting plan target, logs progress for seven days, reviews the weekly status window, receives an adjusted plan target when progress is off track, and receives one follow-up reminder when progress updates stop.

## Human Actors
- Operations user: completes onboarding, enters baseline context, logs progress, reviews status, accepts or rejects reminders, exports or deletes data.
- Product owner: reviews release evidence for the first planning loop before broader claims.

## External Systems
- Optional source import: deferred until manual logging works.
- Payment processor: supplies entitlement events after the planning loop proves value.

## Internal Product Systems
- Onboarding and Acknowledgement Flow: records acknowledgement, eligibility, required disclosure, preferences, and baseline handoff.
- Baseline Context Capture: records capacity, current service level, planning preference, and goal inputs.
- Plan Target and Recommendation Engine: computes the starting target and target adjustments.
- Daily Progress Logging: records progress entries, missing logs, and corrections.
- Weekly Status and Check-in Review: calculates status window, progress status, and off-track reasons.
- Reminder and Guardrail Service: sends follow-up reminders, blocks unsafe guidance, and shows guardrail flags.
- Subscription and Entitlement: controls paid feature access after the core loop proves value.
- Account Data Export and Deletion: exports or deletes user data with proof and retention boundaries.

## Critical Assumptions
- The first release supports manual logging only.
- Guidance must avoid unsupported operational promises.
- The first proof must show normal, missing-log, off-track, safety-blocked, export, and deletion paths.

## Ambiguities
- Exact planning rule and disclaimer text need product-owner confirmation.

## Proof Boundary
Release 0.0.1 succeeds when one operations user can complete onboarding, record baseline context, receive a starting plan target, log seven days of progress, review the weekly status window, get an adjusted plan target when off track, receive at least one follow-up reminder when progress updates stop, and prove export and deletion behavior without claiming automated source integrations.
"""


TRIP_COMPARISON_INTENT = """# Trip Planning Comparison

## Product Story
Trip Planning Comparison helps a traveler compare travel options for one trip using schedule, fare, walking time, and reliability evidence before choosing a route.

## State Object
A trip comparison request tracks origin, destination, departure time, rider preference, candidate options, fare evidence, schedule evidence, ranking rationale, selected route, and unresolved blockers.

## First Complete Path
A traveler enters origin, destination, departure time, and preference, the product fetches candidate options, calculates fare and schedule evidence, ranks alternatives, highlights the lowest-cost acceptable route, lets the traveler choose an option, and stores the comparison evidence.

## Human Actors
- Traveler: enters trip details, compares options, chooses a route, and needs transparent cost and timing evidence.
- Transit planner: reviews release evidence that options, prices, schedules, and ranking rationale are correct.

## External Systems
- Transit schedule feed: supplies routes, departure times, transfer windows, and service alerts.
- Fare table feed: supplies fare rules, zones, discounts, and transfer pricing.

## Internal Product Systems
- Trip Intake Adapter: captures origin, destination, departure time, rider preference, and validation blockers.
- Schedule Candidate Service: normalizes schedule feed options, transfer windows, and service alerts.
- Fare Evidence Service: calculates price options, fare rules, discounts, and transfer costs.
- Option Ranking Engine: orders alternatives by fare, travel time, walking time, reliability, and preference.
- Comparison Review Surface: shows ranked options, lowest-cost acceptable route, rationale, blockers, and selected route evidence.

## Critical Assumptions
- Release 0.0.1 uses deterministic fixture feeds before live provider credentials.
- The first release supports one city and one rider profile.

## Ambiguities
- Exact weighting between lowest-cost and fastest needs product-owner confirmation.

## Proof Boundary
Release 0.0.1 succeeds when one traveler can enter a trip, see candidate options with fare and schedule evidence, understand why the lowest-cost acceptable route is ranked first, select a route, and replay the comparison evidence without claiming live agency integration.
"""


PAIN_RELIEF_TRACKING_INTENT = """# Health Episode Journal (working title)

## Product Story
Health Episode Journal helps a person track pain episodes, relief attempts, medication facts, and simple trend context so they can understand what happened before a care conversation without treating the app as medical advice.

## State Object
A pain journal entry tracks actor identity, episode timestamp, intensity rating, body location, trigger notes, relief method, medication taken as recorded by the user, side effect notes, timeline visibility, edit history, and safety disclaimer acknowledgement.

## First Complete Path
A person opens the app, logs a pain entry with intensity, body area, trigger notes, medication taken, and relief attempt, the product persists the entry, shows it on a timeline and trend view, and lets the person edit the entry if they made a mistake.

## Human Actors
- Person managing pain: logs pain entries, reviews trends, edits mistakes, and decides what to discuss with a clinician.
- Product owner: reviews release evidence for the first tracking loop and safety boundaries.

## External Systems
- Authentication provider: signs the person in.
- Clinician portal: deferred until the personal journal loop works.

## Internal Product Systems
- Pain Entry Capture and Editing: records pain episode details, validates required fields, stores correction history, and blocks unsafe or incomplete entries.
- Personal History, Trends, and Timeline Views: shows persisted pain entries, trend snapshots, edit history, and empty or stale states.
- Medication and Relief Tracking with Reminders: records user-entered medication facts, relief attempts, reminder preferences, and missed reminder state.
- Shareable Visit Summary Generation: creates clinician-facing summaries from selected journal data.
- Account and Profile Management: owns identity, consent, privacy preferences, export, deletion, and caregiver delegation.

## Critical Assumptions
- The first release is a personal tracking product, not diagnosis or medication dosing advice.
- Reminders and clinician sharing are deferred until the create-view-edit loop is proven.
- Health data is sensitive and export or deletion must be explicit.

## Ambiguities
- Exact body-location taxonomy and intensity scale need product-owner confirmation.

## Proof Boundary
Release 0.0.1 succeeds when one person can create a pain entry, see the persisted entry on timeline and trend views, edit the entry, and replay the entry history without claiming diagnosis, medication dosing advice, reminders, clinician sharing, or emergency triage automation.
"""


PROTOCOL_EFFECT_TRACKING_INTENT = """# Protocol Effect Tracker

## Product Story
A researcher or self-experimenter running a personal protocol needs one place to record interventions they're testing — supplements, fasting windows, exercise blocks, sleep changes — and connect them to the biomarkers and outcomes that tell them whether anything is working. Today that lives in scattered spreadsheets, lab PDFs, and wearable apps that never talk to each other, so the signal gets lost. The tracker pulls the intervention timeline and the measurement timeline into one view, so a person can look at a metric and see what they were doing in the weeks before it moved.

## State Object
The central object is a tracked protocol: a set of active interventions over time, paired with timestamped measurements (lab panels, biomarkers, wearable-derived metrics) and the subjective notes around them. Each measurement carries its source, date, and value; each intervention carries its start, stop, dose or parameters, and adherence. The protocol's state is the running history of what was changed and what was measured.

## First Complete Path
A user creates a protocol, logs an active intervention with a start date and dose, records a baseline measurement for a chosen biomarker, then later adds a follow-up measurement. The app shows both points on the metric's timeline with the intervention overlaid, so the first end-to-end value is: log an intervention, record before/after measurements, and see them aligned on one timeline.

## Human Actors
- Self-experimenter or quantified-self user tracking their own protocol
- Protocol-focused clinician or coach reviewing a client's interventions and trends
- Researcher aggregating structured intervention and outcome data

## External Systems
- Wearable and health platforms (Apple Health, Oura, Whoop, Fitbit) for metric import
- Lab providers or lab-result imports (manual entry or file upload) for biomarker panels
- Reference sources for normal ranges and intervention evidence

## Internal Product Systems
- Intervention log with dosing, scheduling, and adherence tracking
- Measurement store for biomarkers and wearable-derived metrics with units and sources
- Timeline and correlation view that aligns interventions against outcomes
- Protocol management grouping interventions and measurements into a tracked plan

## Critical Assumptions
- Single-user personal tracking is the first target, not multi-patient clinical or regulated medical use
- Measurements are entered manually or imported from files at first; live API integrations come later
- The product is observational and informational — it surfaces correlations, not medical diagnoses or treatment advice
- Data is private to the user by default

## Ambiguities
- Whether this is strictly personal self-tracking or also meant for clinicians managing multiple clients
- Whether automated wearable/lab integrations are in the first release or deferred to manual entry first
- How far the analysis goes: simple timeline overlay, or statistical correlation and trend detection

## Proof Boundary
Proven when a user can create a protocol, log at least one intervention with timing and dose, record baseline and follow-up measurements for a biomarker, and view both interventions and measurements aligned on a single timeline. Live third-party integrations, statistical correlation engines, and multi-user roles are out of scope for this first proof.
"""


def _proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=GENERIC_DECISION_REVIEW_INTENT,
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(GENERIC_DECISION_REVIEW_INTENT),
    )


def _service_goal_proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=SERVICE_GOAL_PLANNING_INTENT,
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(SERVICE_GOAL_PLANNING_INTENT),
    )


def _trip_comparison_proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=TRIP_COMPARISON_INTENT,
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(TRIP_COMPARISON_INTENT),
    )


def _pain_relief_tracking_proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Health Episode Journal (working title)",
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(
            PAIN_RELIEF_TRACKING_INTENT,
            prompt="Health Episode Journal (working title)",
        ),
    )


def _protocol_effect_tracking_proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a protocol effect tracker",
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(PROTOCOL_EFFECT_TRACKING_INTENT),
    )


def _rendered_specs(proposal: dict[str, object]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for component in proposal["components"]:  # type: ignore[index]
        row = dict(component)
        specs[str(row["label"])] = build_component_spec(
            component_id=str(row["component_id"]),
            label=str(row["label"]),
            path=str(row.get("path") or row.get("intended_path") or ""),
            kind=str(row.get("kind") or "service"),
            status=str(row.get("status") or "planned"),
            sources=tuple(str(item) for item in row.get("sources", []) or []),
            workstreams=tuple(str(item) for item in row.get("workstreams", []) or []),
            diagrams=tuple(str(item) for item in row.get("diagrams", []) or []),
            responsibility=str(row.get("responsibility") or ""),
            boundary=str(row.get("boundary") or ""),
            dependencies=tuple(str(item) for item in row.get("dependencies", []) or []),
            interfaces=tuple(str(item) for item in row.get("interfaces", []) or []),
            validation=tuple(str(item) for item in row.get("validation", []) or []),
            risks=tuple(str(item) for item in row.get("risks", []) or []),
            qualification=str(row.get("qualification") or "candidate"),
            implementation_handoff=row.get("implementation_handoff") if isinstance(row.get("implementation_handoff"), dict) else None,
            component_contract=row.get("component_contract") if isinstance(row.get("component_contract"), dict) else None,
        )
    return specs


def _component_contract(proposal: dict[str, object], label_part: str) -> dict[str, object]:
    for component in proposal["components"]:  # type: ignore[index]
        row = dict(component)
        if label_part.casefold() in str(row.get("label", "")).casefold():
            return dict(row["component_contract"])
    raise AssertionError(f"missing component containing {label_part!r}")


def _created_backlog(proposal: dict[str, object], tmp_path: Path) -> list[dict[str, str]]:
    rows = []
    for index, row in enumerate(proposal["backlog"], start=1):  # type: ignore[index]
        title = str(dict(row).get("title", ""))
        rows.append(
            {
                "idea_id": f"B-{index:03d}",
                "title": title,
                "idea_path": str(tmp_path / f"B-{index:03d}.md"),
            }
        )
    return rows


def test_greenfield_project_payload_keeps_actor_responsibilities_specific(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    payload = build_greenfield_payload(proposal=proposal, repo_root=tmp_path)

    actors = {title: body for _role, title, body in payload["actors"]}

    assert set(actors) >= {
        "Decision reviewers",
        "Packet preparers",
        "Record owners",
        "Contributors",
        "Outcome recipients",
    }
    assert actors["Decision reviewers"].startswith("Review materials")
    assert actors["Packet preparers"].startswith("Assemble packets")
    assert actors["Record owners"].startswith("Publish the final decision record")
    assert actors["Outcome recipients"].startswith("Receive the decision outcome")
    assert all("," not in title for title in actors)

    rendered = json.dumps(payload, sort_keys=True)
    assert "Build the Source-backed" not in rendered
    assert "supports the accepted path" not in rendered
    assert "additional accepted items remain" not in rendered


def test_greenfield_component_contracts_stay_component_local(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    specs = _rendered_specs(proposal)
    rendered = json.dumps(proposal, sort_keys=True) + "\n" + "\n".join(specs.values())

    assert rendered_component_spec_quality_issues(specs, project_title=str(proposal["intent"]["title"])) == []
    for banned in (
        "inspect The",
        "Human actors:",
        "plus 1 more",
        "owns the ",
        "responsibility and keeps it tied",
        "inputs and produced outputs",
        "supports the accepted path",
        "additional accepted items remain",
        "additional accepted systems remain",
        "external-provider truth",
        "downstream reviewer",
        "matching decisions",
        "lifecycle status decisions",
        "scoring rubric",
        "assignment routing",
        "search query",
    ):
        assert banned not in rendered

    context = _component_contract(proposal, "Location and Context")
    assert "location context" in str(context["owned_state"]).casefold()
    assert "source freshness" in str(context["owned_state"]).casefold()
    assert "uploaded context material" not in str(context["owned_state"]).casefold()

    questions = _component_contract(proposal, "Question and Response")
    assert "follow-up questions" in str(questions["owned_state"]).casefold()
    assert "unresolved blocker" in str(questions["owned_state"]).casefold()
    assert "score output" not in str(questions["owned_state"]).casefold()

    decision = _component_contract(proposal, "Decision Rationale")
    assert "decision rationale" in str(decision["owned_state"]).casefold()
    assert "final rationale" in str(decision["owned_state"]).casefold()
    assert "outcome" in str(decision["owned_state"]).casefold()

    audit = _component_contract(proposal, "Audit Trail")
    assert "immutable event history" in str(audit["owned_state"]).casefold()
    assert "replay evidence" in str(audit["owned_state"]).casefold()


def test_greenfield_atlas_uses_first_path_events_and_evidence_owner(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    diagrams = {str(row["title"]): str(row["mermaid_source"]) for row in proposal["diagrams"]}  # type: ignore[index]
    sequence = diagrams["First Path Sequence"]
    proof = diagrams["Release Proof Review"]
    boundary = diagrams["Component Boundary View"]

    assert sequence.startswith("flowchart LR")
    assert 'S1["Open a packet"]' in sequence
    assert "S1 --> C1" in sequence
    assert 'S2["Check the context evidence"]' in sequence
    assert "S2 --> C2" in sequence
    assert "Compare recommendation with<br/>feedback" in sequence
    assert "S4 --> C5" in sequence
    assert "Save follow-up questions for<br/>preparers" in sequence
    assert "S5 --> C4" in sequence
    assert "Record rationale after the<br/>final outcome" in sequence
    assert "S7 --> C6" in sequence
    assert "Publish a decision packet with<br/>attachments and audit history" in sequence
    assert "sequenceDiagram" not in sequence
    assert "C4-" not in sequence
    assert "Source-backed Audit Trail Adapter" in boundary
    assert "Source-backed Audit Trail Adapter proof record" in proof
    assert "Release 0.0.1 succeeds when a representative" not in proof


def test_greenfield_health_tracking_artifacts_strip_working_title_and_parse_material_first_path(tmp_path: Path) -> None:
    title = normalize_project_title("Health Episode Journal (working title)")
    intent = parse_confirmed_intent_text(
        PAIN_RELIEF_TRACKING_INTENT,
        prompt="Health Episode Journal (working title)",
    )
    proposal = _pain_relief_tracking_proposal(tmp_path)
    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    rendered_public = json.loads(json.dumps(proposal))
    rendered_public["intent"].pop("source_title", None)
    rendered = json.dumps(rendered_public, sort_keys=True).casefold()

    assert title.canonical_title == "Health Episode Journal"
    assert title.raw_title == "Health Episode Journal (working title)"
    assert intent["title"] == "Health Episode Journal"
    assert intent["source_title"] == "Health Episode Journal (working title)"
    assert intent["prompt"] == "Health Episode Journal"
    rendered_intent = dict(intent)
    rendered_intent.pop("source_title", None)
    assert "working title" not in json.dumps(rendered_intent, sort_keys=True).casefold()
    first_action = material_first_path_action(str(intent["first_path"]))
    assert first_action.startswith("Logs a pain entry with intensity")
    assert "body area" in first_action
    assert proposal["intent"]["title"] == "Health Episode Journal"
    assert proposal["intent"]["source_title"] == "Health Episode Journal (working title)"
    assert decision.passed, decision.issues
    assert greenfield_quality_issues(proposal) == []
    assert generated_semantic_slop_issues(proposal) == []

    for banned in (
        "working title",
        "first accepted action",
        "owns maintains",
        "prevents downstream work can trust",
        "valid transition display, stale",
        "rejected or blocked cases, evidence",
        "done, path, mean, person, create, view, edit",
    ):
        assert banned not in rendered


def test_greenfield_health_tracking_registry_uses_domain_artifacts_and_safety_proof(tmp_path: Path) -> None:
    assert component_axis_key_for_label("Pain Entry Capture and Editing Service").startswith("derived_")
    assert component_axis_key_for_label("Medication and Relief Tracking with Reminders Service").startswith("derived_")

    proposal = _pain_relief_tracking_proposal(tmp_path)
    pain_entry = _component_contract(proposal, "Pain Entry Capture")
    medication = _component_contract(proposal, "Medication and Relief")
    account = _component_contract(proposal, "Account and Profile")
    specs = _rendered_specs(proposal)
    rendered = (json.dumps(proposal, sort_keys=True) + "\n" + "\n".join(specs.values())).casefold()

    assert rendered_component_spec_quality_issues(specs, project_title=str(proposal["intent"]["title"])) == []
    for expected in (
        "pain episode details",
        "pain entry intensity",
        "body area",
        "correction history",
        "replayable change evidence",
    ):
        assert expected in json.dumps(pain_entry, sort_keys=True).casefold()
    for expected in (
        "user-entered medication facts",
        "relief attempts",
        "reminder preferences",
        "missed reminder state",
        "medication taken",
    ):
        assert expected in json.dumps(medication, sort_keys=True).casefold()
    for expected in (
        "safety posture",
        "outside the confirmed boundary",
        "sensitive-data posture",
    ):
        assert expected in rendered

    assert "goal target" not in json.dumps(account, sort_keys=True).casefold()
    assert "plan rule" not in json.dumps(account, sort_keys=True).casefold()
    assert "status window" not in json.dumps(account, sort_keys=True).casefold()
    assert "daily log entry" not in json.dumps(medication, sort_keys=True).casefold()
    assert "habit status" not in json.dumps(medication, sort_keys=True).casefold()


def test_greenfield_health_tracking_defers_later_scope_and_keeps_atlas_implementable(tmp_path: Path) -> None:
    assert release_scope_for_component(
        {
            "label": "Medication and Relief Tracking with Reminders Service",
            "responsibility": "records user-entered medication facts, relief attempts, reminder preferences, and missed reminder state.",
        },
        first_path="A person logs a pain entry and sees it on a timeline.",
        proof_boundary="Release succeeds without claiming reminders or clinician sharing.",
        non_goals=["Reminders and clinician sharing are deferred until the journal loop works."],
    ) == "out_of_scope"
    assert release_scope_for_component(
        {
            "label": "Shareable Visit Summary Generation Service",
            "responsibility": "may later produce clinician-facing summaries.",
        },
        first_path="A person logs a pain entry, sees it on a timeline, and edits it.",
        proof_boundary="Reminders and clinician sharing are explicitly out of scope for this release.",
        non_goals=[],
    ) == "out_of_scope"

    proposal = _pain_relief_tracking_proposal(tmp_path)
    release_scopes = {str(row["label"]): str(row["release_scope"]) for row in proposal["components"]}  # type: ignore[index]
    active_labels = {
        str(row["label"])
        for row in proposal["components"]  # type: ignore[index]
        if str(row.get("release_scope")) in {"first_path_required", "supporting"}
    }
    diagrams = {str(row["title"]): str(row["mermaid_source"]) for row in proposal["diagrams"]}  # type: ignore[index]
    sequence = diagrams["First Path Sequence"]
    boundary = diagrams["Component Boundary View"]
    proof = diagrams["Release Proof Review"]

    assert release_scopes["Pain Entry Capture and Editing Service"] == "first_path_required"
    assert release_scopes["Personal History, Trends, and Timeline Views Service"] == "first_path_required"
    assert release_scopes["Medication and Relief Tracking with Reminders Service"] == "out_of_scope"
    assert release_scopes["Shareable Visit Summary Generation Service"] == "out_of_scope"
    assert "Medication and Relief Tracking with Reminders Service" not in active_labels
    assert "Shareable Visit Summary Generation Service" not in active_labels

    assert sequence.startswith("flowchart LR")
    assert "Log a pain entry with" in sequence
    assert "S1 --> C1" in sequence
    assert "Persists the entry" in sequence
    assert "Show it on a timeline" in sequence
    assert "S3 --> C2" in sequence
    assert "Trend view" in sequence
    assert "Let the person edit the entry" in sequence
    assert "S5 --> C1" in sequence
    assert "A person opens the app" not in sequence
    assert "Medication and Relief" not in sequence
    assert "Shareable Visit" not in sequence
    assert "Clinician" not in sequence
    assert ": capture" not in sequence.casefold()

    assert "Deferred scope<br/>Medication and Relief Tracking with Reminders Service" in boundary
    assert "Deferred scope<br/>Shareable Visit Summary Generation Service" in boundary
    assert "Proof checkpoint<br/>Proven when one person can create a pain entry" in proof
    assert "see the persisted entry" in proof
    assert "done, path, mean, person" not in proof


def test_greenfield_protocol_effect_tracker_uses_protocol_measurement_and_timeline_contracts(tmp_path: Path) -> None:
    assert (
        component_axis_key_for_label("Intervention Log with Dosing, Scheduling, and Adherence Tracking Service")
    ).startswith("derived_")
    assert component_axis_key_for_label("Timeline and Correlation View Service").startswith("derived_")
    assert (
        component_axis_key_for_label(
            "Protocol Management Grouping Interventions and Measurements Into a Tracked Plan Service"
        )
    ).startswith("derived_")

    proposal = _protocol_effect_tracking_proposal(tmp_path)
    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    specs = _rendered_specs(proposal)
    rendered = (json.dumps(proposal, sort_keys=True) + "\n" + "\n".join(specs.values())).casefold()

    assert decision.passed, decision.issues
    assert greenfield_quality_issues(proposal) == []
    assert generated_semantic_slop_issues(proposal) == []
    assert rendered_component_spec_quality_issues(specs, project_title=str(proposal["intent"]["title"])) == []

    semantic_model = proposal["semantic_model"]  # type: ignore[index]
    first_path_contract = semantic_model["first_path_contract"]  # type: ignore[index]
    semantic_components = {
        str(row["label"]): row for row in semantic_model["components"]  # type: ignore[index]
    }
    assert first_path_contract["capability"] == (
        "creating a protocol, logging an active intervention with a start date and dose, "
        "recording a baseline measurement for a chosen biomarker, and adding a follow-up measurement"
    )
    assert first_path_contract["visible_result"] == "See them aligned on one timeline"
    assert len(first_path_contract["events"]) >= 6
    proof_checkpoint = str(semantic_model["diagram_event_graph"]["proof_checkpoint"])  # type: ignore[index]
    assert "accepted first path" in proof_checkpoint
    assert "protocol, intervention" not in proof_checkpoint
    assert (
        semantic_components["Timeline and Correlation View Service"]["semantic_axis"]
    ).startswith("derived_")
    assert (
        semantic_components["Protocol Management Grouping Interventions and Measurements Into a Tracked Plan Service"][
            "semantic_axis"
        ]
    ).startswith("derived_")

    release_scopes = {str(row["label"]): str(row["release_scope"]) for row in proposal["components"]}  # type: ignore[index]
    assert release_scopes["Intervention Log with Dosing, Scheduling, and Adherence Tracking Service"] == "first_path_required"
    assert release_scopes["Measurement Store"] == "first_path_required"
    assert release_scopes["Timeline and Correlation View Service"] == "first_path_required"
    assert (
        release_scopes["Protocol Management Grouping Interventions and Measurements Into a Tracked Plan Service"]
        == "first_path_required"
    )

    intervention = _component_contract(proposal, "Intervention Log")
    measurement = _component_contract(proposal, "Measurement Store")
    timeline = _component_contract(proposal, "Timeline and Correlation")
    protocol = _component_contract(proposal, "Protocol Management")

    for expected in (
        "intervention log",
        "scheduling",
        "adherence tracking",
        "source evidence",
        "blocker state",
    ):
        assert expected in json.dumps(intervention, sort_keys=True).casefold()
    for expected in (
        "wearable-derived metrics",
        "baseline measurement",
        "chosen biomarker",
        "follow-up measurement",
        "aligned timeline",
    ):
        assert expected in json.dumps(measurement, sort_keys=True).casefold()
    for expected in (
        "aligns interventions",
        "timeline",
        "correlation view",
        "active intervention",
        "baseline measurement",
    ):
        assert expected in json.dumps(timeline, sort_keys=True).casefold()
        for expected in (
            "protocol management",
            "interventions",
            "measurements",
            "tracked plan",
            "active intervention",
        ):
            assert expected in json.dumps(protocol, sort_keys=True).casefold()

    diagrams = {str(row["title"]): str(row["mermaid_source"]) for row in proposal["diagrams"]}  # type: ignore[index]
    sequence = diagrams["First Path Sequence"]
    proof = diagrams["Release Proof Review"]

    assert sequence.startswith("flowchart LR")
    assert "Create a protocol" in sequence
    assert "S1 --> C4" in sequence
    assert "Log an active intervention" in sequence
    assert "S2 --> C1" in sequence
    assert "Record a baseline measurement" in sequence
    assert "S3 --> C2" in sequence
    assert "Add a follow-up measurement" in sequence
    assert "Show both points on the<br/>metric's timeline" in sequence
    assert "S5 --> C3" in sequence
    assert "See them aligned on one<br/>timeline" in sequence
    assert "A2->>" not in sequence
    assert "A3->>" not in sequence
    assert "Proof checkpoint<br/>Proven when a user can create a protocol" in proof
    assert "protocol, intervention, timing, dose, baseline, follow-up" not in proof

    for banned in (
        "daily log entry",
        "habit log",
        "activity event",
        "check-in answer",
        "symptom entry",
        "body location",
        "relief method",
        "medication-taken",
        "access grant or denial",
        "protected visibility decision",
        "retention decision",
        "role-specific actor visibility",
        "transition history",
        "first path entry",
        "evidence evidence",
        "proven, protocol, least",
        "multi-user roles are.",
    ):
        assert banned not in rendered


def test_greenfield_post_confirm_completion_report_passes_for_protocol_fixture(tmp_path: Path) -> None:
    proposal = _protocol_effect_tracking_proposal(tmp_path)
    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert report.passed, report.issues
    assert report.semantic_model is True
    assert report.artifact_counts["workstreams"] >= 3
    assert report.artifact_counts["components"] >= 3
    assert report.artifact_counts["diagrams"] >= 3
    assert report.tribunal_status == "passed"


def test_greenfield_post_confirm_completion_fails_without_semantic_model(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal.pop("semantic_model")

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "requires GreenfieldSemanticModel" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_on_component_semantic_drift(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["semantic_model"]["components"][0]["produced_outputs"] = "drifted output"

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "drifted from proposal `produced_outputs`" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_on_workstream_semantic_drift(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["semantic_model"]["workstreams"][0]["title"] = "Detached Workstream"

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    joined = "\n".join(report.issues)
    assert "missing workstream contract" in joined
    assert "not rendered by proposal" in joined


def test_greenfield_post_confirm_completion_fails_on_workstream_contract_content_drift(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["semantic_model"]["workstreams"][0]["first_slice"] = "Detached first slice"

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "drifted from proposal `first_slice`" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_on_release_diagram_drift(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["semantic_model"]["diagram_event_graph"]["component_sequence"] = []

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "DiagramEventGraph component sequence drifted" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_on_diagram_event_drift(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["semantic_model"]["diagram_event_graph"]["events"][0]["text"] = "Detached diagram event"

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "DiagramEventGraph events drifted" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_when_deferred_component_leaks_into_diagram_graph(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    component_id = proposal["components"][-1]["component_id"]
    proposal["components"][-1]["release_scope"] = "deferred"
    for row in proposal["semantic_model"]["components"]:
        if row["component_id"] == component_id:
            row["release_scope"] = "deferred"
    proposal["semantic_model"]["diagram_event_graph"]["component_sequence"].append(component_id)

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "DiagramEventGraph component sequence drifted" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_without_first_path_and_release_proofs(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["semantic_model"]["proof_obligations"] = [
        row
        for row in proposal["semantic_model"]["proof_obligations"]
        if row["key"] not in {"first_path_contract", "release_boundary"}
    ]

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    joined = "\n".join(report.issues)
    assert "missing `first_path_contract` proof obligation" in joined
    assert "missing `release_boundary` proof obligation" in joined


def test_greenfield_completion_package_report_passes_with_prewrite_radar_and_release_bundle(tmp_path: Path) -> None:
    proposal = _protocol_effect_tracking_proposal(tmp_path)
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_prewrite_backlog_result(proposal),
        rendered_atlas_sources=_prewrite_atlas_sources(proposal),
        component_registry_preview=_prewrite_component_preview(proposal), project_brief_preview=proposal["project_brief"], tribunal_preview={"status": "passed", "version": "greenfield-validation-gate-v1", "summary": "Accepted product direction is coherent enough to create project records.", "dimensions": {"intent": "present", "first_path": "present", "topology": "present", "proof": "present"}, "issues": []},
        accepted_project_preview={"schema_version": "odylith.accepted_project.v1", "origin": "greenfield", "proposal": {"semantic_model": proposal["semantic_model"]}, "validation_gate": {"status": "passed"}, "created": {"workstreams": _prewrite_backlog_result(proposal)["created"], "components": list(_prewrite_component_preview(proposal)), "diagrams": [f"D-{index:03d}" for index, _row in enumerate(proposal["diagrams"], start=1)], "release_selector": "0.0.1"}},
        compass_memory_preview={"kind": "decision", "summary": "Accepted greenfield proposal", "evidence_tier": "user_intent", "work_category": "governance", "workstreams": ["B-001", "B-002", "B-003", "B-004"], "components": [row["component_id"] for row in _prewrite_component_preview(proposal)]}, next_steps_preview={"project_workstream_id": "B-001", "start_workstream_id": "B-001", "release_selector": "0.0.1", "implementation_prompt": "Implement the first workstream from the accepted semantic model with proof gates.", "operator_sequence": ["Review the project brief.", "Open the first workstream.", "Author the first technical plan."], "coding_readiness_gates": ["Semantic contract accepted.", "Release boundary accepted.", "Proof commands identified."], "verification_commands": ["./.odylith/bin/odylith context --repo-root . B-001"]},
        program_result={"created": True, "dry_run": True},
        release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
        release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
        release_workstream_ids=("B-001",),
    )

    report = build_greenfield_package_report(package)

    assert report.passed, report.issues
    assert report.artifact_counts["rendered_workstream_files"] == len(proposal["backlog"])
    assert report.artifact_counts["release_workstream_ids"] == 1


def test_greenfield_completion_package_report_fails_incomplete_prewrite_radar_bundle(tmp_path: Path) -> None:
    proposal = _protocol_effect_tracking_proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    backlog_result["idea_files"].pop(next(iter(backlog_result["idea_files"])))

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=backlog_result,
            rendered_atlas_sources=_prewrite_atlas_sources(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "render one workstream file per created workstream" in "\n".join(report.issues)


def test_greenfield_completion_package_report_fails_missing_release_assignment_preview(tmp_path: Path) -> None:
    proposal = _protocol_effect_tracking_proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_prewrite_backlog_result(proposal),
            rendered_atlas_sources=_prewrite_atlas_sources(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"release": {"release_id": "release-test"}},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "missing release assignment preview" in "\n".join(report.issues)


def test_greenfield_completion_package_report_fails_release_assignment_preview_drift(tmp_path: Path) -> None:
    proposal = _protocol_effect_tracking_proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_prewrite_backlog_result(proposal),
            rendered_atlas_sources=_prewrite_atlas_sources(proposal),
            program_result={"created": True, "dry_run": True},
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-999"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "did not cover first-release workstream ids" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_on_rendered_registry_scope_drift(tmp_path: Path) -> None:
    proposal = _protocol_effect_tracking_proposal(tmp_path)

    report = build_greenfield_completion_report(
        proposal,
        release_selector="0.0.1",
        rendered_component_specs={"Detached Component": "# Detached Component\n\nBroken."},
    )

    assert not report.passed
    joined = "\n".join(report.issues)
    assert "missing rendered active component spec" in joined
    assert "outside active release scope" in joined


def test_greenfield_post_confirm_completion_fails_provider_call_leak(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["provider_calls"] = 1

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "provider-free" in "\n".join(report.issues)


def test_greenfield_post_confirm_completion_fails_contrastive_unexplained_artifact_terms(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    proposal["components"][0]["component_contract"]["outside_boundary"] += (
        ", outsiderterm state, outsiderterm signal, outsiderterm marker, outsiderterm handoff, "
        "outsiderterm blocker, outsiderterm report, outsiderterm packet, and outsiderterm result"
    )

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    joined = "\n".join(report.issues)
    assert "contrastive domain drift" in joined
    assert "outsiderterm" in joined


def test_greenfield_post_confirm_completion_fails_near_duplicate_generated_sentences(tmp_path: Path) -> None:
    proposal = copy.deepcopy(_protocol_effect_tracking_proposal(tmp_path))
    repeated = (
        "Protocol intervention timing, dose, baseline measurement, follow-up measurement, "
        "timeline alignment, and source reference stay together."
    )
    proposal["components"][0]["source_system_description"] += f". {repeated}"
    proposal["components"][0]["component_contract"]["outside_boundary"] += f". {repeated}"
    proposal["components"][1]["source_system_description"] += f". {repeated}"
    proposal["release_plan"]["strategy"] += f". {repeated}"
    promotion_criteria = proposal["release_plan"]["promotion_criteria"]
    if isinstance(promotion_criteria, list):
        promotion_criteria.append(repeated)
    else:
        proposal["release_plan"]["promotion_criteria"] = f"{promotion_criteria}. {repeated}"
    proposal["diagrams"][0]["summary"] += f". {repeated}"

    report = build_greenfield_completion_report(proposal, release_selector="0.0.1")

    assert not report.passed
    assert "semantic repetition" in "\n".join(report.issues)


def test_greenfield_apply_post_confirm_failure_is_internal_not_operator_repair(tmp_path: Path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _trip_comparison_proposal(tmp_path)
    monkeypatch.setattr(
        greenfield_apply_prewrite,
        "render_prewrite_component_specs",
        lambda **_kwargs: {"Broken Component": "Broken Component owns maintains state."},
    )

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    message = str(excinfo.value)
    assert "greenfield post-confirm completion failed" in message
    assert "No governed records were written." in message
    assert "needs operator/proposal input" not in message


def _prewrite_backlog_result(proposal: dict[str, object]) -> dict[str, object]:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, dict)]
    created = [
        {
            "idea_id": f"B-{index:03d}",
            "title": str(row.get("title", "")),
            "idea_path": f"odylith/radar/source/ideas/test-{index}.md",
        }
        for index, row in enumerate(rows, start=1)
    ]
    return {
        "created": created,
        "idea_files": {
            f"/tmp/test-{index}.md": f"# {row['title']}\n\n{proposal['intent']['first_path']}\n\n{proposal['intent']['proof_boundary']}\n"
            for index, row in enumerate(created, start=1)
        },
        "backlog_index_text": "\n".join(str(row["title"]) for row in created),
        "validation_gate": {"status": "passed"},
    }


def _prewrite_atlas_sources(proposal: dict[str, object]) -> dict[str, str]:
    return greenfield_apply_prewrite.render_prewrite_atlas_sources(proposal)


def _prewrite_component_preview(proposal: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(
        {"component_id": str(row.get("component_id", "")), "validation_gate": {"status": "passed"}}
        for row in proposal.get("components", [])
        if isinstance(row, dict) and str(row.get("release_scope", "")).casefold() not in {"deferred", "out_of_scope", "external"}
    )


def test_greenfield_runtime_domain_intelligence_has_no_fixture_specific_axis_catalog() -> None:
    source_root = Path("src/odylith/runtime")
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            source_root / "domain_intelligence" / "greenfield_component_axes.py",
            source_root / "domain_intelligence" / "greenfield_component_semantic_contract.py",
            source_root / "domain_intelligence" / "greenfield_confirmed_diagrams.py",
        )
    ).casefold()

    for banned in (
        "symptom_self_tracking",
        "medication_relief_tracking",
        "protocol_intervention_tracking",
        "timeline_correlation_view",
        "case identity",
        "workspace status",
        "checklist progress",
    ):
        assert banned not in source


def test_greenfield_apply_keeps_deferred_components_out_of_first_release_registry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_proposals.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    proposal = _pain_relief_tracking_proposal(tmp_path)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    registered_labels = {str(row.get("label", "")) for row in result["components"]}
    assert "Pain Entry Capture and Editing Service" in registered_labels
    assert "Personal History, Trends, and Timeline Views Service" in registered_labels
    assert "Account and Profile Management Service" in registered_labels
    assert "Medication and Relief Tracking with Reminders Service" not in registered_labels
    assert "Shareable Visit Summary Generation Service" not in registered_labels

    registry_text = (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    assert "medication-and-relief-tracking-with-reminders" not in registry_text
    assert "shareable-visit-summary-generation" not in registry_text


def test_greenfield_service_goal_governance_preserves_intent_and_avoids_cross_domain_templates(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(SERVICE_GOAL_PLANNING_INTENT)
    proposal = _service_goal_proposal(tmp_path)
    specs = _rendered_specs(proposal)
    rendered = json.dumps(proposal, sort_keys=True) + "\n" + "\n".join(specs.values())

    assert "follow-up reminder when progress updates stop" in intent["proof_boundary"]
    assert "prove export and deletion behavior" in intent["proof_boundary"]
    assert "receive at least one." not in rendered

    parent = dict(proposal["backlog"][0])  # type: ignore[index]
    first_slice = str(parent["recommended_first_slice"])
    for expected in (
        "completes onboarding and acknowledgement",
        "logs progress for seven days",
        "receives an adjusted plan target",
        "receives one follow-up reminder",
    ):
        assert expected in first_slice

    backlog_titles = {str(dict(row)["title"]) for row in proposal["backlog"]}  # type: ignore[index]
    release_targets = list(proposal["release_plan"]["target_workstream_titles"])  # type: ignore[index]
    assert release_targets
    assert set(release_targets) <= backlog_titles
    assert str(proposal["backlog"][-1]["title"]) in release_targets  # type: ignore[index]

    diagrams = {str(row["title"]): str(row["mermaid_source"]) for row in proposal["diagrams"]}  # type: ignore[index]
    sequence = diagrams["First Path Sequence"]
    assert sequence.startswith("flowchart LR")
    assert "Complete onboarding and<br/>acknowledgement" in sequence
    assert "S1 --> C1" in sequence
    assert "Enter baseline capacity" in sequence
    assert "S2 --> C2" in sequence
    assert "Receive a starting plan target" in sequence
    assert "Log progress for seven days" in sequence
    assert "S4 --> C4" in sequence
    assert "Review the weekly status" in sequence
    assert "S5 --> C5" in sequence
    assert "Receive one follow-up reminder" in sequence

    for banned in (
        "case identity",
        "workspace status",
        "checklist progress",
        "saved notes",
        "actor notes",
        "reviewer eligibility",
        "assignment routing",
        "conflict constraints",
        "accepts computes plan targets input",
        "produces computes plan targets result",
        "computes plan targets input",
        "computes plan targets result",
        "output coverage for computes plan targets and",
        "one follow-up.",
        "state profile",
        "user path, state, evidence, decision, and follow-up",
        "entry, actions, feedback, and handoff",
        "evidence Its proof obligation",
        "run the repo-native test, lint, typecheck, build, and browser proof named by the first technical plan",
    ):
        assert banned not in rendered

    plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=_created_backlog(proposal, tmp_path),
        diagram_ids=[f"D-{index:03d}" for index in range(1, len(proposal["diagrams"]) + 1)],  # type: ignore[index]
    )
    component_lines = greenfield_traceability._component_lines_for_workstream("B-001", proposal=proposal, plan=plan)
    assert component_lines
    assert all("Related diagrams:" not in line for line in component_lines)
    assert all(line.count(":") == 0 for line in component_lines)


def test_greenfield_ranking_engine_and_review_surface_stay_distinct(tmp_path: Path) -> None:
    proposal = _trip_comparison_proposal(tmp_path)
    ranking = _component_contract(proposal, "Option Ranking")
    surface = _component_contract(proposal, "Comparison Review")
    diagrams = {str(row["title"]): str(row["mermaid_source"]) for row in proposal["diagrams"]}  # type: ignore[index]
    sequence = diagrams["First Path Sequence"]
    boundary = diagrams["Component Boundary View"]
    proof = diagrams["Release Proof Review"]
    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    rendered = json.dumps(proposal, sort_keys=True)

    assert decision.passed
    assert "alternatives by fare" in str(ranking["owned_state"]).casefold()
    assert "ranked alternatives" in str(ranking["produced_outputs"]).casefold()
    assert "alternatives by fare" not in str(surface["owned_state"]).casefold()
    assert "ranked options" in str(surface["owned_state"]).casefold()
    assert "candidate ranked options" in str(surface["accepted_inputs"]).casefold()
    assert "route evidence" in str(surface["owned_state"]).casefold()

    assert sequence.startswith("flowchart LR")
    assert "Enter origin, destination" in sequence
    assert "S1 --> C1" in sequence
    assert "Fetch candidate options" in sequence
    assert "S2 --> C2" in sequence
    assert "Calculate fare and schedule<br/>evidence" in sequence
    assert "S3 --> C3" in sequence
    assert "Rank alternatives" in sequence
    assert "S4 --> C4" in sequence
    assert "Highlight the lowest-cost<br/>acceptable route" in sequence
    assert "S5 --> C5" in sequence
    assert "Let the traveler choose an<br/>option" in sequence
    assert "Store the comparison evidence" in sequence
    assert "A1->>" not in sequence
    assert 'input1["External input<br/>Transit schedule feed"] --> boundary2' in boundary
    assert 'input2["External input<br/>Fare table feed"] --> boundary3' in boundary
    assert "Proof checkpoint<br/>Proven when one traveler can enter a trip" in proof
    assert "check traveler" not in proof
    assert "Commuter, and" not in rendered
    assert "user path, state, evidence, decision, and follow-up" not in rendered
    assert "entry, actions, feedback, and handoff" not in rendered
    assert "state profile" not in rendered


def test_greenfield_tribunal_rejects_shallow_confirmed_artifact_substance(tmp_path: Path) -> None:
    proposal = _trip_comparison_proposal(tmp_path)
    proposal["backlog"][1]["problem"] = "Do the thing."  # type: ignore[index]
    proposal["backlog"][1]["opportunity"] = "Build it."  # type: ignore[index]
    proposal["backlog"][1]["product_view"] = "Users use it."  # type: ignore[index]
    proposal["backlog"][1]["recommended_first_slice"] = "Implement it."  # type: ignore[index]
    proposal["backlog"][1]["success_metrics"] = ["It works.", "It is done."]  # type: ignore[index]
    proposal["backlog"][1]["dependencies"] = ["Generic dependency."]  # type: ignore[index]
    proposal["backlog"][1]["interfaces"] = ["Generic interface."]  # type: ignore[index]
    proposal["backlog"][1]["validation"] = ["Generic validation."]  # type: ignore[index]
    for component in proposal["components"]:  # type: ignore[index]
        if "Comparison Review" in str(component["label"]):
            component["component_contract"]["owned_state"] += ", ranking rule"  # type: ignore[index]
    for diagram in proposal["diagrams"]:  # type: ignore[index]
        if diagram["title"] == "First Path Sequence":
            diagram["mermaid_source"] = "sequenceDiagram\n  A1->>C1: Start\n"

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    issues = "\n".join(decision.issues)

    assert not decision.passed
    assert "confirmed Radar workstream `Let Traveler Enter Origin, Destination, Departure Time, and Preference` is too thin" in issues
    assert "presentation boundary but owns computation or source-truth state" in issues
    assert "collapses the first path into too few events" in issues


def test_greenfield_tribunal_rejects_cross_axis_registry_proof_leakage(tmp_path: Path) -> None:
    proposal = _trip_comparison_proposal(tmp_path)
    proposal["components"][0]["component_contract"]["local_proof"] = [  # type: ignore[index]
        "Privacy lifecycle proof shows actor identity, consent history, protected-state reference, retention rule, lifecycle decision, and audit event.",
        "Deletion block proof keeps protected state unchanged.",
        "Lifecycle replay proof reconstructs protected-data lifecycle states.",
    ]
    proposal["components"][1]["component_contract"]["owned_state"] += ", question list"  # type: ignore[index]

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    issues = "\n".join(decision.issues)

    assert not decision.passed
    assert "uses privacy lifecycle proof for a non-privacy ownership boundary" in issues
    assert "imports question-tracking state without a question or response boundary" in issues


def test_greenfield_tribunal_rejects_sequence_tail_truncation(tmp_path: Path) -> None:
    proposal = _trip_comparison_proposal(tmp_path)
    for diagram in proposal["diagrams"]:  # type: ignore[index]
        if diagram["title"] == "First Path Sequence":
            diagram["mermaid_source"] = "\n".join(
                [
                    "sequenceDiagram",
                    "  autonumber",
                    "  participant A1 as Commuter",
                    "  participant C1 as Trip Intake Adapter",
                    "  participant C2 as Schedule Candidate Service",
                    "  participant C3 as Fare Evidence Service",
                    "  A1->>C1: A traveler enters trip details",
                    "  C1->>C2: prepare to fetch candidate options",
                    "  A1->>C2: Fetches candidate options",
                    "  C2->>C3: prepare to calculate fare evidence",
                    "  A1->>C3: Calculates fare evidence",
                ]
            )

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")
    issues = "\n".join(decision.issues)

    assert not decision.passed
    assert "omits the tail of the accepted first path" in issues


def test_greenfield_release_title_normalization_preserves_comma_bearing_titles() -> None:
    title = "Build Account, Data Export, and Deletion Proof Review"

    release_plan = _normalize_release_plan(
        {
            "selector": "0.0.1",
            "target_workstream_titles": title,
            "release_stages": [{"stage": "wave-1", "workstream_titles": title}],
        }
    )

    assert release_plan["target_workstream_titles"] == [title]
    assert release_plan["release_stages"][0]["workstream_titles"] == [title]


def test_greenfield_quality_gate_rejects_split_release_title_fragments(tmp_path: Path) -> None:
    proposal = _service_goal_proposal(tmp_path)
    proposal["release_plan"]["target_workstream_titles"] = [  # type: ignore[index]
        "Build Account",
        "Data Export",
        "and Deletion Proof Review",
    ]

    issues = greenfield_quality_issues(proposal)

    assert any("references workstream title" in issue for issue in issues)


def test_greenfield_component_contract_normalizes_capability_phrases_into_artifacts() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Planning Engine",
            "source_system_description": "computes plan targets from progress snapshots and status windows with rationale",
        },
        proposal={"intent": {"title": "Generic Planning", "first_path": "A user receives an adjusted plan target."}},
        sibling=None,
        previous_label="Daily Progress Logging",
        next_label="Weekly Status Review",
        state_label="planning record",
    ).fields
    rendered = json.dumps(contract, sort_keys=True).casefold()

    assert "computes plan targets input" not in rendered
    assert "computes plan targets result" not in rendered
    assert "plan adjustment request" in str(contract["accepted_inputs"]).casefold()
    assert "progress snapshot" in str(contract["accepted_inputs"]).casefold()
    assert "status window" in str(contract["accepted_inputs"]).casefold()
    assert "plan adjustment result" in str(contract["produced_outputs"]).casefold()
    assert "adjustment rationale" in str(contract["produced_outputs"]).casefold()


def test_greenfield_component_contract_nominalizes_inflected_verbs_and_notes() -> None:
    guardrail = derive_component_semantic_contract(
        {
            "label": "Availability Guardrail Service",
            "source_system_description": "verifies availability and checkout eligibility. Relevant behavior: approve checkout, and return condition.",
        },
        proposal={"intent": {"title": "Generic Resource Checkout"}},
        sibling=None,
        previous_label="Reservation Intake Adapter",
        next_label="Checkout Approval Ledger",
        state_label="resource item",
    ).fields
    rendered_guardrail = json.dumps(guardrail, sort_keys=True).casefold()

    assert "verifies availability" not in rendered_guardrail
    assert "approve checkout" not in rendered_guardrail
    assert "availability" in rendered_guardrail
    assert "checkout eligibility" in rendered_guardrail
    assert "checkout" in rendered_guardrail

    recorder = derive_component_semantic_contract(
        {
            "label": "Return Condition Recorder",
            "source_system_description": "records returned state, damage notes, and restoration blockers.",
        },
        proposal={"intent": {"title": "Generic Resource Checkout"}},
        sibling=None,
        previous_label="Checkout Approval Ledger",
        next_label="Audit History Ledger",
        state_label="resource item",
    ).fields
    rendered_recorder = json.dumps(recorder, sort_keys=True).casefold()

    assert "damage notes" in rendered_recorder
    assert "case identity" not in rendered_recorder
    assert "workspace status" not in rendered_recorder
    assert "checklist progress" not in rendered_recorder


def test_greenfield_checklist_ledger_and_risk_review_workspace_stay_distinct(tmp_path: Path) -> None:
    assert component_axis_key_for_label("Compliance Checklist Ledger").startswith("derived_")
    assert component_axis_key_for_label("Risk Review Workspace").startswith("derived_")
    assert component_axis_key_for_label("Habit, Activity, Status, and Check-in Tracking Service").startswith("derived_")
    assert component_axis_key_for_label("Progress Analytics and Status Explanations Service").startswith("derived_")

    text = """# Vendor Onboarding Review

## Product Story
Vendor Onboarding Review helps a procurement team collect vendor documents, verify required compliance evidence, approve or block onboarding, and record the reason before spend begins.

## State Object
A vendor onboarding file tracks vendor identity, submitted documents, compliance checklist, risk review, approval decision, blocked reason, spend-readiness status, notification status, and audit history.

## First Complete Path
A vendor submits onboarding documents, the product validates required files, runs compliance checks, routes risk review to procurement, records approval or blocked reason, notifies the vendor, marks spend readiness, and preserves audit history.

## Human Actors
- Vendor contact: submits documents and receives approval or blocked reason.
- Procurement reviewer: verifies compliance evidence, records risk review, and approves or blocks readiness.

## External Systems
- Document repository: stores submitted vendor files.
- Message provider: delivers vendor notifications.

## Internal Product Systems
- Vendor Intake Adapter: captures vendor identity, files, and missing-document blockers.
- Compliance Checklist Ledger: records required checks, rule references, and pass or block outcomes.
- Risk Review Workspace: records reviewer notes, risk flags, and readiness blockers.
- Vendor Notification Log: records notification delivery and response state.
- Spend Readiness Decision Service: records approval or blocked reason and readiness handoff.
- Audit Retention Ledger: preserves immutable onboarding history.

## Critical Assumptions
- Release 0.0.1 supports deterministic document fixtures before live repository credentials.
- The first release supports one procurement reviewer.

## Ambiguities
- Exact compliance checklist content needs legal owner confirmation.

## Proof Boundary
Release 0.0.1 succeeds when one vendor can submit documents, missing files block review, required checks are recorded, procurement can approve or block readiness with a reason, the vendor notification is recorded, and audit history can replay the decision.
"""
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Create vendor onboarding",
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(text),
    )
    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert decision.passed, decision.issues
    by_label = {str(component["label"]): component["component_contract"] for component in proposal["components"]}
    checklist = by_label["Compliance Checklist Ledger"]
    risk_review = by_label["Risk Review Workspace"]
    checklist_rendered = json.dumps(checklist, sort_keys=True).casefold()
    risk_owned = str(risk_review["owned_state"]).casefold()
    risk_rendered = json.dumps(risk_review, sort_keys=True).casefold()
    proposal_rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert "rule reference" in checklist_rendered
    assert "pass or block" in checklist_rendered
    assert "policy rule" not in str(checklist["owned_state"]).casefold()
    assert "risk flags" in risk_owned
    assert "reviewer notes" in risk_owned
    assert "readiness blockers" in risk_owned
    assert "policy rule" not in risk_owned
    assert "risk disclosure" not in risk_owned
    assert "case identity" not in proposal_rendered
    assert "workspace status" not in proposal_rendered
    assert "checklist progress" not in proposal_rendered
    assert "accepted source changes" not in proposal_rendered
    assert "too interchangeable" not in risk_rendered

    checklist_spec = build_component_spec(
        component_id="compliance-checklist-ledger",
        label="Compliance Checklist Ledger",
        path="src/vendor_onboarding_review/compliance_checklist_ledger",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-003",),
        component_contract=checklist,
    )
    assert "check_rule_ledger_proof" not in checklist_spec
    assert "Suggested fixture:" not in checklist_spec
    assert "compliance" in checklist_spec.casefold()
    assert "Invalid or missing" in checklist_spec
    assert "replay proof" in checklist_spec


def test_greenfield_component_spec_renderer_uses_narrative_distinct_contract_sections() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Planning Engine",
            "source_system_description": "computes plan targets from progress snapshots and status windows with rationale",
        },
        proposal={"intent": {"title": "Generic Planning"}},
        sibling={"label": "Weekly Status Review", "source_system_description": "calculates weekly status and progress state"},
        previous_label="Daily Progress Logging",
        next_label="Weekly Status Review",
        state_label="planning record",
    ).fields

    spec = build_component_spec(
        component_id="planning-engine",
        label="Planning Engine",
        path="src/planning/engine.py",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-001",),
        component_contract=contract,
    )

    assert rendered_component_spec_quality_issues({"Planning Engine": spec}, project_title="Generic Planning") == []
    assert "## Component Brief" not in spec
    assert "## Boundary Narrative" not in spec
    assert "## First Release Proof" not in spec
    assert "## Implementation Starting Point" not in spec
    assert "Planning Engine carries the product logic" in spec
    assert "Component Snapshot" not in spec
    assert "runtime ownership boundary" not in spec
    assert "structured contract below" not in spec
    assert "Refused domain responsibilities:" not in spec
    assert "Forbidden runtime authorities:" not in spec
    assert "Source-backed proof named by the first implementation plan" not in spec
    assert "computes plan targets input" not in spec.casefold()

    assert "Suggested fixture:" not in spec
    assert "Planning Engine proof ties" in spec
    assert "Invalid or missing" in spec


def test_greenfield_component_spec_renderer_rejects_mechanical_contract_dump() -> None:
    contract = {
        "owned_state": (
            "Decision and reason-code service state, producing the explainable result, "
            "Related path: review flow captures declared facts, "
            "runs them against configurable review checks, decision reason-code, local blockers, "
            "handoff evidence for application review state"
        ),
        "accepted_inputs": (
            "Required producing the explainable result, decision reason-code command, required fields, "
            "prior state, source evidence, authorized actor, validation notes"
        ),
        "produced_outputs": (
            "Validated producing the explainable result, decision reason-code state, correction marker, "
            "replayable change evidence, blocked-state evidence, reviewer explanation, handoff record"
        ),
        "states_or_transitions": "open, requested, qualified, returned, visible, received, captured, validated, blocked, revised, handed-off",
        "outside_boundary": (
            "Refused domain responsibilities: responsibilities not named by this component boundary; "
            "sibling-owned state: reviewer queue state, case routing; "
            "forbidden runtime authorities: mutation of upstream source truth, silent overwrite of downstream handoff state, release approval"
        ),
        "local_proof": [
            "Decision and Reason-code Service proof ties producing the explainable result, required inputs, produced outputs, blocker behavior, and downstream handoff together",
            "Invalid or missing producing the explainable result blocks trusted downstream state instead of producing Decision and Reason-code Service output",
            "Decision and Reason-code Service replay proof preserves actor, source, validation status, blocker state, and handoff evidence",
        ],
        "upstream_truth": "Qualification Rules Engine",
        "downstream_consumers": "Reviewer Queue Service",
        "unique_failure": (
            "Decision and Reason-code Service can look complete while producing the explainable result is missing, "
            "stale, assigned to the wrong boundary, or released without source evidence, blocker state, or downstream handoff evidence."
        ),
    }

    spec = build_component_spec(
        component_id="decision-and-reason-code-service",
        label="Decision and Reason-code Service",
        path="src/application_review/decision_and_reason_code_service",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-004",),
        diagrams=("D-002",),
        component_contract=contract,
    )

    assert rendered_component_spec_quality_issues({"Decision and Reason-code Service": spec}, project_title="Application Review") == []
    assert "explainable result" in spec
    assert "decision reason-code" in spec
    assert "Qualification Rules Engine" in spec
    assert "Reviewer Queue Service" in spec
    for forbidden in (
        "Component Snapshot",
        "Component planning record for",
        "runtime ownership boundary",
        "structured contract below",
        "It exists to make this failure testable",
        "Related path:",
        "Required producing",
        "Validated producing",
        "Suggested fixture:",
        "Refused domain responsibilities:",
        "Forbidden runtime authorities:",
        "Operator Verification",
        "Related path:",
        "runs them against",
    ):
        assert forbidden not in spec


def test_greenfield_component_ids_remove_product_component_word_overlap() -> None:
    rows = confirmed_components(
        label="Service Goal Planning",
        label_slug="service-goal-planning",
        internal_systems=[
            "Planning Engine: computes plan targets from progress snapshots and status windows.",
        ],
        first_path="A user receives an adjusted plan target.",
        state_object="planning record",
        proof_boundary="Plan adjustment evidence is visible.",
    )

    component_id = str(rows[0]["component_id"])
    assert component_id == "service-goal-planning-engine"
    assert "planning-planning" not in component_id

def test_greenfield_quality_gate_rejects_verb_phrase_slot_filling() -> None:
    issues = public_prose_quality_issues(
        {
            "component_contract": {
                "accepted_inputs": "Planning Engine accepts computes plan targets input.",
                "produced_outputs": "Planning Engine produces computes plan targets result.",
            }
        }
    )

    assert any("verb phrase inserted into contract artifact slot" in issue for issue in issues)

def test_greenfield_quality_gate_rejects_generic_governance_posture_filler() -> None:
    issues = public_prose_quality_issues(
        {
            "problem": "The user path, state, evidence, decision, and follow-up are scattered.",
            "opportunity": "Build the narrow entry, actions, feedback, and handoff before adding scope.",
            "product_view": "Users inspect state profile, the first-path outcome, visible blockers, risk posture, and evidence.",
        }
    )

    assert any("generic governance posture filler" in issue for issue in issues)

def test_greenfield_first_action_clause_stops_before_next_product_action() -> None:
    assert (
        _first_action_clause(
            "A requester submits a maintenance request, the product verifies required details, assigns a technician, estimates cost and timing, and notifies the requester."
        )
        == "A requester submits a maintenance request"
    )
    assert _sentence_fragment("Validated intake request and downstream handoff") == "validated intake request and downstream handoff"
