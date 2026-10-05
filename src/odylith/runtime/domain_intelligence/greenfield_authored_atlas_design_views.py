"""Render provisional design Atlas views beside source-grounded meaning.

The provisional design is already structurally validated.  This owner maps its
component, delivery, exchange, and source-support identities into display data;
it never infers source semantics or changes first-path ownership.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_first_run import (
    authored_event_display_text,
)
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
    proof_is_provisional: bool = False,
    source_lifecycle: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return three deterministic proposed-design lenses from canonical rows."""

    event_orders = tuple(int(row["order"]) for row in relations)
    design = validate_provisional_design(
        provisional_design,
        event_orders=event_orders,
        source_precedence=source_precedence,
        result_event_order=next((int(row["order"]) for row in relations if row["visible_result_quote"]), None),
    )
    components = [
        {
            "name": row["name"],
            "description": row["responsibility"],
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
        proof_is_provisional=proof_is_provisional,
        non_goals=non_goals,
        source_lifecycle=source_lifecycle,
    )
    source_fact_guide = (
        "a cited state lifecycle; its off-path transitions do not become first-run actions."
        if source_lifecycle and source_lifecycle.get("off_path_transitions")
        else "an edge-free context inventory; no transition or causal topology is inferred."
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
                (
                    "Proposed component support for source-stated actions and state, with an "
                    "explicitly proposed proof checkpoint."
                )
                if proof_is_provisional
                else (
                    "Proposed component support for source-stated actions, with source-stated "
                    "state, result, and proof."
                )
            ),
            "read_guide": (
                "Select a diagram box in Read mode for complete statements. Open Supporting details "
                "for source-action references and proposed boundary checks. Component support "
                "does not transfer the stated actor's action to a component. "
                "Linked workstream boxes retain the full deliverable and shared acceptance; no "
                "check is claimed to have passed or be exhaustive proof. The source-action "
                "reference box retains every full action and stated performer. References do not "
                "create additional events or execution order. "
                "Source facts and lifecycle boxes preserve their complete statements and citations. "
                "Compact labels are references, not summaries. Source-stated facts are "
                + source_fact_guide
            ),
            "source": support_source,
            "boxes": support_boxes,
        },
    }


