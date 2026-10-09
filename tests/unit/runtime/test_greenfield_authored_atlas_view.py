"""Characterization of the sealed model-authored Greenfield Atlas view."""

from __future__ import annotations

from copy import deepcopy
import datetime as dt
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_authored_atlas_view
from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import mermaid_label
from odylith.runtime.domain_intelligence import greenfield_confirmed_text
from odylith.runtime.domain_intelligence import greenfield_deferral_predicates
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_authored_first_run import (
    authored_event_display_text,
)
from odylith.runtime.surfaces import atlas_box_explanations
from odylith.runtime.surfaces import atlas_diagram_intelligence
from odylith.runtime.surfaces import render_mermaid_catalog
from tests.unit.runtime.test_greenfield_authored_lexical_isolation import (
    _authored_intent,
    _public_propose,
)


def test_mermaid_label_encodes_format_characters_once_without_rewriting_text() -> None:
    assert mermaid_label('"<sample>" & #quot; `code`', width=100) == (
        '#34;#60;sample#62;#34; #38; #35;quot; #96;code#96;'
    )
    assert mermaid_label("A sample's release-readiness proof is available for review.") == (
        "A sample's release-readiness<br/>proof is available for<br/>review."
    )
    assert mermaid_label('日本語 — café ♥ 50% / path | value', width=100) == (
        '日本語 — café ♥ 50% / path | value'
    )


