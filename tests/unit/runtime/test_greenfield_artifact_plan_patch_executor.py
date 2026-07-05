from __future__ import annotations

from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_post_confirm_patch_apply
from odylith.runtime.domain_intelligence.greenfield_artifact_plan_patch_executor import (
    apply_artifact_plan_patch_operations,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import (
    GreenfieldCompletionReport,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    GreenfieldPostConfirmRepairContext,
)


def test_artifact_plan_patch_updates_only_sanctioned_projection_fields() -> None:
    proposal: dict[str, Any] = {
        "project_brief": {
            "schema_version": "odylith.greenfield.project_brief.v1",
            "project_outcome": "Old outcome.",
        },
        "backlog": [
            {
                "workstream_id": "B-001",
                "title": "Review case record",
                "success_metrics": ["Old metric."],
            }
        ],
        "components": [
            {
                "component_id": "case-ledger",
                "label": "Case Ledger",
                "responsibility": "Old responsibility.",
            }
        ],
        "diagrams": [
            {
                "slug": "case-flow",
                "title": "Case Flow",
                "summary": "Old summary.",
            }
        ],
        "release_plan": {"strategy": "Old strategy."},
        "validation_strategy": ["Old validation."],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-101",
            "target_layer": "artifact_plan",
            "target_path": "project_brief.project_outcome",
            "semantic_node_id": "ArtifactPlanIR.project_brief",
            "issue_code": "artifact_shape_drift",
            "rejected_interpretation": "project brief lacked the approved release proof.",
            "confidence": 0.91,
            "replacement_fact": {
                "project_brief": {
                    "schema_version": "must-not-change",
                    "project_outcome": "Release 0.0.1 proves the accepted case record path with review evidence.",
                },
                "backlog": [
                    {
                        "match": {"title": "Review case record"},
                        "fields": {
                            "workstream_id": "B-999",
                            "success_metrics": ["Reviewer can inspect the case record with evidence."],
                        },
                    }
                ],
                "components": [
                    {
                        "match": {"component_id": "case-ledger"},
                        "fields": {
                            "component_id": "changed",
                            "responsibility": "Owns case record state and review evidence.",
                        },
                    }
                ],
                "diagrams": [
                    {
                        "index": 0,
                        "fields": {
                            "slug": "changed",
                            "summary": "Shows the accepted case record handoff and evidence boundary.",
                        },
                    }
                ],
                "release_plan": {"strategy": "Promote only after case record proof passes."},
                "validation_strategy": ["Validate the case record proof before release."],
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is True
    assert proposal["project_brief"]["schema_version"] == "odylith.greenfield.project_brief.v1"
    assert "accepted case record path" in proposal["project_brief"]["project_outcome"]
    assert proposal["backlog"][0]["workstream_id"] == "B-001"
    assert proposal["backlog"][0]["success_metrics"] == ["Reviewer can inspect the case record with evidence."]
    assert proposal["components"][0]["component_id"] == "case-ledger"
    assert proposal["components"][0]["responsibility"] == "Owns case record state and review evidence."
    assert proposal["diagrams"][0]["slug"] == "case-flow"
    assert proposal["diagrams"][0]["summary"] == "Shows the accepted case record handoff and evidence boundary."
    assert proposal["release_plan"]["strategy"] == "Promote only after case record proof passes."
    assert proposal["validation_strategy"] == ["Validate the case record proof before release."]
    ledger = proposal["artifact_plan_patch_ledger"]
    assert ledger[0]["operation_id"] == "GF-PATCH-101"
    assert "project_brief.project_outcome" in ledger[0]["applied_paths"]
    assert "components[0].responsibility" in ledger[0]["applied_paths"]


def test_artifact_plan_patch_refuses_untargeted_row_mutation() -> None:
    proposal: dict[str, Any] = {
        "backlog": [
            {
                "workstream_id": "B-001",
                "title": "Review case record",
                "success_metrics": ["Old metric."],
            }
        ],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-AMBIGUOUS",
            "target_layer": "artifact_plan",
            "semantic_node_id": "ArtifactPlanIR.backlog",
            "replacement_fact": {
                "backlog": [
                    {
                        "fields": {
                            "success_metrics": ["Reviewer can inspect the corrected proof."],
                        },
                    }
                ],
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is False
    assert proposal["backlog"][0]["success_metrics"] == ["Old metric."]
    assert "artifact_plan_patch_ledger" not in proposal


def test_compact_registry_component_patch_updates_matched_component_contract() -> None:
    proposal: dict[str, Any] = {
        "components": [
            {
                "component_id": "assay-intake",
                "label": "Assay Intake",
                "responsibility": "Accepts assay files and metadata.",
                "component_contract": {
                    "owned_state": "assay intake state",
                    "accepted_inputs": "assay files, metadata, authorized actor, validation context",
                    "produced_outputs": "validated assay package, blocked-state detail, reviewer explanation, next-step context",
                    "states_or_transitions": "assay received, assay validated, blocked, ready-for-next-step",
                    "outside_boundary": "adjacent component state owned elsewhere",
                    "local_proof": ["Successful path evidence for Assay Intake: assay package, required inputs, visible result, and reviewer explanation."],
                    "upstream_truth": "No claimed upstream dependency.",
                    "downstream_consumers": "Review Workspace.",
                    "unique_failure": "Assay Intake can mislead users if assay intake state is missing.",
                },
            },
            {
                "component_id": "review-workspace",
                "label": "Review Workspace",
                "responsibility": "Shows reviewed results, quality flags, confidence, and downloadable evidence.",
                "component_contract": {
                    "owned_state": "quality flags, reviewed results, downloadable evidence, result review",
                    "accepted_inputs": "reviewed results, downloadable evidence, result review input, authorized actor, validation context",
                    "produced_outputs": "quality flags, downloadable evidence, result review evidence, state update",
                    "states_or_transitions": "downloadable evidence received, requested, received, flagged, reviewed",
                    "outside_boundary": "adjacent component state owned elsewhere",
                    "local_proof": [
                        "Successful path evidence for Review Workspace: result review, required inputs, visible result, and reviewer explanation."
                    ],
                    "upstream_truth": "Upstream Model Service ownership.",
                    "downstream_consumers": "Evaluation and Proof Ledger.",
                    "unique_failure": "Review Workspace can mislead users if result review is missing.",
                },
            },
        ],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-REGISTRY",
            "target_layer": "artifact_plan",
            "target_path": "prewrite_package.registry",
            "semantic_node_id": "ArtifactPlanIR.registry",
            "issue_code": "component_contract_quality",
            "operation_kind": "artifact_plan_projection",
            "repair_owner": "registry_renderer",
            "projection_kind": "registry",
            "affected_projections": ["registry"],
            "replacement_fact": {
                "review-workspace": "review outputs with quality flags, confidence, and downloadable evidence",
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is True
    component = proposal["components"][1]
    assert component["responsibility"] == "review outputs with quality flags, confidence, and downloadable evidence"
    assert component["component_id"] == "review-workspace"
    assert component["component_contract"]["produced_outputs"] == (
        "review outputs with quality flags, confidence, and downloadable evidence, "
        "blocked-state detail, reviewer explanation, next-step context, and handoff context"
    )
    assert component["component_contract"]["owned_state"].startswith("quality flags")
    ledger = proposal["artifact_plan_patch_ledger"][0]
    assert ledger["operation_id"] == "GF-PATCH-REGISTRY"
    assert "components[1].responsibility" in ledger["applied_paths"]
    assert "components[1].component_contract.produced_outputs" in ledger["applied_paths"]


def test_compact_registry_component_patch_refuses_unknown_row_key() -> None:
    proposal: dict[str, Any] = {
        "components": [
            {
                "component_id": "known-component",
                "label": "Known Component",
                "responsibility": "Keeps known component state reviewable.",
                "component_contract": {"produced_outputs": "known component output"},
            }
        ],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-UNKNOWN",
            "target_layer": "artifact_plan",
            "target_path": "prewrite_package.registry",
            "semantic_node_id": "ArtifactPlanIR.registry",
            "projection_kind": "registry",
            "affected_projections": ["registry"],
            "replacement_fact": {
                "unknown-component": "replace a row that does not exist",
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is False
    assert proposal["components"][0]["responsibility"] == "Keeps known component state reviewable."
    assert proposal["components"][0]["component_contract"]["produced_outputs"] == "known component output"
    assert "artifact_plan_patch_ledger" not in proposal


def test_path_value_patch_updates_assumption_rows_without_losing_row_shape() -> None:
    proposal: dict[str, Any] = {
        "assumptions": [
            {
                "id": "ASM-001",
                "tier": "user_intent",
                "statement": "The first release records evidence only.",
                "confirm_when": "The operator confirms evidence-only scope.",
            },
            {
                "id": "ASM-002",
                "tier": "odylith_assumption",
                "statement": "External integrations remain sandboxed.",
                "confirm_when": "A maintainer confirms integration custody before live use.",
            },
        ],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-ASSUMPTIONS",
            "target_layer": "artifact_plan",
            "target_path": "proposal.assumptions",
            "semantic_node_id": "ArtifactPlanIR.assumptions",
            "issue_code": "quality_lens_gap",
            "replacement_fact": {
                "path": "assumptions",
                "value": [
                    "ASM-001: The first release records evidence only.",
                    "ASM-002: External integrations remain sandboxed.",
                    (
                        "ASM-003: High-risk decisions require explicit, reviewable confirmation "
                        "before proof is published."
                    ),
                ],
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is True
    assert [row["id"] for row in proposal["assumptions"]] == ["ASM-001", "ASM-002", "ASM-003"]
    assert proposal["assumptions"][0]["tier"] == "user_intent"
    assert proposal["assumptions"][0]["confirm_when"] == "The operator confirms evidence-only scope."
    assert proposal["assumptions"][1]["tier"] == "odylith_assumption"
    assert proposal["assumptions"][1]["confirm_when"] == "A maintainer confirms integration custody before live use."
    assert proposal["assumptions"][2]["tier"] == "user_intent"
    assert proposal["assumptions"][2]["statement"].endswith(".")
    assert "artifact_plan_patch_ledger" in proposal
    assert proposal["artifact_plan_patch_ledger"][0]["applied_paths"] == ("assumptions",)


def test_path_value_patch_preserves_assumption_metadata_when_statement_changes() -> None:
    proposal: dict[str, Any] = {
        "assumptions": [
            {
                "id": "ASM-002",
                "tier": "odylith_assumption",
                "statement": "External integrations remain sandboxed.",
                "confirm_when": "A maintainer confirms integration custody before live use.",
            }
        ],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-ASSUMPTIONS",
            "target_layer": "artifact_plan",
            "target_path": "proposal.assumptions",
            "semantic_node_id": "ArtifactPlanIR.assumptions",
            "issue_code": "quality_lens_gap",
            "replacement_fact": {
                "path": "assumptions",
                "value": [
                    "ASM-002: External integrations remain sandboxed until a maintainer approves live use.",
                ],
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is True
    row = proposal["assumptions"][0]
    assert row["id"] == "ASM-002"
    assert row["tier"] == "odylith_assumption"
    assert row["confirm_when"] == "A maintainer confirms integration custody before live use."
    assert row["statement"] == "External integrations remain sandboxed until a maintainer approves live use."


def test_path_value_patch_updates_nested_component_contract_field() -> None:
    proposal: dict[str, Any] = {
        "semantic_model": {
            "components": [
                {
                    "component_id": "review-workspace",
                    "produced_outputs": "old output",
                }
            ]
        },
        "components": [
            {
                "component_id": "review-workspace",
                "label": "Review Workspace",
                "responsibility": "Shows review state.",
                "component_contract": {
                    "produced_outputs": "old output",
                },
            }
        ],
    }
    operations = [
        {
            "operation_id": "GF-PATCH-NESTED",
            "target_layer": "artifact_plan",
            "target_path": "components[0].component_contract.produced_outputs",
            "semantic_node_id": "ArtifactPlanIR.components[0].component_contract.produced_outputs",
            "projection_kind": "registry",
            "affected_projections": ["registry"],
            "replacement_fact": {
                "path": "components[0].component_contract.produced_outputs",
                "value": "clear review output with blocked-state detail",
            },
        }
    ]

    changed = apply_artifact_plan_patch_operations(proposal, operations)

    assert changed is True
    component = proposal["components"][0]
    assert component["component_contract"]["produced_outputs"] == "clear review output with blocked-state detail"
    assert proposal["semantic_model"]["components"][0]["produced_outputs"] == "clear review output with blocked-state detail"
    assert "component_contract.produced_outputs" not in component
    ledger = proposal["artifact_plan_patch_ledger"][0]
    assert ledger["applied_paths"] == (
        "components[0].component_contract.produced_outputs",
        "semantic_model.components[0].produced_outputs",
    )


def test_patchset_repair_executes_artifact_plan_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "complete_confirmed_proposal",
        lambda proposal, *, release_selector: dict(proposal),
    )
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "ensure_apply_semantic_model",
        lambda proposal, **_kwargs: proposal,
    )
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("project brief preview missing release proof",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-102",
                    "target_layer": "artifact_plan",
                    "target_path": "project_brief.project_outcome",
                    "semantic_node_id": "ArtifactPlanIR.project_brief",
                    "issue_code": "artifact_shape_drift",
                    "affected_projections": ["project_brief"],
                    "replacement_fact": {
                        "path": "project_brief.project_outcome",
                        "value": "Release 0.0.1 proves the accepted path with review evidence.",
                    },
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        {"project_brief": {"project_outcome": "Old outcome."}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert repaired["project_brief"]["project_outcome"] == (
        "Release 0.0.1 proves the accepted path with review evidence."
    )
    assert repaired["artifact_plan_patch_ledger"][0]["operation_id"] == "GF-PATCH-102"


def test_patchset_repair_skips_full_completion_for_scoped_artifact_plan_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)

    def unexpected_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("completion")
        return {}

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", unexpected_completion)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "ensure_apply_semantic_model", unexpected_completion)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("project brief preview missing release proof",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-SCOPED",
                    "target_layer": "artifact_plan",
                    "target_path": "project_brief.project_outcome",
                    "semantic_node_id": "ArtifactPlanIR.project_brief",
                    "issue_code": "artifact_shape_drift",
                    "affected_projections": ["project_brief"],
                    "replacement_fact": {
                        "path": "project_brief.project_outcome",
                        "value": "Release 0.0.1 proves the accepted path with review evidence.",
                    },
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        {"project_brief": {"project_outcome": "Old outcome."}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert calls == []
    assert repaired["project_brief"]["project_outcome"] == (
        "Release 0.0.1 proves the accepted path with review evidence."
    )
    application = repaired["post_confirm_patch_application_ledger"][-1]
    assert application["operation_ids"] == ("GF-PATCH-SCOPED",)
    assert application["affected_projections"] == ("project_brief",)
    assert application["rerender_projections"] == (
        "project_brief",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )
    assert application["full_prewrite_required"] is False
    assert application["rerender_scope"] == "affected_projections"


def test_patchset_repair_routes_program_patch_to_full_prewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )

    def unexpected_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("completion")
        return {}

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", unexpected_completion)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "ensure_apply_semantic_model", unexpected_completion)
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("program wave plan needs restaging",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-PROGRAM",
                    "target_layer": "artifact_plan",
                    "target_path": "program.waves",
                    "projection_kind": "program",
                    "semantic_node_id": "ArtifactPlanIR.program",
                    "issue_code": "program_shape_drift",
                    "replacement_fact": {
                        "path": "program.waves",
                        "value": [{"wave_id": "W1", "goal": "Prove the governed acceptance path."}],
                    },
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        {"program": {"waves": []}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert calls == []
    assert repaired["program"]["waves"] == [{"wave_id": "W1", "goal": "Prove the governed acceptance path."}]
    application = repaired["post_confirm_patch_application_ledger"][-1]
    assert application["affected_projections"] == ("program",)
    assert application["rerender_projections"] == (
        "program",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
        "release",
    )
    assert application["full_prewrite_required"] is True
    assert application["rerender_scope"] == "full_prewrite"


def test_patchset_repair_release_scope_refreshes_compass_without_full_prewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "normalize_host_reasoned_proposal",
        lambda proposal: dict(proposal),
    )
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "validate_host_reasoned_proposal", lambda _proposal: None)
    monkeypatch.setattr(
        greenfield_post_confirm_patch_apply,
        "repair_greenfield_semantic_projections",
        lambda _proposal: False,
    )

    def unexpected_completion(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        calls.append("completion")
        return {}

    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "complete_confirmed_proposal", unexpected_completion)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "ensure_apply_semantic_model", unexpected_completion)
    context = GreenfieldPostConfirmRepairContext(
        pass_index=0,
        elapsed_seconds=1.0,
        budget_seconds=90.0,
        report=GreenfieldCompletionReport(
            status="failed",
            version="greenfield-post-confirm-completion-v1",
            semantic_model=True,
            artifact_counts={},
            tribunal_status="passed",
            issues=("release assignment preview needs acceptance refresh",),
        ),
        issues=(),
        review_report={"version": "odylith.greenfield.post_confirm.review_report.v1"},
        patchset_request={
            "version": "odylith.greenfield.post_confirm.patchset_request.v1",
            "operations": [
                {
                    "operation_id": "GF-PATCH-RELEASE",
                    "target_layer": "artifact_plan",
                    "target_path": "release_plan.strategy",
                    "projection_kind": "release",
                    "semantic_node_id": "ArtifactPlanIR.release_plan",
                    "issue_code": "release_shape_drift",
                    "replacement_fact": {
                        "path": "release_plan.strategy",
                        "value": "Release 0.0.1 carries the acceptance evidence.",
                    },
                }
            ],
        },
        quality_lenses={"lenses": {}},
        semantic_compiler={},
        repair_tier="rescue",
        rescue_activated=True,
    )

    repaired = greenfield_post_confirm_patch_apply.apply_greenfield_patchset_repairs(
        {"release_plan": {"strategy": "Old strategy."}},
        release_selector="0.0.1",
        repair_context=context,
    )

    assert calls == []
    assert repaired["release_plan"]["strategy"] == "Release 0.0.1 carries the acceptance evidence."
    application = repaired["post_confirm_patch_application_ledger"][-1]
    assert application["affected_projections"] == ("release",)
    assert application["rerender_projections"] == (
        "release",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )
    assert application["full_prewrite_required"] is False
    assert application["rerender_scope"] == "affected_projections"
