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
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_SEMANTICS_KEY, authored_semantics_mapping,
)
from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import (
    render_candidate_intent_markdown,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_semantic_alignment import (
    semantic_component_alignment_issues,
    semantic_workstream_alignment_issues,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_provisional_package import (
    build_provisional_backlog,
    build_provisional_components,
)
from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import (
    _sha256 as _lifecycle_sha256,
    _project_verified_source_lifecycle,
    project_greenfield_source_lifecycle,
)
from odylith.runtime.domain_intelligence.project_intelligence_binding import (
    attach_project_intelligence_bindings,
    project_intelligence_binding_issues,
)
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance.validate_backlog_contract import default_section_boilerplate
from tests.unit.runtime.test_greenfield_authored_component_spec_projection import _authored_proposal
from tests.unit.runtime.test_greenfield_source_lifecycle import _case as _source_duty_case
from tests.unit.runtime.test_greenfield_source_duty_binding import _with_design_duties
from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt_for_ledger


def _attach_lifecycle_duties(intent: dict, *, evidence: str, receipt: dict, binding: dict) -> dict:
    """Combine declared lifecycle atoms with the intent's unchanged action atoms."""
    semantics = intent[AUTHORED_SEMANTICS_KEY]
    prior = semantics["source_duty"]
    ledger = deepcopy(prior["ledger_receipt"]["ledger"])
    combined_binding = deepcopy(prior["binding"])
    for section in ("state_fields", "off_path_transitions", "conditional_guards", "boundaries", "proof_duties"):
        assert not ledger[section]
        ledger[section] = deepcopy(receipt["ledger"][section])
        if section != "state_fields":
            combined_binding[section] = deepcopy(binding[section])
    source = intent["prompt"] + "\n" + evidence
    verified = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    combined_binding.update(source_sha256=verified["source_sha256"], ledger_sha256=verified["ledger_sha256"])
    lifecycle = _project_verified_source_lifecycle(
        receipt=verified, binding=combined_binding, evidence_text=source,
    )
    responsibilities = [
        {**row, "decision_set_sha256": verified["decision_set_sha256"]}
        for row in semantics["component_responsibility_relations"]
    ]
    intent["prompt"] = source
    intent[AUTHORED_SEMANTICS_KEY] = authored_semantics_mapping(
        semantics["source_event_relations"], responsibilities,
        first_path_context_relations=semantics["first_path_context_relations"],
        source_precedence=semantics["source_precedence"],
        provisional_design=semantics["provisional_design"],
        source_duty={"ledger_receipt": verified, "binding": combined_binding, "lifecycle": lifecycle},
    )
    return lifecycle


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
    events = {event["order"]: event for event in semantics["source_event_relations"]}
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


def test_every_delivery_has_local_scope_and_keeps_canonical_decision_refs(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    intent = deepcopy(proposal["intent"])
    original_intent = deepcopy(intent)
    rows = build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})
    assert intent == original_intent
    design = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]
    components = {row["key"]: row for row in design["components"]}
    workstreams = {row["key"]: row for row in design["workstreams"]}
    events = {
        row["order"]: row
        for row in intent[AUTHORED_SEMANTICS_KEY]["source_event_relations"]
    }
    for row, authored in zip(rows, design["workstreams"], strict=True):
        for field in ("problem", "customer", "opportunity"):
            assert row["provisional_workstream_contract"]["decision_refs"][field] == f"/{field}"
        assert row["provisional_workstream_contract"]["decision_refs"]["product_view"] == "/product_view"
        event_orders = sorted({
            order
            for key in authored["component_keys"]
            for order in components[key]["supported_event_orders"]
        })
        assigned_events = [events[order] for order in event_orders]
        assert row["problem"] == authored["problem"]
        assert "Unimplemented assigned source-event support" not in row["problem"]
        assert all(f"Event {order}" not in row["problem"] for order in event_orders)
        assert row["customer"] == intent["customer"]
        assert all(
            event["actor_fact_quote"] not in row["customer"]
            for event in assigned_events
            if event["actor_kind"] != "human"
        )
        assert row["opportunity"] == "\n".join(
            f"- {components[key]['name']} — {components[key]['responsibility']}"
            for key in authored["component_keys"]
        )
        assert row["product_view"] == authored["deliverable"]
        assert row["deliverable"] == authored["deliverable"]
        assert row["recommended_first_slice"] == authored["deliverable"]
        assert row["validation"] == [authored["verification"]]
        assert row["success_metrics"] == row["validation"]
        contract = row["provisional_workstream_contract"]
        assert contract["support_event_refs"] == [
            f"/authored_semantics/source_event_relations/{order - 1}"
            for order in event_orders
        ]
        assert contract["supporting_events"] == assigned_events
        assert row["radar_sections"]["Source Event Support"] == "\n".join(
            f"- Event {event['order']}\nActor: {event['actor_fact_quote']}\n"
            f"Source event: {event['event_quote']}"
            for event in assigned_events
        )
        local_rendering = "\n".join([
            row["problem"], row["customer"], row["opportunity"], row["product_view"],
            *row["radar_sections"].values(),
        ])
        for sibling_order in set(events) - set(event_orders):
            assert events[sibling_order]["event_quote"] not in local_rendering
        for project_fact in (
            intent["problem"], intent["opportunity"], intent["product_view"],
            *intent["non_goals"], *intent["operational_constraints"],
            *intent["success_metrics"], intent["proof_boundary"],
        ):
            assert project_fact not in local_rendering
        assert not {
            "Proposed Solution", "Scope", "Non-Goals", "Validation", "Why Now",
            "Migration/Compatibility", "Open Questions", "Operational Constraints",
            "Source Success Metrics", "Source Proof Boundary", "Design Authority",
        }.intersection(row["radar_sections"])
        assert "`/" not in local_rendering
        dependencies = [workstreams[key]["title"] for key in authored["depends_on"]]
        if dependencies:
            expected_rollout = f"Proposed delivery sequence — Start after {', '.join(dependencies)}."
            assert row["radar_sections"]["Dependencies"] == "\n".join(f"- {title}" for title in dependencies)
            assert row["radar_sections"]["Rollout"] == expected_rollout
        else:
            assert "Dependencies" not in row["radar_sections"]
            assert "Rollout" not in row["radar_sections"]
        expected_checks = "\n".join(
            f"- Proposed component check — {components[key]['name']}: "
            f"{components[key]['verification']}"
            for key in authored["component_keys"]
            if components[key]["verification"] != authored["verification"]
        )
        if expected_checks:
            assert row["radar_sections"]["Test Strategy"] == expected_checks
        else:
            assert "Test Strategy" not in row["radar_sections"]
        assert row["provisional_workstream_contract"]["provisional_workstream"] == authored
    assert len({row["deliverable"] for row in rows}) == 4
    assert len({row["problem"] for row in rows}) == 4
    assert len({row["opportunity"] for row in rows}) == 4
    assert len({row["product_view"] for row in rows}) == 4
    assert len({tuple(row["validation"]) for row in rows}) == 4