def atlas_box(
    node_id: str, label: str, role: str, description: str,
    *, details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build one exact display box for sealing by the Atlas custody owner."""

    box: dict[str, Any] = {
        "node_id": node_id,
        "label": label,
        "role": role,
        "description": description,
    }
    if details is not None:
        box["details"] = atlas_box_details(details)
    return box


def atlas_box_details(value: Any) -> list[dict[str, str]]:
    """Validate optional literal detail rows without interpreting their meaning."""

    if not isinstance(value, list):
        raise ValueError("Atlas box details must be a list")
    rows = []
    for index, row in enumerate(value):
        if not isinstance(row, Mapping) or set(row) != {"label", "text"}:
            raise ValueError(f"Atlas box details[{index}] must contain exactly label and text")
        rows.append({
            key: required_atlas_string(row[key], f"Atlas box details[{index}].{key}")
            for key in ("label", "text")
        })
    return rows


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


def required_atlas_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty, whitespace-exact string")
    return value


def build_provisional_first_run_atlas_view(
    relations: Sequence[Mapping[str, Any]],
    *,
    design: Mapping[str, Any],
    source_precedence: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Project selected events and their declared upstream design support."""

    lines = ["flowchart TD"]
    boxes: list[dict[str, Any]] = []
    performers: dict[tuple[str, str], str] = {}
    orders = design["first_run"]["event_orders"]
    selected = set(orders)
    for relation in relations:
        if relation["order"] not in selected:
            continue
        index = relation["order"]
        event_quote = required_atlas_string(relation.get("event_quote"), "first-path event quote")
        actor_kind = required_atlas_string(relation.get("actor_kind"), "first-path actor kind")
        performer = required_atlas_string(
            relation.get("actor_fact_quote"), "first-path actor fact"
        )
        event_display = authored_event_display_text(relation)
        action_reference = (
            f"{relation['action_verb_quote']} {relation['target_quote']}"
            if relation.get("action_verb_quote") and relation.get("target_quote")
            else event_quote
        )
        lines.append(
            f'  event{index}["Source action {index}<br/>{mermaid_label(action_reference)}"]'
        )
        boxes.append(
            atlas_box(
                f"event{index}",
                event_display,
                f"{actor_kind} event",
                f"Source action {index}, performed by {performer}: {event_quote}",
            )
        )
        identity = (actor_kind, performer)
        if identity not in performers:
            performer_id = f"performer{len(performers) + 1}"
            performers[identity] = performer_id
            lines.append(f'  {performer_id}["{mermaid_label(performer)}"]')
            boxes.append(
                atlas_box(
                    performer_id,
                    performer,
                    "Typed event performer",
                    f"Source-stated {actor_kind} performer for one or more first-path events: "
                    f"{performer}",
                )
            )
        lines.append(f'  {performers[identity]} --> event{index}')
        owner = relation.get("owner_system_quote")
        if isinstance(owner, str) and owner and owner != performer:
            owner_identity = ("owner_system", owner)
            if owner_identity not in performers:
                owner_id = f"performer{len(performers) + 1}"
                performers[owner_identity] = owner_id
                lines.append(f'  {owner_id}["{mermaid_label(owner)}"]')
                boxes.append(
                    atlas_box(
                        owner_id,
                        owner,
                        "Typed event owner",
                        f"Accepted owner system for one or more first-path events: {owner}",
                    )
                )
            lines.append(f'  {performers[owner_identity]} -->|"owns event state"| event{index}')
    required = {
        (row["before_event"], row["after_event"]): row["constraint_index"]
        for row in source_precedence
        if row["before_event"] in selected and row["after_event"] in selected
    }
    for (before, after), constraint_index in required.items():
        lines.append(f'  event{before} -->|"source constraint {constraint_index}"| event{after}')
    for before, after in zip(orders, orders[1:]):
        if (before, after) not in required:
            lines.append(f'  event{before} -.-> event{after}')
    direct_components = {
        component["key"] for component in design["components"]
        if selected.intersection(component["supported_event_orders"])
    }
    supporting_components = set(direct_components)
    workstreams = {row["key"]: row for row in design["workstreams"]}
    # An exchange input or a delivery prerequisite remains necessary support
    # even when its own source actions are outside this walkthrough. Never
    # traverse outgoing exchanges to unrelated downstream consumers.
    while True:
        required_components = set(supporting_components)
        required_components.update(
            exchange["from_component"] for exchange in design["exchanges"]
            if exchange["to_component"] in supporting_components
        )
        for workstream in design["workstreams"]:
            if supporting_components.intersection(workstream["component_keys"]):
                for prerequisite in workstream["depends_on"]:
                    required_components.update(workstreams[prerequisite]["component_keys"])
        if required_components == supporting_components:
            break
        supporting_components = required_components
    component_nodes = {
        component["key"]: f"proposed_component{index}"
        for index, component in enumerate(design["components"], start=1)
        if component["key"] in supporting_components
    }
    for component in design["components"]:
        if component["key"] not in component_nodes:
            continue
        node_id = component_nodes[component["key"]]
        direct = component["key"] in direct_components
        label = "Proposed stage" if direct else "Proposed supporting component"
        lines.append(
            f'  {node_id}["{label}<br/>{mermaid_label(component["name"])}"]'
        )
        boxes.append(
            atlas_box(
                node_id,
                component["name"],
                "Proposed first-run stage" if direct else "Proposed supporting component",
                component["responsibility"],
                details=[],
            )
        )
        for order in component["supported_event_orders"]:
            if order in selected:
                lines.append(f'  event{order} -. "proposed support" .-> {node_id}')
    component_names = {row["key"]: row["name"] for row in design["components"]}
    boxes_by_id = {box["node_id"]: box for box in boxes}
    for exchange_index, exchange in enumerate(design["exchanges"], 1):
        if exchange["from_component"] not in component_nodes or exchange["to_component"] not in component_nodes:
            continue
        origin_box = boxes_by_id[component_nodes[exchange["from_component"]]]
        origin_box["details"].append({
            "label": f"Proposed exchange {exchange_index} to {component_names[exchange['to_component']]}",
            "text": exchange["contract"],
        })
    delivery_edges: set[tuple[str, str]] = set()
    for workstream in design["workstreams"]:
        for prerequisite in workstream["depends_on"]:
            for origin in workstreams[prerequisite]["component_keys"]:
                for target in workstream["component_keys"]:
                    edge = (origin, target)
                    if (
                        origin != target and origin in component_nodes and target in component_nodes
                        and edge not in delivery_edges
                    ):
                        delivery_edges.add(edge)
                        target_box = boxes_by_id[component_nodes[target]]
                        target_box["details"].append({
                            "label": "Proposed delivery prerequisite",
                            "text": f"{component_names[origin]} through {workstreams[prerequisite]['title']}.",
                        })
    return styled_mermaid(lines), boxes


def _component_exchange_view(
    design: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]]]:
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
            component["responsibility"],
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
) -> tuple[str, list[dict[str, Any]]]:
    workstreams = design["workstreams"]
    workstream_ids = {row["key"]: f"workstream{index}" for index, row in enumerate(workstreams, 1)}
    lines = ["flowchart TD"]
    boxes: list[dict[str, Any]] = []
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
    proof_is_provisional: bool,
    source_lifecycle: Mapping[str, Any] | None,
) -> tuple[str, list[dict[str, Any]]]:
    lines = ["flowchart LR"]
    boxes: list[dict[str, Any]] = []
    component_ids = {
        component["key"]: f"component{index}"
        for index, component in enumerate(design["components"], 1)
    }
    event_details = {
        event["order"]: f"Source action {event['order']} · {event['actor_kind']}\n{authored_event_display_text(event)}"
        for event in relations
    }
    for index, component in enumerate(design["components"], 1):
        component_id = component_ids[component["key"]]
        orders = ", ".join(str(order) for order in component["supported_event_orders"])
        actions = f"Source actions: {orders}"
        lines.append(
            f'  {component_id}["Proposed: {mermaid_label(component["name"], width=32)}'
            f'<br/>{mermaid_label(actions, width=32)}<br/>Select for responsibility and check"]'
        )
        boxes.append(atlas_box(
            component_id, component["name"], "Proposed component support",
            component["responsibility"],
            details=[
                {"label": "Source actions", "text": "\n\n".join(
                    event_details[order] for order in component["supported_event_orders"]
                ) or "No source action is assigned."},
                {"label": "Proposed boundary verification", "text": component["verification"]},
                {"label": "Verification source actions", "text": "\n\n".join(
                    event_details[order] for order in component["verification_event_orders"]
                ) or "No source action is assigned."},
            ],
        ))
    for index, workstream in enumerate(design["workstreams"], 1):
        acceptance_id = f"workstream{index}_acceptance"
        lines.append(
            f'  {acceptance_id}["Proposed delivery<br/>{mermaid_label(workstream["title"], width=32)}'
            '<br/>Select for acceptance"]'
        )
        boxes.append(atlas_box(
            acceptance_id, workstream["title"], "Proposed delivery acceptance",
            workstream["deliverable"],
            details=[
                {"label": "Participating components", "text": ", ".join(workstream["component_keys"])},
                {"label": "Proposed verification", "text": workstream["verification"]},
                {"label": "Verification source actions", "text": "\n\n".join(
                    event_details[order] for order in workstream["verification_event_orders"]
                ) or "No source action is assigned."},
            ],
        ))
        for key in workstream["component_keys"]:
            lines.append(f'  {component_ids[key]} -. "participates in delivery" .-> {acceptance_id}')
    actions = "\n\n".join(
        event_details[event["order"]] for event in sorted(relations, key=lambda row: row["order"])
    )
    lines.append('  source_actions["Source action reference<br/>Select for full actions and performers"]')
    boxes.append(atlas_box(
        "source_actions", "Source action reference", "Source-grounded context",
        actions + "\n\nSource identities do not imply execution order.",
    ))
    facts = [f"Source-stated state object: {state_object}"]
    if not proof_is_provisional:
        facts.extend([
            f"Source-stated visible result: {visible_result}",
            f"Source-stated proof boundary: {proof_boundary}",
        ])
    facts.extend(f"Source-stated non-goal {index}: {value}" for index, value in enumerate(non_goals, 1))
    facts_reference = "state and scope" if proof_is_provisional else "state, scope and proof"
    lines.append(f'  source_facts["Source-stated facts<br/>Select for {facts_reference}"]')
    boxes.append(atlas_box(
        "source_facts", "Source-stated facts", "Source-grounded context", "\n\n".join(facts),
    ))
    if source_lifecycle is not None:
        _append_source_lifecycle(
            lines=lines, boxes=boxes, lifecycle=source_lifecycle, component_ids=component_ids,
        )
    if proof_is_provisional:
        lines.append('  proof["Proposed proof checkpoint<br/>Assumption — select for detail"]')
        boxes.append(atlas_box(
            "proof", proof_boundary, "Proposed proof checkpoint",
            "An explicit assumption; no source-stated producer or terminal result is asserted.\n"
            f"Proposed checkpoint: {proof_boundary}",
        ))
    return styled_mermaid(lines), boxes


