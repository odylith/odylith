"""Conservation of authenticated EDIT relations, typed systems and byte custody."""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_prepare_cli as prepare_cli
from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from odylith.runtime.domain_intelligence import greenfield_source_duty_entailment as entailment
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_segment
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_model_source_citations import canonical_citation_from_source_span, resolve_source_citation
from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import (
    project_greenfield_source_event_catalog, source_action_allocation_relations,
    source_owned_greenfield_actor_facts, validate_greenfield_source_duty_design_binding,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    preflight_greenfield_source_duty_ledger, validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import preserved_edit_decisions_fixture
from tests.unit.runtime.test_greenfield_create_transaction import _transaction
from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions


def _fresh(prior, correction="Keep every accepted action and system. Retain its evidence."):
    source = prepare_model_authoring_evidence(prompt=prior.proposal["intent"]["prompt"], edit_evidence=correction).evidence_source
    context = cli._edit_preservation(prior, correction=correction, evidence_text=source)
    semantic = prior.proposal["intent"]["authored_semantics"]
    ledger = deepcopy(semantic["source_duty"]["ledger_receipt"]["ledger"])
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = entailment.source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=entailment.EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
        verifier_task_sha256=task["verifier_task_sha256"],
        identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"},
        **preserved_edit_decisions_fixture(context))
    return source, context, ledger, task, decisions


def _receipt(fresh):
    source, context, ledger, _, decisions = fresh
    return validate_greenfield_source_duty_ledger(ledger, evidence_text=source,
        decision_set=decisions, edit_preservation=context)


def test_all_surviving_actions_keep_relations_even_when_changed_and_authorized(tmp_path):
    prior = _transaction(repo_root=tmp_path)
    fresh = _fresh(prior)
    _, context, _, _, decisions = fresh
    receipt = _receipt(fresh)
    semantic = prior.proposal["intent"]["authored_semantics"]
    binding, design = deepcopy(semantic["source_duty"]["binding"]), deepcopy(semantic["provisional_design"])
    binding.update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    validate_greenfield_source_duty_design_binding(binding, ledger=receipt["ledger"], provisional_design=design, ledger_receipt=receipt)
    key = next(key for key in decisions["edit_preservation"] if key.startswith("first_path_actions/"))
    decisions["edit_preservation"][key].update(verdict="changed", correction_authorization="yes")
    receipt = _receipt(fresh)
    validate_greenfield_source_duty_design_binding(binding, ledger=receipt["ledger"], provisional_design=design, ledger_receipt=receipt)
    order = binding["first_path_actions"][0]["event_order"]
    owner = next(row for row in design["components"] if order in row["supported_event_orders"])
    owner["verification_event_orders"].remove(order)
    with pytest.raises(ValueError, match="every prior component/workstream allocation relation"):
        validate_greenfield_source_duty_design_binding(binding, ledger=receipt["ledger"], provisional_design=design, ledger_receipt=receipt)
    assert context["prior_actions"]["first_path_actions"][0]["allocation_relations"][0]["component_verifies"] is True


def test_equal_marginal_pair_swap_and_workstream_only_verification_are_distinct():
    components = [{"key": key, "supported_event_orders": [1], "verification_event_orders": []} for key in ("a", "b")]
    workstreams = [{"key": "w1", "component_keys": ["a"], "verification_event_orders": [1]},
                   {"key": "w2", "component_keys": ["b"], "verification_event_orders": [1]}]
    before = source_action_allocation_relations({"components": components, "workstreams": workstreams}, 1)
    workstreams[0]["component_keys"], workstreams[1]["component_keys"] = ["b"], ["a"]
    after = source_action_allocation_relations({"components": components, "workstreams": workstreams}, 1)
    assert {r["component_key"] for r in before} == {r["component_key"] for r in after}
    assert {r["workstream_key"] for r in before} == {r["workstream_key"] for r in after}
    assert before != after
    assert all(not row["component_verifies"] and row["workstream_verifies"] for row in before + after)


