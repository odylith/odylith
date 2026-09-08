"""Render provisional design Atlas views beside source-grounded meaning.

The provisional design is already structurally validated.  This owner maps its
component, delivery, exchange, and source-support identities into display data;
it never infers source semantics or changes first-path ownership.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    PROVISIONAL_DESIGN_AUTHORITY_KIND,
    validate_provisional_design,
)


# Mermaid consumes decimal entities, not HTML's hexadecimal quote escapes.
# Include entity and Markdown introducers so source text is decoded only once.
_MERMAID_LABEL_ENTITIES = str.maketrans({char: f"#{ord(char)};" for char in '&<>"#`'})


def build_provisional_design_atlas_specs(
    *,
    provisional_design: Mapping[str, Any],
    relations: Sequence[Mapping[str, Any]],
    state_object: str,
    visible_result: str,
    proof_boundary: str,
    non_goals: Sequence[str],
    source_precedence: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Return three deterministic proposed-design lenses from canonical rows."""

    event_orders = tuple(int(row["order"]) for row in relations)
    design = validate_provisional_design(
        provisional_design,
        event_orders=event_orders,
        source_precedence=source_precedence,
        result_event_order=next(int(row["order"]) for row in relations if row["visible_result_quote"]),
    )
    components = [
        {
            "name": row["name"],
            "description": f"Proposed responsibility: {row['responsibility']}",
        }
        for row in design["components"]
    ]
    component_ids = [row["key"] for row in design["components"]]
    workstream_titles = [row["title"] for row in design["workstreams"]]
    exchange_source, exchange_boxes = _component_exchange_view(design)
    delivery_source, delivery_boxes = _delivery_view(design)
    support_source, support_boxes = _capability_support_view(
        design=design,
        relations=relations,
        state_object=state_object,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        non_goals=non_goals,
    )
    shared = {
        "authority_kind": PROVISIONAL_DESIGN_AUTHORITY_KIND,
        "components": components,
        "component_ids": component_ids,
        "workstream_titles": workstream_titles,
    }
    return {
        "component_exchanges": {
            **shared,
            "title": "Proposed Component Exchanges",
            "summary": "Information proposed to cross logical component boundaries.",
            "read_guide": (
                "Arrows are proposed information exchanges, not source-stated integrations "
                "or separate deployments. Labels preserve each complete proposed contract."
            ),
            "source": exchange_source,
            "boxes": exchange_boxes,
        },
        "delivery_dependencies": {
            **shared,
            "title": "Proposed Delivery Dependencies and Acceptance",
            "summary": (
                "Delivery prerequisites and observable acceptance proposed for each workstream."
            ),
            "read_guide": (
                "Solid arrows are proposed delivery prerequisites. Dotted arrows connect each "
                "workstream to its proposed deliverable and verification; no check is claimed "
                "to have passed."
            ),
            "source": delivery_source,
            "boxes": delivery_boxes,
        },
        "capability_support": {
            **shared,
            "title": "Proposed Capability Support and Source Facts",
            "summary": (
                "Proposed component support for source-stated actions, with source-stated "
                "state, result, and proof."
            ),
            "read_guide": (
                "Each group pairs a proposed responsibility with its supported source actions "
                "and proposed verification, not a passed check. Repeated action IDs refer to the "
                "same source action, not additional events or execution order. Support does not "
                "transfer the stated actor's action to a component. Source-stated facts are "
                "an edge-free context inventory; no transition or causal topology is inferred."
            ),
            "source": support_source,
            "boxes": support_boxes,
        },
    }


def atlas_box(node_id: str, label: str, role: str, description: str) -> dict[str, str]:
    """Build one exact display box for sealing by the Atlas custody owner."""

    return {
        "node_id": node_id,
        "label": label,
        "role": role,
        "description": description,
    }


def mermaid_label(value: str, *, width: int = 28) -> str:
    """Escape and wrap a validated display value without truncation."""

    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "<br/>".join(line.translate(_MERMAID_LABEL_ENTITIES) for line in lines)


def styled_mermaid(lines: Sequence[str]) -> str:
    """Finish one exact Mermaid source using the authored Atlas display styles."""

    return "\n".join(
        [
            *lines,
            "  classDef personStyle fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
        ]
    ) + "\n"


