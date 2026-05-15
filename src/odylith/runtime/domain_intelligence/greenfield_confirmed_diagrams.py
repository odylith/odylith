"""Atlas diagram helpers for confirmed greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def confirmed_diagrams(
    *,
    label: str,
    components: list[dict[str, Any]],
    diagram_slugs: Mapping[str, str],
    product_story: str = "",
    first_path: str = "",
    proof_boundary: str = "",
    human_actors: list[str] | None = None,
    external_systems: list[str] | None = None,
    internal_systems: list[str] | None = None,
) -> list[dict[str, Any]]:
    component_rows = [
        {
            "name": str(row["label"]),
            "description": _component_description(row, first_path=first_path, proof_boundary=proof_boundary),
        }
        for row in components
    ]
    workstreams = [
        f"Establish {label} Program",
        f"Prove {str(components[0]['label']) if components else label}",
        f"Define {label} Product Boundaries",
    ]
    story = product_story or f"{label} context around the accepted first workflow."
    actors = human_actors or [f"{label} product user"]
    externals = external_systems or []
    internals = internal_systems or [str(row.get("label", "")) for row in components]
    return [
        {
            "slug": diagram_slugs["context"],
            "title": "System Context View",
            "kind": "flowchart",
            "summary": f"{story} This view separates human actors, external systems, and product-owned components.",
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": workstreams,
            "related_components": [str(row["component_id"]) for row in components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _context_mermaid(label=label, actors=actors, external_systems=externals, components=components),
        },
        {
            "slug": diagram_slugs["sequence"],
            "title": "First Workflow Sequence",
            "kind": "sequenceDiagram",
            "summary": f"Walk the accepted first workflow in product terms: {first_path}",
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": workstreams,
            "related_components": [str(row["component_id"]) for row in components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _sequence_mermaid(label=label, actors=actors, components=components, first_path=first_path),
        },
        {
            "slug": diagram_slugs["ownership"],
            "title": "Ownership And Proof View",
            "kind": "flowchart",
            "summary": f"Show which product systems own state, evidence, external boundaries, and proof for release readiness: {proof_boundary}",
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": component_rows,
            "related_workstream_titles": workstreams,
            "related_components": [str(row["component_id"]) for row in components],
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "mermaid_source": _ownership_mermaid(
                label=label,
                components=components,
                internal_systems=internals,
                proof_boundary=proof_boundary,
            ),
        },
    ]


def _component_description(row: Mapping[str, Any], *, first_path: str, proof_boundary: str) -> str:
    label = str(row.get("label", "")).strip() or "Component"
    responsibility = str(row.get("responsibility", "")).strip()
    boundary = str(row.get("boundary", "")).strip()
    description = responsibility or boundary or f"{label} participates in the accepted first workflow."
    if first_path:
        description += f" It matters for release 0.0.1 because the first workflow depends on: {first_path}"
    if proof_boundary:
        description += f" Proof must stay inside: {proof_boundary}"
    return description


def _context_mermaid(
    *,
    label: str,
    actors: list[str],
    external_systems: list[str],
    components: list[dict[str, Any]],
) -> str:
    lines = ["flowchart LR"]
    first_component = _node_id("component", 1)
    for index, actor in enumerate(actors[:5], start=1):
        node = _node_id("actor", index)
        lines.append(f'  {node}["{_short_label(actor)}"] --> {first_component}')
    if not components:
        lines.append(f'  {first_component}["{_escape_label(label)}<br/>product core"]')
    for index, component in enumerate(components[:7], start=1):
        node = _node_id("component", index)
        lines.append(f'  {node}["{_escape_label(str(component.get("label", "")))}"]')
        if index > 1:
            lines.append(f"  {first_component} --> {node}")
    target_component = _adapter_node(components) or first_component
    for index, external in enumerate(external_systems[:5], start=1):
        node = _node_id("external", index)
        lines.append(f'  {node}["{_short_label(external)}"] --> {target_component}')
    lines.extend(
        [
            "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("actor", index) for index in range(1, min(len(actors), 5) + 1)) + " actor;",
            "  class " + ",".join(_node_id("component", index) for index in range(1, max(1, min(len(components), 7)) + 1)) + " service;",
        ]
    )
    if external_systems:
        lines.append("  class " + ",".join(_node_id("external", index) for index in range(1, min(len(external_systems), 5) + 1)) + " external;")
    return "\n".join(lines) + "\n"


def _sequence_mermaid(*, label: str, actors: list[str], components: list[dict[str, Any]], first_path: str) -> str:
    actor = _participant_label(actors[0] if actors else f"{label} user")
    selected = components[:4] or [{"label": f"{label} product core"}]
    lines = [
        "sequenceDiagram",
        "  autonumber",
        f"  participant A as {actor}",
    ]
    for index, component in enumerate(selected, start=1):
        lines.append(f"  participant C{index} as {_participant_label(str(component.get('label', 'Component')))}")
    lines.append(f"  A->>C1: start accepted first workflow")
    if first_path:
        lines.append(f"  Note over A,C1: {_sequence_text(first_path)}")
    for index in range(1, len(selected)):
        lines.append(f"  C{index}->>C{index + 1}: pass domain state, evidence, or review responsibility")
        lines.append(f"  C{index + 1}-->>C{index}: return traceable result")
    lines.append("  C1-->>A: show current state, supporting evidence, and blocking issues")
    return "\n".join(lines) + "\n"


def _ownership_mermaid(
    *,
    label: str,
    components: list[dict[str, Any]],
    internal_systems: list[str],
    proof_boundary: str,
) -> str:
    lines = ["flowchart TB"]
    if not components:
        lines.append(f'  product["{_escape_label(label)}<br/>product boundary"] --> proof["Release<br/>proof"]')
    for index, component in enumerate(components[:7], start=1):
        node = _node_id("owner", index)
        label_text = str(component.get("label", "")) or (internal_systems[index - 1] if index <= len(internal_systems) else f"Component {index}")
        lines.append(f'  {node}["{_escape_label(label_text)}"]')
        if index > 1:
            lines.append(f"  {_node_id('owner', index - 1)} --> {node}")
    proof_node = _node_id("proof", 1)
    lines.append(f'  {proof_node}["Proof boundary<br/>{_escape_label(_trim(proof_boundary, 52))}"]')
    if components:
        lines.append(f"  {_node_id('owner', min(len(components), 7))} --> {proof_node}")
    lines.extend(
        [
            "  classDef owner fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef gate fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
            "  class " + ",".join(_node_id("owner", index) for index in range(1, max(1, min(len(components), 7)) + 1)) + " owner;",
            "  class proof1 gate;",
        ]
    )
    return "\n".join(lines) + "\n"


def _adapter_node(components: list[dict[str, Any]]) -> str:
    for index, row in enumerate(components[:7], start=1):
        if str(row.get("kind", "")).casefold() == "adapter":
            return _node_id("component", index)
    return ""


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}{index}"


def _short_label(value: str) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip() or "Actor"
    return _escape_label(_trim(text, 42))


def _participant_label(value: str) -> str:
    return _escape_label(_trim(str(value or "").split("—", 1)[0].split(":", 1)[0].strip(), 34) or "Participant")


def _sequence_text(value: str) -> str:
    return _escape_label(_trim(value, 110))


def _escape_label(value: str) -> str:
    return str(value or "").replace('"', "'").replace("\n", " ").strip()


def _trim(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


__all__ = ["confirmed_diagrams"]
