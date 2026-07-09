"""Completeness contract for transaction-bound greenfield create packages."""

from __future__ import annotations

from collections.abc import Mapping

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence import greenfield_traceability_commit
from odylith.runtime.domain_intelligence.greenfield_apply_components import first_release_component_rows
from odylith.runtime.domain_intelligence.greenfield_completion_types import GreenfieldCompletionPackage


def require_complete_compiled_greenfield_package(
    prewrite_package: GreenfieldCompletionPackage,
    *,
    release_selector: str,
) -> None:
    """Reject transaction packages that would need post-confirm artifact generation."""

    proposal = prewrite_package.proposal if isinstance(prewrite_package.proposal, Mapping) else {}
    issues: list[str] = []
    if not isinstance(prewrite_package.program_result, Mapping) or not prewrite_package.program_result:
        issues.append("missing compiled program_result")
    traceability_plan = greenfield_traceability_commit.compiled_traceability_plan(
        getattr(prewrite_package, "traceability_plan", None), required=False
    )
    if traceability_plan is None or not traceability_plan.workstreams:
        issues.append("missing compiled traceability_plan")
    if not prewrite_package.release_workstream_ids:
        issues.append("missing compiled release_workstream_ids")
    if not isinstance(prewrite_package.next_steps_preview, Mapping) or not prewrite_package.next_steps_preview:
        issues.append("missing compiled next_steps_preview")
    if not _has_compiled_memory_package(prewrite_package):
        issues.append("missing compiled accepted-project, project brief, or Compass memory preview")
    issues.extend(
        greenfield_surface_refresh_proof.surface_refresh_preview_issues(
            prewrite_package.surface_refresh_preview,
        )
    )

    component_rows = [row for row in first_release_component_rows(proposal) if isinstance(row, Mapping)]
    if component_rows:
        if not isinstance(prewrite_package.rendered_component_specs, Mapping) or not prewrite_package.rendered_component_specs:
            issues.append("missing compiled rendered_component_specs")
        if not prewrite_package.component_registry_preview:
            issues.append("missing compiled component_registry_preview")
        component_previews = greenfield_component_commit.precompiled_component_previews(prewrite_package)
        handoffs = greenfield_component_commit.precompiled_component_handoffs(prewrite_package)
        authoring_inputs = greenfield_component_commit.precompiled_component_authoring_inputs(prewrite_package)
        missing_handoffs = [
            greenfield_traceability.component_key(row)
            for row in component_rows
            if greenfield_traceability.component_key(row) not in handoffs
        ]
        if missing_handoffs:
            issues.append("missing compiled component implementation handoffs")
        missing_authoring_inputs = [
            greenfield_traceability.component_key(row)
            for row in component_rows
            if greenfield_traceability.component_key(row) not in authoring_inputs
        ]
        if missing_authoring_inputs:
            issues.append("missing compiled component authoring inputs")
        missing_registry_entries = [
            greenfield_traceability.component_key(row)
            for row in component_rows
            if greenfield_traceability.component_key(row) not in component_previews
            or not isinstance(component_previews[greenfield_traceability.component_key(row)].get("registry_entry"), Mapping)
        ]
        if missing_registry_entries:
            issues.append("missing compiled component registry entries")
        for key, preview in component_previews.items():
            issues.extend(greenfield_component_commit.compiled_component_registry_entry_issues(key=key, preview=preview))

    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    if diagram_rows:
        atlas_sources = (
            prewrite_package.rendered_atlas_sources
            if isinstance(prewrite_package.rendered_atlas_sources, Mapping)
            else {}
        )
        if len(atlas_sources) != len(diagram_rows):
            issues.append("missing compiled rendered_atlas_sources")
        if not str(prewrite_package.atlas_review_date or "").strip():
            issues.append("missing compiled atlas_review_date")
        compiled_diagram_ids: tuple[str, ...] = ()
        try:
            compiled_diagram_ids = tuple(
                greenfield_apply_diagrams.compiled_atlas_diagram_ids(
                    prewrite_package,
                    expected_count=len(diagram_rows),
                )
            )
        except ValueError as exc:
            issues.append(str(exc))
        try:
            compiled_catalog_rows = greenfield_apply_diagrams.compiled_atlas_catalog_rows(
                prewrite_package,
                expected_ids=compiled_diagram_ids,
            )
        except ValueError as exc:
            compiled_catalog_rows = []
            issues.append(str(exc))
        source_paths = {str(path).strip() for path in atlas_sources}
        missing_catalog_sources = [
            str(row.get("source_mmd", "")).strip()
            for row in compiled_catalog_rows
            if str(row.get("source_mmd", "")).strip() not in source_paths
        ]
        if missing_catalog_sources:
            issues.append("compiled Atlas catalog rows drifted from rendered_atlas_sources")
        if traceability_plan is not None:
            issues.extend(
                greenfield_traceability_commit.compiled_traceability_diagram_issues(
                    traceability_plan=traceability_plan,
                    diagram_ids=compiled_diagram_ids,
                )
            )

    if str(release_selector or "").strip():
        if not isinstance(prewrite_package.release_target_result, Mapping) or not prewrite_package.release_target_result:
            issues.append("missing compiled release_target_result")
        if not isinstance(prewrite_package.release_assignment_result, Mapping) or not prewrite_package.release_assignment_result:
            issues.append("missing compiled release_assignment_result")

    if issues:
        detail = "; ".join(dedupe_strings(issues))
        raise ValueError(
            "compiled greenfield package is incomplete; rebuild the ProductCreateTransaction before commit: "
            f"{detail}"
        )


def _has_compiled_memory_package(prewrite_package: GreenfieldCompletionPackage | None) -> bool:
    return bool(
        prewrite_package is not None
        and isinstance(prewrite_package.accepted_project_preview, Mapping)
        and str(prewrite_package.project_brief_record_text or "").strip()
        and isinstance(prewrite_package.compass_memory_preview, Mapping)
    )


__all__ = ["require_complete_compiled_greenfield_package"]
