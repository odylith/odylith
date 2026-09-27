"""Render proposed Registry contracts after exact source-and-design parity.

The canonical design owns proposed responsibilities, exchanges, and proof. Exact
support events retain source actors; they are not owner-bound component facts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import datetime as dt
from pathlib import Path
from types import MappingProxyType
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN, AUTHORED_SEMANTIC_ROOT,
    authored_source_custody, first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import authored_projection_parity_issues
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import allocated_diagram_ids
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    derive_risk_scope, provisional_design_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_package import (
    PROVISIONAL_DESIGN_ROOT, provisional_delivery_acceptance_text, provisional_exchange_text,
    provisional_risk_text,
)
from odylith.runtime.governance import artifact_tribunal


_RISK_SCOPE_AUTHORITY_ATTESTATION = object()


class _VerifiedRiskScopeAuthority:
    """Immutable in-process design authority for component risk rendering."""

    __slots__ = ("_attestation", "_design")

    def __init__(self, design: Mapping[str, Any], *, attestation: object) -> None:
        self._design = _freeze_risk_design(design)
        self._attestation = attestation

    def __deepcopy__(self, _memo: dict[int, Any]) -> _VerifiedRiskScopeAuthority:
        return self

    def scope_for(self, allocation: Mapping[str, Any]) -> dict[str, Any]:
        return derive_risk_scope(self._design, self._canonical_risk(allocation))

    def text_for(self, allocation: Mapping[str, Any]) -> str:
        canonical_allocation = {
            "risk_ref": allocation.get("risk_ref"),
            "risk_item": self._canonical_risk(allocation),
        }
        return provisional_risk_text(canonical_allocation, design=self._design)

    def _canonical_risk(self, allocation: Mapping[str, Any]) -> Mapping[str, Any]:
        risk_ref = allocation.get("risk_ref")
        risks = self._design["risk_posture"]["items"]
        index = _canonical_risk_index(risk_ref)
        if index >= len(risks):
            raise ValueError("Registry component risk reference is outside canonical design")
        canonical = _thaw_risk_design(risks[index])
        supplied = allocation.get("risk_item")
        if not isinstance(supplied, Mapping) or dict(supplied) != canonical:
            raise ValueError("Registry component risk differs from its canonical design row")
        return canonical


def _freeze_risk_design(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_risk_design(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_risk_design(item) for item in value)
    return value


def _thaw_risk_design(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_risk_design(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_risk_design(item) for item in value]
    return value


def _canonical_risk_index(value: Any) -> int:
    """Decode one exact canonical design risk reference."""

    prefix = f"{PROVISIONAL_DESIGN_ROOT}/risk_posture/items/"
    index_text = value.removeprefix(prefix) if isinstance(value, str) else ""
    if (
        not isinstance(value, str)
        or not value.startswith(prefix)
        or not index_text.isdecimal()
        or str(int(index_text)) != index_text
    ):
        raise ValueError("Registry component has an invalid canonical risk reference")
    return int(index_text)


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
    risk_scope_authority = _VerifiedRiskScopeAuthority(
        provisional_design_from_intent(intent),
        attestation=_RISK_SCOPE_AUTHORITY_ATTESTATION,
    )
    workstreams_by_component, workstream_titles, delivery_links = _component_workstream_links(
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
            "workstreams": workstreams, "diagrams": diagrams,
            "risks": tuple(component.get("risks") or ()),
            "delivery_workstream_links": {
                delivery["design_ref"]: dict(delivery_links[delivery["design_ref"]])
                for delivery in component["component_contract"]["delivery_workstreams"]
            },
            "implementation_handoff": {
                "workstream_id": workstreams[0],
                "workstream_title": workstream_titles[workstreams[0]],
                "release_selector": str(release_selector or "").strip(),
            },
            "source_custody": source_custody,
            "risk_scope_authority": risk_scope_authority,
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
    risk_scope_authority = _require_risk_scope_authority(row)
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
        "## Proposed verification", "",
        "### Boundary check", "", _evidence_block(component["verification"]), "",
        "### Linked delivery acceptance", "",
        "Proposed workstream checks; not passed checks or exhaustive component tests.", "",
    ]
    for delivery in contract["delivery_workstreams"]:
        workstream = delivery["provisional_workstream"]
        workstream_id = row["delivery_workstream_links"][delivery["design_ref"]]["workstream_id"]
        lines.extend([
            f"- Workstream: `{workstream_id}` — {workstream['title']}", "",
            _evidence_block(workstream["verification"]), "",
        ])
        if len(workstream["component_keys"]) > 1:
            lines.extend([
                "Shared acceptance across " + ", ".join(f"`{key}`" for key in workstream["component_keys"]) + ".", "",
            ])
    lines.extend([
        "## Proposed risks", "",
        *(
            [
                _evidence_block(risk_scope_authority.text_for(allocation))
                for allocation in contract["risk_allocations"]
            ]
            or ["The reviewed provisional design identified no material risk for this component."]
        ),
        "",
    ])
    lines.extend([
        "## Source-event support", "",
        "These exact source events support the design; their actors retain ownership of their actions.", "",
    ])
    for reference, event in zip(contract["support_event_refs"], contract["supporting_events"], strict=True):
        lines.extend([
            f"### Event {event['order']} — {event['actor_fact_quote']}", "",
            f"- Source relation: `{reference}`", f"- Source actor kind: `{event['actor_kind']}`", "",
            _evidence_block(event["event_quote"]), "",
        ])
    lines.extend([
        "## Trace links", "", f"- Canonical design row: `{contract['design_ref']}`",
        *[f"- Acceptance authority: `{delivery['design_ref']}/verification`"
          for delivery in contract["delivery_workstreams"]],
        *[f"- Workstream: `{value}`" for value in workstreams],
        *[f"- Diagram: `{value}`" for value in diagrams], "",
        "## Feature History", "", _feature_history_line(workstreams[0]), "",
    ])
    return "\n".join(lines)


def _provisional_component_contract(row: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = row.get("component_contract")
    fields = {
        "authority_kind", "design_ref", "provisional_component", "support_event_refs",
        "supporting_events", "exchanges", "delivery_workstreams", "risk_allocations",
    }
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
    deliveries = contract.get("delivery_workstreams")
    if not isinstance(deliveries, list) or not deliveries:
        raise ValueError("Registry component requires linked delivery acceptance")
    for delivery in deliveries:
        if (
            not isinstance(delivery, Mapping)
            or set(delivery) != {"design_ref", "provisional_workstream"}
            or not isinstance(delivery.get("design_ref"), str)
            or not isinstance(delivery.get("provisional_workstream"), Mapping)
        ):
            raise ValueError("Registry component has malformed delivery acceptance")
        workstream = delivery["provisional_workstream"]
        reference = delivery["design_ref"]
        index = reference.removeprefix(f"{PROVISIONAL_DESIGN_ROOT}/workstreams/")
        if not index.isascii() or not index.isdecimal() or reference != f"{PROVISIONAL_DESIGN_ROOT}/workstreams/{int(index)}":
            raise ValueError("Registry component has invalid delivery authority reference")
        component_keys = workstream.get("component_keys")
        if not isinstance(component_keys, list) or component.get("key") not in component_keys:
            raise ValueError("Registry component cannot inherit unrelated delivery acceptance")
        for field in ("key", "title", "verification"):
            _required_scalar(workstream, field)
    if len({delivery["provisional_workstream"]["key"] for delivery in deliveries}) != len(deliveries):
        raise ValueError("Registry component has duplicate delivery acceptance")
    if len({delivery["design_ref"] for delivery in deliveries}) != len(deliveries):
        raise ValueError("Registry component has duplicate delivery authority reference")
    if "workstreams" in row:
        _require_delivery_allocation(row, deliveries)
    checks = {
        "component_id": component.get("key"), "label": component.get("name"),
        "responsibility": component.get("responsibility"),
        "validation": [component.get("verification"), *[
            provisional_delivery_acceptance_text(delivery["provisional_workstream"])
            for delivery in deliveries
        ]], "kind": "component",
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
    risk_allocations = contract.get("risk_allocations")
    if not isinstance(risk_allocations, list) or any(
        not isinstance(item, Mapping) for item in risk_allocations
    ):
        raise ValueError("Registry component has malformed proposed risks")
    if (
        any(
            set(allocation) != {
                "risk_ref", "risk_item",
            }
            or not isinstance(allocation.get("risk_item"), Mapping)
            or set(allocation["risk_item"]) != {
                "key", "category", "statement", "trigger", "mitigation",
                "verification", "scope_paths",
            }
            for allocation in risk_allocations
        )
    ):
        raise ValueError("Registry component has invalid proposed risk references")
    try:
        risk_indices = [
            _canonical_risk_index(allocation.get("risk_ref"))
            for allocation in risk_allocations
        ]
    except ValueError as error:
        raise ValueError("Registry component has invalid proposed risk references") from error
    if len(set(risk_indices)) != len(risk_indices):
        raise ValueError("Registry component has invalid proposed risk references")
    if risk_allocations:
        risk_scope_authority = _require_risk_scope_authority(row)
        derived_scopes = [
            risk_scope_authority.scope_for(allocation)
            for allocation in risk_allocations
        ]
        if list(row.get("risks") or ()) != [
            risk_scope_authority.text_for(item) for item in risk_allocations
        ]:
            raise ValueError("Registry component drifted from its proposed risks")
        if any(
            component.get("key") not in scope.get("component_keys", ())
            for scope in derived_scopes
        ):
            raise ValueError("Registry component inherited an unrelated proposed risk")
    elif row.get("risks"):
        raise ValueError("Registry component drifted from its proposed risks")
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


def _require_delivery_allocation(row: Mapping[str, Any], deliveries: list[Mapping[str, Any]]) -> None:
    """Bind proposed delivery identity to issued Radar IDs, independent of order."""

    links = row.get("delivery_workstream_links")
    if not isinstance(links, Mapping) or set(links) != {delivery["design_ref"] for delivery in deliveries}:
        raise ValueError("Registry component delivery allocation is incomplete")
    identifiers: list[str] = []
    for delivery in deliveries:
        link = links[delivery["design_ref"]]
        if (
            not isinstance(link, Mapping) or set(link) != {"workstream_id", "workstream_key"}
            or link["workstream_key"] != delivery["provisional_workstream"]["key"]
        ):
            raise ValueError("Registry component delivery allocation has mismatched identity")
        identifiers.append(_required_scalar(link, "workstream_id"))
    workstreams = _required_sequence(row, "workstreams")
    if len(set(identifiers)) != len(identifiers) or len(workstreams) != len(identifiers) or set(workstreams) != set(identifiers):
        raise ValueError("Registry component delivery allocation differs from its workstream links")


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


def _require_risk_scope_authority(row: Mapping[str, Any]) -> _VerifiedRiskScopeAuthority:
    authority = row.get("risk_scope_authority")
    if (
        not isinstance(authority, _VerifiedRiskScopeAuthority)
        or authority._attestation is not _RISK_SCOPE_AUTHORITY_ATTESTATION
    ):
        raise ValueError("Registry component is missing its verified risk-scope authority")
    return authority


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
) -> tuple[dict[str, tuple[str, ...]], dict[str, str], dict[str, dict[str, str]]]:
    proposal_rows, created_rows = _mapping_sequence(proposal.get("backlog")), _mapping_sequence(backlog_result.get("created"))
    if len(created_rows) != len(proposal_rows):
        raise ValueError("authored component projection is missing allocated workstream links")
    links: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    delivery_links: dict[str, dict[str, str]] = {}
    for proposed, created in zip(proposal_rows, created_rows, strict=True):
        workstream_id = _required_scalar(created, "idea_id")
        if workstream_id in titles:
            raise ValueError("Registry component has duplicate allocated workstream ID")
        titles[workstream_id] = _required_scalar(proposed, "title")
        contract = proposed["provisional_workstream_contract"]
        if contract["design_ref"] in delivery_links:
            raise ValueError("Registry component has duplicate canonical delivery reference")
        delivery_links[contract["design_ref"]] = {
            "workstream_id": workstream_id,
            "workstream_key": contract["provisional_workstream"]["key"],
        }
        for component_id in _sequence(proposed.get("component_focus")):
            links.setdefault(component_id, []).append(workstream_id)
    return ({key: tuple(dict.fromkeys(values)) for key, values in links.items()}, titles, delivery_links)


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
