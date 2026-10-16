"""Source-owned project audience and versioned proposed display names."""
from copy import deepcopy
import json
import os
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from odylith.runtime.domain_intelligence import greenfield_host_candidate_shape as shape_owner
from odylith.runtime.domain_intelligence import greenfield_source_duty_binding as binding_owner
from odylith.runtime.domain_intelligence import greenfield_create_transaction as transaction_owner
from odylith.runtime.domain_intelligence.greenfield_host_candidate import admit_greenfield_host_candidate
from odylith.runtime.domain_intelligence.greenfield_host_candidate_shape import greenfield_host_candidate_schema, canonical_greenfield_host_candidate
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import validate_greenfield_authoring_response
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import GreenfieldModelAuthoringError
from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger, validate_greenfield_source_duty_ledger
from odylith.runtime.domain_intelligence.greenfield_provisional_design import require_source_design_pair, validate_provisional_design
from odylith.runtime.project_intelligence.authored_fact_presenter import authored_fact_view
from tests.unit.runtime.greenfield_model_authoring_fixtures import synthetic_source_duty_receipt_for_ledger, fresh_project_projection_fixture
from tests.unit.runtime.test_greenfield_model_path_custody import _source
from tests.unit.runtime.test_greenfield_source_run_plan import _carrier_case, _transaction_for_intent
from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions


def _case(*, suffix=""):
    prompt = _source() + suffix
    prepared = prepare_model_authoring_evidence(prompt=prompt)
    _, candidate, receipt = _carrier_case("first_path", source=prepared.evidence_source)
    return prompt, prepared, candidate, receipt


def _receipt(candidate, ledger, source):
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    candidate["result"]["source_duty_binding"].update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    return receipt


def _export(name, value):
    if prefix := os.environ.get("ODYLITH_CUSTOMER_TEST_EVIDENCE_DIR"):
        target = Path(prefix) / (name + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


@pytest.mark.parametrize("verdict", ["no", "uncertain", "missing"])
def test_project_customer_requires_source_only_affirmative_judgment(verdict):
    _, prepared, _, receipt = _case()
    decisions = deepcopy(receipt["decision_set"])
    if verdict == "missing":
        decisions.pop("customer")
    else:
        decisions["customer"]["verdict"] = verdict
    with pytest.raises(ValueError, match="customer decision|decision set is malformed"):
        validate_greenfield_source_duty_ledger(receipt["ledger"], evidence_text=prepared.evidence_source, decision_set=decisions)


def test_inventory_customer_is_required_and_cannot_use_reference_or_instruction():
    _, prepared, _, receipt = _case()
    missing = deepcopy(receipt["ledger"])
    missing.pop("customer")
    with pytest.raises(ValueError, match="object fields"):
        preflight_greenfield_source_duty_ledger(missing, evidence_text=prepared.evidence_source)
    for handling in ("reference_context", "authoring_instruction"):
        controlled = deepcopy(receipt["ledger"])
        controlled["evidence_controls"] = [{**controlled["customer"], "handling": handling}]
        with pytest.raises(ValueError, match="customer.*conflicts with ledger.evidence_controls"):
            preflight_greenfield_source_duty_ledger(controlled, evidence_text=prepared.evidence_source)


@pytest.mark.parametrize("selected", ["Dock attendant Ivo", None])
def test_candidate_cannot_reselect_project_customer(selected):
    _, prepared, candidate, receipt = _case()
    candidate["result"]["facts"]["customer"] = None if selected is None else {"quote": selected, "context": selected}
    with pytest.raises(ValueError):
        admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)