@pytest.mark.parametrize("verdict", ["preserved", "changed"])
@pytest.mark.parametrize("mutation", ["pair_swap", "support", "component_verify", "workstream_verify", "add_edge"])
def test_full_relational_gate_refuses_every_surviving_allocation_drift(verdict, mutation):
    from tests.unit.runtime.test_greenfield_source_lifecycle import _case
    from tests.unit.runtime.greenfield_model_authoring_fixtures import edit_action_context_fixture
    from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import project_greenfield_source_lifecycle
    from odylith.runtime.domain_intelligence.greenfield_source_duty_binding import require_preserved_source_duty_owners

    prompt, prior, candidate, binding = _case("dossier")
    design = {
        "components": [{"key": key, "supported_event_orders": [1, 2],
                        "verification_event_orders": [] if key == "a" else [1, 2]}
                       for key in ("a", "b", "c", "d")],
        "workstreams": [{"key": f"w{index}", "component_keys": [key], "verification_event_orders": [1, 2]}
                        for index, key in enumerate(("a", "b", "c", "d"), 1)],
    }
    lifecycle = project_greenfield_source_lifecycle(ledger_receipt=prior, binding=binding,
        candidate_result=candidate, evidence_text=prompt)
    correction = "Change the action text while keeping its allocation."
    context = edit_action_context_fixture(prior_source=prompt, prior_receipt=prior,
        prior_lifecycle=lifecycle, design=design, correction=correction)
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction).evidence_source
    preflight = preflight_greenfield_source_duty_ledger(prior["ledger"], evidence_text=source)
    task = entailment.source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=entailment.EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
        verifier_task_sha256=task["verifier_task_sha256"],
        identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"},
        **preserved_edit_decisions_fixture(context))
    for key, decision in decisions["edit_preservation"].items():
        if key.startswith("first_path_actions/"):
            decision.update(verdict=verdict, correction_authorization="yes" if verdict == "changed" else "not_required")
    receipt = validate_greenfield_source_duty_ledger(prior["ledger"], evidence_text=source,
        decision_set=decisions, edit_preservation=context)
    require_preserved_source_duty_owners(binding, receipt, provisional_design=design)
    assert context["prior_actions"]["first_path_actions"][0]["allocation_relations"] == [
        {"component_key": key, "workstream_key": f"w{index}",
         "component_verifies": key != "a", "workstream_verifies": True}
        for index, key in enumerate(("a", "b", "c", "d"), 1)]
    changed = deepcopy(design)
    if mutation == "pair_swap":
        changed["workstreams"][1]["component_keys"] = ["c"]
        changed["workstreams"][2]["component_keys"] = ["b"]
        before = source_action_allocation_relations(design, 1)
        after = source_action_allocation_relations(changed, 1)
        for key in ("component_key", "workstream_key"):
            assert {row[key] for row in before} == {row[key] for row in after}
    elif mutation == "support":
        changed["components"][1]["supported_event_orders"].remove(1)
        changed["components"][1]["verification_event_orders"].remove(1)
        changed["workstreams"][1]["verification_event_orders"].remove(1)
    elif mutation == "component_verify":
        changed["components"][0]["verification_event_orders"].append(1)
    elif mutation == "workstream_verify":
        changed["workstreams"][0]["verification_event_orders"].remove(1)
    else:
        changed["workstreams"][1]["component_keys"].append("a")
    with pytest.raises(ValueError, match="every prior component/workstream allocation relation"):
        require_preserved_source_duty_owners(binding, receipt, provisional_design=changed)


def test_shifted_duty_ids_keep_allocations_and_two_prior_actions_cannot_share_a_carrier(tmp_path):
    prior = _transaction(repo_root=tmp_path)
    source, context, ledger, _, _ = _fresh(prior)
    old_id = ledger["first_path_actions"][0]["id"]
    ledger["first_path_actions"][0]["id"] = "current-renumbered-action"
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = entailment.source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=entailment.EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
        verifier_task_sha256=task["verifier_task_sha256"],
        identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"},
        **preserved_edit_decisions_fixture(context, current_ids={old_id: "current-renumbered-action"}))
    receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=source,
        decision_set=decisions, edit_preservation=context)
    semantic = prior.proposal["intent"]["authored_semantics"]
    binding = deepcopy(semantic["source_duty"]["binding"])
    binding.update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    binding["first_path_actions"][0]["duty_id"] = "current-renumbered-action"
    validate_greenfield_source_duty_design_binding(binding, ledger=ledger,
        provisional_design=semantic["provisional_design"], ledger_receipt=receipt)
    other = context["prior_actions"]["first_path_actions"][1]["duty"]["id"]
    decisions["edit_preservation"][f"first_path_actions/{other}"]["current_duty_id"] = "current-renumbered-action"
    with pytest.raises(ValueError, match="distinct|carrier"):
        validate_greenfield_source_duty_ledger(ledger, evidence_text=source,
            decision_set=decisions, edit_preservation=context)


