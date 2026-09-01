"""Render Registry records from the closed authored component projection.

The model-authored relation set is the only semantic authority. This module
renders its owner-bound component facts and structural trace links without
inventing local boundaries, interfaces, dependencies, risks, or proof claims.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    AUTHORED_SEMANTIC_ROOT,
    authored_source_custody,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_apply_diagrams import allocated_diagram_ids
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.governance import artifact_tribunal


_AUTHORED_COMPONENT_CONTRACT_FIELDS = frozenset(
    {
        "owner_system",
        "responsibility_facts",
        "owner_bound_events",
        "event_targets",
        "visible_results",
        "recovery_events",
        "state_context",
        "external_dependencies",
        "operational_constraints",
    }
)
_UNBOUND_COMPONENT_FIELDS = (
    "boundary",
    "interfaces",
    "risks",
    "security_compliance",
)


def is_authored_component_projection(proposal: Mapping[str, Any]) -> bool:
    """Return whether a proposal carries the complete authored authority marker."""

    if proposal.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        return False
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping) or not first_path_relations_from_intent(intent):
        raise ValueError("model-authored component projection requires verified authored semantics")
    return True


def build_authored_component_authoring_inputs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Project exact authored component fields into Registry authoring inputs."""

    if not is_authored_component_projection(proposal):
        raise ValueError("authored component input projection requires authored semantics")
    components = tuple(
        row
        for row in _mapping_sequence(proposal.get("components"))
        if str(row.get("release_scope") or "").strip().casefold()
        not in {"deferred", "out_of_scope", "external"}
    )
    if not components:
        raise ValueError("model-authored component projection requires a first-release component")
    intent = proposal.get("intent")
    authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent, Mapping) or not isinstance(authority, Mapping):
        raise ValueError("model-authored component projection is missing sealed Product Intent authority")
    source_custody = authored_source_custody(intent=intent, authority=authority)

    workstreams_by_component, workstream_titles = _component_workstream_links(
        proposal=proposal,
        backlog_result=backlog_result,
    )
    diagrams_by_component = _component_diagram_links(root=root, proposal=proposal)
    rows: list[dict[str, Any]] = []
    for component in components:
        component_id = _required_scalar(component, "component_id")
        if component.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
            raise ValueError(f"authored component `{component_id}` lost its projection origin")
        label = _required_scalar(component, "label")
        path = _required_scalar(component, "intended_path")
        responsibility = _required_scalar(component, "responsibility")
        contract = _authored_component_contract(
            component,
            component_id=component_id,
            label=label,
            responsibility=responsibility,
        )
        workstreams = tuple(workstreams_by_component.get(component_id, ()))
        if not workstreams:
            raise ValueError(f"authored component `{component_id}` has no exact workstream trace link")
        diagrams = tuple(diagrams_by_component.get(component_id, ()))
        if not diagrams:
            raise ValueError(f"authored component `{component_id}` has no exact diagram trace link")
        handoff = {
            "workstream_id": workstreams[0],
            "workstream_title": workstream_titles.get(workstreams[0], ""),
            "release_selector": str(release_selector or "").strip(),
        }
        rows.append(
            {
                "component_id": component_id,
                "label": label,
                "path": path,
                "kind": _required_scalar(component, "kind"),
                "category": "application",
                "status": _required_scalar(component, "status"),
                "qualification": _required_scalar(component, "qualification"),
                "owner": "repo",
                "product_layer": "application",
                "sources": (AUTHORED_SEMANTIC_ROOT,),
                "workstreams": workstreams,
                "diagrams": diagrams,
                "responsibility": responsibility,
                "boundary": "",
                "dependencies": tuple(contract["external_dependencies"]),
                "interfaces": (),
                "validation": tuple(contract["operational_constraints"]),
                "risks": (),
                "implementation_handoff": handoff,
                "component_contract": contract,
                "projection_origin": AUTHORED_PROJECTION_ORIGIN,
                "source_custody": source_custody,
            }
        )
    return tuple(rows)


def build_authored_component_registry_entry(row: Mapping[str, Any]) -> dict[str, Any]:
    """Build a Registry manifest row without interpreting authored prose."""

    _require_authored_custody(row)
    component_id = _required_scalar(row, "component_id")
    label = _required_scalar(row, "label")
    path = _required_scalar(row, "path")
    kind = _required_scalar(row, "kind")
    responsibility = _required_scalar(row, "responsibility")
    sources = list(_required_sequence(row, "sources"))
    workstreams = list(_required_sequence(row, "workstreams"))
    diagrams = list(_sequence(row.get("diagrams")))
    return {
        "component_id": component_id,
        "name": label,
        "kind": kind,
        "category": _required_scalar(row, "category"),
        "qualification": _required_scalar(row, "qualification"),
        "aliases": [],
        "path_prefixes": [path],
        "workstreams": workstreams,
        "diagrams": diagrams,
        "owner": _required_scalar(row, "owner"),
        "status": _required_scalar(row, "status"),
        "what_it_is": (
            f"{label} is a planned Registry {kind}. "
            f"Source-custodied responsibility: {responsibility}"
        ),
        "why_tracked": (
            "Tracked because the accepted typed intent supplies exact component facts "
            "and first-release trace links."
        ),
        "spec_ref": f"odylith/registry/source/components/{component_id}/CURRENT_SPEC.md",
        "sources": sources,
        "subcomponents": [],
        "product_layer": _required_scalar(row, "product_layer"),
    }


