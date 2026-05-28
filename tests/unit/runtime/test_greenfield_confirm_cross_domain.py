from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo


_SLOP_PHRASES = (
    "working title",
    "owns maintains",
    "first path entry",
    "proof-token",
    "access grant or denial",
    "recorded daily log",
    "case identity",
    "workspace status",
    "checklist progress",
)

_SOURCE_DOMAIN_LEAK_TERMS = (
    "biomarker",
    "calorie",
    "checkout",
    "clinician",
    "ecommerce",
    "fare",
    "grant decision",
    "home repair",
    "longevity",
    "medication",
    "municipal permit",
    "pain",
    "plant sensor",
    "protocol outcome",
    "stomach fat",
    "symptom",
    "transport",
)


_INTENT_FIXTURES = (
    pytest.param(
        "protocol-outcome",
        """# Protocol Outcome Notebook

Product story
A self-directed researcher needs one notebook that connects protocol setup, intervention records, measurements, and outcome review without implying scientific certainty.

State object
A tracked protocol record carries intervention entries, timing, amount-as-recorded, baseline measurement, follow-up measurement, source note, outcome review status, and blockers.

First complete path
A researcher creates a protocol, records an intervention with timing and amount, adds a baseline measurement, later adds a follow-up measurement, and sees one outcome review that keeps the evidence aligned.

Human actors
- Self-directed researcher: creates protocols, records interventions, and reviews outcome evidence.
- Study collaborator: checks source notes, blockers, and outcome review status.

External systems
- User-supplied spreadsheet for measurement imports.
- Source document folder for reference notes.

Internal product systems
- Protocol Builder - owns protocol setup, measurement intent, and required-source blockers.
- Intervention Log - records timing, amount-as-recorded, schedule context, and intervention evidence.
- Measurement Store - records baseline and follow-up measurements, source notes, and validation blockers.
- Outcome Review Surface - aligns protocol, intervention, measurements, blockers, and outcome review status.

Critical assumptions
- Release 0.0.1 records user-entered facts and does not claim causal or medical correctness.
- The first release uses local fixtures before any live measurement integration.

Ambiguities
- Which measurement formats should be supported first.
- Whether collaborators can edit or only review.

Proof boundary
Release 0.0.1 succeeds when one protocol, intervention record, baseline measurement, follow-up measurement, and outcome review can be replayed with source notes and visible blockers for missing evidence.
""",
        ("protocol", "intervention", "baseline measurement", "follow-up measurement", "outcome review"),
        ("fare option", "symptom episode", "service address", "application packet"),
        id="protocol-outcome",
    ),
    pytest.param(
        "symptom-relief",
        """# Symptom Relief Journal

Product story
A person managing recurring symptoms needs a journal that captures an episode, what they tried for relief, and how the episode changed over time without giving diagnosis or dosing advice.

State object
A symptom episode record tracks intensity, body area, trigger note, relief action, medication-as-recorded note, side-effect note, timeline event, edit history, and safety disclaimer acknowledgement.

First complete path
A person records one symptom episode, adds intensity and body area, notes a trigger, records a relief action, views the event on a timeline, edits the entry, and sees the corrected timeline state.

Human actors
- Symptom journal owner: records episodes, relief actions, edits, and timeline review.
- Care partner: reviews shared episode context and safety notes when invited.

External systems
- Optional exported notes supplied by the user.

Internal product systems
- Episode Capture - owns symptom episode fields, required-entry blockers, and edit history.
- Relief Action Ledger - records relief actions, medication-as-recorded notes, side effects, and non-advice boundaries.
- Timeline View - shows episode events, edits, blockers, and corrected state.
- Safety Notice Boundary - keeps diagnosis, dosing, emergency escalation, and caregiver sharing boundaries visible.

Critical assumptions
- Release 0.0.1 is a tracking product, not a clinical decision product.
- Medication notes are recorded exactly as supplied by the user and never recommended by the product.

Ambiguities
- Whether invited care partners can comment or only view.

Proof boundary
Release 0.0.1 succeeds when one user can record, view, edit, and replay a symptom episode with relief action, safety notice, and timeline evidence intact.
""",
        ("symptom episode", "body area", "relief action", "timeline", "safety notice"),
        ("fare option", "baseline measurement", "service address", "application packet"),
        id="symptom-relief",
    ),
    pytest.param(
        "fare-choice",
        """# Fare Choice Assistant

Product story
A trip planner needs a compact assistant that compares travel options for a specific trip and preserves why the cheapest or preferred option was selected.

State object
A trip comparison record tracks origin, destination, departure time, fare option, travel time, constraint, ranked result, selected option, decision note, and stale-quote blocker.

First complete path
A planner enters origin, destination, and departure time, imports available fare options, compares price and travel time, selects one option, and saves the decision note with stale-quote blockers visible.

Human actors
- Trip planner: enters trip details, compares options, and selects the preferred route.
- Budget approver: reviews fare evidence, selected option, and stale-quote blockers.

External systems
- Transit fare feed for fixture fare options.
- Rideshare quote export supplied by the user.

Internal product systems
- Trip Intake - owns origin, destination, departure time, required-field blockers, and trip identity.
- Fare Option Collector - records fare options, travel time, source timestamp, and stale-quote blockers.
- Comparison Ranker - orders options by price, timing, constraints, and selected option rationale.
- Decision Note View - preserves selected option, decision note, evidence, and handoff status.

Critical assumptions
- Release 0.0.1 uses fixture fare data before live provider integrations.
- Cheapest option is not automatically final when user constraints say otherwise.

Ambiguities
- Which fare sources must be trusted first.

Proof boundary
Release 0.0.1 succeeds when one trip can move from entered route details to ranked fare options, selected option, saved rationale, and visible stale-quote evidence.
""",
        ("origin", "destination", "fare option", "selected option", "stale-quote"),
        ("symptom episode", "baseline measurement", "service address", "application packet"),
        id="fare-choice",
    ),
    pytest.param(
        "service-visit",
        """# Home Repair Visit Planner

Product story
A home repair team needs one planner that turns a service request into a scheduled visit with readiness evidence, quote context, and visible blockers.

State object
A service visit record tracks requester contact, service address, issue description, visit window, technician assignment, quote estimate, readiness checklist, blocker reason, and confirmation status.

First complete path
A requester submits an issue, the coordinator verifies service address and issue details, selects a visit window, assigns a technician, creates a quote estimate, and confirms the scheduled visit with readiness blockers visible.

Human actors
- Homeowner requester: submits the issue, service address, and preferred visit window.
- Service coordinator: verifies details, schedules the visit, and confirms readiness.
- Technician lead: reviews assignment, quote estimate, and blocker reason before the visit.

External systems
- Calendar availability export for visit windows.
- Parts catalog fixture for quote estimate inputs.

Internal product systems
- Service Request Intake - owns requester contact, service address, issue details, and missing-detail blockers.
- Visit Scheduler - owns visit windows, technician assignment, schedule conflicts, and confirmation status.
- Quote Estimate Builder - records quote estimate inputs, parts context, and review blockers.
- Readiness Review View - shows readiness checklist, blocker reason, assignment, and scheduled visit handoff.

Critical assumptions
- Release 0.0.1 uses fixture availability and parts data before live integrations.
- Quote estimates are planning context, not a binding contract.

Ambiguities
- Whether requesters can reschedule directly in the first release.

Proof boundary
Release 0.0.1 succeeds when one service request can be verified, scheduled, assigned, estimated, confirmed, and reviewed with readiness evidence and blockers intact.
""",
        ("service address", "visit window", "technician", "quote estimate", "readiness"),
        ("fare option", "symptom episode", "baseline measurement", "application packet"),
        id="service-visit",
    ),
    pytest.param(
        "decision-review",
        """# Grant Decision Review Desk

Product story
A funding program needs a review desk that keeps application evidence, eligibility checks, scoring, rationale, and published outcome together.

State object
A grant decision record tracks application packet, applicant identity, eligibility rule version, score entry, reviewer rationale, conflict marker, approval status, outcome notice, and appeal blocker.

First complete path
A program officer opens an application packet, checks eligibility rules, records score entries, adds rationale, resolves or marks conflicts, approves or blocks the decision, and publishes an outcome notice with evidence attached.

Human actors
- Program officer: reviews packets, eligibility, scores, rationale, and outcome status.
- Applicant representative: receives the outcome notice and appeal blocker context.
- Appeal assessor: checks conflicts, rationale, and evidence when a decision is disputed.

External systems
- Application intake export for packet fixtures.
- Eligibility policy document for rule references.

Internal product systems
- Packet Intake - owns application packet identity, applicant identity, and missing-packet blockers.
- Eligibility Rule Check - records rule version, eligibility result, conflict marker, and blocked decision state.
- Scoring Ledger - records score entries, rationale, reviewer evidence, and disputed-score blockers.
- Outcome Publication View - publishes approval or blocked outcome, notice state, appeal blocker, and evidence handoff.

Critical assumptions
- Release 0.0.1 uses fixture packets and policy documents before live applicant portals.
- Published outcomes must not hide unresolved conflicts or missing rationale.

Ambiguities
- Whether appeals are recorded in release 0.0.1 or deferred.

Proof boundary
Release 0.0.1 succeeds when one application packet can be checked, scored, justified, approved or blocked, and published with rule version, rationale, conflict state, and evidence visible.
""",
        ("application packet", "eligibility", "score", "rationale", "outcome notice"),
        ("fare option", "symptom episode", "baseline measurement", "service address"),
        id="decision-review",
    ),
)


