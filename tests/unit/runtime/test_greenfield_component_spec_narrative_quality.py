from __future__ import annotations

from types import SimpleNamespace

from odylith.runtime.artifact_quality.greenfield_package_quality import (
    greenfield_rendered_package_quality_issues,
)
from odylith.runtime.governance.component_spec_narrative import build_narrative_component_spec


def test_evidence_component_specs_do_not_repeat_generic_opening_sentence() -> None:
    specs: dict[str, str] = {}
    for label in (
        "Object Provenance Workspace Intake Register Service",
        "Object Provenance Workspace Review Workspace",
        "Object Provenance Workspace Proof Ledger",
    ):
        specs[label] = build_narrative_component_spec(
            component_id=label.casefold().replace(" ", "-"),
            label=label,
            path=f"src/example/{label.casefold().replace(' ', '_')}",
            kind="service",
            status="planned",
            sources=("user_intent",),
            workstreams=("B-002",),
            diagrams=("D-002",),
            responsibility="keeps object provenance and related state tied to the result a reviewer needs to understand",
            component_contract={
                "owned_state": "object provenance and related state, evidence record, reviewer result, blocker state, and proof trail",
                "accepted_inputs": "object claim, provenance note, prior state, authorized actor, and validation context",
                "produced_outputs": "review result, evidence record, blocked-state detail, and next-step context",
                "states_or_transitions": "draft, submitted, reviewed, blocked, corrected, accepted, and ready-for-next-step",
                "outside_boundary": "upstream source truth and final release approval",
                "local_proof": [
                    f"Successful path evidence for {label}: evidence record, visible result, and reviewer explanation.",
                    f"Replay evidence for {label}: actor, input facts, status, explanation, and proof trail.",
                ],
                "upstream_truth": "Accepted input context",
                "downstream_consumers": "Release review",
                "unique_failure": f"{label} can mislead users if evidence record is missing or stale.",
            },
        )

    issues = greenfield_rendered_package_quality_issues(
        SimpleNamespace(
            proposal={},
            rendered_component_specs=specs,
        )
    )
    rendered = "\n".join(specs.values())

    assert "Its job is to keep" not in rendered
    assert "without making this component own the decision" in rendered
    assert "repeats a noncanonical sentence" not in "\n".join(issues)


def test_read_model_opening_uses_complete_public_copy() -> None:
    spec = build_narrative_component_spec(
        component_id="case-status-dashboard",
        label="Case Status Dashboard",
        path="src/example/case_status_dashboard",
        kind="surface",
        status="planned",
        sources=("user_intent",),
        workstreams=("B-002",),
        diagrams=("D-002",),
        responsibility="shows the accepted case status and review explanation",
        component_contract={
            "owned_state": "case status view and review explanation",
            "accepted_inputs": "accepted case state, authorized actor, and validation context",
            "produced_outputs": "current case status, reviewer explanation, and next-step context",
            "states_or_transitions": "submitted, reviewed, blocked, corrected, and completed",
            "outside_boundary": "case mutation and final release approval",
            "local_proof": [
                "Successful path evidence for Case Status Dashboard: current case status and reviewer explanation.",
                "Blocked input evidence for Case Status Dashboard: missing case state stops before a trusted result.",
                "Replay evidence for Case Status Dashboard: actor, case facts, status, explanation, and proof trail.",
            ],
            "upstream_truth": "Case State Store",
            "downstream_consumers": "Case reviewer",
            "unique_failure": "The dashboard can show stale case status or hide the review explanation.",
        },
    )

    assert "without taking ownership of those source records." in spec
    assert "source records it displays" not in spec
    assert not greenfield_rendered_package_quality_issues(
        SimpleNamespace(proposal={}, rendered_component_specs={"case-status-dashboard": spec})
    )