def build_authored_component_spec(row: Mapping[str, Any]) -> str:
    """Render one typed component contract without a narrative inference pass."""

    _require_authored_custody(row)
    component_id = _required_scalar(row, "component_id")
    label = _required_scalar(row, "label")
    path = _required_scalar(row, "path")
    kind = _required_scalar(row, "kind")
    status = _required_scalar(row, "status")
    qualification = _required_scalar(row, "qualification")
    responsibility = _required_scalar(row, "responsibility")
    workstreams = _required_sequence(row, "workstreams")
    diagrams = _sequence(row.get("diagrams"))
    contract = row.get("component_contract")
    if not isinstance(contract, Mapping):
        raise ValueError(f"authored component `{component_id}` is missing its typed component contract")

    contract = _authored_component_contract(
        row,
        component_id=component_id,
        label=label,
        responsibility=responsibility,
    )
    owner_system = _required_contract_text(contract, "owner_system", component_id=component_id)
    responsibility_facts = _required_contract_facts(
        contract,
        "responsibility_facts",
        component_id=component_id,
    )
    owner_bound_events = _contract_facts(contract, "owner_bound_events", component_id=component_id)
    event_targets = _contract_facts(contract, "event_targets", component_id=component_id)
    visible_results = _contract_facts(contract, "visible_results", component_id=component_id)
    recovery_events = _contract_facts(contract, "recovery_events", component_id=component_id)
    state_context = _contract_facts(contract, "state_context", component_id=component_id)
    external_dependencies = _contract_facts(
        contract,
        "external_dependencies",
        component_id=component_id,
    )
    operational_constraints = _contract_facts(
        contract,
        "operational_constraints",
        component_id=component_id,
    )

    return "\n".join(
        [
            f"# {label}",
            "",
            f"> Candidate Registry component projected from `{AUTHORED_SEMANTIC_ROOT}`.",
            "",
            "## Component Snapshot",
            "",
            f"- Component ID: `{component_id}`",
            f"- Kind: `{kind}`",
            f"- Status: `{status}`",
            f"- Qualification: `{qualification}`",
            f"- Planned path: `{path}`",
            f"- Semantic authority: `{AUTHORED_SEMANTIC_ROOT}`",
            "",
            "## Source-custodied responsibility",
            "",
            _relation_facts(responsibility_facts, relation_label="responsibility fact"),
            "",
            "## Source-custodied owner relations",
            "",
            "### Owner system",
            "",
            _evidence_block(owner_system),
            "",
            "### Owner-bound events",
            "",
            _relation_facts(owner_bound_events, relation_label="owner-bound event"),
            "",
            "### Event targets",
            "",
            _relation_facts(event_targets, relation_label="event target"),
            "",
            "### Visible results",
            "",
            _relation_facts(visible_results, relation_label="visible result"),
            "",
            "### Recovery events",
            "",
            _relation_facts(recovery_events, relation_label="recovery event"),
            "",
            "### State context",
            "",
            _relation_facts(state_context, relation_label="state context fact"),
            "",
            "### External dependencies",
            "",
            _relation_facts(external_dependencies, relation_label="external dependency"),
            "",
            "### Operational constraints",
            "",
            _relation_facts(operational_constraints, relation_label="operational constraint"),
            "",
            "## Trace links",
            "",
            f"- Semantic source: `{AUTHORED_SEMANTIC_ROOT}`",
            *[f"- Workstream: `{workstream}`" for workstream in workstreams],
            *([f"- Diagram: `{diagram}`" for diagram in diagrams] or ["- Diagram: no authored component link"]),
            "",
        ]
    )


def _require_authored_custody(row: Mapping[str, Any]) -> None:
    custody = row.get("source_custody")
    if not isinstance(custody, Mapping) or not artifact_tribunal.source_custody_valid(custody):
        raise ValueError("authored component projection is missing its exact semantic custody contract")


def _required_scalar(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"authored component projection requires `{key}`")
    return value.strip()


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
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())


def _ordered_values(values: Sequence[str]) -> tuple[str, ...]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            rows.append(value)
            seen.add(value)
    return tuple(rows)


