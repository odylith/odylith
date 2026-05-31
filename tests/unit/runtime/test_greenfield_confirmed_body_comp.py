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
