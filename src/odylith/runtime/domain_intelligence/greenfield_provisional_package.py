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
    assumption_preview_values,
    assumption_targets,
    decision_copy,
    require_decision_assumptions,
)
from odylith.runtime.domain_intelligence.greenfield_authored_radar_ordering import (
    build_authored_ordering_decision,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    provisional_design_from_intent,
)


PROVISIONAL_DESIGN_ROOT = "/authored_semantics/provisional_design"


def build_provisional_components(
    *, intent: Mapping[str, Any], product_slug: str,
) -> list[dict[str, Any]]:
    """Keep proposed component contracts separate from exact support events."""

    design = provisional_design_from_intent(intent)
    events = {row["order"]: row for row in first_path_relations_from_intent(intent)}
    rows: list[dict[str, Any]] = []
    for index, component in enumerate(design["components"]):
        key = component["key"]
        exchanges = [
            deepcopy(row) for row in design["exchanges"]
            if key in (row["from_component"], row["to_component"])
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
            "validation": [component["verification"]],
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
    """Give every proposed delivery canonical decisions and distinct acceptance."""

    require_decision_assumptions(intent)
    design = provisional_design_from_intent(intent)
    assumptions = intent.get("assumptions", [])
    assumption_refs = assumption_targets(assumptions)
    decisions = {
        field: (f"Source fact — {intent[field]}" if intent.get(field) else decision_copy(intent, field))
        for field in DECISION_FIELDS
    }
    decision_refs = {
        field: f"/{field}" if intent.get(field) else assumption_refs[field]
        for field in DECISION_FIELDS
    }
    components = {row["key"]: row for row in design["components"]}
    workstreams = {row["key"]: row for row in design["workstreams"]}
    events = {row["order"]: row for row in first_path_relations_from_intent(intent)}
    rows: list[dict[str, Any]] = []
    for index, workstream in enumerate(design["workstreams"]):
        component_keys = workstream["component_keys"]
        event_orders = sorted({
            order for key in component_keys for order in components[key]["supported_event_orders"]
        })
        supporting_events = [deepcopy(events[order]) for order in event_orders]
        exchanges = [
            deepcopy(row) for row in design["exchanges"]
            if row["from_component"] in component_keys or row["to_component"] in component_keys
        ]
        deliverable = f"Proposed deliverable — {workstream['deliverable']}"
        verification = [f"Proposed acceptance — {workstream['verification']}"]
        dependencies = [workstreams[key]["title"] for key in workstream["depends_on"]]
        interfaces = [provisional_exchange_text(row) for row in exchanges]
        design_ref = f"{PROVISIONAL_DESIGN_ROOT}/workstreams/{index}"
        sections = {
            "Proposed Solution": deliverable,
            "Scope": "Proposed logical responsibilities:\n\n" + _bullets([
                components[key]["responsibility"] for key in component_keys
            ]),
            "Non-Goals": _bullets(intent.get("non_goals", []), empty="No source-stated non-goals."),
            "Risks": "No separate risk assessment has been accepted; provisional design is not a claim of risk-free implementation.",
            "Dependencies": _bullets(dependencies, empty="No proposed delivery dependencies."),
            "Validation": _bullets(verification),
            "Rollout": deliverable,
            "Why Now": decisions["opportunity"],
            "Impacted Components": _bullets([components[key]["name"] for key in component_keys]),
            "Interface Changes": _bullets(interfaces, empty="No proposed component exchanges."),
            "Migration/Compatibility": "Provisional greenfield design; no existing implementation or migration is asserted.",
            "Test Strategy": _bullets(verification),
            "Open Questions": _bullets(intent.get("ambiguities", []), empty="No unresolved material question."),
            "Assumptions": _bullets(assumption_preview_values(assumptions), empty="No decision assumptions."),
            "Operational Constraints": _bullets(intent.get("operational_constraints", []), empty="No source-stated operating constraints."),
            "Source Success Metrics": _bullets(intent.get("success_metrics", [])),
            "Source Proof Boundary": str(intent["proof_boundary"]),
            "Source Event Support": _bullets([
                f"Event {event['order']} — {event['event_quote']}"
                for event in supporting_events
            ]),
            "Design Authority": (
                "This workstream and its component ownership, exchanges, deliverable, and acceptance "
                "are provisional design. Source-event support does not transfer the original actor's ownership."
            ),
        }
        rows.append({
            "title": workstream["title"],
            "workstream_type": "standalone",
            "workstream_role": "provisional_design",
            **decisions,
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
                why_now=decisions["opportunity"],
                expected_outcome=deliverable,
                deferred_scope=intent.get("non_goals", []),
                ranking_basis=deliverable,
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
            },
            "radar_sections": sections,
        })
    return rows


def provisional_exchange_text(exchange: Mapping[str, Any]) -> str:
    """Render a proposed contract without presenting it as an observed exchange."""

    return (
        f"Proposed exchange — {exchange['from_component']} → {exchange['to_component']}: "
        f"{exchange['contract']}"
    )


def _bullets(values: Sequence[str], *, empty: str = "") -> str:
    return "\n".join(f"- {value}" for value in values) or empty