@pytest.mark.parametrize("mutation", ["rename", "remove", "replace", "retype"])
def test_unsupported_roster_mutation_is_a_truthful_no_write_outcome(tmp_path, monkeypatch, mutation):
    prior = _transaction(repo_root=tmp_path)
    fresh = _fresh(prior, correction=f"{mutation} the accepted system. Preserve all other duties.")
    decisions = fresh[-1]
    assert decisions["system_preservation"]
    atom_id = next(iter(decisions["system_preservation"]))
    decisions["system_preservation"][atom_id] = {
        "verdict": "removed" if mutation == "remove" else "changed", "correction_authorization": "yes"}
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    writes = []
    monkeypatch.setattr(cli.greenfield_pending_transaction_store, "stage_pending_transaction", lambda **kw: writes.append(kw), raising=False)
    with pytest.raises(ValueError) as error:
        _receipt(fresh)
    assert str(error.value) == entailment.UNSUPPORTED_SYSTEM_MUTATION
    assert writes == []
    assert {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


def test_candidate_empty_system_arrays_retain_exact_accepted_typed_roster(tmp_path):
    prior = _transaction(repo_root=tmp_path)
    source, context, *_ = fresh = _fresh(prior)
    receipt = _receipt(fresh)
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    facts = source_owned_greenfield_actor_facts(catalog,
        supplemental={"human_actors": [], "internal_systems": [], "external_systems": []},
        evidence_text=source, ledger_receipt=receipt)
    prior_names = prior.proposal["intent"]["internal_systems"]
    assert set(prior_names) <= {row["quote"] for row in facts["internal_systems"]}
    primary = [a for a in context["prior_system_facts"]["internal_systems"]
               if any(l["relation_order"] == 0 for l in a["projection_links"])]
    assert len(primary) == len(prior_names)
    for atom in primary:
        start, end = entailment.mapped_prior_source_span(context, atom["source_span_refs"][0], evidence_text=source)
        citation = canonical_citation_from_source_span(source.encode(), start=start, end=end)
        assert resolve_source_citation(source.encode(), citation) == (atom["normalized_value"], start)


@pytest.mark.parametrize("prior", ["\u2003\n猫 actor reviews review; review;\n\t ",
    combined_prompt_evidence_segment(prompt="é source with repeated review", edit_evidence="confirmed document: review")[0]])
def test_fixed_address_unicode_nested_and_strip_frames(prior):
    correction = "Keep the exact previous source. Add Δ."
    source, segment = combined_prompt_evidence_segment(prompt=prior, edit_evidence=correction)
    context = {"prior_source_segment": segment, "correction": correction}
    assert entailment.prior_source_bytes(context, evidence_text=source) == prior.encode()
    left, right = len(segment["removed_prefix"].encode()), len(prior.encode()) - len(segment["removed_suffix"].encode())
    locator = {"source_start_byte": left, "source_end_byte": right, "text_sha256": hashlib.sha256(prior.encode()[left:right]).hexdigest()}
    start, end = entailment.mapped_prior_source_span(context, locator, evidence_text=source)
    assert source.encode()[start:end] == prior.encode()[left:right]
    locator["source_start_byte"] = 0
    if left:
        with pytest.raises(ValueError, match="locator"):
            entailment.mapped_prior_source_span(context, locator, evidence_text=source)
    segment["embedded_start"] += 1
    with pytest.raises(ValueError, match="segment|frame"):
        entailment.prior_source_bytes(context, evidence_text=source)


def test_absent_reviewed_document_and_missing_baseline_refuse_before_discovery(tmp_path, monkeypatch):
    prior = _transaction(repo_root=tmp_path)
    authority = deepcopy(prior.intent_authority)
    authority["markdown_source_sha256"] = hashlib.sha256(b"reviewed document absent from prompt").hexdigest()
    previous = replace(prior, intent_authority=authority)
    from odylith.runtime.domain_intelligence import greenfield_create_transaction as transaction
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
    monkeypatch.setattr(transaction, "load_compiled_product_create_transaction_file", lambda path: previous)
    monkeypatch.setattr(pending, "resolve_pending_transaction", lambda **kw: tmp_path / "sealed.json")
    calls = []
    monkeypatch.setattr(prepare_cli, "resolve_trusted_codex_executable", lambda **kw: calls.append("discovery"))
    args = argparse.Namespace(repo_root=str(tmp_path), edit="Preserve the roster.", edit_evidence="", transaction_hash=prior.transaction_hash,
                              completion_receipt="delivered.json", release="")
    with pytest.raises(ValueError, match="reviewed-document source"):
        prepare_cli.prepare_request(args)
    assert calls == []
    fresh = _fresh(prior)
    context = deepcopy(fresh[1]); context.pop("prior_actions")
    with pytest.raises(ValueError, match="malformed"):
        entailment.source_duty_entailment_task(preflight_greenfield_source_duty_ledger(fresh[2], evidence_text=fresh[0]),
            evidence_text=fresh[0], edit_preservation=context)


def test_canonical_byte_bound_counts_utf8_and_escaped_json():
    value = {"a": "猫\n"}
    size = len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
    assert entailment.require_greenfield_request_bound(value, maximum=size, label="test request") == size
    with pytest.raises(ValueError, match="bound"):
        entailment.require_greenfield_request_bound(value, maximum=size - 1, label="test request")


# These fixtures use the actual compiler and accepted receipt owners, not padded JSON.
def _bounded_prior(lengths, root):
    from tests.unit.runtime.test_greenfield_source_event_roles import _mixed_source_graph
    from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt_for_ledger
    from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
    from odylith.runtime.domain_intelligence.greenfield_authored_proposal import build_authored_greenfield_proposal
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
    from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
    from tests.unit.runtime.test_greenfield_create_transaction import _package, _seal_test_package
    from tests.unit.runtime.greenfield_authored_proposal_fixtures import approved_authored_quality_manifest_fixture

    _, old_prepared, candidate, receipt = _mixed_source_graph(32)
    paragraph = "Bound reference paragraph: " + "x" * 2374
    human = deepcopy(candidate["result"]["facts"]["human_actors"][0])
    human["context"] = receipt["ledger"]["first_path_actions"][0]["event_ref"]["quote"]
    candidate["result"]["facts"]["human_actors"][0] = human
    extra = [f"{human['quote']} records receipt {index:02d}." for index in range(25, 33)]
    prompt = old_prepared.prompt + " " + " ".join(extra) + " " + paragraph
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    source = prepared.evidence_source
    ledger = deepcopy(receipt["ledger"])
    ledger["first_path_actions"][0]["actor_ref"] = human
    promoted = ledger["system_duties"][:22]
    for row in promoted:
        row.pop("execution_kind")
        row["observable_result"] = row["target"]
    ledger["first_path_actions"] += promoted
    ledger["supporting_human_actions"] = []
    ledger["system_duties"] = []
    for index, event in enumerate(extra, 25):
        citation = {"quote": event, "context": event}
        ledger["supporting_human_actions"].append({
            "id": f"support-{index}", "source_refs": [], "event_ref": citation,
            "actor_ref": human, "role_refs": [citation], "statement": event,
            "action": "records", "target": f"receipt {index:02d}",
        })
    duties = ledger["first_path_actions"] + ledger["supporting_human_actions"]
    for index, duty in enumerate(duties):
        duty["source_refs"] = [
            {"quote": "Bound reference paragraph", "context": paragraph[:lengths[4 * index + j]]}
            for j in range(4)
        ]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    candidate["result"]["provisional_design"]["first_run"]["event_orders"] = list(range(1, 25))
    candidate["result"]["source_duty_binding"].update(
        source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    # The existing fixture generates host bindings from this frozen source catalog.
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=root,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    proposal = build_authored_greenfield_proposal(observed_source={},
        release_selector="0.0.1", confirmed_intent=intent)
    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    package = _seal_test_package(_package(proposal, repo_root=root), repo_root=root)
    transaction = build_product_create_transaction(proposal=proposal, release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []}, prewrite_package=package,
        backlog_result=package.backlog_result or {}, intent_authority=authority, repo_root=root,
        quality_manifest=approved_authored_quality_manifest_fixture(intent_authority=authority, proposal=proposal))
    source = prepare_model_authoring_evidence(prompt=transaction.proposal["intent"]["prompt"],
        edit_evidence="Keep the exact roster and allocations.").evidence_source
    return transaction, source


def _canonical_size(value):
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _boundary_prior(root):
    lengths = [500] * 128
    prior, source = _bounded_prior(lengths, root)
    context = cli._edit_preservation(prior, correction="Keep the exact roster and allocations.", evidence_text=source)
    delta = entailment.MAX_EDIT_CONTEXT_BYTES - _canonical_size(context)
    quotient, remainder = divmod(delta, len(lengths))
    lengths = [length + quotient for length in lengths]
    lengths[0] += remainder
    prior, source = _bounded_prior(lengths, root)
    context = cli._edit_preservation(prior, correction="Keep the exact roster and allocations.", evidence_text=source)
    assert _canonical_size(context) == 131072
    return prior, source, context, lengths


def test_authenticated_context_max_and_plus_one_precede_provider_discovery(tmp_path, monkeypatch):
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import write_compiled_product_create_transaction_file
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
    prior, source, context, lengths = _boundary_prior(tmp_path)
    assert len(context["prior_actions"]["first_path_actions"]) == 24
    assert len(context["prior_actions"]["supporting_human_actions"]) == 8
    assert len(prior.proposal["intent"]["prompt"].encode()) <= 65536
    sealed = write_compiled_product_create_transaction_file(tmp_path / "max.json", prior)
    monkeypatch.setattr(pending, "resolve_pending_transaction", lambda **kw: sealed)
    calls = []
    class DiscoveryReached(Exception):
        pass
    def discover(**kwargs):
        calls.append("discovery")
        raise DiscoveryReached
    monkeypatch.setattr(prepare_cli, "resolve_trusted_codex_executable", discover)
    args = argparse.Namespace(repo_root=str(tmp_path), edit=context["correction"], edit_evidence="", transaction_hash=prior.transaction_hash,
                              completion_receipt="delivered.json", release="", diagnostic_evidence_dir="")
    with pytest.raises(DiscoveryReached):
        prepare_cli.prepare_request(args)
    assert calls == ["discovery"]
    lengths[0] += 1
    oversized, _ = _bounded_prior(lengths, tmp_path)
    sealed = write_compiled_product_create_transaction_file(tmp_path / "plus-one.json", oversized)
    args.transaction_hash = oversized.transaction_hash
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    calls.clear()
    with pytest.raises(ValueError, match="131072-byte bound"):
        prepare_cli.prepare_request(args)
    assert calls == []
    assert {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before
    # Every individual citation is legal; repeated expansion still cannot evade the total bound.
    repeated, repeated_source = _bounded_prior([2400] * 128, tmp_path)
    with pytest.raises(ValueError, match="131072-byte bound"):
        cli._edit_preservation(repeated, correction=context["correction"], evidence_text=repeated_source)


def _request_with_citations(prior, source, context, lengths, *, candidate):
    from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
        greenfield_host_candidate_contract, greenfield_host_candidate_authoring_request,
    )
    ledger = deepcopy(prior.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"])
    paragraph = "Bound reference paragraph: " + "x" * 2374
    actions = ledger["first_path_actions"] + ledger["supporting_human_actions"]
    for index, duty in enumerate(actions):
        duty["source_refs"] = [{"quote": "Bound reference paragraph", "context": paragraph[:lengths[4 * index + j]]} for j in range(4)]
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = entailment.source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    if not candidate:
        return task
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=entailment.EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
        verifier_task_sha256=task["verifier_task_sha256"], identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"},
        **preserved_edit_decisions_fixture(context))
    receipt = validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions, edit_preservation=context)
    contract = greenfield_host_candidate_contract(source, edit_preservation=context)
    action = ledger["first_path_actions"][0]
    admission = {"mode": "authority_admitted", "gate": {"decision": "admit", "required_fields": [],
        "owner_quote": source, "task_quote": source, "result_quote": source, "question": ""}}
    request = greenfield_host_candidate_authoring_request(contract, source_duty_receipt=receipt, authority_admission=admission)
    return {"request": request, "response_schema": contract["candidate_schema"]}


