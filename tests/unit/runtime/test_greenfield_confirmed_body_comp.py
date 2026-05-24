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


BODY_COMPOSITION_INTENT = """Body Composition and Waist Reduction App

Product story

A consumer wellness app helps adults understand body composition changes and reduce abdominal fat risk markers through measurable habits, progress tracking, and safer guidance. It should not promise spot reduction. The product frames tummy fat reduction as waist measurement improvement driven by overall fat loss, strength training, nutrition, sleep, and consistency.

State object

The core product state is a user progress profile: baseline body metrics, waist and weight history, optional photos, goals, activity and nutrition habits, adherence signals, recommendations, check-ins, and privacy consent choices.

First complete path

A user signs up, completes a baseline assessment, records waist and body composition measurements, chooses a realistic goal, receives a first-week plan, logs daily habits, and gets a weekly progress review that adjusts guidance based on trend data rather than single-day changes.

Human actors

- Primary user trying to improve body composition and waist measurements
- Optional coach, dietitian, or trainer reviewing progress and guidance
- Support or safety reviewer handling risky inputs, complaints, and account issues
- Product operator managing content, privacy settings, and recommendation rules

External systems

- Apple Health, Google Fit, or wearable activity feeds
- Smart scale or body composition device integrations
- Nutrition and food database provider
- Push notification, email, and authentication services
- Payment provider if the app includes subscriptions or coaching

Internal product systems

- Onboarding and consent flow
- Measurement capture for weight, waist, photos, and body composition estimates
- Goal setting and plan generation
- Habit, activity, nutrition, and check-in tracking
- Progress analytics and trend explanations
- Safety guardrails for medical, eating disorder, pregnancy, underage, and extreme weight-loss cases
- Privacy, retention, export, and deletion controls

Critical assumptions

- The app is a wellness product, not a medical diagnosis or treatment tool.
- Guidance prioritizes sustainable fat loss and health markers over cosmetic promises.
- Tummy fat reduction is expressed as waist trend reduction, not targeted fat burning.
- Optional photos are sensitive data and require explicit consent, strong privacy controls, and easy deletion.
- The first release can work with manual measurement entry before advanced integrations.
- Recommendations must be conservative, explainable, and easy for users to ignore or adjust.

Ambiguities

- Whether body composition is estimated from manual inputs, photos, smart scales, or professional measurements.
- Whether the product is self-serve only or includes human coaching.
- Whether the target audience is general consumers, postpartum users, fitness users, or metabolic health users.
- Whether nutrition logging should be detailed calorie tracking or lower-friction habit tracking.
- Which jurisdictions and age groups the app will support.
- Whether the business model is subscription, paid coaching, device companion, or employer wellness.

Proof boundary

The first governed product slice should prove that a user can safely create a baseline, understand what is being measured, follow a first plan, and review progress without misleading claims. It should validate privacy handling, measurement clarity, recommendation guardrails, and a coherent first-week loop. It should not claim proven fat-loss efficacy until there is real outcome data.
"""


def test_confirmed_body_composition_intent_repairs_actor_and_system_labels() -> None:
    intent = parse_confirmed_intent_text(
        BODY_COMPOSITION_INTENT,
        prompt="Draft a product-first greenfield proposal for a body composition and tummy fat reduction app.",
    )

    encoded = json.dumps(intent)
    assert "Primary User" not in encoded
    assert "behavior for the accepted path" not in encoded
    assert "Relevant evidence" not in encoded
    assert "and downstream, and keeps" not in encoded
    assert "Evidence for this slice" not in encoded
    assert "Body Composition User" in encoded
    assert "Content Privacy Operator" in encoded
    assert "Measurement Capture For Weight, Waist, Photos, And —" not in encoded
    assert "Safety Guardrails For Medical, Eating Disorder, Pregnancy, —" not in encoded
    assert "Measurement Capture For Weight, Waist, Photos, And Body Composition Estimates" in encoded
    assert "Safety Guardrails For Medical, Eating Disorder, Pregnancy, Underage, And Extreme Weight-loss Cases" in encoded
    assert "without." not in encoded


def test_confirmed_body_composition_create_reaches_all_prewrite_gates(tmp_path) -> None:
    prompt = "Draft a product-first greenfield proposal for a body composition and tummy fat reduction app."
    intent = parse_confirmed_intent_text(BODY_COMPOSITION_INTENT, prompt=prompt)

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
    assert "Measurement Capture for Weight, Waist, Photos, and Service" not in encoded
    assert "Safety Guardrails for Medical, Eating Disorder, Pregnancy, Service" not in encoded
    assert "Measurement Capture for Weight, Waist, Photos, and Body Composition Estimates Service" in encoded
    assert "Safety Guardrails for Medical, Eating Disorder, Pregnancy, Underage, and Extreme Weight-loss Cases Service" in encoded
    measurement = next(row for row in proposal["components"] if row["component_id"].startswith("measurement-capture"))
    privacy = next(row for row in proposal["components"] if row["component_id"].startswith("privacy-retention"))
    assert measurement["kind"] == "service"
    assert "privacy preference" in privacy["component_contract"]["owned_state"].casefold()
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
