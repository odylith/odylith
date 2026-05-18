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
    assert entry["what_it_is"].startswith("Payments Boundary is planned as an integration boundary")
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

    assert "| Status | `planned` |" in text
    assert "Planned from user-stated intent" in text
    assert "No source-backed claim is made yet" in text
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

    assert "Checkout owns payment handoff and order-draft recovery" in text
    assert "| Workstreams | `B-200`, `B-201` |" in text
    assert "| Diagrams | `D-200` |" in text
    assert "## Component Role" in text
    assert "## Runtime Boundary" in text
    assert "## Runtime Contract" in text
    assert "## Checkout Boundary Runtime Boundary" not in text
    assert "### Collaborators And Dependencies" in text
    assert "- Depends on Payment sandbox for state, behavior, evidence, or access this component does not own." in text
    assert "- Checkout request contract." in text
    assert "| Payment failure recovery proof |" in text
    assert "- Provider-specific behavior may change the boundary." in text
    assert "[B-201](odylith/radar/radar.html?view=plan&workstream=B-201)" in text
    assert "Use `B-201` (Checkout first slice) as the implementation-plan anchor" in text
    assert "- Wave: Checkout spine (active)." in text
    assert "- Release target: 0.0.1." in text
    assert "- First coding slice: Implement browse-to-checkout with payment sandbox failure recovery." in text
    assert "- Promotion requires source-backed evidence for: happy-path checkout smoke proof and Payment failure recovery proof; proposal text alone is not enough." in text
    assert "- `./.odylith/bin/odylith context --repo-root . B-201`" in text
    assert "- run npm test" in text


def test_component_spec_template_keeps_greenfield_contracts_concise() -> None:
    text = component_spec_rendering.build_component_spec(
        component_id="field-intake",
        label="Field Intake Service",
        path="src/field_intake",
        kind="service",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-210",),
        responsibility="Own field intake records for the accepted first release path.",
        boundary=(
            "Field Intake owns field intake records. Rationale: intake must stay attributable, "
            "recoverable, and reviewable before downstream decisions use it."
        ),
        dependencies=(
            "Depends on the accepted product direction for user, problem, first path, and proof boundary.",
            "Design pressure: intake must stay attributable, recoverable, and reviewable before downstream decisions use it.",
        ),
        interfaces=("Expose operations for field intake records needed by the accepted first path.",),
        validation=("Proof shows field intake records work inside the accepted first path, including success and recovery evidence.",),
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
    assert "| Proof shows field intake" not in text
    assert "Depends on Design pressure" not in text
    assert "Release 0.0.1 contribution: The first complete path is a controlled field review." in text
    assert "Required proof: field intake records work inside the accepted first path" in text
    assert "| Field intake records work inside the accepted first path" in text
    assert "- Design pressure: intake must stay attributable" in text
