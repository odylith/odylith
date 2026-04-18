"""Shared lookup helpers for Radar/Atlas UI title metadata.

These helpers normalize and aggregate human-readable titles for workstream and
diagram identifiers so both HTML generators can emit consistent tooltip data.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Iterable, Mapping

_WORKSTREAM_ID_RE = re.compile(r"^B-\d+$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d+$")
_COMPONENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def normalize_workstream_id(value: Any) -> str:
    """Normalize workstream ids to the canonical `B-123` form."""
    token = str(value or "").strip()
    if not token:
        return ""
    if _WORKSTREAM_ID_RE.match(token):
        return token
    return ""


def normalize_diagram_id(value: Any) -> str:
    """Normalize diagram ids and strip optional `diagram:` prefixes."""
    token = str(value or "").strip()
    if not token:
        return ""
    if token.startswith("diagram:"):
        token = token[len("diagram:") :].strip()
    if _DIAGRAM_ID_RE.match(token):
        return token
    return ""


def normalize_component_id(value: Any) -> str:
    """Normalize component ids to the lowercase registry token form."""
    token = str(value or "").strip().lower()
    if not token:
        return ""
    if _COMPONENT_ID_RE.fullmatch(token):
        return token
    return ""


def _sorted_lookup(mapping: Mapping[str, str]) -> dict[str, str]:
    """Return a mapping sorted by key for stable UI payload output."""
    return {key: mapping[key] for key in sorted(mapping)}


def _normalize_title(value: Any) -> str:
    """Normalize display titles without altering their visible casing."""
    return str(value or "").strip()


def _store_title(
    lookup: dict[str, str],
    *,
    raw_id: Any,
    raw_title: Any,
    normalize_id: Callable[[Any], str],
) -> None:
    """Record one normalized title entry when both id and title are valid."""
    normalized_id = normalize_id(raw_id)
    title = _normalize_title(raw_title)
    if normalized_id and title:
        lookup[normalized_id] = title


def build_workstream_title_lookup(
    *,
    entries: Iterable[Mapping[str, Any]] | None = None,
    traceability_graph: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Build a workstream-id to title lookup from entries and traceability graph data."""
    lookup: dict[str, str] = {}

    for row in entries or []:
        _store_title(
            lookup,
            raw_id=row.get("idea_id"),
            raw_title=row.get("title"),
            normalize_id=normalize_workstream_id,
        )

    graph = traceability_graph if isinstance(traceability_graph, Mapping) else {}
    workstreams = graph.get("workstreams", [])
    if isinstance(workstreams, list):
        for row in workstreams:
            if not isinstance(row, Mapping):
                continue
            _store_title(
                lookup,
                raw_id=row.get("idea_id"),
                raw_title=row.get("title"),
                normalize_id=normalize_workstream_id,
            )

    return _sorted_lookup(lookup)


def build_diagram_title_lookup(
    *,
    diagrams: Iterable[Mapping[str, Any]] | None = None,
    traceability_graph: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Build a diagram-id to title lookup from catalog and graph-derived data."""
    lookup: dict[str, str] = {}

    for row in diagrams or []:
        _store_title(
            lookup,
            raw_id=row.get("diagram_id") or row.get("id"),
            raw_title=row.get("title") or row.get("label"),
            normalize_id=normalize_diagram_id,
        )

    graph = traceability_graph if isinstance(traceability_graph, Mapping) else {}
    graph_diagrams = graph.get("diagrams", [])
    if isinstance(graph_diagrams, list):
        for row in graph_diagrams:
            if not isinstance(row, Mapping):
                continue
            _store_title(
                lookup,
                raw_id=row.get("diagram_id") or row.get("id"),
                raw_title=row.get("title") or row.get("label"),
                normalize_id=normalize_diagram_id,
            )

    nodes = graph.get("nodes", [])
    if isinstance(nodes, list):
        for row in nodes:
            if not isinstance(row, Mapping):
                continue
            node_type = str(row.get("type", "")).strip().lower()
            if node_type != "diagram":
                continue
            _store_title(
                lookup,
                raw_id=row.get("diagram_id") or row.get("id"),
                raw_title=row.get("title") or row.get("label"),
                normalize_id=normalize_diagram_id,
            )

    return _sorted_lookup(lookup)


def build_component_title_lookup(
    *,
    components: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, str]:
    """Build a component-id to title lookup from registry component rows."""
    lookup: dict[str, str] = {}
    for row in components or []:
        _store_title(
            lookup,
            raw_id=row.get("component_id") or row.get("id"),
            raw_title=row.get("name") or row.get("title") or row.get("label"),
            normalize_id=normalize_component_id,
        )
    return _sorted_lookup(lookup)


def build_diagram_related_workstream_lookup(
    *,
    diagrams: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, list[str]]:
    """Build a diagram-id to related-workstream-id lookup for tooltip payloads."""
    lookup: dict[str, list[str]] = {}
    for row in diagrams or []:
        diagram_id = normalize_diagram_id(row.get("diagram_id") or row.get("id"))
        if not diagram_id:
            continue
        related = row.get("related_workstreams")
        if not isinstance(related, list):
            continue
        values: list[str] = []
        seen: set[str] = set()
        for item in related:
            workstream_id = normalize_workstream_id(item)
            if not workstream_id or workstream_id in seen:
                continue
            seen.add(workstream_id)
            values.append(workstream_id)
        if values:
            lookup[diagram_id] = values
    return {key: lookup[key] for key in sorted(lookup)}


def build_tooltip_lookup_payload(
    *,
    entries: Iterable[Mapping[str, Any]] | None = None,
    diagrams: Iterable[Mapping[str, Any]] | None = None,
    components: Iterable[Mapping[str, Any]] | None = None,
    traceability_graph: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Build the combined tooltip payload consumed by Radar and Atlas UI surfaces."""
    return {
        "workstream_titles": build_workstream_title_lookup(
            entries=entries,
            traceability_graph=traceability_graph,
        ),
        "diagram_titles": build_diagram_title_lookup(
            diagrams=diagrams,
            traceability_graph=traceability_graph,
        ),
        "component_titles": build_component_title_lookup(
            components=components,
        ),
        "diagram_related_workstreams": build_diagram_related_workstream_lookup(
            diagrams=diagrams,
        ),
    }
