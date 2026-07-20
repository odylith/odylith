from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from odylith import cli
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_create_cli
from odylith.runtime.domain_intelligence import greenfield_commit_transaction
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    _POSTCONFIRM_RUNTIME_SOURCE_FILES,
)
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import load_sealed_product_create_commit
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_ALLOWED_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_contract import POST_CONFIRM_FORBIDDEN_OPERATIONS
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_compiler_identity,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_hash
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import (
    PRECONFIRM_QUALITY_MANIFEST_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction


def _quality_manifest() -> dict[str, Any]:
    return {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
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


def _transaction(repo_root: Path) -> Any:
    intent = confirmed_intent_with_authority(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        repo_root=repo_root,
        write_files=True,
    )
    authority = dict(intent[PRODUCT_INTENT_AUTHORITY_KEY])
    proposal = {
        "intent": {"title": "Municipal Permit Review Workspace"},
        PRODUCT_INTENT_AUTHORITY_KEY: authority,
        "backlog": [{"title": "Prove permit review path"}],
        "components": [],
        "diagrams": [],
    }
    package = compiled_greenfield_package_fixture(
        proposal=proposal,
        repo_root=repo_root,
    )
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=authority,
        quality_manifest=_quality_manifest(),
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
    )


def test_compiler_identity_fingerprints_only_postconfirm_runtime() -> None:
    paths = set(_POSTCONFIRM_RUNTIME_SOURCE_FILES)

    assert "runtime/domain_intelligence/greenfield_commit_transaction.py" in paths
    assert "runtime/domain_intelligence/greenfield_create_commit.py" in paths
    assert "runtime/domain_intelligence/greenfield_sealed_product_intent_authority.py" in paths
    assert "runtime/domain_intelligence/greenfield_compiled_write.py" in paths
    assert "runtime/domain_intelligence/greenfield_repository_write_set.py" in paths
    assert "runtime/domain_intelligence/greenfield_commit_journal.py" in paths
    assert "cli.py" in paths
    assert "runtime/domain_intelligence/greenfield_proposals_cli.py" in paths
    assert "runtime/domain_intelligence/greenfield_transaction.py" in paths
    assert "runtime/domain_intelligence/greenfield_create_transaction.py" not in paths
    assert "runtime/domain_intelligence/greenfield_product_intent_envelope.py" not in paths
    assert "runtime/domain_intelligence/greenfield_preconfirm_engine.py" not in paths
    assert "runtime/domain_intelligence/greenfield_source_casing.py" not in paths
    assert "runtime/domain_intelligence/greenfield_structural_copy.py" not in paths
    assert "runtime/artifact_quality/generated_copy_quality.py" not in paths
    assert "runtime/surfaces/render_casebook_dashboard.py" not in paths


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
        source_root / "runtime/domain_intelligence/greenfield_create_contract.py",
        source_root / "runtime/domain_intelligence/greenfield_proposals_cli.py",
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
        source_root / "runtime/domain_intelligence/greenfield_create_contract.py",
        source_root / "runtime/domain_intelligence/greenfield_proposals_cli.py",
    }
    assert expected - executed == expected_untraced
    assert executed == expected - expected_untraced


def test_postconfirm_allowed_operations_are_explicit() -> None:
    assert POST_CONFIRM_ALLOWED_OPERATIONS == (
        "verify_transaction_hash",
        "verify_compiler_receipt",
        "verify_compiler_provenance",
        "verify_sealed_product_intent_authority_bytes",
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


def test_sealed_commit_loader_rejects_receipted_unapproved_quality_manifest(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["quality_manifest"]["status"] = "failed"
    _rewrite_sealed_transaction(transaction_path, payload)

    with pytest.raises(ValueError, match="quality manifest is not approved"):
        load_sealed_product_create_commit(transaction_path)


@pytest.mark.parametrize("case", ("malformed", "resealed"))
def test_commit_rejects_malformed_or_resealed_authority_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    if case == "malformed":
        for authority in (
            payload["intent_authority"],
            payload["proposal"][PRODUCT_INTENT_AUTHORITY_KEY],
        ):
            authority["authority_snapshot_sha256"] = "not-a-sha256"
    else:
        payload["intent_authority"]["resealed_by_test"] = "untrusted"
    rewritten_hash = _rewrite_sealed_transaction(transaction_path, payload)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("sealed Product Intent authority must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="sealed Product Intent authority"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=rewritten_hash,
            confirm=True,
        )


def test_sealed_commit_loader_rejects_receipted_provenance_contract_drift(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["compiler_provenance"]["post_confirm_allowed_operations"] = []
    _rewrite_sealed_transaction(transaction_path, payload)
    with pytest.raises(ValueError, match="compiler identity or compiler provenance"):
        load_sealed_product_create_commit(transaction_path)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("post_confirm_allowed_operations", []),
        ("post_confirm_forbidden_operations", []),
    ),
)
def test_commit_reloads_and_rejects_receipted_operation_contract_drift_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    replacement: list[str],
) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    payload["compiler_provenance"][field] = replacement
    rewritten_hash = _rewrite_sealed_transaction(transaction_path, payload)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("operation-contract drift must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="compiler identity or compiler provenance"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction_path,
            transaction_hash=rewritten_hash,
            confirm=True,
        )


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

    def capture_compiled_write(**kwargs: Any) -> dict[str, Any]:
        commit_transaction = kwargs["transaction"]
        write_set = commit_transaction.prewrite_package.repository_write_set
        observed_write_sets.append(
            (
                str(write_set["write_set_hash"]),
                str(write_set["before_fingerprints"]["odylith/radar"]),
            )
        )
        return greenfield_compiled_write.compiled_greenfield_commit_result(transaction=commit_transaction)

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
            "'odylith.runtime.domain_intelligence.greenfield_text', "
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
        {**product_create_transaction_compiler_identity(), "version": "odylith.greenfield.compiler_identity.v3"},
        {**product_create_transaction_compiler_identity(), "odylith_version": "0.0.0-stale"},
        {**product_create_transaction_compiler_identity(), "source_files_sha256": "stale"},
    ),
)
def test_commit_rejects_stale_compiler_identity_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity: Mapping[str, Any],
) -> None:
    transaction = _replace_compiler_identity(_transaction(tmp_path), identity)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("stale compiler identity must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="compiler identity"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
        )
