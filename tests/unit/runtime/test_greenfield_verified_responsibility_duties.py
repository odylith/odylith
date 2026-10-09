"""Verified duty identity owns responsibilities, including shared source clauses."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    authored_component_relation_facts, first_path_relations_from_intent,
    validate_component_responsibility_relations,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    _require_host_candidate_authority_binding, product_create_transaction_from_dict,
    product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION, admit_greenfield_host_candidate,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    authored_response, host_candidate_response, synthetic_source_duty_receipt,
    synthetic_source_duty_receipt_for_ledger,
)
from tests.unit.runtime.test_greenfield_model_path_custody import _TEXT_FIELDS, _LIST_FIELDS
from tests.unit.runtime.test_greenfield_source_duty_actor_identity import five_actor_candidate

# Exact retained v27 clause and supporting refs; fixture declarations are not semantic qualification.
LAUNCH_RULE = "Recording launch status is prohibited if either check fails; the launch console must still remain unavailable unless the readiness disposition is approved."
ACCESS_REF = "the launch console must remain unavailable until the readiness disposition is approved"
CHECK_REF = "Before recording launch status, the study coordinator must verify that the shown consent material is the version bound to the experiment and that the shown readiness disposition matches the dossier."


def _citation(quote):
    return {"quote": quote, "context": quote}


def _case(*, alias=False, guards=False):
    events = (
        "Dock attendant Ivo enters a vessel tag",
        "Berth map records berth occupancy",
        "Readback panel shows the placement",
    )
    joined = " and ".join(events)
    intent = {
        **_TEXT_FIELDS, **deepcopy(_LIST_FIELDS), "first_path": joined,
        "title": "Berth map" if alias else "Harbor Desk",
        "internal_systems": ["Berth map", "Readback panel"],
        "component_responsibilities": [],
        "operational_constraints": ["Retain source notes for seven years"],
    }
    if guards:
        intent["operational_constraints"].append(LAUNCH_RULE)
    prompt = ". ".join(str(row) for value in intent.values()
                       for row in (value if isinstance(value, list) else [value]) if str(row))
    if guards:
        prompt += "\n" + ACCESS_REF + "\n" + CHECK_REF
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source = prepared.evidence_source
    response = authored_response(intent, evidence_text=source, first_path_relations=[
        {"actor_kind": "human", "actor_fact_quote": "Dock attendant Ivo", "event_quote": events[0],
         "action_verb_quote": "enters", "target_quote": "a vessel tag", "visible_result_quote": ""},
        {"actor_kind": "product", "actor_fact_quote": "Berth map", "owner_system_quote": "Berth map",
         "event_quote": events[1], "action_verb_quote": "records", "target_quote": "berth occupancy", "visible_result_quote": ""},
        {"actor_kind": "product", "actor_fact_quote": "Readback panel", "owner_system_quote": "Readback panel",
         "event_quote": events[2], "action_verb_quote": "shows", "target_quote": "the placement", "visible_result_quote": "the placement"},
    ])
    candidate = host_candidate_response(response, evidence_text=source)
    ledger = deepcopy(synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"])
    for duty in ledger["first_path_actions"]:
        duty["event_ref"] = _citation(joined)
        duty["source_refs"] = [_citation(joined), duty["actor_ref"]]
    if alias:
        ledger["first_path_actions"][1]["performer_role"] = "product_title"
    if guards:
        ledger["conditional_guards"] = [
            {"id": "launch-access", "protected_action": "Make the study launch console available.",
             "rule": "The launch console must remain unavailable unless the readiness disposition is approved.",
             "trigger": "The readiness disposition is not approved.", "source_refs": [_citation(ACCESS_REF), _citation(LAUNCH_RULE)]},
            {"id": "launch-recording-checks", "protected_action": "Record launch status.",
             "rule": "Recording launch status is prohibited if either the consent-version check or the readiness-disposition match check fails.",
             "trigger": "Either required verification check fails.", "source_refs": [_citation(CHECK_REF), _citation(LAUNCH_RULE)]},
        ]
        ledger["boundaries"] = [{"id": "retention", "kind": "data_use", "rule": "Retain source notes for seven years", "source_refs": [_citation("Retain source notes for seven years")]}]
        ledger["proof_duties"] = [{"id": "placement-proof", "dossier_or_artifact": "placement receipt", "must_show": "Verify the placement and retention receipt", "source_refs": [_citation("Verify the placement and retention receipt")]}]
        design = candidate["result"]["provisional_design"]
        component = design["components"][0]["key"]
        workstream = next(row["key"] for row in design["workstreams"] if component in row["component_keys"])
        for role in ("conditional_guards", "boundaries", "proof_duties"):
            candidate["result"]["source_duty_binding"][role] = [
                {"duty_id": duty["id"], "component_key": component, "workstream_key": workstream}
                for duty in ledger[role]
            ]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt["ledger_sha256"]
    return prompt, prepared, candidate, receipt, events, joined


def _materialized(tmp_path, **options):
    prompt, prepared, candidate, receipt, events, joined = _case(**options)
    authoring = {}
    intent = materialize_host_authored_intent(
        prompt=prompt, repo_root=tmp_path, prepared_evidence=prepared,
        host_candidate=candidate, source_duty_receipt=receipt, authoring_receipt=authoring,
    )
    return intent, authoring, receipt, events, joined


def test_shared_human_and_two_product_span_projects_each_verified_duty(tmp_path):
    intent, _, receipt, events, joined = _materialized(tmp_path)
    rows = intent["authored_semantics"]["component_responsibility_relations"]
    assert intent["component_responsibilities"] == list(events[1:])
    assert [row["first_path_event_order"] for row in rows] == [2, 3]
    assert [row["owner_system_path"] for row in rows] == ["/internal_systems/0", "/internal_systems/1"]
    assert [row["source_duty_id"] for row in rows] == [duty["id"] for duty in receipt["ledger"]["first_path_actions"][1:]]
    assert {row["decision_set_sha256"] for row in rows} == {receipt["decision_set_sha256"]}
    assert all(joined != row["responsibility_quote"] for row in rows)
    assert events[0] not in intent["component_responsibilities"]
    relations = first_path_relations_from_intent(json.loads(json.dumps(intent)))
    assert len({(row["source_start_byte"], row["source_end_byte"]) for row in relations}) == 1
    assert [row["actor_kind"] for row in relations] == ["human", "product", "product"]


def test_source_title_performer_keeps_validated_event_owner_address(tmp_path):
    intent, _, _, _, _ = _materialized(tmp_path, alias=True)
    rows = intent["authored_semantics"]["component_responsibility_relations"]
    events = first_path_relations_from_intent(intent)
    assert rows[0]["owner_system_path"] == events[1]["actor_fact_path"] == "/title"
    assert rows[1]["owner_system_path"] == events[2]["actor_fact_path"] == "/internal_systems/0"


@pytest.mark.parametrize("damage", ("missing_duty", "wrong_duty", "missing_decision", "wrong_decision", "missing_event", "wrong_event", "missing_actor", "wrong_actor", "human_promotion", "external_promotion", "remove_all_metadata", "missing_source_snapshot", "wrong_source_snapshot"))
def test_canonical_and_current_sealed_profile_refuse_forged_provenance(tmp_path, damage):
    intent, authoring, _, _, _ = _materialized(tmp_path)
    damaged = json.loads(json.dumps(intent))
    rows = damaged["authored_semantics"]["component_responsibility_relations"]
    row = rows[0]
    if damage == "missing_source_snapshot": damaged.pop("prompt")
    elif damage == "wrong_source_snapshot": damaged["prompt"] += " altered source"
    elif damage == "missing_event": row.pop("first_path_event_order")
    elif damage == "missing_actor": row.pop("owner_system_path")
    elif damage.startswith("missing_"):
        row.pop("source_duty_id" if damage == "missing_duty" else "decision_set_sha256")
    elif damage == "wrong_duty": row["source_duty_id"] = "not-an-accepted-duty"
    elif damage == "wrong_decision": row["decision_set_sha256"] = "0" * 64
    elif damage == "wrong_event": row["first_path_event_order"] = 3
    elif damage == "wrong_actor": row["owner_system_path"], row["owner_system_quote"] = "/internal_systems/1", "Readback panel"
    elif damage == "human_promotion": row["first_path_event_order"] = 1
    elif damage == "external_promotion":
        damaged["authored_semantics"]["first_path_relations"][1]["actor_kind"] = "external_system"
    elif damage == "remove_all_metadata":
        for relation in rows:
            relation.pop("source_duty_id"); relation.pop("decision_set_sha256")
    with pytest.raises(ValueError):
        _require_host_candidate_authority_binding(
            {"model_authoring": authoring}, intent[PRODUCT_INTENT_AUTHORITY_KEY],
            proposal={"intent": damaged}, passive=True,
        )
    with pytest.raises(ValueError):
        validate_component_responsibility_relations(
            rows, intent=damaged,
            first_path_relations=damaged["authored_semantics"]["first_path_relations"], require_verified_duties=True,
        )


def test_current_compiled_transaction_round_trips_without_source_reinterpretation(tmp_path):
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction
    transaction = _transaction(repo_root=tmp_path)
    loaded = product_create_transaction_from_dict(json.loads(json.dumps(product_create_transaction_to_dict(transaction))))
    assert loaded.transaction_hash == transaction.transaction_hash
    assert loaded.proposal["intent"]["prompt"] == transaction.proposal["intent"]["prompt"]
    assert loaded.quality_manifest["model_authoring"]["host_candidate"]["contract_version"] == HOST_CANDIDATE_CONTRACT_VERSION


def test_human_only_source_keeps_proposed_components_without_accepted_roles():
    source, candidate, _ = five_actor_candidate()
    authored, _ = admit_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=synthetic_source_duty_receipt(candidate, evidence_text=source))
    assert authored.intent["component_responsibilities"] == []
    assert authored.component_responsibility_relations == ()
    assert authored.provisional_design["components"]
    assert authored_component_relation_facts(title=authored.intent["title"], internal_systems=(), relations=authored.first_path_relations, component_responsibility_relations=()) == ()


def test_candidate_cannot_reintroduce_independent_component_authority():
    _, prepared, candidate, receipt, _, _ = _case()
    candidate["result"]["components"] = []
    with pytest.raises(ValueError, match="invalid shape"):
        admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)


def test_retained_research_guard_rules_refs_and_allocations_survive_views(tmp_path):
    intent, _, receipt, _, _ = _materialized(tmp_path, guards=True)
    lifecycle = intent["authored_semantics"]["source_duty"]["lifecycle"]
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)
    for role, key in (("conditional_guards", "source_conditional_guards"), ("boundaries", "source_boundaries"), ("proof_duties", "source_proof_duties")):
        canonical = lifecycle[role]
        component_rows = [duty for row in proposal["components"] for duty in row["component_contract"][key]]
        workstream_rows = [duty for row in proposal["backlog"] for duty in row["provisional_workstream_contract"][key]]
        assert component_rows == workstream_rows == canonical
        for duty, original in zip(canonical, receipt["ledger"][role], strict=True):
            assert [ref["quote"] for ref in duty["source_refs"]] == [ref["quote"] for ref in original["source_refs"]]
            assert duty["component_key"] and duty["workstream_key"]
            if role == "conditional_guards": assert duty["rule"] == original["rule"]
    guards = lifecycle["conditional_guards"]
    assert [row["duty_id"] for row in guards] == ["launch-access", "launch-recording-checks"]
    assert guards[0]["source_refs"][1]["quote"] == guards[1]["source_refs"][1]["quote"] == LAUNCH_RULE
    assert len(proposal["diagrams"]) == 5
    assert len(proposal["components"]) == len(proposal["backlog"]) == 4
    for diagram in proposal["diagrams"]:
        assert diagram["projection_origin"] == "model_authored_typed_intent"


@pytest.mark.parametrize("damage", ("omitted_guard", "wrong_allocation"))
def test_lifecycle_coverage_and_allocation_refusal_remains(tmp_path, damage):
    prompt, prepared, candidate, receipt, _, _ = _case(guards=True)
    rows = candidate["result"]["source_duty_binding"]["conditional_guards"]
    if damage == "omitted_guard": rows.pop()
    else: rows[0]["component_key"] = "unowned-component"
    with pytest.raises(ValueError):
        materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path, prepared_evidence=prepared, host_candidate=candidate, source_duty_receipt=receipt)
    assert not (tmp_path / ".odylith").exists()
