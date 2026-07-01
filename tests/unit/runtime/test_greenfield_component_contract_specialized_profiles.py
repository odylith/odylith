from __future__ import annotations

from types import SimpleNamespace

from odylith.runtime.artifact_quality.greenfield_package_quality import (
    greenfield_rendered_package_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    ensure_component_contract,
)
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec


def test_specialized_component_profiles_preserve_component_local_failure_custody() -> None:
    rows = (
        _component_row(
            label="Attachment Intake Service",
            unique_failure="Attachment Intake Service can mislead users if intake evidence is missing or stale.",
        ),
        _component_row(
            label="Attachment Review Workspace",
            unique_failure="Attachment Review Workspace can mislead users if review rationale is missing or stale.",
        ),
        _component_row(
            label="Attachment Proof Ledger",
            unique_failure="Attachment Proof Ledger can mislead users if proof history is missing or stale.",
        ),
    )
    specs: dict[str, str] = {}

    for index, row in enumerate(rows):
        contract = ensure_component_contract(
            row,
            proposal={"title": "Attachment Review", "state_object": "Review Record"},
            previous_label=str(rows[index - 1]["label"]) if index else "",
            next_label=str(rows[index + 1]["label"]) if index + 1 < len(rows) else "",
            workstream_title="Review evidence flow",
        )
        specs[str(row["label"])] = build_narrative_component_spec(
            component_id=str(row["component_id"]),
            label=str(row["label"]),
            path=f"src/example/{row['component_id']}",
            kind="service",
            status="planned",
            sources=("user_intent",),
            workstreams=("B-001",),
            diagrams=("D-001",),
            responsibility=str(row["responsibility"]),
            component_contract=contract,
        )

    rendered = "\n".join(specs.values())
    issues = greenfield_rendered_package_quality_issues(
        SimpleNamespace(proposal={}, rendered_component_specs=specs)
    )
    failure_lines = [
        line.strip()
        for line in rendered.splitlines()
        if "The product failure to guard against:" in line
    ]

    assert "attached to the wrong review record" not in rendered.casefold()
    assert len(failure_lines) == 3
    assert len(set(failure_lines)) == 3
    assert all(label in rendered for label in ("Attachment Intake Service", "Attachment Review Workspace", "Attachment Proof Ledger"))
    assert "repeats noncanonical prose" not in "\n".join(issues)


def _component_row(*, label: str, unique_failure: str) -> dict[str, object]:
    slug = label.casefold().replace(" ", "-")
    return {
        "component_id": slug,
        "label": label,
        "kind": "service",
        "source_system_description": (
            f"owns {label.casefold()} attachment context, required evidence, blocked-state detail, "
            "and handoff proof for the confirmed first path"
        ),
        "responsibility": "keeps attachment context reviewable with missing-input recovery evidence",
        "component_contract": {
            "owned_state": f"{label} attachment context, required evidence, blocker state, and proof trail",
            "accepted_inputs": "source actor, required evidence, prior state, and validation context",
            "produced_outputs": "reviewable state, blocked-state detail, reviewer explanation, and next-step context",
            "states_or_transitions": "draft, submitted, reviewed, blocked, corrected, accepted, and ready-for-next-step",
            "outside_boundary": "upstream source truth and final release approval",
            "local_proof": [
                f"Successful path evidence for {label}: local evidence, visible result, and reviewer explanation.",
                f"Blocked input evidence for {label}: invalid input, no misleading result, and recovery explanation.",
                f"Replay evidence for {label}: actor, input facts, status, and proof trail.",
            ],
            "upstream_truth": "Accepted input context",
            "downstream_consumers": "Release review",
            "unique_failure": unique_failure,
        },
    }
