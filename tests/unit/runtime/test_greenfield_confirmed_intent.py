from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import normalize_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.governance import artifact_tribunal
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import _confirmed_intent
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


def test_confirmed_intent_parser_keeps_ambiguities_out_of_first_path() -> None:
    intent = _confirmed_intent()

    assert "Does the first release need applicant self-service" not in str(intent["first_path"])
    assert intent["first_path"].endswith("final status.")
    assert intent["ambiguities"] == [
        "Does the first release need applicant self-service, or only internal staff review?",
        "Are zoning rules imported from a live GIS source, or referenced manually by reviewers?",
        "Does final approval require one supervisor or multiple department sign-offs?",
    ]


def test_confirmed_intent_parser_allows_hyphenated_domain_workflow_phrases() -> None:
    text = CONFIRMED_INTENT_TEXT.replace(
        "A permit coordinator imports one permit application, a zoning reviewer records a zoning check, "
        "the applicant submits one revision, and a supervisor reviews the decision package with traceable "
        "documents, comments, checks, and final status.",
        "A permit coordinator uses a mobile-first workflow to import one permit application, a zoning "
        "reviewer records a zoning check, the applicant submits one revision, and a supervisor reviews "
        "the decision package with traceable documents, comments, checks, and final status.",
    )

    intent = parse_confirmed_intent_text(
        text,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )

    assert "mobile-first workflow" in str(intent["first_path"])


def test_confirmed_intent_parser_strips_markdown_emphasis_from_actor_rows() -> None:
    intent = parse_confirmed_intent_text(
        """Shared Operations Review — Product Intent Confirmation

Product story
The workspace helps an operator find stale work items, understand why each item needs review, decide whether to keep or close it, and leave a traceable outcome for the next reviewer. The product connects item ingestion, evidence review, operator approval, and follow-up tracking so the operator and support reviewer can see what changed and why.

State object that changes through the first journey
A review record tracks imported items, evidence, operator approval, action state, and the next follow-up check.

First complete path the product should prove before broader scope
The user imports work history, reviews one stale item, approves a close-or-keep decision, records the outcome, and checks whether the next follow-up state changed as expected.

Human actors
- **Primary operator:** wants to reduce stale work without accidentally closing important items.
- **Support reviewer:** checks ambiguous follow-up attempts and user disputes.

External systems
- Work history export.
- External action portal or support inbox.

Internal product systems
- Work item ingestion — imports activity and normalizes item id, source, timestamp, status, and owner so review evidence starts from a consistent record.
- Stale-item detection — identifies likely stale items from repeated inactivity, status age, dependency state, and known workflow markers while keeping uncertainty visible.
- User review flow — explains evidence to the primary operator, captures keep-or-close approval, and prevents action without an explicit user decision.
- Follow-up tracker — records the attempted action, external response, support reviewer escalation, and follow-up status for the next cycle.

Critical assumptions
- Release 0.0.1 guides or records one review path; it does not claim universal automated remediation.

Ambiguities that would change the first path
- Whether work history import comes from a live connection or a file export.

Proof boundary
Release 0.0.1 succeeds when a reviewer can see the imported items, the stale-item evidence, the user approval, the action outcome, and the next follow-up check.
""",
        prompt="Draft a product-first greenfield proposal for a shared operations review workspace.",
    )

    encoded = json.dumps(intent)
    assert "**" not in encoded
    assert "Primary operator: wants to reduce stale work" in encoded
    assert "Support reviewer: checks ambiguous follow-up attempts" in encoded