def test_ordering_rationale_explains_only_typed_delivery_dependencies(tmp_path: Path) -> None:
    intent = deepcopy(_authored_proposal(tmp_path)["intent"])
    workstreams = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]["workstreams"]
    first, second, third, independent = workstreams
    first["depends_on"] = []
    second["depends_on"] = [first["key"]]
    third["depends_on"] = [first["key"], second["key"]]
    independent["depends_on"] = []
    original = deepcopy(intent)

    rows = build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})

    assert intent == original
    assert [row["ordering_decision"]["ranking_basis"] for row in rows] == [
        f"Proposed dependency order — No prerequisites. Enables {second['title']}, {third['title']}.",
        f"Proposed dependency order — Requires {first['title']} first. Enables {third['title']}.",
        f"Proposed dependency order — Requires {first['title']}, {second['title']} first. "
        "No other proposed workstream depends on this delivery.",
        "Proposed dependency order — No prerequisites. "
        "No other proposed workstream depends on this delivery.",
    ]
    for row in rows:
        decision = row["ordering_decision"]
        assert decision["ranking_basis"] != decision["expected_outcome"]
        assert row["deliverable"] not in decision["ranking_basis"]


def test_provisional_metadata_carries_no_unsupplied_value_effort_or_urgency_judgments(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    before = deepcopy(proposal["intent"])
    args = greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1")
    for row in proposal["backlog"]:
        assert row["assessment_status"] == "unassessed"
        assert row["assessment_provenance"] == "greenfield_provisional_design"
        assert row["ordering_decision"]["priority"] == "unassessed"
        override = args.section_overrides_by_title[row["title"]]
        for field in ("priority", "sizing", "complexity", "confidence"):
            assert row[field] == override[field] == getattr(args, field) == "unassessed"
        for field in ("commercial_value", "product_impact", "market_value", "ordering_score"):
            assert row[field] is override[field] is getattr(args, field) is None
        for field in ("assessment_status", "assessment_provenance"):
            assert row[field] == override[field] == getattr(args, field)
    assert proposal["intent"] == before


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
        assert registry._provisional_component_contract(row, semantics_version=intent[AUTHORED_SEMANTICS_KEY]["version"]) == row["component_contract"]
    assert design["workstreams"][1]["depends_on"]


@pytest.mark.parametrize("field", ["problem", "customer", "opportunity", "product_view"])
def test_decision_assumptions_remain_referenced_without_prose_fanout(tmp_path: Path, field: str) -> None:
    intent = deepcopy(_authored_proposal(tmp_path)["intent"])
    intent[field] = ""
    statement = f"The {field} remains a provisional decision, not source truth."
    intent["assumptions"] = [{"applies_to": field, "statement": statement}]
    rows = build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})
    for row in rows:
        rendered = "\n".join([
            row["problem"], row["customer"], row["opportunity"], row["product_view"],
            *row["radar_sections"].values(),
        ])
        assert (statement in rendered) is (field == "customer")
        if field == "customer":
            assert row["customer"] == f"Assumption — {statement}"
        assert "Assumptions" not in row["radar_sections"]
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
        assert entry["what_it_is"] == row["responsibility"]
        assert entry["status"] == row["status"] == "planned"
        assert row["component_contract"]["authority_kind"] == "provisional_design"
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
        assert "Proposed Solution" not in sections
        assert "Validation" not in sections
        assert "Why Now" not in sections
        assert sections["Source Event Support"] == row["radar_sections"]["Source Event Support"]
        for optional in ("Rollout", "Test Strategy", "Source Lifecycle", "Source Proof Duties"):
            assert sections.get(optional) == row["radar_sections"].get(optional)
        for section, boilerplate in default_section_boilerplate(row["title"]).items():
            assert sections.get(section) != boilerplate, section


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


