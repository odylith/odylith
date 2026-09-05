"""Build and verify the sealed Atlas view of model-authored Greenfield facts.

The model-authoring response already owns semantic meaning.  This module makes
one presentation projection from its typed actors, events, components, state,
result, and proof.  Marked rows therefore carry exact display data and custody
hashes; consumers must not reinterpret their Mermaid or prose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
from html import escape
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)

AUTHORED_ATLAS_AUTHORITY_KEY = "authored_atlas_view_authority"
AUTHORED_ATLAS_AUTHORITY_VERSION = "odylith.greenfield.authored-atlas-view.v1"
AUTHORED_ATLAS_ROLES = ("context", "sequence", "state_evidence", "component_boundaries")
_WORKSTREAM_ROLES_BY_DIAGRAM = {
    "context": ("project", "workflow", "boundary"),
    "sequence": ("project", "workflow", "proof"),
    "state_evidence": ("project", "proof"),
    "component_boundaries": ("project", "boundary"),
}


def build_authored_atlas_diagrams(
    *,
    title: str,
    diagram_slugs: Mapping[str, str],
    human_actors: Sequence[str],
    external_systems: Sequence[str],
    non_goals: Sequence[str],
    state_object: str,
    visible_result: str,
    proof_boundary: str,
    components: Sequence[Mapping[str, Any]],
    backlog: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
    diagram_roles: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Project only selected existing authored views without interpreting text."""

    selected_roles = _selected_diagram_roles(diagram_roles)

    component_rows = [
        {
            "name": _required_string(row.get("label"), "component label"),
            "description": _required_string(
                row.get("responsibility"),
                "component responsibility",
            ),
        }
        for row in components
    ]
    component_ids = [
        _required_string(row.get("component_id"), "component id") for row in components
    ]
    workstream_titles = _workstream_titles_by_diagram(backlog)

    context_source, context_boxes = _context_view(
        title=title,
        actors=human_actors,
        externals=external_systems,
        components=components,
    )
    sequence_source, sequence_boxes = _sequence_view(relations)
    state_source, state_boxes = _state_view(
        state_object=state_object,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        relations=relations,
        context_relations=context_relations,
    )
    boundary_source, boundary_boxes = _boundary_view(
        title=title,
        components=components,
        externals=external_systems,
        non_goals=non_goals,
        context_relations=context_relations,
    )
    specs = {
        "context": {
            "title": "System Context View",
            "summary": f"Accepted actors, named systems, and candidate product-owned boundaries for {title}.",
            "read_guide": (
                "Read the accepted human actors into the product boundary, treat components as "
                "candidate ownership, and keep accepted external systems outside that boundary."
            ),
            "source": context_source,
            "boxes": context_boxes,
        },
        "sequence": {
            "title": "First Path Sequence",
            "summary": "The verified first-path events in source order.",
            "read_guide": (
                "Read the source-bound events in order; owner boxes connect typed owner systems "
                "to the events they own."
            ),
            "source": sequence_source,
            "boxes": sequence_boxes,
        },
        "state_evidence": {
            "title": "State and Evidence View",
            "summary": (
                "An inventory of the accepted state object, visible result, and proof boundary."
            ),
            "read_guide": (
                "Read the source-bound state-to-event association, then treat the visible result "
                "and proof boundary as accepted facts. A dotted result-to-proof edge appears only "
                "when the exact visible-result text is contained by the proof boundary."
            ),
            "source": state_source,
            "boxes": state_boxes,
        },
        "component_boundaries": {
            "title": "Component Boundary View",
            "summary": (
                "A containment view of candidate components, external systems, and accepted non-goals."
            ),
            "read_guide": (
                "Read the product container as candidate ownership, external systems as outside "
                "dependencies, and non-goals as explicitly outside scope."
            ),
            "source": boundary_source,
            "boxes": boundary_boxes,
        },
    }

    rows: list[dict[str, Any]] = []
    for key in selected_roles:
        spec = specs[key]
        row: dict[str, Any] = {
            "slug": _required_string(diagram_slugs.get(key), f"{key} diagram slug"),
            "title": spec["title"],
            "kind": "flowchart",
            "summary": spec["summary"],
            "read_guide": spec["read_guide"],
            "owner": "repo",
            "status": "draft",
            "link_state": "atlas_first_draft",
            "components": deepcopy(component_rows),
            "related_workstream_titles": list(workstream_titles[key]),
            "related_components": list(component_ids),
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "projection_origin": AUTHORED_PROJECTION_ORIGIN,
            "mermaid_source": spec["source"],
            "diagram_boxes": deepcopy(spec["boxes"]),
        }
        row[AUTHORED_ATLAS_AUTHORITY_KEY] = _authority_for_row(row)
        validate_authored_atlas_view(row, source_text=row["mermaid_source"])
        rows.append(row)
    return rows


