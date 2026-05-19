from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams


def _diagram_slugs() -> dict[str, str]:
    return {
        "context": "context",
        "sequence": "sequence",
        "state_evidence": "state-evidence",
        "component_boundaries": "component-boundaries",
        "ownership": "ownership",
        "proof_review": "proof-review",
    }


def test_atlas_component_cards_explain_specific_boundary_without_path_boilerplate() -> None:
    rows = confirmed_diagrams(
        label="Operations Platform",
        diagram_slugs=_diagram_slugs(),
        components=[
            {
                "component_id": "source-import",
                "label": "Source Import Adapter",
                "kind": "adapter",
                "responsibility": "External source import",
            },
            {
                "component_id": "decision-scoring",
                "label": "Decision Scoring Engine",
                "kind": "service",
                "responsibility": "Scores candidate decisions with confidence, inputs, and rule version.",
            },
            {
                "component_id": "state-ledger",
                "label": "State Ledger Service",
                "kind": "service",
                "responsibility": "Records versioned state changes, actor, timestamp, and source evidence.",
            },
            {
                "component_id": "exception-review",
                "label": "Exception Review Workflow",
                "kind": "service",
                "responsibility": "Coordinates exception review, handoff, blocked-state recovery, and final outcome.",
            },
            {
                "component_id": "user-review",
                "label": "User Review Surface",
                "kind": "client",
                "responsibility": "Review screen for user approval and correction.",
            },
            {
                "component_id": "assignment-planner",
                "label": "Assignment Planner",
                "kind": "service",
                "responsibility": "Assigns jobs to available resources while respecting priority, capacity, and constraints.",
            },
        ],
    )

    components = {row["name"]: row["description"] for row in rows[0]["components"]}
    encoded = json.dumps(rows)

    assert components["Source Import Adapter"] == (
        "Translates external source import inputs into product-owned records and preserves source provenance. "
        "Reviewers need to see which source supplied the input and what normalized result entered the product."
    )
    assert components["Decision Scoring Engine"] == (
        "Scores candidate decisions with confidence, inputs, and rule version. Reviewers need to see the inputs, "
        "rule version, result, and downstream decision that depended on it."
    )
    assert components["State Ledger Service"] == (
        "Records versioned state changes, actor, timestamp, and source evidence. Reviewers need to see the "
        "versioned state, source evidence, and decisions that depended on this record."
    )
    assert components["Exception Review Workflow"] == (
        "Coordinates exception review, handoff, blocked-state recovery, and final outcome. Reviewers need to see "
        "each responsibility transfer, failure state, recovery action, and final outcome."
    )
    assert components["User Review Surface"] == (
        "Presents review screen for user approval and correction to users and captures the action or decision the "
        "product needs next. Reviewers need to see what the user saw, submitted, corrected, or approved and which "
        "product state changed after that action."
    )
    assert components["Assignment Planner"] == (
        "Owns the product responsibility to assign jobs to available resources while respecting priority, capacity, "
        "and constraints. Reviewers need to see what this boundary receives, produces, records, and makes available next."
    )
    assert "accepted first release path" not in encoded
    assert "for the accepted first" not in encoded
    assert "Owns the responsibility to" not in encoded
    assert "hands off" not in encoded
    assert "part of the path" not in encoded
    assert "Design pressure" not in encoded
    assert "Domain evidence" not in encoded
    assert "**" not in encoded
    assert "`" not in encoded
