from __future__ import annotations

import json

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    component_spec_preflight_issues,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.governance.component_spec_rendering import build_component_spec


SERVICE_READINESS_INTENT = """# Service Readiness Review App

Product story

An operations app helps coordinators understand service readiness changes through measurable intake, progress tracking, and conservative guidance. It should not promise automatic operational approval. The product frames readiness improvement as capacity, availability, inspection evidence, and follow-through moving in a traceable direction.

State object

The core product state is a service readiness profile: baseline service metrics, capacity and availability history, optional attachments, goals, work habits, progress signals, recommendations, check-ins, and privacy consent choices.

First complete path

A coordinator signs up, completes a baseline assessment, records capacity and availability measurements, chooses a realistic goal, receives a first-week plan, logs daily work signals, and gets a weekly readiness review that adjusts guidance based on status data rather than single-day changes.

Human actors

- Primary coordinator trying to improve service readiness and capacity visibility
- Optional supervisor or reviewer checking progress and guidance
- Support or safety reviewer handling risky inputs, complaints, and account issues
- Product operator managing content, privacy settings, and recommendation rules

External systems

- Inventory, scheduling, or service activity feeds
- Attachment storage or inspection evidence providers
- Reference data provider
- Push notification, email, and authentication services
- Payment provider if the app includes subscriptions or support services

Internal product systems

- Onboarding and consent flow
- Measurement capture for capacity, availability, attachments, and readiness estimates
- Goal setting and plan generation
- Habit, activity, status, and check-in tracking
- Progress analytics and status explanations
- Policy guardrails for approval limits, escalation, restricted actions, evidence gaps, and high-risk cases
- Privacy, retention, export, and deletion controls

Critical assumptions

- The app is an operations planning product, not an automatic approval system.
- Guidance prioritizes traceable readiness and reviewable evidence over unsupported promises.
- Readiness improvement is expressed as status movement, not hidden automatic scoring.
- Optional attachments are sensitive data and require explicit consent, strong privacy controls, and easy deletion.
- The first release can work with manual measurement entry before advanced integrations.
- Recommendations must be conservative, explainable, and easy for users to ignore or adjust.

Ambiguities

- Whether readiness is estimated from manual inputs, attachments, provider feeds, or reviewer measurements.
- Whether the product is self-serve only or includes human review.
- Whether the target audience is internal coordinators, supervisors, vendor teams, or customer support.
- Whether activity logging should be detailed task tracking or lower-friction status tracking.
- Which jurisdictions and access groups the app will support.
- Whether the business model is subscription, paid support, provider companion, or internal operations.

Proof boundary

The first governed product slice should prove that a coordinator can safely create a baseline, understand what is being measured, follow a first plan, and review progress without misleading claims. It should validate privacy handling, measurement clarity, recommendation guardrails, and a coherent first-week loop. It should not claim automatic readiness approval until there is real outcome data.
"""


