"""Prewrite package assembly for confirmed greenfield creation."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from odylith.install.bootstrap_assets import customer_backlog_index_source
from odylith.install.bootstrap_assets import customer_diagram_catalog_source
from odylith.install.bootstrap_assets import customer_plan_index_source
from odylith.install.fs import atomic_write_text
from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_component_registry_scope
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.proposal_memory import build_greenfield_acceptance_event_preview
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.governance.component_spec_rendering import build_component_spec


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
        rendered_component_specs = render_prewrite_component_specs(
            root=prewrite_root,
            proposal=proposal,
            release_selector=release_selector,
            backlog_result=staged_backlog_result,
            program_result=preview_program_result,
        )
        component_registry_preview = remap_prewrite_component_items(
            preview_prewrite_components(
                root=prewrite_root,
                proposal=proposal,
                release_selector=release_selector,
                backlog_result=staged_backlog_result,
                program_result=preview_program_result,
            ),
            source_root=prewrite_root,
            target_root=root,
        )
        rendered_atlas_sources = render_prewrite_atlas_sources(proposal)
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
        for row in _mapping_rows(backlog_result.get("created"))
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


def allocated_diagram_ids(
    repo_root: Path,
    count: int,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[str]:
    """Allocate stable diagram ids while preserving existing catalog slug ids."""

    slug_ids = _catalog_diagram_ids_by_slug(repo_root)
    if rows is None:
        rows = ()
    first = int(_next_diagram_id(repo_root).split("-", 1)[1])
    next_number = first
    used = set(slug_ids.values())
    allocated: list[str] = []
    for index in range(max(0, count)):
        row = rows[index] if index < len(rows) else {}
        slug = str(row.get("slug", "")).strip() if isinstance(row, Mapping) else ""
        existing = slug_ids.get(slug)
        if existing:
            allocated.append(existing)
            continue
        while f"D-{next_number:03d}" in used:
            next_number += 1
        diagram_id = f"D-{next_number:03d}"
        used.add(diagram_id)
        allocated.append(diagram_id)
        next_number += 1
    return allocated


def render_prewrite_component_specs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
) -> dict[str, str]:
    """Render Registry specs in memory for the post-confirm completion gate."""

    specs: dict[str, str] = {}
    for row in component_authoring_prewrite_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
        program_result=program_result,
    ):
        specs[str(row["label"])] = build_component_spec(
            component_id=str(row["component_id"]),
            label=str(row["label"]),
            path=str(row["path"]),
            kind=str(row["kind"]),
            status=str(row["status"]),
            qualification=str(row["qualification"]),
            sources=tuple(str(item) for item in row["sources"]),
            workstreams=tuple(str(item) for item in row["workstreams"]),
            diagrams=tuple(str(item) for item in row["diagrams"]),
            responsibility=str(row["responsibility"]),
            boundary=str(row["boundary"]),
            dependencies=tuple(str(item) for item in row["dependencies"]),
            interfaces=tuple(str(item) for item in row["interfaces"]),
            validation=tuple(str(item) for item in row["validation"]),
            risks=tuple(str(item) for item in row["risks"]),
            implementation_handoff=row["implementation_handoff"] if isinstance(row["implementation_handoff"], Mapping) else None,
            component_contract=row["component_contract"] if isinstance(row["component_contract"], Mapping) else None,
        )
    return specs


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


def preview_prewrite_components(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Run component authoring Tribunal checks before target writes begin."""

    preview_rows: list[dict[str, Any]] = []
    for row in component_authoring_prewrite_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
        program_result=program_result,
    ):
        created = component_authoring.register_component(
            repo_root=root,
            component_id=str(row["component_id"]),
            label=str(row["label"]),
            path=str(row["path"]),
            kind=str(row["kind"]),
            category="application",
            qualification=str(row["qualification"]),
            owner="repo",
            status=str(row["status"]),
            product_layer="application",
            sources=tuple(str(item) for item in row["sources"]),
            workstreams=tuple(str(item) for item in row["workstreams"]),
            diagrams=tuple(str(item) for item in row["diagrams"]),
            responsibility=str(row["responsibility"]),
            boundary=str(row["boundary"]),
            dependencies=tuple(str(item) for item in row["dependencies"]),
            interfaces=tuple(str(item) for item in row["interfaces"]),
            validation=tuple(str(item) for item in row["validation"]),
            risks=tuple(str(item) for item in row["risks"]),
            implementation_handoff=row["implementation_handoff"] if isinstance(row["implementation_handoff"], Mapping) else None,
            component_contract=row["component_contract"] if isinstance(row["component_contract"], Mapping) else None,
            dry_run=True,
            update_existing=True,
            refresh=False,
        )
        created_payload = created.as_dict()
        created_payload["what_it_is"] = component_authoring._public_what_it_is(  # noqa: SLF001 - prewrite mirrors component_authoring output.
            label=str(row["label"]),
            kind=str(row["kind"]),
            responsibility=str(row["responsibility"]),
        )
        preview_rows.append(created_payload)
    return tuple(preview_rows)