def test_verified_customer_remains_global_while_absence_requires_existing_assumption(tmp_path):
    prompt, prepared, candidate, receipt = _case()
    canonical = canonical_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)
    canonical["result"]["facts"]["customer"] = {"quote": "Dock attendant Ivo", "occurrence": 1}
    with pytest.raises(GreenfieldModelAuthoringError, match="canonical customer"):
        validate_greenfield_authoring_response(canonical, evidence_text=prepared.evidence_source, accepted_source_duties=receipt,
            accepted_source_duty_binding=binding_owner.validate_greenfield_source_duty_binding(candidate["result"]["source_duty_binding"], ledger_receipt=receipt, candidate_result=candidate["result"], evidence_text=prepared.evidence_source),
            elapsed_seconds=0, provider={}, profile_id="standard", effective_timeout_seconds=300, semantic_model_call_count=0, allow_zero_semantic_calls=True)
    ledger = deepcopy(receipt["ledger"])
    ledger["customer"] = None
    receipt = _receipt(candidate, ledger, prepared.evidence_source)
    with pytest.raises((ValueError, GreenfieldModelAuthoringError), match="customer|assumption"):
        admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)
    candidate["result"]["assumptions"].append({"applies_to": "customer", "statement": "Proposed audience to confirm before implementation."})
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path, host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    assert intent.get("customer", "") == ""
    transaction = _transaction_for_intent(intent, tmp_path)
    assert all(row["customer"] == "Assumption — Proposed audience to confirm before implementation." for row in transaction.proposal["backlog"])
    _export("absent-customer-assumption", {"kind": "synthetic affirmative absence; no live semantic qualification", "source": prepared.evidence_source, "receipt": receipt, "candidate": candidate, "transaction": transaction_owner.product_create_transaction_to_dict(transaction)})


@pytest.mark.parametrize("named", [False, True])
def test_actual_named_and_unnamed_compiler_presenter_radar_atlas_paths(tmp_path, named):
    case = fresh_project_projection_fixture(tmp_path, named=named)
    expected, proposal, payload = case["expected"], case["proposal"], case["project_payload"]
    assert proposal["intent"]["title"] == expected["source_title"]
    assert proposal["intent"]["customer"] == expected["customer"] != expected["first_performer"]
    assert all(row["customer"] == expected["customer"] for row in proposal["backlog"])
    assert all("## Customer\n" in text and expected["customer"] in text.split("## Customer\n", 1)[1].split("\n##", 1)[0] for text in case["radar_markdown"].values())
    assert payload["title"] == payload["product_story"]["headline"] == expected["project_name"]
    assert case["prewrite"].package.project_brief_record_text.splitlines()[0] == f"# {expected['project_name']} Project Brief"
    assert payload["authored_facts"]["title"] == expected["source_title"]
    assert proposal["semantic_model"]["domain_ontology"]["product_title"] == expected["source_title"]
    assert proposal["artifact_derivation"]["project_title"] == expected["project_name"]
    assert authored_fact_view(payload) is not None
    assert case["intent"]["authored_semantics"]["source_precedence"] == expected["source_precedence"]
    atlas = case["first_run_atlas"]
    assert 'event2 --> event3' in atlas["mermaid_source"]
    assert 'Source action' not in atlas["mermaid_source"] and 'source constraint' not in atlas["mermaid_source"]
    event3 = next(box for box in atlas["diagram_boxes"] if box["node_id"] == "event3")
    assert {"label": "Source prerequisite", "text": "before_event=2; after_event=3; constraint_index=1"} in event3["details"]
    assert all(box["label"] != "Action 1" for box in atlas["diagram_boxes"])
    _export("compiled-" + ("named" if named else "unnamed"), {"kind": case["kind"], "source": case["source"], "receipt": case["receipt"], "candidate": case["candidate"], "proposal": proposal, "project_payload": payload, "radar_markdown": case["radar_markdown"], "first_run_atlas": atlas, "expected": expected})


def test_explicit_name_and_exact_source_design_pairs_are_mandatory():
    _, prepared, candidate, receipt = _case()
    original = deepcopy(candidate["result"]["provisional_design"])
    candidate["result"]["provisional_design"]["project_name"] = "Conflicting proposed name"
    with pytest.raises((ValueError, GreenfieldModelAuthoringError), match="explicit verified source name"):
        admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)
    old_design = deepcopy(original)
    old_design["version"] = "odylith.greenfield.provisional-design.v6"
    old_design.pop("project_name")
    with pytest.raises(ValueError, match="version pair"):
        require_source_design_pair(old_design, source_duty={"ledger_receipt": receipt})
    old_receipt = deepcopy(receipt)
    old_receipt["ledger"]["version"] = "odylith.greenfield.source-duty-ledger.v13"
    with pytest.raises(ValueError, match="version pair"):
        require_source_design_pair(original, source_duty={"ledger_receipt": old_receipt})
    # Human presentation validates structure only; it has no receipt to grant authority.
    old_design["first_run"]["event_orders"] = [1, 2, 3]
    validate_provisional_design(old_design, event_orders=[1, 2, 3], result_event_order=3)
    with pytest.raises(ValueError, match="authenticated source"):
        require_source_design_pair(original, source_duty=None)


