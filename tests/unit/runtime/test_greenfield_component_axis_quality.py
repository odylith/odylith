from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_axes import component_axis_key_for_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.governance.component_spec_rendering import build_component_spec


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
    assert "stops before a trusted result" in checklist_spec
    assert "A replay of Compliance Checklist Ledger still connects" in checklist_spec
