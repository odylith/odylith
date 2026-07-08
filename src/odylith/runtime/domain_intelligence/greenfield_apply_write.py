"""Final governed writes for confirmed greenfield apply."""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_findings
from odylith.runtime.artifact_quality.greenfield_package_repetition import (
    package_repetition_sample_matches_source_truth,
)
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedPackageQualityFinding
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_backlog_commit
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_component_registry_scope
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_source_casing
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_dependency_lookup_for
from odylith.runtime.domain_intelligence.greenfield_apply_components import first_release_component_rows
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import allocated_diagram_ids
from odylith.runtime.domain_intelligence.greenfield_component_contract import rendered_component_spec_quality_issues
from odylith.runtime.domain_intelligence.greenfield_component_contract_targets import operator_component_spec_issues
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_completion_report
from odylith.runtime.domain_intelligence.proposal_memory import record_compiled_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_memory import record_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_memory import compiled_project_brief_record_text
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.project_intelligence import builder as project_intelligence_builder
from odylith.runtime.surfaces import brand_assets
from odylith.runtime.surfaces import scaffold_mermaid_diagram


def release_assignment_note(*, selector: str) -> str:
    return f"Target confirmed first-wave greenfield workstream(s) for release `{selector}`."


def write_greenfield_proposal(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    tribunal: Any,
    backlog_result: Mapping[str, Any],
    prewrite_package: GreenfieldCompletionPackage | None = None,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply accepted Radar, Registry, Atlas, release, and memory records."""

    completion_quality_debt: list[str] = []
    source_text = greenfield_source_casing.proposal_source_casing_text(proposal)
    if source_text:
        restored_proposal = greenfield_source_casing.restore_source_casing_in_public_copy(
            proposal,
            source_text=source_text,
        )
        if isinstance(restored_proposal, Mapping):
            proposal = restored_proposal
        restored_backlog_result = greenfield_source_casing.restore_source_casing_in_public_copy(
            backlog_result,
            source_text=source_text,
        )
        if isinstance(restored_backlog_result, Mapping):
            backlog_result = restored_backlog_result
        if prewrite_package is not None:
            prewrite_package = greenfield_source_casing.package_with_source_casing(prewrite_package)
    if prewrite_package is not None:
        _raise_for_incomplete_compiled_write_package(prewrite_package, release_selector=release_selector)
    validation_gate = _source_cased_validation_gate(tribunal, source_text=source_text)
    release_bootstrap = None
    release_targeting = None
    has_compiled_package = prewrite_package is not None
    rendered_atlas_sources = dict(prewrite_package.rendered_atlas_sources or {}) if prewrite_package else {}
    rendered_component_specs = dict(prewrite_package.rendered_component_specs or {}) if prewrite_package else {}
    atlas_review_date = _atlas_review_date(prewrite_package)
    for raw_path in backlog_result.get("stale_idea_files", []):
        path = Path(str(raw_path))
        if path.is_file():
            path.unlink()
    greenfield_apply_prewrite.remove_stale_workstream_artifacts(root=root, stale_ids=backlog_result.get("stale_idea_ids", []))
    if release_selector:
        release_bootstrap = greenfield_apply_prewrite.ensure_release_target(
            repo_root=root,
            proposal=proposal,
            selector=release_selector,
        )
    greenfield_backlog_commit.write_backlog_files(backlog_result)
    if prewrite_package is not None and isinstance(prewrite_package.program_result, Mapping):
        program_result = greenfield_programs.materialize_compiled_greenfield_program(
            repo_root=root,
            backlog_result=backlog_result,
            program_result=prewrite_package.program_result,
        )
    else:
        program_result = greenfield_programs.create_greenfield_program(
            repo_root=root,
            proposal=proposal,
            backlog_result=backlog_result,
        )
    first_release_workstreams = (
        [str(item).strip().upper() for item in prewrite_package.release_workstream_ids if str(item).strip()]
        if prewrite_package is not None and prewrite_package.release_workstream_ids
        else greenfield_programs.first_release_workstream_ids(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            program_result=program_result,
        )
    )
    if release_selector:
        release_targeting = release_planning_authoring.add_workstreams_to_release(
            repo_root=root,
            workstream_ids=first_release_workstreams,
            selector=release_selector,
            note=release_assignment_note(selector=release_selector),
            idea_specs=backlog_result["_candidate_idea_specs"],
            allow_existing=True,
            dry_run=False,
        )
        if isinstance(release_targeting, dict) and isinstance(release_targeting.get("release"), Mapping):
            release_targeting.setdefault("release_id", str(release_targeting["release"].get("release_id", "")).strip())
    diagrams_created: list[str] = []
    atlas_scaffold_logs: list[str] = []
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    diagram_ids = (
        _compiled_atlas_diagram_ids(prewrite_package, expected_count=len(diagram_rows))
        if has_compiled_package
        else allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
    )
    traceability_plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        diagram_ids=diagram_ids,
    )
    for row, diagram_id in zip(diagram_rows, diagram_ids, strict=False):
        _scaffold_proposal_diagram(
            root=root,
            row=row,
            diagram_id=diagram_id,
            traceability_plan=traceability_plan,
            atlas_scaffold_logs=atlas_scaffold_logs,
            starter_source=_prewrite_atlas_source(
                row,
                rendered_atlas_sources,
                required=has_compiled_package,
            ),
            review_date=atlas_review_date,
        )
        diagrams_created.append(diagram_id)
    touched_backlog_paths = (
        greenfield_backlog_commit.compiled_backlog_traceability_paths(repo_root=root, backlog_result=backlog_result)
        if has_compiled_package
        else greenfield_traceability.apply_backlog_traceability(
            repo_root=root,
            proposal=proposal,
            plan=traceability_plan,
        )
    )
    component_handoffs = greenfield_component_commit.precompiled_component_handoffs(prewrite_package)
    if not component_handoffs:
        component_handoffs = greenfield_experience.build_component_handoffs(
            proposal=proposal,
            backlog_result=backlog_result,
            first_release_workstreams=first_release_workstreams,
            program_result=program_result,
            traceability_plan=traceability_plan,
            release_selector=release_selector,
        )
    component_diagram_scope = (
        {}
        if has_compiled_package
        else greenfield_component_registry_scope.build_component_diagram_scope(
            rows=diagram_rows,
            diagram_ids=diagram_ids,
        )
    )

    component_rows = first_release_component_rows(proposal)
    compiled_component_previews = greenfield_component_commit.compiled_component_previews_for_rows(
        prewrite_package,
        component_rows,
    )
    component_dependency_lookup = {} if has_compiled_package else component_dependency_lookup_for(component_rows)
    components_created: list[dict[str, Any]] = []
    for row in component_rows:
        if not isinstance(row, Mapping):
            continue
        key = greenfield_traceability.component_key(row)
        if has_compiled_package:
            preview = compiled_component_previews.get(key)
            if not preview:
                raise ValueError(f"compiled component registry preview missing for {key or '<unknown component>'}")
            created = greenfield_component_commit.materialize_compiled_component_from_preview(
                root=root,
                preview=preview,
                rendered_component_specs=rendered_component_specs,
            )
        else:
            handoff = component_handoffs.get(key, {})
            authoring_input = greenfield_component_commit.legacy_component_authoring_input(
                row=row,
                handoff=handoff,
                traceability_plan=traceability_plan,
                component_diagram_scope=component_diagram_scope,
                component_dependency_lookup=component_dependency_lookup,
                proposal=proposal,
            )
            created = greenfield_component_commit.register_component_from_authoring_input(
                root=root,
                authoring_input=authoring_input,
            )
            greenfield_component_commit.write_repaired_component_spec(
                root=root,
                created=created.as_dict(),
                rendered_component_specs=rendered_component_specs,
            )
        components_created.append(created.as_dict())
    if has_compiled_package:
        greenfield_component_commit.raise_for_compiled_component_registry_readback(
            root=root,
            previews=compiled_component_previews,
            rendered_component_specs=rendered_component_specs,
        )
    if not has_compiled_package:
        _raise_for_component_spec_quality(
            root=root,
            proposal=proposal,
            components=components_created,
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )

    release_id = "none"
    if isinstance(release_targeting, Mapping):
        release_id = str(release_targeting.get("release_id", "")).strip() or "none"
    if prewrite_package is not None and isinstance(prewrite_package.next_steps_preview, Mapping):
        next_steps = dict(prewrite_package.next_steps_preview)
    else:
        next_steps = greenfield_experience.build_next_steps(
            proposal=proposal,
            backlog_result=backlog_result,
            first_release_workstreams=first_release_workstreams,
            program_result=program_result,
            release_selector=release_selector,
        )
    if source_text and not (prewrite_package is not None and isinstance(prewrite_package.next_steps_preview, Mapping)):
        restored_next_steps = greenfield_source_casing.restore_source_casing_in_public_copy(
            next_steps,
            source_text=source_text,
        )
        if isinstance(restored_next_steps, Mapping):
            next_steps = restored_next_steps
    if not has_compiled_package:
        _raise_for_final_next_steps_quality(
            next_steps,
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )
    if _has_compiled_memory_package(prewrite_package):
        memory_record = record_compiled_greenfield_acceptance(
            repo_root=root,
            accepted_project_preview=prewrite_package.accepted_project_preview or {},
            project_brief_record_text=prewrite_package.project_brief_record_text,
            compass_memory_preview=prewrite_package.compass_memory_preview or {},
        )
        _raise_for_compiled_memory_readback(root=root, prewrite_package=prewrite_package, memory_record=memory_record)
    else:
        memory_record = record_greenfield_acceptance(
            repo_root=root,
            proposal=proposal,
            backlog_items=backlog_result["created"],
            component_items=components_created,
            diagram_ids=diagrams_created,
            release_selector=release_selector,
            release_id=release_id,
            validation_gate=validation_gate,
            source_launch_context=next_steps,
        )
    if not has_compiled_package:
        _raise_for_final_package_quality(
            root=root,
            proposal=proposal,
            release_selector=release_selector,
            tribunal=tribunal,
            backlog_result=backlog_result,
            program_result=program_result,
            release_bootstrap=release_bootstrap,
            release_targeting=release_targeting,
            first_release_workstreams=first_release_workstreams,
            component_rows=components_created,
            diagram_rows=diagram_rows,
            diagram_ids=diagram_ids,
            atlas_review_date=atlas_review_date,
            memory_record=memory_record,
            next_steps=next_steps,
            validation_gate=validation_gate,
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )
    if completion_quality_debt:
        _persist_completion_quality_debt(root=root, debt=completion_quality_debt)
    brand_asset_paths = brand_assets.ensure_brand_assets(repo_root=root)
    try:
        dashboard_refresh = _refresh_greenfield_dashboard(repo_root=root)
    except RuntimeError as exc:
        dashboard_refresh = {
            "status": "warning",
            "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
            "view": owned_surface_refresh.dashboard_handoff(surface="project"),
            "warning": str(exc),
        }
    else:
        dashboard_refresh["rendered_surface_custody"] = _raise_for_greenfield_rendered_surface_custody(
            repo_root=root,
            diagram_ids=diagrams_created,
        )
    dashboard_refresh["managed_brand_assets"] = {
        "status": "passed",
        "seeded_count": len(brand_asset_paths),
    }

    return {
        "mode": "applied",
        "validation_gate": validation_gate,
        "backlog": backlog_result["created"],
        "components": components_created,
        "diagrams": diagrams_created,
        "program": program_result,
        "backlog_topology": touched_backlog_paths,
        "atlas_scaffold_logs": atlas_scaffold_logs,
        "memory": memory_record,
        "dashboard_refresh": dashboard_refresh,
        "next_steps": next_steps,
        "prewrite_safety": dict(prewrite_package.prewrite_safety_preview or {}) if prewrite_package else {},
        "release_bootstrap": release_bootstrap or {"created": False, "release": {}},
        "release_target": release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
        "completion_priority_quality_debt": completion_quality_debt,
    }


_GREENFIELD_VISIBLE_SURFACES = ("radar", "registry", "atlas", "compass", "tooling_shell")


def _source_cased_validation_gate(tribunal: Any, *, source_text: str) -> dict[str, Any]:
    """Return the validation gate using the same visible source-casing custody as durable memory."""

    if isinstance(tribunal, Mapping):
        gate = dict(tribunal)
    else:
        gate = tribunal.to_dict() if hasattr(tribunal, "to_dict") else {}
    if not isinstance(gate, Mapping):
        return {}
    if not source_text:
        return dict(gate)
    restored = greenfield_source_casing.restore_source_casing_in_public_copy(
        gate,
        source_text=source_text,
    )
    return dict(restored) if isinstance(restored, Mapping) else dict(gate)


def _refresh_greenfield_dashboard(*, repo_root: Path) -> dict[str, Any]:
    view = owned_surface_refresh.dashboard_handoff(surface="project")
    owned_surface_refresh.raise_for_failed_refreshes(
        repo_root=Path(repo_root).resolve(),
        surfaces=_GREENFIELD_VISIBLE_SURFACES,
        operation_label="Greenfield apply dashboard visibility",
    )
    return {
        "status": "passed",
        "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
        "view": view,
    }


def _raise_for_greenfield_rendered_surface_custody(*, repo_root: Path, diagram_ids: Sequence[str]) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    issues: list[str] = []
    required_surfaces = (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
    )
    for relative_path in required_surfaces:
        path = root / relative_path
        if not path.is_file() or path.stat().st_size <= 0:
            issues.append(f"missing rendered Atlas surface: {relative_path}")
    catalog_path = root / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog = _read_json_mapping(catalog_path)
    rows = catalog.get("diagrams") if isinstance(catalog.get("diagrams"), list) else []
    by_id = {
        str(row.get("diagram_id", "")).strip(): row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("diagram_id", "")).strip()
    }
    checked_ids: list[str] = []
    for diagram_id in [str(value).strip() for value in diagram_ids if str(value).strip()]:
        checked_ids.append(diagram_id)
        row = by_id.get(diagram_id)
        if not isinstance(row, Mapping):
            issues.append(f"missing Atlas catalog entry for greenfield diagram: {diagram_id}")
            continue
        for field in ("source_svg", "source_png"):
            relative_asset = str(row.get(field, "")).strip()
            asset_path = root / relative_asset if relative_asset else None
            if not relative_asset or asset_path is None or not asset_path.is_file() or asset_path.stat().st_size <= 0:
                issues.append(f"{diagram_id}: missing rendered Atlas {field}: {relative_asset or '<empty>'}")
        if not str(row.get("render_source_fingerprint", "")).strip():
            issues.append(f"{diagram_id}: missing Atlas render_source_fingerprint")
        fingerprints = row.get("reviewed_watch_fingerprints")
        if not isinstance(fingerprints, Mapping) or not fingerprints:
            issues.append(f"{diagram_id}: missing Atlas reviewed_watch_fingerprints")
    if issues:
        detail = "\n".join(f"- {issue}" for issue in issues)
        raise RuntimeError(f"greenfield post-confirm rendered surface custody failed with {len(issues)} issue(s):\n{detail}")
    return {
        "status": "passed",
        "atlas_surface_count": len(required_surfaces),
        "atlas_diagram_count": len(checked_ids),
    }


def _prewrite_atlas_source(
    row: Mapping[str, Any],
    rendered_atlas_sources: Mapping[str, str],
    *,
    required: bool = False,
) -> str:
    path = _atlas_source_path_for_row(row)
    if not path:
        if required:
            raise ValueError("compiled greenfield Atlas source missing source path")
        return ""
    source = str(rendered_atlas_sources.get(path, "")).strip()
    if required and not source:
        raise ValueError(f"compiled greenfield Atlas source missing for {path}")
    return source


def _atlas_review_date(prewrite_package: GreenfieldCompletionPackage | None) -> str:
    if prewrite_package is not None:
        review_date = str(getattr(prewrite_package, "atlas_review_date", "") or "").strip()
        if not review_date:
            raise ValueError("compiled greenfield Atlas review date missing")
        return review_date
    return dt.date.today().isoformat()


def _compiled_atlas_diagram_ids(
    prewrite_package: GreenfieldCompletionPackage | None,
    *,
    expected_count: int,
) -> list[str]:
    raw_ids = prewrite_package.atlas_diagram_ids if prewrite_package is not None else ()
    diagram_ids = [str(item).strip().upper() for item in raw_ids if str(item).strip()]
    if len(diagram_ids) != expected_count:
        raise ValueError(
            "compiled greenfield Atlas diagram ids missing or incomplete "
            f"(expected {expected_count}, found {len(diagram_ids)})"
        )
    invalid = next((item for item in diagram_ids if not re.fullmatch(r"D-\d{3,}", item)), "")
    if invalid:
        raise ValueError(f"compiled greenfield Atlas diagram id is invalid: {invalid}")
    return diagram_ids


def _raise_for_incomplete_compiled_write_package(
    prewrite_package: GreenfieldCompletionPackage,
    *,
    release_selector: str,
) -> None:
    proposal = prewrite_package.proposal if isinstance(prewrite_package.proposal, Mapping) else {}
    issues: list[str] = []
    if not isinstance(prewrite_package.program_result, Mapping) or not prewrite_package.program_result:
        issues.append("missing compiled program_result")
    if not prewrite_package.release_workstream_ids:
        issues.append("missing compiled release_workstream_ids")
    if not isinstance(prewrite_package.next_steps_preview, Mapping) or not prewrite_package.next_steps_preview:
        issues.append("missing compiled next_steps_preview")
    if not _has_compiled_memory_package(prewrite_package):
        issues.append("missing compiled accepted-project, project brief, or Compass memory preview")

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
        try:
            _compiled_atlas_diagram_ids(prewrite_package, expected_count=len(diagram_rows))
        except ValueError as exc:
            issues.append(str(exc))

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


def _raise_for_compiled_memory_readback(
    *,
    root: Path,
    prewrite_package: GreenfieldCompletionPackage,
    memory_record: Mapping[str, Any],
) -> None:
    event = memory_record.get("event") if isinstance(memory_record.get("event"), Mapping) else {}
    accepted_at = str(event.get("ts_iso", "")).strip()
    expected_accepted_project = dict(prewrite_package.accepted_project_preview or {})
    expected_accepted_project["accepted_at"] = accepted_at
    expected_accepted_project = _json_comparable_mapping(expected_accepted_project)
    actual_accepted_project = _read_json_mapping(root / "odylith/runtime/source/accepted-project.v1.json")
    expected_project_brief = compiled_project_brief_record_text(
        prewrite_package.project_brief_record_text,
        accepted_at=accepted_at,
    )
    actual_project_brief = _read_text(root / "odylith/runtime/source/project-brief.v1.md")
    issues: list[str] = []
    if actual_accepted_project != expected_accepted_project:
        issues.append("accepted project record does not match compiled transaction preview")
    if actual_project_brief != expected_project_brief:
        issues.append("project brief record does not match compiled transaction text")
    if issues:
        detail = "\n".join(f"- {issue}" for issue in dedupe_strings(issues))
        raise ValueError(f"greenfield post-confirm compiled memory readback failed with {len(issues)} issue(s):\n{detail}")


def _json_comparable_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError("compiled memory preview is not JSON-serializable for readback") from exc
    return normalized if isinstance(normalized, Mapping) else {}


def _atlas_source_path_for_row(row: Mapping[str, Any]) -> str:
    slug = str(row.get("slug", "")).strip()
    if not slug:
        return ""
    return f"odylith/atlas/source/{slug}.mmd"


def _raise_for_final_package_quality(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    tribunal: Any,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
    release_bootstrap: Mapping[str, Any] | None,
    release_targeting: Mapping[str, Any] | None,
    first_release_workstreams: Sequence[str],
    component_rows: Sequence[Mapping[str, Any]],
    diagram_rows: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    atlas_review_date: str,
    memory_record: Mapping[str, Any],
    next_steps: Mapping[str, Any],
    validation_gate: Mapping[str, Any] | None = None,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
    completion_quality_debt: list[str] | None = None,
) -> None:
    accepted_project_preview = _read_json_mapping(root / "odylith/runtime/source/accepted-project.v1.json")
    project_dashboard_preview = project_intelligence_builder.build_project_intelligence_payload(
        repo_root=root,
        shell_payload={},
    )
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector=release_selector,
        rendered_component_specs=_actual_component_specs(root=root, components=component_rows),
        rendered_atlas_sources=_actual_atlas_sources(root=root, rows=diagram_rows),
        atlas_review_date=atlas_review_date,
        atlas_diagram_ids=tuple(diagram_ids),
        component_registry_preview=tuple(dict(row) for row in component_rows),
        project_brief_preview=proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {},
        project_brief_record_text=_read_text(root / "odylith/runtime/source/project-brief.v1.md"),
        tribunal_preview=dict(validation_gate or tribunal.to_dict()),
        accepted_project_preview=accepted_project_preview,
        project_dashboard_preview=project_dashboard_preview,
        compass_memory_preview=memory_record.get("event") if isinstance(memory_record.get("event"), Mapping) else {},
        next_steps_preview=next_steps,
        backlog_result=backlog_result,
        program_result=program_result,
        release_target_result=release_bootstrap or {"created": False, "release": {}},
        release_assignment_result=release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
        release_workstream_ids=tuple(str(item) for item in first_release_workstreams if str(item).strip()),
    )
    completion = build_greenfield_completion_report(
        proposal,
        release_selector=release_selector,
        rendered_component_specs=package.rendered_component_specs,
        tribunal_preview=package.tribunal_preview,
    )
    package_findings = greenfield_rendered_package_quality_findings(package)
    package_debt_messages = [
        finding.message
        for finding in package_findings
        if _structured_package_repetition_debt_allowed(finding, package=package)
    ]
    package_blocker_messages = [
        finding.message
        for finding in package_findings
        if finding.message not in set(package_debt_messages)
    ]
    issues = dedupe_strings(
        [
            *completion.issues,
            *package_blocker_messages,
            *generated_public_copy_issues("accepted-project final memory", accepted_project_preview),
            *generated_public_copy_issues("Compass final memory", package.compass_memory_preview),
        ]
    )
    if issues:
        _record_or_raise_completion_quality_debt(
            issues,
            error_prefix="greenfield post-confirm final write quality failed",
            debt_prefix="final write quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
            projection_copy_debt_allowed=True,
        )
    if package_debt_messages:
        _record_or_raise_structured_completion_quality_debt(
            package_debt_messages,
            error_prefix="greenfield post-confirm final write quality failed",
            debt_prefix="final write quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
        )


def _raise_for_final_next_steps_quality(
    next_steps: Mapping[str, Any],
    *,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
    completion_quality_debt: list[str] | None = None,
) -> None:
    issues = dedupe_strings(
        generated_public_copy_issues("operator next-steps final memory", next_steps)
    )
    if issues:
        _record_or_raise_completion_quality_debt(
            issues,
            error_prefix="greenfield post-confirm final next steps quality failed",
            debt_prefix="final next steps quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
            projection_copy_debt_allowed=True,
        )


def _actual_component_specs(*, root: Path, components: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    specs: dict[str, str] = {}
    for component in components:
        label = str(component.get("label", "")).strip()
        spec_path = Path(str(component.get("spec_path", "")))
        if not label:
            continue
        if not spec_path.is_absolute():
            spec_path = root / spec_path
        if spec_path.is_file():
            specs[label] = spec_path.read_text(encoding="utf-8")
    return specs


def _actual_atlas_sources(*, root: Path, rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for row in rows:
        path = _atlas_source_path_for_row(row)
        if not path:
            continue
        source_path = root / path
        if source_path.is_file():
            sources[path] = source_path.read_text(encoding="utf-8")
    return sources


def _read_json_mapping(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, Mapping) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _scaffold_proposal_diagram(
    *,
    root: Path,
    row: Mapping[str, Any],
    diagram_id: str,
    traceability_plan: Any,
    atlas_scaffold_logs: list[str],
    review_date: str,
    starter_source: str = "",
) -> None:
    components: list[dict[str, str]] = []
    for component in row.get("components", []):
        if not isinstance(component, Mapping):
            continue
        name = str(component.get("name", "")).strip()
        description = str(component.get("description", "")).strip()
        if name and description:
            components.append({"name": name, "description": description})
    link = next((item for item in traceability_plan.diagram_links if item.diagram_id == diagram_id), None)
    related_backlog = list(link.related_backlog_paths) if link is not None else []
    watch_paths: list[str] = []
    for path in row.get("watch_paths", []):
        token = str(path).strip()
        if not token:
            continue
        candidate = (root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            watch_paths.append(token)
    rc, log_lines = scaffold_mermaid_diagram.scaffold_diagram(
        repo_root=root,
        catalog="odylith/atlas/source/catalog/diagrams.v1.json",
        diagram_id=diagram_id,
        slug=str(row.get("slug", "")).strip(),
        title=str(row.get("title", "")).strip(),
        kind=str(row.get("kind", "flowchart")).strip() or "flowchart",
        owner=str(row.get("owner", "repo")).strip() or "repo",
        summary=str(row.get("summary", "")).strip(),
        read_guide=str(row.get("read_guide", "")).strip(),
        components=components,
        related_backlog=related_backlog,
        related_plans=[],
        related_docs=[],
        related_code=[],
        watch_paths=watch_paths,
        review_date=review_date,
        starter_source=starter_source or validated_mermaid_source(row),
        refresh=False,
    )
    log_text = "\n".join(log_lines).strip()
    if log_text:
        atlas_scaffold_logs.append(log_text)
    if rc != 0:
        if _upsert_existing_proposal_diagram(
            root=root,
            row=row,
            diagram_id=diagram_id,
            components=components,
            related_backlog=related_backlog,
            watch_paths=watch_paths,
            review_date=review_date,
            log_text=log_text,
            atlas_scaffold_logs=atlas_scaffold_logs,
            starter_source=starter_source,
        ):
            _update_scaffolded_diagram_link_state(
                root=root,
                slug=str(row.get("slug", "")).strip(),
                link_state=str(row.get("link_state", "")).strip(),
            )
            return
        detail = f": {log_text}" if log_text else ""
        raise RuntimeError(f"atlas scaffold failed for {row.get('slug')}{detail}")
    _update_scaffolded_diagram_link_state(
        root=root,
        slug=str(row.get("slug", "")).strip(),
        link_state=str(row.get("link_state", "")).strip(),
    )


def _upsert_existing_proposal_diagram(
    *,
    root: Path,
    row: Mapping[str, Any],
    diagram_id: str,
    components: list[dict[str, str]],
    related_backlog: list[str],
    watch_paths: list[str],
    review_date: str,
    log_text: str,
    atlas_scaffold_logs: list[str],
    starter_source: str = "",
) -> bool:
    if "already exists" not in log_text:
        return False
    slug = str(row.get("slug", "")).strip()
    if not slug and not diagram_id:
        return False
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return False
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return False
    entry = next(
        (
            item
            for item in diagrams
            if isinstance(item, dict)
            and (
                (slug and str(item.get("slug", "")).strip() == slug)
                or (diagram_id and str(item.get("diagram_id", "")).strip() == diagram_id)
            )
        ),
        None,
    )
    if entry is None:
        return False
    source_mmd = str(entry.get("source_mmd") or f"odylith/atlas/source/{slug}.mmd").strip()
    source_svg = str(entry.get("source_svg") or f"odylith/atlas/source/{slug}.svg").strip()
    source_png = str(entry.get("source_png") or f"odylith/atlas/source/{slug}.png").strip()
    entry.update(
        {
            "diagram_id": str(entry.get("diagram_id") or diagram_id).strip(),
            "slug": str(entry.get("slug") or slug).strip(),
            "title": str(row.get("title", "")).strip(),
            "kind": str(row.get("kind", "flowchart")).strip() or "flowchart",
            "owner": str(row.get("owner", "repo")).strip() or "repo",
            "last_reviewed_utc": review_date,
            "source_mmd": source_mmd,
            "source_svg": source_svg,
            "source_png": source_png,
            "summary": str(row.get("summary", "")).strip(),
            "read_guide": str(row.get("read_guide", "")).strip(),
            "components": components,
            "related_backlog": dedupe_strings(related_backlog),
            "change_watch_paths": dedupe_strings(watch_paths) or [source_mmd],
        }
    )
    catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    source_path = root / source_mmd
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text((starter_source or validated_mermaid_source(row)).rstrip() + "\n", encoding="utf-8")
    atlas_scaffold_logs.append(f"updated existing diagram: {entry['slug']}")
    return True

def _update_scaffolded_diagram_link_state(*, root: Path, slug: str, link_state: str) -> None:
    if not slug or not link_state:
        return
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return
    changed = False
    for item in diagrams:
        if not isinstance(item, dict):
            continue
        if str(item.get("slug", "")).strip() != slug:
            continue
        if str(item.get("link_state", "")).strip() != link_state:
            item["link_state"] = link_state
            changed = True
    if changed:
        catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def _raise_for_component_spec_quality(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    components: Sequence[Mapping[str, Any]],
    completion_priority_write_policy: Mapping[str, Any] | None = None,
    completion_quality_debt: list[str] | None = None,
) -> None:
    specs: dict[str, str] = {}
    for component in components:
        spec_path = Path(str(component.get("spec_path", "")))
        if not spec_path.is_absolute():
            spec_path = root / spec_path
        label = str(component.get("label", "") or component.get("component_id", "") or spec_path.parent.name).strip()
        if spec_path.is_file() and label:
            specs[label] = spec_path.read_text(encoding="utf-8")
    if not specs:
        return
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "")).strip()
    issues = rendered_component_spec_quality_issues(specs, project_title=title)
    if issues:
        _record_or_raise_completion_quality_debt(
            operator_component_spec_issues(issues),
            error_prefix="greenfield component spec quality gate failed",
            debt_prefix="component spec quality",
            completion_priority_write_policy=completion_priority_write_policy,
            completion_quality_debt=completion_quality_debt,
            projection_copy_debt_allowed=True,
        )


def _record_or_raise_completion_quality_debt(
    issues: Sequence[str],
    *,
    error_prefix: str,
    debt_prefix: str,
    completion_priority_write_policy: Mapping[str, Any] | None,
    completion_quality_debt: list[str] | None,
    projection_copy_debt_allowed: bool = False,
) -> None:
    if not issues:
        return
    issue_rows = dedupe_strings(str(issue) for issue in issues if str(issue).strip())
    if not issue_rows:
        return
    if _completion_priority_write_allowed(
        completion_priority_write_policy,
        debt_prefix=debt_prefix,
        issue_rows=issue_rows,
        projection_copy_debt_allowed=projection_copy_debt_allowed,
    ):
        if completion_quality_debt is not None:
            completion_quality_debt.extend(f"{debt_prefix}: {issue}" for issue in issue_rows)
        return
    detail = "\n".join(f"- {issue}" for issue in issue_rows)
    raise ValueError(f"{error_prefix} with {len(issue_rows)} issue(s):\n{detail}")


def _record_or_raise_structured_completion_quality_debt(
    issues: Sequence[str],
    *,
    error_prefix: str,
    debt_prefix: str,
    completion_priority_write_policy: Mapping[str, Any] | None,
    completion_quality_debt: list[str] | None,
) -> None:
    issue_rows = dedupe_strings(str(issue) for issue in issues if str(issue).strip())
    if not issue_rows:
        return
    if _completion_priority_policy_base_allowed(completion_priority_write_policy):
        if completion_quality_debt is not None:
            completion_quality_debt.extend(f"{debt_prefix}: {issue}" for issue in issue_rows)
        return
    detail = "\n".join(f"- {issue}" for issue in issue_rows)
    raise ValueError(f"{error_prefix} with {len(issue_rows)} issue(s):\n{detail}")


def _completion_priority_write_allowed(
    policy: Mapping[str, Any] | None,
    *,
    debt_prefix: str,
    issue_rows: Sequence[str],
    projection_copy_debt_allowed: bool,
) -> bool:
    if not _completion_priority_policy_base_allowed(policy):
        return False
    if not projection_copy_debt_allowed:
        return False
    return all(
        _late_projection_copy_debt_issue(debt_prefix=debt_prefix, issue=issue)
        or _completion_priority_policy_covers_late_issue(policy, issue)
        for issue in issue_rows
    )


def _completion_priority_policy_base_allowed(policy: Mapping[str, Any] | None) -> bool:
    return bool(
        isinstance(policy, Mapping)
        and str(policy.get("status", "")).strip() == "write_allowed_with_projection_quality_debt"
        and int(policy.get("hard_blocker_count", 1) or 0) == 0
    )


def _structured_package_repetition_debt_allowed(
    finding: RenderedPackageQualityFinding,
    *,
    package: GreenfieldCompletionPackage,
) -> bool:
    if finding.code != "package_repetition":
        return False
    if finding.source != "package_repetition_quality":
        return False
    if finding.severity not in {"low", "medium"}:
        return False
    if not finding.projection_id or finding.projection_id in {"release", "review_report"}:
        return False
    if finding.surface in {"release", "semantic_model", "tribunal"}:
        return False
    if not finding.semantic_node_id.startswith("ArtifactPlanIR."):
        return False
    if package_repetition_sample_matches_source_truth(package, finding.sample):
        return False
    return bool(finding.owner == "typed_package_artifact_gate" or finding.owner.endswith("_renderer"))


def _late_projection_copy_debt_issue(*, debt_prefix: str, issue: str) -> bool:
    text = str(issue or "").casefold()
    prefix = str(debt_prefix or "").casefold()
    if any(
        marker in text
        for marker in (
            "missing proof contract",
            "project implementation prompt",
            "release package",
            "semantic",
            "source token",
            "domain term",
            "accepted assumption",
        )
    ):
        return False
    if prefix == "final next steps quality":
        return _mechanical_projection_copy_issue(text)
    if prefix in {"component spec quality", "final write quality"}:
        return _mechanical_projection_copy_issue(text)
    return False


def _mechanical_projection_copy_issue(text: str) -> bool:
    if any(
        marker in text
        for marker in (
            "adjacent duplicate word",
            "repeats adjacent word",
            "clipped or dangling",
            "clipped action phrase",
            "clipped boundary phrase",
            "malformed ownership verb pair",
            "malformed connector sequence",
            "sentence-fragment drift",
            "invalid verb inflection",
            "doubled sentence punctuation",
            "comma-spliced capitalized clause",
            "repeats the same visible result",
        )
    ):
        return True
    return _mechanical_generated_prose_issue(text)


def _completion_priority_policy_covers_late_issue(policy: Mapping[str, Any] | None, issue: str) -> bool:
    if not isinstance(policy, Mapping):
        return False
    codes = {str(code or "").strip() for code in policy.get("debt_issue_codes", []) if str(code or "").strip()}
    text = str(issue or "").casefold()
    return "component_contract_quality" in codes and "finite/finite ownership verb drift" in text


_MECHANICAL_GENERATED_PROSE_LABELS = (
    "malformed ownership verb pair",
    "malformed ownership sentence",
    "duplicated evidence word",
    "dangling close-parenthesis token",
    "missing sentence boundary before proof obligation",
)


def _mechanical_generated_prose_issue(text: str) -> bool:
    prefix = "generated prose uses "
    if not text.startswith(prefix):
        return False
    return any(text.startswith(f"{prefix}{label}") for label in _MECHANICAL_GENERATED_PROSE_LABELS)


def _persist_completion_quality_debt(*, root: Path, debt: Sequence[str]) -> None:
    rows = dedupe_strings(str(item) for item in debt if str(item).strip())
    if not rows:
        return
    path = root / "odylith/runtime/source/accepted-project.v1.json"
    payload = dict(_read_json_mapping(path))
    if not payload:
        return
    ledger = {
        "status": "recorded",
        "guard": "typed_noncritical_projection_debt_only",
        "count": len(rows),
        "items": rows,
    }
    payload["completion_priority_quality_debt"] = ledger
    source_launch = payload.get("source_launch")
    if isinstance(source_launch, Mapping):
        source_launch_payload = dict(source_launch)
    else:
        source_launch_payload = {}
    source_launch_payload["completion_priority_quality_debt"] = ledger
    payload["source_launch"] = source_launch_payload
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def completion_priority_write_policy_from_manifest(manifest: Mapping[str, Any]) -> Mapping[str, Any] | None:
    priority = manifest.get("completion_priority") if isinstance(manifest.get("completion_priority"), Mapping) else None
    if priority is not None:
        return priority
    if str(manifest.get("status", "")).strip() != "passed":
        return None
    return {
        "status": "write_allowed_with_projection_quality_debt",
        "policy": (
            "post-confirm governed record creation takes priority when a final persisted-projection "
            "quality gate finds non-critical debt after a clean prewrite manifest"
        ),
        "original_stop_reason": str(manifest.get("stop_reason", "")).strip() or "passed",
        "debt_issue_count": 0,
        "debt_issue_codes": [],
        "hard_blocker_count": 0,
    }


__all__ = [
    "completion_priority_write_policy_from_manifest",
    "release_assignment_note",
    "write_greenfield_proposal",
]
