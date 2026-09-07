"""No-network proposal and artifact contracts for the required design carrier."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_authored_component_spec as registry
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    authored_projection_parity_issues,
    build_authored_greenfield_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import AUTHORED_SEMANTICS_KEY
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_component_alignment_issues,
    semantic_workstream_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_provisional_package import (
    build_provisional_backlog,
    build_provisional_components,
)
from odylith.runtime.domain_intelligence.project_intelligence_binding import (
    attach_project_intelligence_bindings,
    project_intelligence_binding_issues,
)
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance.validate_backlog_contract import default_section_boilerplate
from tests.unit.runtime.test_greenfield_authored_component_spec_projection import _authored_proposal


def _allocated(proposal: dict) -> dict:
    return {"created": [
        {"idea_id": f"B-{index:03d}", "title": row["title"]}
        for index, row in enumerate(proposal["backlog"], start=1)
    ]}


@pytest.mark.parametrize("surface", ["backlog", "components", "diagrams"])
def test_artifact_bindings_preserve_explicit_source_and_design_authority(tmp_path: Path, surface: str) -> None:
    proposal = attach_project_intelligence_bindings(_authored_proposal(tmp_path))
    assert project_intelligence_binding_issues(proposal) == []
    rows = proposal[surface]
    for row in rows:
        assert row["project_intelligence_binding"]["authority_kind"] == row["authority_kind"]
    if surface == "diagrams":
        assert [row["authority_kind"] for row in rows] == [
            "source_grounded", "provisional_design", "provisional_design", "provisional_design", "provisional_design",
        ]
    else:
        assert all(row["authority_kind"] == "provisional_design" for row in rows)
    rows[-1]["project_intelligence_binding"]["authority_kind"] = "source_grounded"
    assert any("authority_kind" in issue for issue in project_intelligence_binding_issues(proposal))


@pytest.mark.parametrize("invalid", [None, "source_grounded", [], {}])
def test_proposed_component_cannot_lose_or_promote_design_authority(tmp_path: Path, invalid: object) -> None:
    proposal = attach_project_intelligence_bindings(_authored_proposal(tmp_path))
    proposal["components"][0]["authority_kind"] = invalid
    assert any("source/design authority" in issue for issue in project_intelligence_binding_issues(proposal))
    with pytest.raises(ValueError, match="source/design authority"):
        attach_project_intelligence_bindings(proposal)


def test_fresh_proposal_uses_one_design_without_promoting_support_to_ownership(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    intent = proposal["intent"]
    semantics = intent[AUTHORED_SEMANTICS_KEY]
    design = semantics["provisional_design"]
    events = {event["order"]: event for event in semantics["first_path_relations"]}
    assert len(proposal["components"]) == len(design["components"]) == 4
    assert len(proposal["backlog"]) == len(design["workstreams"]) == 4
    assert len(proposal["diagrams"]) == 5
    assert proposal["semantic_model"]["provisional_design"] == design
    for row, authored in zip(proposal["components"], design["components"], strict=True):
        assert row["component_id"] == authored["key"]
        assert row["authority_kind"] == "provisional_design"
        contract = row["component_contract"]
        assert contract["provisional_component"] == authored
        assert "owner_bound_events" not in contract
        assert "responsibility_facts" not in contract
        assert contract["supporting_events"] == [events[order] for order in authored["supported_event_orders"]]
    assert events[1]["actor_kind"] == "human"
    assert events[1]["actor_fact_quote"] == "Planner"
    assert authored_projection_parity_issues(proposal) == []
    assert semantic_component_alignment_issues(proposal, proposal["semantic_model"]) == []
    assert semantic_workstream_alignment_issues(proposal, proposal["semantic_model"]) == []


def test_every_delivery_keeps_canonical_decisions_and_distinct_proposed_acceptance(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    intent = proposal["intent"]
    design = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]
    for row, authored in zip(proposal["backlog"], design["workstreams"], strict=True):
        for field in ("problem", "customer", "opportunity", "product_view"):
            assert row[field] == f"Source fact — {intent[field]}"
            assert row["provisional_workstream_contract"]["decision_refs"][field] == f"/{field}"
        assert row["deliverable"] == authored["deliverable"]
        assert row["recommended_first_slice"] == f"Proposed deliverable — {authored['deliverable']}"
        assert row["validation"] == [f"Proposed acceptance — {authored['verification']}"]
        assert row["success_metrics"] == row["validation"]
        assert row["provisional_workstream_contract"]["provisional_workstream"] == authored
        assert "actor's ownership" in row["radar_sections"]["Design Authority"]
    assert len({row["deliverable"] for row in proposal["backlog"]}) == 4


def test_exchange_direction_does_not_invent_component_dependencies(tmp_path: Path) -> None:
    intent = deepcopy(_authored_proposal(tmp_path)["intent"])
    design = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]
    client, service = (row["key"] for row in design["components"][:2])
    design["exchanges"] = [
        {"from_component": client, "to_component": service, "contract": "Client invokes Service."},
        {"from_component": service, "to_component": client, "contract": "Service returns a response."},
    ]
    rows = build_provisional_components(intent=intent, product_slug="harbor-planner")

    assert all(row["dependencies"] == [] for row in rows)
    for row in rows[:2]:
        assert row["component_contract"]["exchanges"] == design["exchanges"]
        assert len(row["interfaces"]) == 2
        assert registry._provisional_component_contract(row) == row["component_contract"]
    assert design["workstreams"][1]["depends_on"]


@pytest.mark.parametrize("field", ["problem", "customer", "opportunity", "product_view"])
def test_decision_assumptions_remain_visible_on_every_radar_row(tmp_path: Path, field: str) -> None:
    intent = deepcopy(_authored_proposal(tmp_path)["intent"])
    intent[field] = ""
    statement = f"The {field} remains a provisional decision, not source truth."
    intent["assumptions"] = [{"applies_to": field, "statement": statement}]
    rows = build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})
    for row in rows:
        assert row[field] == f"Assumption — {statement}"
        assert statement in row["radar_sections"]["Assumptions"]
        assert row["provisional_workstream_contract"]["decision_refs"][field] == "/assumptions/0"
    intent["assumptions"] = []
    with pytest.raises(ValueError, match="requires one fact or one assumption"):
        build_provisional_backlog(intent=intent, diagram_slugs={})


@pytest.mark.parametrize("surface", ["components", "backlog", "semantic_model", "diagrams"])
def test_complete_projection_parity_rejects_design_view_drift(tmp_path: Path, surface: str) -> None:
    proposal = _authored_proposal(tmp_path)
    if surface == "components":
        proposal[surface][0]["responsibility"] = "Unbound replacement responsibility"
    elif surface == "backlog":
        proposal[surface][0]["deliverable"] = "Unbound replacement deliverable"
    elif surface == "semantic_model":
        proposal[surface]["provisional_design"]["exchanges"] = []
    else:
        proposal[surface][0]["summary"] = "Unbound replacement view"
    assert any(f"`{surface}`" in issue for issue in authored_projection_parity_issues(proposal))
    with pytest.raises(ValueError, match="projection drifted"):
        registry.build_authored_component_authoring_inputs(
            root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_allocated(proposal),
        )


def test_registry_compiler_renders_proposed_contract_and_exact_source_performer(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    inputs = registry.build_authored_component_authoring_inputs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_allocated(proposal),
    )
    assert len(inputs) == 4
    for row in inputs:
        spec = registry.build_authored_component_spec(row)
        entry = registry.build_authored_component_registry_entry(row)
        assert "## Proposed responsibility" in spec
        assert "## Proposed inputs and outputs" in spec
        assert "## Proposed verification" in spec
        assert "## Source-event support" in spec
        assert "Source-custodied responsibility" not in spec
        assert "proposed logical component" in entry["what_it_is"]
        assert row["component_contract"]["provisional_component"]["verification"] in spec
        for event in row["component_contract"]["supporting_events"]:
            assert event["event_quote"] in spec
            assert f"Event {event['order']} — {event['actor_fact_quote']}" in spec
    assert "Event 1 — Planner" in registry.build_authored_component_spec(inputs[0])


def test_rebuilding_changed_design_does_not_bypass_original_seal(tmp_path: Path) -> None:
    original = _authored_proposal(tmp_path)
    intent = deepcopy(original["intent"])
    intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]["components"][0]["responsibility"] = "A new proposed responsibility."
    changed = build_authored_greenfield_proposal(
        observed_source=original["observed_source"], release_selector="0.0.1", confirmed_intent=intent,
    )
    changed[PRODUCT_INTENT_AUTHORITY_KEY] = original[PRODUCT_INTENT_AUTHORITY_KEY]
    assert authored_projection_parity_issues(changed) == []
    with pytest.raises(ValueError, match="do not match sealed"):
        registry.build_authored_component_authoring_inputs(
            root=tmp_path, proposal=changed, release_selector="0.0.1", backlog_result=_allocated(changed),
        )


def test_radar_compiler_keeps_source_decisions_and_proposed_sections_without_reparse(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    args = greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1")
    for row in proposal["backlog"]:
        row_args = backlog_authoring._title_specific_args(title=row["title"], args=args)
        sections = backlog_authoring._grounded_sections_for_title(
            title=row["title"], args=row_args, source_custody=args.source_custody,
        )
        assert sections["Problem"] == row["problem"]
        assert sections["Customer"] == row["customer"]
        assert sections["Opportunity"] == row["opportunity"]
        assert sections["Product View"] == row["product_view"]
        assert sections["Proposed Solution"] == row["recommended_first_slice"]
        assert sections["Design Authority"] == row["radar_sections"]["Design Authority"]
        assert row["validation"][0] in sections["Validation"]
        for section, boilerplate in default_section_boilerplate(row["title"]).items():
            assert sections[section] != boilerplate, section


def test_projectors_are_deep_copies_and_missing_design_has_no_source_only_fallback(tmp_path: Path) -> None:
    intent = _authored_proposal(tmp_path)["intent"]
    original = deepcopy(intent)
    rows = build_provisional_components(intent=intent, product_slug="harbor-planner")
    rows[0]["component_contract"]["supporting_events"][0]["actor_fact_quote"] = "Impersonated actor"
    assert intent == original
    intent[AUTHORED_SEMANTICS_KEY].pop("provisional_design")
    with pytest.raises(ValueError):
        build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)


def test_semantic_alignment_rejects_source_actor_reassignment_even_with_matching_views(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    contract = proposal["components"][0]["component_contract"]
    contract["supporting_events"][0]["actor_fact_quote"] = "Proposed component"
    proposal["semantic_model"]["components"][0]["component_contract"] = deepcopy(contract)
    assert any("canonical provisional design" in issue for issue in semantic_component_alignment_issues(
        proposal, proposal["semantic_model"],
    ))