PEPTIDE_TRACK_INTENT = """# PeptideTrack — Personal Peptide Protocol & Outcome Tracker

Product story

You are running peptide protocols and want one place that turns "what am I taking, how much, and is it working" into a clear, evidence-grounded answer. PeptideTrack holds your peptide regimen, explains each peptide in plain terms, suggests dosage ranges informed by your lab reports and stated conditions, and then closes the loop by correlating your logged usage against body composition changes over time so you can see whether a protocol is actually moving the metrics you care about.

State object

The core unit is a Protocol: a peptide plus its dosing schedule, the lab and condition context that justified it, the usage log against that schedule, and the body composition readings collected while it ran. A user's account is a timeline of these protocols, each progressing from planned, to active, to evaluated against outcomes.

First complete path

A user adds a peptide, enters or imports recent lab values and relevant conditions, and receives a suggested dosage range with an explanation and explicit safety caveats. They log each dose as they take it, periodically record body composition readings, and after enough data the app shows whether the tracked metrics trended with usage for that protocol.

Human actors

- The individual user running and logging their own peptide protocols
- A coach or clinician the user may share a protocol or outcome summary with (read-oriented)

External systems

- Lab report sources (manual entry first; PDF or portal import later)
- Body composition data sources such as DEXA, InBody, or smart-scale exports
- A peptide reference knowledge source for descriptions and typical dosage ranges

Internal product systems

- Peptide reference catalog (descriptions, mechanisms, typical ranges, cautions)
- Lab and condition profile store
- Dosage suggestion engine that combines reference ranges with the user's labs and conditions
- Usage logging and schedule adherence tracking
- Body composition timeline and outcome correlation view

Critical assumptions

- This is a personal tracking and education tool, not a medical device, and it must surface that dosing output is informational and not a prescription.
- The user is willing to enter lab values and body composition readings manually for the first version.
- A curated peptide reference set covers the user's peptides well enough to be useful at launch.
- Single-user, private data is the starting scope; sharing is a later layer.

Ambiguities

- Regulatory and safety posture: how strongly to gate or disclaimer dosage suggestions, and whether to cap them to reference ranges only.
- Data sourcing: how much to invest now in automated lab/body-comp import versus manual entry first.
- Outcome model: simple trend visualization versus a stronger statistical correlation between usage adherence and composition change.
- Scope of the peptide catalog at launch, including which peptides and where their reference data comes from.

Proof boundary

The product is proven when a user can add a peptide, get a lab- and condition-aware dosage suggestion with its rationale and caveats, log usage against a schedule, record body composition readings, and see a clear view of whether the tracked metrics moved with usage for that protocol.
"""


def test_confirmed_service_readiness_intent_repairs_actor_and_system_labels() -> None:
    intent = parse_confirmed_intent_text(
        SERVICE_READINESS_INTENT,
        prompt="Draft a product-first greenfield proposal for a service readiness review app.",
    )

    encoded = json.dumps(intent)
    assert "Primary User" not in encoded
    assert "behavior for the accepted path" not in encoded
    assert "Relevant evidence" not in encoded
    assert "and downstream, and keeps" not in encoded
    assert "Evidence for this slice" not in encoded
    assert "readiness and capacity visibility coordinator" in encoded.casefold()
    assert "Supervisor or Reviewer Checking Progress" not in encoded
    assert "Content Privacy Operator" in encoded
    assert "Measurement Capture For Capacity, Availability, Attachments, And —" not in encoded
    assert "Policy Guardrails For Approval Limits, Escalation, Restricted Actions, —" not in encoded
    assert "measurement capture for capacity, availability, attachments, and readiness estimates" in encoded.casefold()
    assert (
        "policy guardrails for approval limits, escalation, restricted actions, evidence gaps, and high-risk cases"
        in encoded.casefold()
    )
    assert "without." not in encoded


def test_confirmed_service_readiness_create_reaches_all_prewrite_gates(tmp_path) -> None:
    prompt = "Draft a product-first greenfield proposal for a service readiness review app."
    intent = parse_confirmed_intent_text(SERVICE_READINESS_INTENT, prompt=prompt)

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )

    encoded = json.dumps(proposal)
    assert "Primary User" not in encoded
    assert "behavior for the accepted path" not in encoded
    assert "Relevant evidence" not in encoded
    assert "Measurement Capture for Capacity, Availability, Attachments, and Service" not in encoded
    assert "Policy Guardrails for Approval Limits, Escalation, Restricted Actions, Service" not in encoded
    assert "Measurement Capture for Capacity, Availability, Attachments, and Readiness Estimates Service" in encoded
    assert "Policy Guardrails for Approval Limits, Escalation, Restricted Actions, Evidence Gaps, and High-risk Cases Service" in encoded
    measurement = next(row for row in proposal["components"] if row["component_id"].startswith("measurement-capture"))
    privacy = next(row for row in proposal["components"] if row["component_id"].startswith("privacy-retention"))
    assert measurement["kind"] == "service"
    assert "privacy" in privacy["component_contract"]["owned_state"].casefold()
    assert "deletion controls" in privacy["component_contract"]["owned_state"].casefold()
    proof_row = proposal["backlog"][-1]
    assert "Privacy, Retention, Export, and Deletion Controls Proof Record" in proof_row["recommended_first_slice"]
    assert "Onboarding and Consent Flow Proof Record" not in proof_row["recommended_first_slice"]
    assert "without." not in encoded
    assert greenfield_quality_issues(proposal) == []
    assert component_spec_preflight_issues(proposal) == []
    rendered_specs = "\n".join(_rendered_component_specs(proposal))
    assert "by accepting." not in rendered_specs
    assert "Evidence for this slice" not in rendered_specs
    assert "Relevant evidence" not in rendered_specs

    decision = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    assert decision.passed
    assert all(row["visible_actor"] != "Primary User" for row in decision.visible_actors)
    assert all(row["visible_actor"] != "Evidence for this slice" for row in decision.visible_actors)


