"""Source role and recurrence controls independent of proposed execution order."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
from odylith.runtime.domain_intelligence import greenfield_authored_component_spec as registry
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import first_path_relations_from_intent, source_event_relations_from_intent
from odylith.runtime.domain_intelligence.greenfield_authored_first_run import authored_first_run_relations
from odylith.runtime.domain_intelligence.greenfield_event_ordering import validate_first_run
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import greenfield_authoring_schema
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import canonical_greenfield_host_candidate, greenfield_host_candidate_schema
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import project_greenfield_source_event_catalog, require_preserved_source_duty_owners
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from tests.unit.runtime.greenfield_model_authoring_fixtures import host_candidate_response, synthetic_source_duty_receipt, synthetic_source_duty_receipt_for_ledger
from tests.unit.runtime.test_greenfield_model_path_custody import _source, _response
from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case, _admit


@pytest.mark.parametrize("execution_kind", ["discrete_action", "recurring_invariant"])
def test_whole_product_performer_retains_independent_identity_and_complete_custody(tmp_path, execution_kind):
    prompt = _source()
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source = prepared.evidence_source
    response = _response(source)
    response["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3]
    candidate = host_candidate_response(response, evidence_text=source)
    ledger = deepcopy(synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"])
    duty = ledger["system_duties"][0]
    mention = {"quote": "the product", "context": "Dock attendant Ivo enters a vessel tag and the product records berth occupancy before the berth map shows the placement"}
    duty.update(performer_role="product_wide", execution_kind=execution_kind,
                actor_ref=mention, statement="the product records berth occupancy")
    proof = "Source evidence preserves berth history"
    ledger["proof_duties"] = [{"id": "history-proof", "source_refs": [{"quote": proof, "context": proof}],
                               "dossier_or_artifact": "berth history", "must_show": proof}]
    component = next(row for row in candidate["result"]["provisional_design"]["components"] if 3 in row["supported_event_orders"])
    workstream = next(row for row in candidate["result"]["provisional_design"]["workstreams"] if component["key"] in row["component_keys"])
    candidate["result"]["source_duty_binding"]["proof_duties"] = [{"duty_id": "history-proof", "component_key": component["key"], "workstream_key": workstream["key"]}]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt["ledger_sha256"]
    schema = greenfield_host_candidate_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(json.dumps(candidate)))
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=source, source_duty_receipt=receipt)
    Draft202012Validator(greenfield_authoring_schema(source_event_graph=True)).validate(canonical)
    for forbidden in ("title", "internal_systems"):
        invented = deepcopy(candidate)
        invented["result"]["events"] = [{"actor_fact": {"field": forbidden, "row": 1}, "action_quote": "records", "target_quote": "berth occupancy"}]
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(invented)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    assert len(catalog["facts"]["internal_systems"]) == 1
    assert catalog["events"][-1]["actor_fact_path"] == "/product_identity"
    materialized = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    semantics = materialized["authored_semantics"]
    assert "first_path_relations" not in semantics
    assert [row["order"] for row in first_path_relations_from_intent(materialized)] == [1, 2]
    assert [row["order"] for row in authored_first_run_relations(materialized)] == [1, 2]
    complete = source_event_relations_from_intent(json.loads(json.dumps(materialized)))
    assert complete[-1]["actor_kind"] == "product_wide"
    assert complete[-1]["actor_fact_quote"] == "the product"
    assert materialized["title"] != "the product"
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=materialized)
    model = proposal["semantic_model"]
    assert model["schema_version"].endswith(".v5")
    proof_obligation = next(row for row in model["proof_obligations"] if row["key"] == "source_proof/history-proof")
    assert proof_obligation["claim"] == proof_obligation["required_evidence"] == proof
    assert proof_obligation["source_refs"] == semantics["source_duty"]["lifecycle"]["proof_duties"][0]["source_refs"]
    assert any(row["duty_id"] == "history-proof" for component in proposal["components"] for row in component["component_contract"]["source_proof_duties"])
    assert model["first_path_contract"]["actor"] == "Dock attendant Ivo"
    assert [row["source_event_order"] for row in model["first_path_contract"]["events"]] == [1, 2]
    assert any(3 in row["component_contract"]["provisional_component"]["supported_event_orders"] for row in proposal["components"])


@pytest.mark.parametrize("recurring", [(), (3,)])
def test_cited_concrete_before_open_duty_is_executable_but_recurring_guard_is_not(recurring):
    run = {"event_orders": [3, 1, 2], "rationale": "A cited prerequisite precedes opening."}
    args = dict(event_orders=(1, 2, 3), first_path_event_orders=(1, 2),
                source_precedence=[{"before_event": 3, "after_event": 1, "constraint_index": 1}],
                result_event_order=2, recurring_event_orders=recurring)
    if recurring:
        with pytest.raises(ValueError, match="recurring invariant"):
            validate_first_run(run, **args)
    else:
        assert validate_first_run(run, **args) == run


def test_preserved_owner_pairs_cannot_move_but_exact_authorized_change_can():
    receipt = _admit(_edit_case())
    prior = receipt["edit_preservation"]["prior_lifecycle"]
    binding = {role: [{key: row[key] for key in ("duty_id", "component_key", "workstream_key")}
                      for row in prior[role]] for role in ("off_path_transitions", "conditional_guards", "boundaries", "proof_duties")}
    binding.update(first_path_actions=[{"duty_id": "A1", "event_order": 1}, {"duty_id": "A2", "event_order": 2}],
                   supporting_human_actions=[], system_duties=[])
    design = {"components": [{"key": "record-state", "supported_event_orders": [1, 2], "verification_event_orders": [1, 2]}],
              "workstreams": [{"key": "record-delivery", "component_keys": ["record-state"], "verification_event_orders": [1, 2]}]}
    require_preserved_source_duty_owners(binding, receipt, provisional_design=design)
    binding["conditional_guards"][0]["component_key"] = "different-owner"
    with pytest.raises(ValueError, match="prior component"):
        require_preserved_source_duty_owners(binding, receipt, provisional_design=design)
    receipt["decision_set"]["edit_preservation"]["conditional_guards/G1"].update(verdict="changed", correction_authorization="yes")
    require_preserved_source_duty_owners(binding, receipt, provisional_design=design)


def _mixed_source_graph(count):
    extra_events = [f"Berth map records receipt {order:02d}." for order in range(4, count + 1)]
    prompt = _source() + " " + " ".join(extra_events)
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source = prepared.evidence_source
    response = _response(source)
    response["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3]
    candidate = host_candidate_response(response, evidence_text=source)
    ledger = deepcopy(synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"])
    for order, event in enumerate(extra_events, start=4):
        citation = {"quote": event, "context": event}
        ledger["system_duties"].append({
            "id": f"receipt-{order:02d}", "source_refs": [],
            "performer_role": "internal_system", "execution_kind": "discrete_action",
            "event_ref": citation, "actor_ref": deepcopy(ledger["system_duties"][0]["actor_ref"]),
            "role_refs": [citation], "statement": event, "action": "records", "target": f"receipt {order:02d}",
        })
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    design = candidate["result"]["provisional_design"]
    design["first_run"]["event_orders"] = [1, 2]
    for key in ("supported_event_orders", "verification_event_orders"):
        design["components"][0][key] = list(range(1, min(count, 32) + 1))
    design["workstreams"][0]["verification_event_orders"] = list(range(1, min(count, 32) + 1))
    candidate["result"]["source_duty_binding"]["ledger_sha256"] = receipt["ledger_sha256"]
    return prompt, prepared, candidate, receipt


@pytest.mark.parametrize("count", [25, 32])
def test_complete_source_graph_accepts_existing_envelope_beyond_declared_path_cap(tmp_path, count):
    prompt, prepared, candidate, receipt = _mixed_source_graph(count)
    schema = greenfield_host_candidate_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(json.dumps(candidate)))
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)
    assert len(canonical["result"]["events"]) == count
    Draft202012Validator(greenfield_authoring_schema(source_event_graph=True)).validate(canonical)
    with pytest.raises(ValidationError):
        Draft202012Validator(greenfield_authoring_schema()).validate(canonical)
    materialized = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    complete = source_event_relations_from_intent(json.loads(json.dumps(materialized)))
    assert len(complete) == count
    assert [row["order"] for row in first_path_relations_from_intent(materialized)] == [1, 2]
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=materialized)
    supported = {order for row in proposal["components"] for order in row["component_contract"]["provisional_component"]["supported_event_orders"]}
    assert supported == set(range(1, count + 1))


def test_complete_source_graph_refuses_thirty_third_source_duty():
    with pytest.raises(ValueError, match="source action duties exceed"):
        _mixed_source_graph(33)


def test_declared_path_and_provider_design_keep_their_existing_bounds():
    _, prepared, candidate, receipt = _mixed_source_graph(25)
    ledger = deepcopy(receipt["ledger"])
    ledger["first_path_actions"].extend(ledger.pop("system_duties"))
    ledger["system_duties"] = []
    for duty in ledger["first_path_actions"]:
        duty.pop("execution_kind", None)
        duty["observable_result"] = "receipt retained"
    with pytest.raises(ValueError, match="first_path_actions.*too large"):
        synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prepared.evidence_source)
    candidate["result"]["provisional_design"]["components"][0]["supported_event_orders"].append(33)
    with pytest.raises(ValidationError):
        Draft202012Validator(greenfield_host_candidate_schema()).validate(candidate)


def test_recurring_history_safeguard_retains_all_projection_custody_without_becoming_first_run(tmp_path):
    safeguard = (
        "Before any already-authorized actor changes a governed record's state, the product must "
        "retain the immediately preceding state and its cited evidence as retrievable history linked to that record."
    )
    proof = "the immediately preceding state and its cited evidence as retrievable history linked to that record"
    prompt = _source() + " " + safeguard
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source = prepared.evidence_source
    response = _response(source)
    response["result"]["provisional_design"]["first_run"]["event_orders"] = [1, 3]
    candidate = host_candidate_response(response, evidence_text=source)
    ledger = deepcopy(synthetic_source_duty_receipt(candidate, evidence_text=source)["ledger"])
    citation = {"quote": safeguard, "context": safeguard}
    ledger["system_duties"].append({
        "id": "retain-prior-state", "source_refs": [], "performer_role": "product_wide",
        "execution_kind": "recurring_invariant", "event_ref": citation,
        "actor_ref": {"quote": "the product", "context": safeguard}, "role_refs": [citation],
        "statement": safeguard, "action": "retain", "target": "the immediately preceding state and its cited evidence",
    })
    ledger["conditional_guards"] = [{"id": "history-before-change", "source_refs": [citation],
        "trigger": "Before any already-authorized actor changes a governed record's state",
        "protected_action": "changes a governed record's state", "rule": safeguard}]
    ledger["proof_duties"] = [{"id": "retrievable-history", "source_refs": [citation],
        "dossier_or_artifact": "retrievable history", "must_show": proof}]
    design = candidate["result"]["provisional_design"]
    design["first_run"]["event_orders"] = [1, 2]
    for key in ("supported_event_orders", "verification_event_orders"):
        design["components"][0][key].append(4)
    design["workstreams"][0]["verification_event_orders"].append(4)
    allocation = {"component_key": design["components"][0]["key"], "workstream_key": design["workstreams"][0]["key"]}
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    binding = candidate["result"]["source_duty_binding"]
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    binding["conditional_guards"] = [{"duty_id": "history-before-change", **allocation}]
    binding["proof_duties"] = [{"duty_id": "retrievable-history", **allocation}]
    Draft202012Validator(greenfield_host_candidate_schema()).validate(json.loads(json.dumps(candidate)))
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    proposal = build_authored_greenfield_proposal(observed_source={}, release_selector="0.0.1", confirmed_intent=intent)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    complete = source_event_relations_from_intent(proposal["intent"])
    assert complete[3]["event_quote"] == safeguard
    assert complete[3]["actor_fact_path"] == "/product_identity"
    assert proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"]["system_duties"][-1] == ledger["system_duties"][-1]
    assert [row["order"] for row in first_path_relations_from_intent(intent)] == [1, 2]
    assert [row["order"] for row in authored_first_run_relations(intent)] == [1, 2]
    model = proposal["semantic_model"]
    assert model["source_lifecycle"]["conditional_guards"][0]["rule"] == safeguard
    assert model["source_lifecycle"]["proof_duties"][0]["must_show"] == proof
    obligation = next(row for row in model["proof_obligations"] if row["key"] == "source_proof/retrievable-history")
    assert obligation["claim"] == obligation["required_evidence"] == proof
    owner = next(row for row in proposal["components"] if row["component_id"] == allocation["component_key"])
    assert 4 in owner["component_contract"]["provisional_component"]["supported_event_orders"]
    assert owner["component_contract"]["source_conditional_guards"][0]["rule"] == safeguard
    assert owner["component_contract"]["source_proof_duties"][0]["must_show"] == proof
    inputs = registry.build_authored_component_authoring_inputs(root=tmp_path, proposal=proposal, release_selector="0.0.1",
        backlog_result={"created": [{"idea_id": f"B-{index:03d}", "title": row["title"]} for index, row in enumerate(proposal["backlog"], 1)]})
    spec = registry.build_authored_component_spec(next(row for row in inputs if row["component_id"] == allocation["component_key"]))
    assert safeguard in spec and proof in spec
    capability = next(row for row in proposal["diagrams"] if row["slug"].endswith("capability-support"))
    sequence = next(row for row in proposal["diagrams"] if row["title"] == "Proposed First Run")
    assert safeguard in json.dumps(capability["diagram_boxes"])
    assert safeguard not in json.dumps(sequence["diagram_boxes"])
