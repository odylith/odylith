"""Exact correction custody and passive compiler goldens for fresh EDIT v6."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    admit_greenfield_host_candidate,
    greenfield_host_candidate_authoring_request,
    greenfield_host_candidate_contract,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import (
    source_duty_entailment_task,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    GreenfieldSourceDutyLedgerError,
    preflight_greenfield_source_duty_ledger,
    validate_greenfield_source_duty_ledger,
    verify_greenfield_source_duty_ledger_receipt,
)
from tests.unit.runtime.test_greenfield_edit_lifecycle_preservation import (
    GUARD_KEY, _admit, _edit_case,
)


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures/greenfield-edit-authorization"
GOLDEN_HASHES = {
    "initial-v4-v7.json": "470939302fe338a3c240a9016254767e15ff0dae8782124bf933deae724ddd43",
    "edit-v5-v8.json": "bc3eea3c8081b9adda1d9a9882edf81d3cd5e3f9e642ac3a4ca1368c988c305e",
    "legacy-v8-pct.json": "39546111c3eda9f3e258894665c053408d8962f0da26f3ec765d7d50823cf6fa",
    "legacy-v8-pct.json.compiler-receipt.v1.json": "0f06526a664b960b14fee4ebdc90423f4afbf3b29113728f69b5ffcfa56ceac6",
}


def _golden(name):
    raw = (FIXTURES / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_HASHES[name]
    return json.loads(raw)


@pytest.mark.parametrize("name", ["initial-v4-v7.json", "edit-v5-v8.json"])
def test_frozen_compiler_task_and_receipt_rebuild_exactly(name):
    golden = _golden(name)
    receipt, source = golden["receipt"], golden["source"]
    context = golden.get("context")
    task = source_duty_entailment_task(
        preflight_greenfield_source_duty_ledger(
            receipt["ledger"], evidence_text=source, _passive_source_version="odylith.greenfield.source-duty-ledger.v5",
        ),
        evidence_text=source, edit_preservation=context,
        _passive_legacy_edit=context is not None,
    )
    assert task == golden["task"]
    assert json.dumps(task, ensure_ascii=False, sort_keys=True) == json.dumps(
        golden["task"], ensure_ascii=False, sort_keys=True,
    )
    assert verify_greenfield_source_duty_ledger_receipt(
        receipt, evidence_text=source, edit_preservation=context,
    ) == receipt


def test_fresh_admission_cannot_select_legacy_profile_from_model_version():
    golden = _golden("edit-v5-v8.json")
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="^Fresh EDIT requires authenticated action and roster baselines$"):
        validate_greenfield_source_duty_ledger(
            golden["receipt"]["ledger"], evidence_text=golden["source"],
            decision_set=golden["receipt"]["decision_set"], edit_preservation=golden["context"],
        )


@pytest.mark.parametrize("entrypoint", ["request", "admission"])
def test_fresh_candidate_entrypoints_refuse_valid_passive_v8_receipt(entrypoint):
    golden = _golden("edit-v5-v8.json")
    assert verify_greenfield_source_duty_ledger_receipt(
        golden["receipt"], evidence_text=golden["source"],
    ) == golden["receipt"]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="version"):
        if entrypoint == "request":
            greenfield_host_candidate_authoring_request(
                greenfield_host_candidate_contract(golden["source"], edit_preservation=golden["context"]),
                source_duty_receipt=golden["receipt"], authority_admission={},
            )
        else:
            admit_greenfield_host_candidate(
                {}, evidence_text=golden["source"], source_duty_receipt=golden["receipt"],
            )


@pytest.mark.parametrize("receipt_version,decision_version", [
    ("v8", "v6"), ("v9", "v5"), ("v7", "v5"), ("v10", "v6"),
])
def test_passive_edit_receipt_and_decision_versions_are_closed(receipt_version, decision_version):
    golden = _golden("edit-v5-v8.json")
    receipt = deepcopy(golden["receipt"])
    receipt["version"] = "odylith.greenfield.source-duty-ledger-receipt." + receipt_version
    receipt["decision_set"]["version"] = "odylith.greenfield.source-duty-decisions." + decision_version
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="version|binding|malformed"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=golden["source"])


@pytest.mark.parametrize("damage", ["outside_correction", "ambiguous_context", "unused", "duplicate", "index"])
def test_legacy_passive_citation_checks_remain_strict(damage):
    golden = _golden("edit-v5-v8.json")
    receipt = deepcopy(golden["receipt"])
    decisions = receipt["decision_set"]
    correction = golden["context"]["correction"]
    decisions["edit_preservation"][GUARD_KEY].update(
        verdict="removed", current_duty_id="", correction_ref_indexes=[0],
    )
    decisions["edit_correction_refs"] = [{"quote": correction, "context": correction}]
    if damage == "outside_correction":
        decisions["edit_correction_refs"] = [{"quote": "Before approval", "context": "Before approval"}]
    elif damage == "ambiguous_context":
        decisions["edit_correction_refs"] = [{"quote": "approval", "context": "status"}]
    elif damage == "unused":
        decisions["edit_preservation"][GUARD_KEY].update(
            verdict="preserved", current_duty_id="G1", correction_ref_indexes=[],
        )
    elif damage == "duplicate":
        decisions["edit_correction_refs"] *= 2
    else:
        decisions["edit_preservation"][GUARD_KEY]["correction_ref_indexes"] = [1]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="EDIT"):
        verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=golden["source"])


@pytest.mark.parametrize("padding", ["x" * 5000, "界🙂e\u0301" * 1000], ids=["long_ascii", "long_unicode"])
def test_whole_correction_exceeding_quote_limit_retains_exact_utf8_authority(padding):
    correction = "Remove the requirement that access remain open before approval.\n" + padding
    case = _edit_case(correction, include_guard=False)
    source, _, context, task, decisions = case
    decisions["edit_preservation"][GUARD_KEY].update(
        verdict="removed", current_duty_id="", correction_authorization="yes",
    )
    receipt = _admit(case)
    exact = correction.encode("utf-8")
    authority = source.encode("utf-8")
    start = len(authority) - len(exact) - 1
    assert len(correction) > 2400 and len(authority) <= 65536
    assert authority[start:start + len(exact)] == exact
    assert task["edit_preservation"]["correction"] == correction
    assert receipt["edit_preservation"]["correction_sha256"] == hashlib.sha256(exact).hexdigest()
    assert receipt["edit_preservation"] == context
    assert "edit_correction_refs" not in task["decision_set_schema"]["properties"]
    assert "correction_ref_indexes" not in task["decision_set_schema"]["properties"]["edit_preservation"]["properties"][GUARD_KEY]["properties"]
    assert verify_greenfield_source_duty_ledger_receipt(receipt, evidence_text=source) == receipt


@pytest.mark.parametrize("damage", ["wrong_carrier", "removed_carrier", "missing_prior"])
def test_authorization_yes_cannot_bypass_typed_or_complete_preservation_laws(damage):
    case = _edit_case("Remove the approval access guard.")
    rows = case[-1]["edit_preservation"]
    rows[GUARD_KEY].update(verdict="changed", correction_authorization="yes")
    if damage == "wrong_carrier":
        rows[GUARD_KEY]["current_duty_id"] = "F1"
    elif damage == "removed_carrier":
        rows[GUARD_KEY]["verdict"] = "removed"
    else:
        del rows["state_fields/F1"]
    with pytest.raises(GreenfieldSourceDutyLedgerError, match="EDIT"):
        _admit(case)


def test_source_only_task_requires_explicit_authorization_for_each_prior_meaning():
    task = _edit_case()[-2]
    instruction = task["edit_preservation_task"]
    assert "For EACH changed or removed prior duty" in instruction
    assert "general preservation language" in instruction
    assert "Return no or uncertain authorization when unsupported" in instruction
    assert "requires a separate judgment for every prior meaning" in instruction
    # These are verifier obligations. Mechanical custody does not prove a yes true.


def test_real_legacy_v8_pct_preserves_passive_custody_and_refuses_changed_writer(tmp_path):
    from odylith.runtime.domain_intelligence import greenfield_commit_transaction as commit
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
        build_product_create_transaction, load_compiled_product_create_transaction_file,
    )

    path = FIXTURES / "legacy-v8-pct.json"
    _golden(path.name)
    receipt = _golden(path.name + ".compiler-receipt.v1.json")
    receipt_path = path.with_name(path.name + ".compiler-receipt.v1.json")
    before = path.read_bytes()
    receipt_before = receipt_path.read_bytes()
    transaction = load_compiled_product_create_transaction_file(path)
    source_duty = transaction.proposal["intent"]["authored_semantics"]["source_duty"]
    assert source_duty["ledger_receipt"]["version"] == "odylith.greenfield.source-duty-ledger-receipt.v8"
    assert transaction.quality_manifest["model_authoring"]["host_candidate"]["contract_version"] == "odylith.greenfield.host-candidate-contract.v50"
    with pytest.raises(ValueError, match="source-duty hashes"):
        build_product_create_transaction(
            proposal=transaction.proposal, release_selector=transaction.release_selector,
            validation_gate=transaction.validation_gate, prewrite_package=transaction.prewrite_package,
            backlog_result=transaction.backlog_result, intent_authority=transaction.intent_authority,
            quality_manifest=transaction.quality_manifest, repo_root=tmp_path,
        )
    assert receipt["post_confirm_runtime_identity"] != commit.build_product_create_transaction_compiler_identity()
    with pytest.raises(ValueError, match="post-confirm runtime changed"):
        commit.load_sealed_product_create_commit(path)
    assert path.read_bytes() == before
    assert receipt_path.read_bytes() == receipt_before
    assert list(tmp_path.iterdir()) == []
