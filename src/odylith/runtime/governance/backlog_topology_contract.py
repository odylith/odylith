"""Validate topology-bearing Radar workstream metadata."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Mapping, Protocol

from odylith.runtime.governance.backlog_metadata import split_metadata_ids

_IDEA_ID_RE = re.compile(r"^B-(?P<num>\d{3,})$")
_TOPOLOGY_GATE_START = dt.date(2026, 5, 1)
_TOPOLOGY_SENSITIVE_TERMS = (
    "atlas",
    "browser surface",
    "casebook",
    "claude",
    "codex",
    "compass",
    "context engine",
    "cross-host",
    "dashboard",
    "delivery intelligence",
    "execution engine",
    "governance surface",
    "host adapter",
    "host hook",
    "intervention",
    "memory substrate",
    "migration",
    "product surface",
    "radar",
    "registry",
    "runtime",
    "subagent",
    "surface dag",
    "topology",
    "tribunal",
)


class TopologyIdeaSpec(Protocol):
    path: Path
    metadata: Mapping[str, str]
    section_bodies: Mapping[str, str]

    @property
    def idea_id(self) -> str: ...

    @property
    def status(self) -> str: ...


def _normalize_workstream_ref(raw: str) -> str:
    token = str(raw or "").strip().upper()
    if token in {"", "NONE", "-"}:
        return ""
    return token


def _build_topology_values(spec: TopologyIdeaSpec, field: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in split_metadata_ids(spec.metadata.get(field, "")):
        normalized = _normalize_workstream_ref(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        values.append(normalized)
    return values


def _build_related_diagram_values(spec: TopologyIdeaSpec) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for token in split_metadata_ids(spec.metadata.get("related_diagram_ids", "")):
        if token in {"NONE", "-"} or token in seen:
            continue
        seen.add(token)
        values.append(token)
    return values


def _topology_rationale_text(spec: TopologyIdeaSpec) -> str:
    return "\n".join(
        spec.section_bodies.get(section, "")
        for section in ("Scope", "Non-Goals", "Interface Changes", "Open Questions")
    ).lower()


def _topology_rationale_exempts(spec: TopologyIdeaSpec) -> bool:
    text = _topology_rationale_text(spec)
    return "no topology" in text or "topology not required" in text or "no diagram" in text


def _topology_sensitive(spec: TopologyIdeaSpec) -> bool:
    haystack = "\n".join(
        [
            str(spec.metadata.get("title", "")),
            str(spec.metadata.get("impacted_parts", "")),
            spec.section_bodies.get("Problem", ""),
            spec.section_bodies.get("Proposed Solution", ""),
            spec.section_bodies.get("Scope", ""),
            spec.section_bodies.get("Impacted Components", ""),
        ]
    ).lower()
    return any(term in haystack for term in _TOPOLOGY_SENSITIVE_TERMS)


def _topology_gate_applies(spec: TopologyIdeaSpec) -> bool:
    try:
        opened = dt.date.fromisoformat(spec.metadata.get("date", "").strip())
    except ValueError:
        return True
    return opened >= _TOPOLOGY_GATE_START


def validate_topology_contract(*, ideas: Mapping[str, TopologyIdeaSpec]) -> list[str]:
    errors: list[str] = []
    idea_ids = set(ideas.keys())

    for idea_id, spec in sorted(ideas.items()):
        for diagram_id in _build_related_diagram_values(spec):
            if not re.fullmatch(r"D-\d{3}", diagram_id):
                errors.append(f"{spec.path}: `related_diagram_ids` contains invalid diagram id `{diagram_id}`")

        if (
            spec.status in {"implementation", "finished"}
            and _topology_gate_applies(spec)
            and _topology_sensitive(spec)
            and not _build_related_diagram_values(spec)
            and not _topology_rationale_exempts(spec)
        ):
            errors.append(
                f"{spec.path}: topology-sensitive workstream `{idea_id}` opened on or after {_TOPOLOGY_GATE_START.isoformat()} must declare `related_diagram_ids` or an explicit topology rationale"
            )

        parent_values = _build_topology_values(spec, "workstream_parent")
        if len(parent_values) > 1:
            errors.append(f"{spec.path}: `workstream_parent` expects a single B-id, got `{','.join(parent_values)}`")
            continue

        if parent_values:
            parent_id = parent_values[0]
            if not _IDEA_ID_RE.fullmatch(parent_id):
                errors.append(f"{spec.path}: `workstream_parent` must contain a valid B-id, got `{parent_id}`")
            elif parent_id == idea_id:
                errors.append(f"{spec.path}: `workstream_parent` cannot self-reference `{idea_id}`")
            elif parent_id not in idea_ids:
                errors.append(f"{spec.path}: `workstream_parent` references missing workstream `{parent_id}`")

        for child_id in _build_topology_values(spec, "workstream_children"):
            if not _IDEA_ID_RE.fullmatch(child_id):
                errors.append(f"{spec.path}: `workstream_children` contains invalid B-id `{child_id}`")
                continue
            if child_id == idea_id:
                errors.append(f"{spec.path}: `workstream_children` cannot self-reference `{idea_id}`")
                continue
            if child_id not in idea_ids:
                errors.append(f"{spec.path}: `workstream_children` references missing workstream `{child_id}`")

    for idea_id, spec in sorted(ideas.items()):
        parent_values = _build_topology_values(spec, "workstream_parent")
        if parent_values:
            parent_id = parent_values[0]
            parent = ideas.get(parent_id)
            if parent is not None and idea_id not in set(_build_topology_values(parent, "workstream_children")):
                errors.append(
                    f"{parent.path}: missing reciprocal `workstream_children` entry `{idea_id}` for `{idea_id}.workstream_parent={parent_id}`"
                )

        for child_id in _build_topology_values(spec, "workstream_children"):
            child = ideas.get(child_id)
            if child is None:
                continue
            reciprocal = _build_topology_values(child, "workstream_parent")
            if not reciprocal:
                errors.append(
                    f"{child.path}: missing reciprocal `workstream_parent: {idea_id}` for `{idea_id}.workstream_children`"
                )
            elif reciprocal[0] != idea_id:
                errors.append(
                    f"{child.path}: `workstream_parent` must be `{idea_id}` to match `{idea_id}.workstream_children`"
                )

    return errors
