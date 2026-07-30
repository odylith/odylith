"""Prewrite package assembly for confirmed greenfield creation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import datetime as dt
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text
from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_acceptance_identity
from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence.greenfield_prewrite_stage_root import ensure_greenfield_create_baseline
from odylith.runtime.domain_intelligence.greenfield_prewrite_stage_root import staged_greenfield_prewrite_root
from odylith.runtime.domain_intelligence.greenfield_prewrite_stale_cleanup import (
    accepted_greenfield_workstream_ids,
)
from odylith.runtime.domain_intelligence.greenfield_prewrite_stale_cleanup import (
    mark_previous_greenfield_workstreams_stale,
)
from odylith.runtime.domain_intelligence.greenfield_prewrite_stale_cleanup import (
    remove_prewrite_stale_idea_files,
)
from odylith.runtime.domain_intelligence.greenfield_prewrite_stale_cleanup import (
    remove_stale_workstream_artifacts,
)
from odylith.runtime.domain_intelligence import greenfield_prewrite_transaction_seal
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_release_commit
from odylith.runtime.domain_intelligence import greenfield_source_casing
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence import greenfield_traceability_commit
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.proposal_memory import build_greenfield_acceptance_event_preview
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.domain_intelligence.proposal_memory import build_project_brief_source_markdown
from odylith.runtime.domain_intelligence.proposal_memory import compiled_project_brief_record_text
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from odylith.runtime.surfaces import brand_assets


@dataclass(frozen=True)
class GreenfieldPrewriteBuild:
    package: GreenfieldCompletionPackage
    backlog_result: Mapping[str, Any]


def build_prewrite_completion_package(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_args: Sequence[Mapping[str, Any]],
    validation_gate: Mapping[str, Any],
    release_assignment_note: str,
) -> GreenfieldPrewriteBuild:
    """Render the full confirmed-create package in a staged repo before writes."""

    source_text = greenfield_source_casing.proposal_source_casing_text(proposal)
    accepted_at = _compiled_acceptance_timestamp()
    baseline_writes = greenfield_create_baseline.precompiled_greenfield_create_baseline_writes(root)
    brand_asset_writes = brand_assets.precompiled_brand_asset_writes(repo_root=root)
    if source_text:
        restored_proposal = greenfield_source_casing.restore_source_casing_in_public_copy(
            proposal,
            source_text=source_text,
        )
        if isinstance(restored_proposal, Mapping):
            proposal = restored_proposal
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    previous_greenfield_ids = accepted_greenfield_workstream_ids(root)
    with staged_greenfield_prewrite_root(root) as prewrite_root:
        brand_assets.materialize_precompiled_brand_assets(
            repo_root=prewrite_root,
            brand_asset_writes=brand_asset_writes,
        )
        staged_backlog_result = backlog_authoring.create_queued_backlog_items(
            repo_root=prewrite_root,
            backlog_index_path=prewrite_root / "odylith/radar/source/INDEX.md",
            ideas_root=prewrite_root / "odylith/radar/source/ideas",
            titles=[str(row.get("title", "")).strip() for row in backlog_rows if str(row.get("title", "")).strip()],
            args=backlog_args,
        )
        staged_backlog_result = mark_previous_greenfield_workstreams_stale(
            staged_backlog_result,
            stale_ids=previous_greenfield_ids,
        )
        remove_prewrite_stale_idea_files(root=prewrite_root, backlog_result=staged_backlog_result)
        remove_stale_workstream_artifacts(
            root=prewrite_root,
            stale_ids=staged_backlog_result.get("stale_idea_ids", ()),
        )
        preview_program_result = greenfield_programs.create_greenfield_program(
            repo_root=prewrite_root,
            proposal=proposal,
            backlog_result=staged_backlog_result,
            dry_run=True,
        )
        rendered_component_specs = greenfield_apply_components.render_prewrite_component_specs(
            root=prewrite_root,
            proposal=proposal,
            release_selector=release_selector,
            backlog_result=staged_backlog_result,
            program_result=preview_program_result,
        )
        staged_component_registry_preview = greenfield_apply_components.preview_prewrite_components(
            root=prewrite_root,
            proposal=proposal,
            release_selector=release_selector,
            backlog_result=staged_backlog_result,
            program_result=preview_program_result,
        )
        component_registry_preview = remap_prewrite_component_items(
            staged_component_registry_preview,
            source_root=prewrite_root,
            target_root=root,
        )
        rendered_atlas_sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal)
        atlas_review_date = dt.date.today().isoformat()
        materialize_prewrite_backlog_result(staged_backlog_result)
        diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
        diagram_ids = greenfield_apply_diagrams.allocated_diagram_ids(prewrite_root, len(diagram_rows), rows=diagram_rows)
        traceability_plan = greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=staged_backlog_result["created"],
            diagram_ids=diagram_ids,
        )
        staged_traceability_plan = traceability_plan
        greenfield_traceability.apply_backlog_traceability(
            repo_root=prewrite_root,
            proposal=proposal,
            plan=traceability_plan,
        )
        staged_program_result = greenfield_programs.materialize_compiled_greenfield_program(
            repo_root=prewrite_root,
            backlog_result=staged_backlog_result,
            program_result=preview_program_result,
        )
        staged_backlog_result = refresh_prewrite_backlog_result(staged_backlog_result)
        backlog_result = remap_prewrite_backlog_result(
            staged_backlog_result,
            source_root=prewrite_root,
            target_root=root,
        )
        traceability_plan = greenfield_traceability_commit.rebase_compiled_traceability_plan(
            traceability_plan,
            backlog_result=backlog_result,
        )
        atlas_catalog_rows = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
            root=root,
            rows=diagram_rows,
            diagram_ids=diagram_ids,
            traceability_plan=traceability_plan,
            review_date=atlas_review_date,
        )
        first_release_workstreams = greenfield_programs.first_release_workstream_ids(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            program_result=preview_program_result,
        )
        preview_release_target = None
        preview_release_assignment = None
        staged_release_bootstrap: Mapping[str, Any] = {"created": False, "release": {}}
        staged_release_targeting: Mapping[str, Any] = {
            "selector": release_selector,
            "release_id": "none",
            "events": [],
        }
        if release_selector:
            preview_release_target = ensure_release_target(
                repo_root=prewrite_root,
                proposal=proposal,
                selector=release_selector,
                dry_run=True,
            )
            staged_release_bootstrap = greenfield_release_commit.materialize_compiled_release_target(
                repo_root=prewrite_root,
                release_selector=release_selector,
                release_target_result=preview_release_target,
            )
            preview_release_assignment = release_planning_authoring.add_workstreams_to_release(
                repo_root=prewrite_root,
                workstream_ids=first_release_workstreams,
                selector=release_selector,
                note=release_assignment_note,
                idea_specs=staged_backlog_result["_candidate_idea_specs"],
                allow_existing=True,
                dry_run=True,
            )
            staged_release_targeting = greenfield_release_commit.materialize_compiled_release_assignment(
                repo_root=prewrite_root,
                release_assignment_result=preview_release_assignment,
            )
            staged_release_targeting = {
                **staged_release_targeting,
                "workstream_ids": list(first_release_workstreams),
            }
        prewrite_safety_preview = prewrite_safety_evidence(
            validation_gate=validation_gate,
            program_result=preview_program_result,
            release_target_result=preview_release_target,
            release_assignment_result=preview_release_assignment,
            release_selector=release_selector,
        )
        package_proposal = proposal_with_component_brief_gate(proposal)
        project_brief = package_proposal.get("project_brief") if isinstance(package_proposal.get("project_brief"), Mapping) else {}
        next_steps_preview = greenfield_experience.build_next_steps(
            proposal=package_proposal,
            backlog_result=backlog_result,
            first_release_workstreams=first_release_workstreams,
            program_result=preview_program_result,
            release_selector=release_selector,
        )
        accepted_project_preview = preview_accepted_project_memory(
            root=prewrite_root,
            proposal=package_proposal,
            backlog_result=backlog_result,
            component_items=component_registry_preview,
            release_selector=release_selector,
            release_target_result=preview_release_target,
            release_assignment_result=preview_release_assignment,
            validation_gate=validation_gate,
            source_launch_context=next_steps_preview,
            accepted_at=accepted_at,
        )
        compass_memory_preview = preview_compass_acceptance_event(
            root=prewrite_root,
            target_root=root,
            proposal=package_proposal,
            backlog_result=backlog_result,
            component_items=component_registry_preview,
            release_selector=release_selector,
            release_target_result=preview_release_target,
            release_assignment_result=preview_release_assignment,
            accepted_at=accepted_at,
        )
        project_brief_record_text = build_project_brief_source_markdown(
            proposal=package_proposal,
            backlog_items=mapping_rows(backlog_result.get("created")),
            component_items=component_registry_preview,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
            release_id=_prewrite_release_id(preview_release_target, preview_release_assignment),
            accepted_at=accepted_at,
        )
        resolved_accepted_at = greenfield_acceptance_identity.resolve_preconfirm_acceptance_timestamp(
            repo_root=root,
            fresh_accepted_at=accepted_at,
            accepted_project_preview=accepted_project_preview,
            project_brief_record_text=project_brief_record_text,
            compass_memory_preview=compass_memory_preview,
            portable_roots=(prewrite_root,),
        )
        if resolved_accepted_at != accepted_at:
            accepted_at = resolved_accepted_at
            accepted_project_preview = dict(accepted_project_preview)
            accepted_project_preview["accepted_at"] = accepted_at
            compass_memory_preview = dict(compass_memory_preview)
            compass_memory_preview["ts_iso"] = accepted_at
            project_brief_record_text = compiled_project_brief_record_text(
                project_brief_record_text,
                accepted_at=accepted_at,
            )
        project_dashboard_preview = preview_project_dashboard_payload(
            root=root,
            proposal=package_proposal,
            accepted_project_preview=accepted_project_preview,
            source_launch_context=next_steps_preview,
        )
        transaction_seal = greenfield_prewrite_transaction_seal.seal_staged_greenfield_create(
            greenfield_prewrite_transaction_seal.GreenfieldPrewriteSealRequest(
                prewrite_root=prewrite_root,
                target_root=root,
                proposal=package_proposal,
                validation_gate=validation_gate,
                staged_backlog_result=staged_backlog_result,
                target_backlog_result=backlog_result,
                staged_component_registry_preview=staged_component_registry_preview,
                rendered_component_specs=rendered_component_specs,
                diagram_rows=diagram_rows,
                diagram_ids=diagram_ids,
                staged_traceability_plan=staged_traceability_plan,
                rendered_atlas_sources=rendered_atlas_sources,
                atlas_review_date=atlas_review_date,
                compiled_atlas_catalog_rows=atlas_catalog_rows,
                accepted_project_preview=accepted_project_preview,
                project_brief_record_text=project_brief_record_text,
                compass_memory_preview=compass_memory_preview,
                next_steps_preview=next_steps_preview,
                staged_program_result=staged_program_result,
                prewrite_safety_preview=prewrite_safety_preview,
                staged_release_bootstrap=staged_release_bootstrap,
                staged_release_targeting=staged_release_targeting,
                brand_asset_count=len(brand_asset_writes),
            )
        )
        package = GreenfieldCompletionPackage(
            proposal=package_proposal,
            release_selector=release_selector,
            rendered_component_specs=rendered_component_specs,
            rendered_atlas_sources=rendered_atlas_sources,
            atlas_review_date=atlas_review_date,
            atlas_diagram_ids=tuple(diagram_ids),
            atlas_catalog_rows=atlas_catalog_rows,
            component_registry_preview=component_registry_preview,
            project_brief_preview=project_brief,
            project_brief_record_text=project_brief_record_text,
            tribunal_preview=validation_gate,
            accepted_project_preview=accepted_project_preview,
            project_dashboard_preview=project_dashboard_preview,
            compass_memory_preview=compass_memory_preview,
            next_steps_preview=next_steps_preview,
            backlog_result=backlog_result,
            program_result=preview_program_result,
            traceability_plan=traceability_plan,
            baseline_writes=baseline_writes,
            brand_asset_writes=brand_asset_writes,
            prewrite_safety_preview=prewrite_safety_preview,
            surface_refresh_preview=transaction_seal.surface_refresh_preview,
            release_target_result=preview_release_target,
            release_assignment_result=preview_release_assignment,
            release_workstream_ids=tuple(first_release_workstreams),
            repository_write_set=transaction_seal.repository_write_set,
            commit_result_preview=transaction_seal.commit_result_preview,
        )
        package = greenfield_source_casing.package_with_source_casing(package)
        source_cased_seal = greenfield_prewrite_transaction_seal.seal_staged_greenfield_create(
            greenfield_prewrite_transaction_seal.GreenfieldPrewriteSealRequest(
                prewrite_root=prewrite_root,
                target_root=root,
                proposal=package.proposal,
                validation_gate=package.tribunal_preview,
                staged_backlog_result=staged_backlog_result,
                target_backlog_result=package.backlog_result,
                staged_component_registry_preview=package.component_registry_preview,
                rendered_component_specs=package.rendered_component_specs,
                diagram_rows=diagram_rows,
                diagram_ids=package.atlas_diagram_ids,
                staged_traceability_plan=staged_traceability_plan,
                rendered_atlas_sources=package.rendered_atlas_sources,
                atlas_review_date=package.atlas_review_date,
                compiled_atlas_catalog_rows=package.atlas_catalog_rows,
                accepted_project_preview=package.accepted_project_preview,
                project_brief_record_text=package.project_brief_record_text,
                compass_memory_preview=package.compass_memory_preview,
                next_steps_preview=package.next_steps_preview,
                staged_program_result=package.program_result,
                prewrite_safety_preview=package.prewrite_safety_preview,
                staged_release_bootstrap=staged_release_bootstrap,
                staged_release_targeting={
                    **dict(package.release_assignment_result or {}),
                    "workstream_ids": list(package.release_workstream_ids),
                },
                brand_asset_count=len(brand_asset_writes),
            )
        )
        package = replace(
            package,
            surface_refresh_preview=source_cased_seal.surface_refresh_preview,
            repository_write_set=source_cased_seal.repository_write_set,
            commit_result_preview=source_cased_seal.commit_result_preview,
        )
        return GreenfieldPrewriteBuild(
            backlog_result=package.backlog_result or backlog_result,
            package=package,
        )


def prewrite_safety_evidence(
    *,
    validation_gate: Mapping[str, Any],
    program_result: Mapping[str, Any] | None,
    release_target_result: Mapping[str, Any] | None,
    release_assignment_result: Mapping[str, Any] | None,
    release_selector: str,
) -> dict[str, Any]:
    """Return explicit prewrite proof before final governed writes run."""

    program = dict(program_result or {})
    release_target = dict(release_target_result or {})
    release_assignment = dict(release_assignment_result or {})
    selector = str(release_selector or "").strip()
    checks = {
        "program_dry_run": bool(program.get("created")) and bool(program.get("dry_run")),
        "validation_gate_passed": str(validation_gate.get("status", "")).strip().casefold() == "passed",
        "release_target_dry_run": not selector or bool(release_target.get("dry_run")),
        "release_assignment_dry_run": not selector or bool(release_assignment.get("dry_run")),
    }
    return {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "program": _safety_evidence_subset(program, keys=("created", "dry_run", "umbrella_id", "program_path")),
        "release_target": _safety_evidence_subset(release_target, keys=("dry_run", "release_id", "selector")),
        "release_assignment": _safety_evidence_subset(
            release_assignment,
            keys=("dry_run", "selector", "workstream_ids", "release_id"),
        ),
    }


def _safety_evidence_subset(source: Mapping[str, Any], *, keys: Sequence[str]) -> dict[str, Any]:
    return {key: source[key] for key in keys if key in source}


def proposal_with_component_brief_gate(proposal: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(proposal)
    labels = [
        str(row.get("label", "")).strip()
        for row in greenfield_apply_components.first_release_component_rows(result)
        if str(row.get("label", "")).strip()
    ]
    if not labels:
        return result
    brief = dict(result.get("project_brief")) if isinstance(result.get("project_brief"), Mapping) else {}
    gates = [str(item).strip() for item in brief.get("coding_readiness_gates", []) if str(item).strip()] if isinstance(brief.get("coding_readiness_gates"), list) else []
    summary = ", ".join(labels)
    gate = f"The first-release components come from product systems named in the accepted product direction: {summary}."
    replaced = False
    updated: list[str] = []
    for item in gates:
        if "components come from product systems named in the accepted product direction" in item.casefold():
            updated.append(gate)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(gate)
    brief["coding_readiness_gates"] = updated
    result["project_brief"] = brief
    return result


def remap_prewrite_backlog_result(
    backlog_result: Mapping[str, Any],
    *,
    source_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    """Convert staged Radar render paths into target-repo paths before writes."""

    staged_root = Path(source_root).expanduser().resolve()
    real_root = Path(target_root).expanduser().resolve()
    remapped: dict[str, Any] = dict(backlog_result)
    remapped["created"] = [
        _remap_created_backlog_item(row, source_root=staged_root, target_root=real_root)
        for row in mapping_rows(backlog_result.get("created"))
    ]
    remapped["backlog_index"] = _remap_path_text(backlog_result.get("backlog_index"), source_root=staged_root, target_root=real_root)
    remapped["idea_files"] = _remap_text_by_path(backlog_result.get("idea_files"), source_root=staged_root, target_root=real_root)
    remapped["existing_idea_files"] = _remap_text_by_path(
        backlog_result.get("existing_idea_files"),
        source_root=staged_root,
        target_root=real_root,
    )
    remapped["stale_idea_files"] = [
        _remap_path_text(path, source_root=staged_root, target_root=real_root)
        for path in backlog_result.get("stale_idea_files", [])
        if str(path).strip()
    ]
    remapped["stale_idea_ids"] = [str(value).strip().upper() for value in backlog_result.get("stale_idea_ids", []) if str(value).strip()]
    remapped["_candidate_idea_specs"] = _remap_candidate_idea_specs(
        backlog_result.get("_candidate_idea_specs"),
        source_root=staged_root,
        target_root=real_root,
    )
    return remapped


def materialize_prewrite_backlog_result(backlog_result: Mapping[str, Any]) -> None:
    """Write in-memory Radar previews into the staged repo for enrichment passes."""

    index_path = str(backlog_result.get("backlog_index", "")).strip()
    index_text = str(backlog_result.get("backlog_index_text", "") or "")
    if index_path and index_text:
        atomic_write_text(Path(index_path).expanduser().resolve(), index_text, encoding="utf-8")
    for raw_path, text in _as_mapping(backlog_result.get("idea_files")).items():
        path = Path(str(raw_path)).expanduser().resolve()
        if str(path):
            atomic_write_text(path, str(text or ""), encoding="utf-8")


def _as_mapping(value: Any) -> Mapping[Any, Any]:
    return value if isinstance(value, Mapping) else {}


def refresh_prewrite_backlog_result(backlog_result: Mapping[str, Any]) -> dict[str, Any]:
    """Reload staged Radar files after traceability enrichment mutates them."""

    refreshed: dict[str, Any] = dict(backlog_result)
    idea_files: dict[str, str] = {}
    candidate_specs = (
        dict(refreshed.get("_candidate_idea_specs"))
        if isinstance(refreshed.get("_candidate_idea_specs"), Mapping)
        else {}
    )
    for row in mapping_rows(refreshed.get("created")):
        path_text = str(row.get("idea_path", "")).strip()
        if not path_text:
            continue
        path = Path(path_text).expanduser().resolve()
        if not path.exists():
            continue
        idea_files[str(path)] = path.read_text(encoding="utf-8")
        metadata, sections = backlog_authoring._parse_metadata_and_sections(path)
        idea_id = str(metadata.get("idea_id", "")).strip().upper()
        if idea_id:
            candidate_specs[idea_id] = backlog_contract.IdeaSpec(
                path=path,
                metadata=metadata,
                sections=set(sections),
                section_bodies=dict(sections),
            )
    if idea_files:
        refreshed["idea_files"] = idea_files
    if candidate_specs:
        refreshed["_candidate_idea_specs"] = candidate_specs
    return refreshed


def remap_prewrite_component_items(
    component_items: Sequence[Mapping[str, Any]],
    *,
    source_root: Path,
    target_root: Path,
) -> tuple[dict[str, Any], ...]:
    """Convert staged Registry preview paths into target-repo paths before gates."""

    staged_root = Path(source_root).expanduser().resolve()
    real_root = Path(target_root).expanduser().resolve()
    return tuple(
        _remap_component_item(row, source_root=staged_root, target_root=real_root)
        for row in component_items
        if isinstance(row, Mapping)
    )


def release_id_for_proposal(proposal: Mapping[str, Any], *, selector: str) -> str:
    """Resolve a stable release id for confirmed greenfield release targeting."""

    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_id = str(release_plan.get("provisional_release_id", "")).strip()
    if release_id:
        return slugify(release_id)
    if selector:
        return slugify(f"release-{selector}")
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    project_slug = slugify(str(intent.get("project_slug", "")).strip() or str(intent.get("title", "")).strip())
    return slugify(f"release-{project_slug}-first") if project_slug else "release-greenfield-first"


def ensure_release_target(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    selector: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create or preview the release selector needed by confirmed greenfield apply."""

    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip() or "Greenfield Project"
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    version, tag = greenfield_programs.semver_release_metadata(selector=selector, release_plan=release_plan)
    registry_path = release_planning_contract.releases_registry_path(repo_root=repo_root)
    registry_document, _errors = release_planning_contract.load_registry_document(path=registry_path)
    aliases = dict(registry_document.get("aliases", {})) if isinstance(registry_document.get("aliases"), Mapping) else {}
    release_aliases = [selector]
    if release_planning_contract.canonical_alias_token("current") not in aliases:
        release_aliases.append("current")
    release_name = greenfield_programs.compact_release_target_label(version or selector)
    return release_planning_authoring.ensure_release_selector(
        repo_root=repo_root,
        selector=selector,
        release_id=release_id_for_proposal(proposal, selector=selector),
        status="planning",
        version=version,
        tag=tag,
        name=release_name,
        notes=f"Greenfield release plan for {title}; created only after proposal confirmation.",
        aliases=tuple(release_aliases),
        dry_run=dry_run,
    )


