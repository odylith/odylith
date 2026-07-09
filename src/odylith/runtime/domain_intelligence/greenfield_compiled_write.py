"""Strict compiled-package sink for ProductCreateTransaction commits."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_backlog_commit
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_compiled_memory_readback
from odylith.runtime.domain_intelligence import greenfield_compiled_package_contract
from odylith.runtime.domain_intelligence import greenfield_compiled_readback
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_release_commit
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence import greenfield_traceability_commit
from odylith.runtime.domain_intelligence.greenfield_apply_components import first_release_component_rows
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction
from odylith.runtime.domain_intelligence.proposal_memory import record_compiled_greenfield_acceptance
from odylith.runtime.governance import owned_surface_refresh


_GREENFIELD_VISIBLE_SURFACES = greenfield_surface_refresh_proof.GREENFIELD_VISIBLE_SURFACES


def write_compiled_greenfield_package(
    *,
    root: Path,
    transaction: ProductCreateTransaction,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a verified transaction package through the compiled-only boundary.

    This path intentionally does not call the legacy proposal writer. A confirmed
    transaction may only materialize sealed package fields, validate readback,
    refresh required surfaces, and return the committed record summary.
    """

    _ = completion_priority_write_policy
    repo_root = Path(root).expanduser().resolve()
    package = transaction.prewrite_package
    proposal = package.proposal if isinstance(package.proposal, Mapping) else transaction.proposal
    release_selector = str(transaction.release_selector or "").strip()
    backlog_result = _mapping(package.backlog_result) or _mapping(transaction.backlog_result)
    validation_gate = _mapping(transaction.validation_gate)
    greenfield_compiled_package_contract.require_complete_compiled_greenfield_package(
        package,
        release_selector=release_selector,
    )
    surface_refresh_preview = greenfield_surface_refresh_proof.require_compiled_surface_refresh_preview(
        package.surface_refresh_preview,
    )
    rendered_atlas_sources = dict(package.rendered_atlas_sources or {})
    rendered_component_specs = dict(package.rendered_component_specs or {})
    atlas_review_date = greenfield_apply_diagrams.atlas_review_date(package)

    _remove_precompiled_stale_workstreams(root=repo_root, backlog_result=backlog_result)
    greenfield_backlog_commit.write_backlog_files(backlog_result, repo_root=repo_root)

    release_bootstrap: Mapping[str, Any] = {"created": False, "release": {}}
    if release_selector:
        release_bootstrap = greenfield_release_commit.materialize_compiled_release_target(
            repo_root=repo_root,
            release_selector=release_selector,
            release_target_result=package.release_target_result or {},
        )

    program_result = greenfield_programs.materialize_compiled_greenfield_program(
        repo_root=repo_root,
        backlog_result=backlog_result,
        program_result=package.program_result or {},
    )
    first_release_workstreams = tuple(
        str(item).strip().upper() for item in package.release_workstream_ids if str(item).strip()
    )

    release_targeting: Mapping[str, Any] = {"selector": release_selector, "release_id": "none", "events": []}
    if release_selector:
        release_targeting = greenfield_release_commit.materialize_compiled_release_assignment(
            repo_root=repo_root,
            release_assignment_result=package.release_assignment_result or {},
        )

    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    diagram_ids = greenfield_apply_diagrams.compiled_atlas_diagram_ids(
        package,
        expected_count=len(diagram_rows),
    )
    traceability_plan = greenfield_traceability_commit.compiled_traceability_plan(package.traceability_plan)
    traceability_plan = greenfield_traceability_commit.rebase_compiled_traceability_plan(
        traceability_plan,
        backlog_result=backlog_result,
    )
    diagram_write = greenfield_apply_diagrams.materialize_apply_diagrams(
        root=repo_root,
        rows=diagram_rows,
        diagram_ids=diagram_ids,
        traceability_plan=traceability_plan,
        rendered_atlas_sources=rendered_atlas_sources,
        review_date=atlas_review_date,
        require_compiled_sources=True,
        compiled_catalog_rows=package.atlas_catalog_rows,
    )
    diagrams_created = list(diagram_write.diagram_ids)
    touched_backlog_paths = greenfield_backlog_commit.compiled_backlog_traceability_paths(
        repo_root=repo_root,
        backlog_result=backlog_result,
    )
    greenfield_compiled_readback.raise_for_compiled_backlog_and_atlas_readback(
        root=repo_root,
        package=package,
    )

    component_rows = [row for row in first_release_component_rows(proposal) if isinstance(row, Mapping)]
    compiled_component_previews = greenfield_component_commit.compiled_component_previews_for_rows(
        package,
        component_rows,
    )
    components_created: list[dict[str, Any]] = []
    for row in component_rows:
        key = greenfield_traceability.component_key(row)
        preview = compiled_component_previews.get(key)
        if not preview:
            raise ValueError(f"compiled component registry preview missing for {key or '<unknown component>'}")
        created = greenfield_component_commit.materialize_compiled_component_from_preview(
            root=repo_root,
            preview=preview,
            rendered_component_specs=rendered_component_specs,
        )
        components_created.append(created.as_dict())
    greenfield_component_commit.raise_for_compiled_component_registry_readback(
        root=repo_root,
        previews=compiled_component_previews,
        rendered_component_specs=rendered_component_specs,
    )

    memory_record = record_compiled_greenfield_acceptance(
        repo_root=repo_root,
        accepted_project_preview=package.accepted_project_preview or {},
        project_brief_record_text=package.project_brief_record_text,
        compass_memory_preview=package.compass_memory_preview or {},
    )
    greenfield_compiled_memory_readback.raise_for_compiled_memory_readback(
        root=repo_root,
        prewrite_package=package,
        memory_record=memory_record,
    )

    dashboard_refresh = _refresh_compiled_greenfield_dashboard(
        repo_root=repo_root,
        surface_refresh_preview=surface_refresh_preview,
    )
    rendered_surface_custody = greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(
        repo_root=repo_root,
        diagram_ids=diagrams_created,
    )
    dashboard_refresh["rendered_surface_custody"] = rendered_surface_custody
    dashboard_refresh["managed_brand_assets"] = {
        "status": "passed",
        "seeded_count": len(package.brand_asset_writes or {}),
    }

    return {
        "mode": "applied",
        "validation_gate": validation_gate,
        "backlog": list(backlog_result.get("created", [])),
        "components": components_created,
        "diagrams": diagrams_created,
        "program": program_result,
        "backlog_topology": touched_backlog_paths,
        "atlas_scaffold_logs": list(diagram_write.scaffold_logs),
        "memory": memory_record,
        "dashboard_refresh": dashboard_refresh,
        "next_steps": dict(package.next_steps_preview or {}),
        "prewrite_safety": dict(package.prewrite_safety_preview or {}),
        "release_bootstrap": release_bootstrap or {"created": False, "release": {}},
        "release_target": release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
        "completion_priority_quality_debt": [],
    }