@pytest.mark.parametrize(("name", "intent_text", "expected_terms", "forbidden_terms"), _INTENT_FIXTURES)
def test_greenfield_create_confirm_completes_cross_domain_projects(
    tmp_path,
    monkeypatch,
    capsys,
    name: str,
    intent_text: str,
    expected_terms: tuple[str, ...],
    forbidden_terms: tuple[str, ...],
) -> None:
    _seed_empty_governance_repo(tmp_path)
    intent_path = tmp_path / ".odylith/runtime/greenfield/confirmed-intent.md"
    intent_path.parent.mkdir(parents=True, exist_ok=True)
    intent_path.write_text(intent_text, encoding="utf-8")
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            f"Create {name}",
            "--intent-file",
            ".odylith/runtime/greenfield/confirmed-intent.md",
            "--confirm",
            "--release",
            "0.0.1",
        ]
    )

    output = capsys.readouterr().out
    assert rc == 0, output
    assert "- validation gate: passed" in output
    accepted = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    registry = json.loads((tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8"))
    compass_events = (tmp_path / "odylith/compass/runtime/agent-stream.v1.jsonl").read_text(encoding="utf-8").splitlines()
    release_events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8").splitlines()
    assert accepted["validation_gate"]["status"] == "passed"
    assert isinstance(accepted["proposal"]["semantic_model"], dict)
    assert len(list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))) >= 4
    assert len(registry["components"]) >= 3
    assert len(list((tmp_path / "odylith/atlas/source").glob("*.mmd"))) >= 4
    assert release_events
    assert compass_events and json.loads(compass_events[-1])["kind"] == "decision"
    rendered = _rendered_greenfield_text(tmp_path)
    for expected in expected_terms:
        assert expected in rendered
    for banned in (*_SLOP_PHRASES, *forbidden_terms):
        assert banned not in rendered


def _rendered_greenfield_text(root) -> str:
    suffixes = {".md", ".json", ".jsonl", ".mmd"}
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in root.rglob("*")
        if path.is_file() and path.suffix in suffixes
    ).casefold()


def test_greenfield_generator_source_does_not_bake_fixture_domain_terms() -> None:
    root = Path(__file__).resolve().parents[3]
    source_roots = [
        root / "src/odylith/runtime/domain_intelligence",
        root / "src/odylith/runtime/project_intelligence",
    ]
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for source_root in source_roots
        for path in source_root.rglob("*.py")
    ).casefold()

    leaked = [term for term in _SOURCE_DOMAIN_LEAK_TERMS if term in source_text]

    assert leaked == []
