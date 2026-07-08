from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines


_VALID_EDITED_CONFIRMATION = """# Lab Evidence Review Workspace - Product Intent Confirmation

## Product story
Research coordinators need one accountable workspace for turning dense lab submission notes into a reviewed evidence package without treating planning notes or implementation guidance as product truth. The product keeps intake, review, custody, and release-readiness decisions understandable before broader automation exists.

## State object
The lab evidence package records submitted sample context, reviewer notes, custody status, method constraints, evidence gaps, release-readiness status, and the reviewer decision that must stay visible across the evidence review path.

## First complete path
A research coordinator opens a new lab evidence package, records the submitted sample context, attaches method constraints, assigns a reviewer, resolves evidence gaps, saves custody status, and sees a release-readiness decision with the accepted proof trail.

## Human actors
- Research Coordinator: needs the product to record sample context, route review, resolve evidence gaps, and keep the accepted release-readiness decision visible.
- Evidence Reviewer: needs the product to review method constraints, add proof notes, and confirm the evidence package is ready or blocked.

## External systems
- Existing laboratory submission notes and sample tracking exports.

## Internal product systems
- Evidence Intake Workspace: receives lab submission details and keeps package state available for review.
- Custody Review Ledger: records reviewer decisions, evidence gaps, custody status, and proof trail changes.
- Release Readiness View: shows the accepted decision, blocked-path evidence, and visible proof summary.

## Critical assumptions
- Release 0.0.1 records evidence review and custody proof only.

## Ambiguities
- Live laboratory integrations can wait until the first package review path is proven.

## Proof boundary
Release 0.0.1 is proven only when the same lab evidence package can be opened, reviewed, updated with custody proof, and read back with the release-readiness decision and blocked evidence intact.
"""


def test_confirmation_choice_block_highlights_exact_allowed_commands() -> None:
    lines = format_confirmation_choice_lines(
        (
            ("CONFIRM", "Commit the validated package."),
            ("EDIT", "Rebuild from the corrected evidence."),
            ("REJECT", "Stop without writing records."),
        )
    )
    rendered = "\n".join(lines)

    assert rendered.index("**Allowed first words:** `CONFIRM` | `EDIT` | `REJECT`.") < rendered.index(
        "### Command: `CONFIRM`"
    )
    assert "**Start your reply with exactly one command:** `CONFIRM`, `EDIT`, or `REJECT`." in rendered
    assert "Do not write anything before the command." in rendered
    assert rendered.count("**Reply starts with:**") == 3
    assert rendered.count("**What happens:**") == 3
    assert "### Command: `CONFIRM`" in rendered
    assert "### Command: `EDIT`" in rendered
    assert "### Command: `REJECT`" in rendered


def test_file_backed_edited_confirmation_validation_failure_does_not_regenerate_from_prompt(tmp_path: Path) -> None:
    original_prompt = (
        "Create a municipal permit review workspace where permit clerks intake applications, "
        "validate zoning attachments, route reviewer decisions, and show applicants a clear approval packet."
    )
    path = tmp_path / "confirmed-intent.md"
    path.write_text(
        """# Edited Review Workspace - Product Intent Confirmation

## Product story
Turn the operator intent into a clear product narrative before implementation begins.

## State object
The product record tracks review status and evidence for one workflow.

## First complete path
The first workflow starts with intake, then review, then a visible result.

## Human actors
- Workflow lead: confirms the workflow.

## Internal product systems
- Workflow intake: receives work.
- Workflow review: reviews work.

## Proof boundary
The proof shows the workflow is visible before implementation begins.
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as exc:
        load_confirmed_intent_record(path, prompt=original_prompt)

    message = str(exc.value)
    assert "Odylith needs one material product decision" in message
    assert "municipal permit review workspace" not in message


def test_confirmed_proposal_uses_edited_intent_not_stale_prompt_terms(tmp_path: Path) -> None:
    stale_prompt = (
        "Create an orthopedic implant fatigue-test measurement console with wear-cycle telemetry, "
        "implant crack propagation readings, and orthopedic approval evidence."
    )
    accepted_intent = parse_confirmed_intent_text(_VALID_EDITED_CONFIRMATION, prompt=stale_prompt)

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=stale_prompt,
        release_selector="0.0.1",
        confirmed_intent=accepted_intent,
        require_completion_ready=False,
    )

    rendered = json.dumps(proposal, sort_keys=True)
    assert "Lab Evidence Review Workspace" in rendered
    assert "release-readiness decision" in rendered
    assert "orthopedic implant" not in rendered.casefold()
    assert "fatigue-test" not in rendered.casefold()
    assert "crack propagation" not in rendered.casefold()
