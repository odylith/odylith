"""Product Intent custody checks for installed Greenfield matrix scoring."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"


def _scoring_module():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    return importlib.import_module("greenfield_matrix_quality_scoring")


def _transaction_summary() -> dict[str, str]:
    return {
        "transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }


def _manifest() -> dict[str, object]:
    return {
        "product_create_transaction": _transaction_summary(),
        "write_transaction": {
            "status": "committed",
            "commit_only": True,
            "prewrite_clean_before_commit": True,
            "rollback_guard": "enabled",
            "product_create_transaction_hash": "a" * 64,
            "product_facts_sha256": "c" * 64,
            "repository_write_set_hash": "b" * 64,
        },
    }


def test_write_transaction_custody_accepts_matching_product_intent_hashes() -> None:
    scoring = _scoring_module()

    assert scoring.write_transaction_custody_issues(
        _manifest(),
        product_create_transaction=_transaction_summary(),
    ) == ()


def test_write_transaction_custody_requires_a_product_intent_hash() -> None:
    scoring = _scoring_module()
    manifest = _manifest()
    write_transaction = manifest["write_transaction"]
    assert isinstance(write_transaction, dict)
    write_transaction.pop("product_facts_sha256")

    issues = scoring.write_transaction_custody_issues(
        manifest,
        product_create_transaction=_transaction_summary(),
    )

    assert "write transaction is missing a valid Product Intent facts hash" in issues


def test_write_transaction_custody_rejects_manifest_or_receipt_product_intent_drift() -> None:
    scoring = _scoring_module()
    manifest = _manifest()
    manifest_transaction = manifest["product_create_transaction"]
    assert isinstance(manifest_transaction, dict)
    manifest_transaction["product_facts_sha256"] = "d" * 64

    manifest_issues = scoring.write_transaction_custody_issues(
        manifest,
        product_create_transaction=_transaction_summary(),
    )

    assert "write transaction Product Intent facts hash does not match the manifest summary" in manifest_issues

    receipt = _transaction_summary()
    receipt["product_facts_sha256"] = "d" * 64
    receipt_issues = scoring.write_transaction_custody_issues(
        _manifest(),
        product_create_transaction=receipt,
    )

    assert "write transaction Product Intent facts hash does not match the create payload summary" in receipt_issues