def _append_source_lifecycle(
    *,
    lines: list[str],
    boxes: list[dict[str, Any]],
    lifecycle: Mapping[str, Any],
    component_ids: Mapping[str, str],
) -> None:
    """Display sealed source transitions without inventing an actor or an event."""

    field_nodes: dict[str, str] = {}
    for index, field in enumerate(lifecycle["state_fields"], 1):
        node = f"state_field{index}"
        field_nodes[field["duty_id"]] = node
        quote = _source_quote(field["source_refs"])
        label = f"{field['state_object']} · {field['field']}"
        lines.append(f'  {node}["State field<br/>{mermaid_label(label, width=44)}"]')
        boxes.append(atlas_box(
            node, label, "Source-stated state field",
            f"Source: {quote}\nMeaning: {field['meaning']}",
        ))
    for index, transition in enumerate(lifecycle["off_path_transitions"], 1):
        node = f"off_path_transition{index}"
        quote = _source_quote(transition["source_refs"])
        label = f"{transition['governed_object']} · {transition['trigger']}"
        lines.append(
            f'  {node}["Off-path state transition<br/>{mermaid_label(label, width=44)}'
            '<br/>Select for source detail"]'
        )
        boxes.append(atlas_box(
            node, label, "Source-stated off-path transition",
            f"Source: {quote}\nTrigger: {transition['trigger']}\n"
            f"Governed object: {transition['governed_object']}",
        ))
        component = component_ids[transition["component_key"]]
        lines.append(f'  {component} -. "proposed lifecycle support" .-> {node}')
        for effect_index, effect in enumerate(transition["effects"], 1):
            field = field_nodes[effect["state_field_id"]]
            change = f"Change: {effect['change']}\nObservable check: {effect['observable_check']}"
            effect_node = f"{node}_effect{effect_index}"
            change_label = f"Effect {index}.{effect_index}<br/>{mermaid_label(effect['change'], width=32)}"
            lines.append(f'  {effect_node}["{change_label}"]')
            lines.append(
                f'  {node} -->|"source-stated effect"| {effect_node}'
            )
            lines.append(f'  {effect_node} -->|"changes {mermaid_label(effect["field"])}"| {field}')
            boxes.append(atlas_box(
                effect_node,
                change,
                "Source-stated state effect",
                f"Trigger: {transition['trigger']}\nField: {effect['field']}\n"
                f"Change: {effect['change']}\nObservable check: {effect['observable_check']}",
            ))


def _source_quote(source_refs: Sequence[Mapping[str, Any]]) -> str:
    if not source_refs:
        raise ValueError("source lifecycle row has no source citation")
    return "; ".join(f"“{ref['quote']}”" for ref in source_refs)


__all__ = [
    "atlas_box",
    "atlas_box_details",
    "build_provisional_design_atlas_specs",
    "build_provisional_first_run_atlas_view",
    "required_atlas_string",
    "mermaid_label",
    "styled_mermaid",
]
