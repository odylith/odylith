"""Current producer custody survives release readback without semantic credit."""

from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
import sys

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_relation_fidelity import snapshot_relation_evidence
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_fact_ledger_hash, _authored_atom_id
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import authored_relation_set_sha256
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import validate_greenfield_authoring_response
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import STANDARD_PROFILE_ID
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import authored_semantics_mapping
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_facts_hash,
    product_facts_payload,
    require_verified_source_action_relations,
    build_product_intent_envelope,
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import _sha256
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    structural_design_fixture,
    synthetic_source_duty_receipt_for_ledger,
    authored_response,
)
from tests.unit.runtime.test_greenfield_normalized_action_custody import _shared_clause_candidate
from tests.unit.runtime.test_greenfield_product_intent_envelope import _INTENT, _RELATIONS, _source


def _normalized_snapshot(tmp_path):
    source, _prepared, candidate, receipt = _shared_clause_candidate()
    old_clause = "A reviewer defines scope and audience"
    clause = "A reviewer defines scope, audience, location, duration, budget, status and owner"
    source = source.replace(old_clause, clause)
    source += " Withdrawal closes scope and audience access. Only reviewers may restore withdrawn access."
    candidate = json.loads(json.dumps(candidate).replace(old_clause, clause))
    ledger = json.loads(json.dumps(receipt["ledger"]).replace(old_clause, clause))
    human, _duplicate_human, product = ledger["first_path_actions"]
    ledger["first_path_actions"] = [human, product]
    targets = ("audience", "location", "duration", "budget", "status", "owner")
    ledger["supporting_human_actions"] = [
        {**{key: deepcopy(value) for key, value in human.items() if key not in {"performer_role", "observable_result"}},
         "id": f"support-{index}", "statement": f"A reviewer defines {target}", "target": target}
        for index, target in enumerate(targets, 1)
    ]
    ledger["state_fields"] = [{
        "id": "access-field", "state_object": "scope and audience", "field": "access",
        "meaning": "access availability",
        "source_refs": [{"quote": "scope and audience access", "context": "scope and audience access"}],
    }]
    ledger["off_path_transitions"] = [{
        "id": "withdrawal", "trigger": "withdrawal", "governed_object": "scope and audience",
        "source_refs": [{"quote": "Withdrawal closes scope and audience access", "context": "Withdrawal closes scope and audience access"}],
        "effects": [{"field": "access", "change": "closed", "observable_check": "access closed"}],
    }]
    ledger["boundaries"] = [{
        "id": "restore-authority", "kind": "authority", "rule": "Only reviewers may restore withdrawn access",
        "source_refs": [{"quote": "Only reviewers may restore withdrawn access", "context": "Only reviewers may restore withdrawn access"}],
    }]
    prepared = prepare_model_authoring_evidence(prompt=source)
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prepared.evidence_source)
    result = candidate["result"]
    human_event, _duplicate, product_event = result["events"]
    result["events"] = [deepcopy(human_event) for _ in range(7)] + [product_event]
    result["terminal"]["event_order"] = 8
    result["terminal"]["result_fact"]["row"] = 8
    result["provisional_design"] = {
        **structural_design_fixture(range(1, 9), first_run_event_orders=[1, 8]),
        "project_summary": result["provisional_design"]["project_summary"],
    }
    binding = result["source_duty_binding"]
    binding["source_sha256"] = receipt["source_sha256"]
    binding["ledger_sha256"] = receipt["ledger_sha256"]
    binding["first_path_actions"] = [
        {"duty_id": human["id"], "event_order": 1},
        {"duty_id": product["id"], "event_order": 8},
    ]
    binding["supporting_human_actions"] = [
        {"duty_id": duty["id"], "event_order": index + 2}
        for index, duty in enumerate(ledger["supporting_human_actions"])
    ]
    owner = {
        "component_key": result["provisional_design"]["components"][0]["key"],
        "workstream_key": result["provisional_design"]["workstreams"][0]["key"],
    }
    binding["off_path_transitions"] = [{
        "duty_id": "withdrawal", **owner, "effects": [{"effect_index": 1, "state_field_id": "access-field"}],
    }]
    binding["boundaries"] = [{"duty_id": "restore-authority", **owner}]
    intent = materialize_host_authored_intent(
        prompt=source, repo_root=tmp_path, host_candidate=candidate,
        source_duty_receipt=receipt, prepared_evidence=prepared,
    )
    authority = intent["product_intent_authority"]
    snapshot = {
        "facts": product_facts_payload(intent),
        "authored_semantics": intent["authored_semantics"],
        **{key: deepcopy(authority[key]) for key in (
            "atomic_facts", "atomic_custody_sha256", "product_facts_sha256", "authored_relation_set_sha256",
        )},
    }
    return SimpleNamespace(prompt=source, confirmed_intent_markdown=""), snapshot