@pytest.mark.parametrize("change", ["wrong_value", "wrong_address", "invent_absent"])
def test_fully_rehashed_customer_substitutions_refuse_transaction_readback(tmp_path, monkeypatch, change):
    prompt, prepared, candidate, receipt = _case(suffix=" Second audience mention: Dock attendants.")
    if change == "invent_absent":
        ledger = deepcopy(receipt["ledger"])
        ledger["customer"] = None
        receipt = _receipt(candidate, ledger, prepared.evidence_source)
    wrong = {"quote": "Dock attendant Ivo", "context": "Dock attendant Ivo enters a vessel tag"} if change == "wrong_value" else {"quote": "Dock attendants", "context": "Second audience mention: Dock attendants."}
    actual_owner = binding_owner.source_owned_greenfield_actor_facts
    def altered(*args, **kwargs):
        facts = actual_owner(*args, **kwargs)
        facts["customer"] = deepcopy(wrong)
        return facts
    # Test-only fault injection constructs an internally hashed specimen. Every
    # production gate is restored before asserting the specific readback refusal.
    with monkeypatch.context() as construction:
        construction.setattr(binding_owner, "source_owned_greenfield_actor_facts", altered)
        construction.setattr(shape_owner, "source_owned_greenfield_actor_facts", altered)
        construction.setattr(transaction_owner, "_require_host_candidate_authority_binding", lambda *args, **kwargs: None)
        intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path, host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
        transaction = _transaction_for_intent(intent, tmp_path)
        payload = transaction_owner.product_create_transaction_to_dict(transaction)
    with pytest.raises(ValueError, match="customer differs|customer custody differs") as refusal:
        transaction_owner.product_create_transaction_from_dict(json.loads(json.dumps(payload)))
    _export("rehash-customer-" + change, {"kind": "new synthetic fully rehashed fault injection; guards restored for readback", "source": prepared.evidence_source, "receipt": receipt, "candidate": candidate, "transaction": payload, "refusal": str(refusal.value)})


def test_advertised_inventory_schema_to_actual_cli_admission(tmp_path, capsys):
    from odylith import cli
    from odylith.runtime.domain_intelligence.greenfield_source_duty_authoring import greenfield_source_duty_authoring_schema
    from tests.unit.runtime.greenfield_model_authoring_fixtures import source_duty_authoring_fixture
    prompt, prepared, candidate, receipt = _case()
    wire = source_duty_authoring_fixture(receipt["ledger"], evidence_text=prepared.evidence_source)
    Draft202012Validator(greenfield_source_duty_authoring_schema()).validate(wire)
    ledger_file, decision_file = tmp_path / "inventory.json", tmp_path / "decisions.json"
    ledger_file.write_text(json.dumps(wire))
    args = ["greenfield", "source-ledger-check", "--repo-root", str(tmp_path), "--prompt", prompt, "--ledger-file", str(ledger_file)]
    assert cli.main(args) == 0
    preflight_output = json.loads(capsys.readouterr().out)
    assert preflight_output["preflight"]["ledger"] == receipt["ledger"]
    decision_file.write_text(json.dumps(receipt["decision_set"]))
    assert cli.main([*args, "--decision-file", str(decision_file)]) == 0
    admitted = json.loads(capsys.readouterr().out)
    assert admitted["receipt"] == receipt
    Draft202012Validator(greenfield_host_candidate_schema()).validate(candidate)
    authored, host_receipt = admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=admitted["receipt"])
    assert authored.intent["customer"] == "Dock attendants"
    _export("native-schema-cli", {"kind": "mocked producer values through actual schema, CLI and candidate admission; no model", "source": prepared.evidence_source, "inventory": wire, "preflight": preflight_output, "admission": admitted, "candidate": candidate, "host_receipt": host_receipt})


