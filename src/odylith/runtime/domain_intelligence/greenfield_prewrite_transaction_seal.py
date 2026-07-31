"""Final staged-tree seal for pre-confirm greenfield transactions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_backlog_commit
from odylith.runtime.domain_intelligence import greenfield_prewrite_commit_result
from odylith.runtime.domain_intelligence import greenfield_prewrite_surface_stage
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof


@dataclass(frozen=True)
class GreenfieldPrewriteSealRequest:
    prewrite_root: Path
    target_root: Path
    proposal: Mapping[str, Any]
    validation_gate: Mapping[str, Any]
    staged_backlog_result: Mapping[str, Any]
    target_backlog_result: Mapping[str, Any]
    staged_component_registry_preview: Sequence[Mapping[str, Any]]
    rendered_component_specs: Mapping[str, str]
    diagram_rows: Sequence[Mapping[str, Any]]
    diagram_ids: Sequence[str]
    staged_traceability_plan: Any
    rendered_atlas_sources: Mapping[str, str]
    atlas_review_date: str
    compiled_atlas_catalog_rows: Sequence[Mapping[str, Any]]
    accepted_project_preview: Mapping[str, Any]
    project_brief_record_text: str
    compass_memory_preview: Mapping[str, Any]
    next_steps_preview: Mapping[str, Any]
    prewrite_safety_preview: Mapping[str, Any]
    staged_release_bootstrap: Mapping[str, Any]
    staged_release_targeting: Mapping[str, Any]
    brand_asset_count: int


@dataclass(frozen=True)
class GreenfieldPrewriteTransactionSeal:
    surface_refresh_preview: Mapping[str, Any]
    repository_write_set: Mapping[str, Any] | None
    commit_result_preview: Mapping[str, Any] | None


def seal_staged_greenfield_create(request: GreenfieldPrewriteSealRequest) -> GreenfieldPrewriteTransactionSeal:
    """Prove the final stage, then seal its bytes and operator result."""

    try:
        staged_surfaces = greenfield_prewrite_surface_stage.materialize_staged_greenfield_surfaces(
            prewrite_root=request.prewrite_root,
            proposal=request.proposal,
            staged_component_registry_preview=request.staged_component_registry_preview,
            rendered_component_specs=request.rendered_component_specs,
            diagram_rows=request.diagram_rows,
            diagram_ids=request.diagram_ids,
            staged_traceability_plan=request.staged_traceability_plan,
            rendered_atlas_sources=request.rendered_atlas_sources,
            atlas_review_date=request.atlas_review_date,
            compiled_atlas_catalog_rows=request.compiled_atlas_catalog_rows,
            accepted_project_preview=request.accepted_project_preview,
            project_brief_record_text=request.project_brief_record_text,
            compass_memory_preview=request.compass_memory_preview,
        )
    except (RuntimeError, ValueError) as exc:
        return GreenfieldPrewriteTransactionSeal(
            surface_refresh_preview=greenfield_surface_refresh_proof.failed_prewrite_surface_refresh_preview(
                reason=exc,
            ),
            repository_write_set=None,
            commit_result_preview=None,
        )

    backlog_topology = greenfield_backlog_commit.compiled_backlog_traceability_paths(
        repo_root=request.prewrite_root,
        backlog_result=request.staged_backlog_result,
    )
    commit_result = greenfield_prewrite_commit_result.build_greenfield_commit_result_preview(
        source_root=request.prewrite_root,
        target_root=request.target_root,
        validation_gate=request.validation_gate,
        backlog_result=request.target_backlog_result,
        components=staged_surfaces.components_created,
        diagrams=staged_surfaces.diagram_ids,
        backlog_topology=backlog_topology,
        staged_surfaces=staged_surfaces,
        next_steps=request.next_steps_preview,
        prewrite_safety=request.prewrite_safety_preview,
        release_bootstrap=request.staged_release_bootstrap,
        release_target=request.staged_release_targeting,
        brand_asset_count=request.brand_asset_count,
    )
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=request.target_root,
        staged_root=request.prewrite_root,
    )
    return GreenfieldPrewriteTransactionSeal(
        surface_refresh_preview=dict(staged_surfaces.surface_refresh_preview),
        repository_write_set=write_set,
        commit_result_preview=commit_result,
    )


__all__ = [
    "GreenfieldPrewriteSealRequest",
    "GreenfieldPrewriteTransactionSeal",
    "seal_staged_greenfield_create",
]
