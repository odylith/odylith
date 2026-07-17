from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    PRODUCT_CREATE_TRANSACTION_COMPILER_IDENTITY_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import _COMPILER_IDENTITY_SOURCE_FILES
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


def test_compiler_identity_fingerprints_the_commit_journal_runtime() -> None:
    assert "runtime/domain_intelligence/greenfield_commit_journal.py" in _COMPILER_IDENTITY_SOURCE_FILES


def test_compiler_identity_fingerprints_the_product_intent_authority_runtime() -> None:
    assert (
        "runtime/domain_intelligence/greenfield_product_intent_envelope.py"
        in _COMPILER_IDENTITY_SOURCE_FILES
    )


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
