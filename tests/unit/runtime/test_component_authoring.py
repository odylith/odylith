from __future__ import annotations

from odylith.runtime.governance import component_authoring


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
    text = component_authoring._build_spec_template(
        component_id="research-solver",
        label="Solver Engine",
        path="src/solver",
        kind="library",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-200",),
    )

    assert "**Status**: planned" in text
    assert "planned from user-stated intent" in text
    assert "No source-backed claim is made yet" in text
    assert "(Plan: [B-200](odylith/radar/radar.html?view=plan&workstream=B-200))" in text
