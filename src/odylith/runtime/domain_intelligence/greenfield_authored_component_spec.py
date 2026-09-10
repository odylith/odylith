"""Render proposed Registry contracts after exact source-and-design parity.

The canonical design owns proposed responsibilities, exchanges, and proof. Exact
support events retain source actors; they are not owner-bound component facts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import datetime as dt
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN, AUTHORED_SEMANTIC_ROOT,
    authored_source_custody, first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import authored_projection_parity_issues
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import allocated_diagram_ids
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_provisional_package import provisional_exchange_text
from odylith.runtime.governance import artifact_tribunal


def is_authored_component_projection(proposal: Mapping[str, Any]) -> bool:
    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        return False
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping) or not first_path_relations_from_intent(intent):
        raise ValueError("model-authored component projection requires verified authored semantics")
    return True


def build_authored_component_authoring_inputs(
    *, root: Path, proposal: Mapping[str, Any], release_selector: str,
    backlog_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Require full deterministic parity before issuing Registry input rows."""

    if not is_authored_component_projection(proposal):
        raise ValueError("authored component input projection requires authored semantics")
    issues = authored_projection_parity_issues(proposal)
    if issues:
        raise ValueError("; ".join(issues))
    intent, authority = proposal.get("intent"), proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent, Mapping) or not isinstance(authority, Mapping):
        raise ValueError("model-authored component projection is missing sealed Product Intent authority")
    source_custody = authored_source_custody(intent=intent, authority=authority)
    workstreams_by_component, workstream_titles = _component_workstream_links(
        proposal=proposal, backlog_result=backlog_result,
    )
    diagrams_by_component = _component_diagram_links(root=root, proposal=proposal)
    rows: list[dict[str, Any]] = []
    for component in _mapping_sequence(proposal.get("components")):
        component_id = _required_scalar(component, "component_id")
        workstreams = tuple(workstreams_by_component.get(component_id, ()))
        diagrams = tuple(diagrams_by_component.get(component_id, ()))
        if not workstreams or not diagrams:
            raise ValueError(f"provisional component `{component_id}` requires exact workstream and diagram trace links")
        row = {
            **deepcopy(dict(component)),
            "path": _required_scalar(component, "intended_path"),
            "category": "application", "owner": "repo", "product_layer": "application",
            "sources": (AUTHORED_SEMANTIC_ROOT,),
            "workstreams": workstreams, "diagrams": diagrams, "risks": (),
            "implementation_handoff": {
                "workstream_id": workstreams[0],
                "workstream_title": workstream_titles[workstreams[0]],
                "release_selector": str(release_selector or "").strip(),
            },
            "source_custody": source_custody,
        }
        _provisional_component_contract(row)
        rows.append(row)
    return tuple(rows)


def build_authored_component_registry_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    _require_authored_custody(row)
    _provisional_component_contract(row)
    component_id, label = _required_scalar(row, "component_id"), _required_scalar(row, "label")
    return {
        "component_id": component_id, "name": label,
        "kind": _required_scalar(row, "kind"), "category": _required_scalar(row, "category"),
        "qualification": _required_scalar(row, "qualification"), "aliases": [],
        "path_prefixes": [_required_scalar(row, "path")],
        "workstreams": list(_required_sequence(row, "workstreams")),
        "diagrams": list(_required_sequence(row, "diagrams")),
        "owner": _required_scalar(row, "owner"), "status": _required_scalar(row, "status"),
        "what_it_is": f"{label} is a proposed logical component. Proposed responsibility: {row['responsibility']}",
        "why_tracked": (
            "The provisional design assigns this capability a delivery and verification contract. "
            "Source-event support does not establish implementation or transfer actor ownership."
        ),
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": list(_required_sequence(row, "sources")), "subcomponents": [],
        "product_layer": _required_scalar(row, "product_layer"),
    }


def build_authored_component_spec(row: Mapping[str, Any]) -> str:
    """Keep proposed design and unchanged source-event support visibly separate."""

    _require_authored_custody(row)
    contract = _provisional_component_contract(row)
    component = contract["provisional_component"]
    workstreams, diagrams = _required_sequence(row, "workstreams"), _required_sequence(row, "diagrams")
    lines = [
        f"# {row['label']}", "",
        "> Proposed logical component; no implementation or deployment is asserted.", "",
        "## Component Snapshot", "",
        f"- Component ID: `{row['component_id']}`", f"- Kind: `{row['kind']}`",
        f"- Status: `{row['status']}`", f"- Qualification: `{row['qualification']}`",
        f"- Proposed path: `{row['path']}`",
        f"- Design authority: `{AUTHORED_SEMANTIC_ROOT}.provisional_design`", "",
        "## Proposed responsibility", "", _evidence_block(component["responsibility"]), "",
        "## Proposed inputs and outputs", "",
        *([_evidence_block(provisional_exchange_text(exchange)) for exchange in contract["exchanges"]]
          or ["No component exchanges are proposed for this capability."]), "",
        "## Proposed verification", "", _evidence_block(component["verification"]), "",
        "## Source-event support", "",
        "These exact source events support the design; their actors retain ownership of their actions.", "",
    ]
    for reference, event in zip(contract["support_event_refs"], contract["supporting_events"], strict=True):
        lines.extend([
            f"### Event {event['order']} — {event['actor_fact_quote']}", "",
            f"- Source relation: `{reference}`", f"- Source actor kind: `{event['actor_kind']}`", "",
            _evidence_block(event["event_quote"]), "",
        ])
    lines.extend([
        "## Trace links", "", f"- Canonical design row: `{contract['design_ref']}`",
        *[f"- Workstream: `{value}`" for value in workstreams],
        *[f"- Diagram: `{value}`" for value in diagrams], "",
        "## Feature History", "", _feature_history_line(workstreams[0]), "",
    ])
    return "\n".join(lines)


