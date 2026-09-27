"""Project one required provisional design into Registry and Radar proposals.

Source relations support proposed capabilities without transferring the source
performer's ownership. Decisions remain source facts or visible assumptions;
delivery, exchanges, and verification remain explicitly proposed design.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_assumptions import (
    DECISION_FIELDS,
    assumption_targets,
    decision_copy,
    require_decision_assumptions,
)
from odylith.runtime.domain_intelligence.greenfield_authored_radar_ordering import (
    build_authored_ordering_decision,
)
from odylith.runtime.domain_intelligence.greenfield_authored_first_run import (
    authored_event_display_text,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    derive_risk_scope, provisional_design_from_intent,
)


PROVISIONAL_DESIGN_ROOT = "/authored_semantics/provisional_design"


def build_provisional_components(
    *, intent: Mapping[str, Any], product_slug: str,
) -> list[dict[str, Any]]:
    """Keep proposed component contracts separate from exact support events."""

    design = provisional_design_from_intent(intent)
    events = {row["order"]: row for row in first_path_relations_from_intent(intent)}
    risk_allocations = build_provisional_risk_allocations(design)
    rows: list[dict[str, Any]] = []
    for index, component in enumerate(design["components"]):
        key = component["key"]
        allocated_risks = [
            deepcopy(allocation) for allocation in risk_allocations
            if key in derive_risk_scope(design, allocation["risk_item"])["component_keys"]
        ]
        exchanges = [
            deepcopy(row) for row in design["exchanges"]
            if key in (row["from_component"], row["to_component"])
        ]
        deliveries = [
            {
                "design_ref": f"{PROVISIONAL_DESIGN_ROOT}/workstreams/{workstream_index}",
                "provisional_workstream": deepcopy(workstream),
            }
            for workstream_index, workstream in enumerate(design["workstreams"])
            if key in workstream["component_keys"]
        ]
        contract = {
            "authority_kind": "provisional_design",
            "design_ref": f"{PROVISIONAL_DESIGN_ROOT}/components/{index}",
            "provisional_component": deepcopy(component),
            "support_event_refs": [
                f"/authored_semantics/first_path_relations/{order - 1}"
                for order in component["supported_event_orders"]
            ],
            "supporting_events": [
                deepcopy(events[order]) for order in component["supported_event_orders"]
            ],
            "exchanges": exchanges,
            "delivery_workstreams": deliveries,
            "risk_allocations": allocated_risks,
        }
        rows.append({
            "component_id": key,
            "label": component["name"],
            "kind": "component",
            "intended_path": f"src/{product_slug}/{key}",
            "responsibility": component["responsibility"],
            "boundary": "Proposed logical ownership; no implementation or deployment is asserted.",
            # Exchange direction does not establish an implementation dependency.
            "dependencies": [],
            "interfaces": [provisional_exchange_text(row) for row in exchanges],
            "validation": [component["verification"], *[
                provisional_delivery_acceptance_text(delivery["provisional_workstream"])
                for delivery in deliveries
            ]],
            "risks": [
                provisional_risk_text(allocation, design=design)
                for allocation in allocated_risks
            ],
            "status": "planned",
            "qualification": "candidate",
            "evidence_tier": "user_intent",
            "release_scope": "first_release",
            "authority_kind": "provisional_design",
            "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            "component_contract": contract,
        })
    return rows


def build_provisional_backlog(
    *,
    intent: Mapping[str, Any],
    diagram_slugs: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Give every proposed delivery local scope and canonical decision references."""

    require_decision_assumptions(intent)
    design = provisional_design_from_intent(intent)
    assumptions = intent.get("assumptions", [])
    assumption_refs = assumption_targets(assumptions)
    decision_refs = {
        field: f"/{field}" if intent.get(field) else assumption_refs[field]
        for field in DECISION_FIELDS
    }
    components = {row["key"]: row for row in design["components"]}
    workstreams = {row["key"]: row for row in design["workstreams"]}
    events = {row["order"]: row for row in first_path_relations_from_intent(intent)}
    risk_allocations = build_provisional_risk_allocations(design)
    rows: list[dict[str, Any]] = []
    for index, workstream in enumerate(design["workstreams"]):
        component_keys = workstream["component_keys"]
        event_orders = sorted({
            order for key in component_keys for order in components[key]["supported_event_orders"]
        })
        supporting_events = [deepcopy(events[order]) for order in event_orders]
        allocated_risks = [
            deepcopy(allocation) for allocation in risk_allocations
            if workstream["key"]
            in derive_risk_scope(design, allocation["risk_item"])["workstream_keys"]
        ]
        event_scope = [
            f"Event {event['order']}\n{authored_event_display_text(event)}"
            for event in supporting_events
        ]
        component_scope = [
            f"{components[key]['name']} — {components[key]['responsibility']}"
            for key in component_keys
        ]
        exchanges = [
            deepcopy(row) for row in design["exchanges"]
            if row["from_component"] in component_keys or row["to_component"] in component_keys
        ]
        deliverable = f"Proposed deliverable — {workstream['deliverable']}"
        local_problem = (
            "Unimplemented assigned source-event support — "
            + ", ".join(f"Event {order}" for order in event_orders)
            + "."
        )
        local_customer = f"Customer or beneficiary — {decision_copy(intent, 'customer')}"
        local_opportunity = "Proposed component scope:\n\n" + _bullets(component_scope)
        product_view = f"Proposed workstream outcome — {workstream['deliverable']}"
        verification = [f"Proposed acceptance — {workstream['verification']}"]
        dependencies = [workstreams[key]["title"] for key in workstream["depends_on"]]
        dependents = [
            row["title"] for row in workstreams.values() if workstream["key"] in row["depends_on"]
        ]
        prerequisite_reason = f"Requires {', '.join(dependencies)} first." if dependencies else "No prerequisites."
        dependent_reason = (
            f"Enables {', '.join(dependents)}." if dependents
            else "No other proposed workstream depends on this delivery."
        )
        if dependencies:
            rollout = f"Proposed delivery sequence — Start after {', '.join(dependencies)}."
        else:
            rollout = "Proposed delivery sequence — Begin without a proposed prerequisite."
        component_checks = [
            f"Proposed component check — {components[key]['name']}: "
            f"{components[key]['verification']}"
            for key in component_keys
        ]
        interfaces = [provisional_exchange_text(row) for row in exchanges]
        design_ref = f"{PROVISIONAL_DESIGN_ROOT}/workstreams/{index}"
        proof_section = (
            "Source Proof Boundary"
            if intent.get("proof_boundary")
            else "Proposed Proof Checkpoint"
        )
        sections = {
            "Proposed Solution": deliverable,
            "Scope": "Proposed logical responsibilities:\n\n" + _bullets([
                components[key]["responsibility"] for key in component_keys
            ]),
            "Non-Goals": "Project-level non-goals remain governed by the Product Intent.",
            "Risks": _bullets(
                provisional_risk_posture_texts(
                    design=design,
                    risk_posture=design["risk_posture"],
                    allocated_risks=allocated_risks,
                    scope_kind="workstream",
                ),
            ),
            "Dependencies": _bullets(dependencies, empty="No proposed delivery dependencies."),
            "Validation": _bullets(verification),
            "Rollout": rollout,
            "Why Now": local_opportunity,
            "Impacted Components": _bullets([components[key]["name"] for key in component_keys]),
            "Interface Changes": _bullets(interfaces, empty="No proposed component exchanges."),
            "Migration/Compatibility": "Provisional greenfield design; no existing implementation or migration is asserted.",
            "Test Strategy": _bullets(component_checks),
            "Open Questions": "Project-level questions remain governed by the Product Intent.",
            "Operational Constraints": (
                "Project-level operating constraints remain governed by the Product Intent."
            ),
            "Source Success Metrics": (
                "Project-level success metrics remain governed by the Product Intent."
            ),
            proof_section: (
                "The project proof decision remains governed by the Product Intent."
            ),
            "Source Event Support": _bullets(event_scope),
            "Design Authority": (
                "This workstream and its component ownership, exchanges, deliverable, and acceptance "
                "are provisional design. Source-event support does not transfer the original actor's ownership."
            ),
        }
        rows.append({
            "title": workstream["title"],
            "workstream_type": "standalone",
            "workstream_role": "provisional_design",
            "problem": local_problem,
            "customer": local_customer,
            "opportunity": local_opportunity,
            "product_view": product_view,
            "success_metrics": verification,
            "priority": "P1",
            "sizing": "M",
            "complexity": "Medium",
            "recommended_first_slice": deliverable,
            "deliverable": workstream["deliverable"],
            "component_focus": list(component_keys),
            "related_diagram_slugs": list(diagram_slugs.values()),
            "dependencies": dependencies,
            "interfaces": interfaces,
            "validation": verification,
            "evidence_tier": "user_intent",
            "authority_kind": "provisional_design",
            "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            "ordering_decision": build_authored_ordering_decision(
                why_now=local_opportunity,
                expected_outcome=deliverable,
                deferred_scope=[],
                ranking_basis=f"Proposed dependency order — {prerequisite_reason} {dependent_reason}",
            ),
            "provisional_workstream_contract": {
                "authority_kind": "provisional_design",
                "design_ref": design_ref,
                "provisional_workstream": deepcopy(workstream),
                "decision_refs": dict(decision_refs),
                "support_event_refs": [
                    f"/authored_semantics/first_path_relations/{order - 1}" for order in event_orders
                ],
                "supporting_events": supporting_events,
                "exchanges": exchanges,
                "risk_allocations": allocated_risks,
            },
            "radar_sections": sections,
        })
    return rows


