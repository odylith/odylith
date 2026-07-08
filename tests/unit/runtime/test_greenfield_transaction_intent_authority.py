from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_intent_authority
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import POST_CONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import POST_CONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_snapshot_hash,
)


_CONFIRMED_INTENT = """# Lab Evidence Review Workspace - Product Intent Confirmation

## Product story
Research coordinators need one accountable workspace for turning dense lab submission notes into a reviewed evidence package without treating planning notes or implementation guidance as product truth. The product keeps intake, review, custody, and release-readiness decisions understandable before broader automation exists.

## State object
The lab evidence package records submitted sample context, reviewer notes, custody status, method constraints, evidence gaps, release-readiness status, and the reviewer decision that must stay visible across the evidence review path.

## First complete path
A research coordinator opens a new lab evidence package, records the submitted sample context, attaches method constraints, assigns a reviewer, resolves evidence gaps, saves custody status, and sees a release-readiness decision with the accepted proof trail.

## Human actors
- Research Coordinator: needs the product to record sample context, route review, resolve evidence gaps, and keep the accepted release-readiness decision visible.
- Evidence Reviewer: needs the product to review method constraints, add proof notes, and confirm the evidence package is ready or blocked.

## External systems
- Existing laboratory submission notes and sample tracking exports.

## Internal product systems
- Evidence Intake Workspace: receives lab submission details and keeps package state available for review.
- Custody Review Ledger: records reviewer decisions, evidence gaps, custody status, and proof trail changes.
- Release Readiness View: shows the accepted decision, blocked-path evidence, and visible proof summary.

## Critical assumptions
- Release 0.0.1 records evidence review and custody proof only.

## Ambiguities
- Live laboratory integrations can wait until the first package review path is proven.

## Proof boundary
Release 0.0.1 is proven only when the same lab evidence package can be opened, reviewed, updated with custody proof, and read back with the release-readiness decision and blocked evidence intact.
"""


def _approved_quality_manifest() -> dict[str, Any]:
    return {
        "version": POST_CONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": POST_CONFIRM_ENGINE_VERSION,
        "status": "passed",
        "validation_status": "passed",
        "hard_blocker": False,
        "issue_count": 0,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
    }


def _recorded_authority(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_CONFIRMED_INTENT, encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    structured_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    authority = product_intent_authority_from_envelope(
        record.envelope,
        structured_intent_path=structured_path,
        markdown_source_path=path,
    )
    return path, record.product_facts, authority


def _transaction(tmp_path: Path, *, authority: dict[str, Any] | None = None) -> Any:
    path, facts, file_authority = _recorded_authority(tmp_path)
    intent_authority = authority or file_authority
    proposal = {
        "intent": facts,
        PRODUCT_INTENT_AUTHORITY_KEY: intent_authority,
        "backlog": [{"title": "Prove lab evidence review path"}],
        "components": [],
        "diagrams": [],
    }
    package = GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result={"created": []},
        prewrite_safety_preview={"status": "passed"},
    )
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=intent_authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=tmp_path,
    )


def test_product_create_transaction_carries_confirmed_intent_authority_block(tmp_path: Path) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    payload = product_create_transaction_to_dict(transaction)

    persisted = payload["intent_authority"]
    assert persisted["version"] == "odylith.product-intent-authority.v2"
    assert persisted["origin"] == "verified_typed_envelope"
    assert persisted["decision"] == "confirmed_intent_accepted"
    assert persisted["fact_authority"] == "product_facts"
    assert persisted["markdown_authority"] == "ingest_only"
    assert persisted[PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert persisted["markdown_source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert persisted["markdown_source_path"] == str(path)
    assert persisted["structured_intent_path"] == str(path.with_suffix(".json"))
    assert persisted["source_format"] == "markdown"
    assert persisted["materiality_status"] == "passed"
    assert persisted["material_custody_sha256"]
    assert persisted["authority_snapshot_sha256"] == product_intent_authority_snapshot_hash(persisted)
    assert persisted["material_fields"]["first_path"]["custody_state"] == "accepted_fact"
    assert payload["transaction_hash"] == transaction.transaction_hash

    restored = product_create_transaction_from_dict(payload)

    assert restored.intent_authority[PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert restored.summary()["product_facts_sha256"] == authority[PRODUCT_FACTS_HASH_KEY]


def test_product_create_transaction_rejects_missing_intent_authority_payload(tmp_path: Path) -> None:
    payload = product_create_transaction_to_dict(_transaction(tmp_path))
    payload.pop("intent_authority")

    with pytest.raises(ValueError, match="Product Intent authority"):
        product_create_transaction_from_dict(payload)


def test_product_create_transaction_rejects_blocked_materiality_authority(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    blocked = {
        **authority,
        "materiality_status": "clarification_required",
        "blocked_material_fields": ["first_path"],
    }
    blocked["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(blocked)

    with pytest.raises(ValueError, match="did not pass materiality"):
        _transaction(tmp_path, authority=blocked)


def test_product_create_transaction_rejects_inferred_material_custody(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "custody_state": "inferred_fact",
        "derivation": "normalization_or_completion",
        "confidence": "medium",
        "source_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="unresolved material custody"):
        _transaction(tmp_path, authority=mutated)


def test_create_rejects_confirmed_intent_source_drift_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    path.write_text(_CONFIRMED_INTENT + "\n## Product story\nDrifted after compile.\n", encoding="utf-8")
    write_calls: list[str] = []

    def _baseline_should_not_run(_root: Path) -> None:
        write_calls.append("baseline")
        raise AssertionError("baseline creation must not run after intent authority drift")

    class _TransactionShouldNotRun:
        def __init__(self, _root: Path) -> None:
            write_calls.append("transaction")
            raise AssertionError("write transaction must not open after intent authority drift")

    def _write_should_not_run(**_kwargs: Any) -> dict[str, Any]:
        write_calls.append("write")
        raise AssertionError("write path must not run after intent authority drift")

    monkeypatch.setattr(greenfield_create_commit, "ensure_greenfield_create_baseline", _baseline_should_not_run)
    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", _TransactionShouldNotRun)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", _write_should_not_run)

    with pytest.raises(ValueError, match="source hash changed"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction=transaction,
            confirm=True,
        )

    assert write_calls == []


def test_create_rejects_missing_structured_intent_sidecar_before_write(tmp_path: Path) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    path.with_suffix(".json").unlink()

    with pytest.raises(ValueError, match="structured sidecar is not readable"):
        require_product_create_transaction_intent_authority(transaction, repo_root=tmp_path)


def test_create_rejects_structured_envelope_drift_with_unchanged_markdown(tmp_path: Path) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    structured_path = path.with_suffix(".json")
    payload = json.loads(structured_path.read_text(encoding="utf-8"))
    payload["decision_record"] = {
        **dict(payload["decision_record"]),
        "fact_authority": "markdown_projection",
    }
    structured_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid|structured envelope changed"):
        require_product_create_transaction_intent_authority(transaction, repo_root=tmp_path)


def test_product_create_transaction_hash_rejects_intent_authority_mutation(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    mutated = replace(
        transaction,
        intent_authority={**dict(transaction.intent_authority), PRODUCT_FACTS_HASH_KEY: "forged"},
    )

    assert not mutated.verified
    with pytest.raises(ValueError, match="hash mismatch"):
        require_product_create_transaction_verified(mutated)


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