def test_off_path_lifecycle_is_projected_only_to_bound_component_and_workstream(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    intent = deepcopy(proposal["intent"])
    design = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]
    component_key = design["components"][0]["key"]
    workstream_key = next(
        row["key"] for row in design["workstreams"] if component_key in row["component_keys"]
    )
    evidence, receipt, candidate, binding = _source_duty_case("dossier")
    candidate["provisional_design"]["components"][0]["key"] = component_key
    candidate["provisional_design"]["workstreams"][0].update({
        "key": workstream_key, "component_keys": [component_key],
    })
    binding["off_path_transitions"][0].update({
        "component_key": component_key, "workstream_key": workstream_key,
    })
    lifecycle = _attach_lifecycle_duties(intent, evidence=evidence, receipt=receipt, binding=binding)
    transition = lifecycle["off_path_transitions"][0]
    original_intent = deepcopy(intent)

    components = build_provisional_components(intent=intent, product_slug="harbor-planner")
    backlog = build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})

    assert intent == original_intent
    assert [row["component_id"] for row in components if row["component_contract"]["source_lifecycle_transitions"]] == [component_key]
    assert [row["provisional_workstream_contract"]["provisional_workstream"]["key"] for row in backlog
            if row["provisional_workstream_contract"]["source_lifecycle_transitions"]] == [workstream_key]
    owner = next(row for row in components if row["component_id"] == component_key)
    delivery = next(row for row in backlog if row["provisional_workstream_contract"]["provisional_workstream"]["key"] == workstream_key)
    assert owner["component_contract"]["source_lifecycle_transitions"] == [transition]
    assert delivery["provisional_workstream_contract"]["source_lifecycle_transitions"] == [transition]
    assert "Withdrawal closes dossier access and erases the cached copy" in delivery["radar_sections"]["Source Lifecycle"]
    assert "Source citation (occurrence 1)" in delivery["radar_sections"]["Source Lifecycle"]
    assert delivery["radar_sections"]["Source Lifecycle"].index("access: closed") < delivery["radar_sections"]["Source Lifecycle"].index("cache: erased")
    assert all("Source Lifecycle" not in row["radar_sections"] for row in backlog if row is not delivery)
    assert [row["component_contract"]["supporting_events"] for row in components] == [
        row["component_contract"]["supporting_events"] for row in proposal["components"]
    ]
    assert [row["provisional_workstream_contract"]["supporting_events"] for row in backlog] == [
        row["provisional_workstream_contract"]["supporting_events"] for row in proposal["backlog"]
    ]
    assert all("withdrawal" not in row["radar_sections"]["Source Event Support"].lower() for row in backlog)

    inputs = registry.build_authored_component_authoring_inputs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1", backlog_result=_allocated(proposal),
    )
    for row in inputs:
        row["component_contract"]["source_lifecycle_transitions"] = (
            [deepcopy(transition)] if row["component_id"] == component_key else []
        )
        spec = registry.build_authored_component_spec(row)
        assert ("## Source state lifecycle" in spec) is (row["component_id"] == component_key)
        if row["component_id"] == component_key:
            assert "Withdrawal closes dossier access and erases the cached copy" in spec
            assert "Source citation (occurrence 1)" in spec
            assert spec.index("access: closed") < spec.index("cache: erased")
            assert "performer" not in spec.lower()

    wrong_owner = next(row for row in inputs if row["component_id"] != component_key)
    wrong_owner["component_contract"]["source_lifecycle_transitions"] = [deepcopy(transition)]
    with pytest.raises(ValueError, match="unrelated source lifecycle"):
        registry.build_authored_component_spec(wrong_owner)

    intent[AUTHORED_SEMANTICS_KEY]["source_duty"]["lifecycle"]["off_path_transitions"][0]["workstream_key"] = "missing-delivery"
    with pytest.raises(ValueError, match="owner is absent"):
        build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})


