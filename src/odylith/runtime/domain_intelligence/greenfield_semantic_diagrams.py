"""Render adaptive Atlas drafts from one typed semantic projection plan."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_evidence_tier,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    SemanticDiagramPlan,
    SemanticProjectionEdge,
    SemanticProjectionNode,
    SemanticProjectionPlan,
    SemanticProjectionViewEdge,
)


_WATCH_PATHS = ["odylith/radar/source", "odylith/registry/source"]
_NODE_ROLES = {
    "identity": "Product identity",
    "actor": "Human actor",
    "workflow_step": "Workflow step",
    "state_object": "State object",
    "visible_output": "Visible output",
    "external_system": "External dependency",
    "internal_system": "Product responsibility",
    "component_responsibility": "Component responsibility",
    "operational_constraint": "Operational constraint",
    "non_goal": "Excluded scope",
    "assumption": "Visible assumption",
    "ambiguity": "Open ambiguity",
}
_EDGE_LABELS = {
    "owned_by": "owned by",
    "produces": "produces",
    "changes": "changes",
    "depends_on": "depends on",
    "implements": "implements",
    "constrained_by": "constrained by",
    "excludes": "excludes",
}


def semantic_diagrams(
    *,
    plan: SemanticProjectionPlan,
    backlog: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Render the one-to-four exact diagram slices selected by the plan."""

    node_by_id = plan.node_by_id
    edge_by_id = {edge.relation_id: edge for edge in plan.edges}
    view_edge_by_id = {edge.edge_id: edge for edge in plan.view_edges}
    component_ids = [str(row["component_id"]) for row in plan.components]
    component_rows = [
        {
            "name": str(row["label"]),
            "description": _component_description(row),
            "custody_state": str(row["custody_state"]),
            "evidence_tier": str(row["evidence_tier"]),
            "semantic_fact_id": str(row["semantic_fact_id"]),
        }
        for row in plan.components
    ]
    diagrams: list[dict[str, Any]] = []
    for diagram in plan.diagram_plans:
        nodes = tuple(node_by_id[fact_id] for fact_id in diagram.fact_ids)
        edges = tuple(edge_by_id[relation_id] for relation_id in diagram.relation_ids)
        view_edges = tuple(
            view_edge_by_id[edge_id] for edge_id in diagram.view_edge_ids
        )
        boxes = _diagram_boxes(nodes)
        diagrams.append(
            {
                "slug": diagram.slug,
                "title": diagram.title,
                "kind": "flowchart",
                "summary": diagram.summary,
                "read_guide": (
                    "Follow solid arrows for sealed Semantic Intent relations and "
                    "dashed then-arrows for workflow order projected from typed steps."
                ),
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": component_rows,
                "related_workstream_titles": _related_workstreams(
                    diagram=diagram,
                    backlog=backlog,
                ),
                "related_components": component_ids,
                "watch_paths": list(_WATCH_PATHS),
                "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
                "evidence_tier": semantic_evidence_tier(
                    SEMANTIC_SYSTEM_POLICY_CUSTODY
                ),
                "projection_origin": "verified_semantic_intent_graph",
                "semantic_fact_ids": list(diagram.fact_ids),
                "semantic_relation_ids": list(diagram.relation_ids),
                "projection_view_edge_ids": list(diagram.view_edge_ids),
                "diagram_boxes": [
                    {
                        "label": box["label"],
                        "role": box["role"],
                        "description": box["description"],
                    }
                    for box in boxes
                ],
                "diagram_box_custody": [
                    {
                        "box_index": index,
                        "label": box["label"],
                        "custody_state": box["custody_state"],
                        "evidence_tier": box["evidence_tier"],
                        "semantic_fact_ids": list(box["semantic_fact_ids"]),
                    }
                    for index, box in enumerate(boxes)
                ],
                "mermaid_source": _mermaid(
                    nodes=nodes,
                    edges=edges,
                    view_edges=view_edges,
                ),
            }
        )
    return diagrams


