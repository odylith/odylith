from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import MATERIAL_FACT_KEYS
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_intent_authority_from_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import prompt_only_material_decision_error
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_confirmation_choice_lines
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text


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


def _accepted_intent_with_authority(tmp_path: Path, *, prompt: str) -> dict[str, object]:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_VALID_EDITED_CONFIRMATION, encoding="utf-8")
    intent = parse_confirmed_intent_text(_VALID_EDITED_CONFIRMATION, prompt=prompt)
    envelope = build_product_intent_envelope(
        intent,
        source_text=_VALID_EDITED_CONFIRMATION,
        source_path=path,
        source_format="markdown",
    )
    structured_path = write_structured_confirmed_intent_file(path, intent, envelope=envelope)
    intent[PRODUCT_INTENT_AUTHORITY_KEY] = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=structured_path,
        markdown_source_path=path,
    )
    return intent


def test_confirmation_choice_block_highlights_exact_allowed_commands() -> None:
    transaction_hash = "a" * 64
    lines = format_confirmation_choice_lines(
        (
            (f"CONFIRM {transaction_hash}", "Commit the validated package."),
            (f"EDIT {transaction_hash} <corrections>", "Rebuild from the corrected evidence."),
            (f"REJECT {transaction_hash}", "Stop without writing records."),
        )
    )
    rendered = "\n".join(lines)

    assert rendered.startswith("## Choose one command")
    assert "For EDIT, replace `<corrections>` with your changes" in rendered
    assert "approval code binds your choice to this reviewed package" in rendered
    assert "### CONFIRM" in rendered
    assert "### EDIT" in rendered
    assert "### REJECT" in rendered
    assert rendered.count("```text") == 3
    assert f"CONFIRM {transaction_hash}" in rendered
    assert f"EDIT {transaction_hash} <corrections>" in rendered
    assert f"REJECT {transaction_hash}" in rendered
    assert "Command buttons" not in rendered
    assert "Copy-ready reply" not in rendered


def test_product_intent_preview_defers_the_only_command_rail_to_the_transaction() -> None:
    confirmation = build_product_intent_confirmation(
        prompt="Create a review workspace for field inspectors to record findings and publish approval packets.",
        title="Field Inspection Review Workspace",
        repo_name="field-inspection",
    )

    rendered = format_product_intent_confirmation_text(confirmation)

    assert "Product Intent Preview" in rendered
    assert "ProductCreateTransaction" not in rendered
    assert "### Command: `CONFIRM`" not in rendered
    assert "### Command: `EDIT`" not in rendered
    assert "### Command: `REJECT`" not in rendered
    assert confirmation["mode"] == "product_intent_preview_request"
    assert confirmation["write_policy"] == "precompile_transaction_before_confirm"
    commands = confirmation["commands"]
    assert "--intent-file" not in " ".join(str(value) for value in commands.values())
    assert "compile_transaction_after_intent_confirmation" not in commands
    assert "odylith greenfield propose" in commands["compile_transaction_from_prompt_evidence"]


def test_visible_confirmation_preserves_material_custody_when_proof_copy_has_no_final_period(
    tmp_path: Path,
) -> None:
    prompt = (
        "A city public works department needs to prioritize an emergency pavement repair after a bus route "
        "reports a deep pothole. The inspector documents the distress rating, the traffic engineer approves "
        "the lane closure, and the contractor records asphalt temperature during placement. Preserve the work "
        "zone permit, compaction test, pavement section, and reopening inspection; a citizen complaint does "
        "not establish that the repair meets specification."
    )
    confirmation = build_product_intent_confirmation(
        prompt=prompt,
        title="Approved Lane Closure Workspace",
        repo_name="pavement-repair",
    )
    rendered = format_product_intent_confirmation_text(confirmation)
    path = tmp_path / "confirmed-intent.md"
    path.write_text(rendered, encoding="utf-8")

    record = load_confirmed_intent_record(path, prompt=prompt)
    structured_path = write_structured_confirmed_intent_file(
        path,
        record.product_facts,
        envelope=record.envelope,
    )
    authority = product_intent_authority_from_envelope(
        record.envelope,
        structured_intent_path=structured_path,
        markdown_source_path=path,
    )

    require_product_intent_authority(authority)
    for key in MATERIAL_FACT_KEYS:
        field = authority["material_fields"][key]
        assert field["custody_state"] == "accepted_fact"
        assert field["source_span_ids"]
        assert field["product_claim_span_ids"]


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


def test_materiality_recovery_asks_one_focused_question() -> None:
    message = str(prompt_only_material_decision_error())

    assert message.count("?") == 1
    assert "who uses it" not in message
    assert "state changes" not in message


def test_confirmed_proposal_uses_edited_intent_not_stale_prompt_terms(tmp_path: Path) -> None:
    stale_prompt = (
        "Create an orthopedic implant fatigue-test measurement console with wear-cycle telemetry, "
        "implant crack propagation readings, and orthopedic approval evidence."
    )
    accepted_intent = _accepted_intent_with_authority(tmp_path, prompt=stale_prompt)

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
    assert "wear-cycle telemetry" not in rendered.casefold()
    assert "fatigue-test" not in rendered.casefold()
    assert "crack propagation" not in rendered.casefold()