@pytest.mark.parametrize("candidate", [False, True], ids=["verifier", "candidate-and-schema"])
def test_complete_authenticated_request_max_and_plus_one_refuse_target_invocation(tmp_path, monkeypatch, candidate):
    prior, source, context, _ = _boundary_prior(tmp_path)
    lengths = [300 + index for index in range(128)]
    with monkeypatch.context() as probe:
        probe.setattr(entailment, "MAX_AUTHORING_REQUEST_BYTES", 1024 * 1024)
        size = _canonical_size(_request_with_citations(prior, source, context, lengths, candidate=candidate))
        delta = 262144 - size
        quotient, remainder = divmod(delta, len(lengths))
        lengths = [length + quotient for length in lengths]
        lengths[-1] += remainder
        assert max(lengths) <= 2400
        measured = _request_with_citations(prior, source, context, lengths, candidate=candidate)
        assert _canonical_size(measured) == 262144
    calls = []
    def target():
        request = _request_with_citations(prior, source, context, lengths, candidate=candidate)
        calls.append("candidate" if candidate else "verifier")
        return request
    assert _canonical_size(target()) == 262144
    assert len(calls) == 1
    calls.clear()
    lengths[-1] += 1
    with pytest.raises(ValueError, match="262144-byte bound"):
        target()
    assert calls == []