def _reseal(snapshot):
    """Recompute outer digests so controls exercise custody, rather than stale hashes."""
    semantics = snapshot["authored_semantics"]
    snapshot["authored_relation_set_sha256"] = authored_relation_set_sha256(
        semantics["first_path_relations"], semantics["component_responsibility_relations"],
        first_path_context_relations=semantics["first_path_context_relations"],
        source_precedence=semantics["source_precedence"], source_duty=semantics["source_duty"],
        provisional_design=semantics["provisional_design"],
    )
    snapshot["product_facts_sha256"] = product_facts_hash(snapshot["facts"])
    snapshot["atomic_custody_sha256"] = atomic_fact_ledger_hash(snapshot["atomic_facts"])


def test_normalized_shared_witness_and_six_local_supporting_events_pass_current_owners(tmp_path):
    case, snapshot = _normalized_snapshot(tmp_path)
    frozen = deepcopy(snapshot)
    evidence = snapshot_relation_evidence(case=case, snapshot=snapshot)
    assert evidence.issues == ()
    assert len(evidence.keys["first_path_events"]) == 8
    semantics = snapshot["authored_semantics"]
    assert semantics["provisional_design"]["first_run"]["event_orders"] == [1, 8]
    assert len(snapshot["facts"]["supporting_events"]) == 6
    assert all(row["event_start_byte"] == 0 for row in semantics["first_path_relations"][1:7])
    shared = semantics["first_path_relations"][:7]
    assert len({(row["source_start_byte"], row["source_end_byte"]) for row in shared}) == 1
    source_bytes = prepare_model_authoring_evidence(prompt=case.prompt).evidence_source.encode()
    witness = source_bytes[shared[0]["source_start_byte"]:shared[0]["source_end_byte"]]
    assert witness == b"A reviewer defines scope, audience, location, duration, budget, status and owner"
    assert all(row["event_quote"].encode() != witness for row in shared)
    assert any(atom["entailment_relationship"] == "verified_source_action" for atom in snapshot["atomic_facts"])
    assert snapshot == frozen


@pytest.mark.parametrize("damage", [
    "action", "target", "statement", "actor", "kind", "witness", "source", "receipt",
    "binding_source", "binding_ledger", "duplicate_role", "missing_role", "duty_identity",
    "supporting_offset", "first_run_pollution", "extra_semantics", "extra_source_duty", "extra_binding",
    "atomic_witness", "atomic_projection", "atomic_digest", "facts_digest", "lifecycle_binding_hash",
    "lifecycle_version", "state_meaning", "state_source_quote", "off_path_effect",
    "off_path_owner", "coordinated_off_path_owner", "boundary_occurrence",
])
def test_recomputed_relation_digest_does_not_hide_custody_damage(tmp_path, damage):
    case, snapshot = _normalized_snapshot(tmp_path)
    semantics = snapshot["authored_semantics"]
    relation = semantics["first_path_relations"][1]
    source_duty = semantics["source_duty"]
    binding = source_duty["binding"]
    if damage == "action":
        relation["action_verb_quote"] = "audience"
    elif damage == "target":
        relation["target_quote"] = "reviewer"
    elif damage == "statement":
        relation["event_quote"] = "A reviewer defines owner"
        relation["event_end_byte"] = len(relation["event_quote"].encode())
        snapshot["facts"]["supporting_events"][0] = relation["event_quote"]
        relation["target_quote"] = "owner"
    elif damage == "actor":
        relation["actor_fact_path"] = "/internal_systems/0"
        relation["actor_fact_quote"] = "Review Desk"
        relation["actor_kind"] = "product"
        relation["owner_system_path"] = "/internal_systems/0"
        relation["owner_system_quote"] = "Review Desk"
    elif damage == "kind":
        relation["actor_kind"] = "product"
    elif damage == "witness":
        relation["source_start_byte"] += 1
    elif damage == "source":
        case.prompt += " Changed source."
    elif damage == "receipt":
        source_duty["ledger_receipt"]["decision_set_sha256"] = "a" * 64
    elif damage in {"binding_source", "binding_ledger"}:
        binding["source_sha256" if damage == "binding_source" else "ledger_sha256"] = "a" * 64
    elif damage == "duplicate_role":
        binding["supporting_human_actions"][0]["event_order"] = 1
    elif damage == "missing_role":
        binding["supporting_human_actions"].pop()
    elif damage == "duty_identity":
        binding["supporting_human_actions"][0]["duty_id"] = "unknown"
    elif damage == "supporting_offset":
        relation["event_start_byte"] += 1
        relation["event_end_byte"] += 1
    elif damage == "first_run_pollution":
        semantics["provisional_design"]["first_run"]["event_orders"].insert(1, 2)
    elif damage == "extra_semantics":
        semantics["unexpected"] = []
    elif damage == "extra_source_duty":
        source_duty["unexpected"] = []
    elif damage == "extra_binding":
        binding["unexpected"] = []
    elif damage == "atomic_witness":
        snapshot["atomic_facts"][0]["source_span_refs"][0]["text_sha256"] = "a" * 64
    elif damage == "atomic_projection":
        snapshot["atomic_facts"][0]["projection_links"][0]["projection_start_byte"] += 1
    elif damage == "lifecycle_binding_hash":
        source_duty["lifecycle"]["binding_sha256"] = "a" * 64
    elif damage == "lifecycle_version":
        source_duty["lifecycle"]["version"] = "attacker.v1"
    elif damage == "state_meaning":
        source_duty["lifecycle"]["state_fields"][0]["meaning"] = "invented meaning"
    elif damage == "state_source_quote":
        source_duty["lifecycle"]["state_fields"][0]["source_refs"][0]["quote"] = "invented witness"
    elif damage == "off_path_effect":
        source_duty["lifecycle"]["off_path_transitions"][0]["effects"][0]["change"] = "invented effect"
    elif damage in {"off_path_owner", "coordinated_off_path_owner"}:
        binding["off_path_transitions"][0]["component_key"] = "missing-component"
        if damage == "coordinated_off_path_owner":
            source_duty["lifecycle"]["off_path_transitions"][0]["component_key"] = "missing-component"
    elif damage == "boundary_occurrence":
        source_duty["lifecycle"]["boundaries"][0]["source_refs"][0]["occurrence"] = 999
    if damage in {
        "lifecycle_version", "state_meaning", "state_source_quote", "off_path_effect",
        "off_path_owner", "coordinated_off_path_owner", "boundary_occurrence",
    }:
        lifecycle = source_duty["lifecycle"]
        lifecycle["binding_sha256"] = _sha256(binding)
        lifecycle["lifecycle_sha256"] = _sha256({
            key: value for key, value in lifecycle.items() if key != "lifecycle_sha256"
        })
    if damage in {"atomic_witness", "atomic_projection"}:
        atom = snapshot["atomic_facts"][0]
        atom["atom_id"] = _authored_atom_id(atom)
        snapshot["atomic_facts"].sort(key=lambda row: row["atom_id"])
    if damage == "extra_source_duty":
        with pytest.raises(ValueError, match="source-duty custody"):
            _reseal(snapshot)
        assert snapshot_relation_evidence(case=case, snapshot=snapshot).issues
        return
    _reseal(snapshot)
    if damage == "atomic_digest":
        snapshot["atomic_custody_sha256"] = "a" * 64
    elif damage == "facts_digest":
        snapshot["product_facts_sha256"] = "a" * 64
    assert snapshot_relation_evidence(case=case, snapshot=snapshot).issues


