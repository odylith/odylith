"""Canonical host-receipt custody for Greenfield transaction approval."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
    approved_authored_quality_manifest_fixture,
)


def test_materialized_host_receipt_binds_the_sealed_authority(tmp_path: Path) -> None:
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
    receipt = proposal["_test_model_authoring_receipt"]
    authority = proposal[PRODUCT_INTENT_AUTHORITY_KEY]

    assert receipt["authoring_origin"] == "host_native"
    assert receipt["runtime_semantic_model_call_count"] == 0
    assert receipt["host_candidate"]["canonical_candidate_sha256"] == authority[
        "canonical_candidate_sha256"
    ]
    assert receipt["canonical_authority"] == {
        "canonical_candidate_sha256": authority["canonical_candidate_sha256"],
        "source_sha256": authority["markdown_source_sha256"],
        "product_facts_sha256": authority["product_facts_sha256"],
        AUTHORED_RELATION_SET_SHA256_KEY: authority[
            AUTHORED_RELATION_SET_SHA256_KEY
        ],
    }


def test_current_host_receipt_is_quality_approved() -> None:
    greenfield_create_transaction.require_product_create_transaction_quality_approved(
        approved_authored_quality_manifest_fixture()
    )


@pytest.mark.parametrize(
    ("surface", "field", "value"),
    (
        ("model_authoring", "runtime_semantic_model_call_count", 1),
        ("model_authoring", "runtime_semantic_model_call_count", False),
        ("model_authoring", "runtime_semantic_model_call_count", 0.0),
        ("host_candidate", "canonical_candidate_sha256", "f" * 64),
        ("host_candidate", "source_sha256", "f" * 64),
        ("canonical_authority", "product_facts_sha256", "not-a-hash"),
        ("semantic_compiler", "post_candidate_receipt_semantic_calls", 1),
        ("semantic_compiler", "post_candidate_receipt_semantic_calls", False),
        ("semantic_compiler", "post_candidate_receipt_semantic_calls", 0.0),
    ),
)
def test_host_receipt_tampering_fails_closed(
    surface: str,
    field: str,
    value: object,
) -> None:
    manifest = approved_authored_quality_manifest_fixture()
    if surface in {"host_candidate", "canonical_authority"}:
        target = manifest["model_authoring"][surface]
    else:
        target = manifest[surface]
    target[field] = value

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            manifest
        )


def test_host_receipt_rejects_unknown_compatibility_field() -> None:
    manifest = approved_authored_quality_manifest_fixture()
    tampered = deepcopy(manifest)
    tampered["model_authoring"]["legacy_second_authority"] = {"status": "admitted"}

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        greenfield_create_transaction.require_product_create_transaction_quality_approved(
            tampered
        )