def component_authoring_prewrite_inputs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
    program_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    first_release_workstreams = greenfield_programs.first_release_workstream_ids(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        program_result=program_result,
    )
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    diagram_ids = allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
    traceability_plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        diagram_ids=diagram_ids,
    )
    component_handoffs = greenfield_experience.build_component_handoffs(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=first_release_workstreams,
        program_result=program_result,
        traceability_plan=traceability_plan,
        release_selector=release_selector,
    )
    component_diagram_scope = greenfield_component_registry_scope.build_component_diagram_scope(
        rows=diagram_rows,
        diagram_ids=diagram_ids,
    )
    component_rows = first_release_component_rows(proposal)
    component_dependency_lookup = component_dependency_lookup_for(component_rows)
    inputs: list[dict[str, Any]] = []
    for row in component_rows:
        key = greenfield_traceability.component_key(row)
        handoff = component_handoffs.get(key, {})
        label = str(row.get("label", "") or row.get("component_id", "")).strip()
        if not label:
            continue
        inputs.append(
            {
                "component_id": str(row.get("component_id", "")).strip(),
                "label": label,
                "path": str(row.get("intended_path", "")).strip(),
                "kind": str(row.get("kind", "service")).strip() or "service",
                "status": str(row.get("status", "planned")).strip() or "planned",
                "qualification": str(row.get("qualification", "candidate")).strip() or "candidate",
                "sources": ("user_intent",),
                "workstreams": greenfield_component_registry_scope.registry_component_workstreams(
                    handoff=handoff,
                    fallback=traceability_plan.component_workstreams.get(key, ()),
                ),
                "diagrams": greenfield_component_registry_scope.registry_component_diagrams(
                    row=row,
                    diagram_scope=component_diagram_scope,
                    fallback=traceability_plan.component_diagrams.get(key, ()),
                ),
                "responsibility": str(row.get("responsibility", "")).strip(),
                "boundary": str(row.get("boundary", "")).strip(),
                "dependencies": component_dependency_lines(
                    row_text_tuple(row, "dependencies", "depends_on"),
                    lookup=component_dependency_lookup,
                ),
                "interfaces": row_text_tuple(row, "interfaces", "interface_changes"),
                "validation": row_text_tuple(row, "validation", "test_strategy"),
                "risks": component_risk_lines(row, proposal),
                "implementation_handoff": handoff,
                "component_contract": row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else None,
            }
        )
    return tuple(inputs)


def render_prewrite_atlas_sources(proposal: Mapping[str, Any]) -> dict[str, str]:
    """Render Atlas Mermaid source files in memory for the completion gate."""

    sources: dict[str, str] = {}
    for row in proposal.get("diagrams", []):
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug", "")).strip() or slugify(str(row.get("title", "")).strip())
        if not slug:
            continue
        sources[f"odylith/atlas/source/{slug}.mmd"] = validated_mermaid_source(row).rstrip() + "\n"
    return sources


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
        backlog_items=_mapping_rows(backlog_result.get("created")),
        component_items=tuple(row for row in component_items if isinstance(row, Mapping)),
        diagram_ids=allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows),
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
        backlog_items=_mapping_rows(backlog_result.get("created")),
        component_items=tuple(row for row in component_items if isinstance(row, Mapping)),
        diagram_ids=allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows),
        release_selector=release_selector,
        release_id=_prewrite_release_id(release_target_result, release_assignment_result),
    )


