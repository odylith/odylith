"""Parser-free traceability data contract shared by pre- and post-confirm code."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)


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
        workstreams=tuple(_created_workstream(row) for row in _rows(payload.get("workstreams"))),
        component_workstreams=_tuple_map(payload.get("component_workstreams")),
        component_diagrams=_tuple_map(payload.get("component_diagrams")),
        diagram_links=tuple(_diagram_link(row) for row in _rows(payload.get("diagram_links"))),
        backlog_diagrams=_tuple_map(payload.get("backlog_diagrams")),
    )


def component_key(row: Mapping[str, Any]) -> str:
    """Return a stable identifier without interpreting component prose."""

    return semantic_artifact_identifier(
        row.get("component_id") or row.get("label"),
        fallback="component",
    )


def _created_workstream(value: Mapping[str, Any]) -> CreatedWorkstream:
    return CreatedWorkstream(
        idea_id=str(value.get("idea_id") or "").strip().upper(),
        title=str(value.get("title") or "").strip(),
        path=Path(str(value.get("path") or "")).expanduser(),
        row=value.get("row") if isinstance(value.get("row"), Mapping) else {},
    )


def _diagram_link(value: Mapping[str, Any]) -> DiagramLink:
    return DiagramLink(
        row=value.get("row") if isinstance(value.get("row"), Mapping) else {},
        diagram_id=str(value.get("diagram_id") or "").strip(),
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


def _rows(value: Any) -> tuple[Mapping[str, Any], ...]:
    return tuple(row for row in _sequence(value) if isinstance(row, Mapping))


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else ()


__all__ = [
    "CreatedWorkstream",
    "DiagramLink",
    "GreenfieldTraceabilityPlan",
    "component_key",
    "traceability_plan_from_payload",
]