def test_guard_boundary_and_proof_duty_survive_canonical_package_projection(tmp_path: Path) -> None:
    proposal = _authored_proposal(tmp_path)
    intent = deepcopy(proposal["intent"])
    design = intent[AUTHORED_SEMANTICS_KEY]["provisional_design"]
    component_key = design["components"][0]["key"]
    workstream_key = next(
        row["key"] for row in design["workstreams"] if component_key in row["component_keys"]
    )
    evidence, receipt, candidate, binding = _source_duty_case("dossier")
    evidence, receipt, binding = _with_design_duties(evidence, receipt, binding)
    candidate["provisional_design"]["components"][0]["key"] = component_key
    candidate["provisional_design"]["workstreams"][0].update({
        "key": workstream_key, "component_keys": [component_key],
    })
    binding["off_path_transitions"][0].update({
        "component_key": component_key, "workstream_key": workstream_key,
    })
    for role in ("conditional_guards", "boundaries", "proof_duties"):
        binding[role][0].update({
            "component_key": component_key, "workstream_key": workstream_key,
        })
    lifecycle = _attach_lifecycle_duties(intent, evidence=evidence, receipt=receipt, binding=binding)
    preview = render_candidate_intent_markdown(intent)
    for heading in ("Source conditional guards", "Source boundaries", "Source proof duties"):
        assert f"## {heading}" in preview
    components = build_provisional_components(intent=intent, product_slug="harbor-planner")
    backlog = build_provisional_backlog(intent=intent, diagram_slugs={"context": "context"})
    owner = next(row for row in components if row["component_id"] == component_key)
    delivery = next(
        row for row in backlog
        if row["provisional_workstream_contract"]["provisional_workstream"]["key"] == workstream_key
    )
    for role, section in (
        ("conditional_guards", "Source Conditional Guards"),
        ("boundaries", "Source Boundaries"),
        ("proof_duties", "Source Proof Duties"),
    ):
        assert owner["component_contract"][f"source_{role}"] == lifecycle[role]
        assert delivery["provisional_workstream_contract"][f"source_{role}"] == lifecycle[role]
        assert lifecycle[role][0]["source_refs"][0]["quote"] in delivery["radar_sections"][section]
    assert registry._provisional_component_contract(
        owner, semantics_version=intent[AUTHORED_SEMANTICS_KEY]["version"],
    ) == owner["component_contract"]
    inputs = registry.build_authored_component_authoring_inputs(
        root=tmp_path, proposal=proposal, release_selector="0.0.1",
        backlog_result=_allocated(proposal),
    )
    component_input = next(row for row in inputs if row["component_id"] == component_key)
    component_input["component_contract"] = deepcopy(owner["component_contract"])
    spec = registry.build_authored_component_spec(component_input)
    for heading in ("Source conditional guards", "Source boundaries", "Source proof duties"):
        assert f"## {heading}" in spec
    for role in ("conditional_guards", "boundaries", "proof_duties"):
        assert lifecycle[role][0]["source_refs"][0]["quote"] in spec
    wrong_owner = deepcopy(component_input)
    wrong_owner["component_contract"]["source_boundaries"][0]["workstream_key"] = "unrelated"
    with pytest.raises(ValueError, match="unrelated source boundaries"):
        registry.build_authored_component_spec(wrong_owner)

    stale = deepcopy(intent)
    stale_lifecycle = stale[AUTHORED_SEMANTICS_KEY]["source_duty"]["lifecycle"]
    stale_lifecycle["boundaries"] = []
    stale_lifecycle["lifecycle_sha256"] = _lifecycle_sha256({
        key: value for key, value in stale_lifecycle.items() if key != "lifecycle_sha256"
    })
    with pytest.raises(ValueError, match="incomplete coverage"):
        build_provisional_components(intent=stale, product_slug="harbor-planner")
    stale = deepcopy(intent)
    stale[AUTHORED_SEMANTICS_KEY]["source_duty"]["binding"]["proof_duties"][0]["duty_id"] = "stale"
    with pytest.raises(ValueError, match="custody is stale"):
        build_provisional_backlog(intent=stale, diagram_slugs={"context": "context"})