def preview_accepted_project_memory(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    component_items: Sequence[Mapping[str, Any]],
    release_selector: str,
    release_target_result: Mapping[str, Any] | None,
    release_assignment_result: Mapping[str, Any] | None,
    validation_gate: Mapping[str, Any] | None,
    source_launch_context: Mapping[str, Any] | None = None,
    accepted_at: str = "prewrite",
) -> dict[str, Any]:
    """Build the accepted-project memory record before target writes begin."""

    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    return build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=mapping_rows(backlog_result.get("created")),
        component_items=tuple(row for row in component_items if isinstance(row, Mapping)),
        diagram_ids=greenfield_apply_diagrams.allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows),
        release_selector=release_selector,
        release_id=_prewrite_release_id(release_target_result, release_assignment_result),
        validation_gate=validation_gate,
        source_launch_context=source_launch_context,
        accepted_at=accepted_at,
        repo_root=root,
    )


def preview_project_dashboard_payload(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    accepted_project_preview: Mapping[str, Any],
    source_launch_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the accepted Project tab preview before target writes begin."""

    dashboard_proposal = dict(proposal)
    dashboard_proposal["_accepted_project"] = {
        "accepted_at": str(accepted_project_preview.get("accepted_at") or "prewrite"),
        "origin": str(accepted_project_preview.get("origin") or "greenfield"),
        "evidence_tier": str(accepted_project_preview.get("evidence_tier") or "user_intent"),
        "created": dict(accepted_project_preview.get("created") or {})
        if isinstance(accepted_project_preview.get("created"), Mapping)
        else {},
        "source_path": "odylith/runtime/source/accepted-project.v1.json",
        "validation_gate": dict(accepted_project_preview.get("validation_gate") or {})
        if isinstance(accepted_project_preview.get("validation_gate"), Mapping)
        else {},
    }
    dashboard_proposal["_source_launch"] = (
        dict(source_launch_context)
        if isinstance(source_launch_context, Mapping)
        else dict(accepted_project_preview.get("source_launch") or {})
        if isinstance(accepted_project_preview.get("source_launch"), Mapping)
        else {}
    )
    return build_greenfield_payload(proposal=dashboard_proposal, repo_root=root)


def preview_compass_acceptance_event(
    *,
    root: Path,
    target_root: Path | None = None,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    component_items: Sequence[Mapping[str, Any]],
    release_selector: str,
    release_target_result: Mapping[str, Any] | None,
    release_assignment_result: Mapping[str, Any] | None,
    accepted_at: str = "prewrite",
) -> dict[str, Any]:
    """Build the Compass acceptance event before the target stream is appended."""

    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    return build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=mapping_rows(backlog_result.get("created")),
        component_items=tuple(row for row in component_items if isinstance(row, Mapping)),
        diagram_ids=greenfield_apply_diagrams.allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows),
        release_selector=release_selector,
        release_id=_prewrite_release_id(release_target_result, release_assignment_result),
        accepted_at=accepted_at,
        repo_root=target_root or root,
    )


def _compiled_acceptance_timestamp() -> str:
    return dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def _prewrite_release_id(*sources: Mapping[str, Any] | None) -> str:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for value in (source.get("release_id"), (source.get("release") or {}).get("release_id") if isinstance(source.get("release"), Mapping) else ""):
            text = str(value or "").strip()
            if text:
                return text
    return "none"


def _remap_created_backlog_item(
    row: Mapping[str, Any],
    *,
    source_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    updated = dict(row)
    if str(updated.get("idea_path", "")).strip():
        updated["idea_path"] = _remap_path_text(updated.get("idea_path"), source_root=source_root, target_root=target_root)
    return updated


def _remap_component_item(
    row: Mapping[str, Any],
    *,
    source_root: Path,
    target_root: Path,
) -> dict[str, Any]:
    updated = dict(row)
    for key in ("registry_path", "spec_path"):
        if str(updated.get(key, "")).strip():
            remapped = _remap_path_text(updated.get(key), source_root=source_root, target_root=target_root)
            updated[key] = _target_relative_path_text(remapped, target_root=target_root)
    return updated


def _remap_text_by_path(value: Any, *, source_root: Path, target_root: Path) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {
        _remap_path_text(path, source_root=source_root, target_root=target_root): str(text)
        for path, text in value.items()
        if str(path).strip()
    }


def _remap_candidate_idea_specs(value: Any, *, source_root: Path, target_root: Path) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    remapped: dict[str, Any] = {}
    for key, spec in value.items():
        path = getattr(spec, "path", None)
        if not isinstance(path, Path):
            remapped[str(key)] = spec
            continue
        remapped[str(key)] = type(spec)(
            path=Path(_remap_path_text(path, source_root=source_root, target_root=target_root)),
            metadata=dict(getattr(spec, "metadata", {}) or {}),
            sections=set(getattr(spec, "sections", set()) or set()),
            section_bodies=dict(getattr(spec, "section_bodies", {}) or {}),
        )
    return remapped


def _remap_path_text(value: Any, *, source_root: Path, target_root: Path) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    path = Path(raw).expanduser()
    if not path.is_absolute():
        return raw
    try:
        relative = path.resolve().relative_to(source_root)
    except ValueError:
        return str(path.resolve())
    return str((target_root / relative).resolve())


def _target_relative_path_text(value: Any, *, target_root: Path) -> str:
    """Keep compiled component links portable without accepting foreign roots."""

    raw = str(value or "").strip()
    path = Path(raw).expanduser()
    if not raw or not path.is_absolute():
        return raw
    try:
        return str(path.resolve(strict=False).relative_to(target_root.resolve(strict=False)))
    except ValueError:
        return raw


__all__ = [
    "accepted_greenfield_workstream_ids",
    "ensure_greenfield_create_baseline",
    "ensure_release_target",
    "mark_previous_greenfield_workstreams_stale",
    "remove_prewrite_stale_idea_files",
    "remove_stale_workstream_artifacts",
    "preview_accepted_project_memory",
    "preview_compass_acceptance_event",
    "preview_project_dashboard_payload",
    "prewrite_safety_evidence",
    "remap_prewrite_backlog_result",
    "staged_greenfield_prewrite_root",
]
