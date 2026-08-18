"""Compile one deterministic delivery topology from a verified semantic graph."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_component_rows,
    semantic_evidence_tier,
)


SEMANTIC_PROJECTION_PLAN_VERSION = "odylith.greenfield.semantic-projection-plan.v3"
_FACT_KIND_ORDER = (
    "identity",
    "actor",
    "workflow_step",
    "state_object",
    "visible_output",
    "external_system",
    "internal_system",
    "component_responsibility",
    "operational_constraint",
    "non_goal",
    "assumption",
    "ambiguity",
)
_RELATION_KIND_ORDER = (
    "owned_by",
    "produces",
    "changes",
    "depends_on",
    "implements",
    "constrained_by",
    "excludes",
)
_FACT_KIND_RANK = {kind: index for index, kind in enumerate(_FACT_KIND_ORDER)}
_RELATION_KIND_RANK = {
    kind: index for index, kind in enumerate(_RELATION_KIND_ORDER)
}


@dataclass(frozen=True)
class SemanticProjectionNode:
    """One exact typed fact used by every delivery projection."""

    fact_id: str
    kind: str
    label: str
    statement: str
    order: int
    owner_kind: str
    custody_state: str
    attributes: tuple[tuple[str, str], ...]

    def attribute(self, name: str) -> str:
        return next((value for key, value in self.attributes if key == name), "")


@dataclass(frozen=True)
class SemanticProjectionEdge:
    """One exact typed relation; endpoints are never reconstructed from prose."""

    relation_id: str
    kind: str
    subject_id: str
    object_id: str
    order: int
    custody_state: str


@dataclass(frozen=True)
class SemanticProjectionViewEdge:
    """One system-policy edge used only to render an ordered projection view."""

    edge_id: str
    kind: str
    subject_id: str
    object_id: str
    order: int


@dataclass(frozen=True)
class SemanticDiagramPlan:
    """One adaptive Atlas view over an exact node and edge subset."""

    key: str
    slug: str
    title: str
    summary: str
    fact_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    view_edge_ids: tuple[str, ...]


@dataclass(frozen=True)
class SemanticWorkstreamPlan:
    """One product or component delivery slice."""

    kind: str
    title: str
    component_ids: tuple[str, ...]
    diagram_keys: tuple[str, ...]


@dataclass(frozen=True)
class SemanticProjectionPlan:
    """The sole topology decision shared by proposal, Radar, and Atlas."""

    title: str
    project_slug: str
    identity_fact_id: str
    nodes: tuple[SemanticProjectionNode, ...]
    edges: tuple[SemanticProjectionEdge, ...]
    view_edges: tuple[SemanticProjectionViewEdge, ...]
    components: tuple[Mapping[str, Any], ...]
    workflow_step_fact_ids: tuple[str, ...]
    state_fact_ids: tuple[str, ...]
    visible_output_fact_ids: tuple[str, ...]
    start_component_id: str
    diagram_plans: tuple[SemanticDiagramPlan, ...]
    workstream_plans: tuple[SemanticWorkstreamPlan, ...]

    @property
    def node_by_id(self) -> dict[str, SemanticProjectionNode]:
        return {node.fact_id: node for node in self.nodes}

    @property
    def state_labels(self) -> tuple[str, ...]:
        by_id = self.node_by_id
        return tuple(by_id[fact_id].label for fact_id in self.state_fact_ids)

    @property
    def visible_output_labels(self) -> tuple[str, ...]:
        by_id = self.node_by_id
        return tuple(by_id[fact_id].label for fact_id in self.visible_output_fact_ids)

    @property
    def diagram_slugs(self) -> dict[str, str]:
        return {diagram.key: diagram.slug for diagram in self.diagram_plans}


def build_semantic_projection_plan(
    graph: Mapping[str, Any],
    *,
    project_slug: str,
) -> SemanticProjectionPlan:
    """Compile exact graph topology once without label or statement inference."""

    nodes = tuple(sorted((_node(row) for row in graph["facts"]), key=_node_key))
    edges = tuple(sorted((_edge(row) for row in graph["relations"]), key=_edge_key))
    identities = tuple(node for node in nodes if node.kind == "identity")
    if len(identities) != 1:
        raise ValueError("verified semantic projection requires one identity fact")
    components = tuple(
        semantic_component_rows(graph, project_slug=project_slug)
    )
    if not components:
        raise ValueError("verified semantic projection requires a release component")
    workflow_step_fact_ids = _fact_ids(nodes, "workflow_step")
    view_edges = _workflow_sequence_edges(workflow_step_fact_ids)
    state_fact_ids = _fact_ids(nodes, "state_object")
    visible_output_fact_ids = _fact_ids(nodes, "visible_output")
    diagram_plans = _diagram_plans(
        title=identities[0].label,
        project_slug=project_slug,
        nodes=nodes,
        edges=edges,
        view_edges=view_edges,
        components=components,
        state_fact_ids=state_fact_ids,
        visible_output_fact_ids=visible_output_fact_ids,
    )
    workstream_plans = _workstream_plans(
        title=identities[0].label,
        components=components,
        diagrams=diagram_plans,
    )
    start_component = next(
        (
            component
            for workflow_id in workflow_step_fact_ids
            for component in components
            if workflow_id in component["semantic_implements"]
        ),
        None,
    )
    if start_component is None:
        raise ValueError(
            "verified semantic projection lacks a component for its first workflow action"
        )
    return SemanticProjectionPlan(
        title=identities[0].label,
        project_slug=project_slug,
        identity_fact_id=identities[0].fact_id,
        nodes=nodes,
        edges=edges,
        view_edges=view_edges,
        components=components,
        workflow_step_fact_ids=workflow_step_fact_ids,
        state_fact_ids=state_fact_ids,
        visible_output_fact_ids=visible_output_fact_ids,
        start_component_id=str(start_component["component_id"]),
        diagram_plans=diagram_plans,
        workstream_plans=workstream_plans,
    )


def semantic_projection_plan_mapping(
    plan: SemanticProjectionPlan,
) -> dict[str, Any]:
    """Persist the exact topology contract for downstream graph-native waves."""

    return {
        "version": SEMANTIC_PROJECTION_PLAN_VERSION,
        "project_slug": plan.project_slug,
        "identity_fact_id": plan.identity_fact_id,
        "start_component_id": plan.start_component_id,
        "nodes": [
            {
                "fact_id": node.fact_id,
                "kind": node.kind,
                "label": node.label,
                "statement": node.statement,
                "order": node.order,
                "owner_kind": node.owner_kind,
                "custody_state": node.custody_state,
                "attributes": [
                    {"name": name, "value": value}
                    for name, value in node.attributes
                ],
            }
            for node in plan.nodes
        ],
        "edges": [
            {
                "relation_id": edge.relation_id,
                "kind": edge.kind,
                "subject_id": edge.subject_id,
                "object_id": edge.object_id,
                "order": edge.order,
                "custody_state": edge.custody_state,
            }
            for edge in plan.edges
        ],
        "view_edges": [
            {
                "edge_id": edge.edge_id,
                "kind": edge.kind,
                "subject_id": edge.subject_id,
                "object_id": edge.object_id,
                "order": edge.order,
            }
            for edge in plan.view_edges
        ],
        "axes": {
            "workflow_step_fact_ids": list(plan.workflow_step_fact_ids),
            "state_fact_ids": list(plan.state_fact_ids),
            "visible_output_fact_ids": list(plan.visible_output_fact_ids),
            "component_fact_ids": [
                str(component["semantic_fact_id"])
                for component in plan.components
            ],
        },
        "components": [
            {
                "component_id": str(component["component_id"]),
                "semantic_fact_id": str(component["semantic_fact_id"]),
                "release_scope": str(component["release_scope"]),
                "component_role": str(component["component_role"]),
                "implements": list(component["semantic_implements"]),
            }
            for component in plan.components
        ],
        "workstreams": [
            {
                "kind": workstream.kind,
                "title": workstream.title,
                "component_ids": list(workstream.component_ids),
                "diagram_keys": list(workstream.diagram_keys),
            }
            for workstream in plan.workstream_plans
        ],
        "diagrams": [
            {
                "key": diagram.key,
                "slug": diagram.slug,
                "title": diagram.title,
                "summary": diagram.summary,
                "fact_ids": list(diagram.fact_ids),
                "relation_ids": list(diagram.relation_ids),
                "view_edge_ids": list(diagram.view_edge_ids),
            }
            for diagram in plan.diagram_plans
        ],
    }


def semantic_release_plan(
    *,
    plan: SemanticProjectionPlan,
    release: str,
) -> dict[str, Any]:
    """Project release membership and start ownership from typed topology."""

    workstream_titles = [row.title for row in plan.workstream_plans]
    release_components = list(plan.components)
    result_components = [
        row for row in release_components if row.get("component_role") == "result_implementing"
    ]
    supporting = [
        row for row in release_components if row.get("component_role") == "boundary_supporting"
    ]
    if not result_components:
        raise ValueError(
            "verified semantic release requires a result-implementing component"
        )
    deferred = [
        node
        for node in plan.nodes
        if node.kind == "internal_system"
        and node.attribute("release_scope") == "deferred"
    ]
    start_owner = next(
        row
        for row in result_components
        if row["component_id"] == plan.start_component_id
    )
    start_title = (
        f"Implement {start_owner['label']}"
        if len(plan.components) > 1
        else workstream_titles[0]
    )
    stateful = bool(plan.state_fact_ids)
    return {
        "provisional_release_id": (
            f"release-{plan.project_slug}-{release.replace('.', '-')}"
        ),
        "selector": release,
        "label": f"{plan.title} {release} first path",
        "strategy": (
            f"Promote {plan.title} only after graph, behavior, and release-proof "
            "evidence agree."
        ),
        "release_stages": [
            {
                "stage": "first-path",
                "label": f"{plan.title} first-path proof",
                "workstream_titles": workstream_titles,
                "release_gate": (
                    "The sealed first path passes success, blocked, and evidence checks."
                ),
            }
        ],
        "project_workstream_title": workstream_titles[0],
        "start_workstream_title": start_title,
        "target_workstream_titles": workstream_titles,
        "release_component_fact_ids": [
            str(row["semantic_fact_id"]) for row in release_components
        ],
        "result_component_fact_ids": [
            str(row["semantic_fact_id"]) for row in result_components
        ],
        "supporting_component_fact_ids": [
            str(row["semantic_fact_id"]) for row in supporting
        ],
        "deferred_component_fact_ids": [node.fact_id for node in deferred],
        "promotion_criteria": [
            "Every sealed workflow action has behavior evidence.",
            *(
                ["Every state object and visible output matches exact typed evidence and the release decision."]
                if stateful
                else ["Every visible output matches exact typed evidence and the release decision."]
            ),
            "Every readiness assertion cites validation output and exact graph facts.",
        ],
        "milestones": [
            {
                "name": f"{plan.title} release review accepted",
                "exit_criteria": (
                    "The sealed first path, operating boundaries, and proof "
                    "evidence satisfy the release gate."
                ),
            }
        ],
        "custody_state": SEMANTIC_SYSTEM_POLICY_CUSTODY,
        "evidence_tier": semantic_evidence_tier(
            SEMANTIC_SYSTEM_POLICY_CUSTODY
        ),
    }


def semantic_security_compliance(
    *,
    plan: SemanticProjectionPlan,
    proof_boundary: str,
) -> dict[str, str]:
    """Expose only accepted operating boundaries and release evidence."""

    constraints = _node_statements(plan, "operational_constraint")
    exclusions = _node_statements(plan, "non_goal")
    return {
        "release_boundary": proof_boundary,
        "operating_constraints": _plain_list(constraints, fallback="None asserted"),
        "excluded_scope": _plain_list(exclusions, fallback="None asserted"),
    }


def semantic_validation_strategy(
    *,
    plan: SemanticProjectionPlan,
    success_metrics: Sequence[str],
    proof_boundary: str,
) -> list[str]:
    """Project checks from the axes that the graph actually carries."""

    return [
        "Validate every workflow step in graph order and verify the owner declared by its relation.",
        *(
            [f"Reconstruct every state object ({_plain_list(plan.state_labels)}) from exact typed evidence and compare each accepted transition."]
            if plan.state_labels
            else []
        ),
        f"Show every visible output ({_plain_list(plan.visible_output_labels)}) and tie each to its exact producing edge.",
        f"Compare release evidence with the sealed proof boundary: {proof_boundary}",
        *success_metrics,
    ]


def _node_statements(plan: SemanticProjectionPlan, kind: str) -> tuple[str, ...]:
    return tuple(node.statement for node in plan.nodes if node.kind == kind)


def _diagram_plans(
    *,
    title: str,
    project_slug: str,
    nodes: Sequence[SemanticProjectionNode],
    edges: Sequence[SemanticProjectionEdge],
    view_edges: Sequence[SemanticProjectionViewEdge],
    components: Sequence[Mapping[str, Any]],
    state_fact_ids: tuple[str, ...],
    visible_output_fact_ids: tuple[str, ...],
) -> tuple[SemanticDiagramPlan, ...]:
    workflow_ids = _fact_ids(nodes, "workflow_step")
    actor_ids = _fact_ids(nodes, "actor")
    first_path_ids = {
        *workflow_ids,
        *actor_ids,
        *state_fact_ids,
        *visible_output_fact_ids,
    }
    first_path_edges = tuple(
        edge
        for edge in edges
        if edge.kind in {"owned_by", "changes", "produces"}
        and edge.subject_id in first_path_ids
        and edge.object_id in first_path_ids
    )
    plans = [
        SemanticDiagramPlan(
            key="first_path",
            slug=f"{project_slug}-first-path",
            title="First Path",
            summary=(
                f"Shows the ordered {title} workflow and the exact owners, "
                "state changes, and visible outputs attached to it."
            ),
            fact_ids=tuple(node.fact_id for node in nodes if node.fact_id in first_path_ids),
            relation_ids=tuple(edge.relation_id for edge in first_path_edges),
            view_edge_ids=tuple(edge.edge_id for edge in view_edges),
        )
    ]
    external_ids = _fact_ids(nodes, "external_system")
    system_ids = tuple(str(component["semantic_fact_id"]) for component in components)
    if actor_ids or external_ids:
        plans.append(
            _connected_diagram(
                key="context",
                slug=f"{project_slug}-system-context",
                title="System Context",
                summary=(
                    f"Reviews accepted {title} actors and external systems at "
                    "the product boundary."
                ),
                seed_ids=(
                    *(node.fact_id for node in nodes if node.kind == "identity"),
                    *actor_ids,
                    *system_ids,
                    *external_ids,
                ),
                relation_kinds=("owned_by", "depends_on"),
                nodes=nodes,
                edges=edges,
            )
        )
    if state_fact_ids:
        plans.append(
            _connected_diagram(
                key="state_evidence",
                slug=f"{project_slug}-state-evidence",
                title="State and Output Evidence",
                summary=(
                    f"Reviews every accepted {title} state object and visible output "
                    "with its typed workflow and system edges."
                ),
                seed_ids=(*state_fact_ids, *visible_output_fact_ids),
                relation_kinds=("changes", "produces", "implements"),
                nodes=nodes,
                edges=edges,
            )
        )
    cross_boundary_dependency = any(
        edge.kind == "depends_on"
        and edge.subject_id in system_ids
        and edge.object_id != edge.subject_id
        for edge in edges
    )
    if len(components) > 1 or cross_boundary_dependency:
        plans.append(
            _connected_diagram(
                key="component_boundaries",
                slug=f"{project_slug}-component-boundaries",
                title="Component Boundaries",
                summary=(
                    f"Reviews {title} implementation and dependency edges across "
                    "release components and external systems."
                ),
                seed_ids=(*system_ids, *external_ids),
                relation_kinds=("depends_on", "implements"),
                nodes=nodes,
                edges=edges,
            )
        )
    if not 1 <= len(plans) <= 4:
        raise ValueError("semantic projection must select between one and four diagrams")
    return tuple(plans)


def _connected_diagram(
    *,
    key: str,
    slug: str,
    title: str,
    summary: str,
    seed_ids: Sequence[str],
    relation_kinds: Sequence[str],
    nodes: Sequence[SemanticProjectionNode],
    edges: Sequence[SemanticProjectionEdge],
) -> SemanticDiagramPlan:
    selected_ids = set(seed_ids)
    selected_edge_ids: set[str] = set()
    changed = True
    while changed:
        changed = False
        for edge in edges:
            if edge.kind not in relation_kinds:
                continue
            if edge.subject_id not in selected_ids and edge.object_id not in selected_ids:
                continue
            if edge.relation_id not in selected_edge_ids:
                selected_edge_ids.add(edge.relation_id)
                changed = True
            before = len(selected_ids)
            selected_ids.update((edge.subject_id, edge.object_id))
            changed = changed or len(selected_ids) != before
    selected_edges = [
        edge for edge in edges if edge.relation_id in selected_edge_ids
    ]
    return SemanticDiagramPlan(
        key=key,
        slug=slug,
        title=title,
        summary=summary,
        fact_ids=tuple(node.fact_id for node in nodes if node.fact_id in selected_ids),
        relation_ids=tuple(edge.relation_id for edge in selected_edges),
        view_edge_ids=(),
    )


def _workflow_sequence_edges(
    workflow_fact_ids: Sequence[str],
) -> tuple[SemanticProjectionViewEdge, ...]:
    return tuple(
        SemanticProjectionViewEdge(
            edge_id=f"workflow-sequence-{index}",
            kind="workflow_sequence",
            subject_id=subject_id,
            object_id=object_id,
            order=index,
        )
        for index, (subject_id, object_id) in enumerate(
            zip(workflow_fact_ids, workflow_fact_ids[1:], strict=False)
        )
    )


def _workstream_plans(
    *,
    title: str,
    components: Sequence[Mapping[str, Any]],
    diagrams: Sequence[SemanticDiagramPlan],
) -> tuple[SemanticWorkstreamPlan, ...]:
    component_ids = tuple(str(row["component_id"]) for row in components)
    diagram_keys = tuple(diagram.key for diagram in diagrams)
    product = SemanticWorkstreamPlan(
        kind="product",
        title=f"Deliver {title} First Path",
        component_ids=component_ids,
        diagram_keys=diagram_keys,
    )
    if len(components) == 1:
        return (product,)
    diagram_by_key = {diagram.key: diagram for diagram in diagrams}
    children = []
    for component in components:
        component_fact_id = str(component["semantic_fact_id"])
        component_diagrams = tuple(
            key
            for key in diagram_keys
            if component_fact_id in diagram_by_key[key].fact_ids
        )
        children.append(
            SemanticWorkstreamPlan(
                kind="component",
                title=f"Implement {component['label']}",
                component_ids=(str(component["component_id"]),),
                diagram_keys=component_diagrams,
            )
        )
    return (product, *children)


def _node(row: Mapping[str, Any]) -> SemanticProjectionNode:
    return SemanticProjectionNode(
        fact_id=str(row["fact_id"]),
        kind=str(row["kind"]),
        label=str(row["label"]),
        statement=str(row["statement"]),
        order=int(row["order"]),
        owner_kind=str(row["owner_kind"]),
        custody_state=str(row["custody"]),
        attributes=tuple(
            (str(attribute["name"]), str(attribute["value"]).strip())
            for attribute in row.get("attributes", ())
            if isinstance(attribute, Mapping)
        ),
    )


def _edge(row: Mapping[str, Any]) -> SemanticProjectionEdge:
    return SemanticProjectionEdge(
        relation_id=str(row["relation_id"]),
        kind=str(row["kind"]),
        subject_id=str(row["subject_id"]),
        object_id=str(row["object_id"]),
        order=int(row["order"]),
        custody_state=str(row["custody"]),
    )


def _node_key(node: SemanticProjectionNode) -> tuple[int, int, str]:
    return (_FACT_KIND_RANK[node.kind], node.order, node.fact_id)


def _edge_key(edge: SemanticProjectionEdge) -> tuple[int, int, str]:
    return (_RELATION_KIND_RANK[edge.kind], edge.order, edge.relation_id)


def _fact_ids(
    nodes: Sequence[SemanticProjectionNode], kind: str
) -> tuple[str, ...]:
    return tuple(node.fact_id for node in nodes if node.kind == kind)


def _plain_list(values: Sequence[str], *, fallback: str = "") -> str:
    return ", ".join(values) or fallback


__all__ = [
    "SEMANTIC_PROJECTION_PLAN_VERSION",
    "SemanticDiagramPlan",
    "SemanticProjectionEdge",
    "SemanticProjectionNode",
    "SemanticProjectionPlan",
    "SemanticProjectionViewEdge",
    "SemanticWorkstreamPlan",
    "build_semantic_projection_plan",
    "semantic_projection_plan_mapping",
    "semantic_release_plan",
    "semantic_security_compliance",
    "semantic_validation_strategy",
]
