"""Component-local Registry scope selection for greenfield apply.

Radar and Atlas own the broad project topology. This module keeps Registry
component dossiers focused on the component's own implementation lane and
component-relevant diagrams so generated specs do not repeat the whole project.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class ComponentDiagramScope:
    ids_by_slug: Mapping[str, str]
    allowlist: frozenset[str]


def build_component_diagram_scope(
    *,
    rows: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
) -> ComponentDiagramScope:
    ids_by_slug: dict[str, str] = {}
    allowlist: set[str] = set()
    for row, diagram_id in zip(rows, diagram_ids, strict=False):
        if _is_project_level_diagram(row):
            continue
        identifier = str(diagram_id).strip().upper()
        if not identifier:
            continue
        allowlist.add(identifier)
        for value in (row.get("slug"), row.get("id"), row.get("title")):
            slug = slugify(str(value or "").strip())
            if slug:
                ids_by_slug.setdefault(slug, identifier)
    return ComponentDiagramScope(ids_by_slug=ids_by_slug, allowlist=frozenset(allowlist))


def registry_component_workstreams(
    *,
    handoff: Mapping[str, Any],
    fallback: Sequence[str],
) -> tuple[str, ...]:
    primary = str(handoff.get("workstream_id", "") or "").strip().upper()
    if primary:
        return (primary,)
    for item in fallback:
        token = str(item).strip().upper()
        if token:
            return (token,)
    return ()


def registry_component_diagrams(
    *,
    row: Mapping[str, Any],
    diagram_scope: ComponentDiagramScope,
    fallback: Sequence[str],
) -> tuple[str, ...]:
    explicit_ids: list[str] = []
    for value in row_text_tuple(row, "related_diagram_slugs", "diagram_slugs", "related_diagrams", "diagrams"):
        slug = slugify(value)
        diagram_id = diagram_scope.ids_by_slug.get(slug)
        if diagram_id:
            explicit_ids.append(diagram_id)
    if explicit_ids:
        return tuple(unique_text(explicit_ids))
    return tuple(
        unique_text(
            identifier
            for item in fallback
            if (identifier := str(item).strip().upper()) and identifier in diagram_scope.allowlist
        )
    )


def _is_project_level_diagram(row: Mapping[str, Any]) -> bool:
    text = " ".join(str(row.get(key, "") or "") for key in ("slug", "title", "summary")).casefold()
    return any(
        phrase in text
        for phrase in (
            "system overview",
            "system context",
            "top-level greenfield topology",
            "project overview",
            "program overview",
            "program waves",
        )
    )


__all__ = [
    "ComponentDiagramScope",
    "build_component_diagram_scope",
    "registry_component_diagrams",
    "registry_component_workstreams",
]