def _authored_component_contract(
    component: Mapping[str, Any],
    *,
    component_id: str,
    label: str,
    responsibility: str,
) -> dict[str, Any]:
    contract = component.get("component_contract")
    if not isinstance(contract, Mapping) or set(contract) != _AUTHORED_COMPONENT_CONTRACT_FIELDS:
        raise ValueError(
            f"authored component `{component_id}` requires the closed owner-bound component contract"
        )
    owner_system = _required_contract_text(contract, "owner_system", component_id=component_id)
    responsibility_facts = _required_contract_facts(
        contract,
        "responsibility_facts",
        component_id=component_id,
    )
    for key in (
        "owner_bound_events",
        "event_targets",
        "visible_results",
        "recovery_events",
        "state_context",
        "external_dependencies",
        "operational_constraints",
    ):
        _contract_facts(contract, key, component_id=component_id)
    if owner_system != label:
        raise ValueError(f"authored component `{component_id}` owner system must match its label exactly")
    if responsibility != "; ".join(responsibility_facts):
        raise ValueError(
            f"authored component `{component_id}` responsibility must exactly join its responsibility facts"
        )
    if _sequence(component.get("dependencies")) != _contract_facts(
        contract,
        "external_dependencies",
        component_id=component_id,
    ):
        raise ValueError(f"authored component `{component_id}` dependencies drifted from typed context")
    if _sequence(component.get("validation")) != _contract_facts(
        contract,
        "operational_constraints",
        component_id=component_id,
    ):
        raise ValueError(f"authored component `{component_id}` validation drifted from typed context")
    if any(component.get(key) not in (None, "", [], ()) for key in _UNBOUND_COMPONENT_FIELDS):
        raise ValueError(f"authored component `{component_id}` contains unbound local semantics")
    if component.get("kind") != "component":
        raise ValueError(f"authored component `{component_id}` kind must remain implementation-neutral")
    return dict(contract)


def _required_contract_text(contract: Mapping[str, Any], key: str, *, component_id: str) -> str:
    value = contract.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"authored component `{component_id}` requires contract field `{key}`")
    return value


def _required_contract_facts(
    contract: Mapping[str, Any],
    key: str,
    *,
    component_id: str,
) -> tuple[str, ...]:
    values = _contract_facts(contract, key, component_id=component_id)
    if not values:
        raise ValueError(f"authored component `{component_id}` requires contract field `{key}`")
    return values


def _contract_facts(
    contract: Mapping[str, Any],
    key: str,
    *,
    component_id: str,
) -> tuple[str, ...]:
    value = contract.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"authored component `{component_id}` contract field `{key}` must be exact text facts")
    return tuple(value)


def _component_workstream_links(
    *,
    proposal: Mapping[str, Any],
    backlog_result: Mapping[str, Any],
) -> tuple[dict[str, tuple[str, ...]], dict[str, str]]:
    proposal_rows = _mapping_sequence(proposal.get("backlog"))
    created_rows = _mapping_sequence(backlog_result.get("created"))
    if len(created_rows) < len(proposal_rows):
        raise ValueError("authored component projection is missing allocated workstream links")
    links: dict[str, list[str]] = {}
    titles: dict[str, str] = {}
    for index, proposal_row in enumerate(proposal_rows):
        created = created_rows[index]
        workstream_id = _required_scalar(created, "idea_id")
        titles[workstream_id] = _required_scalar(proposal_row, "title")
        for component_id in _sequence(proposal_row.get("component_focus")):
            links.setdefault(component_id, []).append(workstream_id)
    return (
        {component_id: _ordered_values(workstreams) for component_id, workstreams in links.items()},
        titles,
    )


def _component_diagram_links(
    *,
    root: Path,
    proposal: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    diagram_rows = _mapping_sequence(proposal.get("diagrams"))
    diagram_ids = allocated_diagram_ids(root, len(diagram_rows), rows=diagram_rows)
    links: dict[str, list[str]] = {}
    for diagram, diagram_id in zip(diagram_rows, diagram_ids, strict=True):
        for component_id in _sequence(diagram.get("related_components")):
            links.setdefault(component_id, []).append(diagram_id)
    return {component_id: _ordered_values(diagrams) for component_id, diagrams in links.items()}


def _evidence_block(value: str) -> str:
    return "\n".join(f"> {line}" for line in value.splitlines())


def _relation_facts(values: Sequence[str], *, relation_label: str) -> str:
    if not values:
        return f"> No source-custodied {relation_label} was authored for this component."
    return "\n\n".join(_evidence_block(value) for value in values)


__all__ = [
    "AUTHORED_SEMANTIC_ROOT",
    "build_authored_component_authoring_inputs",
    "build_authored_component_registry_entry",
    "build_authored_component_spec",
    "is_authored_component_projection",
]
