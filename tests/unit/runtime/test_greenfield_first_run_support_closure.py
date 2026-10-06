"""Required design support stays separate from the selected human walkthrough."""

from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_atlas_view import (
    validate_authored_atlas_view,
)
from tests.unit.runtime.test_greenfield_authored_atlas_view import (
    _authored_diagrams,
    _provisional_design,
    _relation,
)


def support_closure_case(*, exchange_support: bool, delivery_support: bool) -> tuple:
    design = _provisional_design(event_orders=tuple(range(1, 11)))
    design["first_run"]["event_orders"] = list(range(1, 8))
    scopes = [list(range(1, 8)), [8], [9], [10]]
    for component, workstream, scope in zip(
        design["components"], design["workstreams"], scopes, strict=True,
    ):
        component["supported_event_orders"] = scope
        component["verification_event_orders"] = scope
        workstream["verification_event_orders"] = scope
        workstream["depends_on"] = []
    if delivery_support:
        design["workstreams"][0]["depends_on"] = ["occupancy"]
        design["workstreams"][1]["depends_on"] = ["placement"]
    design["exchanges"] = [{
        "from_component": "vessel-intake", "to_component": "placement-evidence",
        "contract": "A downstream archive receives completed records.",
    }]
    if exchange_support:
        design["exchanges"].extend([
            {"from_component": "placement-view", "to_component": "occupancy-record",
             "contract": "Provide eligibility evidence."},
            {"from_component": "occupancy-record", "to_component": "vessel-intake",
             "contract": "Provide the current eligible state."},
            {"from_component": "vessel-intake", "to_component": "placement-view",
             "contract": "Acknowledge the eligibility version used."},
        ])
    relations = tuple(
        _relation(order, "Dock attendant Ivo", f"Dock attendant Ivo records action {order}.")
        if order <= 7 else
        _relation(order, "Berth map", f"The product maintains support state {order}.",
                  actor_kind="product", owner="Berth map")
        for order in range(1, 11)
    )
    return design, relations


@pytest.mark.parametrize("exchange_support,delivery_support", [(True, False), (False, True), (True, True)])
def test_first_run_retains_required_support_without_promoting_support_events(
    exchange_support: bool, delivery_support: bool,
) -> None:
    design, relations = support_closure_case(
        exchange_support=exchange_support, delivery_support=delivery_support,
    )
    original = deepcopy((design, relations))
    rows = _authored_diagrams(
        relations=relations, provisional_design=design, result_event_order=7,
    )
    assert (design, relations) == original
    sequence = rows[1]
    boxes = {box["node_id"]: box for box in sequence["diagram_boxes"]}
    source = sequence["mermaid_source"]
    assert [node for node in boxes if node.startswith("event")] == [
        f"event{order}" for order in range(1, 8)
    ]
    assert boxes["proposed_component1"]["role"] == "Proposed first-run stage"
    for index in (2, 3):
        assert boxes[f"proposed_component{index}"]["role"] == "Proposed supporting component"
        assert f'proposed_component{index}["Proposed supporting component<br/>' in source
    assert "proposed_component4" not in source
    assert "support state" not in source
    assert "downstream archive" not in source
    assert [line.strip() for line in source.splitlines() if line.strip().startswith("event") and " -.-> event" in line] == [
        f'event{order} -.-> event{order + 1}'
        for order in range(1, 7)
    ]
    for index in (1, 2, 3):
        assert boxes[f"proposed_component{index}"]["description"] == design["components"][index - 1]["responsibility"]
    first_run_detail = "\n".join(
        box["description"] + "\n" + "\n".join(row["text"] for row in box.get("details", []))
        for box in boxes.values()
    )
    assert "A downstream archive receives completed records." not in first_run_detail
    if exchange_support:
        for index, (origin, target, contract) in enumerate((
            (3, "Occupancy Record", "Provide eligibility evidence."),
            (2, "Vessel Intake", "Provide the current eligible state."),
            (1, "Placement View", "Acknowledge the eligibility version used."),
        ), 2):
            assert {"label": f"Proposed exchange {index} to {target}", "text": contract} in boxes[
                f"proposed_component{origin}"
            ]["details"]
        exchanges = rows[2]["mermaid_source"]
        assert 'component3 -->|"Proposed exchange: Provide eligibility' in exchanges
        assert 'component2 -->|"Proposed exchange: Provide the current' in exchanges
        assert 'component1 -->|"Proposed exchange: Acknowledge the' in exchanges
    if delivery_support:
        assert {"label": "Proposed delivery prerequisite", "text": "Placement View through Deliver the placement view."} in boxes[
            "proposed_component2"
        ]["details"]
        assert {"label": "Proposed delivery prerequisite", "text": "Occupancy Record through Deliver occupancy recording."} in boxes[
            "proposed_component1"
        ]["details"]
        delivery = rows[3]["mermaid_source"]
        assert 'workstream3 -->|"proposed prerequisite"| workstream2' in delivery
        assert 'workstream2 -->|"proposed prerequisite"| workstream1' in delivery
    assert "Proposed exchange:" not in source
    assert "proposed delivery prerequisite" not in source
    assert "Declared exchange inputs and delivery prerequisites" in sequence["read_guide"]
    assert validate_authored_atlas_view(sequence, source_text=source)["diagram_boxes"] == sequence["diagram_boxes"]
