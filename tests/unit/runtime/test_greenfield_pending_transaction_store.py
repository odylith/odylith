from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from tests.unit.runtime.test_greenfield_create_transaction import _transaction


def test_pending_transaction_is_immutable_and_hash_addressed(tmp_path: Path) -> None:
    transaction = _transaction(repo_root=tmp_path)

    path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=transaction,
    )

    assert path == greenfield_pending_transaction_store.pending_transaction_path(
        tmp_path,
        transaction.transaction_hash,
    )
    assert path.is_file()
    assert greenfield_pending_transaction_store.resolve_pending_transaction(
        repo_root=tmp_path,
        transaction_hash=transaction.transaction_hash,
    ) == path
    assert greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=transaction,
    ) == path


def test_pending_transaction_staging_failure_has_no_visible_partial_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(repo_root=tmp_path)

    def _fail(*_args: object, **_kwargs: object) -> Path:
        raise OSError("injected staging failure")

    monkeypatch.setattr(
        greenfield_pending_transaction_store.greenfield_create_transaction,
        "write_compiled_product_create_transaction_file",
        _fail,
    )

    with pytest.raises(OSError, match="injected staging failure"):
        greenfield_pending_transaction_store.stage_pending_transaction(
            repo_root=tmp_path,
            transaction=transaction,
        )

    target = greenfield_pending_transaction_store.pending_transaction_directory(
        tmp_path,
        transaction.transaction_hash,
    )
    assert not target.exists()
    assert not list(target.parent.glob(".stage-*"))


def test_pending_transaction_address_rejects_mutated_existing_bytes(tmp_path: Path) -> None:
    transaction = _transaction(repo_root=tmp_path)
    path = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=transaction,
    )
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="does not match.*receipt"):
        greenfield_pending_transaction_store.stage_pending_transaction(
            repo_root=tmp_path,
            transaction=transaction,
        )


def test_repository_lock_rejects_a_concurrent_decision(tmp_path: Path) -> None:
    with greenfield_repository_lock.greenfield_repository_lock(tmp_path):
        with pytest.raises(greenfield_repository_lock.GreenfieldRepositoryBusyError):
            with greenfield_repository_lock.greenfield_repository_lock(tmp_path):
                raise AssertionError("second owner must not enter the mutation boundary")
