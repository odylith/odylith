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
from odylith.runtime.domain_intelligence import greenfield_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
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
    )


def _provisional_design(*, event_orders: tuple[int, ...] = (1, 2, 3)) -> dict[str, Any]:
    assigned_orders = [
        [event_orders[index % len(event_orders)]] for index in range(3)
    ]
    assigned_orders.append(list(event_orders))
    return {
        "version": "odylith.greenfield.provisional-design.v2",
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
            },
            {
                "key": "occupancy-record",
                "name": "Occupancy Record",
                "responsibility": "Record proposed berth occupancy.",
                "supported_event_orders": assigned_orders[1],
                "verification": "Recorded berth occupancy remains available to the placement view.",
            },
            {
                "key": "placement-view",
                "name": "Placement View",
                "responsibility": "Show the proposed berth placement.",
                "supported_event_orders": assigned_orders[2],
                "verification": "The placement view shows the recorded berth placement.",
            },
            {
                "key": "placement-evidence",
                "name": "Placement Evidence",
                "responsibility": "Retain proposed evidence for the placement path.",
                "supported_event_orders": assigned_orders[3],
                "verification": "Placement evidence identifies the supported source events.",
            },
        ],
        "workstreams": [
            {
                "key": "intake",
                "title": "Deliver vessel intake",
                "component_keys": ["vessel-intake"],
                "depends_on": [],
                "deliverable": "Working vessel-tag intake.",
                "verification": "Submit a vessel tag and verify its saved value.",
            },
            {
                "key": "occupancy",
                "title": "Deliver occupancy recording",
                "component_keys": ["occupancy-record"],
                "depends_on": ["intake"],
                "deliverable": "Working berth-occupancy recording.",
                "verification": "Record occupancy and verify the saved berth state.",
            },
            {
                "key": "placement",
                "title": "Deliver the placement view",
                "component_keys": ["placement-view"],
                "depends_on": ["occupancy"],
                "deliverable": "Working berth-placement view.",
                "verification": "Open the view and verify the recorded placement appears.",
            },
            {
                "key": "evidence",
                "title": "Deliver placement evidence",
                "component_keys": ["placement-evidence"],
                "depends_on": ["placement"],
                "deliverable": "Working placement-evidence record.",
                "verification": "Verify the evidence identifies every supported source event.",
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
    assert boxes["actor2"]["description"] == (
        "Named in project evidence; no first-path action is assigned."
    )
    assert "actor1 --> product" not in context["mermaid_source"]
    assert "actor2 --> product" not in context["mermaid_source"]
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
    assert context["mermaid_source"].count('actor1_actions["') == 1
    assert boxes["actor1_actions"]["label"] == "\n".join(events)
    assert [line for line in boxes["actor1_actions"]["label"].splitlines()] == list(events)


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

    assert boxes["actor1_actions"]["label"].splitlines() == [
        "Mara records the intake",
        "Mara publishes the result",
    ]
    assert boxes["actor2_actions"]["label"] == "Ivo reviews the intake"
    assert context["mermaid_source"].count('|"performs"|') == 2


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

    assert action_box["label"] == human_event
    assert product_event not in action_box["label"]


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
    assert boxes["product_actions"]["label"] == "\n".join(events)
    assert 'product -->|"performs"| product_actions' in context["mermaid_source"]
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

    assert boxes[f"{node_id}_actions"]["label"] == event
    assert f'{node_id} -->|"performs"| {node_id}_actions' in context["mermaid_source"]
    assert context["mermaid_source"].count('|"performs"|') == 1
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

    assert {key: row["label"].splitlines() for key, row in boxes.items() if key.endswith("_actions")} == expected
    assert boxes["actor2"]["role"] == "Participant"
    assert 'actor2 -->|"performs"|' not in context["mermaid_source"]
    assert 'external2 -->|"performs"|' not in context["mermaid_source"]
    for action_id in expected:
        assert f'{action_id.removesuffix("_actions")} -->|"performs"| {action_id}' in context["mermaid_source"]
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

    assert action_box["label"].splitlines() == [repeated_event, repeated_event]
    assert greenfield_authored_atlas_view.validate_authored_atlas_view(
        context,
        source_text=context["mermaid_source"],
    )["diagram_boxes"] == context["diagram_boxes"]

    tampered = deepcopy(context)
    tampered_action = next(
        row for row in tampered["diagram_boxes"] if row["node_id"] == "actor1_actions"
    )
    tampered_action["label"] = repeated_event
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

    source = next(
        row["mermaid_source"] for row in rows if row["slug"] == "harbor-desk-context"
    )
    assert 'subgraph product["Harbor Desk"]' in source
    assert 'component1["Berth map"]' in source
    assert 'component2["Receipt vault"]' in source
    assert "external1 -.-> component1" in source
    assert "external1 -.-> product" not in source


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
    assert {"event1", "event2", "event3", "owner1"} <= node_ids_by_slug["harbor-desk-sequence"]
    assert {"proposed", "component1", "component4"} <= node_ids_by_slug[
        "harbor-desk-component-exchanges"
    ]
    assert {"workstream1", "workstream1_acceptance", "workstream4"} <= node_ids_by_slug[
        "harbor-desk-delivery-dependencies"
    ]
    assert {
        "component1_support",
        "component1_actions",
        "component1",
        "component1_verification",
        "source_facts",
        "state",
        "result",
        "proof",
        "non_goal1",
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
    assert 'component1 -->|"proposed support"| component1_actions' in support
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
    assert 'event1 -. "proposed next step" .-> event2' in first_run["mermaid_source"]
    assert "event1 --> event2" not in first_run["mermaid_source"]
    exchanges = design_rows[1]
    assert "Proposed berth-occupancy<br/>state" in exchanges["mermaid_source"]
    assert exchanges["diagram_boxes"][1]["description"].startswith(
        "Proposed responsibility:"
    )
    assert {row["name"] for row in exchanges["components"]} == {
        "Vessel Intake",
        "Occupancy Record",
        "Placement View",
        "Placement Evidence",
    }


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
    assert 'event2 -. "proposed next step" .-> event3' in source
    assert 'event3 -. "proposed next step" .-> event1' in source
    assert 'event1 -. "proposed next step" .-> event2' not in source
    design["first_run"]["event_orders"] = [1, 2]
    with pytest.raises(ValueError, match="must include every source event exactly once"):
        _authored_diagrams(
            relations=relations, provisional_design=design,
            result_event_order=1, visible_result="the placement",
        )


def test_capability_support_keeps_source_events_and_proposed_ownership_distinct() -> None:
    rows = _authored_diagrams()
    support = next(
        row for row in rows if row["slug"] == "harbor-desk-capability-support"
    )
    boxes = {row["node_id"]: row for row in support["diagram_boxes"]}

    assert boxes["component1_actions"]["label"] == (
        "Source action 1 · human: Dock attendant Ivo\n"
        "Dock attendant Ivo enters a vessel tag"
    )
    assert boxes["component1_actions"]["role"] == "Supported source actions"
    assert boxes["component1"]["role"] == "Proposed component"
    assert 'component1 -->|"proposed support"| component1_actions' in support["mermaid_source"]
    assert "event1 --> component1" not in support["mermaid_source"]
    assert "owner" not in support["mermaid_source"]
    assert boxes["source_facts"]["label"] == "Source-stated facts"
    assert "Accepted" not in json.dumps(support)


@pytest.mark.parametrize("reverse_rows", [False, True])
def test_capability_support_local_groups_preserve_exact_many_to_many_references(
    reverse_rows: bool,
) -> None:
    relations = (
        _relation(1, "Dispatch coordinator", "submits the request; retains its receipt"),
        _relation(2, "Audit reviewer", "checks the receipt without approving payment"),
        _relation(3, "Berth map", "shows the receipt & its `review` status", actor_kind="product", owner="Berth map"),
    )
    if reverse_rows:
        relations = tuple(reversed(relations))
    design = _provisional_design()
    before = deepcopy((relations, design))
    support = _authored_diagrams(
        relations=relations, provisional_design=design,
        human_actors=("Dispatch coordinator", "Audit reviewer"),
    )[-1]
    boxes = {row["node_id"]: row for row in support["diagram_boxes"]}
    source = support["mermaid_source"]
    by_order = {row["order"]: row for row in relations}
    for index, component in enumerate(design["components"], 1):
        actions = "\n\n".join(
            f"Source action {order} · {by_order[order]['actor_kind']}: "
            f"{by_order[order]['actor_fact_quote']}\n{by_order[order]['event_quote']}"
            for order in component["supported_event_orders"]
        )
        assert boxes[f"component{index}_actions"]["label"] == actions
        assert "<br/><br/>".join(
            "<br/>".join(mermaid_label(line, width=44) for line in action.splitlines())
            for action in actions.split("\n\n")
        ) in source
        assert mermaid_label(component["responsibility"], width=44) in source
        assert mermaid_label(component["verification"], width=44) in source
        group = source.split(f"  subgraph component{index}_support[", 1)[1].split("  end", 1)[0]
        assert f'component{index} -->|"proposed support"| component{index}_actions' in group
        assert f'component{index} -. "proposed verification" .-> component{index}_verification' in group
        assert group.count("-->") == 1
        assert group.count(".->") == 1
    assert source.count("-->") == len(design["components"])
    assert source.count(".->") == len(design["components"])
    assert "source_path" not in source
    assert "Repeated action IDs refer to the same source action" in support["read_guide"]
    assert (relations, design) == before


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
        "action_target": 0,
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
    trap("action_target", greenfield_text, "normalize_action_target_language")

    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=_authored_intent(),
    )

    assert rc == 0, payload
    assert provider.calls == 1
    assert family_calls["terminal_deferral"] == 0
    assert family_calls["source_casing"] == 0
    assert family_calls["connector"] == 0
    assert family_calls["action_target"] == 0

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