def test_same_label_distinct_typed_addresses_survive_but_same_address_retyping_refuses():
    from tests.unit.runtime.test_greenfield_source_lifecycle import _case
    from tests.unit.runtime.greenfield_model_authoring_fixtures import edit_action_context_fixture, synthetic_source_duty_receipt_for_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import project_greenfield_source_lifecycle
    prompt, old, candidate, binding = _case("dossier")
    ledger = deepcopy(old["ledger"])
    for index, (kind, clause) in enumerate((("internal_system", "Internal Link receives the dossier."),
                                           ("external_system", "External Link receives the dossier.")), 3):
        prompt += " " + clause
        event = {"quote": clause, "context": clause}
        ledger["system_duties"].append({"id": f"link-{index}", "source_refs": [], "performer_role": kind,
            "execution_kind": "discrete_action", "event_ref": event, "actor_ref": {"quote": "Link", "context": clause},
            "role_refs": [event], "statement": clause, "action": "receives", "target": "the dossier"})
    prior = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prompt)
    binding.update(source_sha256=prior["source_sha256"], ledger_sha256=prior["ledger_sha256"],
        system_duties=[{"duty_id": f"link-{i}", "event_order": i} for i in (3, 4)])
    design = candidate["provisional_design"]
    design["components"][0].update(supported_event_orders=[1, 2, 3, 4], verification_event_orders=[1, 2, 3, 4])
    design["workstreams"][0]["verification_event_orders"] = [1, 2, 3, 4]
    lifecycle = project_greenfield_source_lifecycle(ledger_receipt=prior, binding=binding, candidate_result=candidate, evidence_text=prompt)
    correction = "Preserve both distinct Link systems and their existing types."
    context = edit_action_context_fixture(prior_source=prompt, prior_receipt=prior, prior_lifecycle=lifecycle,
        design=design, correction=correction, prior_facts={
            "internal_systems": [ledger["system_duties"][0]["actor_ref"]],
            "external_systems": [ledger["system_duties"][1]["actor_ref"]]})
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction).evidence_source
    def accepted():
        preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
        task = entailment.source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
        decisions = _yes_decisions(preflight, evidence_text=source)
        decisions.update(version=entailment.EDIT_SOURCE_DUTY_DECISION_SET_VERSION, verifier_task_sha256=task["verifier_task_sha256"],
            identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"}, **preserved_edit_decisions_fixture(context))
        return validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions, edit_preservation=context)
    receipt = accepted()
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    facts = source_owned_greenfield_actor_facts(catalog, supplemental={"human_actors": [], "internal_systems": [], "external_systems": []},
                                              evidence_text=source, ledger_receipt=receipt)
    assert facts["internal_systems"] == [{"quote": "Link", "context": "Internal Link receives the dossier."}]
    assert facts["external_systems"] == [{"quote": "Link", "context": "External Link receives the dossier."}]
    ledger["system_duties"][0]["performer_role"] = "external_system"
    receipt = accepted()
    catalog = project_greenfield_source_event_catalog(receipt, evidence_text=source)
    with pytest.raises(ValueError) as error:
        source_owned_greenfield_actor_facts(catalog, supplemental={"human_actors": [], "internal_systems": [], "external_systems": []},
                                          evidence_text=source, ledger_receipt=receipt)
    assert str(error.value) == entailment.UNSUPPORTED_SYSTEM_MUTATION


