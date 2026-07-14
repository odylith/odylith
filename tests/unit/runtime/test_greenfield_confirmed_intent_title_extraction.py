from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_intent_authority_from_envelope
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues

ROOT = Path(__file__).resolve().parents[3]


def _with_authority(intent: dict[str, object], source_text: str) -> dict[str, object]:
    path = ROOT / ".odylith/runtime/greenfield/confirmed-intent.md"
    envelope = build_product_intent_envelope(
        intent,
        source_text=source_text,
        source_path=path,
        source_format="markdown",
    )
    intent[PRODUCT_INTENT_AUTHORITY_KEY] = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=path.with_suffix(".json"),
        markdown_source_path=path,
    )
    return intent


def test_confirmed_intent_parser_does_not_promote_next_step_confirm_bullet_to_title() -> None:
    prompt = (
        "Create a greenfield project for a municipal permit intake and review workspace. "
        "Residents submit permit requests with property details, staff triage completeness, "
        "reviewers coordinate comments, and supervisors track service-level commitments through approval or revision."
    )
    source_text = """# Municipal Permit Intake and Review Workspace

## Product story
Residents need a clear way to submit permit requests with property details, and municipal staff need a shared workspace to triage completeness, coordinate review comments, and keep service commitments visible. The first release should make the permit case state explicit from intake through approval or revision.

## State object
A permit case that includes applicant details, property information, completeness status, review comments, service-level dates, approval state, and revision history.

## First complete path
A resident submits a permit request, intake staff check completeness, reviewers add comments, a supervisor monitors service-level risk, and the case closes with approval or a revision request.

## Human actors
- Resident applicant
- Intake staff member
- Permit reviewer
- Supervising manager

## External systems
- Property reference source for parcel or address details
- Existing staff identity provider for municipal users

## Internal product systems
- Permit intake workspace
- Completeness triage queue
- Review coordination board
- Service-level tracking and case closure records

## Critical assumptions
- The first release manages request workflow and decision records, not payment collection or statutory rule automation.
- Staff can manually verify property details when an external source is unavailable.

## Ambiguities
- Exact permit categories and jurisdiction-specific review rules need confirmation before implementation.
- Notification channels can be chosen later without changing the first case workflow.

## Proof boundary
Prove that a submitted permit case can move through triage, review, supervisor tracking, and final approval or revision with durable state and traceable decisions.

## Next step
- Confirm: create the governed project records from this accepted Product Intent Confirmation.
- Edit: revise the product story, actors, systems, assumptions, first path, or proof boundary before creating records.
- Reject: stop without writing governed records.
"""
    intent = _with_authority(parse_confirmed_intent_text(source_text, prompt=prompt), source_text)
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=ROOT,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Municipal Permit Intake and Review Workspace"
    assert "Confirm: create the governed project records" not in rendered
    assert "confirm-create-the-governed-project-records" not in rendered
    assert "permit intake workspace" in rendered.casefold()
    assert greenfield_quality_issues(proposal) == []


def test_confirmed_intent_parser_does_not_promote_choose_one_actions_to_title() -> None:
    prompt = "Create a greenfield project for a municipal permit intake and review workspace."
    source_text = """# Municipal Permit Intake and Review Workspace

## Product story
Residents need a clear way to submit permit requests, and municipal staff need a shared workspace to review them.

## State object
A permit case records applicant details, property information, status, blockers, review comments, and decision history.

## First complete path
A resident submits a permit request, staff review it, and the case closes with an approval or revision request.

## Human actors
- Resident applicant
- Permit staff reviewer

## Internal product systems
- Permit intake workspace
- Permit review board

## Proof boundary
Prove that one submitted permit case can move through review and final decision with durable state.

## Choose one command

**Start your reply with exactly one command:** `CONFIRM`, `EDIT`, or `REJECT`.
Only the first command counts. Do not paste Odylith system commands in your reply.

### Command: `CONFIRM`
**Reply starts with:** `CONFIRM`

Accept this interpretation.

### Command: `EDIT`
**Reply starts with:** `EDIT`

Reply with corrections.

### Command: `REJECT`
**Reply starts with:** `REJECT`

Stop here.
"""
    intent = _with_authority(parse_confirmed_intent_text(source_text, prompt=prompt), source_text)
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=ROOT,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered_intent = json.dumps(proposal["intent"], sort_keys=True)
    rendered_commands = json.dumps(proposal["apply_commands"], sort_keys=True)

    assert intent["title"] == "Municipal Permit Intake and Review Workspace"
    assert "CONFIRM" not in rendered_intent
    assert "Municipal Permit Intake and Review Workspace" in rendered_intent
    assert "CONFIRM" in rendered_commands