@pytest.mark.parametrize("field", ["project_title", "project_slug"])
def test_fully_rehashed_display_binding_drift_refuses_readback(tmp_path, field):
    from dataclasses import replace
    from odylith.runtime.domain_intelligence.project_intelligence_binding import project_intelligence_binding_issues
    prompt, prepared, candidate, receipt = _case()
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    transaction = _transaction_for_intent(intent, tmp_path)
    proposal = deepcopy(transaction.proposal)
    # The helper above uses the direct authored builder without binding metadata;
    # attach the real binding owner before this isolated projection mutation.
    from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings
    proposal = attach_project_intelligence_bindings(proposal)
    proposal["artifact_derivation"][field] = "A different projection" if field == "project_title" else "different-projection"
    changed = replace(transaction, proposal=proposal,
        prewrite_package=replace(transaction.prewrite_package, proposal=proposal))
    changed = replace(changed, transaction_hash=transaction_owner.product_create_transaction_hash(changed))
    payload = transaction_owner.product_create_transaction_to_dict(changed)
    assert project_intelligence_binding_issues(proposal) == ["fresh authored artifact project name or slug differs from its paired provisional design"]
    with pytest.raises(ValueError, match="project name or slug differs") as refusal:
        transaction_owner.product_create_transaction_from_dict(json.loads(json.dumps(payload)))
    _export("rehash-display-" + field, {"kind": "new synthetic rehashed projection metadata mutation; product source authority unchanged", "source": prepared.evidence_source, "transaction": payload, "refusal": str(refusal.value)})


@pytest.mark.parametrize("version", [None, [], {}, 7, True])
def test_malformed_versions_keep_typed_value_error_before_presentation(version):
    from odylith.runtime.domain_intelligence.greenfield_provisional_design import provisional_design_schema
    from tests.unit.runtime.test_greenfield_authored_fact_presenter import _project
    with pytest.raises(ValueError, match="unsupported authority contract"):
        provisional_design_schema(version)
    _, _, candidate, receipt = _case()
    bad_receipt = deepcopy(receipt)
    bad_receipt["ledger"]["version"] = version
    with pytest.raises(ValueError, match="authenticated source custody"):
        require_source_design_pair(candidate["result"]["provisional_design"], source_duty={"ledger_receipt": bad_receipt})
    payload = _project()
    payload["authored_facts"]["provisional_design"]["version"] = version
    with pytest.raises(ValueError, match="unsupported authority contract"):
        authored_fact_view(payload)