def test_confirmed_intent_parser_accepts_current_sectioned_confirmation_contract() -> None:
    intent = parse_confirmed_intent_text(
        """Product Intent Confirmation

Inventory Service Quality Tracker

Product story
A small operations team needs one place to see whether service inventory is ready for daily work. The product turns intake records, inspection notes, stock counts, and repair status into a clear readiness view so a coordinator can decide what can be assigned, what needs attention, and what should stay out of circulation.

State object
The state object is an inventory readiness record: item identity, current condition, availability, inspection history, open repair notes, assignment status, and reviewer decision.

First complete path
A coordinator imports a small item list, opens one item, records an inspection, marks one repair blocker, clears that blocker, and sees the item move from unavailable to ready with a traceable explanation.

Human actors
- Coordinator: reviews readiness and decides what can be used.
- Inspector: records condition and repair evidence.
- Operations reviewer: checks whether readiness claims are supported.

External systems
- CSV or spreadsheet exports from the current inventory system.
- Repair notes, inspection photos, and assignment records.

Internal product systems
- Inventory import and normalization: converts item lists into stable records with item identity, condition, source, and assignment context.
- Readiness state tracker: records availability, blockers, repair status, reviewer decision, and the state transitions that explain why an item is ready.
- Inspection and repair evidence log: captures inspection notes, repair evidence, blocker clearance, and reviewer-visible history.

Critical assumptions
- The first release is an internal operations tool.
- Imports can start from CSV before live integrations exist.

Ambiguities
- Whether item identity comes from barcode, SKU, asset tag, or manual entry.
- Whether repair evidence must include images in the first release.

Proof boundary
Release 0.0.1 is trusted only when one item can move through import, inspection, blocker, repair clearance, and ready decision with evidence that a reviewer can inspect. It must not claim live integrations, automatic repair diagnosis, or production-scale assignment planning yet.

Next step
Confirm: create the governed greenfield records from this accepted interpretation.
Edit: revise the product story, first path, actors, systems, assumptions, ambiguities, or proof boundary before writing records.
Reject: stop without writing records.
""",
        prompt="Draft a product-first greenfield proposal for an inventory service quality tracker.",
    )

    assert intent["state_object"].startswith("The state object is an inventory readiness record")
    assert str(intent["first_path"]).startswith("A coordinator imports a small item list")
    assert "Next step" not in str(intent["proof_boundary"])
    assert len(intent["internal_systems"]) == 3


def test_confirmed_intent_parser_accepts_domain_specific_evidence_review_surface(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """Equipment Reliability Review Workspace — Product Intent Confirmation

Product story
The app helps reliability engineers catch efficiency loss and early equipment degradation before it turns into missed performance, unplanned service changes, or operational failures. It gives engineers one reviewable workspace for run data, equipment state, degradation signals, and maintenance decisions so the team can act before the next run.

State object
An Equipment Health Record tracks equipment identity, session run, telemetry summary, efficiency trend, inspection notes, degradation alerts, maintenance decision, and evidence attached to each readiness state.

First complete path
A reliability engineer imports one run, reviews equipment telemetry and inspection notes, sees an efficiency-loss warning, records a maintenance decision, and verifies whether the equipment is cleared, watched, or removed before the next run.

Human actors
- Reliability engineer — reviews run evidence, decides whether equipment condition is safe enough for the next run, and owns the maintenance recommendation.
- Operations lead — checks the engineer decision and coordinates service change or continued use.
- Data engineer — maintains telemetry feeds and confirms signal quality before reliability claims are trusted.

External systems
- Telemetry logger supplies run traces and sensor samples.
- Maintenance history system supplies prior equipment usage, service intervals, and component changes.

Internal product systems
The internal product systems include a telemetry ingestion pipeline, equipment health model, degradation alert ledger, maintenance decision workspace, and run evidence review surface.

Critical assumptions
- Release 0.0.1 starts with one equipment asset and one post-run review path.
- Sensor data is imported from fixtures before live team integrations are trusted.
- The product recommends maintenance review but does not automate operational safety approval.

Ambiguities
- Which telemetry channels are required for the first reliability signal?
- What threshold should classify efficiency loss as actionable?
- Who has authority to clear equipment after a warning?

Proof boundary
Release 0.0.1 succeeds when an engineer can import one run, inspect the equipment health record, see the degradation evidence and efficiency trend, record the maintenance decision, and explain why the equipment is cleared, watched, or removed before the next run.
""",
        prompt="Build an equipment reliability review app",
    )

    assert len(intent["internal_systems"]) == 5
    assert any(row.startswith("Run Evidence Review Surface —") for row in intent["internal_systems"])
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Build an equipment reliability review app",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    encoded = json.dumps(proposal)
    assert "Run Evidence Review Surface" in encoded
    assert not greenfield_quality_issues(proposal)


def test_confirmed_intent_parser_still_rejects_exact_generic_system_scaffold() -> None:
    with pytest.raises(ValueError, match="internal_systems"):
        parse_confirmed_intent_text(
            """Generic Workflow Workspace — Product Intent Confirmation

Product story
The workspace helps an operations reviewer complete one reliable workflow without losing the state, supporting evidence, or final decision. The product gives the reviewer a single place to inspect the request, follow the handoff, and understand why the outcome should be trusted before broader automation is introduced.

State object
A workflow record moves from submitted to reviewed to decided, keeping the active state, owner, evidence references, blocked reason, and final outcome attached to each transition.

First complete path
A reviewer imports one request, checks the current state, reviews the evidence, records a decision, and confirms that the workflow outcome is visible with the supporting state and evidence before release.

Human actors
- Reviewer — inspects the workflow record, evaluates evidence, and records the decision.
- Operations lead — checks whether the decision path is trustworthy enough to release.

Internal product systems
- Workflow service — records the request handoff and workflow step progression.
- State store — stores the current workflow state and transition history.
- Evidence review — checks supporting evidence before the reviewer records the decision.

Critical assumptions
- The first release proves one workflow path before automation.

Ambiguities
- Whether the first release needs one reviewer or two reviewers.

Proof boundary
Release 0.0.1 succeeds when a reviewer can inspect one workflow record, see the state, evidence, and decision, and explain why the outcome is ready without relying on hidden chat context.
""",
            prompt="Build a generic workflow workspace",
        )


