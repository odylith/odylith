"""Exact typed traceability for sealed Greenfield authored projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    PROVISIONAL_DESIGN_AUTHORITY_KIND,
    provisional_design_from_intent,
)
from odylith.runtime.governance import backlog_authoring


@dataclass(frozen=True)
class CreatedWorkstream:
    idea_id: str
    title: str
    path: Path
    row: Mapping[str, Any]


@dataclass(frozen=True)
class DiagramLink:
    row: Mapping[str, Any]
    diagram_id: str
    related_workstream_ids: tuple[str, ...]
    related_backlog_paths: tuple[str, ...]


@dataclass(frozen=True)
class GreenfieldTraceabilityPlan:
    workstreams: tuple[CreatedWorkstream, ...]
    component_workstreams: dict[str, tuple[str, ...]]
    component_diagrams: dict[str, tuple[str, ...]]
    diagram_links: tuple[DiagramLink, ...]
    backlog_diagrams: dict[str, tuple[str, ...]]


def traceability_plan_from_payload(value: Any) -> GreenfieldTraceabilityPlan:
    """Rehydrate a serialized prewrite traceability plan."""

    payload = value if isinstance(value, Mapping) else {}
    return GreenfieldTraceabilityPlan(
        workstreams=tuple(_created_workstream_from_payload(row) for row in _rows(payload.get("workstreams"))),
        component_workstreams=_tuple_map(payload.get("component_workstreams")),
        component_diagrams=_tuple_map(payload.get("component_diagrams")),
        diagram_links=tuple(_diagram_link_from_payload(row) for row in _rows(payload.get("diagram_links"))),
        backlog_diagrams=_tuple_map(payload.get("backlog_diagrams")),
    )


def component_key(row: Mapping[str, Any]) -> str:
    """Return the stable proposal-local key for an authored component row."""

    return slugify(str(row.get("component_id", "")).strip() or str(row.get("label", "")).strip())


def build_traceability_plan(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
) -> GreenfieldTraceabilityPlan:
    """Bind authored artifacts through exact typed references only."""

    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise ValueError("Greenfield traceability requires a sealed authored projection")

    workstreams = _created_workstreams(proposal=proposal, created_backlog=created_backlog)
    workstreams_by_title = {workstream.title: workstream for workstream in workstreams}
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    components_by_id: dict[str, Mapping[str, Any]] = {}
    for component in components:
        component_id = str(component.get("component_id") or "").strip()
        if not component_id:
            raise ValueError("model-authored component is missing its typed component id")
        components_by_id[component_id] = component

    component_workstreams: dict[str, tuple[str, ...]] = {}
    for component_id, component in components_by_id.items():
        related = tuple(
            workstream.idea_id
            for workstream in workstreams
            if component_id in _authored_reference_list(workstream.row, "component_focus")
        )
        if not related:
            raise ValueError(f"model-authored component `{component_id}` has no exact workstream binding")
        component_workstreams[component_key(component)] = related

    diagrams = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    if len(diagrams) != len(diagram_ids):
        raise ValueError("model-authored diagrams must have one allocated id per typed diagram")

    paths_by_id = {workstream.idea_id: str(workstream.path) for workstream in workstreams}
    component_diagrams: dict[str, list[str]] = {
        component_key(component): [] for component in components
    }
    backlog_diagrams: dict[str, list[str]] = {}
    diagram_links: list[DiagramLink] = []
    for row, raw_diagram_id in zip(diagrams, diagram_ids, strict=True):
        diagram_id = str(raw_diagram_id).strip()
        if not diagram_id:
            raise ValueError("model-authored diagram allocation produced an empty id")
        related_titles = _authored_reference_list(row, "related_workstream_titles")
        if not related_titles:
            raise ValueError(f"model-authored diagram `{diagram_id}` is missing workstream bindings")
        unknown_titles = [title for title in related_titles if title not in workstreams_by_title]
        if unknown_titles:
            raise ValueError(
                f"model-authored diagram `{diagram_id}` references unknown workstream `{unknown_titles[0]}`"
            )
        related_ids = tuple(workstreams_by_title[title].idea_id for title in related_titles)
        related_component_ids = _authored_reference_list(row, "related_components")
        unknown_components = [
            component_id for component_id in related_component_ids if component_id not in components_by_id
        ]
        if unknown_components:
            raise ValueError(
                f"model-authored diagram `{diagram_id}` references unknown component `{unknown_components[0]}`"
            )
        diagram_links.append(
            DiagramLink(
                row=row,
                diagram_id=diagram_id,
                related_workstream_ids=related_ids,
                related_backlog_paths=tuple(paths_by_id[idea_id] for idea_id in related_ids),
            )
        )
        for component_id in related_component_ids:
            component_diagrams[component_key(components_by_id[component_id])].append(diagram_id)
        for idea_id in related_ids:
            backlog_diagrams.setdefault(idea_id, []).append(diagram_id)

    return GreenfieldTraceabilityPlan(
        workstreams=workstreams,
        component_workstreams=component_workstreams,
        component_diagrams={key: _unique(values) for key, values in component_diagrams.items()},
        diagram_links=tuple(diagram_links),
        backlog_diagrams={key: _unique(values) for key, values in backlog_diagrams.items()},
    )


def apply_backlog_traceability(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    plan: GreenfieldTraceabilityPlan,
) -> list[str]:
    """Publish exact diagram and allocated design prerequisites before sealing."""

    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise ValueError("Greenfield traceability publication requires a sealed authored projection")
    dependencies = _allocated_workstream_dependencies(proposal=proposal, workstreams=plan.workstreams)
    records = [
        (workstream, *backlog_authoring._parse_metadata_and_sections(workstream.path))
        for workstream in plan.workstreams
    ]
    for workstream, metadata, _ in records:
        if metadata.get("idea_id") != workstream.idea_id or metadata.get("title") != workstream.title:
            raise ValueError("Greenfield workstream allocation does not match its compiled Radar record")
    touched: list[str] = []
    for workstream, metadata, sections in records:
        metadata["workstream_depends_on"] = _join_ids(dependencies[workstream.idea_id])
        diagrams = plan.backlog_diagrams.get(workstream.idea_id, ())
        if diagrams:
            metadata["related_diagram_ids"] = _join_ids(
                _merge_ids(metadata.get("related_diagram_ids", ""), diagrams)
            )
        workstream.path.write_text(
            backlog_authoring._render_idea_text(metadata=metadata, sections=sections),
            encoding="utf-8",
        )
        touched.append(_repo_relative(repo_root=repo_root, path=workstream.path))
    return touched


def _allocated_workstream_dependencies(
    *, proposal: Mapping[str, Any], workstreams: Sequence[CreatedWorkstream],
) -> dict[str, tuple[str, ...]]:
    design = provisional_design_from_intent(_mapping(proposal.get("intent")))
    canonical_rows = {row["key"]: row for row in design["workstreams"]}
    ids_by_key: dict[str, str] = {}
    allocated_ids: set[str] = set()
    allocated_paths: set[Path] = set()
    for workstream in workstreams:
        contract = _mapping(workstream.row.get("provisional_workstream_contract"))
        projected = _mapping(contract.get("provisional_workstream"))
        key = projected.get("key")
        canonical = canonical_rows.get(key) if isinstance(key, str) else None
        if (
            canonical is None
            or projected != canonical
            or contract.get("authority_kind") != PROVISIONAL_DESIGN_AUTHORITY_KIND
            or workstream.row.get("authority_kind") != PROVISIONAL_DESIGN_AUTHORITY_KIND
            or workstream.title != canonical["title"]
            or workstream.row.get("title") != canonical["title"]
            or key in ids_by_key
            or not workstream.idea_id
            or workstream.idea_id in allocated_ids
            or workstream.path.resolve() in allocated_paths
        ):
            raise ValueError("Greenfield workstream allocation must bind each canonical design key exactly once")
        ids_by_key[key] = workstream.idea_id
        allocated_ids.add(workstream.idea_id)
        allocated_paths.add(workstream.path.resolve())
    if ids_by_key.keys() != canonical_rows.keys():
        raise ValueError("Greenfield workstream allocation is missing canonical design workstreams")
    return {
        ids_by_key[key]: tuple(ids_by_key[dependency] for dependency in row["depends_on"])
        for key, row in canonical_rows.items()
    }


def allocated_workstreams(
    *, proposal: Mapping[str, Any], created_backlog: Sequence[Mapping[str, Any]],
) -> tuple[CreatedWorkstream, ...]:
    """Validate exact design-key allocations and preserve canonical design order."""

    workstreams = _created_workstreams(proposal=proposal, created_backlog=created_backlog)
    dependencies = _allocated_workstream_dependencies(proposal=proposal, workstreams=workstreams)
    by_id = {workstream.idea_id: workstream for workstream in workstreams}
    return tuple(by_id[idea_id] for idea_id in dependencies)


def first_executable_workstream(
    *, proposal: Mapping[str, Any], created_backlog: Sequence[Mapping[str, Any]],
    first_release_workstreams: Sequence[str],
) -> CreatedWorkstream:
    """Select a dependency-free workstream from a closed, allocated release.

    Independent roots retain canonical design order as a deterministic tie-break;
    neither allocation numbers nor source-event order imply delivery priority.
    """

    workstreams = _created_workstreams(proposal=proposal, created_backlog=created_backlog)
    dependencies = _allocated_workstream_dependencies(proposal=proposal, workstreams=workstreams)
    release_ids = tuple(str(item).strip().upper() for item in first_release_workstreams)
    if not release_ids or len(set(release_ids)) != len(release_ids) or any(
        idea_id not in dependencies for idea_id in release_ids
    ):
        raise ValueError("Greenfield first release must contain unique allocated workstreams")
    release_set = set(release_ids)
    if any(not set(dependencies[idea_id]) <= release_set for idea_id in release_ids):
        raise ValueError("Greenfield first release has a prerequisite outside its release scope")
    by_id = {workstream.idea_id: workstream for workstream in workstreams}
    return next(
        by_id[idea_id] for idea_id, prerequisites in dependencies.items()
        if idea_id in release_set and not prerequisites
    )


def _created_workstreams(
    *,
    proposal: Mapping[str, Any],
    created_backlog: Sequence[Mapping[str, Any]],
) -> tuple[CreatedWorkstream, ...]:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    workstreams: list[CreatedWorkstream] = []
    rows_by_title = {str(row.get("title", "")): row for row in rows}
    if len(rows_by_title) != len(rows):
        raise ValueError("Greenfield workstream allocation has duplicate proposal titles")
    for created in created_backlog:
        row = rows_by_title.get(str(created.get("title", "")), {})
        idea_id = str(created.get("idea_id", "")).strip().upper()
        title = str(created.get("title", "")).strip() or str(row.get("title", "")).strip()
        raw_path = str(created.get("idea_path", "")).strip()
        if not idea_id or not raw_path or not row:
            raise ValueError("Greenfield workstream allocation is missing its exact record binding")
        workstreams.append(
            CreatedWorkstream(
                idea_id=idea_id,
                title=title,
                path=Path(raw_path).expanduser().resolve(),
                row=row,
            )
        )
    return tuple(workstreams)


def _authored_reference_list(row: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = row.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    references = tuple(str(item).strip() for item in value)
    if any(not item for item in references):
        raise ValueError(f"model-authored `{key}` contains an empty typed reference")
    return references


def _created_workstream_from_payload(value: Mapping[str, Any]) -> CreatedWorkstream:
    return CreatedWorkstream(
        idea_id=str(value.get("idea_id", "")).strip().upper(),
        title=str(value.get("title", "")).strip(),
        path=Path(str(value.get("path", ""))).expanduser(),
        row=_mapping(value.get("row")),
    )


def _diagram_link_from_payload(value: Mapping[str, Any]) -> DiagramLink:
    return DiagramLink(
        row=_mapping(value.get("row")),
        diagram_id=str(value.get("diagram_id", "")).strip(),
        related_workstream_ids=tuple(
            str(item).strip().upper()
            for item in _sequence(value.get("related_workstream_ids"))
            if str(item).strip()
        ),
        related_backlog_paths=tuple(
            str(item).strip()
            for item in _sequence(value.get("related_backlog_paths"))
            if str(item).strip()
        ),
    )


def _tuple_map(value: Any) -> dict[str, tuple[str, ...]]:
    source = value if isinstance(value, Mapping) else {}
    return {
        str(key): tuple(str(item).strip() for item in _sequence(items) if str(item).strip())
        for key, items in source.items()
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    return tuple(row for row in _sequence(value) if isinstance(row, Mapping))


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _merge_ids(current: str, values: Sequence[str]) -> tuple[str, ...]:
    return _unique((*current.split(","), *values), uppercase=True)


def _join_ids(values: Sequence[str]) -> str:
    return ",".join(_unique(values, uppercase=True))


def _unique(values: Sequence[str], *, uppercase: bool = False) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if uppercase:
            text = text.upper()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return tuple(result)


def _repo_relative(*, repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())
