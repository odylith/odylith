"""Commit-time source-duty receipt parity for sealed Greenfield transactions."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction
from tests.unit.runtime.test_greenfield_transaction_provenance import _transaction
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_RECEIPT_VERSION,
)


@pytest.mark.parametrize(
    ("contract", "receipt", "passive", "expected_error"),
    (
        (53, 9, False, "EDIT preservation context is malformed"),
        (53, 9, True, "EDIT preservation context is malformed"),
        (52, 9, True, None),
        (51, 9, True, None),
        (50, 8, True, None),
        (52, 9, False, "source-duty hashes do not match"),
        (50, 8, False, "source-duty hashes do not match"),
        (50, 9, True, "source-duty hashes do not match"),
        (52, 8, True, "source-duty hashes do not match"),
        (49, 9, True, "source-duty hashes do not match"),
        (54, 9, True, "source-duty hashes do not match"),
    ),
)
def test_edit_custody_preserves_closed_pairs_and_current_context_validation(
    tmp_path: Path, contract: int, receipt: int, passive: bool, expected_error: str | None,
) -> None:
    transaction = _transaction(tmp_path)
    proposal = copy.deepcopy(transaction.proposal)
    quality = copy.deepcopy(transaction.quality_manifest)
    ledger = proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]
    ledger["version"] = f"odylith.greenfield.source-duty-ledger-receipt.v{receipt}"
    ledger["edit_preservation"] = {}
    quality["model_authoring"]["host_candidate"]["contract_version"] = (
        f"odylith.greenfield.host-candidate-contract.v{contract}"
    )
    if expected_error is None:
        greenfield_create_transaction._require_host_candidate_authority_binding(
            quality, transaction.intent_authority, proposal=proposal, passive=passive,
        )
    else:
        with pytest.raises(ValueError, match=expected_error):
            greenfield_create_transaction._require_host_candidate_authority_binding(
                quality, transaction.intent_authority, proposal=proposal, passive=passive,
            )


@pytest.mark.parametrize(
    ("receipt_field", "sealed_field"),
    (
        ("source_duty_ledger_sha256", "ledger_sha256"),
        ("source_duty_verifier_task_sha256", "verifier_task_sha256"),
        ("source_duty_decision_set_sha256", "decision_set_sha256"),
        ("source_duty_binding_sha256", "binding_sha256"),
    ),
)
def test_commit_time_host_receipt_requires_source_duty_hash_parity(
    tmp_path: Path, receipt_field: str, sealed_field: str,
) -> None:
    transaction = _transaction(tmp_path)
    authority = copy.deepcopy(transaction.intent_authority)
    quality_manifest = copy.deepcopy(transaction.quality_manifest)
    proposal = copy.deepcopy(transaction.proposal)
    host_receipt = quality_manifest["model_authoring"]["host_candidate"]
    original_hash = host_receipt[receipt_field]

    greenfield_create_transaction._require_host_candidate_authority_binding(  # noqa: SLF001
        quality_manifest, authority, proposal=proposal,
    )
    if receipt_field == "source_duty_ledger_sha256":
        proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["version"] = (
            "odylith.greenfield.source-duty-ledger-receipt.v5"
        )
        with pytest.raises(ValueError, match="source-duty hashes do not match"):
            greenfield_create_transaction._require_host_candidate_authority_binding(  # noqa: SLF001
                quality_manifest, authority, proposal=proposal,
            )
        proposal["intent"]["authored_semantics"]["source_duty"]["ledger_receipt"]["version"] = (
            SOURCE_DUTY_LEDGER_RECEIPT_VERSION
        )
    host_receipt[receipt_field] = "0" * 64
    with pytest.raises(ValueError, match="source-duty hashes do not match"):
        greenfield_create_transaction._require_host_candidate_authority_binding(  # noqa: SLF001
            quality_manifest, authority, proposal=proposal,
        )
    host_receipt[receipt_field] = original_hash
    location = "lifecycle" if sealed_field == "binding_sha256" else "ledger_receipt"
    proposal["intent"]["authored_semantics"]["source_duty"][location][sealed_field] = "0" * 64
    with pytest.raises(ValueError, match="source-duty hashes do not match"):
        greenfield_create_transaction._require_host_candidate_authority_binding(  # noqa: SLF001
            quality_manifest, authority, proposal=proposal,
        )
