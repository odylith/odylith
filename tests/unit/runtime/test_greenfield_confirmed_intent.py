from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    CONTRACT_KEYS,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import normalize_confirmed_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_first_path_source
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.governance import artifact_tribunal
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


ROOT = Path(__file__).resolve().parents[3]


def _max_word_overlap(values: list[str]) -> float:
    word_sets = [
        {
            word.strip(".,;:!?()[]{}").casefold()
            for word in value.split()
            if len(word.strip(".,;:!?()[]{}")) > 3
        }
        for value in values
    ]
    scores: list[float] = []
    for index, left in enumerate(word_sets):
        for right in word_sets[index + 1 :]:
            if left and right:
                scores.append(len(left & right) / min(len(left), len(right)))
    return max(scores or [0.0])


def test_confirmed_intent_prompt_wrapper_semantics_stay_in_prompt_source_owner() -> None:
    parser_source = (
        ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py"
    ).read_text(encoding="utf-8")
    prompt_source = (
        ROOT / "src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py"
    ).read_text(encoding="utf-8")

    assert "prompt_first_path_source" in parser_source
    assert "_REQUEST_COMMAND_WORDS" not in parser_source
    assert "def _strip_operator_request_wrapper" not in parser_source
    assert "def prompt_first_path_source" in prompt_source
    assert "def _strip_operator_request_wrapper" in prompt_source
    assert "import re" not in prompt_source
    assert "re." not in prompt_source


def test_confirmed_prompt_source_removes_command_wrapper_without_regex_rules() -> None:
    assert (
        prompt_first_path_source("Build a CRM for sales reps to qualify leads and managers to see pipeline health.")
        == "sales reps can qualify leads and managers can see pipeline health"
    )
    assert (
        prompt_first_path_source(
            "Draft a tool that helps clinics schedule intake, confirm insurance, and show patients next steps."
        )
        == "clinics schedule intake, confirm insurance, and show patients next steps"
    )


def test_confirmed_intent_parser_recovers_from_host_guidance_envelope_without_cli_leakage() -> None:
    prompt = (
        "Build a neighborhood tool where residents report broken streetlights, city staff triage duplicate reports, "
        "dispatch crews, and residents see repair status updates."
    )
    intent = parse_confirmed_intent_text(
        f"""Product Intent Confirmation needed
No files changed. Source posture: docs_only.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
- Render the visible confirmation as sectioned Markdown in this order.

Original user intent
{prompt}
Next step
- Confirm: if the interpretation is right, write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md, then run greenfield create with --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm.
- Edit: if the product story is wrong, ask for corrections.
- Reject: stop here.
Confirmed CLI after confirmation: odylith greenfield create --repo-root . --prompt '{prompt}' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1
""",
        prompt=prompt,
    )

    rendered = json.dumps(intent, sort_keys=True)
    assert "repo-root" not in rendered
    assert "Confirmed CLI" not in rendered
    assert "Visible format contract" not in rendered
    assert "to first," not in rendered
    assert "to residents report" not in rendered
    assert intent["title"] == "Repair Status Updates Workspace"
    assert "residents report broken streetlights" in intent["first_path"]
    assert "repair status updates" in intent["proof_boundary"].casefold()
    assert intent["internal_systems"]


def test_confirmed_intent_parser_removes_command_wrapper_from_recovered_first_path() -> None:
    prompt = "Build a CRM for sales reps to qualify leads and managers to see pipeline health."
    intent = parse_confirmed_intent_text(
        f"""Product Intent Confirmation needed

Visible format contract
- Render the visible confirmation as sectioned Markdown.

Original user intent
{prompt}
Next step
- Confirm the interpretation.
""",
        prompt=prompt,
    )

    rendered = json.dumps(intent, sort_keys=True)
    assert "Build a CRM" not in rendered
    assert "where Build" not in rendered
    assert "sales reps to qualify" not in rendered
    assert "sales reps can qualify leads" in rendered
    assert intent["title"] == "Pipeline Health Workspace"
    assert intent["first_path"].startswith("sales reps can qualify leads")


