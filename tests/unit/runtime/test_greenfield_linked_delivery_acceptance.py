"""Component views retain canonical delivery acceptance without inventing proof."""

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_authored_component_spec as registry
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import authored_projection_parity_issues
from odylith.runtime.domain_intelligence.greenfield_provisional_package import build_provisional_components
from tests.unit.runtime.test_greenfield_authored_atlas_view import _authored_diagrams, _provisional_design
from tests.unit.runtime.test_greenfield_provisional_package import _allocated, _authored_proposal
from tests.unit.runtime import test_greenfield_authored_component_spec_projection as fixtures
from odylith.runtime.domain_intelligence.greenfield_provisional_package import provisional_delivery_acceptance_text


@pytest.mark.parametrize("reverse", [False, True])
def test_components_retain_all_and_only_linked_acceptance_in_canonical_order(tmp_path: Path, reverse: bool) -> None:
    intent = deepcopy(_authored_proposal(tmp_path)["intent"])
    design = intent["authored_semantics"]["provisional_design"]
    first, second = [component["key"] for component in design["components"][:2]]
    design["workstreams"][0]["component_keys"] = [first, second]
    design["workstreams"][1]["component_keys"] = [first, second]
    if reverse:
        design["workstreams"].reverse()
    original = deepcopy(intent)
    rows = build_provisional_components(intent=intent, product_slug="harbor-planner")
    for row in rows:
        expected = [
            {"design_ref": f"/authored_semantics/provisional_design/workstreams/{index}",
             "provisional_workstream": workstream}
            for index, workstream in enumerate(design["workstreams"])
            if row["component_id"] in workstream["component_keys"]
        ]
        assert row["component_contract"]["delivery_workstreams"] == expected
        registry._provisional_component_contract(row)
        assert row["validation"][0] == row["component_contract"]["provisional_component"]["verification"]
        assert len(row["validation"]) == len(expected) + 1
    assert len(rows[0]["component_contract"]["delivery_workstreams"]) == 2
    rows[0]["component_contract"]["delivery_workstreams"][0]["provisional_workstream"]["verification"] = "changed"
    assert intent == original


def test_registry_distinguishes_boundary_check_from_exact_delivery_acceptance(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    rows = registry.build_authored_component_authoring_inputs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_allocated(proposal),
    )
    for row in rows:
        spec = registry.build_authored_component_spec(row)
        assert "### Boundary check" in spec
        assert "### Linked delivery acceptance" in spec
        assert "not passed checks or exhaustive component tests" in spec
        for delivery in row["component_contract"]["delivery_workstreams"]:
            assert delivery["provisional_workstream"]["verification"] in spec
            assert f"{delivery['design_ref']}/verification" in spec
            for key in delivery["provisional_workstream"]["component_keys"]:
                assert f"`{key}`" in spec


@pytest.mark.parametrize("mutation", ["omit", "text", "reference", "unrelated", "duplicate"])
def test_changed_delivery_projection_is_rejected_before_registry_issuance(tmp_path: Path, mutation: str) -> None:
    proposal = _authored_proposal(tmp_path)
    deliveries = proposal["components"][0]["component_contract"]["delivery_workstreams"]
    if mutation == "omit":
        deliveries.clear()
    elif mutation == "text":
        deliveries[0]["provisional_workstream"]["verification"] = "Weaker unrelated acceptance."
    elif mutation == "reference":
        deliveries[0]["design_ref"] = "/unbound/acceptance"
    elif mutation == "unrelated":
        deliveries[0]["provisional_workstream"]["component_keys"] = ["unrelated"]
    else:
        deliveries.append(deepcopy(deliveries[0]))
    assert authored_projection_parity_issues(proposal)
    with pytest.raises(ValueError, match="projection drifted"):
        registry.build_authored_component_authoring_inputs(
            root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_allocated(proposal),
        )


