"""Commit-time source-duty receipt parity for sealed Greenfield transactions."""

from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_FACTS_HASH_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    CANONICAL_CANDIDATE_SHA256_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import (
    SOURCE_DUTY_LEDGER_RECEIPT_VERSION,
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
    receipt_field: str, sealed_field: str,
) -> None:
    authority = {
        "markdown_source_sha256": "a" * 64,
        CANONICAL_CANDIDATE_SHA256_KEY: "b" * 64,
        PRODUCT_FACTS_HASH_KEY: "c" * 64,
        AUTHORED_RELATION_SET_SHA256_KEY: "d" * 64,
    }
    host_receipt = {
        "source_sha256": authority["markdown_source_sha256"],
        "canonical_candidate_sha256": authority[CANONICAL_CANDIDATE_SHA256_KEY],
        "source_duty_ledger_sha256": "e" * 64,
        "source_duty_verifier_task_sha256": "8" * 64,
        "source_duty_decision_set_sha256": "7" * 64,
        "source_duty_binding_sha256": "f" * 64,
    }
    quality_manifest = {"model_authoring": {
        "runtime_semantic_model_call_count": 0,
        "host_candidate": host_receipt,
        "canonical_authority": {
            "source_sha256": authority["markdown_source_sha256"],
            "canonical_candidate_sha256": authority[CANONICAL_CANDIDATE_SHA256_KEY],
            "product_facts_sha256": authority[PRODUCT_FACTS_HASH_KEY],
            AUTHORED_RELATION_SET_SHA256_KEY: authority[AUTHORED_RELATION_SET_SHA256_KEY],
        },
    }}
    proposal = {"intent": {"authored_semantics": {"source_duty": {
        "ledger_receipt": {
            "version": SOURCE_DUTY_LEDGER_RECEIPT_VERSION,
            "source_sha256": authority["markdown_source_sha256"],
            "ledger_sha256": host_receipt["source_duty_ledger_sha256"],
            "verifier_task_sha256": host_receipt["source_duty_verifier_task_sha256"],
            "decision_set_sha256": host_receipt["source_duty_decision_set_sha256"],
        },
        "lifecycle": {"binding_sha256": host_receipt["source_duty_binding_sha256"]},
    }}}}

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
    host_receipt[receipt_field] = {
        "ledger_sha256": "e" * 64,
        "verifier_task_sha256": "8" * 64,
        "decision_set_sha256": "7" * 64,
        "binding_sha256": "f" * 64,
    }[sealed_field]
    location = "lifecycle" if sealed_field == "binding_sha256" else "ledger_receipt"
    proposal["intent"]["authored_semantics"]["source_duty"][location][sealed_field] = "0" * 64
    with pytest.raises(ValueError, match="source-duty hashes do not match"):
        greenfield_create_transaction._require_host_candidate_authority_binding(  # noqa: SLF001
            quality_manifest, authority, proposal=proposal,
        )
