from __future__ import annotations

from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import component_spec_rendering


def test_component_register_entry_can_record_user_intent_candidates() -> None:
    entry = component_authoring._build_registry_entry(
        component_id="shop-payments",
        label="Payments Boundary",
        path="src/payments",
        kind="integration",
        category="application",
        qualification="candidate",
        owner="repo",
        status="planned",
        product_layer="application",
        sources=("user_intent",),
        workstreams=("B-200",),
        diagrams=("D-200",),
    )

    assert entry["category"] == "application"
    assert entry["owner"] == "repo"
    assert entry["status"] == "planned"
    assert entry["sources"] == ["user_intent"]
    assert entry["workstreams"] == ["B-200"]
    assert entry["diagrams"] == ["D-200"]
    assert entry["what_it_is"].startswith("Payments Boundary defines the planned integration ownership boundary")
    assert "responsible for" not in entry["what_it_is"]
    assert "initial evidence anchor" not in entry["what_it_is"]
    assert "user-stated intent" in entry["why_tracked"]
    assert "agent sessions" not in entry["why_tracked"]


def test_component_spec_template_does_not_claim_source_for_user_intent() -> None:
    text = component_spec_rendering.build_component_spec(
        component_id="research-solver",
        label="Solver Engine",
        path="src/solver",
        kind="library",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-200",),
    )

    assert "## Component Brief" not in text
    assert "## Boundary Narrative" not in text
    assert "## First Release Proof" not in text
    assert "Planned from user-stated intent" in text
    assert "Source boundary: src/solver" in text
    assert "[B-200](odylith/radar/radar.html?view=plan&workstream=B-200)" in text


def test_component_spec_template_uses_greenfield_responsibility_and_links() -> None:
    text = component_spec_rendering.build_component_spec(
        component_id="shop-checkout",
        label="Checkout Boundary",
        path="src/checkout",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-200", "B-201"),
        diagrams=("D-200",),
        responsibility="Payment handoff, order draft, idempotency, and recovery behavior.",
        boundary="Checkout owns payment handoff and order-draft recovery until source evidence narrows it.",
        dependencies=("Payment sandbox", "Order ledger"),
        interfaces=("Checkout request contract", "Payment callback contract"),
        validation=("Happy-path checkout smoke proof", "Payment failure recovery proof"),
        risks=("Provider-specific behavior may change the boundary",),
        implementation_handoff={
            "workstream_id": "B-201",
            "workstream_title": "Checkout first slice",
            "wave_label": "Checkout spine",
            "wave_status": "active",
            "release_selector": "0.0.1",
            "first_slice": "Implement browse-to-checkout with payment sandbox failure recovery.",
            "validation_gates": ["Checkout smoke proof passes", "Payment failure recovery proof passes"],
            "verification_commands": ["./.odylith/bin/odylith context --repo-root . B-201", "run npm test"],
        },
    )

    assert "payment handoff" in text
    assert "order draft" in text
    assert "Trace links: workstreams B-200, B-201, diagrams D-200" in text
    assert "## Component Brief" not in text
    assert "## Boundary Narrative" not in text
    assert "## First Release Proof" not in text
    assert "## Checkout Boundary Runtime Boundary" not in text
    assert "Checkout Boundary receives its trusted context from Payment sandbox and prepares work for Order ledger." in text
    assert "Payment failure recovery proof." in text
    assert "Provider-specific behavior may change the boundary." in text
    assert "[B-201](odylith/radar/radar.html?view=plan&workstream=B-201)" in text
    assert "Use B-201 (Checkout first slice) as the implementation anchor" in text
    assert "Release wave: Checkout spine." in text
    assert "Release target: 0.0.1." in text
    assert "Implement browse-to-checkout with payment sandbox failure recovery." in text


def test_component_spec_template_keeps_greenfield_contracts_concise() -> None:
    text = component_spec_rendering.build_component_spec(
        component_id="field-intake",
        label="Field Intake Service",
        path="src/field_intake",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-210",),
        responsibility="Records field intake with attribution, review state, and recovery outcome.",
        boundary=(
            "Field Intake owns the state and rules for recording field intake with attribution, review state, "
            "and recovery outcome. Presentation and downstream decisions stay outside."
        ),
        dependencies=(
            "Coordinates with Review Queue for reviewer assignment and recovery decisions.",
            "Intake must stay attributable, recoverable, and reviewable before downstream decisions use it.",
        ),
        interfaces=(
            "Command, query, or event contract for recording field intake; includes accepted input, produced state, "
            "failure state, and ownership handoff.",
        ),
        validation=("Contract proof covers accepted intake, rejected input, and reviewer-visible recovery state.",),
        implementation_handoff={
            "release_selector": "0.0.1",
            "first_slice": (
                "The first complete path is a controlled field review. "
                "The user records one intake, attaches evidence, and sees the review result."
            ),
            "project_outcome": (
                "Evidence should come from a realistic fixture showing successful intake, rejection, "
                "and reviewer-visible recovery."
            ),
            "verification_commands": ["run pytest"],
        },
    )

    assert "because The first" not in text
    assert "First proof must show Proof shows" not in text
    assert "Promotion requires Proof shows" not in text
    assert "| Contract proof covers" not in text
    assert "Depends on Design pressure" not in text
    assert "Depends on Intake must" not in text
    assert "Release 0.0.1 contribution:" not in text
    assert "Product context:" not in text
    assert "Project outcome:" not in text
    assert "Accepted intent says this component records field intake with attribution, review state, and recovery outcome." in text
    assert "field intake with attribution command" in text
    assert "Contract proof covers accepted intake, rejected input, and reviewer-visible recovery state." in text
    assert "Intake must stay attributable" in text
    assert "…" not in text