def test_confirmed_intent_parser_accepts_internal_external_heading_and_prose_systems() -> None:
    intent = parse_confirmed_intent_text(
        """# Product Intent Confirmation

	Product title:
	Low-Cost Field Water Quality Monitor

	Product story:
	The product is a compact low-cost field water-quality monitor for community groups that need quick local screening before sending samples to a lab. It captures pH, turbidity, temperature, and conductivity readings, guides a non-specialist through calibration, and produces a readable result that explains whether the sample is safe, uncertain, or needs lab review. The value is practical screening without turning the device into a professional laboratory instrument.

	State object that changes through the first journey:
	The primary state object is the water sample assessment. An assessment starts as prepared, tracks calibration state, sample source, readings, confidence bands, battery level, contamination warnings, and reviewer notes, then ends as passed, flagged for retest, escalated to lab review, or safely discarded.

	First complete path the product should prove before broader scope:
	A field volunteer powers on the device, confirms calibration, collects one water sample, records the sample location and source, runs the sensor reading, sees a safe-or-review result, and exports a clear sample assessment with readings, calibration evidence, and next action.

	Main human actors:
	- Field volunteer who collects samples and needs simple prompts, calibration feedback, and a readable result.
	- Program coordinator who reviews sample trends and decides which sites need lab follow-up.
	- Lab reviewer who receives escalated samples and checks whether field evidence is complete enough to trust.

	External systems separated from internal product systems:
	- Water sources, sample containers, calibration solution, and field conditions.
	- Optional lab information system used for escalated samples.

	Internal systems separated from external systems:
	The internal product systems combine a sampling probe and a low-cost sensor board and a calibration controller and a battery enclosure module and a result display and an assessment recorder and a safety cleanup checklist into one portable screening device. These internal systems matter because the product must stay inexpensive and field-ready while still producing trustworthy readings, calibration evidence, contamination handling, runtime status, and clear escalation behavior for the first screening path.

	Critical assumptions:
	- Low cost means community-affordable and bill-of-materials conscious, not laboratory-grade.
	- Field screening means triage evidence only; certified water-safety decisions stay with lab or regulatory review.

	Ambiguities that materially change the proposal:
	- Which measurements belong in release 0.0.1 versus later sensor expansion.
	- Whether sample records stay local-only or sync to a coordinator dashboard.

	Proof boundary:
	Evidence should come from a bench test or field trial showing calibration, sample reading stability, result explanation, battery behavior, and safe cleanup handling. Until then, the product must not claim regulatory certification, laboratory accuracy, contamination-safe handling for every sample type, or reliable operation across all field conditions.
	""",
        prompt="Draft a product-first greenfield proposal for a low-cost field water quality monitor.",
    )

    assert intent["title"] == "Low-Cost Field Water Quality Monitor"
    assert "Water sources" in intent["external_systems"][0]
    internal_systems = intent["internal_systems"]
    assert len(internal_systems) >= 6
    assert any("Calibration Controller" in row for row in internal_systems)
    assert any("Battery Enclosure Module — Owns battery enclosure module. Relevant behavior" in row for row in internal_systems)
    assert any("battery level" in row for row in internal_systems)
    assert not any("Owns the accepted" in row for row in internal_systems)
    assert all("—" in row for row in internal_systems)
    assert not any("External systems" in row for row in internal_systems)