def _component_exchange_view(
    design: Mapping[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    components = design["components"]
    component_ids = {row["key"]: f"component{index}" for index, row in enumerate(components, 1)}
    lines = ["flowchart TD", '  subgraph proposed["Proposed logical design — not deployments"]']
    boxes = [atlas_box(
        "proposed", "Proposed logical design — not deployments", "Container",
        "Groups proposed logical components without claiming implementation or deployment.",
    )]
    for index, component in enumerate(components, 1):
        node_id = f"component{index}"
        lines.append(f'    {node_id}["{mermaid_label(component["name"])}"]')
        boxes.append(atlas_box(
            node_id, component["name"], "Proposed component",
            f"Proposed responsibility: {component['responsibility']}",
        ))
    lines.append("  end")
    for exchange in design["exchanges"]:
        origin = component_ids[exchange["from_component"]]
        target = component_ids[exchange["to_component"]]
        lines.append(
            f'  {origin} -->|"Proposed exchange: {mermaid_label(exchange["contract"])}"| {target}'
        )
    return styled_mermaid(lines), boxes


def _delivery_view(
    design: Mapping[str, Any],
) -> tuple[str, list[dict[str, str]]]:
    workstreams = design["workstreams"]
    workstream_ids = {row["key"]: f"workstream{index}" for index, row in enumerate(workstreams, 1)}
    lines = ["flowchart TD"]
    boxes: list[dict[str, str]] = []
    for index, workstream in enumerate(workstreams, 1):
        node_id = f"workstream{index}"
        acceptance_id = f"workstream{index}_acceptance"
        acceptance = (
            f"Deliverable: {workstream['deliverable']}\n"
            f"Verification: {workstream['verification']}"
        )
        lines.extend([
            f'  {node_id}["{mermaid_label(workstream["title"])}"]',
            f'  {acceptance_id}["{mermaid_label(acceptance)}"]',
            f'  {node_id} -. "proposed acceptance" .-> {acceptance_id}',
        ])
        boxes.extend([
            atlas_box(
                node_id, workstream["title"], "Proposed workstream",
                f"Proposed deliverable: {workstream['deliverable']}",
            ),
            atlas_box(
                acceptance_id, acceptance, "Proposed delivery acceptance",
                f"Proposed verification: {workstream['verification']}",
            ),
        ])
    for workstream in workstreams:
        for dependency in workstream["depends_on"]:
            lines.append(
                f'  {workstream_ids[dependency]} -->|"proposed prerequisite"| '
                f'{workstream_ids[workstream["key"]]}'
            )
    return styled_mermaid(lines), boxes


def _capability_support_view(
    *,
    design: Mapping[str, Any],
    relations: Sequence[Mapping[str, Any]],
    state_object: str,
    visible_result: str,
    proof_boundary: str,
    non_goals: Sequence[str],
) -> tuple[str, list[dict[str, str]]]:
    events = {row["order"]: row for row in relations}
    lines = ["flowchart LR"]
    boxes: list[dict[str, str]] = []
    for index, component in enumerate(design["components"], 1):
        component_id = f"component{index}"
        support_id = f"component{index}_support"
        actions_id = f"component{index}_actions"
        verification_id = f"component{index}_verification"
        action_rows = [
            f"Source action {order} · {events[order]['actor_kind']}: "
            f"{events[order]['actor_fact_quote']}\n{events[order]['event_quote']}"
            for order in component["supported_event_orders"]
        ]
        actions = "\n\n".join(action_rows)
        actions_label = "<br/><br/>".join(
            "<br/>".join(mermaid_label(line, width=44) for line in row.splitlines())
            for row in action_rows
        )
        lines.extend([
            f'  subgraph {support_id}["Proposed support: {mermaid_label(component["name"])}"]',
            '    direction LR',
            f'    {component_id}["Responsibility<br/>{mermaid_label(component["responsibility"], width=44)}"]',
            f'    {actions_id}["{actions_label}"]',
            f'    {verification_id}["Verification<br/>{mermaid_label(component["verification"], width=44)}"]',
            f'    {component_id} -->|"proposed support"| {actions_id}',
            f'    {component_id} -. "proposed verification" .-> {verification_id}',
            "  end",
        ])
        boxes.extend([
            atlas_box(
                support_id, component["name"], "Proposed support group",
                "Groups one proposed responsibility, its source-action references and verification.",
            ),
            atlas_box(
                component_id, component["name"], "Proposed component",
                f"Proposed responsibility: {component['responsibility']}",
            ),
            atlas_box(
                actions_id, actions, "Supported source actions",
                "Exact source-action references; support does not transfer actor ownership.",
            ),
            atlas_box(
                verification_id, component["verification"],
                "Proposed boundary verification",
                f"Proposed verification for {component['name']}: {component['verification']}",
            ),
        ])
    lines.extend([
        '  subgraph source_facts["Source-stated facts"]',
        f'    state["State object<br/>{mermaid_label(state_object)}"]',
        f'    result["Visible result<br/>{mermaid_label(visible_result)}"]',
        f'    proof["Proof boundary<br/>{mermaid_label(proof_boundary)}"]',
    ])
    boxes.extend([
        atlas_box(
            "source_facts", "Source-stated facts", "Source-grounded context",
            "Groups source-stated state, result, proof, and non-goals without "
            "inferring transitions.",
        ),
        atlas_box(
            "state", state_object, "State object",
            f"Source-stated state object: {state_object}",
        ),
        atlas_box(
            "result", visible_result, "Visible result",
            f"Source-stated visible result: {visible_result}",
        ),
        atlas_box(
            "proof", proof_boundary, "Proof boundary",
            f"Source-stated proof boundary: {proof_boundary}",
        ),
    ])
    for index, non_goal in enumerate(non_goals, 1):
        lines.append(f'    non_goal{index}["Non-goal<br/>{mermaid_label(non_goal)}"]')
        boxes.append(atlas_box(
            f"non_goal{index}", non_goal, "Non-goal",
            f"Source-stated work outside scope: {non_goal}",
        ))
    lines.append("  end")
    return styled_mermaid(lines), boxes


__all__ = [
    "atlas_box",
    "build_provisional_design_atlas_specs",
    "mermaid_label",
    "styled_mermaid",
]