def _selected_diagram_roles(values: Sequence[str] | None) -> tuple[str, ...]:
    if values is None:
        return AUTHORED_ATLAS_ROLES
    roles = tuple(values)
    canonical = tuple(role for role in AUTHORED_ATLAS_ROLES if role in roles)
    if not roles or roles != canonical or len(roles) != len(set(roles)):
        raise ValueError("model-authored Atlas roles must be unique existing views in canonical order")
    return roles
def _workstream_titles_by_diagram(backlog: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    rows = [
        (
            _required_string(row.get("title"), "workstream title"),
            row.get("workstream_role"),
        )
        for row in backlog
    ]
    if not rows:
        raise ValueError("model-authored Atlas view requires at least one workstream")
    if all(role is None for _, role in rows):
        titles = [title for title, _ in rows]
        return {diagram_role: list(titles) for diagram_role in AUTHORED_ATLAS_ROLES}
    if any(not isinstance(role, str) or not role for _, role in rows):
        raise ValueError("model-authored Atlas workstreams have incomplete typed roles")
    roles = [str(role) for _, role in rows]
    if len(roles) != len(set(roles)) or "project" not in roles:
        raise ValueError("model-authored Atlas workstream roles are incomplete or duplicated")
    result: dict[str, list[str]] = {}
    for diagram_role, accepted_roles in _WORKSTREAM_ROLES_BY_DIAGRAM.items():
        titles = [title for title, role in rows if role in accepted_roles]
        if not titles:
            raise ValueError(f"model-authored `{diagram_role}` view has no typed workstream")
        result[diagram_role] = titles
    return result


def is_authored_atlas_view(row: Mapping[str, Any]) -> bool:
    """Return whether a row claims the sealed authored Atlas contract.

    Projection origin is sufficient to enter the fail-closed branch.  A lost
    marker must never silently reactivate legacy semantic interpretation.
    """

    return (
        AUTHORED_ATLAS_AUTHORITY_KEY in row
        or row.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN
    )


def validate_authored_atlas_view(
    row: Mapping[str, Any],
    *,
    source_text: str,
) -> dict[str, Any]:
    """Validate exact authored view custody and return its display projection.

    This intentionally does not parse Mermaid or classify prose.  Construction
    fixes the node/source relationship, while hashes and ordered IDs prove that
    the same view reached staging and rendering.
    """

    authority = row.get(AUTHORED_ATLAS_AUTHORITY_KEY)
    if not isinstance(authority, Mapping):
        raise ValueError("authored Atlas view authority must be an object")
    expected_keys = {
        "version",
        "projection_origin",
        "source_sha256",
        "surface_sha256",
        "node_order",
    }
    if set(authority) != expected_keys:
        raise ValueError("authored Atlas view authority has an invalid schema")
    if authority.get("version") != AUTHORED_ATLAS_AUTHORITY_VERSION:
        raise ValueError("authored Atlas view authority has an unsupported version")
    if authority.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise ValueError("authored Atlas view authority has an invalid projection origin")
    if row.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise ValueError("authored Atlas row has an invalid projection origin")

    source = _required_source(source_text)
    source_sha256 = _sha256_text(source)
    if authority.get("source_sha256") != source_sha256:
        raise ValueError("authored Atlas Mermaid source does not match its sealed hash")

    node_order = _string_list(authority.get("node_order"), "authored Atlas node order")
    if len(node_order) != len(set(node_order)):
        raise ValueError("authored Atlas node order contains duplicate node IDs")

    raw_boxes = row.get("diagram_boxes")
    if not isinstance(raw_boxes, list) or not raw_boxes:
        raise ValueError("authored Atlas diagram_boxes must be a non-empty list")
    boxes: list[dict[str, str]] = []
    box_ids: list[str] = []
    for index, raw_box in enumerate(raw_boxes):
        if not isinstance(raw_box, Mapping):
            raise ValueError(f"authored Atlas diagram_boxes[{index}] must be an object")
        if set(raw_box) != {"node_id", "label", "role", "description"}:
            raise ValueError(f"authored Atlas diagram_boxes[{index}] has an invalid schema")
        node_id = _required_string(raw_box.get("node_id"), f"diagram_boxes[{index}].node_id")
        box_ids.append(node_id)
        boxes.append(
            {
                "node_id": node_id,
                "label": _required_string(raw_box.get("label"), f"diagram_boxes[{index}].label"),
                "role": _required_string(raw_box.get("role"), f"diagram_boxes[{index}].role"),
                "description": _required_string(
                    raw_box.get("description"),
                    f"diagram_boxes[{index}].description",
                ),
            }
        )
    if len(box_ids) != len(set(box_ids)):
        raise ValueError("authored Atlas diagram_boxes contain duplicate node IDs")
    if set(box_ids) != set(node_order):
        missing = [node_id for node_id in node_order if node_id not in set(box_ids)]
        unexpected = [node_id for node_id in box_ids if node_id not in set(node_order)]
        detail = []
        if missing:
            detail.append(f"missing {', '.join(missing)}")
        if unexpected:
            detail.append(f"unmatched {', '.join(unexpected)}")
        raise ValueError(
            "authored Atlas diagram_boxes do not match sealed node IDs"
            + (f": {'; '.join(detail)}" if detail else "")
        )
    if box_ids != node_order:
        raise ValueError("authored Atlas diagram_boxes are reordered from sealed node IDs")

    summary = _required_string(row.get("summary"), "authored Atlas summary")
    read_guide = _required_string(row.get("read_guide"), "authored Atlas read guide")
    components = _component_rows(row.get("components"))
    surface_payload = _surface_payload(
        source_sha256=source_sha256,
        node_order=node_order,
        boxes=boxes,
        summary=summary,
        read_guide=read_guide,
        components=components,
    )
    if authority.get("surface_sha256") != _sha256_json(surface_payload):
        raise ValueError("authored Atlas display rows do not match their sealed hash")
    return {
        "summary": summary,
        "read_guide": read_guide,
        "diagram_boxes": deepcopy(boxes),
        "components": deepcopy(components),
    }


def _authority_for_row(row: Mapping[str, Any]) -> dict[str, Any]:
    source = _required_source(row.get("mermaid_source"))
    boxes = row.get("diagram_boxes")
    if not isinstance(boxes, list):
        raise ValueError("authored Atlas diagram_boxes must be a list")
    node_order = [
        _required_string(box.get("node_id"), "authored Atlas box node id")
        for box in boxes
        if isinstance(box, Mapping)
    ]
    source_sha256 = _sha256_text(source)
    surface_payload = _surface_payload(
        source_sha256=source_sha256,
        node_order=node_order,
        boxes=boxes,
        summary=_required_string(row.get("summary"), "authored Atlas summary"),
        read_guide=_required_string(row.get("read_guide"), "authored Atlas read guide"),
        components=_component_rows(row.get("components")),
    )
    return {
        "version": AUTHORED_ATLAS_AUTHORITY_VERSION,
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "source_sha256": source_sha256,
        "surface_sha256": _sha256_json(surface_payload),
        "node_order": node_order,
    }


def _surface_payload(
    *,
    source_sha256: str,
    node_order: Sequence[str],
    boxes: Sequence[Mapping[str, Any]],
    summary: str,
    read_guide: str,
    components: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "version": AUTHORED_ATLAS_AUTHORITY_VERSION,
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "source_sha256": source_sha256,
        "node_order": list(node_order),
        "diagram_boxes": [dict(box) for box in boxes],
        "narrative": {"summary": summary, "read_guide": read_guide},
        "components": [dict(component) for component in components],
    }


def _context_view(
    *,
    title: str,
    actors: Sequence[str],
    externals: Sequence[str],
    components: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    lines = ["flowchart LR", '  subgraph people["Accepted human actors"]']
    boxes = [
        _box(
            "people",
            "Accepted human actors",
            "Container",
            "Groups the accepted human actors in the first product path.",
        )
    ]
    for index, actor in enumerate(actors, start=1):
        lines.append(f'    actor{index}["{_mermaid_label(actor)}"]')
        boxes.append(
            _box(
                f"actor{index}",
                actor,
                "Human actor",
                f"Accepted human actor in the first product path: {actor}",
            )
        )
    component_rows = [
        (
            _required_string(component.get("label"), "component label"),
            _required_string(component.get("responsibility"), "component responsibility"),
        )
        for component in components
    ]
    sole_title_product = (
        len(component_rows) == 1
        and " ".join(component_rows[0][0].split()).casefold()
        == " ".join(title.split()).casefold()
    )
    lines.append("  end")
    lines.append(
        f'  product["{_mermaid_label(title)}"]'
        if sole_title_product
        else f'  subgraph product["{_mermaid_label(title)}"]'
    )
    boxes.append(
        _box(
            "product",
            title,
            "Product boundary",
            (
                f"Candidate product boundary and sole product-owned component for {title}."
                if sole_title_product
                else f"Contains the candidate product-owned components for {title}."
            ),
        )
    )
    for index, (label, responsibility) in enumerate(component_rows, start=1):
        if sole_title_product:
            continue
        lines.append(f'    component{index}["{_mermaid_label(label)}"]')
        boxes.append(
            _box(
                f"component{index}",
                label,
                "Product-owned component",
                f"Accepted responsibility: {responsibility}",
            )
        )
    if not sole_title_product:
        lines.append("  end")
    if externals:
        lines.append('  subgraph external_systems["Accepted external systems"]')
        boxes.append(
            _box(
                "external_systems",
                "Accepted external systems",
                "Container",
                "Groups accepted systems that remain outside product ownership.",
            )
        )
        for index, external in enumerate(externals, start=1):
            lines.append(f'    external{index}["{_mermaid_label(external)}"]')
            boxes.append(
                _box(
                    f"external{index}",
                    external,
                    "External system",
                    f"Accepted external system outside product ownership: {external}",
                )
            )
        lines.append("  end")
    for actor_index, _actor in enumerate(actors, start=1):
        lines.append(f"  actor{actor_index} --> product")
    for external_index, component_index in _external_component_edges(
        externals=externals,
        components=components,
    ):
        target = (
            f"component{component_index}"
            if component_index and not sole_title_product
            else "product"
        )
        lines.append(f"  external{external_index} -.-> {target}")
    return _styled_mermaid(lines), boxes


def _sequence_view(
    relations: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    lines = ["flowchart LR"]
    boxes: list[dict[str, str]] = []
    owners: dict[str, str] = {}
    for index, relation in enumerate(relations, start=1):
        event_quote = _required_string(relation.get("event_quote"), "first-path event quote")
        actor_kind = _required_string(relation.get("actor_kind"), "first-path actor kind")
        lines.append(f'  event{index}["{_mermaid_label(event_quote)}"]')
        boxes.append(
            _box(
                f"event{index}",
                event_quote,
                f"{actor_kind} event",
                f"Source-bound first-path event {index}: {event_quote}",
            )
        )
        owner = relation.get("owner_system_quote")
        if isinstance(owner, str) and owner:
            if owner not in owners:
                owner_id = f"owner{len(owners) + 1}"
                owners[owner] = owner_id
                lines.append(f'  {owner_id}["{_mermaid_label(owner)}"]')
                boxes.append(
                    _box(
                        owner_id,
                        owner,
                        "Typed event owner",
                        f"Accepted owner system for one or more first-path events: {owner}",
                    )
                )
            lines.append(f"  {owners[owner]} --> event{index}")
        if index > 1:
            lines.append(f"  event{index - 1} --> event{index}")
    return _styled_mermaid(lines), boxes


def _state_view(
    *,
    state_object: str,
    visible_result: str,
    proof_boundary: str,
    relations: Sequence[Mapping[str, Any]],
    context_relations: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    state_relation = next(
        (
            row
            for row in context_relations
            if row.get("context_kind") == "state_object"
            and row.get("fact_quote") == state_object
        ),
        None,
    )
    if not isinstance(state_relation, Mapping):
        raise ValueError("authored Atlas state view requires the typed state relation")
    event_order = state_relation.get("first_path_event_order")
    linked_event = next(
        (
            row
            for row in relations
            if row.get("order") == event_order
        ),
        None,
    )
    lines = [
        "flowchart LR",
        '  subgraph accepted_facts["Accepted project facts"]',
        f'    state["State object<br/>{_mermaid_label(state_object)}"]',
        f'    result["Visible result<br/>{_mermaid_label(visible_result)}"]',
        f'    proof["Proof boundary<br/>{_mermaid_label(proof_boundary)}"]',
        "  end",
    ]
    boxes = [
        _box(
            "accepted_facts",
            "Accepted project facts",
            "Container",
            "Groups the typed state, result, and proof facts without inferring transitions.",
        ),
        _box("state", state_object, "State object", f"Accepted state object: {state_object}"),
        _box("result", visible_result, "Visible result", f"Accepted visible result: {visible_result}"),
        _box("proof", proof_boundary, "Proof boundary", f"Accepted proof boundary: {proof_boundary}"),
    ]
    if isinstance(linked_event, Mapping):
        event_quote = _required_string(
            linked_event.get("event_quote"), "state-linked event"
        )
        lines.insert(
            3,
            f'    state_event["State-linked event<br/>{_mermaid_label(event_quote)}"]',
        )
        lines.append("  state -. exact source overlap .-> state_event")
        boxes.insert(
            2,
            _box(
                "state_event",
                event_quote,
                "State-linked event",
                "Exact source overlap binds this event to the accepted state object: "
                f"{event_quote}",
            ),
        )
    if visible_result in proof_boundary:
        lines.append("  result -. exact source containment .-> proof")
    return _styled_mermaid(lines), boxes


def _boundary_view(
    *,
    title: str,
    components: Sequence[Mapping[str, Any]],
    externals: Sequence[str],
    non_goals: Sequence[str],
    context_relations: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    lines = ["flowchart TB", f'  subgraph product["{_mermaid_label(title)}"]']
    boxes = [
        _box(
            "product",
            title,
            "Product boundary",
            f"Contains the candidate product-owned components for {title}.",
        )
    ]
    for index, component in enumerate(components, start=1):
        label = _required_string(component.get("label"), "component label")
        responsibility = _required_string(
            component.get("responsibility"),
            "component responsibility",
        )
        lines.append(f'    component{index}["{_mermaid_label(label)}"]')
        boxes.append(
            _box(
                f"component{index}",
                label,
                "Product-owned component",
                f"Accepted responsibility: {responsibility}",
            )
        )
    lines.append("  end")
    if externals:
        lines.append('  subgraph external_systems["Accepted external systems"]')
        boxes.append(
            _box(
                "external_systems",
                "Accepted external systems",
                "Container",
                "Groups accepted systems that remain outside product ownership.",
            )
        )
        for index, external in enumerate(externals, start=1):
            lines.append(f'    external{index}["{_mermaid_label(external)}"]')
            boxes.append(
                _box(
                    f"external{index}",
                    external,
                    "External system",
                    f"Accepted external system outside product ownership: {external}",
                )
            )
        lines.append("  end")
    if non_goals:
        lines.append('  subgraph outside_scope["Accepted non-goals"]')
        boxes.append(
            _box(
                "outside_scope",
                "Accepted non-goals",
                "Container",
                "Groups source-accepted work that remains outside the product boundary.",
            )
        )
        for index, non_goal in enumerate(non_goals, start=1):
            lines.append(f'    non_goal{index}["{_mermaid_label(non_goal)}"]')
            boxes.append(
                _box(
                    f"non_goal{index}",
                    non_goal,
                    "Non-goal",
                    f"Accepted work outside the product boundary: {non_goal}",
                )
            )
        lines.append("  end")
    linked_external_quotes = {
        str(row.get("fact_quote") or "")
        for row in context_relations
        if row.get("context_kind") == "external_system"
    }
    for external_index, component_index in _external_component_edges(
        externals=externals,
        components=components,
    ):
        external = externals[external_index - 1]
        if external not in linked_external_quotes:
            raise ValueError("authored Atlas external edge lacks a typed context relation")
        target = f"component{component_index}" if component_index else "product"
        lines.append(f"  external{external_index} -.-> {target}")
    for index, _non_goal in enumerate(non_goals, start=1):
        lines.append(f"  product -.-> non_goal{index}")
    return _styled_mermaid(lines), boxes


def _external_component_edges(
    *,
    externals: Sequence[str],
    components: Sequence[Mapping[str, Any]],
) -> tuple[tuple[int, int], ...]:
    edges: list[tuple[int, int]] = []
    for external_index, external in enumerate(externals, start=1):
        matched = False
        for component_index, component in enumerate(components, start=1):
            contract = component.get("component_contract")
            dependencies = (
                contract.get("external_dependencies")
                if isinstance(contract, Mapping)
                else component.get("dependencies")
            )
            if external in _string_sequence(dependencies):
                edges.append((external_index, component_index))
                matched = True
        if not matched:
            edges.append((external_index, 0))
    return tuple(edges)


def _box(node_id: str, label: str, role: str, description: str) -> dict[str, str]:
    return {
        "node_id": _required_string(node_id, "Atlas node id"),
        "label": _required_string(label, "Atlas box label"),
        "role": _required_string(role, "Atlas box role"),
        "description": _required_string(description, "Atlas box description"),
    }


def _component_rows(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValueError("authored Atlas components must be a non-empty list")
    rows: list[dict[str, str]] = []
    for index, raw_row in enumerate(value):
        if not isinstance(raw_row, Mapping) or set(raw_row) != {"name", "description"}:
            raise ValueError(f"authored Atlas components[{index}] has an invalid schema")
        rows.append(
            {
                "name": _required_string(raw_row.get("name"), f"components[{index}].name"),
                "description": _required_string(
                    raw_row.get("description"),
                    f"components[{index}].description",
                ),
            }
        )
    return rows


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    return [_required_string(item, f"{name} item") for item in value]


def _string_sequence(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must be a non-empty, whitespace-exact string")
    return value


def _required_source(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("authored Atlas Mermaid source must be non-empty")
    if value != value.rstrip() + "\n":
        raise ValueError("authored Atlas Mermaid source must end with exactly one newline")
    return value


def _styled_mermaid(lines: list[str]) -> str:
    lines.extend(
        [
            "  classDef personStyle fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;",
            "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;",
            "  classDef external fill:#FFF7ED,stroke:#FDBA74,color:#17233A,stroke-width:1px;",
        ]
    )
    return "\n".join(lines) + "\n"


def _mermaid_label(value: Any, *, width: int = 28) -> str:
    words = _required_string(value, "Mermaid label").split()
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
    return "<br/>".join(escape(line, quote=True) for line in lines)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "AUTHORED_ATLAS_AUTHORITY_KEY",
    "AUTHORED_ATLAS_AUTHORITY_VERSION",
    "build_authored_atlas_diagrams",
    "is_authored_atlas_view",
    "validate_authored_atlas_view",
]
