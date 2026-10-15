"""Context may retain exact nonperformers without authorizing product claims."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_source_duty_ledger as ledger_owner
from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring as authoring_owner
from odylith.runtime.domain_intelligence.greenfield_host_candidate import admit_greenfield_host_candidate
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_from_dict, product_create_transaction_to_dict,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt_for_ledger
from tests.unit.runtime.test_greenfield_source_run_plan import seven_action_system_result_case, _transaction_for_intent

CONTEXT = "The optional Reef catalog supplies reference metadata; a lookup is supporting context, not an action in the chosen path."
INSTRUCTION = "Describe the supplied evidence clearly."


def context_case(field="external_systems"):
    """Declare new synthetic source; never edit or reuse the failed live output."""
    prompt, _, candidate, receipt = seven_action_system_result_case()
    context, name = {
        "external_systems": (CONTEXT, "Reef catalog"),
        "human_actors": ("The optional museum observer receives reference context but performs no workspace action.", "museum observer"),
        "internal_systems": ("The optional in-workspace reference viewer is supporting context, not a required path system.", "reference viewer"),
    }[field]
    prompt += " " + context + " " + INSTRUCTION
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    ledger = deepcopy(receipt["ledger"])
    ledger["evidence_controls"] = [
        {"quote": text, "context": text, "handling": handling}
        for text, handling in ((context, "reference_context"), (INSTRUCTION, "authoring_instruction"))]
    ledger["nonperforming_participants"][field] = [
        {"quote": name, "context": context, "mention_ordinal": 1}]
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prepared.evidence_source)
    candidate["result"]["source_duty_binding"].update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    return prompt, prepared, candidate, receipt


def _export(name, value):
    if directory := os.environ.get("ODYLITH_MENTION_TEST_EVIDENCE_DIR"):
        destination = Path(directory) / "context-authority"
        destination.mkdir(parents=True, exist_ok=True)
        (destination / (name + ".json")).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


@pytest.mark.parametrize("field", ["human_actors", "internal_systems", "external_systems"])
def test_context_participant_preserves_complete_run_roles_and_transaction(tmp_path, field):
    prompt, prepared, candidate, receipt = context_case(field)
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    transaction = _transaction_for_intent(intent, tmp_path)
    name = receipt["ledger"]["nonperforming_participants"][field][0]["quote"]
    assert intent[field][-1] == name
    relations = intent["authored_semantics"]["source_event_relations"]
    assert all(row["actor_fact_quote"] != name for row in relations)
    assert intent["authored_semantics"]["provisional_design"]["first_run"]["event_orders"] == [1, 2, 3, 4, 5, 6, 7, 13]
    assert all(component["dependencies"] == [] for component in transaction.proposal["components"])
    _export("participant-companion-" + field, {"kind": "new synthetic compiler transaction; no model/live qualification",
        "source": prepared.evidence_source, "receipt": receipt, "candidate": candidate,
        "transaction": product_create_transaction_to_dict(transaction)})


@pytest.mark.parametrize("judgment", ["entity_name", "participant_type", "nonperformance", "identity_nonduplication"])
@pytest.mark.parametrize("verdict", ["no", "uncertain", "missing"])
def test_context_membership_requires_every_existing_affirmative_judgment(judgment, verdict):
    _, prepared, _, receipt = context_case()
    decisions = deepcopy(receipt["decision_set"])
    row = decisions["participant_decisions"]["/external_systems/0"]
    if verdict == "missing":
        del row[judgment]
    else:
        row[judgment] = verdict
    with pytest.raises(ValueError, match="participant"):
        ledger_owner.validate_greenfield_source_duty_ledger(receipt["ledger"], evidence_text=prepared.evidence_source, decision_set=decisions)


@pytest.mark.parametrize("handling", ["reference_context", "authoring_instruction"])
@pytest.mark.parametrize("use", ["identity", "event", "actor", "support", "role", "state", "transition", "guard", "boundary", "proof", "precedence", "result", "terminal_proof"])
def test_controlled_text_cannot_support_product_uses(handling, use):
    _, prepared, _, receipt = context_case()
    ledger = deepcopy(receipt["ledger"])
    ledger["nonperforming_participants"]["external_systems"] = []
    ledger["evidence_controls"][0]["handling"] = handling
    ref = {"quote": CONTEXT, "context": CONTEXT}
    action = ledger["first_path_actions"][0]
    if use == "identity": ledger["product_identity"]["source_ref"] = ref
    elif use == "event": action["event_ref"] = ref
    elif use == "actor":
        action["actor_ref"] = {"quote": "Reef catalog", "context": CONTEXT}
        action["statement"] = f"Reef catalog {action['action']} {action['target']}"
    elif use == "support": action["source_refs"].append(ref)
    elif use == "role": action["role_refs"].append(ref)
    elif use in {"state", "transition", "guard", "boundary", "proof"}:
        section = {"state": "state_fields", "transition": "off_path_transitions", "guard": "conditional_guards", "boundary": "boundaries", "proof": "proof_duties"}[use]
        ledger[section][0]["source_refs"] = [ref]
    elif use == "precedence": ledger["source_precedence"][0]["constraint_ref"] = ref
    elif use == "result":
        ledger["terminal"].update(result_fact={"field": "success_metrics", "source_ref": ref}, result_quote="Reef catalog", result_occurrence=1)
    else: ledger["terminal"]["proof_boundary"] = ref
    with pytest.raises(ValueError, match=r"ledger\..*\[\d+,\d+\) conflicts with ledger.evidence_controls\[0\]"):
        ledger_owner.preflight_greenfield_source_duty_ledger(ledger, evidence_text=prepared.evidence_source)


@pytest.mark.parametrize("conflict", ["instruction", "partial", "simultaneous"])
def test_participant_exception_cannot_hide_another_control_or_partial_overlap(conflict):
    _, prepared, _, receipt = context_case()
    ledger = deepcopy(receipt["ledger"])
    if conflict == "instruction": ledger["evidence_controls"][0]["handling"] = "authoring_instruction"
    elif conflict == "partial": ledger["evidence_controls"][0].update(quote="Reef", context="Reef")
    else: ledger["evidence_controls"].append({"quote": "Reef catalog", "context": CONTEXT, "handling": "authoring_instruction"})
    with pytest.raises(ValueError, match=r"ledger.nonperforming_participants.external_systems\[0\].*conflicts.*evidence_controls"):
        ledger_owner.preflight_greenfield_source_duty_ledger(ledger, evidence_text=prepared.evidence_source)


def test_locator_context_does_not_grant_or_remove_selected_quote_authority():
    _, prepared, candidate, receipt = context_case()
    candidate["result"]["facts"]["problem"]["context"] = prepared.evidence_source
    assert len(prepared.evidence_source) <= 2400
    admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)


@pytest.mark.parametrize("field", ["problem", "success_metrics"])
@pytest.mark.parametrize("handling", ["reference_context", "authoring_instruction"])
def test_fully_rehashed_controlled_product_fact_refuses_persisted_readback(tmp_path, monkeypatch, field, handling):
    prompt, prepared, candidate, receipt = context_case()
    ref = {"quote": "Reef catalog", "context": CONTEXT} if handling == "reference_context" else {"quote": INSTRUCTION, "context": INSTRUCTION}
    candidate["result"]["facts"][field] = [ref] if field == "success_metrics" else ref
    with pytest.raises(ValueError, match="conflicts with ledger.evidence_controls"):
        admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)
    # Fault injection constructs only a new synthetic, fully compiled specimen.
    # Every real guard is restored before persisted readback is asserted.
    with monkeypatch.context() as construction:
        construction.setattr(ledger_owner, "require_source_evidence_authority", lambda *args, **kwargs: None)
        construction.setattr(authoring_owner, "require_source_evidence_authority", lambda *args, **kwargs: None)
        intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
            host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
        transaction = _transaction_for_intent(intent, tmp_path)
        payload = product_create_transaction_to_dict(transaction)
    with pytest.raises(ValueError, match=rf"/{field}.*conflicts with ledger.evidence_controls") as refused:
        product_create_transaction_from_dict(json.loads(json.dumps(payload)))
    _export(f"rehash-{handling}-{field}", {"kind": "new synthetic fault injection; policy bypass only in specimen construction; all guards restored for readback",
        "source": prepared.evidence_source, "receipt": receipt, "candidate": candidate,
        "transaction": payload, "refusal": str(refused.value)})


def test_each_projection_link_needs_its_own_exact_participant_address():
    _, prepared, _, receipt = context_case()
    source = prepared.evidence_source.encode()
    start = source.index(b"Reef catalog")
    end = start + len(b"Reef catalog")
    offsets = {"human_actors": 4, "internal_systems": 0, "external_systems": 0}
    ledger_owner.require_source_evidence_authority(receipt["ledger"], evidence_text=prepared.evidence_source,
        uses=[("/external_systems/0", start, end)], participant_offsets=offsets)
    for path in ("/problem", "/external_systems/1", "/first_path"):
        with pytest.raises(ValueError, match="conflicts"):
            ledger_owner.require_source_evidence_authority(receipt["ledger"], evidence_text=prepared.evidence_source,
                uses=[("/external_systems/0", start, end), (path, start, end)], participant_offsets=offsets)


@pytest.mark.parametrize("kind,handling", [
    ("normalized-underlying-ref", "reference_context"),
    ("normalized-underlying-ref", "authoring_instruction"),
    ("participant-multiple-links", "reference_context"),
])
def test_fully_rehashed_atomic_source_uses_refuse_persisted_readback(tmp_path, monkeypatch, kind, handling):
    from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
        _authored_atom_id, atomic_fact_ledger_hash,
    )
    from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_intent_authority_snapshot_hash

    prompt, prepared, candidate, receipt = context_case()
    if kind == "participant-multiple-links":
        candidate["result"]["facts"]["problem"] = {"quote": "Reef catalog", "context": CONTEXT}
    # Compile a new, explicitly malicious synthetic specimen with only the new
    # authority policy suspended. Existing schema, source, projection and hash
    # checks all run. Restored persisted readback must catch the authority error.
    with monkeypatch.context() as construction:
        construction.setattr(ledger_owner, "require_source_evidence_authority", lambda *args, **kwargs: None)
        construction.setattr(authoring_owner, "require_source_evidence_authority", lambda *args, **kwargs: None)
        intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
            host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
        authority = intent["product_intent_authority"]
        atoms = authority["atomic_facts"]
        if kind == "normalized-underlying-ref":
            atom = next(row for row in atoms if row["entailment_relationship"] == "verified_source_action"
                and row["projection_links"][0]["relation_role"] == "action_verb_quote")
            quote = "Reef catalog" if handling == "reference_context" else INSTRUCTION
            start = prepared.evidence_source.encode().index(quote.encode())
            ref = atom["source_span_refs"][0]
            digest = hashlib.sha256(quote.encode()).hexdigest()
            index = ref["span_id"].split(":")[1]
            span_id = f"authoring-atom:{index}:{start}:{start + len(quote.encode())}:{digest[:16]}"
            ref.update(span_id=span_id, source_start_byte=start, source_end_byte=start + len(quote.encode()), text_sha256=digest)
            atom["source_span_ids"] = [span_id]
            assert atom["normalized_value"] != quote
        else:
            atom = next(row for row in atoms if row["projection_links"][0]["path"] == "/external_systems/0")
            product_link = next(row for row in atoms if row["projection_links"][0]["path"] == "/problem")["projection_links"][0]
            atom["projection_links"].append(deepcopy(product_link))
            atom["projection_links"].sort(key=lambda link: (link["field"], link["path"]))
            assert [link["path"] for link in atom["projection_links"]] == ["/external_systems/0", "/problem"]
        atom["atom_id"] = _authored_atom_id(atom)
        atoms.sort(key=lambda row: row["atom_id"])
        authority["atomic_custody_sha256"] = atomic_fact_ledger_hash(atoms)
        authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(authority)
        transaction = _transaction_for_intent(intent, tmp_path)
        payload = product_create_transaction_to_dict(transaction)
    expected = r"/first_path#relation:.*action_verb_quote" if kind == "normalized-underlying-ref" else "/problem"
    with pytest.raises(ValueError, match=expected + r".*conflicts with ledger.evidence_controls") as refused:
        product_create_transaction_from_dict(json.loads(json.dumps(payload)))
    assert ledger_owner.verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=prepared.evidence_source) == receipt
    _export(f"rehash-{kind}-{handling}", {"kind": "new synthetic atomic fault injection; real compiler/hash/readback; only new policy bypassed during construction",
        "source": prepared.evidence_source, "receipt": receipt, "candidate": candidate,
        "target_atom": atom, "transaction": payload, "refusal": str(refused.value)})


def test_exact_source12_initial24_task_and_receipt_remain_frozen():
    _, source, _, receipt = seven_action_system_result_case()
    ledger = deepcopy(receipt["ledger"])
    ledger["version"] = "odylith.greenfield.source-duty-ledger.v12"
    old = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    assert old["version"].endswith(".v24")
    assert old["ledger_sha256"] == "a0f72780ae0ec45efbeb86841ea308915243f17a27afa4860c273f48fb52af78"
    assert old["verifier_task_sha256"] == "ae859b1a6925d18ea9387b38ef3814d7017f4e1d8f0c3b71527311edddd04fa3"
    assert old["decision_set_sha256"] == "3494e9868a318261c5d562c1c33b4e48bd1a0bab96096483a7dbb2b2b865d1a5"
    assert ledger_owner.verify_greenfield_source_duty_ledger_receipt(old, evidence_text=source) == old
    with pytest.raises(ValueError, match="receipt version"):
        admit_greenfield_host_candidate({}, evidence_text=source, source_duty_receipt=old)


def test_exact_old_context_rule_is_not_silently_upgraded():
    _, prepared, _, receipt = context_case()
    ledger = deepcopy(receipt["ledger"])
    ledger["version"] = "odylith.greenfield.source-duty-ledger.v12"
    with pytest.raises(ValueError, match="participant overlaps reference-only context"):
        ledger_owner.preflight_greenfield_source_duty_ledger(ledger, evidence_text=prepared.evidence_source,
            _passive_source_version=ledger["version"])


@pytest.mark.parametrize("edit", [False, True])
def test_fresh_host64_refuses_both_valid_host63_receipts_before_candidate(edit):
    if edit:
        from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import _edit_case, _admit
        case = _edit_case(source_version="odylith.greenfield.source-duty-ledger.v12")
        source, receipt = case[0], _admit(case)
    else:
        from tests.unit.runtime.test_greenfield_source_lifecycle import _case
        source, receipt, _, _ = _case("dossier", source_version="odylith.greenfield.source-duty-ledger.v12")
    assert receipt["version"].endswith(".v25" if edit else ".v24")
    assert ledger_owner.verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source) == receipt
    with pytest.raises(ValueError, match="receipt version"):
        admit_greenfield_host_candidate({}, evidence_text=source, source_duty_receipt=receipt)