def test_confirmed_intent_parser_accepts_product_title_and_underscored_system_heading() -> None:
    intent = parse_confirmed_intent_text(
        """# Product Intent Confirmation

## Product Title
Neighborhood Repair Desk

## Product Story
The Neighborhood Repair Desk helps a small operations team receive repair requests, understand which location and asset are affected, route the work to the right crew, and keep residents informed without losing the evidence behind each decision. The product turns scattered calls, photos, location notes, crew updates, and completion checks into one repair record that a coordinator can trust before promising that a problem is resolved.

## State Object
The primary state object is a repair case. It starts as reported, gathers location evidence, asset context, triage priority, assignment, crew updates, resident messages, completion evidence, and final review, then ends as resolved, deferred, duplicate, or blocked with a clear reason.

## First Complete Path
A resident reports a broken shared asset, the coordinator confirms the location and photos, the triage reviewer assigns a priority, the repair crew records the work outcome, and the coordinator closes the case only after the evidence and resident-visible status agree.

## Human Actors
- Resident: reports the issue, supplies location context, and needs a clear status without learning internal queue details.
- Coordinator: reviews new cases, routes work, watches blocked repairs, and decides when a case can be closed.
- Repair crew: receives assigned work, records field updates, and attaches completion evidence from the site.

## Systems
External systems are resident email, field photos, location references, maintenance contractors, and optional facilities maps.

Internal product systems are request intake, evidence ledger, triage queue, assignment tracker, crew update recorder, resident status view, and closure review.

## External Systems
- Resident email and notification channel.
- Field photo source and location reference.

## internal_systems
- Request intake service that captures the resident report, contact route, affected location, asset hint, and original issue description before triage begins.
- Evidence ledger that stores photos, notes, timestamps, reviewer comments, and crew updates so a closeout decision can be traced.
- Triage queue that assigns urgency, ownership, and blocked status while keeping duplicate or unsafe work from moving forward silently.
- Crew update recorder that records field progress, completion evidence, failed access, and follow-up needs from the repair crew.

## Critical Assumptions
- The first release coordinates repair evidence and status; it does not dispatch emergency services or replace contractor management.
- Location evidence may be imperfect, so the product must preserve uncertainty instead of pretending every report is precise.

## Proof Boundary
Release proof requires one repair case to move from resident report to triage, assignment, field update, closure review, and resident-visible final status. A reviewer must be able to trace the closeout decision back to the original report, evidence ledger, crew update, and unresolved blockers.
""",
        prompt="Draft a product-first greenfield proposal for a neighborhood repair desk.",
    )

    assert intent["title"] == "Neighborhood Repair Desk"
    assert len(intent["human_actors"]) == 3
    assert "Resident email" in intent["external_systems"][0]
    assert len(intent["internal_systems"]) == 4
    assert any(row.startswith("Request Intake Service — captures") for row in intent["internal_systems"])
    assert any(row.startswith("Triage Queue — assigns urgency") for row in intent["internal_systems"])


def test_confirmed_intent_parser_uses_opening_narrative_as_product_story() -> None:
    intent = parse_confirmed_intent_text(
        """# Community Permit Review Workspace

A small city office needs one place to receive permit requests, check zoning rules, collect reviewer comments, and show applicants where each request stands. The first release proves that a simple permit can move from intake to review decision without losing the applicant, parcel, rule check, comment history, or final outcome.

## State object that changes through the first journey
Permit request — starts as draft, moves to submitted, checked for zoning fit, reviewed, decided, and closed with an applicant-visible decision record.

## First complete path Odylith should prove before broader scope
An applicant submits one permit request with parcel details and attachments. The system validates the required fields, runs a zoning checklist, routes the request to a reviewer, records the decision with reasons, and shows the applicant the result and next step.

## Human actors
- Applicant: submits a permit request and needs a clear status and decision.
- Permit reviewer: checks request details, zoning fit, attachments, and decision reasons.

## External systems
- Parcel records and zoning maps.
- Email notification provider.

## Internal systems
- Intake service: captures applicant details, parcel reference, requested work, and attachments.
- Zoning checklist service: evaluates required rules and records pass, warning, or failure reasons.
- Review decision ledger: stores reviewer decision, reasons, timestamps, and applicant-visible outcome history.

## Critical assumptions
- First release handles one permit type and one jurisdiction.

## Ambiguities that would change the first path
- Whether zoning checks are manual, rules-based, or integrated with a city GIS system.

## Proof boundary
Release proof must show the accepted permit path end to end with source evidence for intake validation, zoning checklist output, reviewer decision, applicant-visible status, non-goals, and safe handling of missing information.
""",
        prompt="Draft a product-first greenfield proposal for a community permit review workspace.",
    )

    assert intent["title"] == "Community Permit Review Workspace"
    assert str(intent["product_story"]).startswith("A small city office needs")
    assert "Community Permit Review Workspace" not in str(intent["product_story"])


