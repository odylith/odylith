from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_create_cli
from odylith.runtime.domain_intelligence import greenfield_commit_transaction
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence import greenfield_semantic_intent_packet
from odylith.runtime.domain_intelligence import greenfield_semantic_workflow
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    _POSTCONFIRM_RUNTIME_SOURCE_FILES,
)
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import load_sealed_product_create_commit
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_ALLOWED_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_FORBIDDEN_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_contract import (
    PRODUCT_CREATE_TRANSACTION_ACCEPTED_INTENT_AUTHORITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_compiler_identity,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_hash
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    product_intent_authority_snapshot_hash,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import semantic_intent_with_authority


_SEMANTIC_TRANSACTION_TEMPLATE: Any | None = None


def _semantic_transaction_template(repo_root: Path) -> Any:
    global _SEMANTIC_TRANSACTION_TEMPLATE
    if _SEMANTIC_TRANSACTION_TEMPLATE is not None:
        return _SEMANTIC_TRANSACTION_TEMPLATE
    intent = semantic_intent_with_authority()
    authority = dict(intent[PRODUCT_INTENT_AUTHORITY_KEY])
    proposal = greenfield_semantic_workflow.build_verified_semantic_proposal_for_repo(
        repo_root=repo_root,
        authority=authority,
        release_selector="0.0.1",
    )
    _SEMANTIC_TRANSACTION_TEMPLATE = greenfield_semantic_workflow.compile_verified_semantic_transaction(
        repo_root=repo_root,
        proposal=proposal,
        release_selector="0.0.1",
    )
    return _SEMANTIC_TRANSACTION_TEMPLATE


def _transaction(repo_root: Path) -> Any:
    template = _semantic_transaction_template(repo_root)
    return build_product_create_transaction(
        proposal=template.proposal,
        release_selector=template.release_selector,
        validation_gate=template.validation_gate,
        prewrite_package=template.prewrite_package,
        backlog_result=template.backlog_result,
        intent_authority=template.intent_authority,
        quality_manifest=template.quality_manifest,
        repo_root=repo_root,
    )


def _replace_compiler_identity(transaction: Any, identity: Mapping[str, Any]) -> Any:
    candidate = replace(
        transaction,
        compiler_provenance={
            **dict(transaction.compiler_provenance),
            "compiler_identity": dict(identity),
        },
    )
    return replace(candidate, transaction_hash=product_create_transaction_hash(candidate))


def _rewrite_sealed_transaction(path: Path, payload: Mapping[str, Any]) -> str:
    """Produce a structurally valid receipt pair for a negative sealed-input test."""

    rewritten = json.loads(json.dumps(dict(payload)))
    rewritten["transaction_hash"] = greenfield_commit_transaction._payload_hash(rewritten)  # noqa: SLF001
    encoded = json.dumps(rewritten, indent=2, sort_keys=True) + "\n"
    path.write_text(encoded, encoding="utf-8")
    receipt_path = path.with_name(path.name + ".compiler-receipt.v1.json")
    receipt_path.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.compiler_receipt.v1",
                "transaction_hash": rewritten["transaction_hash"],
                "transaction_file_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
                "post_confirm_runtime_identity": (
                    greenfield_commit_transaction.build_product_create_transaction_compiler_identity()
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return str(rewritten["transaction_hash"])


def test_product_create_transaction_provenance_carries_compiler_identity(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)

    assert transaction.compiler_provenance["compiler_identity"] == product_create_transaction_compiler_identity()
    assert (
        transaction.compiler_provenance["compiler_identity"]["version"]
        == PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION
        == "odylith.greenfield.compiler_identity.v15"
    )


@pytest.mark.parametrize("mutation", ("snapshot", "unhashed_extra"))
def test_transaction_rejects_divergent_proposal_authority_bytes(tmp_path: Path, mutation: str) -> None:
    transaction = _transaction(tmp_path)
    proposal = dict(transaction.proposal)
    proposal_authority = dict(proposal[PRODUCT_INTENT_AUTHORITY_KEY])
    if mutation == "snapshot":
        proposal_authority["authority_snapshot_sha256"] = "0" * 64
    else:
        proposal_authority["unhashed_relation_claim"] = "must not be accepted"
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = proposal_authority
    candidate = replace(transaction, proposal=proposal)
    candidate = replace(candidate, transaction_hash=product_create_transaction_hash(candidate))

    with pytest.raises(ValueError, match="proposal authority bytes do not match"):
        greenfield_create_transaction.require_product_create_transaction_hash_verified(candidate)


def test_cli_preview_rejects_compiled_proposal_authority_byte_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction_authority = {
        "version": PRODUCT_CREATE_TRANSACTION_ACCEPTED_INTENT_AUTHORITY_VERSION,
        "authority_snapshot_sha256": "a" * 64,
        "actor_action_relations": [],
    }
    proposal_authority = {
        **transaction_authority,
        "actor_action_relations": [{"actor": "Reviewer", "action": "approves"}],
    }
    candidate = {"title": "Permit Review", PRODUCT_INTENT_AUTHORITY_KEY: transaction_authority}
    transaction = SimpleNamespace(
        proposal={"intent": {"title": "Permit Review"}, PRODUCT_INTENT_AUTHORITY_KEY: proposal_authority},
        intent_authority=transaction_authority,
    )
    monkeypatch.setattr(
        greenfield_semantic_intent_packet,
        "load_semantic_intent_packet",
        lambda *_args, **_kwargs: SimpleNamespace(product_facts=candidate),
    )
    monkeypatch.setattr(
        greenfield_semantic_intent_packet,
        "semantic_intent_authority",
        lambda *_args, **_kwargs: transaction_authority,
    )
    monkeypatch.setattr(
        greenfield_semantic_workflow,
        "build_verified_semantic_proposal_for_repo",
        lambda **_kwargs: {"intent": {"title": "Permit Review"}},
    )
    monkeypatch.setattr(
        greenfield_semantic_workflow,
        "compile_verified_semantic_transaction",
        lambda **_kwargs: transaction,
    )

    with pytest.raises(RuntimeError, match="authority bytes do not match the visible typed preview"):
        greenfield_proposals_cli._compile_prompt_evidence_transaction(  # noqa: SLF001
            repo_root=tmp_path,
            prompt="Build permit review",
            edit_evidence="",
            release_selector="0.0.1",
            semantic_intent_file="semantic-intent.json",
        )


def test_compiler_identity_fingerprints_only_postconfirm_runtime() -> None:
    paths = set(_POSTCONFIRM_RUNTIME_SOURCE_FILES)

    assert "runtime/domain_intelligence/greenfield_commit_transaction.py" in paths
    assert "runtime/domain_intelligence/greenfield_create_commit.py" in paths
    assert "runtime/domain_intelligence/greenfield_compiled_write.py" in paths
    assert "runtime/domain_intelligence/greenfield_repository_write_set.py" in paths
    assert "runtime/domain_intelligence/greenfield_commit_journal.py" in paths
    assert "runtime/common/environment.py" in paths
    assert "cli.py" in paths
    assert "runtime/domain_intelligence/greenfield_proposals_cli.py" not in paths
    assert "runtime/surfaces/greenfield_host_confirmation.py" not in paths
    assert "runtime/domain_intelligence/greenfield_transaction.py" in paths
    assert "runtime/domain_intelligence/greenfield_create_transaction.py" not in paths
    assert "runtime/domain_intelligence/greenfield_operating_envelope.py" not in paths
    assert "runtime/domain_intelligence/greenfield_product_intent_envelope.py" not in paths
    assert "runtime/domain_intelligence/greenfield_sealed_product_intent_authority.py" not in paths
    assert "runtime/domain_intelligence/greenfield_preconfirm_engine.py" not in paths
    assert "runtime/domain_intelligence/greenfield_source_casing.py" not in paths
    assert "runtime/domain_intelligence/greenfield_structural_copy.py" not in paths
    assert "runtime/artifact_quality/generated_copy_quality.py" not in paths
    assert "runtime/surfaces/render_casebook_dashboard.py" not in paths


def test_create_router_imports_no_preconfirm_or_semantic_interpreter() -> None:
    tree = ast.parse(inspect.getsource(greenfield_proposals_cli))
    top_level_imports = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }

    assert not {
        "odylith.runtime.domain_intelligence.greenfield_preconfirm_engine",
        "odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization",
        "odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet",
    } & top_level_imports


def test_commit_loader_has_no_semantic_authority_imports() -> None:
    tree = ast.parse(inspect.getsource(greenfield_commit_transaction))
    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    forbidden = {
        "odylith.runtime.domain_intelligence.greenfield_product_intent_envelope",
        "odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority",
    }
    assert not forbidden.intersection(imported_modules)
    assert all("actor_action" not in module for module in imported_modules)


def test_postconfirm_receipt_covers_executed_runtime(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    sealed_transaction = load_sealed_product_create_commit(transaction_path)
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith"
    expected = {source_root / path for path in _POSTCONFIRM_RUNTIME_SOURCE_FILES}
    executed: set[Path] = set()

    def trace(frame: Any, event: str, _argument: Any) -> Any:
        if event == "call":
            source_path = Path(frame.f_code.co_filename).resolve()
            if source_path.is_relative_to(source_root):
                executed.add(source_path)
        return trace

    previous_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        result = greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=sealed_transaction.transaction_hash,
            confirm=True,
        )
    finally:
        sys.settrace(previous_trace)

    assert result["repository_write_set"]["status"] == "passed"
    assert executed
    expected_untraced = {
        source_root / "__init__.py",
        source_root / "cli.py",
        source_root / "runtime/domain_intelligence/greenfield_create_cli.py",
        source_root / "runtime/domain_intelligence/greenfield_post_confirm_handoff.py",
        source_root / "runtime/common/environment.py",
        source_root / "runtime/domain_intelligence/greenfield_pending_transaction_store.py",
    }
    assert expected - executed == expected_untraced
    assert executed == expected - expected_untraced
    assert source_root / "runtime/domain_intelligence/greenfield_product_intent_envelope.py" not in executed
    assert source_root / "runtime/domain_intelligence/greenfield_create_transaction.py" not in executed


def test_postconfirm_receipt_covers_canonical_create_adapter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith"
    expected = {source_root / path for path in _POSTCONFIRM_RUNTIME_SOURCE_FILES}
    executed: set[Path] = set()

    def trace(frame: Any, event: str, _argument: Any) -> Any:
        if event == "call":
            source_path = Path(frame.f_code.co_filename).resolve()
            if source_path.is_relative_to(source_root):
                executed.add(source_path)
        return trace

    previous_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        result = greenfield_create_cli.main(
            [
                "create",
                "--repo-root",
                str(tmp_path),
                "--transaction-file",
                str(transaction_path),
                "--transaction-hash",
                transaction.transaction_hash,
                "--confirm",
            ]
        )
    finally:
        sys.settrace(previous_trace)

    assert result == 0
    capsys.readouterr()
    assert source_root / "runtime/domain_intelligence/greenfield_create_cli.py" in executed
    expected_untraced = {
        source_root / "__init__.py",
        source_root / "cli.py",
        source_root / "runtime/domain_intelligence/greenfield_pending_transaction_store.py",
    }
    assert expected - executed == expected_untraced
    assert executed == expected - expected_untraced


def test_postconfirm_allowed_operations_are_explicit() -> None:
    assert POST_CONFIRM_ALLOWED_OPERATIONS == (
        "verify_transaction_hash",
        "verify_compiler_receipt",
        "verify_post_confirm_runtime_identity",
        "verify_sealed_write_set",
        "verify_repo_preconditions",
        "apply_preconfirm_refreshed_sealed_bytes",
        "write_sealed_repository_bytes",
        "validate_readback",
        "report_success",
    )
    assert "live_post_confirm_refresh" in POST_CONFIRM_FORBIDDEN_OPERATIONS


def test_sealed_commit_loader_rejects_tampered_transaction_bytes(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    transaction_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match its pre-confirm compiler receipt"):
        load_sealed_product_create_commit(transaction_path)


@pytest.mark.parametrize(
    "authority_version",
    (
        "odylith.product-intent-authority.v4",
        "odylith.product-intent-authority.v5",
        "odylith.product-intent-authority.v6",
        "odylith.product-intent-authority.v7",
    ),
)
def test_commit_rejects_legacy_authority_before_write(
    tmp_path: Path,
    authority_version: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["intent_authority"]["version"] = authority_version
    payload["proposal"][PRODUCT_INTENT_AUTHORITY_KEY]["version"] = authority_version
    payload["commit_summary"]["intent_authority_version"] = authority_version
    rewritten_hash = _rewrite_sealed_transaction(transaction_path, payload)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("a legacy authority must fail before the write boundary")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="unsupported Product Intent authority version"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=rewritten_hash,
            confirm=True,
        )

    assert not (tmp_path / "odylith/radar/source").exists()


@pytest.mark.parametrize(
    ("authority_version", "envelope_version", "ledger_version"),
    (
        (
            "odylith.product-intent-authority.v4",
            "odylith.product-intent-envelope.v4",
            "odylith.product-intent-custody-ledger.v3",
        ),
        (
            "odylith.product-intent-authority.v5",
            "odylith.product-intent-envelope.v5",
            "odylith.product-intent-custody-ledger.v4",
        ),
    ),
)
def test_pending_decoder_requires_v8_authority_rebuild(
    tmp_path: Path,
    authority_version: str,
    envelope_version: str,
    ledger_version: str,
) -> None:
    transaction = _transaction(tmp_path)
    legacy_authority = {
        **dict(transaction.intent_authority),
        "version": authority_version,
        "envelope_schema_version": envelope_version,
        "ledger_version": ledger_version,
    }
    legacy_authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(legacy_authority)
    proposal = dict(transaction.proposal)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = legacy_authority
    candidate = replace(transaction, proposal=proposal, intent_authority=legacy_authority)
    candidate = replace(candidate, transaction_hash=product_create_transaction_hash(candidate))

    with pytest.raises(ValueError, match="unsupported version; rebuild"):
        greenfield_create_transaction.product_create_transaction_from_dict(
            greenfield_create_transaction.product_create_transaction_to_dict(candidate)
        )


@pytest.mark.parametrize("mutation", ("non_mapping_authority", "summary_version"))
def test_sealed_commit_loader_requires_exact_v14_authority_protocol(
    tmp_path: Path,
    mutation: str,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    if mutation == "non_mapping_authority":
        payload["intent_authority"] = []
        expected = "unsupported Product Intent authority version"
    else:
        payload["commit_summary"]["intent_authority_version"] = "odylith.product-intent-authority.v5"
        expected = "summary does not match its accepted Product Intent authority version"
    _rewrite_sealed_transaction(transaction_path, payload)

    with pytest.raises(ValueError, match=expected):
        load_sealed_product_create_commit(transaction_path)


def test_create_contract_accepts_only_v14_intent_authority() -> None:
    assert PRODUCT_CREATE_TRANSACTION_ACCEPTED_INTENT_AUTHORITY_VERSION == "odylith.product-intent-authority.v16"


@pytest.mark.parametrize("mutation", ("extra_field", "reformatted"))
def test_sealed_commit_loader_rejects_receipt_byte_drift(tmp_path: Path, mutation: str) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    receipt_path = transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if mutation == "extra_field":
        receipt["unreviewed_field"] = "not-sealed"
        receipt_text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    else:
        receipt_text = json.dumps(receipt, separators=(",", ":"), sort_keys=True)
    receipt_path.write_text(receipt_text, encoding="utf-8")

    with pytest.raises(ValueError, match="compiler receipt bytes are not canonical"):
        load_sealed_product_create_commit(transaction_path)


def test_commit_rejects_runtime_drift_before_the_write_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    runtime_identity = greenfield_commit_transaction.build_product_create_transaction_compiler_identity()
    monkeypatch.setattr(
        greenfield_commit_transaction,
        "build_product_create_transaction_compiler_identity",
        lambda: {**runtime_identity, "source_files_sha256": "runtime-drift"},
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("runtime drift must not enter the write boundary")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="post-confirm runtime changed"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
        )


def test_sealed_commit_loader_treats_quality_as_opaque_preconfirm_evidence(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["quality_manifest"]["status"] = "failed"
    _rewrite_sealed_transaction(transaction_path, payload)

    loaded = load_sealed_product_create_commit(transaction_path)

    assert loaded.commit_manifest_preview["status"] == "failed"


def test_sealed_commit_projection_exposes_no_product_adjudication_fields(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)

    loaded = load_sealed_product_create_commit(transaction_path)

    assert not hasattr(loaded, "intent_authority")
    assert not hasattr(loaded, "quality_manifest")
    assert not hasattr(loaded, "compiler_provenance")


def test_confirmed_hash_rejects_changed_opaque_evidence_without_any_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["quality_manifest"]["status"] = "failed"
    _rewrite_sealed_transaction(transaction_path, payload)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("a changed transaction must not enter the write boundary")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="does not match the confirmed transaction hash"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
        )


def test_commit_treats_product_quality_and_authority_as_opaque_after_hash_confirmation(
    tmp_path: Path,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["quality_manifest"]["status"] = "failed"
    payload["intent_authority"]["authority_snapshot_sha256"] = "not-a-sha256"
    payload["proposal"][PRODUCT_INTENT_AUTHORITY_KEY]["authority_snapshot_sha256"] = "not-a-sha256"
    rewritten_hash = _rewrite_sealed_transaction(transaction_path, payload)

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction_path,
        transaction_hash=rewritten_hash,
        confirm=True,
    )

    assert result["repository_write_set"]["status"] == "passed"


def test_commit_derives_execution_reporting_from_the_sealed_write_set(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    summary = payload["commit_summary"]
    summary["repository_write_set_hash"] = "forged-write-set-hash"
    summary["repository_write_count"] = 999
    summary.pop("product_facts_sha256")
    rewritten_hash = _rewrite_sealed_transaction(transaction_path, payload)

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction_path,
        transaction_hash=rewritten_hash,
        confirm=True,
    )

    transaction_summary = result["product_create_transaction"]
    write_manifest = result["commit_manifest"]["write_transaction"]
    assert transaction_summary["repository_write_set_hash"] == result["repository_write_set"]["write_set_hash"]
    assert transaction_summary["repository_write_count"] == result["repository_write_set"]["write_count"]
    assert write_manifest["repository_write_set_hash"] == result["repository_write_set"]["write_set_hash"]
    assert write_manifest["product_facts_sha256"] == ""


def test_commit_reloads_receipted_bytes_instead_of_using_a_mutable_loaded_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    loaded = load_sealed_product_create_commit(transaction_path)
    mutable_write_set = loaded.prewrite_package.repository_write_set
    expected_hash = str(mutable_write_set["write_set_hash"])
    expected_radar_fingerprint = str(mutable_write_set["before_fingerprints"]["odylith/radar"])
    mutable_write_set["write_set_hash"] = "forged-in-memory-write-set"
    mutable_write_set["before_fingerprints"]["odylith/radar"] = "forged-in-memory-radar-fingerprint"
    assert loaded.prewrite_package.repository_write_set["write_set_hash"] == expected_hash
    assert (
        loaded.prewrite_package.repository_write_set["before_fingerprints"]["odylith/radar"]
        == expected_radar_fingerprint
    )
    observed_write_sets: list[tuple[str, str]] = []
    write_compiled_package = greenfield_compiled_write.write_compiled_greenfield_package

    def capture_compiled_write(**kwargs: Any) -> dict[str, Any]:
        commit_transaction = kwargs["transaction"]
        write_set = commit_transaction.prewrite_package.repository_write_set
        observed_write_sets.append(
            (
                str(write_set["write_set_hash"]),
                str(write_set["before_fingerprints"]["odylith/radar"]),
            )
        )
        return write_compiled_package(**kwargs)

    monkeypatch.setattr(
        greenfield_compiled_write,
        "write_compiled_greenfield_package",
        capture_compiled_write,
    )

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction_path,
        transaction_hash=loaded.transaction_hash,
        confirm=True,
    )

    assert result["repository_write_set"]["status"] == "passed"
    assert observed_write_sets == [(expected_hash, expected_radar_fingerprint)]


def test_commit_executor_does_not_accept_a_live_compiler_object(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)

    with pytest.raises(TypeError, match="unexpected keyword argument 'transaction'"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction=transaction,
            confirm=True,
        )


def test_canonical_create_classifies_malformed_transaction_before_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    transaction_path.write_text("{not-json\n", encoding="utf-8")

    result = cli.main(
        [
            "greenfield",
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_path),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert result == 2
    assert payload["mode"] == "error"
    assert "ProductCreateTransaction or compiler receipt is malformed" in payload["error"]
    assert "no Product Intent was rejected" in payload["error"]
    assert "no governed records were written" in payload["error"]
    assert "Expecting property name" not in payload["error"]


def test_canonical_create_cli_commits_the_sealed_transaction_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)

    result = cli.main(
        [
            "greenfield",
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_path),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
        ]
    )

    assert result == 0
    assert "Odylith committed the validated Greenfield package." in capsys.readouterr().out


def test_canonical_create_cli_avoids_preconfirm_transaction_runtime(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    source_root = Path(__file__).resolve().parents[3] / "src"
    command = [
        sys.executable,
        "-c",
        (
            "import json, sys; from odylith import cli; "
            "authority_modules = ("
            "'odylith.runtime.domain_intelligence.greenfield_product_intent_envelope', "
            "'odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority', "
            "'odylith.runtime.domain_intelligence.greenfield_confirmed_intent'); "
            "authority_modules_before = {name for name in authority_modules if name in sys.modules}; "
            f"result = cli.main({['greenfield', 'create', '--repo-root', str(tmp_path), '--transaction-file', str(transaction_path), '--transaction-hash', transaction.transaction_hash, '--confirm']!r}); "
            "print(json.dumps({'result': result, "
            "'compiler_loaded': 'odylith.runtime.domain_intelligence.greenfield_create_transaction' in sys.modules, "
            "'new_preconfirm_authority_modules': sorted("
            "name for name in authority_modules if name in sys.modules and name not in authority_modules_before)}))"
        ),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(source_root)},
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload == {
        "result": 0,
        "compiler_loaded": False,
        "new_preconfirm_authority_modules": [],
    }


@pytest.mark.parametrize(
    "identity",
    (
        {},
        {**product_create_transaction_compiler_identity(), "version": "odylith.greenfield.compiler_identity.v6"},
        {**product_create_transaction_compiler_identity(), "odylith_version": "0.0.0-stale"},
        {**product_create_transaction_compiler_identity(), "source_files_sha256": "stale"},
    ),
)
def test_commit_rejects_compiler_identity_drift_before_the_write_boundary(
    tmp_path: Path,
    identity: Mapping[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _replace_compiler_identity(_transaction(tmp_path), identity)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("compiler identity drift must fail before the write boundary")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="compiler (?:identity|provenance) was invalidated"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
        )

    assert not (tmp_path / "odylith/radar/source").exists()
