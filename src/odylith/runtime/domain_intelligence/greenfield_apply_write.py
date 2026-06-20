"""Final governed writes for confirmed greenfield apply."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_component_registry_scope
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_authoring_responsibility
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_dependency_lines
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_dependency_lookup_for
from odylith.runtime.domain_intelligence.greenfield_apply_components import component_risk_lines
from odylith.runtime.domain_intelligence.greenfield_apply_components import first_release_component_rows
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import allocated_diagram_ids
from odylith.runtime.domain_intelligence.greenfield_component_contract import rendered_component_spec_quality_issues
from odylith.runtime.domain_intelligence.greenfield_component_contract_targets import operator_component_spec_issues
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_completion_report
from odylith.runtime.domain_intelligence.proposal_memory import record_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import release_planning_authoring
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
) -> dict[str, Any]:
    """Apply accepted Radar, Registry, Atlas, release, and memory records."""

    release_bootstrap = None
    release_targeting = None
    rendered_atlas_sources = dict(prewrite_package.rendered_atlas_sources or {}) if prewrite_package else {}
    rendered_component_specs = dict(prewrite_package.rendered_component_specs or {}) if prewrite_package else {}
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
    for raw_path, text in backlog_result.get("existing_idea_files", {}).items():
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text), encoding="utf-8")
    for raw_path, text in backlog_result["idea_files"].items():
        path = Path(raw_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text), encoding="utf-8")
    backlog_index_path = Path(backlog_result["backlog_index"])
    backlog_index_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_index_path.write_text(str(backlog_result["backlog_index_text"]), encoding="utf-8")
    program_result = greenfield_programs.create_greenfield_program(
        repo_root=root,
        proposal=proposal,
        backlog_result=backlog_result,
    )
    first_release_workstreams = greenfield_programs.first_release_workstream_ids(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        program_result=program_result,
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
    diagram_ids = allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
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
            starter_source=_prewrite_atlas_source(row, rendered_atlas_sources),
        )
        diagrams_created.append(diagram_id)
    touched_backlog_paths = greenfield_traceability.apply_backlog_traceability(
        repo_root=root,
        proposal=proposal,
        plan=traceability_plan,
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
    components_created: list[dict[str, Any]] = []
    for row in component_rows:
        if not isinstance(row, Mapping):
            continue
        key = greenfield_traceability.component_key(row)
        handoff = component_handoffs.get(key, {})
        created = component_authoring.register_component(
            repo_root=root,
            component_id=str(row.get("component_id", "")).strip(),
            label=str(row.get("label", "")).strip(),
            path=str(row.get("intended_path", "")).strip(),
            kind=str(row.get("kind", "service")).strip() or "service",
            category="application",
            qualification=str(row.get("qualification", "candidate")).strip() or "candidate",
            owner="repo",
            status=str(row.get("status", "planned")).strip() or "planned",
            product_layer="application",
            sources=("user_intent",),
            workstreams=greenfield_component_registry_scope.registry_component_workstreams(
                handoff=handoff,
                fallback=traceability_plan.component_workstreams.get(key, ()),
            ),
            diagrams=greenfield_component_registry_scope.registry_component_diagrams(
                row=row,
                diagram_scope=component_diagram_scope,
                fallback=traceability_plan.component_diagrams.get(key, ()),
            ),
            responsibility=component_authoring_responsibility(row),
            boundary=str(row.get("boundary", "")).strip(),
            dependencies=component_dependency_lines(
                row_text_tuple(row, "dependencies", "depends_on"),
                lookup=component_dependency_lookup,
            ),
            interfaces=row_text_tuple(row, "interfaces", "interface_changes"),
            validation=row_text_tuple(row, "validation", "test_strategy"),
            risks=component_risk_lines(row, proposal),
            implementation_handoff=handoff,
            component_contract=row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else None,
            dry_run=False,
            update_existing=True,
            refresh=False,
        )
        _write_repaired_component_spec(
            root=root,
            created=created.as_dict(),
            rendered_component_specs=rendered_component_specs,
        )
        components_created.append(created.as_dict())
    _raise_for_component_spec_quality(root=root, proposal=proposal, components=components_created)

    release_id = "none"
    if isinstance(release_targeting, Mapping):
        release_id = str(release_targeting.get("release_id", "")).strip() or "none"
    memory_record = record_greenfield_acceptance(
        repo_root=root,
        proposal=proposal,
        backlog_items=backlog_result["created"],
        component_items=components_created,
        diagram_ids=diagrams_created,
        release_selector=release_selector,
        release_id=release_id,
        validation_gate=tribunal.to_dict(),
    )
    next_steps = greenfield_experience.build_next_steps(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=first_release_workstreams,
        program_result=program_result,
        release_selector=release_selector,
    )
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
        memory_record=memory_record,
        next_steps=next_steps,
    )
    dashboard_refresh = _refresh_greenfield_dashboard(repo_root=root)

    return {
        "mode": "applied",
        "validation_gate": tribunal.to_dict(),
        "backlog": backlog_result["created"],
        "components": components_created,
        "diagrams": diagrams_created,
        "program": program_result,
        "backlog_topology": touched_backlog_paths,
        "atlas_scaffold_logs": atlas_scaffold_logs,
        "memory": memory_record,
        "dashboard_refresh": dashboard_refresh,
        "next_steps": next_steps,
        "release_bootstrap": release_bootstrap or {"created": False, "release": {}},
        "release_target": release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
    }


_GREENFIELD_VISIBLE_SURFACES = ("radar", "registry", "atlas", "compass", "tooling_shell")


def _refresh_greenfield_dashboard(*, repo_root: Path) -> dict[str, Any]:
    view = owned_surface_refresh.dashboard_handoff(surface="project")
    try:
        owned_surface_refresh.raise_for_failed_refreshes(
            repo_root=Path(repo_root).resolve(),
            surfaces=_GREENFIELD_VISIBLE_SURFACES,
            operation_label="Greenfield apply dashboard visibility",
        )
    except RuntimeError as exc:
        return {
            "status": "warning",
            "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
            "view": view,
            "warning": str(exc),
        }
    return {
        "status": "passed",
        "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
        "view": view,
    }


def _prewrite_atlas_source(row: Mapping[str, Any], rendered_atlas_sources: Mapping[str, str]) -> str:
    path = _atlas_source_path_for_row(row)
    if not path:
        return ""
    return str(rendered_atlas_sources.get(path, "")).strip()


def _atlas_source_path_for_row(row: Mapping[str, Any]) -> str:
    slug = str(row.get("slug", "")).strip()
    if not slug:
        return ""
    return f"odylith/atlas/source/{slug}.mmd"


def _write_repaired_component_spec(
    *,
    root: Path,
    created: Mapping[str, Any],
    rendered_component_specs: Mapping[str, str],
) -> None:
    label = str(created.get("label", "")).strip()
    rendered = str(rendered_component_specs.get(label, "")).rstrip()
    if not rendered:
        return
    spec_path = Path(str(created.get("spec_path", "")))
    if not spec_path.is_absolute():
        spec_path = root / spec_path
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(f"{rendered}\n", encoding="utf-8")


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
    memory_record: Mapping[str, Any],
    next_steps: Mapping[str, Any],
) -> None:
    accepted_project_preview = _read_json_mapping(root / "odylith/runtime/source/accepted-project.v1.json")
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector=release_selector,
        rendered_component_specs=_actual_component_specs(root=root, components=component_rows),
        rendered_atlas_sources=_actual_atlas_sources(root=root, rows=diagram_rows),
        component_registry_preview=tuple(dict(row) for row in component_rows),
        project_brief_preview=proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {},
        tribunal_preview=tribunal.to_dict(),
        accepted_project_preview=accepted_project_preview,
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
    issues = dedupe_strings(
        [
            *completion.issues,
            *greenfield_rendered_package_quality_issues(package),
            *generated_public_copy_issues("accepted-project final memory", accepted_project_preview),
            *generated_public_copy_issues("Compass final memory", package.compass_memory_preview),
        ]
    )
    if issues:
        detail = "\n".join(f"- {issue}" for issue in issues)
        raise ValueError(f"greenfield post-confirm final write quality failed with {len(issues)} issue(s):\n{detail}")


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


def _scaffold_proposal_diagram(
    *,
    root: Path,
    row: Mapping[str, Any],
    diagram_id: str,
    traceability_plan: Any,
    atlas_scaffold_logs: list[str],
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
        review_date=dt.date.today().isoformat(),
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
            review_date=dt.date.today().isoformat(),
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
        detail = "\n".join(f"- {issue}" for issue in operator_component_spec_issues(issues))
        raise ValueError(f"greenfield component spec quality gate failed with {len(issues)} issue(s):\n{detail}")


__all__ = [
    "release_assignment_note",
    "write_greenfield_proposal",
]