def test_parallel_source_constraints_retain_every_trace_in_native_projection(tmp_path):
    from odylith.runtime.domain_intelligence.greenfield_authored_atlas_design_views import build_provisional_first_run_atlas_view
    first = "Record berth occupancy before showing the placement"
    second = "Persist the recorded occupancy before showing the placement"
    prompt, prepared, candidate, receipt = _case(suffix=" " + first + ". " + second + ".")
    ledger = deepcopy(receipt["ledger"])
    ledger["source_precedence"] = [{"before_duty_id": ledger["first_path_actions"][1]["id"],
        "after_duty_id": ledger["first_path_actions"][2]["id"], "constraint_ref": {"quote": quote, "context": quote}}
        for quote in (first, second)]
    receipt = _receipt(candidate, ledger, prepared.evidence_source)
    intent = materialize_host_authored_intent(prompt=prompt, repo_root=tmp_path,
        host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
    semantics = intent["authored_semantics"]
    assert semantics["source_precedence"] == [
        {"before_event": 2, "after_event": 3, "constraint_index": index} for index in (1, 2)]
    transaction = _transaction_for_intent(intent, tmp_path)
    atlas = next(row for row in transaction.proposal["diagrams"] if row["slug"].endswith("-first-run"))
    assert atlas["mermaid_source"].count("event2 --> event3") == 1
    box = next(row for row in atlas["diagram_boxes"] if row["node_id"] == "event3")
    assert [detail for detail in box["details"] if detail["label"] == "Source prerequisite"] == [
        {"label": "Source prerequisite", "text": f"before_event=2; after_event=3; constraint_index={index}"} for index in (1, 2)]
    old_design = deepcopy(semantics["provisional_design"])
    old_design["version"] = "odylith.greenfield.provisional-design.v6"
    old_design.pop("project_name")
    old_source, old_boxes = build_provisional_first_run_atlas_view(semantics["source_event_relations"],
        design=old_design, source_precedence=semantics["source_precedence"])
    assert 'event2 -->|"source constraint 2"| event3' in old_source
    assert all(detail["label"] != "Source prerequisite" for row in old_boxes for detail in row["details"])
    _export("parallel-precedence-native", {"kind": "new synthetic native materialization and full transaction readback; no model", "source": prepared.evidence_source, "candidate": candidate, "receipt": receipt, "transaction": transaction_owner.product_create_transaction_to_dict(transaction), "historical6_source": old_source})


@pytest.mark.parametrize("basis", ["explicit_name", "product_description"])
def test_missing_proposed_name_is_typed_refusal_for_named_and_unnamed(basis):
    _, prepared, candidate, receipt = _case()
    ledger = deepcopy(receipt["ledger"])
    ledger["product_identity"]["basis"] = basis
    receipt = _receipt(candidate, ledger, prepared.evidence_source)
    del candidate["result"]["provisional_design"]["project_name"]
    with pytest.raises(GreenfieldModelAuthoringError, match="bounded nonblank strings"):
        admit_greenfield_host_candidate(candidate, evidence_text=prepared.evidence_source, source_duty_receipt=receipt)


@pytest.mark.parametrize("named", [False, True])
def test_edit_can_change_only_a_provisional_name_without_reclassifying_source_identity(tmp_path, named):
    from tests.unit.runtime.test_greenfield_edit_allocation_conservation import _fresh, _receipt as edit_receipt

    fixture = fresh_project_projection_fixture(tmp_path, named=named)
    prior = _transaction_for_intent(fixture["intent"], tmp_path)
    correction = "Use Dock Evidence Ledger as the proposed project name. Keep every accepted action, system and its evidence."
    source, context, ledger, task, decisions = fresh = _fresh(prior, correction)
    receipt = edit_receipt(fresh)
    candidate = deepcopy(fixture["candidate"])
    candidate["result"]["provisional_design"]["project_name"] = "Dock Evidence Ledger"
    candidate["result"]["source_duty_binding"].update(
        source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    prompt = prior.proposal["intent"]["prompt"]
    prepared = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction)
    assert prepared.evidence_source == source
    evidence = {"kind": "synthetic EDIT29; real compiler/readback, no model or live EDIT",
        "source": source, "context": context, "task": task, "decisions": decisions,
        "receipt": receipt, "candidate": candidate,
        "prior_transaction": transaction_owner.product_create_transaction_to_dict(prior)}
    if named:
        with pytest.raises(GreenfieldModelAuthoringError, match="explicit verified source name") as refused:
            materialize_host_authored_intent(prompt=prompt, edit_evidence=correction, repo_root=tmp_path,
                host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
        evidence["refusal"] = str(refused.value)
    else:
        intent = materialize_host_authored_intent(prompt=prompt, edit_evidence=correction, repo_root=tmp_path,
            host_candidate=candidate, source_duty_receipt=receipt, prepared_evidence=prepared)
        edited = _transaction_for_intent(intent, tmp_path)
        assert intent["title"] == fixture["expected"]["source_title"]
        assert ledger["product_identity"] == prior.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"]["product_identity"]
        assert edited.proposal["artifact_derivation"]["project_slug"] == "dock-evidence-ledger"
        assert edited.proposal["intent"]["authored_semantics"]["provisional_design"]["project_name"] == "Dock Evidence Ledger"
        assert context["version"].endswith(".v4")
        assert "project_name" not in context and "customer" not in context
        evidence["transaction"] = transaction_owner.product_create_transaction_to_dict(edited)
    _export("edit-project-name-" + ("named-refused" if named else "unnamed-accepted"), evidence)