def _provisional_component_contract(row: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = row.get("component_contract")
    fields = {"authority_kind", "design_ref", "provisional_component", "support_event_refs", "supporting_events", "exchanges"}
    if (
        row.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN
        or row.get("authority_kind") != "provisional_design"
        or not isinstance(contract, Mapping) or set(contract) != fields
        or contract.get("authority_kind") != "provisional_design"
    ):
        raise ValueError("Registry component requires the closed provisional design contract")
    component = contract.get("provisional_component")
    if not isinstance(component, Mapping):
        raise ValueError("Registry component is missing its canonical provisional row")
    checks = {
        "component_id": component.get("key"), "label": component.get("name"),
        "responsibility": component.get("responsibility"),
        "validation": [component.get("verification")], "kind": "component",
    }
    if any(row.get(key) != value for key, value in checks.items()):
        raise ValueError("Registry component drifted from its canonical proposed fields")
    exchanges = contract.get("exchanges")
    if not isinstance(exchanges, list) or any(not isinstance(item, Mapping) for item in exchanges):
        raise ValueError("Registry component has malformed proposed exchanges")
    if row.get("interfaces") != [provisional_exchange_text(item) for item in exchanges]:
        raise ValueError("Registry component drifted from its proposed exchanges")
    if row.get("dependencies") != []:
        raise ValueError("Registry component cannot infer dependencies from proposed exchanges")
    events, orders = contract.get("supporting_events"), component.get("supported_event_orders")
    if not isinstance(events, list) or any(not isinstance(event, Mapping) for event in events):
        raise ValueError("Registry component has malformed source-event support")
    if [event.get("order") for event in events] != orders:
        raise ValueError("Registry component drifted from its source-event support")
    if contract.get("support_event_refs") != [
        f"/authored_semantics/first_path_relations/{order - 1}" for order in orders
    ]:
        raise ValueError("Registry component drifted from exact source-event references")
    return contract


def _feature_history_line(workstream_id: str) -> str:
    plan_href = f"odylith/radar/radar.html?view=plan&workstream={workstream_id}"
    return (
        f"- {dt.date.today().isoformat()}: Initial provisional component projected from sealed Product Intent. "
        f"(Plan: [{workstream_id}]({plan_href}))"
    )


def _require_authored_custody(row: Mapping[str, Any]) -> None:
    custody = row.get("source_custody")
    if not isinstance(custody, Mapping) or not artifact_tribunal.source_custody_valid(custody):
        raise ValueError("authored component projection is missing its exact semantic custody contract")


def _required_scalar(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"authored component projection requires `{key}`")
    return value


def _mapping_sequence(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _required_sequence(row: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = _sequence(row.get(key))
    if not values:
        raise ValueError(f"authored component projection requires `{key}`")
    return values


def _sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _component_workstream_links(
    *, proposal: Mapping[str, Any], backlog_result: Mapping[str, Any],
) -> tuple[dict[str, tuple[str, ...]], dict[str, str]]:
    proposal_rows, created_rows = _mapping_sequence(proposal.get("backlog")), _mapping_sequence(backlog_result.get("created"))
    if len(created_rows) != len(proposal_rows):
        raise ValueError("authored component projection is missing allocated workstream links")
    links: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    for proposed, created in zip(proposal_rows, created_rows, strict=True):
        workstream_id = _required_scalar(created, "idea_id")
        titles[workstream_id] = _required_scalar(proposed, "title")
        for component_id in _sequence(proposed.get("component_focus")):
            links.setdefault(component_id, []).append(workstream_id)
    return ({key: tuple(dict.fromkeys(values)) for key, values in links.items()}, titles)


def _component_diagram_links(*, root: Path, proposal: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    diagram_rows = _mapping_sequence(proposal.get("diagrams"))
    diagram_ids = allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
    links: dict[str, list[str]] = {}
    for diagram, diagram_id in zip(diagram_rows, diagram_ids, strict=True):
        for component_id in _sequence(diagram.get("related_components")):
            links.setdefault(component_id, []).append(diagram_id)
    return {key: tuple(dict.fromkeys(values)) for key, values in links.items()}


def _evidence_block(value: str) -> str:
    return "\n".join(f"> {line}" for line in value.splitlines())


__all__ = [
    "AUTHORED_SEMANTIC_ROOT", "build_authored_component_authoring_inputs",
    "build_authored_component_registry_entry", "build_authored_component_spec",
    "is_authored_component_projection",
]