def test_confirmed_intent_parser_accepts_single_clear_opening_story_sentence() -> None:
    intent = parse_confirmed_intent_text(
        """# Community Permit Review Workspace

A neighborhood association needs one place to receive permit requests, collect required documents, route reviews, record decisions, and show residents what changed without losing context in email threads.

## State object that changes through the first journey
A permit request moves from drafted to submitted, reviewed, approved or rejected, and archived with its evidence and decision history.

## First complete path Odylith should prove before broader scope
A resident submits one permit request with documents, a reviewer checks completeness, the association records an approval or rejection, and the resident sees the outcome and reason.

## Human actors
- Resident: submits requests and reads outcomes.
- Reviewer: checks documents and records decisions.
- Association manager: monitors pending requests and resolves disputes.

## External systems
- Email notifications.
- Document storage.
- Municipal reference rules.

## Internal systems
- Request intake service that captures submitted forms and attachments.
- Review queue that tracks completeness, reviewer assignment, and decision status.
- Decision record that preserves approval, rejection, reason, actor, and timestamp.

## Critical assumptions
- This is an internal workflow for one association first.

## Ambiguities
- Whether residents need public status tracking or private email-only updates.

## Proof boundary
Release evidence must show one request submitted, reviewed, decided, and visible to the resident with source documents and decision history. It must not claim automated legal compliance or municipal submission.
""",
        prompt="Draft a product-first greenfield proposal for a community permit review workspace.",
    )

    assert intent["title"] == "Community Permit Review Workspace"
    assert str(intent["product_story"]).startswith("A neighborhood association needs")


def test_confirmed_intent_parser_enriches_concise_capability_rows_without_schema_repair() -> None:
    intent = parse_confirmed_intent_text(
        """# Field Sensor Review Workspace

A field operations team needs one place to pair a supported sensor, receive readings, explain gaps, show daily status, and let an operator decide whether a site needs attention. The first release proves that sensor data can move from device connection to reviewed status without hiding missing readings, abnormal signals, or unresolved consent and retention decisions.

## State object that changes through the first journey
The primary state object is a site reading timeline. It starts as unpaired, moves through paired, receiving data, quality checked, summarized, alerted, reviewed, exported or deleted, and records stale or abnormal states without pretending they are trusted measurements.

## First complete path Odylith should prove before broader scope
An operator pairs one supported device, grants data permissions, receives live readings, views a current dashboard, reviews a daily summary, sees a clear missing-data or abnormal-reading warning, and manages export or deletion for the stored readings.

## Human actors
- Operator: pairs the device, reads the dashboard, and decides what follow-up is needed.
- Reviewer: checks whether the reading history and warning state are trustworthy enough to act on.
- Support lead: diagnoses sync failures and protects sensitive reading data during incidents.

## External systems
- Sensor hardware, firmware, and calibration source.
- Device operating system permissions.
- Optional notification and storage provider.

## Internal systems
- Device pairing and sync.
- Sensor ingestion and quality checks.
- Metric normalization and status generation.
- Consent, sharing, retention, and deletion.
- Dashboard, history, alerts, and export.

## Critical assumptions
- The first release explains readings and status; it does not claim regulated diagnosis or emergency monitoring.
- The supported device has a stable protocol or fixture contract for the first release.

## Ambiguities
- Whether data stays local-only or can sync to a cloud account.

## Proof boundary
Release proof must show one supported device path from pairing through live reading, stale-data handling, summary generation, warning display, privacy control, export, and deletion. It must not claim certified accuracy, diagnosis, emergency response, or broad hardware compatibility without separate validation.
""",
        prompt="Draft a product-first greenfield proposal for a field sensor review workspace.",
    )

    systems = intent["internal_systems"]
    assert len(systems) == 5
    assert systems[0].startswith("Device Pairing And Sync — owns the device pairing and sync responsibility")
    assert all("—" in row for row in systems)
    assert all("missing or too thin" not in row for row in systems)


def test_confirmed_intent_completion_expands_thin_actors_and_systems_generically() -> None:
    intent = parse_confirmed_intent_text(
        """# Evidence Review Workspace

An operations review team needs one workspace to collect submitted observations, compare them with reference rules, record uncertainty, and decide what follow-up is safe before the next review. The first release proves that one observation can move from intake to review decision without hiding missing evidence, unsafe assumptions, or unresolved ownership.

## State object
An evidence case tracks item identity, observation notes, source references, review status, uncertainty, follow-up decision, and final outcome.

## First complete path
A coordinator imports one submitted observation, a reviewer checks the evidence, the team records one uncertainty, the coordinator chooses a follow-up action, and the case ends with a clear reviewed or blocked status.

## Human actors
- Coordinator
- Reviewer
- Support helper

## External systems
- Submitted notes and supporting files.
- Reference rules.

## Internal product systems
- Case intake.
- Evidence review.
- Follow-up tracker.

## Proof boundary
Release 0.0.1 succeeds when a reviewer can inspect one evidence case, trace the observation to source notes, see the uncertainty and follow-up decision, and explain why the case is reviewed or blocked without claiming complete operational coverage.
""",
        prompt="Draft a product-first greenfield proposal for an evidence review workspace.",
    )

    assert len(intent["human_actors"]) >= 3
    assert all(len(row.split()) >= 7 for row in intent["human_actors"])
    assert len(intent["internal_systems"]) >= 3
    assert all("—" in row for row in intent["internal_systems"])
    assert all(len(row.split("—", 1)[1].split()) >= 5 for row in intent["internal_systems"])
    assert len(intent["success_metrics"]) >= 3
    assert intent["problem"]
    assert intent["customer"]
    assert intent["opportunity"]
    assert intent["product_view"]
    assert "missing or too thin" not in json.dumps(intent)


