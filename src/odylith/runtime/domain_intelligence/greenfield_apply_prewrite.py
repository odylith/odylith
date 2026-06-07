"""Prewrite package assembly for confirmed greenfield creation."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import shutil
import tempfile
from pathlib import Path
from typing import Any

from odylith.install.bootstrap_assets import customer_backlog_index_source
from odylith.install.bootstrap_assets import customer_diagram_catalog_source
from odylith.install.bootstrap_assets import customer_plan_index_source
from odylith.install.fs import atomic_write_text
from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.proposal_memory import build_greenfield_acceptance_event_preview
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import validate_backlog_contract as backlog_contract
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import release_planning_contract


@dataclass(frozen=True)
class GreenfieldPrewriteBuild:
    package: GreenfieldCompletionPackage
    backlog_result: Mapping[str, Any]


def ensure_greenfield_create_baseline(root: Path) -> None:
    """Create missing governance indexes needed by the confirmed-create refresh path."""

    paths = (
        root / "odylith/radar/source/ideas",
        root / "odylith/technical-plans/in-progress",
        root / "odylith/technical-plans/done",
        root / "odylith/technical-plans/parked",
        root / "odylith/atlas/source/catalog",
        root / "odylith/registry/source/components",
    )
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
    backlog_index = root / "odylith/radar/source/INDEX.md"
    if not backlog_index.exists():
        atomic_write_text(backlog_index, customer_backlog_index_source(repo_root=root), encoding="utf-8")
    plan_index = root / "odylith/technical-plans/INDEX.md"
    if not plan_index.exists():
        atomic_write_text(plan_index, customer_plan_index_source(), encoding="utf-8")
    diagram_catalog = root / "odylith/atlas/source/catalog/diagrams.v1.json"
    if not diagram_catalog.exists():
        atomic_write_text(diagram_catalog, customer_diagram_catalog_source(), encoding="utf-8")


@contextmanager
def staged_greenfield_prewrite_root(root: Path) -> Iterator[Path]:
    """Stage governed inputs so completion gates can run without target writes."""

    source_root = Path(root).expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="odylith-greenfield-prewrite-") as tmp:
        stage_root = (Path(tmp) / "repo").resolve()
        stage_root.mkdir(parents=True, exist_ok=True)
        for token in _PREWRITE_STAGE_PATHS:
            _copy_existing_path(source_root / token, stage_root / token)
        ensure_greenfield_create_baseline(stage_root)
        yield stage_root


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

    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    with staged_greenfield_prewrite_root(root) as prewrite_root:
        staged_backlog_result = backlog_authoring.create_queued_backlog_items(
            repo_root=prewrite_root,
            backlog_index_path=prewrite_root / "odylith/radar/source/INDEX.md",
            ideas_root=prewrite_root / "odylith/radar/source/ideas",
            titles=[str(row.get("title", "")).strip() for row in backlog_rows if str(row.get("title", "")).strip()],
            args=backlog_args,
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
        component_registry_preview = remap_prewrite_component_items(
            greenfield_apply_components.preview_prewrite_components(
                root=prewrite_root,
                proposal=proposal,
                release_selector=release_selector,
                backlog_result=staged_backlog_result,
                program_result=preview_program_result,
            ),
            source_root=prewrite_root,
            target_root=root,
        )
        rendered_atlas_sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal)
        materialize_prewrite_backlog_result(staged_backlog_result)
        diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
        diagram_ids = greenfield_apply_diagrams.allocated_diagram_ids(prewrite_root, len(diagram_rows), rows=diagram_rows)
        traceability_plan = greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=staged_backlog_result["created"],
            diagram_ids=diagram_ids,
        )
        greenfield_traceability.apply_backlog_traceability(
            repo_root=prewrite_root,
            proposal=proposal,
            plan=traceability_plan,
        )
        staged_backlog_result = refresh_prewrite_backlog_result(staged_backlog_result)
        backlog_result = remap_prewrite_backlog_result(
            staged_backlog_result,
            source_root=prewrite_root,
            target_root=root,
        )
        first_release_workstreams = greenfield_programs.first_release_workstream_ids(
            proposal=proposal,
            created_backlog=backlog_result["created"],
            program_result=preview_program_result,
        )
        preview_release_target = None
        preview_release_assignment = None
        if release_selector:
            preview_release_target = ensure_release_target(
                repo_root=prewrite_root,
                proposal=proposal,
                selector=release_selector,
                dry_run=True,
            )
            ensure_release_target(
                repo_root=prewrite_root,
                proposal=proposal,
                selector=release_selector,
                dry_run=False,
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
        accepted_project_preview = preview_accepted_project_memory(
            root=prewrite_root,
            proposal=proposal,
            backlog_result=backlog_result,
            component_items=component_registry_preview,
            release_selector=release_selector,
            release_target_result=preview_release_target,
            release_assignment_result=preview_release_assignment,
            validation_gate=validation_gate,
        )
        compass_memory_preview = preview_compass_acceptance_event(
            root=prewrite_root,
            proposal=proposal,
            backlog_result=backlog_result,
            component_items=component_registry_preview,
            release_selector=release_selector,
            release_target_result=preview_release_target,
            release_assignment_result=preview_release_assignment,
        )
        next_steps_preview = greenfield_experience.build_next_steps(
            proposal=proposal,
            backlog_result=backlog_result,
            first_release_workstreams=first_release_workstreams,
            program_result=preview_program_result,
            release_selector=release_selector,
        )
        project_brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
        return GreenfieldPrewriteBuild(
            backlog_result=backlog_result,
            package=GreenfieldCompletionPackage(
                proposal=proposal,
                release_selector=release_selector,
                rendered_component_specs=rendered_component_specs,
                rendered_atlas_sources=rendered_atlas_sources,
                component_registry_preview=component_registry_preview,
                project_brief_preview=project_brief,
                tribunal_preview=validation_gate,
                accepted_project_preview=accepted_project_preview,
                compass_memory_preview=compass_memory_preview,
                next_steps_preview=next_steps_preview,
                backlog_result=backlog_result,
                program_result=preview_program_result,
                release_target_result=preview_release_target,
                release_assignment_result=preview_release_assignment,
                release_workstream_ids=tuple(first_release_workstreams),
            ),
        )


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
        accepted_at="prewrite",
    )


def preview_compass_acceptance_event(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
    component_items: Sequence[Mapping[str, Any]],
    release_selector: str,
    release_target_result: Mapping[str, Any] | None,
    release_assignment_result: Mapping[str, Any] | None,
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
    )


def _prewrite_release_id(*sources: Mapping[str, Any] | None) -> str:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for value in (source.get("release_id"), (source.get("release") or {}).get("release_id") if isinstance(source.get("release"), Mapping) else ""):
            text = str(value or "").strip()
            if text:
                return text
    return "none"


_PREWRITE_STAGE_PATHS = (
    Path("odylith/radar"),
    Path("odylith/technical-plans"),
    Path("odylith/atlas"),
)


def _copy_existing_path(source: Path, target: Path) -> None:
    if not source.exists() and not source.is_symlink():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(source.readlink())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


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
            updated[key] = _remap_path_text(updated.get(key), source_root=source_root, target_root=target_root)
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


__all__ = [
    "ensure_greenfield_create_baseline",
    "ensure_release_target",
    "preview_accepted_project_memory",
    "preview_compass_acceptance_event",
    "remap_prewrite_backlog_result",
    "staged_greenfield_prewrite_root",
]