@pytest.mark.parametrize("edit", [False, True], ids=["retained16", "retained17"])
def test_fresh_host59_refuses_valid_legacy_receipts_before_candidate_or_seal(tmp_path, monkeypatch, edit):
    from odylith.runtime.domain_intelligence import greenfield_host_candidate as host
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import _require_host_candidate_authority_binding
    prior = _transaction(repo_root=tmp_path)
    source = prior.proposal["intent"]["prompt"]
    ledger = prior.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"]
    context = None
    if edit:
        source, fresh, ledger, _, _ = _fresh(prior)
        context = entailment.greenfield_edit_preservation_context(transaction_hash=prior.transaction_hash,
            prior_lifecycle=fresh["prior_lifecycle"], prior_identity=fresh["prior_identity"],
            correction=fresh["correction"], evidence_text=source, _passive_allocations=True)
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = entailment.source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context, _passive_receipt=True)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions["verifier_task_sha256"] = task["verifier_task_sha256"]
    if edit:
        decisions.update(version="odylith.greenfield.source-duty-decisions.v12", edit_preservation={},
            identity_preservation={"verdict": "preserved", "correction_authorization": "not_required"})
    legacy = validate_greenfield_source_duty_ledger(ledger, evidence_text=source, decision_set=decisions,
        edit_preservation=context, _passive_receipt=True)
    assert legacy["version"].endswith(".v17" if edit else ".v16")
    assert verify_greenfield_source_duty_ledger_receipt(legacy, evidence_text=source) == legacy
    contract = host.greenfield_host_candidate_contract(source, edit_preservation=context)
    assert contract["version"].endswith(".v59")
    calls = []
    monkeypatch.setattr(host, "canonical_greenfield_host_candidate", lambda *a, **kw: calls.append("candidate/seal"))
    with pytest.raises(ValueError, match="receipt version"):
        host.admit_greenfield_host_candidate({}, evidence_text=source, source_duty_receipt=legacy)
    action = ledger["first_path_actions"][0]
    admission = {"mode": "authority_admitted", "gate": {"decision": "admit", "required_fields": [],
        "owner_quote": action["actor_ref"]["quote"], "task_quote": action["action"], "result_quote": action["target"], "question": ""}}
    with pytest.raises(ValueError, match="receipt version"):
        host.greenfield_host_candidate_authoring_request(contract, source_duty_receipt=legacy, authority_admission=admission)
    assert calls == []
    proposal = deepcopy(prior.proposal)
    proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"] = legacy
    for passive in (False, True):
        with pytest.raises(ValueError, match="source-duty hashes"):
            _require_host_candidate_authority_binding(prior.quality_manifest, prior.intent_authority, proposal=proposal, passive=passive)


def test_one_atomic_identity_cannot_supply_two_typed_roster_entries(tmp_path):
    from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import _authored_atom_id

    source, context, *_ = _fresh(_transaction(repo_root=tmp_path))
    rows = context["prior_system_facts"]["internal_systems"]
    original = next(atom for atom in rows if atom["projection_links"][0]["relation_order"] == 0)
    shared = deepcopy(original)
    external_link = {**shared["projection_links"][0], "field": "external_systems", "path": "/external_systems/0"}
    shared["projection_links"].append(external_link)
    shared["projection_links"].sort(key=lambda row: (row["field"], row["path"]))
    shared["atom_id"] = _authored_atom_id(shared)
    rows.remove(original)
    rows.append(shared)
    rows.sort(key=lambda atom: atom["atom_id"])
    context["prior_system_facts"]["external_systems"] = [deepcopy(shared)]
    all_atoms = [atom for values in context["prior_system_facts"].values() for atom in values]
    assert len(all_atoms) == 4 and len({atom["atom_id"] for atom in all_atoms}) == 3
    with pytest.raises(ValueError, match="globally unique"):
        entailment._validate_edit_context(context, evidence_text=source)