def first_release_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the component rows eligible for first-release rendering."""

    raw_rows = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    rows = [row for row in raw_rows if is_first_release_component(row)]
    return rows or [row for row in active_release_components(raw_rows)]


def is_first_release_component(row: Mapping[str, Any]) -> bool:
    return str(row.get("release_scope", "")).strip().casefold() not in {"deferred", "out_of_scope", "external"}


def component_dependency_lookup_for(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    lookup: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        for value in (row.get("component_id"), row.get("id"), row.get("label"), row.get("name")):
            key = slugify(str(value or ""))
            if key:
                lookup.setdefault(key, row)
    return lookup


def component_dependency_lines(
    values: Sequence[str],
    *,
    lookup: Mapping[str, Mapping[str, Any]],
) -> tuple[str, ...]:
    rows: list[str] = []
    for value in values:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            continue
        dependency = lookup.get(slugify(text))
        if not dependency:
            rows.append(text)
            continue
        label = str(dependency.get("label") or dependency.get("name") or text).strip()
        responsibility = str(dependency.get("responsibility") or dependency.get("boundary") or "").strip()
        if responsibility:
            rows.append(f"Depends on {label} for {_dependency_responsibility_phrase(responsibility)}")
        else:
            rows.append(f"Depends on {label} for the state, behavior, or proof owned by that boundary")
    return unique_text(rows)


def component_risk_lines(row: Mapping[str, Any], _proposal: Mapping[str, Any]) -> tuple[str, ...]:
    local = unique_text(
        [
            *_posture_lines(row, "risks", "domain_risk", "risk_posture"),
            *_posture_lines(row, "security_posture", "security_compliance", "compliance_posture"),
            *_posture_lines(row, "dependency_expectations"),
        ]
    )
    label = str(row.get("label", "") or row.get("component_id", "") or "Component").strip()
    values = list(local)
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_RISK_TOKENS):
        values.append(_component_operational_risk(row=row, label=label))
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_SECURITY_TOKENS):
        values.append(_component_security_posture(row=row, label=label))
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_POLICY_TOKENS):
        values.append(_component_policy_posture(row=row, label=label))
    return unique_text(values)


def _next_diagram_id(repo_root: Path) -> str:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    max_id = 0
    if catalog.is_file():
        try:
            payload = json.loads(catalog.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        for row in payload.get("diagrams", []) if isinstance(payload, Mapping) else []:
            match = re.fullmatch(r"D-(\d{3,})", str(row.get("diagram_id", "")).strip())
            if match:
                max_id = max(max_id, int(match.group(1)))
    return f"D-{max_id + 1:03d}"


def _catalog_diagram_ids_by_slug(repo_root: Path) -> dict[str, str]:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog.is_file():
        return {}
    try:
        payload = json.loads(catalog.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return {}
    result: dict[str, str] = {}
    for row in diagrams:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug", "")).strip()
        diagram_id = str(row.get("diagram_id", "")).strip()
        if slug and re.fullmatch(r"D-\d{3,}", diagram_id):
            result.setdefault(slug, diagram_id)
    return result


def _prewrite_release_id(*sources: Mapping[str, Any] | None) -> str:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for value in (source.get("release_id"), (source.get("release") or {}).get("release_id") if isinstance(source.get("release"), Mapping) else ""):
            text = str(value or "").strip()
            if text:
                return text
    return "none"


def _component_posture_text(*, row: Mapping[str, Any], risk_lines: Sequence[str]) -> str:
    values = [
        *risk_lines,
        *row_text_tuple(row, "responsibility"),
        *row_text_tuple(row, "boundary"),
        *row_text_tuple(row, "dependencies", "depends_on"),
        *row_text_tuple(row, "interfaces", "interface_changes"),
        *row_text_tuple(row, "validation", "test_strategy"),
    ]
    return " ".join(values).casefold()


def _has_component_posture(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def _component_operational_risk(*, row: Mapping[str, Any], label: str) -> str:
    boundary = str(row.get("boundary", "") or row.get("responsibility", "")).strip()
    boundary_hint = f" its stated boundary ({boundary})" if boundary else " its stated component boundary"
    return f"Operational risk: {label} must not expand beyond{boundary_hint} without owner review and source-backed proof."


def _component_security_posture(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    if kind in {"tooling", "test", "harness"}:
        return (
            f"Security posture: {label} uses secret-free fixtures, rejects production credentials, "
            "and keeps live network access outside its proof boundary."
        )
    if kind in {"application", "ui", "frontend", "web"}:
        return (
            f"Security posture: {label} gates operator access and audit identity at its own visible action boundary."
        )
    return (
        f"Security posture: {label} keeps authorization, data access, and ownership checks at its API or module boundary."
    )


def _component_policy_posture(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    if kind in {"tooling", "test", "harness"}:
        return (
            f"Compliance policy: {label} records deterministic audit evidence and rejects private production data in fixtures."
        )
    if kind in {"application", "ui", "frontend", "web"}:
        return (
            f"Policy posture: {label} preserves accessibility, privacy, audit, and safety semantics for the visible states it owns."
        )
    return (
        f"Compliance policy: {label} keeps audit, privacy, retention, and safety assumptions explicit in its contract tests."
    )


def _dependency_responsibility_phrase(value: str) -> str:
    text = " ".join(str(value or "").split()).strip().rstrip(".")
    if not text:
        return "the state, behavior, or proof owned by that boundary"
    parts = [
        _dependency_clause_phrase(part)
        for part in re.split(r"\s*;\s*", text)
        if part.strip()
    ]
    parts = [part for part in parts if part]
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


def _dependency_clause_phrase(value: str) -> str:
    text = " ".join(str(value or "").split()).strip().rstrip(".")
    if not text:
        return ""
    head, separator, tail = text.partition(" ")
    verb = head.strip(",:;").casefold()
    gerunds = {
        "assemble": "assembling",
        "assembles": "assembling",
        "bind": "binding",
        "binds": "binding",
        "capture": "capturing",
        "captures": "capturing",
        "compute": "computing",
        "computes": "computing",
        "connect": "connecting",
        "connects": "connecting",
        "derive": "deriving",
        "derives": "deriving",
        "enforce": "enforcing",
        "enforces": "enforcing",
        "fetch": "fetching",
        "fetches": "fetching",
        "hold": "holding",
        "holds": "holding",
        "manage": "managing",
        "manages": "managing",
        "own": "owning",
        "owns": "owning",
        "produce": "producing",
        "produces": "producing",
        "provide": "providing",
        "provides": "providing",
        "record": "recording",
        "records": "recording",
        "render": "rendering",
        "renders": "rendering",
        "serve": "serving",
        "serves": "serving",
        "track": "tracking",
        "tracks": "tracking",
        "validate": "validating",
        "validates": "validating",
    }
    if verb in gerunds and separator:
        return f"{gerunds[verb]} {_gerund_joined_verbs(tail.strip(), gerunds)}"
    return text[:1].lower() + text[1:]


def _gerund_joined_verbs(value: str, gerunds: Mapping[str, str]) -> str:
    pattern = re.compile(
        r"\b(?P<join>and|or)\s+(?P<verb>"
        + "|".join(re.escape(verb) for verb in sorted(gerunds, key=len, reverse=True))
        + r")\b",
        flags=re.IGNORECASE,
    )

    def replace(match: re.Match[str]) -> str:
        joiner = match.group("join")
        verb = match.group("verb").casefold()
        return f"{joiner} {gerunds[verb]}"

    return pattern.sub(replace, value)


def _posture_lines(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    lines: list[str] = []
    for key in keys:
        lines.extend(_posture_value_lines(row.get(key)))
    return unique_text(lines)


def _posture_value_lines(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        if "statement" not in value and "mitigation" not in value:
            ignored = {"id", "evidence_tier", "kind"}
            return unique_text(
                line
                for nested_key, nested_value in value.items()
                if str(nested_key) not in ignored
                for line in _posture_value_lines(nested_value)
            )
        statement = join_sentence_text(
            value.get("statement")
            or value.get("risk")
            or value.get("detail")
            or value.get("domain")
            or value.get("security")
            or value.get("policy")
            or value.get("compliance")
        )
        mitigation = join_sentence_text(value.get("mitigation"))
        if statement and mitigation:
            return (f"{statement} Mitigation: {mitigation}",)
        if statement:
            return (statement,)
        ignored = {"id", "evidence_tier", "kind"}
        return unique_text(
            line
            for nested_key, nested_value in value.items()
            if str(nested_key) not in ignored
            for line in _posture_value_lines(nested_value)
        )
    if isinstance(value, (list, tuple, set)):
        return unique_text(line for nested in value for line in _posture_value_lines(nested))
    return text_values(value)


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


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


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


_COMPONENT_RISK_TOKENS = ("risk", "failure", "fallback", "mitigation", "recovery", "degraded", "operational")
_COMPONENT_SECURITY_TOKENS = (
    "security",
    "auth",
    "authorization",
    "credential",
    "permission",
    "session",
    "secret",
    "token",
    "access",
    "ownership",
    "private",
    "abuse",
    "pii",
    "data risk",
)
_COMPONENT_POLICY_TOKENS = (
    "compliance",
    "policy",
    "privacy",
    "retention",
    "audit",
    "regulated",
    "accessibility",
    "public",
    "private",
    "safety",
)


__all__ = [
    "allocated_diagram_ids",
    "component_authoring_prewrite_inputs",
    "component_dependency_lines",
    "component_dependency_lookup_for",
    "component_risk_lines",
    "ensure_greenfield_create_baseline",
    "ensure_release_target",
    "first_release_component_rows",
    "is_first_release_component",
    "preview_prewrite_components",
    "preview_accepted_project_memory",
    "preview_compass_acceptance_event",
    "remap_prewrite_backlog_result",
    "render_prewrite_atlas_sources",
    "render_prewrite_component_specs",
    "staged_greenfield_prewrite_root",
]
