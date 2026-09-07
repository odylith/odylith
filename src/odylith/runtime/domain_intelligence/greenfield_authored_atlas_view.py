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
import json
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import (
    atlas_box as _box,
    build_provisional_design_atlas_specs,
    mermaid_label as _mermaid_label,
    styled_mermaid as _styled_mermaid,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    PROVISIONAL_DESIGN_AUTHORITY_KIND,
)

AUTHORED_ATLAS_AUTHORITY_KEY = "authored_atlas_view_authority"
AUTHORED_ATLAS_AUTHORITY_VERSION = "odylith.greenfield.authored-atlas-view.v2"
SOURCE_GROUNDED_AUTHORITY_KIND = "source_grounded"
AUTHORED_ATLAS_ROLES = (
    "context",
    "sequence",
    "component_exchanges",
    "delivery_dependencies",
    "capability_support",
)


def build_authored_atlas_diagrams(
    *,
    title: str,
    product_story: str,
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
    provisional_design: Mapping[str, Any],
    diagram_roles: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Project source facts and one separately authoritative provisional design."""

    selected_roles = _selected_diagram_roles(diagram_roles)
    title = _required_string(title, "project title")
    product_story = _required_string(product_story, "source product story")
    state_object = _required_string(state_object, "state object")
    visible_result = _required_string(visible_result, "visible result")
    proof_boundary = _required_string(proof_boundary, "proof boundary")

    source_component_rows = [
        {
            "name": _required_string(row.get("label"), "component label"),
            "description": _required_string(
                row.get("responsibility"),
                "component responsibility",
            ),
        }
        for row in components
    ]
    backlog_titles = _workstream_titles(backlog)

    context_source, context_boxes = _context_view(
        title=title,
        product_story=product_story,
        actors=human_actors,
        externals=external_systems,
        components=components,
        relations=relations,
    )
    sequence_source, sequence_boxes = _sequence_view(relations)
    design_specs = build_provisional_design_atlas_specs(
        provisional_design=provisional_design,
        relations=relations,
        state_object=state_object,
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        non_goals=non_goals,
    )
    design_workstream_titles = design_specs["delivery_dependencies"]["workstream_titles"]
    if backlog_titles != design_workstream_titles:
        raise ValueError("authored Atlas workstreams drifted from the provisional design")
    design_component_ids = design_specs["component_exchanges"]["component_ids"]
    specs = {
        "context": {
            "title": "System Context View",
            "summary": (
                f"Who owns the source-stated work in {title}."
            ),
            "read_guide": (
                "People are source-stated participants, not necessarily product users. "
                "Each performing person, product system, or external system connects to its "
                "own exact events; other people remain edge-free. The sequence view shows "
                "event order across owners. Registry links identify proposed "
                "support, not replacement of source ownership."
            ),
            "source": context_source,
            "boxes": context_boxes,
            "authority_kind": SOURCE_GROUNDED_AUTHORITY_KIND,
            "components": source_component_rows,
            "component_ids": design_component_ids,
            "workstream_titles": backlog_titles,
        },
        "sequence": {
            "title": "First Path Sequence",
            "summary": "The verified first-path events in source order.",
            "read_guide": (
                "Read the source-bound events in order; owner boxes connect typed owner systems "
                "to the events they own. Registry links identify proposed support, not replacement "
                "of source ownership."
            ),
            "source": sequence_source,
            "boxes": sequence_boxes,
            "authority_kind": SOURCE_GROUNDED_AUTHORITY_KIND,
            "components": source_component_rows,
            "component_ids": design_component_ids,
            "workstream_titles": backlog_titles,
        },
        **design_specs,
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
            "components": deepcopy(spec["components"]),
            "related_workstream_titles": list(spec["workstream_titles"]),
            "related_components": list(spec["component_ids"]),
            "watch_paths": [],
            "evidence_tier": "user_intent",
            "authority_kind": spec["authority_kind"],
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
        raise ValueError(
            "model-authored Atlas roles must be unique existing views in canonical order"
        )
    return roles


def _workstream_titles(backlog: Sequence[Mapping[str, Any]]) -> list[str]:
    titles = [
        _required_string(row.get("title"), "workstream title") for row in backlog
    ]
    if not titles:
        raise ValueError("model-authored Atlas view requires at least one workstream")
    if len(titles) != len(set(titles)):
        raise ValueError("model-authored Atlas workstream titles must be unique")
    return titles


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
    authority_kind = _authority_kind(row)

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
    components = _component_rows(row.get("components"), authority_kind=authority_kind)
    surface_payload = _surface_payload(
        source_sha256=source_sha256,
        node_order=node_order,
        boxes=boxes,
        summary=summary,
        read_guide=read_guide,
        components=components,
        authority_kind=authority_kind,
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
        components=_component_rows(row.get("components"), authority_kind=_authority_kind(row)),
        authority_kind=_authority_kind(row),
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
    authority_kind: str,
) -> dict[str, Any]:
    return {
        "version": AUTHORED_ATLAS_AUTHORITY_VERSION,
        "projection_origin": AUTHORED_PROJECTION_ORIGIN,
        "source_sha256": source_sha256,
        "node_order": list(node_order),
        "diagram_boxes": [dict(box) for box in boxes],
        "narrative": {"summary": summary, "read_guide": read_guide},
        "components": [dict(component) for component in components],
        "authority_kind": authority_kind,
    }


def _context_view(
    *,
    title: str,
    product_story: str,
    actors: Sequence[str],
    externals: Sequence[str],
    components: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    performer_events: dict[tuple[str, str], list[str]] = {}
    for relation in relations:
        kind = _required_string(relation.get("actor_kind"), "first-path actor kind")
        performer = _required_string(relation.get("actor_fact_quote"), "first-path actor fact")
        if kind == "product" and relation.get("owner_system_quote") != performer:
            raise ValueError("authored Atlas product performer does not match its typed owner")
        event = _required_string(relation.get("event_quote"), "first-path event")
        performer_events.setdefault((kind, performer), []).append(event)
    lines = ["flowchart LR"]
    boxes: list[dict[str, str]] = []
    owner_nodes: dict[tuple[str, str], str] = {}
    if actors:
        lines.append('  subgraph people["People in product context"]')
        boxes.append(
            _box(
                "people",
                "People in product context",
                "Container",
                "Source-stated people, including participants without a first-path action.",
            )
        )
        for index, actor in enumerate(actors, start=1):
            actor_id = f"actor{index}"
            owner_nodes[("human", actor)] = actor_id
            lines.append(f'    {actor_id}["{_mermaid_label(actor)}"]')
            events = performer_events.get(("human", actor), ())
            boxes.append(
                _box(
                    actor_id,
                    actor,
                    "First-path actor" if events else "Participant",
                    f"Performs source-stated first-path actions: {actor}"
                    if events
                    else "Named in project evidence; no first-path action is assigned.",
                )
            )
        lines.append("  end")
    product_lines, product_boxes, component_targets = _product_boundary_projection(
        title=title,
        product_story=product_story,
        components=components,
    )
    lines.extend(product_lines)
    boxes.extend(product_boxes)
    for component, target in zip(components, component_targets, strict=True):
        owner_nodes[("product", component["label"])] = target
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
            external_id = f"external{index}"
            owner_nodes[("external_system", external)] = external_id
            lines.append(f'    {external_id}["{_mermaid_label(external)}"]')
            boxes.append(
                _box(
                    external_id,
                    external,
                    "External system",
                    f"Accepted external system outside product ownership: {external}",
                )
            )
        lines.append("  end")
    for identity, events in performer_events.items():
        owner_id = owner_nodes.get(identity)
        if owner_id is None:
            raise ValueError("authored Atlas performer is missing its typed context owner")
        action_id = f"{owner_id}_actions"
        event_label = "<br/>".join(_mermaid_label(event) for event in events)
        lines.append(f'  {action_id}["{event_label}"]')
        lines.append(f'  {owner_id} -->|"performs"| {action_id}')
        boxes.append(
            _box(
                action_id, "\n".join(events), "Grouped first-path actions",
                f"Exact source events performed by {identity[1]}, in first-path order.",
            )
        )
    for external_index, component_index in _external_component_edges(
        externals=externals,
        components=components,
    ):
        target = component_targets[component_index - 1] if component_index else "product"
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


def _product_boundary_projection(
    *,
    title: str,
    product_story: str,
    components: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[dict[str, str]], tuple[str, ...]]:
    if not components:
        return (
            [f'  product["{_mermaid_label(title)}<br/>{_mermaid_label(product_story)}"]'],
            [_box("product", title, "Product description", product_story)],
            (),
        )
    rows = tuple(
        (
            _required_string(component.get("label"), "component label"),
            _required_string(component.get("responsibility"), "component responsibility"),
        )
        for component in components
    )
    title_key = " ".join(title.split()).casefold()
    sole_title_product = (
        len(rows) == 1 and " ".join(rows[0][0].split()).casefold() == title_key
    )
    lines = [
        f'  product["{_mermaid_label(title)}"]'
        if sole_title_product
        else f'  subgraph product["{_mermaid_label(title)}"]'
    ]
    boxes = [
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
    ]
    component_targets: list[str] = []
    for index, (label, responsibility) in enumerate(rows, start=1):
        target = "product" if sole_title_product else f"component{index}"
        component_targets.append(target)
        if sole_title_product:
            continue
        lines.append(f'    {target}["{_mermaid_label(label)}"]')
        boxes.append(
            _box(
                target,
                label,
                "Product-owned component",
                f"Accepted responsibility: {responsibility}",
            )
        )
    if not sole_title_product:
        lines.append("  end")
    return lines, boxes, tuple(component_targets)


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


def _component_rows(value: Any, *, authority_kind: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or (not value and authority_kind != SOURCE_GROUNDED_AUTHORITY_KIND):
        raise ValueError("authored Atlas components must be a list, non-empty for proposed design")
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


def _authority_kind(row: Mapping[str, Any]) -> str:
    value = row.get("authority_kind")
    if value not in {SOURCE_GROUNDED_AUTHORITY_KIND, PROVISIONAL_DESIGN_AUTHORITY_KIND}:
        raise ValueError("authored Atlas row has an invalid authority kind")
    return str(value)


def _required_source(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("authored Atlas Mermaid source must be non-empty")
    if value != value.rstrip() + "\n":
        raise ValueError("authored Atlas Mermaid source must end with exactly one newline")
    return value


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