def _component_description(component: Mapping[str, Any]) -> str:
    label = str(component.get("label") or "").strip()
    responsibility = str(component.get("responsibility") or "").strip()
    result = str(component.get("result_summary") or "").strip()
    component_role = str(component.get("component_role") or "").strip()
    if result:
        contract = component.get("component_contract")
        if not isinstance(contract, Mapping):
            raise ValueError(f"semantic component `{label}` lacks its typed contract")
        accepted_inputs = str(contract.get("accepted_inputs") or "").strip()
        if not accepted_inputs:
            raise ValueError(f"semantic component `{label}` lacks typed inputs")
        return (
            f"Owns this boundary: {responsibility} "
            f"Receives {accepted_inputs}; produces {result}."
        )
    if component_role != "boundary_supporting":
        raise ValueError(
            f"semantic component `{label}` lacks a result for its typed role"
        )
    relations = [
        str(value).strip().rstrip(".")
        for value in component.get("interfaces", ())
        if str(value).strip()
    ]
    if not relations:
        raise ValueError(
            f"supporting semantic component `{label}` lacks typed boundary relations"
        )
    return (
        f"Owns this supporting boundary: {responsibility} "
        f"Typed relations: {'; '.join(relations)}."
    )


def _related_workstreams(
    *,
    diagram: SemanticDiagramPlan,
    backlog: Sequence[Mapping[str, Any]],
) -> list[str]:
    return [
        str(row["title"])
        for row in backlog
        if diagram.slug in row.get("related_diagram_slugs", ())
    ]


def _box(node: SemanticProjectionNode) -> dict[str, Any]:
    return {
        "label": " ".join(node.label.split()),
        "role": _NODE_ROLES[node.kind],
        "description": " ".join(node.statement.split()),
        "custody_state": node.custody_state,
        "evidence_tier": semantic_evidence_tier(node.custody_state),
        "semantic_fact_ids": [node.fact_id],
    }


def _diagram_boxes(
    nodes: Sequence[SemanticProjectionNode],
) -> list[dict[str, Any]]:
    """Make typed nodes uniquely addressable without changing graph meaning."""

    boxes = [_box(node) for node in nodes]
    label_counts: dict[str, int] = {}
    for box in boxes:
        key = str(box["label"]).casefold()
        label_counts[key] = label_counts.get(key, 0) + 1
    for box in boxes:
        if label_counts[str(box["label"]).casefold()] > 1:
            box["label"] = f'{box["label"]} — {box["role"]}'
    qualified_counts: dict[str, int] = {}
    for box in boxes:
        key = str(box["label"]).casefold()
        qualified_counts[key] = qualified_counts.get(key, 0) + 1
    for node, box in zip(nodes, boxes, strict=True):
        if qualified_counts[str(box["label"]).casefold()] > 1:
            box["label"] = f'{box["label"]} [{node.fact_id}]'
    return boxes


def _mermaid(
    *,
    nodes: Sequence[SemanticProjectionNode],
    edges: Sequence[SemanticProjectionEdge],
    view_edges: Sequence[SemanticProjectionViewEdge],
) -> str:
    node_ids = {
        node.fact_id: f"N{index}"
        for index, node in enumerate(nodes, 1)
    }
    lines = ["flowchart LR"]
    for node in nodes:
        lines.append(
            f'  {node_ids[node.fact_id]}["{_label(node.kind)}<br/>{_label(node.label)}"]'
        )
    for edge in edges:
        lines.append(
            f"  {node_ids[edge.subject_id]} -->|{_EDGE_LABELS[edge.kind]}| "
            f"{node_ids[edge.object_id]}"
        )
    for edge in view_edges:
        lines.append(
            f"  {node_ids[edge.subject_id]} -.->|then| {node_ids[edge.object_id]}"
        )
    people = [node_ids[node.fact_id] for node in nodes if node.kind == "actor"]
    return _styled(lines, people=people)


def _styled(lines: Sequence[str], *, people: Sequence[str]) -> str:
    result = [
        *lines,
        "  classDef semantic fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
        "  classDef person fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
    ]
    if people:
        result.append(f"  class {','.join(people)} person;")
    return "\n".join(result) + "\n"


def _label(value: Any) -> str:
    text = " ".join(str(value or "").replace('"', "'").split())
    if len(text) <= 42:
        return text
    lines: list[str] = []
    current: list[str] = []
    for word in text.split():
        candidate = " ".join([*current, word])
        if current and len(candidate) > 36:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "<br/>".join(lines[:3])


__all__ = ["semantic_diagrams"]