def test_confirmed_body_composition_tracker_removes_generated_text_residue(tmp_path) -> None:
    prompt = "Draft a product-first greenfield proposal for a peptide usage tracker."
    intent = parse_confirmed_intent_text(PEPTIDE_TRACK_INTENT, prompt=prompt)

    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
    )

    encoded = json.dumps(proposal)
    forbidden = (
        "tracked metrics trended",
        "tracked metrics moved with",
        "reach the tracked metrics changed with usage for that protocol",
        "review the tracked metrics changed with usage for that protocol",
        "use the tracked metrics changed with usage for that protocol",
        "shown while the tracked metrics changed with usage for that protocol",
        "reach usage-linked metric change",
        "review usage-linked metric change",
        "use usage-linked metric change",
        "shown while usage-linked metric change",
        "from the usage-linked",
        "using the usage-linked",
        "The Individual User Running",
        "This stays narrow so the team can prove the promised user outcome",
        "Anything not needed for this reviewed behavior waits until the first outcome is proven",
        "service boundary for combines",
        "service boundary for evaluates",
        "for each the accepted state change",
        "Keep Keep",
        "And Condition Profile Store can create false confidence",
        "And Outcome Correlation View can create false confidence",
        "Security posture: And Condition Profile Store",
        "Security posture: And Outcome Correlation View",
        "owns presents",
        "descriptions mechanism",
        "mechanism typical",
        "value relevant condition",
        "metric moved usage protocol",
        "metric changed usage protocol",
        "body composition data such",
        "data such dexa",
        "Combines reference ranges",
        "and iginal input facts",
        "; without it.",
    )
    for phrase in forbidden:
        assert phrase not in encoded
    assert "PeptideTrack Personal Peptide" not in encoded
    assert "Peptide Reference Catalog (descriptions" not in encoded
    assert "Individual User" in encoded
    assert "the usage-linked metric change view for that protocol" in encoded
    assert greenfield_quality_issues(proposal) == []
    assert component_spec_preflight_issues(proposal) == []
    rendered_specs = "\n".join(_rendered_component_specs(proposal))
    rendered_forbidden = (
        "is the place where the product turns prepared evidence into an explained outcome",
        "user adds peptide is calculated",
        "user adds peptide on a successful path",
        "user adds peptide is missing",
        "user adds peptide reviewable",
        "Accepted input context",
        "while keeping",
    )
    for phrase in rendered_forbidden:
        assert phrase not in rendered_specs

    decision = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    assert decision.passed


def _rendered_component_specs(proposal: dict[str, object]) -> list[str]:
    rendered: list[str] = []
    for component in proposal["components"]:  # type: ignore[index]
        row = dict(component)
        rendered.append(
            build_component_spec(
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
                implementation_handoff=row.get("implementation_handoff")
                if isinstance(row.get("implementation_handoff"), dict)
                else None,
                component_contract=row.get("component_contract") if isinstance(row.get("component_contract"), dict) else None,
            )
        )
    return rendered
