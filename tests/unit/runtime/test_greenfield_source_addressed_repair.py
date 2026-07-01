from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionPackage,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_package_findings import (
    package_artifact_findings,
)
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues


def test_registry_package_finding_targets_component_contract_source_path() -> None:
    proposal = {
        "components": [
            {
                "component_id": "intake",
                "label": "Intake",
                "component_contract": {"produced_outputs": "accepted input"},
            },
            {
                "component_id": "review-workspace",
                "label": "Review Workspace",
                "component_contract": {"produced_outputs": "review result"},
            },
        ]
    }
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        component_registry_preview=({"component_id": "review-workspace"},),
        rendered_component_specs={
            "Review Workspace": (
                "# Review Workspace\n\n"
                "## Component Contract\n\n"
                "A reviewer can submits the final check."
            )
        },
    )

    findings = package_artifact_findings(package)

    finding = next(item for item in findings if "modal/base-form grammar drift" in item.message)
    target_path = "components[1].component_contract.produced_outputs"
    assert finding.code == "component_contract_quality"
    assert finding.target_path == target_path
    assert finding.semantic_node_id == f"ArtifactPlanIR.{target_path}"


def test_greenfield_quality_gate_ignores_internal_artifact_plan_patch_ledger() -> None:
    proposal = {
        "intent": {"prompt": "build a review workspace"},
        "artifact_plan_patch_ledger": [
            {
                "rejected_interpretation": "Registry component spec failed before rerender.",
                "applied_paths": ("components[0].component_contract.produced_outputs",),
            }
        ],
        "components": [],
        "backlog": [],
    }

    assert not [
        issue
        for issue in greenfield_quality_issues(proposal)
        if "control-plane term `Registry`" in issue
    ]
