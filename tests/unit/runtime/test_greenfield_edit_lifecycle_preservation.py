"""EDIT coverage witnesses preserve correction precedence before candidate work."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    prepare_model_authoring_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
    GreenfieldSourceDutyEntailmentError,
    greenfield_edit_preservation_context,
    source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_source_lifecycle import (
    project_greenfield_source_lifecycle,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    synthetic_source_duty_receipt_for_ledger,
)
from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions
from tests.unit.runtime.test_greenfield_source_lifecycle import _case


GUARD = "Before approval, access must remain open."
SECOND_GUARD = "Before approval, edits must remain locked."
ADDITIVE = "Show the approval status alongside the record. Keep all earlier safeguards."
GUARD_KEY = "conditional_guards/G1"


def _edit_case(correction=ADDITIVE, *, include_guard=True, include_second_guard=False):
    prompt, receipt, candidate, binding = _case("dossier")
    prompt += " " + GUARD
    ledger = deepcopy(receipt["ledger"])
    ledger["conditional_guards"] = [{
        "id": "G1", "source_refs": [{"quote": GUARD, "context": GUARD}],
        "trigger": "before approval", "protected_action": "approval",
        "rule": "access must remain open",
    }]
    if include_second_guard:
        prompt += " " + SECOND_GUARD
        ledger["conditional_guards"].append({
            "id": "G2", "source_refs": [{"quote": SECOND_GUARD, "context": SECOND_GUARD}],
            "trigger": "before approval", "protected_action": "approval",
            "rule": "edits must remain locked",
        })
    receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=prompt)
    binding.update(source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"])
    binding["conditional_guards"] = [{
        "duty_id": row["id"], "component_key": "record-state", "workstream_key": "record-delivery",
    } for row in ledger["conditional_guards"]]
    lifecycle = project_greenfield_source_lifecycle(
        ledger_receipt=receipt, binding=binding, candidate_result=candidate, evidence_text=prompt,
    )
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction).evidence_source
    context = greenfield_edit_preservation_context(
        transaction_hash="a" * 64, prior_lifecycle=lifecycle,
        correction=correction, evidence_text=source,
    )
    if not include_guard:
        ledger["conditional_guards"] = []
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions["version"] = EDIT_SOURCE_DUTY_DECISION_SET_VERSION
    decisions["verifier_task_sha256"] = task["verifier_task_sha256"]
    decisions["edit_preservation"] = {
        f"{section}/{row['duty_id']}": {
            "verdict": "preserved", "current_duty_id": row["duty_id"], "correction_authorization": "not_required",
        }
        for section in ("state_fields", "off_path_transitions", "conditional_guards", "boundaries", "proof_duties")
        for row in lifecycle[section]
    }
    return source, ledger, context, task, decisions


def _admit(case):
    source, ledger, context, _, decisions = case
    return validate_greenfield_source_duty_ledger(
        ledger, evidence_text=source, decision_set=decisions, edit_preservation=context,
    )


def test_initial_request_keeps_the_existing_non_edit_decision_and_receipt_shape():
    source, receipt, _, _ = _case("dossier")
    ledger = receipt["ledger"]
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source)
    assert "edit_preservation" not in task
    assert "edit_preservation" not in task["decision_set_schema"]["properties"]
    assert receipt["version"] == "odylith.greenfield.source-duty-ledger-receipt.v7"
    assert task["decision_set_schema"]["properties"]["version"]["enum"] == ["odylith.greenfield.source-duty-decisions.v4"]
    assert validate_greenfield_source_duty_ledger(
        ledger, evidence_text=source, decision_set=_yes_decisions(preflight, evidence_text=source),
    ) == receipt


def test_host_receipt_passive_approval_is_an_explicit_closed_version_pair(tmp_path):
    from odylith.runtime.domain_intelligence.greenfield_model_receipt_approval import greenfield_model_authoring_receipt_approved
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction

    transaction = _transaction(repo_root=tmp_path)
    for version, approved in ((49, True), (50, True), (51, True), (48, False), (52, False)):
        model = deepcopy(transaction.quality_manifest["model_authoring"])
        model["host_candidate"]["contract_version"] = f"odylith.greenfield.host-candidate-contract.v{version}"
        assert greenfield_model_authoring_receipt_approved(
            model_authoring=model, semantic_compiler=transaction.quality_manifest["semantic_compiler"],
            requested_repair_tier=transaction.quality_manifest["requested_repair_tier"],
        ) is approved


@pytest.mark.parametrize("damage", ["legacy_decisions", "legacy_receipt", "missing_context", "initial_as_edit"])
def test_initial_and_edit_protocol_pairs_cannot_be_interchanged(damage):
    case = _edit_case()
    source, _, context, _, decisions = case
    receipt = _admit(case)
    assert receipt["version"] == "odylith.greenfield.source-duty-ledger-receipt.v9"
    assert decisions["version"] == "odylith.greenfield.source-duty-decisions.v6"
    if damage == "legacy_decisions":
        decisions["version"] = "odylith.greenfield.source-duty-decisions.v4"
        with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
            _admit(case)
        return
    if damage == "legacy_receipt":
        receipt["version"] = "odylith.greenfield.source-duty-ledger-receipt.v7"
    elif damage == "missing_context":
        del receipt["edit_preservation"]
    else:
        source, receipt, _, _ = _case("dossier")
        context = None
        receipt["version"] = "odylith.greenfield.source-duty-ledger-receipt.v9"
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="version|baseline"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source, edit_preservation=context)


def test_preserved_typed_lifecycle_has_fixed_keys_and_receipt_custody():
    case = _edit_case()
    source, ledger, context, task, _ = case
    sealed_before = json.dumps(context["prior_lifecycle"], sort_keys=True)
    receipt = _admit(case)
    assert receipt["edit_preservation"] == context
    assert verify_greenfield_source_duty_ledger_receipt(
        receipt, evidence_text=source, edit_preservation=context,
    ) == receipt
    schema = task["decision_set_schema"]["properties"]["edit_preservation"]
    assert set(schema["required"]) == {"state_fields/F1", "state_fields/F2", "off_path_transitions/T1", GUARD_KEY}
    assert schema["properties"][GUARD_KEY]["properties"]["current_duty_id"]["enum"] == ["", "G1"]
    assert json.dumps(context["prior_lifecycle"], sort_keys=True) == sealed_before
    assert receipt["ledger"] == ledger


def test_old_global_yes_cannot_admit_an_omitted_prior_guard():
    case = _edit_case(include_guard=False)
    source, ledger, context, _, _ = case
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    old_yes = _yes_decisions(preflight, evidence_text=source)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="malformed"):
        validate_greenfield_source_duty_ledger(
            ledger, evidence_text=source, decision_set=old_yes, edit_preservation=context,
        )
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="typed carrier"):
        _admit(case)


@pytest.mark.parametrize("damage", ["omit", "missing", "uncertain", "prose", "wrong_section", "empty"])
def test_prior_duty_needs_an_affirmative_same_section_carrier(damage):
    case = _edit_case()
    decisions = case[-1]
    row = decisions["edit_preservation"][GUARD_KEY]
    if damage == "omit":
        del decisions["edit_preservation"][GUARD_KEY]
    elif damage in {"missing", "uncertain"}:
        row["verdict"] = damage
        row["current_duty_id"] = ""
    else:
        row["current_duty_id"] = {"prose": "problem", "wrong_section": "A1", "empty": ""}[damage]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="EDIT"):
        _admit(case)


def test_explicit_correction_can_merge_two_prior_guards_into_one_compound_guard():
    correction = (
        "Merge the approval safeguards into a single guard: before approval, "
        "access must remain open and edits must remain locked."
    )
    source, ledger, context, _, decisions = _edit_case(correction, include_second_guard=True)
    prior_before = deepcopy(context["prior_lifecycle"])
    ledger["conditional_guards"] = [{
        "id": "G1", "source_refs": [{"quote": correction, "context": correction}],
        "trigger": "before approval", "protected_action": "approval",
        "rule": "access must remain open and edits must remain locked",
    }]
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    decisions["verifier_task_sha256"] = task["verifier_task_sha256"]
    decisions["decisions"] = _yes_decisions(preflight, evidence_text=source)["decisions"]
    for key in (GUARD_KEY, "conditional_guards/G2"):
        decisions["edit_preservation"][key] = {
            "verdict": "changed", "current_duty_id": "G1", "correction_authorization": "yes",
        }
    receipt = _admit((source, ledger, context, task, decisions))
    assert receipt["ledger"]["conditional_guards"] == ledger["conditional_guards"]
    assert len(receipt["ledger"]["conditional_guards"]) == 1
    assert [row["rule"] for row in prior_before["conditional_guards"]] == [
        "access must remain open", "edits must remain locked",
    ]
    assert receipt["decision_set"]["edit_preservation"] == decisions["edit_preservation"]
    assert context["prior_lifecycle"] == prior_before


@pytest.mark.parametrize("verdict", ["no", "uncertain"])
def test_a_preservation_yes_cannot_override_a_negative_ordinary_duty(verdict):
    case = _edit_case()
    case[-1]["decisions"]["G1"]["verdict"] = verdict
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="not affirmative"):
        _admit(case)


@pytest.mark.parametrize("verdict,correction", [
    ("changed", "Change the approval guard: access may be closed during approval."),
    ("removed", "Remove the requirement that access remain open before approval."),
])
def test_explicit_correction_can_change_or_remove_a_prior_duty(verdict, correction):
    case = _edit_case(correction, include_guard=verdict == "changed")
    source, ledger, context, _, decisions = case
    if verdict == "changed":
        ledger["conditional_guards"][0].update(
            rule="access may be closed during approval",
            source_refs=[{"quote": correction, "context": correction}],
        )
        preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
        task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
        decisions["verifier_task_sha256"] = task["verifier_task_sha256"]
    decisions["edit_preservation"][GUARD_KEY] = {
        "verdict": verdict, "current_duty_id": "G1" if verdict == "changed" else "",
        "correction_authorization": "yes",
    }
    receipt = _admit(case)
    assert receipt["ledger"]["conditional_guards"] == ledger["conditional_guards"]
    assert context["prior_lifecycle"]["conditional_guards"][0]["rule"] == "access must remain open"


@pytest.mark.parametrize("damage", ["no", "uncertain", "missing", "boolean", "preserved_yes", "removed_not_required", "legacy_field"])
def test_override_requires_an_explicit_per_prior_correction_authorization(damage):
    case = _edit_case()
    row = case[-1]["edit_preservation"][GUARD_KEY]
    row.update(verdict="removed", current_duty_id="", correction_authorization="yes")
    if damage in {"no", "uncertain"}:
        row["correction_authorization"] = damage
    elif damage == "missing":
        del row["correction_authorization"]
    elif damage == "boolean":
        row["correction_authorization"] = True
    elif damage == "preserved_yes":
        row.update(verdict="preserved", current_duty_id="G1")
    elif damage == "removed_not_required":
        row["correction_authorization"] = "not_required"
    else:
        row["correction_ref_indexes"] = [0]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="EDIT"):
        _admit(case)


@pytest.mark.parametrize("damage", ["lifecycle", "correction", "source", "task", "receipt", "prior_hash"])
def test_edit_baseline_correction_task_and_receipt_cannot_drift(damage):
    case = _edit_case()
    source, _, context, _, decisions = case
    receipt = _admit(case)
    if damage == "task":
        decisions["verifier_task_sha256"] = "0" * 64
        with pytest.raises(GreenfieldSourceDutyLedgerError, match="binding"):
            _admit(case)
        return
    if damage == "receipt":
        changed = deepcopy(receipt)
        changed["decision_set_sha256"] = "0" * 64
        with pytest.raises(GreenfieldSourceDutyLedgerError, match="hash"):
            verify_greenfield_source_duty_ledger_receipt(changed, evidence_text=source, edit_preservation=context)
        return
    if damage == "prior_hash":
        other_baseline = deepcopy(context)
        other_baseline["transaction_hash"] = "b" * 64
        with pytest.raises(GreenfieldSourceDutyLedgerError, match="baseline"):
            verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source, edit_preservation=other_baseline)
        return
    if damage == "lifecycle":
        context["prior_lifecycle"]["conditional_guards"][0]["rule"] = "no guard"
    elif damage == "correction":
        context["correction_sha256"] = "0" * 64
    else:
        context["source_sha256"] = "0" * 64
    with pytest.raises((GreenfieldSourceDutyLedgerError, GreenfieldSourceDutyEntailmentError), match="EDIT"):
        _admit(case)


def test_manual_edit_preflight_cannot_omit_prior_hash_before_file_or_candidate_work(tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("No input file, candidate, proposal or terminal work is permitted after custody refusal")
    monkeypatch.setattr(cli, "load_greenfield_source_duty_file", forbidden)
    monkeypatch.setattr(cli, "_compile_prompt_evidence_transaction", forbidden)
    assert cli.main([
        "source-ledger-check", "--repo-root", str(tmp_path), "--prompt", "A reviewer opens a record.",
        "--edit", ADDITIVE, "--ledger-file", str(tmp_path / "unread.json"),
    ]) == 2
    assert "prior transaction hash" in json.loads(capsys.readouterr().out)["error"]


def test_existing_parent_refuses_missing_prior_guard_before_candidate_or_proposal(tmp_path, monkeypatch):
    import subprocess
    from pathlib import Path
    from odylith.runtime.domain_intelligence import greenfield_host_flow as host
    from odylith.runtime.domain_intelligence.greenfield_authority_gate import greenfield_authority_gate_contract
    from odylith.runtime.domain_intelligence.greenfield_host_candidate import greenfield_host_candidate_contract
    from odylith.runtime.domain_intelligence.greenfield_source_duty_compact import expand_compact_source_duty_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow

    source, ledger, context, _, decisions = _edit_case(include_guard=False)
    decisions["edit_preservation"][GUARD_KEY].update(verdict="missing", current_duty_id="")
    prompt = _case("dossier")[0] + " " + GUARD
    contract = greenfield_host_candidate_contract(source, edit_preservation=context)
    contract["authority_gate"] = greenfield_authority_gate_contract(
        prompt=prompt, edit_evidence=ADDITIVE, evidence_source=source,
    )
    flow, _, _, _, proposals, repo = _flow(tmp_path, contract={"version": "unused"}, candidate={})
    calls, installed = [], []
    gate = {"decision": "admit", "required_fields": [], "owner_quote": "steward",
            "task_quote": "opens the dossier", "result_quote": "the dossier", "question": ""}

    def invoke_installed(command, timeout):
        installed.append(list(command))
        if "candidate-contract" in command:
            result = contract
        elif "authority-check" in command:
            result = {"mode": "authority_admitted", "gate": gate}
        else:
            assert "source-ledger-check" in command
            assert command[command.index("--transaction-hash") + 1] == context["transaction_hash"]
            assert command[command.index("--completion-receipt") + 1] == "delivered-receipt.json"
            raw = json.loads(Path(command[command.index("--ledger-file") + 1]).read_text())
            current = expand_compact_source_duty_ledger(raw, evidence_text=source)
            preflight = preflight_greenfield_source_duty_ledger(current, evidence_text=source)
            if "--decision-file" not in command:
                result = {"mode": "source_duty_preflight", "preflight": preflight,
                          "decision_task": source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)}
            else:
                with pytest.raises(GreenfieldSourceDutyLedgerError, match="not affirmative"):
                    validate_greenfield_source_duty_ledger(
                        current, evidence_text=source, decision_set=decisions, edit_preservation=context,
                    )
                return subprocess.CompletedProcess(command, 2, stdout=json.dumps({"mode": "error", "error": "EDIT guard is missing"}), stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(result), stderr="")

    def invoke_host(command, **kwargs):
        name = Path(command[command.index("--output-schema") + 1]).name
        calls.append(name)
        assert name != "candidate-schema.json", "Refusal cannot invoke candidate authoring"
        result = {"authority-gate-schema.json": gate,
                  "source-ledger-schema.json": compact_source_duty_view(ledger),
                  "source-duty-decision-schema.json": decisions}[name]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(result), stderr="")

    monkeypatch.setattr(host, "_invoke_host", invoke_host)
    flow = host.HostCandidateFlow(**{
        **flow.__dict__, "prompt": prompt, "edit_evidence": ADDITIVE, "timeout": 315,
        "transaction_hash": context["transaction_hash"], "completion_receipt": "delivered-receipt.json",
        "invoke_installed": invoke_installed,
    })
    with pytest.raises(host.HostCandidateFlowError, match="decision check returned nonzero"):
        host.run_host_candidate_flow(flow)
    assert calls == ["authority-gate-schema.json", "source-ledger-schema.json", "source-duty-decision-schema.json"]
    assert flow.observation_sink["candidate_host_invocations"] == flow.observation_sink["proposal_command_invocations"] == 0
    assert proposals == [] and list(repo.iterdir()) == []


def _stage_transaction_custody(transaction, *, repo_root, bounded):
    from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
    from odylith.runtime.domain_intelligence import greenfield_process as process

    if not bounded:
        return pending.stage_pending_transaction(repo_root=repo_root, transaction=transaction), ""
    import os
    import sys
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import write_compiled_product_create_transaction_file

    # The real guardian registers seals from its inherited child channel.
    source = repo_root / ".odylith/runtime/greenfield/test-stage" / (transaction.transaction_hash + ".json")
    source.parent.mkdir(parents=True, exist_ok=True)
    write_compiled_product_create_transaction_file(source, transaction)
    command = [sys.executable, "-c", (
        "import sys\n"
        "from pathlib import Path\n"
        "from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file\n"
        "from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import stage_pending_transaction\n"
        "transaction = load_compiled_product_create_transaction_file(Path(sys.argv[1]))\n"
        "stage_pending_transaction(repo_root=Path(sys.argv[2]), transaction=transaction)\n"
    ), str(source), str(repo_root)]
    delivered = {}
    with process.supervise_greenfield_journey(seconds=30, completion_receipt_sink=delivered):
        result = process.run_command_with_group_timeout(
            cwd=repo_root, env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
            command=command, timeout=20,
        )
        assert result.returncode == 0, result.stderr
    assert delivered["transaction_hash"] == transaction.transaction_hash
    completion = pending.write_completion_receipt_delivery(repo_root=repo_root, receipt=delivered)
    path = pending.resolve_pending_transaction(
        repo_root=repo_root, transaction_hash=transaction.transaction_hash, completion_receipt=completion,
    )
    return path, completion


@pytest.mark.parametrize("bounded", [True, False])
def test_edit_custody_uses_real_compiler_and_existing_bounded_receipt_policy(tmp_path, bounded, capsys):
    from tests.unit.runtime.test_greenfield_create_transaction import _transaction

    transaction = _transaction(repo_root=tmp_path)
    path, completion = _stage_transaction_custody(transaction, repo_root=tmp_path, bounded=bounded)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    args = argparse.Namespace(transaction_hash=transaction.transaction_hash, completion_receipt=str(completion))
    previous = cli._edit_transaction_from_args(args, repo_root=tmp_path, correction=ADDITIVE)
    assert previous.transaction_hash == transaction.transaction_hash
    prompt = previous.proposal["intent"]["prompt"]
    source = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=ADDITIVE).evidence_source
    context = cli._edit_preservation(previous, correction=ADDITIVE, evidence_text=source)
    assert context["prior_lifecycle"] == previous.proposal["semantic_model"]["source_lifecycle"]
    # --prompt means the exact retained prior source, never its new combined frame.
    assert cli.main([
        "source-ledger-check", "--repo-root", str(tmp_path), "--prompt", source,
        "--transaction-hash", transaction.transaction_hash, "--completion-receipt", str(completion),
        "--edit", ADDITIVE, "--ledger-file", str(tmp_path / "must-not-be-read.json"),
    ]) == 2
    assert "does not match the prior sealed request" in json.loads(capsys.readouterr().out)["error"]
    # An initial receipt over the same complete source cannot enter the EDIT lane.
    ledger = previous.proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["ledger"]
    old_receipt = synthetic_source_duty_receipt_for_ledger(ledger, evidence_text=source)
    old_path = tmp_path / "initial-receipt.json"
    old_path.write_text(json.dumps(old_receipt))
    args.ledger_file = str(old_path)
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="baseline"):
        cli._source_duty_receipt_from_args(args, repo_root=tmp_path, prompt=prompt, edit_evidence=ADDITIVE)
    if bounded:
        wrong_path = tmp_path / "wrong-completion.json"
        wrong = json.loads(completion.read_text())
        wrong["transaction_hash"] = "0" * 64
        wrong_path.write_text(json.dumps(wrong))
        args.completion_receipt = str(wrong_path)
        with pytest.raises(ValueError, match="delivered --completion-receipt"):
            cli._edit_transaction_from_args(args, repo_root=tmp_path, correction=ADDITIVE)
    args.completion_receipt = ""
    if bounded:
        with pytest.raises(ValueError, match="delivered --completion-receipt"):
            cli._edit_transaction_from_args(args, repo_root=tmp_path, correction=ADDITIVE)
    else:
        assert cli._edit_transaction_from_args(args, repo_root=tmp_path, correction=ADDITIVE).transaction_hash == transaction.transaction_hash
    args.completion_receipt = str(completion)
    args.transaction_hash = "0" * 64
    with pytest.raises(ValueError):
        cli._edit_transaction_from_args(args, repo_root=tmp_path, correction=ADDITIVE)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original


@pytest.mark.parametrize("bounded", [True, False])
def test_fresh_v9_compiler_seal_can_be_read_and_used_for_a_second_edit(tmp_path, bounded):
    from odylith.runtime.domain_intelligence import greenfield_proposals
    from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import _model_authoring_manifest
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        build_product_create_transaction,
        load_compiled_product_create_transaction_file,
    )
    from odylith.runtime.domain_intelligence.greenfield_host_candidate_materialization import materialize_host_authored_intent
    from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import _REPEATED_SOURCE_FIELDS, _SINGULAR_SOURCE_FIELDS
    from tests.unit.runtime.greenfield_authored_proposal_fixtures import approved_authored_quality_manifest_fixture
    from tests.unit.runtime.greenfield_model_authoring_fixtures import authored_response, host_candidate_response, synthetic_source_duty_receipt
    from tests.unit.runtime.test_greenfield_create_transaction import _package, _transaction

    sealed = []

    def stage(transaction):
        path, completion = _stage_transaction_custody(transaction, repo_root=tmp_path, bounded=bounded)
        sealed.append((path, path.read_bytes()))
        args = argparse.Namespace(transaction_hash=transaction.transaction_hash, completion_receipt=str(completion))
        return path, args

    initial = _transaction(repo_root=tmp_path)
    initial_source_duty = initial.proposal["intent"]["authored_semantics"]["source_duty"]
    assert initial_source_duty["ledger_receipt"]["version"] == "odylith.greenfield.source-duty-ledger-receipt.v7"
    assert initial_source_duty["ledger_receipt"]["decision_set"]["version"] == "odylith.greenfield.source-duty-decisions.v4"
    _, args = stage(initial)
    guard = "Before a decision, supplier evidence must remain visible."
    for edit_index, correction in enumerate((guard, "Keep every earlier safeguard and its evidence.")):
        previous = cli._edit_transaction_from_args(args, repo_root=tmp_path, correction=correction)
        prior_source_duty = previous.proposal["intent"]["authored_semantics"]["source_duty"]
        prior_version = "odylith.greenfield.source-duty-ledger-receipt.v7" if edit_index == 0 else "odylith.greenfield.source-duty-ledger-receipt.v9"
        assert prior_source_duty["ledger_receipt"]["version"] == prior_version
        prompt = previous.proposal["intent"]["prompt"]
        prepared = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=correction)
        source = prepared.evidence_source
        context = cli._edit_preservation(previous, correction=correction, evidence_text=source)
        prior = previous.proposal["intent"]
        semantics = prior["authored_semantics"]
        facts = {field: deepcopy(prior[field]) for field in (
            *_SINGULAR_SOURCE_FIELDS, *_REPEATED_SOURCE_FIELDS,
            "assumptions", "ambiguities", "component_responsibilities",
        ) if field in prior}
        host_candidate = host_candidate_response(authored_response(
            facts, evidence_text=source,
            first_path_relations=semantics["first_path_relations"],
            component_responsibility_owners=[
                row["owner_system_quote"] for row in semantics["component_responsibility_relations"]
            ],
            provisional_design=semantics["provisional_design"],
        ), evidence_text=source)
        ledger = synthetic_source_duty_receipt(host_candidate, evidence_text=source)["ledger"]
        ledger["conditional_guards"] = [{
            "id": "supplier-evidence-visible", "source_refs": [{"quote": guard, "context": guard}],
            "trigger": "before a decision", "protected_action": "records a decision",
            "rule": "supplier evidence must remain visible",
        }]
        preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
        task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
        decisions = _yes_decisions(preflight, evidence_text=source)
        decisions.update(
            version=EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
            verifier_task_sha256=task["verifier_task_sha256"],
            edit_preservation={
                f"{section}/{row['duty_id']}": {
                    "verdict": "preserved", "current_duty_id": row["duty_id"], "correction_authorization": "not_required",
                }
                for section in ("state_fields", "off_path_transitions", "conditional_guards", "boundaries", "proof_duties")
                for row in context["prior_lifecycle"][section]
            },
        )
        receipt = validate_greenfield_source_duty_ledger(
            ledger, evidence_text=source, decision_set=decisions, edit_preservation=context,
        )
        assert receipt["version"] == "odylith.greenfield.source-duty-ledger-receipt.v9"
        assert receipt["decision_set"]["version"] == EDIT_SOURCE_DUTY_DECISION_SET_VERSION
        result = host_candidate["result"]
        result["source_duty_binding"].update(
            source_sha256=receipt["source_sha256"], ledger_sha256=receipt["ledger_sha256"],
            conditional_guards=[{
                "duty_id": "supplier-evidence-visible",
                "component_key": result["provisional_design"]["components"][0]["key"],
                "workstream_key": result["provisional_design"]["workstreams"][0]["key"],
            }],
        )
        authoring_receipt = {}
        intent = materialize_host_authored_intent(
            prompt=prompt, repo_root=tmp_path, host_candidate=host_candidate,
            source_duty_receipt=receipt, edit_evidence=correction,
            prepared_evidence=prepared, authoring_receipt=authoring_receipt,
        )
        proposal = greenfield_proposals.build_greenfield_proposal(
            repo_root=tmp_path, prompt=prompt, release_selector="0.0.1",
            confirmed_intent=intent, require_completion_ready=False,
        )
        authority = intent["product_intent_authority"]
        proposal["product_intent_authority"] = authority
        package = _package(proposal, repo_root=tmp_path)
        transaction = build_product_create_transaction(
            proposal=proposal, release_selector="0.0.1", validation_gate={"status": "passed", "issues": []},
            prewrite_package=package, backlog_result=package.backlog_result or {},
            intent_authority=authority, repo_root=tmp_path,
            quality_manifest=approved_authored_quality_manifest_fixture(
                intent_authority=authority, proposal=proposal, model_authoring=_model_authoring_manifest(authoring_receipt),
            ),
        )
        path, args = stage(transaction)
        passive = load_compiled_product_create_transaction_file(path)
        loaded = cli._edit_transaction_from_args(args, repo_root=tmp_path, correction="Keep the safeguards.")
        assert passive.transaction_hash == loaded.transaction_hash == transaction.transaction_hash
        source_duty = loaded.proposal["intent"]["authored_semantics"]["source_duty"]
        assert source_duty["ledger_receipt"] == receipt
        assert source_duty["lifecycle"] == loaded.proposal["semantic_model"]["source_lifecycle"]
        assert source_duty["lifecycle"]["conditional_guards"][0]["rule"] == "supplier evidence must remain visible"
        assert receipt["edit_preservation"]["transaction_hash"] == previous.transaction_hash
        if edit_index:
            assert set(decisions["edit_preservation"]) == {"conditional_guards/supplier-evidence-visible"}
    assert all(path.read_bytes() == original for path, original in sealed)