def _authored_diagrams(
    *,
    title: str = "Harbor Desk",
    component_label: str = "Berth map",
    components: tuple[dict[str, Any], ...] | None = None,
    visible_result: str = "the berth map shows the placement",
    result_event_order: int = 3,
    proof_boundary: str = "Verify the placement and retention receipt",
    human_actors: tuple[str, ...] = ("Dock attendant Ivo",),
    external_systems: tuple[str, ...] = ("Harbor Ledger",),
    relations: tuple[dict[str, Any], ...] | None = None,
    provisional_design: dict[str, Any] | None = None,
    source_lifecycle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    source_relations = relations if relations is not None else (
        {
            "order": 1,
            "actor_kind": "human",
            "actor_fact_quote": "Dock attendant Ivo",
            "event_quote": "Dock attendant Ivo enters a vessel tag",
            "owner_system_quote": "",
        },
        {
            "order": 2,
            "actor_kind": "product",
            "actor_fact_quote": component_label,
            "event_quote": "the product records berth occupancy",
            "owner_system_quote": component_label,
        },
        {
            "order": 3,
            "actor_kind": "product",
            "actor_fact_quote": component_label,
            "event_quote": "the berth map shows the placement",
            "owner_system_quote": component_label,
        },
    )
    assert result_event_order in {row["order"] for row in source_relations}
    source_relations = tuple(
        {**row, "visible_result_quote": visible_result if row["order"] == result_event_order else ""}
        for row in source_relations
    )
    design = provisional_design or _provisional_design(
        event_orders=tuple(row["order"] for row in source_relations)
    )
    return greenfield_authored_atlas_view.build_authored_atlas_diagrams(
        title=title,
        product_story=f"{title} supports the source-stated workflow",
        diagram_slugs={
            "context": "harbor-desk-context",
            "sequence": "harbor-desk-sequence",
            "component_exchanges": "harbor-desk-component-exchanges",
            "delivery_dependencies": "harbor-desk-delivery-dependencies",
            "capability_support": "harbor-desk-capability-support",
        },
        human_actors=human_actors,
        external_systems=external_systems,
        non_goals=("Do not manage vessel scheduling",),
        state_object="berth occupancy",
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        components=components if components is not None else (
            {
                "component_id": "berth-map",
                "label": component_label,
                "responsibility": "Record berth occupancy",
                "dependencies": ["Harbor Ledger"],
            },
        ),
        backlog=tuple({"title": row["title"]} for row in design["workstreams"]),
        relations=source_relations,
        provisional_design=design,
        source_lifecycle=source_lifecycle,
    )


def _provisional_design(*, event_orders: tuple[int, ...] = (1, 2, 3)) -> dict[str, Any]:
    assigned_orders = [
        [event_orders[index % len(event_orders)]] for index in range(3)
    ]
    assigned_orders.append(list(event_orders))
    return {
        "version": "odylith.greenfield.provisional-design.v6",
        "authority_kind": "provisional_design",
        "first_run": {
            "event_orders": list(event_orders),
            "rationale": "Use this declared fixture walkthrough to prepare and show the result.",
        },
        "components": [
            {
                "key": "vessel-intake",
                "name": "Vessel Intake",
                "responsibility": "Capture the proposed vessel tag.",
                "supported_event_orders": assigned_orders[0],
                "verification": "A submitted vessel tag remains available for occupancy work.",
                "verification_event_orders": assigned_orders[0],
            },
            {
                "key": "occupancy-record",
                "name": "Occupancy Record",
                "responsibility": "Record proposed berth occupancy.",
                "supported_event_orders": assigned_orders[1],
                "verification": "Recorded berth occupancy remains available to the placement view.",
                "verification_event_orders": assigned_orders[1],
            },
            {
                "key": "placement-view",
                "name": "Placement View",
                "responsibility": "Show the proposed berth placement.",
                "supported_event_orders": assigned_orders[2],
                "verification": "The placement view shows the recorded berth placement.",
                "verification_event_orders": assigned_orders[2],
            },
            {
                "key": "placement-evidence",
                "name": "Placement Evidence",
                "responsibility": "Retain proposed evidence for the placement path.",
                "supported_event_orders": assigned_orders[3],
                "verification": "Placement evidence identifies the supported source events.",
                "verification_event_orders": assigned_orders[3],
            },
        ],
        "workstreams": [
            {
                "key": "intake",
                "title": "Deliver vessel intake",
                "problem": "Harbor staff cannot reliably retain a submitted vessel tag.",
                "component_keys": ["vessel-intake"],
                "depends_on": [],
                "deliverable": "Working vessel-tag intake.",
                "verification": "Submit a vessel tag and verify its saved value.",
                "verification_event_orders": assigned_orders[0],
            },
            {
                "key": "occupancy",
                "title": "Deliver occupancy recording",
                "problem": "Harbor staff cannot reliably connect berth occupancy to the submitted vessel.",
                "component_keys": ["occupancy-record"],
                "depends_on": ["intake"],
                "deliverable": "Working berth-occupancy recording.",
                "verification": "Record occupancy and verify the saved berth state.",
                "verification_event_orders": assigned_orders[1],
            },
            {
                "key": "placement",
                "title": "Deliver the placement view",
                "problem": "Harbor staff cannot see the recorded berth placement in one reviewable view.",
                "component_keys": ["placement-view"],
                "depends_on": ["occupancy"],
                "deliverable": "Working berth-placement view.",
                "verification": "Open the view and verify the recorded placement appears.",
                "verification_event_orders": assigned_orders[2],
            },
            {
                "key": "evidence",
                "title": "Deliver placement evidence",
                "problem": "Reviewers cannot trace a displayed placement to its supporting path.",
                "component_keys": ["placement-evidence"],
                "depends_on": ["placement"],
                "deliverable": "Working placement-evidence record.",
                "verification": "Verify the evidence identifies every supported source event.",
                "verification_event_orders": assigned_orders[3],
            },
        ],
        "exchanges": [
            {
                "from_component": "vessel-intake",
                "to_component": "occupancy-record",
                "contract": "Proposed vessel-tag record",
            },
            {
                "from_component": "occupancy-record",
                "to_component": "placement-view",
                "contract": "Proposed berth-occupancy state",
            },
            {
                "from_component": "placement-view",
                "to_component": "placement-evidence",
                "contract": "Proposed placement result",
            },
        ],
        "risk_posture": {
            "status": "no_material_risks_identified",
            "rationale": "This Atlas fixture carries no product-domain risk claim.",
            "items": [],
        },
    }


def _relation(
    order: int,
    actor: str,
    event: str,
    *,
    actor_kind: str = "human",
    owner: str = "",
) -> dict[str, Any]:
    return {
        "order": order,
        "actor_kind": actor_kind,
        "actor_fact_quote": actor,
        "event_quote": event,
        "owner_system_quote": owner,
    }


def test_context_distinguishes_performers_from_contextual_participants() -> None:
    rows = _authored_diagrams(human_actors=("Dock attendant Ivo", "Field Ombud"))
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")
    boxes = {row["node_id"]: row for row in context["diagram_boxes"]}

    assert boxes["actor1"]["role"] == "First-path actor"
    assert boxes["actor2"]["role"] == "Participant"
    assert boxes["actor1"]["description"] == boxes["actor2"]["description"] == ""
    assert boxes["actor2"]["details"] == [{"label": "Action assignment", "text":
        "Named in project evidence; no first-path action is assigned."}]
    assert "actor1 --> product" not in context["mermaid_source"]
    assert (
        'actor1_actions ---|"first-path interaction"| product'
        in context["mermaid_source"]
    )
    assert (
        'actor2 -. "participant context; no action assigned" .-> product'
        in context["mermaid_source"]
    )
    sequence = next(row for row in rows if row["slug"] == "harbor-desk-sequence")
    assert sequence == next(
        row for row in _authored_diagrams() if row["slug"] == "harbor-desk-sequence"
    )
    greenfield_authored_atlas_view.validate_authored_atlas_view(
        context, source_text=context["mermaid_source"]
    )


def test_context_groups_five_exact_events_under_one_human_performer() -> None:
    events = (
        "city staff register residents",
        "city staff match household needs",
        "city staff track constraints",
        "city staff preserve consent evidence",
        "city staff produce readiness report",
    )
    rows = _authored_diagrams(
        human_actors=("city staff",),
        result_event_order=5,
        visible_result="readiness report",
        relations=tuple(
            _relation(order, "city staff", event)
            for order, event in enumerate(events, start=1)
        ),
    )
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")
    boxes = {row["node_id"]: row for row in context["diagram_boxes"]}

    assert 'actor1 -->|"performs"| actor1_actions' in context["mermaid_source"]
    assert (
        'actor1_actions ---|"first-path interaction"| product'
        in context["mermaid_source"]
    )
    assert context["mermaid_source"].count('actor1_actions["') == 1
    assert boxes["actor1_actions"]["label"] == "First-path actions"
    assert boxes["actor1_actions"]["description"].split("\n\n") == list(events)
    assert (
        'actor1_actions["'
        + "<br/><br/>".join("• " + mermaid_label(event, width=42) for event in events)
        + '"]'
    ) in context["mermaid_source"]


def test_context_groups_each_human_performers_events_without_cross_assignment() -> None:
    relations = (
        _relation(1, "Coordinator Mara", "Mara records the intake"),
        _relation(2, "Reviewer Ivo", "Ivo reviews the intake"),
        _relation(3, "Coordinator Mara", "Mara publishes the result"),
    )
    rows = _authored_diagrams(
        human_actors=("Coordinator Mara", "Reviewer Ivo"),
        result_event_order=3,
        visible_result="the result",
        relations=relations,
    )
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")
    boxes = {row["node_id"]: row for row in context["diagram_boxes"]}

    assert boxes["actor1_actions"]["description"].split("\n\n") == [
        "Mara records the intake",
        "Mara publishes the result",
    ]
    assert boxes["actor2_actions"]["description"] == "Ivo reviews the intake"
    assert context["mermaid_source"].count('|"performs"|') == 2


@pytest.mark.parametrize("actor_kind", ["human", "product", "external_system"])
def test_context_action_listing_does_not_claim_the_proposed_execution_order(
    actor_kind: str,
) -> None:
    actor = {"human": "Mara", "product": "Harbor Desk", "external_system": "Harbor Ledger"}[actor_kind]
    relations = tuple(
        _relation(index, actor, event, actor_kind=actor_kind,
                  owner=actor if actor_kind == "product" else "")
        for index, event in enumerate(("Record the intake", "Inspect the tag"), 1)
    )
    design = _provisional_design(event_orders=(1, 2))
    arguments = dict(
        component_label="Harbor Desk", human_actors=("Mara",),
        result_event_order=1, visible_result="the intake", relations=relations,
    )
    source_list_walk = _authored_diagrams(**arguments, provisional_design=design)
    design["first_run"]["event_orders"] = [2, 1]
    reverse_walk = _authored_diagrams(**arguments, provisional_design=design)

    context = reverse_walk[0]
    assert context == source_list_walk[0]
    assert reverse_walk[1]["mermaid_source"] != source_list_walk[1]["mermaid_source"]
    action_box = next(box for box in context["diagram_boxes"] if box["node_id"].endswith("_actions"))
    assert action_box["description"].split("\n\n") == [row["event_quote"] for row in relations]
    assert {"label": "Performer", "text": actor} in action_box["details"]
    assert {"label": "Performer kind", "text": actor_kind} in action_box["details"]
    assert context["read_guide"].count("Listing order does not establish execution order.") == 1


def test_context_excludes_product_events_from_human_action_groups() -> None:
    human_event = "Mara enters a vessel tag"
    product_event = "Harbor Desk records berth occupancy"
    rows = _authored_diagrams(
        human_actors=("Mara",),
        component_label="Harbor Desk",
        result_event_order=2,
        visible_result="berth occupancy",
        relations=(
            _relation(1, "Mara", human_event),
            _relation(
                2,
                "Harbor Desk",
                product_event,
                actor_kind="product",
                owner="Harbor Desk",
            ),
        ),
    )
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")
    action_box = next(
        row for row in context["diagram_boxes"] if row["node_id"] == "actor1_actions"
    )

    assert action_box["description"] == human_event
    assert product_event not in action_box["description"]


@pytest.mark.parametrize("human_actors", [(), ("Field Ombud",)])
def test_context_has_no_human_performer_edges_without_human_events(
    human_actors: tuple[str, ...],
) -> None:
    rows = _authored_diagrams(
        human_actors=human_actors,
        component_label="Harbor Desk",
        result_event_order=1,
        visible_result="berth occupancy",
        relations=(
            _relation(
                1,
                "Harbor Desk",
                "Harbor Desk records berth occupancy",
                actor_kind="product",
                owner="Harbor Desk",
            ),
        ),
    )
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")

    assert 'actor1 -->|"performs"|' not in context["mermaid_source"]
    assert 'product -->|"performs"| product_actions' in context["mermaid_source"]
    assert all(not row["node_id"].startswith("actor1_actions") for row in context["diagram_boxes"])


def test_product_only_context_retains_five_exact_events_without_empty_people() -> None:
    title = "semiconductor reliability lab custody platform"
    events = (
        "semiconductor reliability lab custody platform that receives wafer lot samples",
        "records chamber exposure conditions",
        "preserves chain-of-custody evidence",
        "tracks failed stress runs",
        "prepares release readiness proof for engineering review",
    )
    rows = _authored_diagrams(
        title=title,
        component_label=title,
        result_event_order=5,
        visible_result="release readiness proof",
        human_actors=(),
        external_systems=(),
        relations=tuple(
            _relation(order, title, event, actor_kind="product", owner=title)
            for order, event in enumerate(events, start=1)
        ),
    )
    context = rows[0]
    boxes = {row["node_id"]: row for row in context["diagram_boxes"]}

    assert set(boxes) == {"product", "product_actions"}
    assert boxes["product_actions"]["description"].split("\n\n") == list(events)
    assert 'product -->|"performs"| product_actions' in context["mermaid_source"]
    assert 'product_actions ---|"first-path interaction"| product' not in context["mermaid_source"]
    assert 'subgraph people[' not in context["mermaid_source"]
    assert 'subgraph external_systems[' not in context["mermaid_source"]
    assert not any(row["role"] in {"Participant", "First-path actor"} for row in boxes.values())
    assert greenfield_authored_atlas_view.validate_authored_atlas_view(
        context, source_text=context["mermaid_source"],
    )["diagram_boxes"] == context["diagram_boxes"]


@pytest.mark.parametrize(
    ("actor_kind", "actor", "owner", "node_id", "humans"),
    [
        ("human", "Mara", "", "actor1", ("Mara",)),
        ("product", "Harbor Desk", "Harbor Desk", "product", ()),
        ("external_system", "Harbor Ledger", "", "external1", ()),
    ],
)
def test_context_preserves_a_single_exact_event_for_each_typed_performer(
    actor_kind: str, actor: str, owner: str, node_id: str, humans: tuple[str, ...],
) -> None:
    event = f'{actor} preserves "café" evidence & IDs for review; no approval is implied.'
    context = _authored_diagrams(
        component_label="Harbor Desk",
        human_actors=humans,
        result_event_order=1,
        visible_result='"café" evidence & IDs',
        relations=(_relation(1, actor, event, actor_kind=actor_kind, owner=owner),),
    )[0]
    boxes = {row["node_id"]: row for row in context["diagram_boxes"]}

    assert boxes[f"{node_id}_actions"]["description"] == event
    assert f'{node_id} -->|"performs"| {node_id}_actions' in context["mermaid_source"]
    assert context["mermaid_source"].count('|"performs"|') == 1
    boundary_edge = f'{node_id}_actions ---|"first-path interaction"| product'
    assert (boundary_edge in context["mermaid_source"]) == (actor_kind != "product")
    assert ("people" in boxes) == bool(humans)


def test_context_groups_mixed_typed_performers_without_cross_assignment() -> None:
    context = _authored_diagrams(
        human_actors=("Mara", "Field Ombud"),
        external_systems=("Harbor Ledger", "Tide Service"),
        result_event_order=6,
        visible_result="the receipt",
        components=(
            {"label": "Harbor Desk", "responsibility": "Record the intake", "dependencies": []},
            {
                "label": "Berth map", "responsibility": "Show the placement", "dependencies": [],
                "component_contract": {"external_dependencies": ["Harbor Ledger"]},
            },
        ),
        relations=(
            _relation(1, "Harbor Desk", "Harbor Desk accepts the intake", actor_kind="product", owner="Harbor Desk"),
            _relation(2, "Mara", "Mara enters a vessel tag"),
            _relation(3, "Harbor Ledger", "Harbor Ledger returns the receipt", actor_kind="external_system"),
            _relation(4, "Berth map", "Berth map shows the placement", actor_kind="product", owner="Berth map"),
            _relation(5, "Mara", "Mara reviews the placement"),
            _relation(6, "Harbor Desk", "Harbor Desk retains the receipt", actor_kind="product", owner="Harbor Desk"),
        ),
    )[0]
    boxes = {row["node_id"]: row for row in context["diagram_boxes"]}
    expected = {
        "actor1_actions": ["Mara enters a vessel tag", "Mara reviews the placement"],
        "component1_actions": ["Harbor Desk accepts the intake", "Harbor Desk retains the receipt"],
        "component2_actions": ["Berth map shows the placement"],
        "external1_actions": ["Harbor Ledger returns the receipt"],
    }

    assert {key: row["description"].split("\n\n") for key, row in boxes.items() if key.endswith("_actions")} == expected
    assert boxes["actor2"]["role"] == "Participant"
    assert 'actor2 -->|"performs"|' not in context["mermaid_source"]
    assert 'external2 -->|"performs"|' not in context["mermaid_source"]
    for action_id in expected:
        assert f'{action_id.removesuffix("_actions")} -->|"performs"| {action_id}' in context["mermaid_source"]
    assert 'actor1_actions ---|"first-path interaction"| product' in context["mermaid_source"]
    assert 'external1_actions ---|"first-path interaction"| product' in context["mermaid_source"]
    assert 'component1_actions ---|"first-path interaction"| product' not in context["mermaid_source"]
    assert 'component2_actions ---|"first-path interaction"| product' not in context["mermaid_source"]
    assert "external1 -.-> component2" in context["mermaid_source"]
    assert "external1 -.-> component1" not in context["mermaid_source"]
    assert "external2 -.-> product" in context["mermaid_source"]


@pytest.mark.parametrize(
    ("kind", "actor", "owner", "error"),
    [
        ("human", "Unselected person", "", "missing its typed context owner"),
        ("external_system", "Unselected service", "", "missing its typed context owner"),
        ("product", "Unselected component", "Unselected component", "missing its typed context owner"),
        ("product", "Berth map", "Harbor Desk", "does not match its typed owner"),
    ],
)
def test_context_rejects_unbound_performers_instead_of_assigning_another_owner(
    kind: str, actor: str, owner: str, error: str,
) -> None:
    with pytest.raises(ValueError, match=error):
        _authored_diagrams(
            result_event_order=1,
            visible_result="the exact event",
            relations=(_relation(1, actor, "Preserve the exact event", actor_kind=kind, owner=owner),),
        )


def test_context_retains_repeated_exact_event_text_and_seals_the_group() -> None:
    repeated_event = "Mara records the intake"
    rows = _authored_diagrams(
        human_actors=("Mara",),
        result_event_order=2,
        visible_result="the intake",
        relations=(
            _relation(1, "Mara", repeated_event),
            _relation(2, "Mara", repeated_event),
        ),
    )
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")
    action_box = next(
        row for row in context["diagram_boxes"] if row["node_id"] == "actor1_actions"
    )

    assert action_box["description"].split("\n\n") == [repeated_event, repeated_event]
    assert greenfield_authored_atlas_view.validate_authored_atlas_view(
        context,
        source_text=context["mermaid_source"],
    )["diagram_boxes"] == context["diagram_boxes"]

    tampered = deepcopy(context)
    tampered_action = next(
        row for row in tampered["diagram_boxes"] if row["node_id"] == "actor1_actions"
    )
    tampered_action["description"] = repeated_event
    with pytest.raises(ValueError, match="sealed hash"):
        greenfield_authored_atlas_view.validate_authored_atlas_view(
            tampered,
            source_text=tampered["mermaid_source"],
        )


def test_context_view_represents_a_sole_title_owned_product_once() -> None:
    rows = _authored_diagrams(component_label="Harbor Desk")
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")

    assert context["mermaid_source"].count('["Harbor Desk"]') == 1
    assert 'subgraph product["Harbor Desk"]' not in context["mermaid_source"]
    assert "component1" not in context["mermaid_source"]
    assert [
        (box["node_id"], box["label"], box["role"])
        for box in context["diagram_boxes"]
        if box["label"] == "Harbor Desk"
    ] == [("product", "Harbor Desk", "Product boundary")]


def test_distinct_multiple_components_keep_containment_and_typed_external_target() -> None:
    components = (
        {
            "component_id": "berth-map",
            "label": "Berth map",
            "responsibility": "Record berth occupancy",
            "dependencies": ["Harbor Ledger"],
        },
        {
            "component_id": "receipt-vault",
            "label": "Receipt vault",
            "responsibility": "Retain placement receipts",
            "dependencies": [],
        },
    )
    rows = _authored_diagrams(components=components)
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")
    boxes = {box["node_id"]: box for box in context["diagram_boxes"]}
    for index, component in enumerate(components, 1):
        assert boxes[f"component{index}"]["description"] == component["responsibility"]
        assert boxes[f"component{index}"]["role"] == "Product-owned component"
    assert context["authority_kind"] == "source_grounded"

    source = next(
        row["mermaid_source"] for row in rows if row["slug"] == "harbor-desk-context"
    )
    assert 'subgraph product["Harbor Desk"]' in source
    assert 'component1["Berth map"]' in source
    assert 'component2["Receipt vault"]' in source
    assert "external1 -.-> component1" in source
    assert "external1 -.-> product" not in source
    assert greenfield_authored_atlas_view.validate_authored_atlas_view(context, source_text=source)["diagram_boxes"] == context["diagram_boxes"]


def _traceability_plan() -> SimpleNamespace:
    return SimpleNamespace(diagram_links=())


def test_authored_atlas_view_seals_exact_versioned_display_custody() -> None:
    rows = _authored_diagrams()

    assert len(rows) == 5
    for row in rows:
        authority = row[greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY]
        assert set(authority) == {
            "version",
            "projection_origin",
            "source_sha256",
            "surface_sha256",
            "node_order",
        }
        assert authority["version"] == greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_VERSION
        assert authority["projection_origin"] == AUTHORED_PROJECTION_ORIGIN
        assert authority["source_sha256"] == hashlib.sha256(
            row["mermaid_source"].encode("utf-8")
        ).hexdigest()
        view = greenfield_authored_atlas_view.validate_authored_atlas_view(
            row,
            source_text=row["mermaid_source"],
        )
        assert view == {
            "summary": row["summary"],
            "read_guide": row["read_guide"],
            "diagram_boxes": row["diagram_boxes"],
            "components": row["components"],
        }
        assert authority["node_order"] == [box["node_id"] for box in row["diagram_boxes"]]


def test_authored_atlas_depth_is_five_distinct_semantic_views_not_a_count_floor() -> None:
    rows = _authored_diagrams()

    assert [(row["slug"], row["title"]) for row in rows] == [
        ("harbor-desk-context", "System Context View"),
        ("harbor-desk-sequence", "Proposed First Run"),
        ("harbor-desk-component-exchanges", "Proposed Component Exchanges"),
        (
            "harbor-desk-delivery-dependencies",
            "Proposed Delivery Dependencies and Acceptance",
        ),
        (
            "harbor-desk-capability-support",
            "Proposed Capability Support and Source Facts",
        ),
    ]
    node_ids_by_slug = {
        row["slug"]: {box["node_id"] for box in row["diagram_boxes"]}
        for row in rows
    }
    assert {"people", "product", "external_systems"} <= node_ids_by_slug["harbor-desk-context"]
    assert {
        "event1", "event2", "event3", "performer1", "performer2",
        "proposed_component1", "proposed_component4",
    } <= node_ids_by_slug["harbor-desk-sequence"]
    assert {"proposed", "component1", "component4"} <= node_ids_by_slug[
        "harbor-desk-component-exchanges"
    ]
    assert {"workstream1", "workstream1_acceptance", "workstream4"} <= node_ids_by_slug[
        "harbor-desk-delivery-dependencies"
    ]
    assert {
        "component1", "component4", "source_actions", "source_facts",
        "workstream1_acceptance",
    } <= node_ids_by_slug["harbor-desk-capability-support"]
    assert len({row["summary"] for row in rows}) == 5
    assert len({row["mermaid_source"] for row in rows}) == 5
    source_by_slug = {row["slug"]: row["mermaid_source"] for row in rows}
    assert "actor1 --> product" not in source_by_slug["harbor-desk-context"]
    assert "actor1 --> component1" not in source_by_slug["harbor-desk-context"]
    assert "external1 -.-> component1" in source_by_slug["harbor-desk-context"]
    assert 'component1 -->|"Proposed exchange: Proposed vessel-tag record"| component2' in source_by_slug[
        "harbor-desk-component-exchanges"
    ]
    assert 'workstream1 -->|"proposed prerequisite"| workstream2' in source_by_slug[
        "harbor-desk-delivery-dependencies"
    ]
    support = source_by_slug["harbor-desk-capability-support"]
    assert 'component1 -. "participates in delivery" .-> workstream1_acceptance' in support
    assert "exact source overlap" not in support
    assert "exact source containment" not in support
    assert "state -->" not in support
    assert "result -->" not in support
    assert "proof -->" not in support


def test_provisional_views_keep_authority_and_complete_labels_separate_from_source() -> None:
    rows = _authored_diagrams()
    source_rows = rows[:1]
    design_rows = rows[1:]

    assert all(row["authority_kind"] == "source_grounded" for row in source_rows)
    assert all(row["authority_kind"] == "provisional_design" for row in design_rows)
    assert source_rows[0]["components"] == [
        {"name": "Berth map", "description": "Record berth occupancy"}
    ]
    assert source_rows[0]["related_components"] == [
        "vessel-intake",
        "occupancy-record",
        "placement-view",
        "placement-evidence",
    ]
    assert all("Accepted" not in json.dumps(row["diagram_boxes"]) for row in rows[2:])
    first_run = design_rows[0]
    assert first_run["components"] == design_rows[1]["components"]
    assert "one first run, not all possible paths" in first_run["read_guide"]
    assert 'event1 -.-> event2' in first_run["mermaid_source"]
    assert "event1 --> event2" not in first_run["mermaid_source"]
    exchanges = design_rows[1]
    assert "Proposed berth-occupancy<br/>state" in exchanges["mermaid_source"]
    assert exchanges["diagram_boxes"][1]["description"] == _provisional_design()["components"][0]["responsibility"]
    assert {row["name"] for row in exchanges["components"]} == {
        "Vessel Intake",
        "Occupancy Record",
        "Placement View",
        "Placement Evidence",
    }


def test_single_human_event_sequence_preserves_typed_performer_edge() -> None:
    event = "extension publishers assemble release notes"
    rows = _authored_diagrams(
        human_actors=("extension publishers",),
        external_systems=(),
        visible_result="release notes",
        result_event_order=1,
        relations=(_relation(1, "extension publishers", event),),
        provisional_design=_provisional_design(event_orders=(1,)),
    )
    sequence = next(row for row in rows if row["slug"] == "harbor-desk-sequence")
    boxes = {row["node_id"]: row for row in sequence["diagram_boxes"]}

    assert boxes["performer1"]["label"] == "extension publishers"
    assert boxes["performer1"]["role"] == "Typed event performer"
    assert boxes["event1"]["label"] == "Action 1"
    assert boxes["event1"]["description"] == event
    assert boxes["event1"]["details"] == [{"label": "Source event", "text":
        authored_event_display_text(_relation(1, "extension publishers", event))}]
    assert boxes["performer1"]["description"] == ""
    assert 'performer1 --> event1' in sequence["mermaid_source"]
    assert 'event1 -. "proposed support" .-> proposed_component1' in sequence["mermaid_source"]
    assert {"label": "Proposed exchange 1 to Occupancy Record", "text": "Proposed vessel-tag record"} in boxes["proposed_component1"]["details"]
    assert "proposed exchange" not in sequence["mermaid_source"]


def test_first_run_keeps_result_first_source_ids_and_proposed_links() -> None:
    design = _provisional_design(event_orders=(1, 2, 3))
    design["first_run"] = {
        "event_orders": [2, 3, 1],
        "rationale": "Capture the vessel and record occupancy before showing the placement.",
    }
    relations = (
        _relation(1, "Berth map", "Berth map shows the placement", actor_kind="product", owner="Berth map"),
        _relation(2, "Dock attendant Ivo", "Dock attendant Ivo enters a vessel tag"),
        _relation(3, "Berth map", "Berth map records berth occupancy", actor_kind="product", owner="Berth map"),
    )
    rows = _authored_diagrams(
        relations=relations, provisional_design=design,
        result_event_order=1, visible_result="the placement",
    )
    first_run = rows[1]
    assert first_run["authority_kind"] == "provisional_design"
    assert [box["node_id"] for box in first_run["diagram_boxes"] if box["node_id"].startswith("event")] == [
        "event1", "event2", "event3",
    ]
    source = first_run["mermaid_source"]
    assert 'event2 -.-> event3' in source
    assert 'event3 -.-> event1' in source
    assert 'event1 -.-> event2' not in source
    design["first_run"]["event_orders"] = [2, 1]
    rows = _authored_diagrams(
        relations=relations, provisional_design=design,
        result_event_order=1, visible_result="the placement",
    )
    selected = rows[1]
    assert [
        box["node_id"] for box in selected["diagram_boxes"]
        if box["node_id"].startswith("event")
    ] == ["event1", "event2"]
    assert 'event2 -.-> event1' in selected["mermaid_source"]
    proposed_steps = [
        line.strip() for line in selected["mermaid_source"].splitlines()
        if line.strip().startswith("event") and " -.-> event" in line
    ]
    assert proposed_steps == ['event2 -.-> event1']
    assert "event3" not in selected["mermaid_source"]


def test_context_does_not_call_unselected_supporting_relation_a_first_path_action() -> None:
    design = _provisional_design(event_orders=(1, 2, 3, 4))
    design["first_run"]["event_orders"] = [1, 2, 3]
    design["components"][3]["supported_event_orders"] = [4]
    design["components"][3]["verification_event_orders"] = [4]
    design["workstreams"][3]["verification_event_orders"] = [4]
    rows = _authored_diagrams(
        human_actors=("Dock attendant Ivo", "Harbor liaison"),
        relations=(
            _relation(1, "Dock attendant Ivo", "Dock attendant Ivo enters a vessel tag"),
            _relation(2, "Berth map", "the product records berth occupancy", actor_kind="product", owner="Berth map"),
            _relation(3, "Berth map", "the berth map shows the placement", actor_kind="product", owner="Berth map"),
            _relation(4, "Harbor liaison", "Harbor liaison inventories old berths"),
        ),
        provisional_design=design,
    )
    context, sequence, support = rows[0], rows[1], rows[-1]
    context_boxes = {box["node_id"]: box for box in context["diagram_boxes"]}

    assert context_boxes["actor2"]["role"] == "Participant"
    assert context_boxes["actor2"]["description"] == ""
    assert "no first-path action is assigned" in context_boxes["actor2"]["details"][0]["text"]
    assert "Harbor liaison inventories old berths" not in context["mermaid_source"]
    assert "event4" not in sequence["mermaid_source"]
    assert "proposed_component4" not in sequence["mermaid_source"]
    assert "Action 4" in next(box["details"][0]["text"] for box in support["diagram_boxes"] if box["node_id"] == "source_actions")


def _source_lifecycle() -> dict[str, Any]:
    return {
        "state_fields": [
            {
                "duty_id": "F1", "state_object": "berth occupancy", "field": "access",
                "meaning": "whether the placement remains accessible",
                "source_refs": [{"quote": "placement access", "occurrence": 1}],
            },
            {
                "duty_id": "F2", "state_object": "berth occupancy", "field": "cache",
                "meaning": "retained placement copy",
                "source_refs": [{"quote": "cached placement", "occurrence": 1}],
            },
        ],
        "off_path_transitions": [
            {
                "duty_id": "T1", "trigger": "withdrawal",
                "governed_object": "berth occupancy", "component_key": "occupancy-record",
                "workstream_key": "occupancy",
                "source_refs": [{
                    "quote": "Withdrawal closes placement access and erases the cached placement",
                    "occurrence": 1,
                }],
                "effects": [
                    {"state_field_id": "F1", "field": "access", "change": "closed", "observable_check": "access closed"},
                    {"state_field_id": "F2", "field": "cache", "change": "erased", "observable_check": "cache empty"},
                ],
            }
        ],
    }


def test_cited_off_path_lifecycle_keeps_two_effects_out_of_first_run() -> None:
    rows = _authored_diagrams(source_lifecycle=_source_lifecycle())
    first_run, support = rows[1], rows[-1]
    boxes = {box["node_id"]: box for box in support["diagram_boxes"]}
    source = support["mermaid_source"]

    assert "Withdrawal closes placement access and erases the cached placement" in boxes[
        "off_path_transition1"
    ]["description"]
    assert boxes["off_path_transition1"]["role"] == "Source-stated off-path transition"
    assert boxes["off_path_transition1_effect1"]["label"] == "Effect 1.1"
    assert boxes["off_path_transition1_effect2"]["label"] == "Effect 1.2"
    assert boxes["off_path_transition1_effect1"]["description"] == "closed"
    assert boxes["off_path_transition1_effect2"]["description"] == "erased"
    assert {"label": "Observable check", "text": "access closed"} in boxes["off_path_transition1_effect1"]["details"]
    assert {"label": "Observable check", "text": "cache empty"} in boxes["off_path_transition1_effect2"]["details"]
    assert {"label": "Trigger", "text": _source_lifecycle()["off_path_transitions"][0]["trigger"]} in boxes["off_path_transition1"]["details"]
    assert boxes["state_field1"]["description"] == _source_lifecycle()["state_fields"][0]["meaning"]
    assert boxes["state_field2"]["description"] == _source_lifecycle()["state_fields"][1]["meaning"]
    assert {"label": "Source", "text": "“placement access”"} in boxes["state_field1"]["details"]
    assert {"label": "Source", "text": "“cached placement”"} in boxes["state_field2"]["details"]
    assert 'component2 -. "proposed lifecycle support" .-> off_path_transition1' in source
    assert 'off_path_transition1_effect1 -->|"changes access"| state_field1' in source
    assert 'off_path_transition1_effect2 -->|"changes cache"| state_field2' in source
    assert 'off_path_transition1_effect1["Effect 1.1<br/>closed"]' in source
    assert 'off_path_transition1_effect2["Effect 1.2<br/>erased"]' in source
    assert "off_path_transition" not in first_run["mermaid_source"]
    assert "withdrawal" not in first_run["mermaid_source"].lower()
    assert [box["node_id"] for box in first_run["diagram_boxes"] if box["node_id"].startswith("event")] == [
        "event1", "event2", "event3"
    ]


def test_lifecycle_effects_on_the_same_field_show_their_distinct_exact_changes() -> None:
    lifecycle = _source_lifecycle()
    lifecycle["off_path_transitions"][0]["effects"] = [
        {
            "state_field_id": "F2", "field": "cache",
            "change": "Exclude the withdrawn record from future cached results.",
            "observable_check": "A new query excludes the withdrawn record.",
        },
        {
            "state_field_id": "F2", "field": "cache",
            "change": "Invalidate existing unpublished cached results that include the withdrawn record.",
            "observable_check": "Existing unpublished results cannot be released.",
        },
    ]
    support = _authored_diagrams(source_lifecycle=lifecycle)[-1]
    boxes = {box["node_id"]: box for box in support["diagram_boxes"]}
    for index, effect in enumerate(lifecycle["off_path_transitions"][0]["effects"], 1):
        node = f"off_path_transition1_effect{index}"
        assert f'{node}["Effect 1.{index}<br/>{mermaid_label(effect["change"], width=32)}"]' in support["mermaid_source"]
        assert boxes[node]["description"] == effect["change"]
        assert {"label": "Observable check", "text": effect["observable_check"]} in boxes[node]["details"]
        assert f'{node} -->|"changes cache"| state_field2' in support["mermaid_source"]


def test_absent_lifecycle_does_not_invent_atlas_transition() -> None:
    support = _authored_diagrams()[-1]
    assert "off_path_transition" not in support["mermaid_source"]
    assert not any(box["role"] == "Source-stated off-path transition" for box in support["diagram_boxes"])


@pytest.mark.parametrize("event_count", [1, 3, 13])
@pytest.mark.parametrize("reverse_rows", [False, True])
def test_capability_support_compact_map_preserves_complete_many_to_many_detail(
    event_count: int, reverse_rows: bool,
) -> None:
    relations = tuple(
        _relation(order, "Dock attendant Ivo", f"Dock attendant Ivo reviews source record {order}")
        for order in range(1, event_count + 1)
    )
    if reverse_rows:
        relations = tuple(reversed(relations))
    design = _provisional_design(event_orders=tuple(range(1, event_count + 1)))
    before = deepcopy((relations, design))
    support = _authored_diagrams(
        relations=relations, provisional_design=design, result_event_order=event_count,
    )[-1]
    boxes = {box["node_id"]: box for box in support["diagram_boxes"]}
    source = support["mermaid_source"]
    assert boxes["source_actions"]["description"] == ""
    action_detail = boxes["source_actions"]["details"][0]["text"]
    for event in sorted(relations, key=lambda row: row["order"]):
        complete = (
            f"Action {event['order']}\n"
            f"{authored_event_display_text(event)}"
        )
        assert action_detail.count(complete) == 1
        assert {"label": "Performer kinds", "text": "\n".join(
            f"Action {row['order']}: {row['actor_kind']}" for row in relations
        )} in boxes["source_actions"]["details"]
    for index, component in enumerate(design["components"], 1):
        box = boxes[f"component{index}"]
        actions = "Source actions: " + ", ".join(map(str, component["supported_event_orders"]))
        details = {row["label"]: row["text"] for row in box["details"]}
        assert details["Source actions"] == "\n\n".join(
            f"Source action {order} · human\n{authored_event_display_text(next(event for event in relations if event['order'] == order))}"
            for order in component["supported_event_orders"]
        )
        assert mermaid_label(actions, width=32) in source
        assert box["description"] == component["responsibility"]
        assert details["Proposed boundary verification"] == component["verification"]
        assert details["Verification source actions"] == "\n\n".join(
            f"Source action {order} · human\n{authored_event_display_text(next(event for event in relations if event['order'] == order))}"
            for order in component["verification_event_orders"]
        )
        assert box["role"] == "Proposed component support"
    for index, workstream in enumerate(design["workstreams"], 1):
        box = boxes[f"workstream{index}_acceptance"]
        details = {row["label"]: row["text"] for row in box["details"]}
        assert details["Proposed verification"] == workstream["verification"]
        assert box["description"] == workstream["deliverable"]
        assert details["Participating components"] == ", ".join(workstream["component_keys"])
    assert boxes["source_facts"]["description"] == ""
    assert boxes["source_facts"]["details"] == [
        {"label": "State object", "text": "berth occupancy"},
        {"label": "Visible result", "text": "the berth map shows the placement"},
        {"label": "Proof boundary", "text": "Verify the placement and retention receipt"},
        {"label": "Non-goal 1", "text": "Do not manage vessel scheduling"},
    ]
    assert "source_actions -->" not in source and "source_facts -->" not in source
    assert source.count(".->") == sum(len(row["component_keys"]) for row in design["workstreams"])
    assert "Select a diagram box in Read mode for complete statements" in support["read_guide"]
    assert (relations, design) == before


def test_long_statements_change_sealed_detail_without_expanding_support_topology() -> None:
    baseline = _authored_diagrams()[-1]
    design = _provisional_design()
    long_statement = "Keep every retained record and its original safety boundary; " * 35 + "the final clause remains."
    for component in design["components"]:
        component["responsibility"] = long_statement
        component["verification"] = long_statement
    for workstream in design["workstreams"]:
        workstream["deliverable"] = long_statement
        workstream["verification"] = long_statement
    support = _authored_diagrams(provisional_design=design)[-1]
    assert support["mermaid_source"] == baseline["mermaid_source"]
    details = {box["node_id"]: box for box in support["diagram_boxes"]}
    for node, verification_label in (("component1", "Proposed boundary verification"), ("workstream1_acceptance", "Proposed verification")):
        assert details[node]["description"] == long_statement
        assert {"label": verification_label, "text": long_statement} in details[node]["details"]
    assert support["authored_atlas_view_authority"]["surface_sha256"] != baseline["authored_atlas_view_authority"]["surface_sha256"]


def test_first_path_keeps_upstream_support_without_selecting_its_actions_or_downstream_consumers() -> None:
    design = _provisional_design(event_orders=(1, 2, 3, 4))
    design["first_run"]["event_orders"] = [3]
    design["components"][3]["supported_event_orders"] = [4]
    design["components"][3]["verification_event_orders"] = [4]
    design["workstreams"][3]["verification_event_orders"] = [4]
    rows = _authored_diagrams(
        relations=tuple(_relation(order, "Dock attendant Ivo", f"reviews record {order}") for order in range(1, 5)),
        provisional_design=design,
    )
    sequence = rows[1]
    boxes = {box["node_id"]: box for box in sequence["diagram_boxes"]}
    assert set(boxes) == {"event3", "performer1", "proposed_component1", "proposed_component2", "proposed_component3"}
    assert boxes["proposed_component1"]["role"] == "Proposed supporting component"
    for index, exchange in enumerate(design["exchanges"][:2], 1):
        detail = boxes[f"proposed_component{index}"]["details"][0]
        assert detail["label"].startswith(f"Proposed exchange {index} to")
        assert detail["text"] == exchange["contract"]
    assert {"label": "Proposed delivery prerequisite", "text": "Vessel Intake through Deliver vessel intake."} in boxes["proposed_component2"]["details"]
    assert "proposed delivery" not in sequence["mermaid_source"]


def test_compact_support_keeps_provisional_proof_out_of_source_facts() -> None:
    from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import build_provisional_design_atlas_specs

    relations = [{**_relation(order, "Dock attendant Ivo", f"reviews record {order}"), "visible_result_quote": ""} for order in (1, 2, 3)]
    support = build_provisional_design_atlas_specs(
        provisional_design=_provisional_design(), relations=relations,
        state_object="berth occupancy", visible_result="Proposed visible result",
        proof_boundary="Proposed retention checkpoint", non_goals=["No scheduling"],
        source_precedence=(), proof_is_provisional=True,
    )["capability_support"]
    boxes = {box["node_id"]: box for box in support["boxes"]}
    assert boxes["source_facts"]["description"] == ""
    assert boxes["source_facts"]["details"] == [
        {"label": "State object", "text": "berth occupancy"},
        {"label": "Non-goal 1", "text": "No scheduling"},
    ]
    assert boxes["proof"]["description"] == "Proposed retention checkpoint"
    assert boxes["proof"]["role"] == "Proposed proof checkpoint"
    assert "no source-stated producer or terminal result is asserted" in boxes["proof"]["details"][0]["text"]
    assert "Assumption" in support["source"]


def test_first_path_preserves_long_contracts_and_empty_action_support_in_detail() -> None:
    design = _provisional_design()
    design["first_run"]["event_orders"] = [1, 3]
    long_contract = "Retain authorization, withdrawal and privacy boundaries across the handoff; " * 25 + "preserve the final condition."
    design["exchanges"][0]["contract"] = long_contract
    before = deepcopy(design)
    rows = _authored_diagrams(provisional_design=design, source_lifecycle=_source_lifecycle())
    first_run, support = rows[1], rows[-1]
    boxes = {box["node_id"]: box for box in first_run["diagram_boxes"]}
    assert boxes["proposed_component2"]["role"] == "Proposed supporting component"
    assert long_contract == boxes["proposed_component1"]["details"][0]["text"]
    assert boxes["proposed_component1"]["description"] == design["components"][0]["responsibility"]
    assert long_contract not in first_run["mermaid_source"]
    support_boxes = {box["node_id"]: box for box in support["diagram_boxes"]}
    assert support_boxes["component2"]["details"][0]["text"].startswith("Source action 2 · product\n")
    assert "Withdrawal closes placement access and erases the cached placement" in support_boxes["off_path_transition1"]["description"]
    assert support_boxes["off_path_transition1_effect2"]["description"] == "erased"
    assert {"label": "Observable check", "text": "cache empty"} in support_boxes["off_path_transition1_effect2"]["details"]
    assert design == before


def test_authored_atlas_authority_kind_is_sealed_with_the_display() -> None:
    row = deepcopy(_authored_diagrams()[0])
    row["authority_kind"] = "provisional_design"

    with pytest.raises(ValueError, match="sealed hash"):
        greenfield_authored_atlas_view.validate_authored_atlas_view(
            row,
            source_text=row["mermaid_source"],
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("missing", "missing"),
        ("duplicate", "duplicate"),
        ("reordered", "reordered"),
        ("unmatched", "unmatched"),
    ),
)
def test_authored_atlas_view_rejects_box_custody_drift_before_staging(
    mutation: str,
    message: str,
) -> None:
    row = deepcopy(_authored_diagrams()[0])
    if mutation == "missing":
        row["diagram_boxes"].pop()
    elif mutation == "duplicate":
        row["diagram_boxes"].append(deepcopy(row["diagram_boxes"][0]))
    elif mutation == "reordered":
        row["diagram_boxes"][0], row["diagram_boxes"][1] = (
            row["diagram_boxes"][1],
            row["diagram_boxes"][0],
        )
    else:
        row["diagram_boxes"][-1]["node_id"] = "unmatched-node"

    with pytest.raises(ValueError, match=message):
        greenfield_apply_diagrams.render_prewrite_atlas_sources({"diagrams": [row]})