def test_confirmed_intent_completion_preserves_explicit_actor_and_system_rows() -> None:
    intent = parse_confirmed_intent_text(
        """Product Intent Confirmation

Cost Option Planner

Product story
A planner needs one narrow workspace to capture one request, compare a small set of options, show the selected option with ordered alternatives, and keep proof that the comparison used the accepted criteria.

State object
A planning request tracks actor identity, request answers, candidate options, comparison criteria, ranked options, selected option, ordered alternatives, explanation, blockers, and proof history.

First complete path
The planner enters one request, adds three candidate options, compares them against the accepted criteria, reviews the selected option and ordered alternatives, and confirms the explanation before the result is handed off.

Human actors
- Planner: enters the request, reviews the selected option, and confirms the explanation.

External systems
- Optional external option source is deferred until manual option entry works.

Internal product systems
- Option Ranking Engine: compares candidate options, applies accepted criteria, selects one option, orders alternatives, and records the explanation.
- Result Handoff Log: records the selected option, ordered alternatives, explanation approval, blocker state, and proof history.

Critical assumptions
- Manual option entry is enough for the first release.

Ambiguities
- Whether the first comparison uses one criterion or multiple weighted criteria.

Proof boundary
Release 0.0.1 succeeds when one planner can enter a request, compare three options, see a selected option with ordered alternatives, and inspect the explanation without claiming external option-source integration.
""",
        prompt="Draft a product-first greenfield proposal for a cost option planner.",
    )

    encoded = json.dumps(intent)
    assert intent["human_actors"] == [
        "Planner: enters the request, reviews the selected option, and confirms the explanation"
    ]
    assert len(intent["internal_systems"]) == 2
    assert str(intent["internal_systems"][0]).startswith(
        "Option Ranking Engine — compares candidate options, applies accepted criteria"
    )
    assert str(intent["internal_systems"][1]).startswith(
        "Result Handoff Log — records the selected option, ordered alternatives"
    )
    assert "operator" not in encoded.casefold()
    assert "reviewer" not in encoded.casefold()
    assert "dashboard" not in encoded.casefold()
    assert "case identity" not in encoded.casefold()
    assert "workspace status" not in encoded.casefold()


def test_confirmed_intent_parser_normalizes_terminal_loop_narration() -> None:
    intent = parse_confirmed_intent_text(
        """Practice Journal

Product story
A learner uses a short guided practice flow so an adult can review what happened without turning the result into a score.

State object
The product tracks a practice record with account owner, learner profile, scenario id, selected choice, reflection, recap status, and review boundary.

First complete path
A parent creates an account, adds a learner profile, and picks the first release band. The learner opens a scenario, makes a choice, sees a consequence and a short reflection, and finishes the moment. The parent later opens a simple recap. This is one full loop from setup to learner choice to adult review.

Human actors
- Learner, a child using the practice flow.
- Parent, the account owner who reviews the recap.

External systems
- Sign-in provider for the adult account.

Internal product systems
- Account service.
- Scenario service.
- Reflection service.
- Recap service.

Critical assumptions
- The adult owns the account and the learner does not self-register.

Ambiguities
- Whether narration is required for the first release.

Proof boundary
The first release succeeds when a parent can create an account and learner profile, the learner can complete one scenario with a selected choice and reflection, and the parent can open a recap.
""",
        prompt="Draft a practice journal",
    )

    assert "and finishes the moment" not in intent["first_path"]
    assert "one full loop" not in intent["first_path"]
    assert "The parent later opens a simple recap." in intent["first_path"]


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


def test_component_semantic_contract_preserves_accepted_component_facts() -> None:
    contract = derive_component_semantic_contract(
        {
            "label": "Decision Package Review",
            "source_system_description": "assembles evidence, reviewer notes, unresolved blockers, and final approval state",
        },
        proposal={},
        sibling={
            "label": "Revision Tracker",
            "source_system_description": "links applicant revisions to the documents and checks they are meant to address",
        },
        previous_label="Revision Tracker",
        next_label="Release Proof Review",
        state_label="Permit Review File",
    )

    encoded = json.dumps(contract.fields).casefold()
    for phrase in ("evidence", "reviewer notes", "unresolved blockers", "final approval state"):
        assert phrase in encoded
    assert "revision tracker ownership" in encoded
    assert "independent review decision" not in encoded
    assert contract.confidence >= 8