def test_confirmed_greenfield_create_completes_thin_intent_before_governed_records(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """# Decision Review Workspace

A small operations team needs one place to receive submitted observations, compare them against quality rules, record uncertainty, and decide whether an item can move forward or needs another review. The first release proves that one decision can be traced from intake through review without hiding missing measurements, reviewer judgment, or unsafe release claims.

## State object
A decision record tracks item identity, source observation, quality checks, uncertainty, reviewer notes, recheck status, and final release decision.

## First complete path
A coordinator imports one observation, a reviewer checks quality evidence, the system records one uncertainty, the reviewer chooses release or recheck, and the record shows the final status with source evidence.

## Human actors
- Coordinator
- Reviewer
- Operations lead

## External systems
- Submitted observation file.
- Quality reference rules.

## Internal product systems
- Case intake.
- Quality review.
- Decision ledger.

## Proof boundary
Release 0.0.1 succeeds when one decision record can be inspected from source observation through quality evidence, uncertainty, reviewer decision, recheck status, and final outcome without claiming automated approval or production certification.
""",
        encoding="utf-8",
    )

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a product-first greenfield proposal for a decision review workspace.",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    assert "greenfield create wrote confirmed proposal" in output
    assert "missing or too thin" not in output
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    encoded = json.dumps(accepted)
    assert "Decision Review Workspace" in encoded
    assert "Case Intake" in encoded
    assert "Quality Review" in encoded
    assert "Decision Ledger" in encoded


