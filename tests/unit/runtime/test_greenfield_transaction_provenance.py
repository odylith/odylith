from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
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
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
    _POSTCONFIRM_RUNTIME_SOURCE_FILES,
)
from odylith.runtime.domain_intelligence.greenfield_commit_transaction import load_sealed_product_create_commit
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
    assert "runtime/domain_intelligence/greenfield_compiled_write.py" in paths
    assert "runtime/domain_intelligence/greenfield_repository_write_set.py" in paths
    assert "runtime/domain_intelligence/greenfield_commit_journal.py" in paths
    assert "runtime/domain_intelligence/greenfield_transaction.py" in paths
    assert "runtime/domain_intelligence/greenfield_create_transaction.py" not in paths
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
            transaction=sealed_transaction,
            confirm=True,
        )
    finally:
        sys.settrace(previous_trace)

    assert result["repository_write_set"]["status"] == "passed"
    assert executed
    assert executed <= expected


def test_sealed_commit_loader_rejects_tampered_transaction_bytes(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    transaction_path = tmp_path / "product-create-transaction.v1.json"
    greenfield_create_transaction.write_compiled_product_create_transaction_file(transaction_path, transaction)
    transaction_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match its pre-confirm compiler receipt"):
        load_sealed_product_create_commit(transaction_path)


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
            f"result = cli.main({['greenfield', 'create', '--repo-root', str(tmp_path), '--transaction-file', str(transaction_path), '--transaction-hash', transaction.transaction_hash, '--confirm']!r}); "
            "print(json.dumps({'result': result, 'compiler_loaded': 'odylith.runtime.domain_intelligence.greenfield_create_transaction' in sys.modules}))"
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
    assert payload == {"result": 0, "compiler_loaded": False}


@pytest.mark.parametrize(
    "identity",
    (
        {},
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

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("stale compiler identity must fail before governed writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="compiler identity"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction=transaction,
            confirm=True,
        )
