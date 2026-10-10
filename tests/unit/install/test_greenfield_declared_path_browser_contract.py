"""Keep release browser evidence tied to the declared path on fresh packages."""

from copy import deepcopy

import pytest

from tests.unit.install.test_greenfield_browser_surface_proof import (
    _authored_contract_module,
    _source_design_structure,
    _with_event_evidence,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import structural_design_fixture


def _fresh_structure() -> tuple[dict, dict]:
    rendered, facts = _source_design_structure()
    facts["authored_semantics_version"] = "odylith.greenfield.authored-semantics.v19"
    facts["source_event_relations"] = deepcopy(facts["first_path_relations"]) + [{
        "order": 3, "event_quote": "Relay publishes the approved status",
        "actor_kind": "product", "actor_fact_quote": "Relay", "visible_result_quote": "",
    }]
    facts["provisional_design"] = structural_design_fixture(
        (1, 2, 3), first_run_event_orders=(1, 3, 2),
    )
    rendered.update(first_path_authority="source_grounded", first_path_label="")
    return rendered, facts


def test_fresh_browser_contract_uses_declared_path_and_keeps_proposed_closure() -> None:
    rendered, facts = _fresh_structure()
    assert [row["order"] for row in facts["first_path_relations"]] == [1, 2]
    assert facts["provisional_design"]["first_run"]["event_orders"] == [1, 3, 2]
    assert _authored_contract_module().authored_structure_issues(rendered, facts) == ()


def test_browser_contract_refuses_proposed_walkthrough_under_first_path() -> None:
    rendered, facts = _fresh_structure()
    by_order = {row["order"]: row for row in facts["source_event_relations"]}
    rendered["first_path"] = [
        {"order": order, "text": by_order[order]["event_quote"]} for order in (1, 3, 2)
    ]
    _with_event_evidence(rendered, {**facts, "first_path_relations": facts["source_event_relations"]})
    rendered.update(first_path_authority="provisional_design", first_path_label="Proposed first run:")
    assert _authored_contract_module().authored_structure_issues(rendered, facts)


@pytest.mark.parametrize("mutation", ["missing", "empty", "duplicate", "unknown", "changed", "boolean"])
def test_browser_contract_refuses_malformed_declared_relations(mutation: str) -> None:
    rendered, facts = _fresh_structure()
    if mutation == "missing":
        facts.pop("first_path_relations")
    elif mutation == "empty":
        facts["first_path_relations"] = []
    elif mutation == "duplicate":
        facts["first_path_relations"].append(deepcopy(facts["first_path_relations"][0]))
    elif mutation == "unknown":
        facts["first_path_relations"][0]["order"] = 99
    elif mutation == "changed":
        facts["first_path_relations"][0]["actor_fact_quote"] = "Another actor"
    else:
        facts["first_path_relations"][0]["order"] = True
    assert _authored_contract_module().authored_structure_issues(rendered, facts)


@pytest.mark.parametrize("field,value", [
    ("first_path_authority", "provisional_design"), ("first_path_label", "Proposed first run:"),
])
def test_browser_contract_refuses_changed_declared_path_authority(field: str, value: str) -> None:
    rendered, facts = _fresh_structure()
    rendered[field] = value
    assert _authored_contract_module().authored_structure_issues(rendered, facts)


def test_historical_browser_contract_retains_its_proposed_path() -> None:
    rendered, facts = _source_design_structure()
    assert _authored_contract_module().authored_structure_issues(rendered, facts) == ()