def test_confirmed_proposal_completion_adds_component_risks_and_fresh_diagram_watch_paths(tmp_path: Path) -> None:
    intent = parse_confirmed_intent_text(
        """# Field Sensor Review Workspace

A field operations team needs one place to pair a supported sensor, receive readings, explain gaps, show daily status, and let an operator decide whether a site needs attention. The first release proves that sensor data can move from device connection to reviewed status without hiding missing readings, abnormal signals, or unresolved consent and retention decisions.

## State object that changes through the first journey
The primary state object is a site reading timeline. It starts as unpaired, moves through paired, receiving data, quality checked, summarized, alerted, reviewed, exported or deleted, and records stale or abnormal states without pretending they are trusted measurements.

## First complete path Odylith should prove before broader scope
An operator pairs one supported device, grants data permissions, receives live readings, views a current dashboard, reviews a daily summary, sees a clear missing-data or abnormal-reading warning, and manages export or deletion for the stored readings.

## Human actors
- Operator: pairs the device, reads the dashboard, and decides what follow-up is needed.
- Reviewer: checks whether the reading history and warning state are trustworthy enough to act on.
- Support lead: diagnoses sync failures and protects sensitive reading data during incidents.

## External systems
- Sensor hardware, firmware, and calibration source.
- Device operating system permissions.
- Optional notification and storage provider.

## Internal systems
- Device pairing and sync.
- Sensor ingestion and quality checks.
- Metric normalization and status generation.
- Consent, sharing, retention, and deletion.
- Dashboard, history, alerts, and export.

## Critical assumptions
- The first release explains readings and status; it does not claim regulated diagnosis or emergency monitoring.
- The supported device has a stable protocol or fixture contract for the first release.

## Ambiguities
- Whether data stays local-only or can sync to a cloud account.

## Proof boundary
Release proof must show one supported device path from pairing through live reading, stale-data handling, summary generation, warning display, privacy control, export, and deletion. It must not claim certified accuracy, diagnosis, emergency response, or broad hardware compatibility without separate validation.
""",
        prompt="Draft a product-first greenfield proposal for a field sensor review workspace.",
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for a field sensor review workspace.",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )

    for component in proposal["components"]:
        risks = component.get("risks")
        assert isinstance(risks, list)
        assert len(risks) >= 3
        joined = " ".join(risks)
        assert "Domain risk:" in joined
        assert "Security and policy posture:" in joined
        assert "privacy" in joined.casefold()
        assert "retention" in joined.casefold()
        assert "safety" in joined.casefold()
        assert "…" not in joined
        decision = artifact_tribunal.run_governed_artifact_tribunal(
            artifact_kind="component",
            payload={
                "component_id": component["component_id"],
                "label": component["label"],
                "path": component["intended_path"],
                "kind": component["kind"],
                "responsibility": component["responsibility"],
                "boundary": component["boundary"],
                "interfaces": component["interfaces"],
                "dependencies": component["dependencies"],
                "validation": component["validation"],
                "risks": component["risks"],
            },
        )
        assert decision.passed, decision.issues

    for diagram in proposal["diagrams"]:
        assert diagram["watch_paths"]
        assert "odylith/atlas/source" not in diagram["watch_paths"]


def test_confirmed_intent_json_splits_labeled_roles_and_sentence_systems() -> None:
    intent = normalize_confirmed_intent(
        {
            "title": "Evidence Review Workspace",
            "product_story": (
                "The Evidence Review Workspace helps a review team collect submissions, compare them against "
                "the accepted policy, capture reviewer notes, and publish a clear decision without losing the "
                "source material behind that decision. The product value is that every acceptance, rejection, "
                "or escalation remains tied to the submitted evidence and the reviewer who made the call."
            ),
            "state_object": (
                "The primary state object is a review case that starts as submitted, moves through evidence "
                "capture, eligibility check, reviewer decision, escalation, and final publication, and keeps "
                "the source evidence attached throughout the journey."
            ),
            "first_path": (
                "A submitter opens one case, uploads evidence, the review team checks eligibility, a reviewer "
                "records a decision with a reason, and the system publishes a final status with the supporting "
                "evidence and unresolved caveats visible."
            ),
            "proof_boundary": (
                "Release proof requires one case to be submitted, reviewed, decided, and published with the "
                "original evidence, reviewer notes, decision reason, escalation state, and final status all "
                "visible to a reviewer."
            ),
            "human_actors": (
                "Submitter: provides the source material and needs a clear status. Reviewer: checks evidence, "
                "records the decision, and explains uncertainty. Operations lead: watches escalations and "
                "decides whether the process is ready to trust."
            ),
            "external_systems": "Email intake, document storage, identity provider, and policy reference material.",
            "internal_systems": (
                "Intake Console captures the submitted request, evidence references, source owner, and contact route. "
                "Evidence Ledger records attachments, reviewer notes, decision reasons, and timestamped state changes. "
                "Review Queue shows eligibility status, blocked cases, reviewer assignment, and escalation needs. "
                "Publication Record exposes the final decision, caveats, and evidence links for later review."
            ),
            "assumptions": [
                "The first release proves one review path before broad automation.",
                "External policy sources remain references, not owned truth.",
            ],
            "ambiguities": ["Whether approvals need one reviewer or two reviewers."],
            "non_goals": ["No automated final decisions in the first release."],
        },
        prompt="Draft a product-first greenfield proposal for an evidence review workspace.",
    )

    assert intent["human_actors"] == [
        "Submitter: provides the source material and needs a clear status",
        "Reviewer: checks evidence, records the decision, and explains uncertainty",
        "Operations lead: watches escalations and decides whether the process is ready to trust",
    ]
    assert intent["internal_systems"][0].startswith("Intake Console — captures the submitted request")
    assert all("Captures The Submitted" not in row for row in intent["internal_systems"])


def test_confirmed_create_uses_structured_intent_fields_without_repair_loop(tmp_path: Path) -> None:
    intent = normalize_confirmed_intent(
        {
            "title": "Evidence Review Workspace",
            "product_story": (
                "An operations team needs a shared workspace for collecting submitted evidence, checking it "
                "against an accepted policy, recording the reviewer decision, and publishing a result that a "
                "later reviewer can understand without reconstructing the context from chat messages, files, "
                "and disconnected notes."
            ),
            "problem": (
                "Review decisions become unsafe when submitted evidence, policy checks, reviewer notes, and "
                "published outcomes drift into separate places and no one can explain why a case was accepted, "
                "rejected, or escalated."
            ),
            "customer": (
                "Review coordinators, assigned reviewers, and operations leads who must make decisions from "
                "submitted evidence while preserving the reason each decision was made."
            ),
            "opportunity": (
                "Turn one submitted case into a traceable review path before adding automation, bulk intake, "
                "or live external policy integrations."
            ),
            "product_view": (
                "The first release is useful when a coordinator can open one case, see what evidence arrived, "
                "route it to a reviewer, capture the review decision, and publish a final status with the "
                "supporting evidence still visible."
            ),
            "state_object": (
                "A review case moves from submitted to evidence captured, eligibility checked, reviewer "
                "decision recorded, escalation resolved, and final status published while preserving the "
                "source evidence and reviewer rationale."
            ),
            "first_path": (
                "A submitter opens one case, uploads evidence, the coordinator checks eligibility, a reviewer "
                "records a decision with a reason, the operations lead handles one escalation if needed, and "
                "the system publishes a final status with the supporting evidence visible."
            ),
            "proof_boundary": (
                "Release proof requires one case to be submitted, reviewed, decided, and published with the "
                "original evidence, policy check result, reviewer rationale, escalation outcome, final status, "
                "and non-goals visible to a reviewer."
            ),
            "success_metrics": [
                "One submitted case reaches a published final status with source evidence and reviewer rationale visible.",
                "One rejected or escalated case shows the blocking reason and preserves the evidence that caused it.",
                "Deferred automation and live integrations remain outside the release proof until separately accepted.",
            ],
            "human_actors": [
                "Submitter: provides source evidence and needs a clear final status.",
                "Reviewer: checks evidence, records the decision, and explains uncertainty.",
                "Operations lead: resolves escalations and decides whether the release proof is strong enough.",
            ],
            "external_systems": [
                "Email intake for submitted material.",
                "Document storage for source files.",
                "Policy reference material used during review.",
            ],
            "component_responsibilities": [
                "Case Intake Console: captures the submitted request, contact route, evidence references, and current intake status.",
                "Evidence Ledger: records evidence files, source owner, reviewer notes, decision reasons, and timestamped state changes.",
                "Review Queue: shows eligibility state, blocked cases, reviewer assignment, and escalation needs.",
                "Publication Record: publishes the final decision, caveats, and supporting evidence links for later review.",
            ],
            "assumptions": [
                "The first release proves one review path before broad automation.",
                "External policy sources remain references, not owned truth.",
            ],
            "material_ambiguities": [
                "Whether the first release needs one reviewer or two reviewers before publication.",
                "Whether submitters need a self-service status page or only a notification.",
            ],
            "non_goals": [
                "No automated final decisions in the first release.",
                "No live external policy synchronization until the first review path is proven.",
            ],
        },
        prompt="Draft a product-first greenfield proposal for an evidence review workspace.",
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for an evidence review workspace.",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    encoded = json.dumps(proposal)
    parent = proposal["backlog"][0]

    assert "Review decisions become unsafe" in parent["problem"]
    assert any("published final status" in metric for metric in parent["success_metrics"])
    assert "Case Intake Console" in encoded
    assert "Evidence Ledger" in encoded
    assert "component_responsibilities" not in proposal
    assert "host-written" not in encoded
    assert "schema repair" not in encoded.casefold()
    assert "proposal JSON repair" not in encoded
    assert "state record" not in encoded.casefold()
    assert "**" not in encoded
    for component in proposal["components"]:
        responsibility = str(component["responsibility"])
        assert len(responsibility.split()) >= 6
        assert "accepted first release path" not in responsibility
        assert "records review evidence" not in responsibility
    for diagram in proposal["diagrams"]:
        for component in diagram["components"]:
            description = str(component["description"])
            assert description.endswith(".")
            assert "accepted first release path" not in description
            assert "For the first release" not in description


def test_confirmed_intent_rejects_meta_scaffold_instead_of_product_story() -> None:
    bad_intent = """Community Archive — Product Intent Confirmation

Product story
Turn the community archive intent into a clear product narrative, first workflow, state object, and proof boundary before implementation begins. Release 0.0.1 narrows that promise to one first slice and keeps the project readable as one product story.

State object that changes through the first journey
A Community Archive state record stores the workflow result, owner, validation output, reviewer decision, and evidence packet so the release claim can be trusted later.

First complete path the product should prove before broader scope
Start with the community archive first workflow, then replay community archive record and review community archive evidence packet before source work starts.

Human actors
- Community Archive workflow lead and beneficiary — prove one journey from intake to visible completion.
- Community Archive proof lead — decides whether evidence is strong enough to trust the release claim.

Internal product systems
- Community Archive Workflow Service — owns the first workflow.
- Community Archive State Store — owns the state record.
- Community Archive Evidence Review — owns the evidence packet.

Proof boundary
The community archive first workflow passes end to end with fixture-backed inputs and documented non-goals, and every release claim maps to state, validation output, reviewer decision, and evidence packet.
"""

    with pytest.raises(ValueError, match="missing or too thin"):
        parse_confirmed_intent_text(bad_intent, prompt="Create a community archive")