def test_component_semantic_contract_keeps_ledger_assessment_and_alert_axes_separate() -> None:
    decision = derive_component_semantic_contract(
        {
            "label": "Decision Ledger",
            "source_system_description": "records final decision, reviewer notes, recheck status, and final release decision",
        },
        proposal={},
        sibling=None,
        previous_label="Quality Review",
        next_label="Release Proof",
        state_label="Decision Record",
    )
    decision_text = json.dumps(decision.fields).casefold()
    assert "final decision" in decision_text
    assert "alert event" not in decision_text
    assert "alert lifecycle" not in decision_text
    assert "threshold signal" not in decision_text

    assessment = derive_component_semantic_contract(
        {
            "label": "Quality Assessment and Scoring",
            "source_system_description": (
                "records quality criteria, risk ratings, scoring inputs, rubric version, "
                "missing-field blockers, and assessment output"
            ),
        },
        proposal={},
        sibling=None,
        previous_label="Evidence Extraction",
        next_label="Decision Ledger",
        state_label="Decision Record",
    )
    assessment_text = json.dumps(assessment.fields).casefold()
    assert "scoring rubric" in assessment_text
    assert "score inputs" in assessment_text or "scoring inputs" in assessment_text
    assert "model input snapshot" not in assessment_text
    assert "derived state estimate" not in assessment_text

    alert = derive_component_semantic_contract(
        {
            "label": "Degradation Alert Ledger",
            "source_system_description": (
                "owns alert events, severity state, acknowledgement state, and alert resolution history"
            ),
        },
        proposal={},
        sibling=None,
        previous_label="State Model",
        next_label="Decision Workspace",
        state_label="Health Record",
    )
    alert_text = json.dumps(alert.fields).casefold()
    for phrase in ("alert event", "severity state", "acknowledgement state", "alert lifecycle"):
        assert phrase in alert_text


