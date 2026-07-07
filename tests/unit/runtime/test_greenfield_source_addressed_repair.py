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


def test_greenfield_quality_gate_allows_source_grounded_control_plane_homonym_only_in_domain_context() -> None:
    accepted = {
        "intent": {
            "prompt": "Create a product for geologic atlas field mapping.",
            "title": "Geologic Atlas Field Mapping Workspace",
            "product_story": "Geologic Atlas Field Mapping Workspace helps field geologists review map evidence.",
            "first_path": "A field geologist manages a map sheet and preserves stratigraphy evidence.",
        },
        "components": [
            {
                "label": "Geologic Atlas Field Mapping Review Workspace",
                "description": "Keeps geologic atlas field mapping evidence reviewable.",
            }
        ],
    }
    leaked = {
        "intent": {
            "prompt": "Create a product for geologic atlas field mapping.",
            "title": "Geologic Atlas Field Mapping Workspace",
            "product_story": "The Atlas diagram shows the generated governance flow.",
            "first_path": "A field geologist manages a map sheet and preserves stratigraphy evidence.",
        },
        "components": [],
    }

    assert not [
        issue
        for issue in greenfield_quality_issues(accepted)
        if "control-plane term `Atlas`" in issue
    ]
    assert [
        issue
        for issue in greenfield_quality_issues(leaked)
        if "control-plane term `Atlas`" in issue
    ]


def test_greenfield_quality_gate_uses_confirmed_sections_for_atlas_review_homonym() -> None:
    workstream = "Keep Single Cell Perturbation Atlas Result Record Clear During Atlas Review"
    proposal = {
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "title": "Single Cell Perturbation Atlas Workspace",
            "product_story": "Single Cell Perturbation Atlas Workspace helps a computational biologist.",
            "state_object": "A single cell perturbation atlas result record tracks review status.",
            "first_path": "Computational biologist can turn a gene perturbation study into a review-ready record.",
            "internal_systems": [
                "Single Cell Perturbation Atlas Review Workspace presents current state and next action.",
            ],
        },
        "program": {
            "blueprint": {"child_workstreams": [workstream]},
            "waves": [{"workstream_titles": [workstream]}],
        },
        "release_plan": {"target_workstream_titles": [workstream]},
        "backlog": [{"title": workstream}],
    }

    issues = greenfield_quality_issues(proposal)

    assert not any("control-plane term `Atlas`" in issue for issue in issues)


def test_confirmed_homonym_context_still_rejects_ungrounded_atlas_surface_copy() -> None:
    proposal = {
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "title": "Geologic Atlas Field Mapping Workspace",
            "product_story": "Geologic Atlas Field Mapping Workspace helps field geologists review map evidence.",
            "state_object": "A geologic atlas field record tracks map evidence.",
            "first_path": "Field geologist reviews map evidence before publishing a warning status.",
            "internal_systems": [
                "Geologic Atlas Field Mapping Review Workspace presents map evidence.",
            ],
        },
        "backlog": [
            {
                "title": "Review Map Evidence",
                "product_view": "The Atlas diagram shows the generated governance flow.",
            }
        ],
    }

    issues = greenfield_quality_issues(proposal)

    assert any("control-plane term `Atlas`" in issue for issue in issues)


def test_confirmed_homonym_context_rejects_source_laundered_atlas_surface_copy() -> None:
    proposal = {
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "title": "Geologic Atlas Field Mapping Workspace",
            "product_story": "The Atlas diagram shows the generated governance flow.",
            "state_object": "A geologic atlas field record tracks map evidence.",
            "first_path": "Field geologist reviews map evidence before publishing a warning status.",
            "internal_systems": [
                "Geologic Atlas Field Mapping Review Workspace presents map evidence.",
            ],
        },
        "backlog": [
            {
                "title": "Review Map Evidence",
                "product_view": "The Atlas diagram shows the generated governance flow.",
            }
        ],
    }

    issues = greenfield_quality_issues(proposal)

    assert any("control-plane term `Atlas`" in issue for issue in issues)


def test_confirmed_homonym_context_rejects_source_laundered_odylith_atlas_copy() -> None:
    proposal = {
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "title": "Geologic Atlas Field Mapping Workspace",
            "product_story": "Odylith Atlas shows the generated governance flow.",
            "state_object": "A geologic atlas field record tracks map evidence.",
            "first_path": "Field geologist reviews map evidence before publishing a warning status.",
            "internal_systems": [
                "Geologic Atlas Field Mapping Review Workspace presents map evidence.",
            ],
        },
        "backlog": [
            {
                "title": "Review Map Evidence",
                "product_view": "Odylith Atlas shows the generated governance flow.",
            }
        ],
    }

    issues = greenfield_quality_issues(proposal)

    assert any("control-plane term `Atlas`" in issue for issue in issues)
