from __future__ import annotations

from pathlib import Path

from odylith.runtime.domain_intelligence.greenfield_artifact_plan import ARTIFACT_PLAN_IR_VERSION
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_draft_exact_repair_path
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_draft_repair_projection
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_affected_projections
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_canonical_root
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_expand_projection_scope
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_is_immutable_field
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_operation_affected_projections
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_projection_for_path
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_root_kind
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_scope_requires_full_prewrite
from odylith.runtime.domain_intelligence.greenfield_projection_repair_targets import (
    projection_repair_target_for_finding,
)


DOMAIN_INTELLIGENCE = Path(__file__).resolve().parents[3] / "src/odylith/runtime/domain_intelligence"


def test_artifact_plan_ir_canonicalizes_sanctioned_roots_and_immutable_fields() -> None:
    assert ARTIFACT_PLAN_IR_VERSION == "odylith.greenfield.artifact_plan_ir.v1"
    assert artifact_plan_canonical_root("radar") == "backlog"
    assert artifact_plan_canonical_root("registry") == "components"
    assert artifact_plan_canonical_root("atlas") == "diagrams"
    assert artifact_plan_canonical_root("release") == "release_plan"

    assert artifact_plan_root_kind("project_brief") == "dict"
    assert artifact_plan_root_kind("validation_strategy") == "list"
    assert artifact_plan_root_kind("components") == "row"
    assert artifact_plan_is_immutable_field("schema_version") is True
    assert artifact_plan_is_immutable_field("component_id") is True
    assert artifact_plan_is_immutable_field("responsibility") is False


def test_artifact_plan_ir_maps_paths_to_projection_ids_without_surface_guessing() -> None:
    assert artifact_plan_projection_for_path("backlog[0].success_metrics") == "radar"
    assert artifact_plan_projection_for_path("components[0].responsibility") == "registry"
    assert artifact_plan_projection_for_path("diagrams[0].summary") == "atlas"
    assert artifact_plan_projection_for_path("rendered_component_specs") == "registry"
    assert artifact_plan_projection_for_path("rendered_atlas_sources") == "atlas"
    assert artifact_plan_projection_for_path("proposal.backlog") == "radar"
    assert artifact_plan_projection_for_path("proposal.assumptions") == "project_brief"
    assert artifact_plan_projection_for_path("ArtifactPlanIR.assumptions") == "project_brief"
    assert artifact_plan_projection_for_path("prewrite_package.next_steps") == "next_steps"

    assert (
        artifact_plan_affected_projections(
            projection_id="review_report",
            target_path="rendered_component_specs",
            surface="engineer",
        )
        == ("registry",)
    )
    assert artifact_plan_affected_projections(target_path="proposal.assumptions") == ("project_brief",)
    assert artifact_plan_affected_projections(surface="product_manager") == ()


def test_artifact_plan_ir_normalizes_artifact_draft_repair_projection_ids() -> None:
    assert artifact_draft_repair_projection("rendered_component_specs") == "registry"
    assert artifact_draft_repair_projection("rendered_atlas_sources") == "atlas"
    assert artifact_draft_repair_projection("artifact_draft_set") == "artifact_draft_set"
    assert artifact_draft_repair_projection("unknown_projection") == ""


def test_artifact_plan_ir_requires_exact_artifact_draft_repair_paths() -> None:
    assert artifact_draft_exact_repair_path("prewrite_package.rendered_component_specs::spec.md") is True
    assert artifact_draft_exact_repair_path("prewrite_package.rendered_component_specs::") is False
    assert artifact_draft_exact_repair_path("prewrite_package.project_brief_preview") is False
    assert artifact_draft_exact_repair_path("prewrite_package.project_brief_preview.project_outcome") is True
    assert artifact_draft_exact_repair_path("prewrite_package.next_steps_preview") is False
    assert artifact_draft_exact_repair_path("prewrite_package.next_steps_preview.operator_sequence[0]") is True
    assert artifact_draft_exact_repair_path("prewrite_package.compass_memory_preview.summary") is True
    assert artifact_draft_exact_repair_path("prewrite_package.compass_memory_preview") is False
    assert artifact_draft_exact_repair_path("prewrite_package.project_dashboard_preview.overview.summary") is True
    assert artifact_draft_exact_repair_path("prewrite_package.project_dashboard_preview.host_handoff_prompts[0]") is False
    assert (
        artifact_draft_exact_repair_path("prewrite_package.project_dashboard_preview.host_handoff_prompts[0].prompt")
        is True
    )