def test_confirmed_create_generates_component_specific_document_and_status_specs(tmp_path: Path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    intent = parse_confirmed_intent_text(
        """Request Handoff Workspace — Product Intent Confirmation

Product story
A source team needs one place to create a request packet, attach required context, send it to a destination team, and see whether the request is accepted, declined, scheduled, completed, or blocked. The first release proves that one request can move from draft to sent, received, accepted, declined, more-info-requested, scheduled, and completed without losing subject identity, required documentation, or status history.

State object
A request handoff record tracks subject identity, source team, destination team, handoff reason, urgency, required documentation, uploaded request context, matching decision, lifecycle status, next-action owner, notifications, stale or blocked markers, and audit history.

First complete path
A coordinator creates a draft request, attaches subject identity and required request context, validates uploaded documents, sends the packet to a destination team, sees received status, handles an accept, decline, or more-info request, schedules the request when accepted, and reviews the completed status history.

Human actors
- Source coordinator — creates the request packet, attaches subject identity and request context, and follows up on missing information.
- Destination coordinator — reviews request context, accepts, declines, or requests more information, and coordinates scheduling.
- Workspace administrator — audits status history and sensitive request-context access.

External systems
- Source record export for subject details and supporting documents.
- Scheduling system for appointment outcome.
- Notification provider for status freshness.

Internal product systems
- Recipient Matching Surface — helps the source coordinator choose a destination team before request send.
- Document and Context Handling Surface — creates request packets, attaches subject identity, captures handoff reason, validates uploaded documents, blocks missing required documentation, records request context provenance, protects sensitive request materials, and hands context into request lifecycle tracking.
- Request Lifecycle Tracking Service — records sent, received, accepted, declined, more-info-requested, scheduled, completed, blocked, and stale lifecycle events.
- Request Status View Service — renders the request status timeline, current next-action owner, role-appropriate status visibility, stale or blocked request indicators, notification-backed freshness, and audit history for both teams.

Critical assumptions
- Release 0.0.1 proves one request path before live source-system write-back or broad automation.
- Sensitive request materials require role-appropriate access control and audit history.

Ambiguities
- Which document types are mandatory for the first destination team?
- Whether scheduling starts as a manual status or a live scheduling integration.

Proof boundary
Release 0.0.1 succeeds when a request packet can be created with subject identity and required request context, missing documentation blocks submission, uploaded context stays attached to the correct request, unauthorized users cannot view or mutate request context, role-appropriate status is visible to both teams, stale or blocked requests are visible, invalid transitions are rejected or hidden, and status history is traceable to source events.
""",
        prompt="Draft a product-first greenfield proposal for a request handoff workspace.",
    )

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for a request handoff workspace.",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )

    encoded = json.dumps(proposal)
    assert "inspect The" not in encoded
    assert "Human actors:" not in encoded
    assert "plus 1 more" not in encoded
    assert "responsibility and keeps it tied" not in encoded
    for component in proposal["components"]:
        assert set(CONTRACT_KEYS) <= set(component["component_contract"])

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    specs = {
        row["label"]: Path(row["spec_path"]).read_text(encoding="utf-8")
        for row in result["components"]
    }
    assert rendered_component_spec_quality_issues(specs, project_title=proposal["intent"]["title"]) == []
    joined_specs = "\n".join(specs.values())
    assert "inspect The" not in joined_specs
    assert "Human actors:" not in joined_specs
    assert "plus 1 more" not in joined_specs
    assert "responsibility and keeps it tied" not in joined_specs

    document_spec = next(text for label, text in specs.items() if "Document and Context" in label)
    document_spec_lower = document_spec.casefold()
    for phrase in (
        "request packet creation",
        "subject identity attachment",
        "handoff reason capture",
        "required documentation completeness",
        "uploaded document validation",
        "missing document blocking",
        "request context provenance",
        "sensitive access control",
        "request lifecycle tracking",
        "Unauthorized users cannot view or mutate request context",
    ):
        assert phrase.casefold() in document_spec_lower
    assert "handoff into request lifecycle tracking" in document_spec_lower or "hands context into request lifecycle tracking" in document_spec_lower

    status_spec = next(text for label, text in specs.items() if "Request Status" in label)
    status_spec_lower = status_spec.casefold()
    for phrase in (
        "request status timeline",
        "next-action owner",
        "role-appropriate status visibility",
        "stale or blocked request indicators",
        "audit history",
    ):
        assert phrase.casefold() in status_spec_lower
    assert (
        "source event" in status_spec_lower
        or "source evidence" in status_spec_lower
        or "audit history" in status_spec_lower
    )
    for transition in ("sent", "received", "accepted", "declined", "scheduled", "completed"):
        assert transition in status_spec_lower
    assert "Define Recipient Matching Surface Boundary" not in status_spec


def test_confirmed_create_repairs_overlapping_structured_review_components(tmp_path: Path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """# Structured Review Workspace

Product story
A review operations team needs one workspace to assign reviewers, collect structured scores, compare decisions, and preserve audit history before a final approval decision. The first release proves one submission can move from assignment through scored review, dashboard comparison, decision, version history, and retention review without hiding permissions, scoring evidence, or audit obligations.

State object
A review decision record tracks submission identity, assigned reviewer, permission state, review form answers, scoring rubric version, score output, dashboard comparison state, decision readiness, final decision, audit trail, version history, retention rule, and replay evidence.

First complete path
A review manager assigns an eligible reviewer, grants the correct permission, the reviewer completes the structured form with required scoring fields, the dashboard compares the scored review against prior evidence, the manager records a decision, and the audit history preserves the versioned decision and retention state.

Human actors
- Review manager - assigns reviewers, grants permission, compares decisions, and records the final decision.
- Assigned reviewer - completes the structured review form and submits required scoring evidence.
- Audit reviewer - checks version history, retention state, and replay evidence before release.

External systems
- Submission intake export for incoming review items.
- Identity provider for reviewer role and permission attributes.
- Retention policy catalog for retention rule selection.

Internal product systems
- Review Assignment and Permission System - owns reviewer eligibility, assignment routing, access grants, conflict checks, and permission state before a reviewer can work.
- Structured Review Form and Scoring Templates - owns required review fields, scoring rubric versions, validation rules, scoring inputs, and score outputs.
- Decision Dashboard and Comparison View - owns current decision summary, comparison display, review readiness, visible blockers, and user-facing decision state.
- Audit Trail, Version History, and Retention Controls - owns immutable event history, version chain, retention policy state, audit reconstruction, change provenance, and replay evidence.

Critical assumptions
- Release 0.0.1 proves one structured review before broad workflow automation.
- Permission, scoring, decision comparison, and audit retention are separate product responsibilities.

Ambiguities
- Whether the first rubric has weighted scoring or pass/fail scoring.
- Whether retention starts as a manual policy choice or a live policy integration.

Proof boundary
Release 0.0.1 succeeds when reviewer assignment respects eligibility and permissions, missing scoring fields block submission, dashboard comparison shows current decision readiness without hiding blockers, audit history preserves the versioned decision and retention state, and replay evidence distinguishes assignment, scoring, dashboard, and audit responsibilities.
""",
        encoding="utf-8",
    )

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a product-first greenfield proposal for a structured review workspace.",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    assert "too similar" not in output
    assert "greenfield create wrote confirmed proposal" in output
    assert (tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json").is_file()
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").is_file()
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/atlas/source/catalog").glob("*.json"))
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    assert accepted["proposal"]["release_plan"]

    specs = {
        path.parent.name: path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")
    }
    assert rendered_component_spec_quality_issues(specs, project_title="Structured Review Workspace") == []
    joined_specs = "\n".join(specs.values())
    for banned in (
        "inspect The",
        "Human actors:",
        "plus 1 more",
        "responsibility and keeps it tied",
    ):
        assert banned not in joined_specs

    def spec_for(title: str) -> str:
        return next(text for text in specs.values() if text.splitlines()[0].startswith(f"# {title}"))

    assignment_spec = spec_for("Review Assignment and Permission System")
    form_spec = spec_for("Structured Review Form and Scoring Templates")
    dashboard_spec = spec_for("Decision Dashboard and Comparison View")
    audit_spec = spec_for("Audit Trail, Version History, and Retention Controls")
    for phrase in (
        "reviewer eligibility",
        "assignment routing",
        "access grants",
        "conflict checks",
        "permission state",
    ):
        assert phrase.casefold() in assignment_spec.casefold()
    assert "outside this boundary" in assignment_spec.casefold()
    assert "refused domain responsibilities:" not in assignment_spec.casefold()
    for phrase in ("review fields", "scoring rubric", "score output"):
        assert phrase.casefold() in form_spec.casefold()
    assert "outside this boundary" in form_spec.casefold()
    assert "refused domain responsibilities:" not in form_spec.casefold()
    for phrase in (
        "current decision summary",
        "comparison display",
        "review readiness",
        "visible blockers",
        "user-facing decision state",
    ):
        assert phrase.casefold() in dashboard_spec.casefold()
    assert "outside this boundary" in dashboard_spec.casefold()
    assert "refused domain responsibilities:" not in dashboard_spec.casefold()
    for phrase in (
        "immutable event history",
        "version chain",
        "retention policy state",
        "audit reconstruction",
        "change provenance",
        "replay evidence",
    ):
        assert phrase.casefold() in audit_spec.casefold()
    assert "outside this boundary" in audit_spec.casefold()
    assert "refused domain responsibilities:" not in audit_spec.casefold()


def test_confirmed_create_preserves_title_actors_and_domain_local_artifacts(tmp_path: Path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    intent = parse_confirmed_intent_text(
        """Civic Case Review Workbench — Product Intent Confirmation

Product story
A civic case workbench helps case board members review land-use cases before a public hearing. It brings the agenda item, parcel map, zoning and impact summaries, staff recommendation, public concerns, saved questions, vote rationale, and source traceability into one reviewable case so board members can prepare and explain decisions without losing the public record.

State object
A civic review case tracks agenda item identity, parcel and location context, zoning district, staff recommendation, impact summary, public comment themes, saved board member questions, hearing vote, rationale, source citations, and audit history.

First complete path
A case board member opens one agenda item, reviews the parcel map and zoning overlays, reads the staff recommendation and impact summary, groups public comments by concern, saves questions for staff, compares the recommendation to concerns, records a vote rationale at the hearing, and sees claim-source traceability for the public record.

Human actors
- Case board member: reviews agenda material, asks questions, records hearing rationale, and needs source-backed context before voting.
- Staff analyst: prepares staff recommendation, impact summary, map context, and responses to board member questions.
- Public participant or resident: submits comments or concerns that must remain visible and traceable.
- Compliance reviewer: checks whether decision rationale and public-record handling satisfy process constraints.

External systems
- Agenda management system supplies hearing items and staff reports.
- GIS or parcel map source supplies location, zoning overlays, and district boundaries.
- Public comment portal supplies resident concerns and attachments.

Internal product systems
- Case Review Workspace — organizes the agenda item, case status, review checklist, board member notes, and hearing-ready state.
- Map and Parcel Context Viewer — presents parcel geometry, zoning overlays, district boundaries, map layers, source freshness, and location constraints.
- Staff Recommendation and Impact Summary — records recommendation text, impact findings, supporting sources, conditions, and comparison points for the case.
- Public Comment Grouping — groups comments by concern, source, attachment, duplicate marker, visibility rule, and unresolved theme.
- Question and Issue Tracker — tracks board member questions, staff responses, open issues, answer status, follow-up owner, and unresolved blockers.
- Vote Rationale and Hearing Outcome Record — records motion, vote, rationale, conditions, abstentions, and final outcome.
- Audit Trail for Source-backed Claims — preserves claim-source lineage, citation history, version replay, access events, and public-record retention.

Critical assumptions
- Release 0.0.1 supports one agenda item review path before live hearing-scale workflow.
- Map and public comment sources can start from imported fixtures before live integrations.
- The product supports decision preparation and rationale capture; it does not automate legal approval or public hearing procedure.

Ambiguities
- Whether public comments need redaction before board member review.
- Whether map context is live GIS or a static exported layer in the first release.

Proof boundary
Release 0.0.1 succeeds when a board member can open one civic case, inspect map and zoning context, compare staff recommendation with public concerns, save questions, record vote rationale, and trace every material claim back to its source without exposing out-of-scope private or legal decision automation.
""",
        prompt="Draft a product-first greenfield proposal for a civic case workbench.",
    )

    assert intent["title"] == "Civic Case Review Workbench"
    assert len(intent["human_actors"]) == 4
    assert any(row.startswith("Compliance reviewer:") for row in intent["human_actors"])

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a product-first greenfield proposal for a civic case workbench.",
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    encoded = json.dumps(proposal)
    for banned in (
        "Additional accepted items remain",
        "supports the accepted path",
        "inputs and produced outputs",
        "scoring rubric",
    ):
        assert banned not in encoded
    assert proposal["intent"]["title"] == "Civic Case Review Workbench"
    assert not greenfield_quality_issues(proposal)

    sequence = next(row for row in proposal["diagrams"] if row["title"] == "First Path Sequence")["mermaid_source"]
    for phrase in ("parcel map", "public comments", "vote rationale", "claim-source"):
        assert phrase in sequence
    context = next(row for row in proposal["diagrams"] if row["title"] == "System Context View")["mermaid_source"]
    assert "Public comment portal" in context
    assert "component4" in context

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    specs = {
        row["label"]: Path(row["spec_path"]).read_text(encoding="utf-8")
        for row in result["components"]
    }
    assert rendered_component_spec_quality_issues(specs, project_title=proposal["intent"]["title"]) == []
    joined_specs = "\n".join(specs.values())
    for banned in ("supports the accepted path", "inputs and produced outputs", "scoring rubric"):
        assert banned not in joined_specs

    expected_spec_terms = {
        "Case Review Workspace": ("agenda item", "case status", "review checklist", "hearing-ready state"),
        "Map and Parcel Context Viewer": ("parcel geometry", "zoning overlays", "map layers", "source freshness"),
        "Staff Recommendation and Impact Summary": ("recommendation text", "impact findings", "comparison points", "supporting sources"),
        "Public Comment Grouping": ("concern", "source", "duplicate marker", "visibility rule"),
        "Question and Issue Tracker": ("board member questions", "staff responses", "answer status", "unresolved blockers"),
        "Vote Rationale and Hearing Outcome Record": ("motion", "vote", "rationale", "final outcome"),
        "Audit Trail for Source-backed Claims": ("claim-source lineage", "citation history", "version replay", "public-record retention"),
    }
    for label, phrases in expected_spec_terms.items():
        spec = next(text for spec_label, text in specs.items() if label in spec_label).casefold()
        for phrase in phrases:
            assert phrase.casefold() in spec

    radar_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/radar/source/ideas").glob("**/*.md")
    )
    for banned in ("inputs and produced outputs", "produced outputs input", "component boundary, diagram view, and release gate"):
        assert banned not in radar_text


def test_confirmed_create_self_repairs_multi_gate_evidence_review_shape(tmp_path: Path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(
        """# Structured Evidence Review Workspace

## Product Story

A review team needs one workspace to run a structured evidence review from question definition through final evidence package. The app helps them import source records, deduplicate candidates, define protocol rules, screen independently, resolve disagreements, extract evidence, assess quality, synthesize findings, and export a traceable review package.

The product is not just a document library. Its value is turning scattered review work into a repeatable process where every include, exclude, extraction, assessment, synthesis, and export decision can be traced to source evidence.

## State Object

The central state object is an Evidence Review Project. It tracks the review question, protocol version, eligibility criteria, imported records, deduplicated candidates, reviewer assignments, screening decisions, disagreement history, source documents, extracted fields, quality assessments, synthesis tables, export package, and audit evidence.

## First Complete Path

A review lead creates an Evidence Review Project, defines the question and eligibility criteria, imports source records, deduplicates candidates, assigns two independent reviewers, captures screening decisions, resolves one disagreement, moves included sources into evidence extraction, records quality assessment, builds a synthesis table, and exports a review package with source references and decision history.

## Human Actors

- Review lead: defines the review question, protocol, eligibility criteria, and final export readiness.
- Independent reviewer: screens assigned records and records include, exclude, or uncertain decisions.
- Method reviewer: checks evidence quality, synthesis readiness, and decision traceability.
- Compliance reviewer: audits access, export evidence, retention, and reproducibility.

## External Systems

- Literature, document, or source-record databases.
- CSV, RIS, BibTeX, DOI, or reference-manager imports.
- Identity provider for reviewer roles and access.
- Document storage for source files and attachments.
- Export targets for spreadsheet, document, CSV, and citation outputs.

## Internal Product Systems

- Source Record Import and Deduplication — imports source records, normalizes metadata, detects duplicates, rejects malformed rows, preserves provenance, and hands candidates into protocol-based review.
- Eligibility Criteria and Protocol Management — defines the review question, criteria, protocol version, inclusion rules, exclusion rules, rule exceptions, and rule-change history before downstream decisions use them.
- Review Assignment and Conflict Resolution — assigns eligible reviewers, grants appropriate access, detects conflicts, tracks assignment state, and blocks work when a reviewer cannot safely review an item.
- Independent Screening Workflow — captures separate reviewer decisions, include or exclude reasons, uncertainty, disagreement markers, resolution decision, and downstream handoff for included sources.
- Evidence Annotation and Extraction — links included sources to annotations, captures extracted fields, records source locations, validates missing evidence, and hands extracted evidence into assessment.
- Quality Assessment and Scoring — records quality criteria, risk ratings, scoring inputs, rubric version, missing-field blockers, and assessment output for each included source.
- Evidence Synthesis and Export Package — builds synthesis tables, assembles exportable outputs, checks completeness, keeps source references visible, and blocks export when required evidence is missing.
- Audit Trail and Retention Controls — records immutable event history, actor identity, version chain, retention policy state, replay evidence, and export audit reconstruction.

## Critical Assumptions

- Human reviewers remain responsible for review decisions.
- AI assistance, if added later, must stay optional, explainable, and separate from human judgment.
- Every decision needs source traceability for reproducibility.
- Release 0.0.1 starts with a small team and deterministic imports before live enterprise scale.
- Access, privacy, audit, retention, and reproducibility matter because review notes and source metadata may be sensitive.

## Ambiguities

- Whether the first import source is a file upload or a live database connection.
- Whether quality assessment starts with weighted scoring or simple categorical ratings.
- Whether export must support spreadsheet output first or document output first.
- Whether cross-organization collaborators are needed in release 0.0.1.

## Proof Boundary

Release 0.0.1 succeeds when one review team can create a project, import and deduplicate records, apply criteria, screen independently, resolve a disagreement, extract evidence, assess quality, build a synthesis table, and export a review package.

Success means the exported package explains which records were included or excluded, who made each decision, which evidence was extracted, what quality assessment was recorded, which source references support the synthesis, and which audit events prove the result.

## Next Step

- Confirm: accept this interpretation and create the governed greenfield records.
- Edit: tell me what to change in the product story, actors, systems, assumptions, first path, or proof boundary.
- Reject: stop here with no records written.
""",
        encoding="utf-8",
    )

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Draft a product-first greenfield proposal for a structured evidence review workspace.",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    for blocker in (
        "proof boundary needs",
        "validation-strategy item was clipped",
        "too similar",
        "need clearer separation",
    ):
        assert blocker not in output
    assert (tmp_path / ".odylith/runtime/greenfield/confirmed-intent.json").is_file()
    assert (tmp_path / "odylith/runtime/source/accepted-project.v1.json").is_file()
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/atlas/source/catalog").glob("*.json"))

    specs = {
        path.parent.name: path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")
    }
    assert rendered_component_spec_quality_issues(specs, project_title="Structured Evidence Review Workspace") == []
    joined_specs = "\n".join(specs.values())
    for banned in (
        "inspect The",
        "Human actors:",
        "plus 1 more",
        "responsibility and keeps it tied",
        "with clear ownership, protected access, required",
    ):
        assert banned not in joined_specs

    def spec_for(title: str) -> str:
        return next(text for text in specs.values() if title in text.splitlines()[0])

    criteria_spec = spec_for("Eligibility Criteria and Protocol Management")
    assignment_spec = spec_for("Review Assignment and Conflict Resolution")
    assert "eligibility criteria" in criteria_spec.casefold()
    assert "protocol version" in criteria_spec.casefold()
    assert "outside this boundary" in criteria_spec.casefold()
    assert "refused domain responsibilities:" not in criteria_spec.casefold()
    assert "eligible reviewers" in assignment_spec.casefold()
    assert "appropriate access" in assignment_spec.casefold()
    assert "outside this boundary" in assignment_spec.casefold()
    assert "refused domain responsibilities:" not in assignment_spec.casefold()
    assert "conflict" in assignment_spec.casefold()

    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in Path("src/odylith/runtime/domain_intelligence").glob("greenfield*.py")
    )
    assert "/Users/freedom/mock/research-review" not in source_text
    assert "Scientific Research Review App" not in source_text


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
	The product is a compact low-cost field water-quality monitor for community groups that need quick local screening before sending samples to a lab. It captures pH, turbidity, temperature, and conductivity readings, guides a novice operator through calibration, and produces a readable result that explains whether the sample is safe, uncertain, or needs lab review. The value is practical screening without turning the device into a professional laboratory instrument.

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


def test_confirmed_intent_parser_accepts_primary_actor_and_system_headings() -> None:
    intent = parse_confirmed_intent_text(
        """Protocol Deviation Review — Product Intent Confirmation

Product story
A lab coordinator needs one reliable place to record protocol deviations, link evidence, and show quality reviewers what changed and what remains unresolved.

State object that changes through the first journey
A Deviation Review Record contains protocol identity, deviation description, evidence attachments, severity classification, reviewer notes, corrective action status, and audit trail.

First complete path Odylith should prove before broader scope
The coordinator creates one deviation record, selects the protocol, describes the deviation, attaches evidence, classifies severity, submits for quality review, receives one requested correction, updates the record, and the reviewer sees a complete audit trail with unresolved blockers called out.

Primary actors
- Lab coordinator: records deviation details and corrections.
- Quality reviewer: reviews evidence, severity, and audit trail completeness.

Primary systems
- Deviation intake: owns protocol selection, deviation detail, and evidence status.
- Severity review: owns classification, rationale, and blocked-state explanation.
- Correction tracker: owns reviewer requests, coordinator responses, and unresolved blockers.
- Audit trail: preserves event history, evidence links, and reviewer-ready replay.

Proof boundary
Release 0.0.1 is trusted when one deviation record can move from intake through severity review, correction, and audit-trail review with replayable evidence and blocked-state explanations.
""",
        prompt="Build a lab protocol deviation tracker for internal quality review.",
    )

    assert intent["human_actors"] == [
        "Lab coordinator: records deviation details and corrections",
        "Quality reviewer: reviews evidence, severity, and audit trail completeness",
    ]
    assert len(intent["internal_systems"]) == 4
    assert intent["internal_systems"][0].startswith("Deviation Intake — owns protocol selection")
    assert not any(row.startswith("Reviewer:") for row in intent["human_actors"])


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
    assert systems[0].startswith("Device Pairing and Sync — owns device pairing and sync state")
    assert "responsibility and keeps it tied" not in systems[0]
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
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
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
    titles = [str(row["title"]) for row in accepted["proposal"]["backlog"]]
    assert titles == [
        "Prove One Complete Decision Review Workspace Path",
        "Let Coordinator Use the Final Status with Source Evidence",
        "Keep Decision Record Clear After Quality Review Changes It",
        "Show Why Decision Record Can Be Trusted",
    ]
    assert not any(title.startswith(("Build ", "Implement ", "Ship ")) for title in titles)
    assert "Useful for One Complete Outcome" not in encoded
    assert "Ship one complete outcome" not in encoded
    rows_by_title = {str(row["title"]): row for row in accepted["proposal"]["backlog"]}
    first_path_row = rows_by_title["Let Coordinator Use the Final Status with Source Evidence"]
    state_row = rows_by_title["Keep Decision Record Clear After Quality Review Changes It"]
    proof_row = rows_by_title["Show Why Decision Record Can Be Trusted"]

    assert "final status with source evidence" in first_path_row["problem"]
    assert "import one observation" in first_path_row["product_view"]
    assert "use the final status with source evidence" in first_path_row["product_view"]
    assert "quality evidence" in encoded
    assert "Decision Record" in state_row["product_view"]
    assert "actor, source, status" in " ".join(state_row["success_metrics"])
    assert "reviewer decision" in proof_row["product_view"]
    assert "automated approval" in " ".join(proof_row["success_metrics"])

    radar_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "odylith/radar/source/ideas").glob("**/*.md")
    )
    for banned in (
        "governed workstream",
        "component boundary, diagram view, and release gate",
        "Release records preserve",
        "Program handoff names",
        "Turn the accepted product intent into inspectable release records",
        "Do not derive product records",
    ):
        assert banned not in radar_text
    child_blobs = [
        " ".join(str(row.get(key, "")) for key in ("problem", "opportunity", "product_view", "recommended_first_slice"))
        for row in (first_path_row, state_row, proof_row)
    ]
    assert _max_word_overlap(child_blobs) < 0.60


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
        "Evidence Reviewer: checks evidence, records the decision, and explains uncertainty",
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