def test_authored_atlas_origin_cannot_fall_back_to_legacy_when_marker_is_missing() -> None:
    row = deepcopy(_authored_diagrams()[0])
    row.pop(greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY)

    with pytest.raises(ValueError, match="authority must be an object"):
        greenfield_apply_diagrams.render_prewrite_atlas_sources({"diagrams": [row]})


def test_authored_atlas_catalog_and_source_survive_compilation_and_readback_exactly(
    tmp_path: Path,
) -> None:
    proposal_row = _authored_diagrams()[0]
    sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(
        {"diagrams": [proposal_row]}
    )
    compiled_row = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=tmp_path,
        rows=(proposal_row,),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(),
        review_date="2026-08-31",
    )[0]
    authority_key = greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY
    assert compiled_row["projection_origin"] == proposal_row["projection_origin"]
    assert compiled_row["authority_kind"] == proposal_row["authority_kind"]
    assert compiled_row[authority_key] == proposal_row[authority_key]
    assert compiled_row["diagram_boxes"] == proposal_row["diagram_boxes"]
    assert compiled_row["summary"] == proposal_row["summary"]
    assert compiled_row["read_guide"] == proposal_row["read_guide"]
    assert compiled_row["components"] == proposal_row["components"]

    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text('{"version":"v1","diagrams":[]}\n', encoding="utf-8")
    result = greenfield_apply_diagrams.materialize_apply_diagrams(
        root=tmp_path,
        rows=(proposal_row,),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(),
        rendered_atlas_sources=sources,
        review_date="2026-08-31",
        require_compiled_sources=True,
        compiled_catalog_rows=(compiled_row,),
    )

    assert result.diagram_ids == ("D-001",)
    written_row = json.loads(catalog_path.read_text(encoding="utf-8"))["diagrams"][0]
    canonical = lambda value: json.dumps(  # noqa: E731 - compact byte comparison helper
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert canonical(written_row) == canonical(compiled_row)
    source_path = tmp_path / compiled_row["source_mmd"]
    assert source_path.read_bytes() == sources[compiled_row["source_mmd"]].encode("utf-8")
    greenfield_authored_atlas_view.validate_authored_atlas_view(
        written_row,
        source_text=source_path.read_text(encoding="utf-8"),
    )


def test_marked_authored_atlas_catalog_direct_renders_exact_rows_without_legacy_parsers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_row = _authored_diagrams()[0]
    sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(
        {"diagrams": [proposal_row]}
    )
    compiled_row = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=tmp_path,
        rows=(proposal_row,),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(),
        review_date=dt.date.today().isoformat(),
    )[0]
    source_path = tmp_path / compiled_row["source_mmd"]
    svg_path = tmp_path / compiled_row["source_svg"]
    png_path = tmp_path / compiled_row["source_png"]
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    for path in (source_path, svg_path, png_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(sources[compiled_row["source_mmd"]], encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    png_path.write_bytes(b"png")
    catalog_path.write_text(
        f"{json.dumps({'version': 'v1', 'diagrams': [compiled_row]}, indent=2)}\n",
        encoding="utf-8",
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("marked authored Atlas row entered a legacy semantic parser")

    monkeypatch.setattr(atlas_box_explanations, "normalize_catalog_diagram_boxes", forbidden)
    monkeypatch.setattr(atlas_box_explanations, "clean_component_description", forbidden)
    monkeypatch.setattr(atlas_box_explanations, "merge_diagram_box_explanations", forbidden)
    monkeypatch.setattr(atlas_diagram_intelligence, "build_diagram_narrative", forbidden)

    diagrams, errors, stats = render_mermaid_catalog._load_catalog(  # noqa: SLF001
        repo_root=tmp_path,
        catalog_path=catalog_path,
        output_path=tmp_path / "odylith/atlas/atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    assert stats == {"total": 1, "fresh": 1, "stale": 0}
    assert diagrams[0]["summary"] == proposal_row["summary"]
    assert diagrams[0]["read_guide"] == proposal_row["read_guide"]
    assert diagrams[0]["diagram_boxes"] == proposal_row["diagram_boxes"]
    assert diagrams[0]["components"] == proposal_row["components"]


def test_public_authored_propose_never_calls_legacy_semantic_rule_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    family_calls = {
        "terminal_deferral": 0,
        "source_casing": 0,
        "connector": 0,
    }
    def trap(family: str, module: object, name: str) -> None:
        original = getattr(module, name)

        def guarded(*args: object, **kwargs: object) -> object:
            family_calls[family] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(module, name, guarded)

    trap(
        "terminal_deferral",
        greenfield_deferral_predicates,
        "terminal_deferral_subject",
    )
    trap(
        "source_casing",
        greenfield_confirmed_text,
        "capitalize_sentence_start_preserving_source_terms",
    )
    trap("connector", greenfield_confirmed_text, "normalize_connector_sequence")

    rc, payload = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=_authored_intent(),
    )

    assert rc == 0, payload
    assert family_calls["terminal_deferral"] == 0
    assert family_calls["source_casing"] == 0
    assert family_calls["connector"] == 0

    transaction = json.loads(
        (tmp_path / payload["transaction_file"]).read_text(encoding="utf-8")
    )
    proposal_rows = transaction["proposal"]["diagrams"]
    compiled_rows = transaction["prewrite_package"]["atlas_catalog_rows"]
    authority_key = greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY
    assert len(proposal_rows) == len(compiled_rows) == 5
    for proposal_row, compiled_row in zip(proposal_rows, compiled_rows, strict=True):
        assert compiled_row["projection_origin"] == AUTHORED_PROJECTION_ORIGIN
        assert compiled_row[authority_key] == proposal_row[authority_key]
        assert compiled_row["diagram_boxes"] == proposal_row["diagram_boxes"]
        assert compiled_row["summary"] == proposal_row["summary"]
        assert compiled_row["read_guide"] == proposal_row["read_guide"]
        assert compiled_row["components"] == proposal_row["components"]


def test_authored_responsibility_and_detail_text_are_exact_and_separately_sealed() -> None:
    design = _provisional_design()
    narrative = 'Preserve café  IDs and **authored** boundaries.\nKeep <tag> & `proof` without rewriting the second sentence.'
    verification = 'Inspect 日本語 evidence and <img src=x onerror=alert(1)> literally. ' * 30 + 'Retain the final condition.'
    design['components'][0]['responsibility'] = narrative
    design['components'][0]['verification'] = verification
    before = deepcopy(design)
    rows = _authored_diagrams(provisional_design=design)
    for row in rows[1:]:
        assert row['components'][0]['description'] == narrative
    for row, node in ((rows[1], 'proposed_component1'), (rows[2], 'component1'), (rows[-1], 'component1')):
        box = next(box for box in row['diagram_boxes'] if box['node_id'] == node)
        assert box['description'] == narrative
        projection = greenfield_authored_atlas_view.validate_authored_atlas_view(row, source_text=row['mermaid_source'])
        assert projection['diagram_boxes'] == row['diagram_boxes']
    support = rows[-1]
    box = next(box for box in support['diagram_boxes'] if box['node_id'] == 'component1')
    assert box['details'][1] == {'label': 'Proposed boundary verification', 'text': verification}
    assert 'actor' not in box['description']
    assert box['role'] == 'Proposed component support'
    assert support['read_guide'].count("does not transfer the stated actor's action") == 1
    assert design == before


@pytest.mark.parametrize('mutation', ['text', 'label', 'drop', 'reorder', 'add'])
def test_authored_detail_custody_rejects_unsealed_changes(mutation: str) -> None:
    row = _authored_diagrams()[-1]
    box = next(box for box in row['diagram_boxes'] if box['node_id'] == 'component1')
    if mutation in ('text', 'label'):
        box['details'][0][mutation] += ' altered'
    elif mutation == 'drop':
        box.pop('details')
    elif mutation == 'reorder':
        box['details'].reverse()
    else:
        box['details'].append({'label': 'Additional check', 'text': 'A newly asserted check.'})
    with pytest.raises(ValueError, match='sealed hash'):
        greenfield_authored_atlas_view.validate_authored_atlas_view(row, source_text=row['mermaid_source'])


@pytest.mark.parametrize('details', [None, '', {}, [None], [{'label': 'Check'}],
    [{'label': 'Check', 'text': 'Exact.', 'authority': 'source'}],
    [{'label': '', 'text': 'Exact.'}], [{'label': 'Check', 'text': 1}],
    [{'label': 'Check', 'text': ' altered '}],
])
def test_authored_detail_schema_fails_before_custody_admission(details: Any) -> None:
    row = _authored_diagrams()[-1]
    row['diagram_boxes'][0]['details'] = details
    with pytest.raises(ValueError, match='Atlas box details'):
        greenfield_authored_atlas_view.validate_authored_atlas_view(row, source_text=row['mermaid_source'])


def test_absent_detail_v3_projection_keeps_observed_prechange_digest() -> None:
    # Captured from the unchanged pre-disclosure compiler and fixture; no new builder supplies the expected digest.
    row = json.loads((Path(__file__).parents[2] / 'fixtures/atlas-authored-v3-pre-disclosure-context.json').read_text())
    assert all('details' not in box for box in row['diagram_boxes'])
    authority = row[greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY]
    assert authority['version'] == 'odylith.greenfield.authored-atlas-view.v3'
    assert authority['surface_sha256'] == 'fa50c2a875f91fc6f34124a2b14bb94f3ad9baadb16041eb8a9175085ddb1798'
    assert greenfield_authored_atlas_view.validate_authored_atlas_view(row, source_text=row['mermaid_source'])['diagram_boxes'] == row['diagram_boxes']


@pytest.mark.parametrize("description", [None, 0, {}, " ", "\n", " padded "])
def test_omitted_copy_does_not_admit_malformed_description(description: Any) -> None:
    row = deepcopy(_authored_diagrams()[0])
    row["diagram_boxes"][0]["description"] = description
    with pytest.raises(ValueError, match="description"):
        greenfield_authored_atlas_view.validate_authored_atlas_view(row, source_text=row["mermaid_source"])


def test_omitted_copy_still_requires_field_and_exact_sealed_support() -> None:
    row = _authored_diagrams()[0]
    assert row["diagram_boxes"][0]["description"] == ""
    assert greenfield_authored_atlas_view.validate_authored_atlas_view(
        row, source_text=row["mermaid_source"],
    )["diagram_boxes"] == row["diagram_boxes"]
    missing = deepcopy(row)
    del missing["diagram_boxes"][0]["description"]
    with pytest.raises(ValueError, match="invalid schema"):
        greenfield_authored_atlas_view.validate_authored_atlas_view(missing, source_text=row["mermaid_source"])
    forged = deepcopy(row)
    forged["diagram_boxes"][0]["details"] = [{"label": "Actor", "text": "A different performer"}]
    with pytest.raises(ValueError, match="sealed hash"):
        greenfield_authored_atlas_view.validate_authored_atlas_view(forged, source_text=row["mermaid_source"])
    action = next(box for box in forged["diagram_boxes"] if box["node_id"].endswith("_actions"))
    forged = deepcopy(row)
    next(box for box in forged["diagram_boxes"] if box["node_id"] == action["node_id"])["description"] = ""
    with pytest.raises(ValueError, match="sealed hash"):
        greenfield_authored_atlas_view.validate_authored_atlas_view(forged, source_text=row["mermaid_source"])


def test_delivery_uses_short_title_and_each_exact_authored_fact_once() -> None:
    design = _provisional_design()
    design["workstreams"][0]["deliverable"] = 'Preserve café  IDs and <tag> & "proof".\nKeep the final clause.'
    design["workstreams"][0]["verification"] = "Verify the complete 日本語 condition without claiming it passed."
    frozen = deepcopy(design)
    row = _authored_diagrams(provisional_design=design)[3]
    boxes = {box["node_id"]: box for box in row["diagram_boxes"]}
    for index, workstream in enumerate(design["workstreams"], 1):
        assert boxes[f"workstream{index}"]["label"] == workstream["title"]
        assert boxes[f"workstream{index}_acceptance"]["label"] == workstream["title"]
        assert boxes[f"workstream{index}"]["description"] == workstream["deliverable"]
        assert boxes[f"workstream{index}_acceptance"]["description"] == workstream["verification"]
        assert f'workstream{index} -. "proposed acceptance" .-> workstream{index}_acceptance' in row["mermaid_source"]
    assert design == frozen