def test_artifact_plan_ir_expands_projection_dependencies_without_prose_routing() -> None:
    operation = {
        "affected_projections": ["project_brief"],
        "target_path": "product_manager.note",
        "projection_kind": "product_manager",
    }

    assert artifact_plan_operation_affected_projections(operation) == ("project_brief",)
    assert artifact_plan_expand_projection_scope(("project_brief",)) == (
        "project_brief",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )
    assert artifact_plan_expand_projection_scope(("registry",)) == (
        "registry",
        "project_brief",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )
    assert artifact_plan_expand_projection_scope(("release",)) == (
        "release",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )
    assert artifact_plan_operation_affected_projections({"projection_kind": "program"}) == ("program",)
    assert artifact_plan_operation_affected_projections({"target_path": "prewrite_package.next_steps"}) == (
        "next_steps",
    )
    assert artifact_plan_expand_projection_scope(("program",)) == (
        "program",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
        "release",
    )
    assert artifact_plan_scope_requires_full_prewrite(("project_brief",)) is False
    assert artifact_plan_scope_requires_full_prewrite(("release",)) is False
    assert artifact_plan_scope_requires_full_prewrite(("radar",)) is True
    assert artifact_plan_scope_requires_full_prewrite(("program",)) is True
    assert artifact_plan_operation_affected_projections({"projection_kind": "product_manager"}) == ()


def test_projection_repair_targets_map_preview_findings_to_source_facts() -> None:
    accepted = projection_repair_target_for_finding(
        {
            "target_path": "prewrite_package.accepted_project_preview.proposal.diagrams[0].mermaid_source",
            "projection_id": "accepted_project",
        }
    )
    assert accepted is not None
    assert accepted.target_layer == "artifact_plan"
    assert accepted.target_path == "diagrams[0].mermaid_source"
    assert accepted.semantic_node_id == "ArtifactPlanIR.diagrams[0].mermaid_source"
    assert accepted.affected_projections == ("atlas", "accepted_project", "project_dashboard")

    dashboard_first_path = projection_repair_target_for_finding(
        {
            "target_path": "prewrite_package.project_dashboard_preview.product_story.release_contract[1].body",
            "projection_id": "project_dashboard",
        }
    )
    assert dashboard_first_path is not None
    assert dashboard_first_path.target_layer == "semantic_model"
    assert dashboard_first_path.target_path == "semantic_model.first_path_contract"
    assert dashboard_first_path.operation_kind == "semantic_first_path"
    assert dashboard_first_path.affected_projections == ("project_dashboard",)

    dashboard_boundary = projection_repair_target_for_finding(
        {
            "target_path": "prewrite_package.project_dashboard_preview.product_story.release_contract[2].body",
            "projection_id": "project_dashboard",
        }
    )
    assert dashboard_boundary is not None
    assert dashboard_boundary.target_layer == "artifact_plan"
    assert dashboard_boundary.target_path == "project_brief.operating_principle"
    assert dashboard_boundary.operation_kind == "artifact_plan_projection"
    assert dashboard_boundary.affected_projections == (
        "project_brief",
        "accepted_project",
        "project_dashboard",
        "compass",
        "next_steps",
    )

    dashboard_proof = projection_repair_target_for_finding(
        {
            "target_path": "prewrite_package.project_dashboard_preview.product_story.release_contract[4].body",
            "projection_id": "project_dashboard",
        }
    )
    assert dashboard_proof is not None
    assert dashboard_proof.target_layer == "semantic_model"
    assert dashboard_proof.target_path == "semantic_model.domain_ontology.proof_boundary"
    assert dashboard_proof.operation_kind == "semantic_proof_boundary"


def test_artifact_plan_ir_contract_replaces_private_projection_maps_in_callers() -> None:
    patchset_source = (DOMAIN_INTELLIGENCE / "greenfield_post_confirm_patchset.py").read_text(encoding="utf-8")
    executor_source = (DOMAIN_INTELLIGENCE / "greenfield_artifact_plan_patch_executor.py").read_text(encoding="utf-8")

    assert "def _projection_from_target_path" not in patchset_source
    assert "artifact_plan_affected_projections" in patchset_source
    assert "_SURFACE_DEFAULT_PROJECTIONS" not in (DOMAIN_INTELLIGENCE / "greenfield_artifact_plan.py").read_text(
        encoding="utf-8"
    )
    assert "_ROOT_ALIASES" not in executor_source
    assert "_IMMUTABLE_FIELDS" not in executor_source
    assert "artifact_plan_canonical_root" in executor_source
    assert "artifact_plan_is_immutable_field" in executor_source
