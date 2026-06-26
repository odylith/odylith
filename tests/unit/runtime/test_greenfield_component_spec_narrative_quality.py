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
