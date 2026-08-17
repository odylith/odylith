"""Lossless Registry rendering for explicit component contracts.

This module presents typed contract fields.  It does not infer component roles,
ownership, lifecycle, outputs, or proof from labels or responsibility prose.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common import display_text


def build_narrative_component_spec(
    *,
    component_id: str,
    label: str,
    path: str,
    kind: str,
    status: str,
    sources: Sequence[str],
    workstreams: Sequence[str],
    diagrams: Sequence[str] = (),
    responsibility: str = "",
    implementation_handoff: Mapping[str, Any] | None = None,
    component_contract: Mapping[str, Any],
) -> str:
    """Render every explicit typed contract field without semantic expansion."""

    handoff = implementation_handoff or {}
    ownership = _items(component_contract, "state_objects", "owned_state")
    inputs = _items(component_contract, "accepted_inputs")
    outputs = _items(component_contract, "visible_outputs", "produced_outputs")
    workflow = _items(component_contract, "workflow_labels", "states_or_transitions")
    outside = _items(component_contract, "outside_boundary")
    boundary = _items(component_contract, "boundary")
    proof = _items(component_contract, "local_proof")
    dependencies = _items(component_contract, "dependencies")
    interfaces = _items(component_contract, "interfaces")
    risks = _items(component_contract, "risks")

    lines = [
        f"# {_text(label) or _text(component_id)}",
        "",
        _planning_note(
            sources=sources,
            path=path,
            workstreams=workstreams,
            diagrams=diagrams,
        ),
        "",
        "## Component Contract",
        "",
        f"- Component ID: `{_text(component_id)}`",
        f"- Kind: `{_text(kind) or 'component'}`",
        f"- Status: `{_text(status) or 'planned'}`",
    ]
    if _text(responsibility):
        lines.append(f"- Responsibility: {_sentence(responsibility)}")
    lines.extend(_section("Owned state", ownership))
    lines.extend(_section("Accepted inputs", inputs))
    lines.extend(_section("Visible outputs", outputs))
    lines.extend(_section("Workflow and state facts", workflow))
    lines.extend(_section("Boundary", boundary))
    lines.extend(_section("Outside boundary", outside))
    lines.extend(_section("Dependencies", dependencies))
    lines.extend(_section("Interfaces", interfaces))
    lines.extend(_section("Proof obligations", proof))
    lines.extend(_section("Risks", risks))
    lines.extend(_handoff_section(handoff=handoff, path=path, workstreams=workstreams))
    lines.extend(
        [
            "",
            "## Feature History",
            "",
            (
                f"- {dt.date.today().isoformat()}: Registered {_text(label)} as a "
                f"{_text(status) or 'planned'} {_text(kind) or 'component'} from explicit contract evidence."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _planning_note(
    *,
    sources: Sequence[str],
    path: str,
    workstreams: Sequence[str],
    diagrams: Sequence[str],
) -> str:
    evidence = ", ".join(_values(sources)) or "explicit contract evidence"
    boundary = _text(path) or "not yet assigned"
    trace = [
        *(f"workstream `{item}`" for item in _values(workstreams)),
        *(f"diagram `{item}`" for item in _values(diagrams)),
    ]
    suffix = f" Trace: {', '.join(trace)}." if trace else ""
    return f"> Evidence: {evidence}. Source boundary: {boundary}.{suffix}"


def _section(title: str, values: Sequence[str]) -> list[str]:
    if not values:
        return []
    return ["", f"### {title}", "", *(f"- {_sentence(value)}" for value in values)]


def _handoff_section(
    *,
    handoff: Mapping[str, Any],
    path: str,
    workstreams: Sequence[str],
) -> list[str]:
    entries = [
        ("Source boundary", _text(path)),
        ("Workstream", _text(handoff.get("workstream_id")) or _first(workstreams)),
        ("Workstream title", _text(handoff.get("workstream_title"))),
        ("First slice", _text(handoff.get("first_slice"))),
        ("Release", _text(handoff.get("release_selector"))),
    ]
    values = [f"{name}: {value}" for name, value in entries if value]
    return _section("Implementation handoff", values)


def _items(contract: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        values = _values(contract.get(key))
        if values:
            return values
    return ()


def _values(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _text(item)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _first(values: Sequence[str]) -> str:
    rows = _values(values)
    return rows[0] if rows else ""


def _text(value: object) -> str:
    text = display_text.strip_inline_markdown_emphasis_tokens(value).replace("`", "")
    return " ".join(text.split()).strip()


def _sentence(value: object) -> str:
    text = _text(value).rstrip(".")
    return f"{text}." if text else ""


__all__ = ["build_narrative_component_spec"]
