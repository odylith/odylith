"""Project Radar workstreams from one typed semantic projection plan."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_component_projection import (
    SEMANTIC_SYSTEM_POLICY_CUSTODY,
    semantic_delivery_risks,
    semantic_evidence_tier,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_plan import (
    SemanticProjectionPlan,
    SemanticWorkstreamPlan,
)


def semantic_backlog_rows(
    *,
    plan: SemanticProjectionPlan,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    success_metrics: Sequence[str],
    proof_boundary: str,
) -> list[dict[str, Any]]:
    """Build one product row, adding component children only for plural topology."""

    components = {
        str(component["component_id"]): component
        for component in plan.components
    }
    rows: list[dict[str, Any]] = []
    for workstream in plan.workstream_plans:
        if workstream.kind == "product":
            rows.append(
                _product_row(
                    workstream=workstream,
                    plan=plan,
                    problem=problem,
                    customer=customer,
                    opportunity=opportunity,
                    product_view=product_view,
                    success_metrics=success_metrics,
                    proof_boundary=proof_boundary,
                )
            )
            continue
        component_id = workstream.component_ids[0]
        rows.append(
            _component_row(
                workstream=workstream,
                component=components[component_id],
                customer=customer,
                opportunity=opportunity,
                success_metrics=success_metrics,
                diagram_slugs=plan.diagram_slugs,
            )
        )
    return rows


def _product_row(
    *,
    workstream: SemanticWorkstreamPlan,
    plan: SemanticProjectionPlan,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    success_metrics: Sequence[str],
    proof_boundary: str,
) -> dict[str, Any]:
    return _row(
        title=workstream.title,
        problem=problem,
        customer=customer,
        opportunity=opportunity,
        product_view=product_view,
        success_metrics=success_metrics,
        first_slice=proof_boundary,
        component_focus=workstream.component_ids,
        diagrams=_diagram_slugs(workstream, plan.diagram_slugs),
        dependencies=_component_values(plan.components, "dependencies"),
        interfaces=_component_values(plan.components, "interfaces"),
        domain_risk="The first path can drift if delivery no longer matches the sealed graph.",
        semantic_fact_refs=_component_fact_refs(plan.components),
        semantic_fact_custody=_component_fact_custody(plan.components),
        custody_state=SEMANTIC_SYSTEM_POLICY_CUSTODY,
    )


def _component_row(
    *,
    workstream: SemanticWorkstreamPlan,
    component: Mapping[str, Any],
    customer: str,
    opportunity: str,
    success_metrics: Sequence[str],
    diagram_slugs: Mapping[str, str],
) -> dict[str, Any]:
    label = str(component["label"])
    responsibility = str(component["responsibility"])
    component_metrics = [
        str(value)
        for value in component.get("validation", ())
        if str(value).strip()
    ] or list(success_metrics)
    dependencies = [
        str(value)
        for value in component.get("dependencies", ())
        if str(value).strip()
    ]
    interfaces = [
        str(value)
        for value in component.get("interfaces", ())
        if str(value).strip()
    ]
    component_role = str(component.get("component_role") or "").strip()
    result_summary = str(component.get("result_summary") or "").strip()
    if not result_summary and component_role != "boundary_supporting":
        raise ValueError(
            f"semantic component `{label}` lacks a result for its typed role"
        )
    if not result_summary and not interfaces:
        raise ValueError(
            f"supporting semantic component `{label}` lacks typed boundary interfaces"
        )
    return _row(
        title=workstream.title,
        problem=f"{label} must fulfill its sealed responsibility without absorbing adjacent component scope.",
        customer=customer,
        opportunity=opportunity,
        product_view=f"{label} owns this release responsibility: {responsibility}",
        success_metrics=component_metrics,
        first_slice=responsibility,
        component_focus=workstream.component_ids,
        diagrams=_diagram_slugs(workstream, diagram_slugs),
        dependencies=dependencies,
        interfaces=interfaces,
        domain_risk=str(component.get("component_contract", {}).get("unique_failure") or ""),
        semantic_fact_refs=_component_fact_refs((component,)),
        semantic_fact_custody=_component_fact_custody((component,)),
        custody_state=str(component["custody_state"]),
    )


def _row(
    *,
    title: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    success_metrics: Sequence[str],
    first_slice: str,
    component_focus: Sequence[str],
    diagrams: Sequence[str],
    dependencies: Sequence[str],
    interfaces: Sequence[str],
    domain_risk: str,
    semantic_fact_refs: Sequence[str],
    semantic_fact_custody: Sequence[Mapping[str, str]],
    custody_state: str,
) -> dict[str, Any]:
    return {
        "title": title,
        "problem": problem,
        "customer": customer,
        "opportunity": opportunity,
        "product_view": product_view,
        "success_metrics": list(success_metrics),
        "recommended_first_slice": (
            f"Validate ownership and evidence for this bounded slice: {first_slice}"
        ),
        "component_focus": list(component_focus),
        "related_diagram_slugs": list(diagrams),
        "dependencies": list(dependencies),
        "interfaces": list(interfaces),
        "validation": [
            f"Validation evidence must demonstrate this accepted slice: {first_slice}",
            *success_metrics,
        ],
        "risks": semantic_delivery_risks(domain_risk=domain_risk),
        "rationale_lines": [
            f"- why now: {opportunity}",
            f"- expected outcome: {first_slice}",
            f"- tradeoff: keep {title} bounded to its typed facts and proof edges.",
        ],
        "why_now": opportunity,
        "ranking_basis": (
            f"{title} follows the sealed workflow order and typed implementation dependencies."
        ),
        "semantic_fact_refs": list(semantic_fact_refs),
        "semantic_fact_custody": [dict(row) for row in semantic_fact_custody],
        "custody_state": custody_state,
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": semantic_evidence_tier(custody_state),
        "workstream_type": "standalone",
    }


def _diagram_slugs(
    workstream: SemanticWorkstreamPlan,
    diagram_slugs: Mapping[str, str],
) -> list[str]:
    return [
        diagram_slugs[key]
        for key in workstream.diagram_keys
        if key in diagram_slugs
    ]


def _component_fact_refs(components: Sequence[Mapping[str, Any]]) -> list[str]:
    refs: list[str] = []
    for component in components:
        for value in (
            component.get("semantic_fact_id"),
            *(component.get("semantic_implements", ()) or ()),
        ):
            token = str(value or "").strip()
            if token and token not in refs:
                refs.append(token)
    return refs


def _component_values(
    components: Sequence[Mapping[str, Any]],
    key: str,
) -> list[str]:
    values: list[str] = []
    for component in components:
        for raw in component.get(key, ()) or ():
            value = str(raw or "").strip()
            if value and value not in values:
                values.append(value)
    return values


def _component_fact_custody(
    components: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for component in components:
        for raw in component.get("semantic_fact_custody", ()):
            if not isinstance(raw, Mapping):
                continue
            fact_id = str(raw.get("fact_id") or "").strip()
            custody_state = str(raw.get("custody_state") or "").strip()
            if fact_id and custody_state and fact_id not in seen:
                seen.add(fact_id)
                rows.append(
                    {"fact_id": fact_id, "custody_state": custody_state}
                )
    return rows


__all__ = ["semantic_backlog_rows"]
