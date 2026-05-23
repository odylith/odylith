from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.governance.component_spec_rendering import build_component_spec
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload


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


def _proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=GENERIC_DECISION_REVIEW_INTENT,
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(GENERIC_DECISION_REVIEW_INTENT),
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
    assert "follow-up request" in str(questions["owned_state"]).casefold()
    assert "unresolved blocker" in str(questions["owned_state"]).casefold()
    assert "score output" not in str(questions["owned_state"]).casefold()

    decision = _component_contract(proposal, "Decision Rationale")
    assert "decision rationale" in str(decision["owned_state"]).casefold()
    assert "final outcome" in str(decision["owned_state"]).casefold()

    audit = _component_contract(proposal, "Audit Trail")
    assert "immutable event history" in str(audit["owned_state"]).casefold()
    assert "replay evidence" in str(audit["owned_state"]).casefold()


def test_greenfield_atlas_uses_first_path_events_and_evidence_owner(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    diagrams = {str(row["title"]): str(row["mermaid_source"]) for row in proposal["diagrams"]}  # type: ignore[index]
    sequence = diagrams["First Path Sequence"]
    proof = diagrams["Release Proof Review"]
    boundary = diagrams["Component Boundary View"]

    assert "A1->>C1: A decision reviewer opens" in sequence
    assert "A1->>C2: Checks the context evidence" in sequence
    assert "A1->>C5: Compares recommendation with" in sequence
    assert "A1->>C4: Saves follow-up questions" in sequence
    assert "A1->>C6: Records rationale after the final" in sequence
    assert "A3->>C7: The record owner publishes" in sequence
    assert "Source-backed Audit Trail Adapter" in boundary
    assert "Source-backed Audit Trail Adapter proof record" in proof
    assert "Release 0.0.1 succeeds when a representative" not in proof
