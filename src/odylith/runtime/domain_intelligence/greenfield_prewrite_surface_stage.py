"""Staged surface materialization for pre-confirm greenfield transactions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.domain_intelligence.proposal_memory import build_greenfield_acceptance_event_preview
from odylith.runtime.domain_intelligence.proposal_memory import build_project_brief_source_markdown
from odylith.runtime.domain_intelligence.proposal_memory import record_compiled_greenfield_acceptance


def build_staged_surface_refresh_preview(
    *,
    prewrite_root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    validation_gate: Mapping[str, Any],
    staged_backlog_result: Mapping[str, Any],
    staged_component_registry_preview: Sequence[Mapping[str, Any]],
    rendered_component_specs: Mapping[str, str],
    diagram_rows: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    staged_traceability_plan: Any,
    rendered_atlas_sources: Mapping[str, str],
    atlas_review_date: str,
    staged_atlas_catalog_rows: Sequence[Mapping[str, Any]],
    release_id: str,
    accepted_at: str,
    source_launch_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Materialize staged truth and run the owned-surface proof before confirm."""

    staged_root = Path(prewrite_root).expanduser().resolve()
    _materialize_staged_component_previews(
        prewrite_root=staged_root,
        proposal=proposal,
        staged_component_registry_preview=staged_component_registry_preview,
        rendered_component_specs=rendered_component_specs,
    )
    greenfield_apply_diagrams.materialize_apply_diagrams(
        root=staged_root,
        rows=diagram_rows,
        diagram_ids=diagram_ids,
        traceability_plan=staged_traceability_plan,
        rendered_atlas_sources=rendered_atlas_sources,
        review_date=atlas_review_date,
        require_compiled_sources=True,
        compiled_catalog_rows=staged_atlas_catalog_rows,
    )
    record_compiled_greenfield_acceptance(
        repo_root=staged_root,
        accepted_project_preview=_accepted_project_preview(
            proposal=proposal,
            backlog_result=staged_backlog_result,
            component_items=staged_component_registry_preview,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
            release_id=release_id,
            validation_gate=validation_gate,
            source_launch_context=source_launch_context,
            accepted_at=accepted_at,
        ),
        project_brief_record_text=build_project_brief_source_markdown(
            proposal=proposal,
            backlog_items=mapping_rows(staged_backlog_result.get("created")),
            component_items=staged_component_registry_preview,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
            release_id=release_id,
            accepted_at=accepted_at,
        ),
        compass_memory_preview=_compass_memory_preview(
            root=staged_root,
            proposal=proposal,
            backlog_result=staged_backlog_result,
            component_items=staged_component_registry_preview,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
            release_id=release_id,
            accepted_at=accepted_at,
        ),
    )
    return greenfield_surface_refresh_proof.build_prewrite_surface_refresh_preview(
        repo_root=staged_root,
    )


def _accepted_project_preview(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    validation_gate: Mapping[str, Any],
    source_launch_context: Mapping[str, Any],
    accepted_at: str,
) -> dict[str, Any]:
    return build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=mapping_rows(backlog_result.get("created")),
        component_items=tuple(row for row in component_items if isinstance(row, Mapping)),
        diagram_ids=tuple(str(value).strip() for value in diagram_ids if str(value).strip()),
        release_selector=release_selector,
        release_id=release_id,
        validation_gate=validation_gate,
        source_launch_context=source_launch_context,
        accepted_at=accepted_at,
    )


def _compass_memory_preview(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    accepted_at: str,
) -> dict[str, Any]:
    return build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=mapping_rows(backlog_result.get("created")),
        component_items=tuple(row for row in component_items if isinstance(row, Mapping)),
        diagram_ids=tuple(str(value).strip() for value in diagram_ids if str(value).strip()),
        release_selector=release_selector,
        release_id=release_id,
        accepted_at=accepted_at,
        repo_root=root,
    )


def _materialize_staged_component_previews(
    *,
    prewrite_root: Path,
    proposal: Mapping[str, Any],
    staged_component_registry_preview: Sequence[Mapping[str, Any]],
    rendered_component_specs: Mapping[str, str],
) -> None:
    preview_by_key = {
        greenfield_traceability.component_key(
            row.get("authoring_input") if isinstance(row.get("authoring_input"), Mapping) else row,
        ): row
        for row in staged_component_registry_preview
        if isinstance(row, Mapping)
    }
    for row in greenfield_apply_components.first_release_component_rows(proposal):
        if not isinstance(row, Mapping):
            continue
        key = greenfield_traceability.component_key(row)
        preview = preview_by_key.get(key)
        if not preview:
            raise ValueError(f"staged component registry preview missing for {key or '<unknown component>'}")
        greenfield_component_commit.materialize_compiled_component_from_preview(
            root=prewrite_root,
            preview=preview,
            rendered_component_specs=rendered_component_specs,
        )


__all__ = ["build_staged_surface_refresh_preview"]