def test_atlas_many_to_many_acceptance_has_one_node_per_workstream() -> None:
    design = _provisional_design()
    first, second = [component["key"] for component in design["components"][:2]]
    design["workstreams"][0]["component_keys"] = [first, second]
    design["workstreams"][1]["component_keys"] = [first, second]
    diagrams = _authored_diagrams(provisional_design=design)
    view = next(row for row in diagrams if row["slug"].endswith("capability-support"))
    source = view["mermaid_source"]
    boxes = {box["node_id"]: box for box in view["diagram_boxes"]}
    for index, workstream in enumerate(design["workstreams"], 1):
        node = f"workstream{index}_acceptance"
        assert source.count(f'{node}["') == 1
        assert workstream["verification"] in boxes[node]["label"]
        for component_index, component in enumerate(design["components"], 1):
            edge = f'component{component_index} -. "participates in delivery" .-> {node}'
            assert (edge in source) == (component["key"] in workstream["component_keys"])
    assert "neither check is passed or exhaustive proof" in view["read_guide"]


@pytest.fixture
def shared_component(tmp_path, monkeypatch):
    original = fixtures.authored_response

    def response(*args, **kwargs):
        value = original(*args, **kwargs)
        design = value["result"]["provisional_design"]
        design["workstreams"][1]["component_keys"].append(design["components"][0]["key"])
        return value

    monkeypatch.setattr(fixtures, "authored_response", response)
    proposal = _authored_proposal(tmp_path)
    return registry.build_authored_component_authoring_inputs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_allocated(proposal),
    )[0]


def _refresh_validation(row):
    contract = row["component_contract"]
    row["validation"] = [contract["provisional_component"]["verification"], *[
        provisional_delivery_acceptance_text(delivery["provisional_workstream"])
        for delivery in contract["delivery_workstreams"]
    ]]


def test_standalone_render_uses_identity_not_delivery_position(shared_component):
    row = shared_component
    row["component_contract"]["delivery_workstreams"].reverse()
    _refresh_validation(row)
    spec = registry.build_authored_component_spec(row)
    for delivery in row["component_contract"]["delivery_workstreams"]:
        expected_id = row["delivery_workstream_links"][delivery["design_ref"]]["workstream_id"]
        assert f"- Workstream: `{expected_id}` — {delivery['provisional_workstream']['title']}" in spec
    assert "Shared acceptance across" in spec


def test_disjoint_deliveries_cannot_share_an_allocated_radar_id(tmp_path):
    proposal = _authored_proposal(tmp_path)
    allocated = _allocated(proposal)
    allocated["created"][1]["idea_id"] = allocated["created"][0]["idea_id"]
    with pytest.raises(ValueError, match="duplicate allocated workstream ID"):
        registry.build_authored_component_authoring_inputs(
            root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=allocated,
        )


@pytest.mark.parametrize("mutation", ["omit", "extra_id", "wrong_key", "duplicate_id", "empty_ref", "unrelated_ref", "duplicate_ref"])
def test_standalone_registry_rejects_broken_acceptance_allocation(shared_component, mutation):
    row = shared_component
    deliveries = row["component_contract"]["delivery_workstreams"]
    links = row["delivery_workstream_links"]
    if mutation == "omit":
        deliveries.pop()
    elif mutation == "extra_id":
        row["workstreams"] += ("B-999",)
    elif mutation == "wrong_key":
        links[deliveries[0]["design_ref"]]["workstream_key"] = "unrelated"
    elif mutation == "duplicate_id":
        links[deliveries[1]["design_ref"]]["workstream_id"] = row["workstreams"][0]
    else:
        deliveries[0]["design_ref"] = {
            "empty_ref": "", "unrelated_ref": "/authored_semantics/provisional_design/components/0",
            "duplicate_ref": deliveries[1]["design_ref"],
        }[mutation]
    _refresh_validation(row)
    for build in (registry.build_authored_component_registry_entry, registry.build_authored_component_spec):
        with pytest.raises(ValueError, match="delivery"):
            build(row)
