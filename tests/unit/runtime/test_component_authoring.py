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
    assert "user-stated intent" in entry["why_tracked"]


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
    assert "- Payment sandbox." in text
    assert "- Checkout request contract." in text
    assert "- Payment failure recovery proof." in text
    assert "- Provider-specific behavior may change the boundary." in text
    assert "[B-201](odylith/radar/radar.html?view=plan&workstream=B-201)" in text
    assert "Use `B-201` (Checkout first slice) as the implementation-plan anchor" in text
    assert "- Wave: Checkout spine (active)." in text
    assert "- Release target: 0.0.1." in text
    assert "- First coding slice: Implement browse-to-checkout with payment sandbox failure recovery." in text
    assert "- Checkout smoke proof passes." in text
    assert "- `./.odylith/bin/odylith context --repo-root . B-201`" in text
    assert "- run npm test" in text