@pytest.mark.parametrize("field,value", [
    ("action_verb_quote", "audience"), ("target_quote", "reviewer"),
    ("actor_fact_quote", "Other reviewer"), ("source_end_byte", 1),
])
def test_shared_admission_owner_rejects_changed_verified_roles(tmp_path, field, value):
    case, snapshot = _normalized_snapshot(tmp_path)
    semantics = snapshot["authored_semantics"]
    relations = semantics["first_path_relations"]
    relations[1][field] = value
    source_text = prepare_model_authoring_evidence(prompt=case.prompt).evidence_source
    with pytest.raises(ValueError, match="verified source action"):
        require_verified_source_action_relations(
            relations, source_duty=semantics["source_duty"], source_text=source_text,
        )


def _legacy_snapshot():
    source = _source()
    prepared = prepare_model_authoring_evidence(prompt=source)
    result = validate_greenfield_authoring_response(
        authored_response(_INTENT, evidence_text=prepared.evidence_source,
                          first_path_relations=_RELATIONS, component_responsibility_owners=["Berth map"]),
        evidence_text=prepared.evidence_source, elapsed_seconds=1,
        provider={"kind": "fixture"}, profile_id=STANDARD_PROFILE_ID,
        effective_timeout_seconds=315, semantic_model_call_count=1,
    )
    semantics = authored_semantics_mapping(
        result.first_path_relations, result.component_responsibility_relations,
        first_path_context_relations=result.first_path_context_relations,
        provisional_design=result.provisional_design, source_duty=None,
    )
    envelope = build_product_intent_envelope(
        {**result.intent, "authored_semantics": semantics}, source_text=prepared.evidence_source,
        canonical_candidate_sha256="a" * 64, authored_source_spans=result.source_spans,
        authored_atomic_claims=result.atomic_claims, authored_source_sha256=result.source_sha256,
    )
    authority = product_intent_authority_from_envelope(envelope)
    snapshot = {
        "facts": envelope["product_facts"], "authored_semantics": semantics,
        **{key: authority[key] for key in (
            "atomic_facts", "atomic_custody_sha256", "product_facts_sha256", "authored_relation_set_sha256",
        )},
    }
    return SimpleNamespace(prompt=source, confirmed_intent_markdown=""), snapshot


def test_exact_source_relations_without_normalized_duties_remain_valid():
    case, snapshot = _legacy_snapshot()
    evidence = snapshot_relation_evidence(case=case, snapshot=snapshot)
    assert evidence.issues == ()
    assert len(evidence.keys["first_path_events"]) == 3
    assert all(row["entailment_relationship"] == "exact_source_span" for row in snapshot["atomic_facts"])