def provisional_delivery_acceptance_text(workstream: Mapping[str, Any]) -> str:
    """Keep delivery acceptance owned by its workstream, including shared work."""

    return f"Proposed delivery acceptance — {workstream['title']}: {workstream['verification']}"


def provisional_exchange_text(exchange: Mapping[str, Any]) -> str:
    """Render a proposed contract without presenting it as an observed exchange."""

    return (
        f"Proposed exchange — {exchange['from_component']} → {exchange['to_component']}: "
        f"{exchange['contract']}"
    )


def build_provisional_risk_allocations(
    design: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Bind unchanged risk meaning to its canonical design reference."""

    return [
        {
            "risk_ref": f"{PROVISIONAL_DESIGN_ROOT}/risk_posture/items/{index}",
            "risk_item": deepcopy(risk),
        }
        for index, risk in enumerate(design["risk_posture"]["items"])
    ]


def provisional_risk_text(
    allocation: Mapping[str, Any], *, design: Mapping[str, Any],
) -> str:
    """Render one reviewed proposed risk without promoting it to accepted fact."""

    risk = allocation["risk_item"]
    scope = derive_risk_scope(design, risk)
    return (
        f"Proposed risk — {risk['statement']}\n"
        f"Category: {risk['category']}\nTrigger: {risk['trigger']}\n"
        f"Mitigation: {risk['mitigation']}\nVerification: {risk['verification']}\n"
        "Scope: "
        f"components [{', '.join(scope['component_keys'])}]; "
        f"workstreams [{', '.join(scope['workstream_keys'])}]; "
        "source events ["
        + ", ".join(str(order) for order in scope["event_orders"])
        + "]."
    )


def provisional_risk_posture_texts(
    *,
    design: Mapping[str, Any],
    risk_posture: Mapping[str, Any],
    allocated_risks: Sequence[Mapping[str, Any]],
    scope_kind: str,
) -> list[str]:
    """Keep reviewed risk meaning visible for material and no-material scopes."""

    if allocated_risks:
        return [
            provisional_risk_text(allocation, design=design)
            for allocation in allocated_risks
        ]
    rationale = str(risk_posture["rationale"])
    if risk_posture["status"] == "no_material_risks_identified":
        return [f"Reviewed no-material-risk posture — {rationale}"]
    return [
        f"No reviewed material risk is allocated to this {scope_kind}. "
        f"Overall reviewed posture — {rationale}"
    ]


def _bullets(values: Sequence[str], *, empty: str = "") -> str:
    return "\n".join(f"- {value}" for value in values) or empty