def _remove_precompiled_stale_workstreams(*, root: Path, backlog_result: Mapping[str, Any]) -> None:
    for raw_path in _sequence(backlog_result.get("stale_idea_files")):
        path = _repo_path(root=root, raw_path=raw_path)
        if path.is_file():
            path.unlink()
    greenfield_apply_prewrite.remove_stale_workstream_artifacts(
        root=root,
        stale_ids=backlog_result.get("stale_idea_ids", ()),
    )


def _refresh_compiled_greenfield_dashboard(
    *,
    repo_root: Path,
    surface_refresh_preview: Mapping[str, Any],
) -> dict[str, Any]:
    sealed_preview = greenfield_surface_refresh_proof.require_compiled_surface_refresh_preview(
        surface_refresh_preview,
    )
    view = owned_surface_refresh.dashboard_handoff(surface="project")
    owned_surface_refresh.raise_for_failed_refreshes(
        repo_root=Path(repo_root).resolve(),
        surfaces=_GREENFIELD_VISIBLE_SURFACES,
        operation_label="Greenfield create dashboard visibility",
    )
    return {
        "status": "passed",
        "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
        "view": view,
        "pre_confirm_surface_refresh": sealed_preview,
    }


def _repo_path(*, root: Path, raw_path: Any) -> Path:
    path = Path(str(raw_path))
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    resolved.relative_to(root)
    return resolved


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


__all__ = ["write_compiled_greenfield_package"]
