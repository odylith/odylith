from __future__ import annotations

from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_commit_transaction
from odylith.runtime.domain_intelligence import greenfield_commit_journal
from odylith.runtime.domain_intelligence import greenfield_create_transaction
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


_DIGEST = "a" * 64


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _stage_from_source(source: Path, stage: Path) -> None:
    stage.mkdir(parents=True, exist_ok=True)
    if (source / "odylith").is_dir():
        shutil.copytree(source / "odylith", stage / "odylith")


@pytest.mark.parametrize("link_level", ("leaf", "parent"))
def test_sealed_transaction_load_rejects_leaf_and_parent_symlinks_before_outside_read(
    tmp_path: Path,
    link_level: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_transaction = outside / "transaction.json"
    outside_receipt = outside / "transaction.json.compiler-receipt.v1.json"
    _write(outside_transaction, "outside transaction\n")
    _write(outside_receipt, "outside receipt\n")
    before = (outside_transaction.read_bytes(), outside_receipt.read_bytes())

    if link_level == "parent":
        (root / ".odylith").symlink_to(outside, target_is_directory=True)
        transaction_path = root / ".odylith/transaction.json"
    else:
        transaction_path = root / ".odylith/runtime/greenfield/transaction.json"
        transaction_path.parent.mkdir(parents=True)
        transaction_path.symlink_to(outside_transaction)
        transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json").symlink_to(
            outside_receipt
        )

    with pytest.raises(ValueError, match="safe repository transaction boundary"):
        greenfield_commit_transaction.load_sealed_product_create_commit(
            transaction_path,
            repo_root=root,
        )

    assert (outside_transaction.read_bytes(), outside_receipt.read_bytes()) == before


def test_repository_lock_rejects_symlinked_dot_odylith_before_outside_write(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / ".odylith").symlink_to(outside, target_is_directory=True)

    with pytest.raises(greenfield_repository_lock.GreenfieldRepositoryLockError):
        with greenfield_repository_lock.greenfield_repository_lock(root):
            raise AssertionError("unsafe lock must not be entered")

    assert list(outside.iterdir()) == []


def test_compiler_receipt_leaf_symlink_rejects_before_transaction_or_outside_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    transaction_path = root / ".odylith/runtime/greenfield/transaction.json"
    outside = tmp_path / "outside-receipt.json"
    _write(transaction_path, "original transaction\n")
    _write(outside, "outside receipt\n")
    receipt = transaction_path.with_name(transaction_path.name + ".compiler-receipt.v1.json")
    receipt.symlink_to(outside)
    transaction_before = transaction_path.read_bytes()
    outside_before = outside.read_bytes()
    transaction = SimpleNamespace(transaction_hash=_DIGEST)

    monkeypatch.setattr(
        greenfield_create_transaction,
        "require_product_create_transaction_verified",
        lambda _transaction: None,
    )
    monkeypatch.setattr(
        greenfield_create_transaction,
        "product_create_transaction_to_dict",
        lambda _transaction: {"transaction_hash": _DIGEST},
    )

    with pytest.raises(ValueError, match="symlink"):
        greenfield_create_transaction.write_compiled_product_create_transaction_file(
            transaction_path,
            transaction,
            repo_root=root,
        )

    assert transaction_path.read_bytes() == transaction_before
    assert outside.read_bytes() == outside_before


@pytest.mark.parametrize("operation", ("stage", "resolve", "discard"))
def test_pending_store_rejects_symlinked_ancestor_before_outside_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / ".odylith").symlink_to(outside, target_is_directory=True)
    writer_called = False

    def forbidden_writer(*_args: object, **_kwargs: object) -> Path:
        nonlocal writer_called
        writer_called = True
        raise AssertionError("pending bytes must not be written through a symlink")

    monkeypatch.setattr(
        greenfield_pending_transaction_store.greenfield_create_transaction,
        "write_compiled_product_create_transaction_file",
        forbidden_writer,
    )
    transaction = SimpleNamespace(transaction_hash=_DIGEST)

    with pytest.raises(ValueError, match="symlink"):
        if operation == "stage":
            greenfield_pending_transaction_store.stage_pending_transaction(
                repo_root=root,
                transaction=transaction,
            )
        elif operation == "resolve":
            greenfield_pending_transaction_store.resolve_pending_transaction(
                repo_root=root,
                transaction_hash=_DIGEST,
            )
        else:
            greenfield_pending_transaction_store.discard_pending_transaction(
                repo_root=root,
                transaction_hash=_DIGEST,
            )

    assert writer_called is False
    assert list(outside.iterdir()) == []


def test_pending_store_ordinary_stage_retry_and_discard_remain_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    transaction = SimpleNamespace(transaction_hash=_DIGEST)

    def write_stub(path: Path, _transaction: object, *, repo_root: Path) -> Path:
        greenfield_transaction_path_boundary.atomic_write_bytes(repo_root, path, b"transaction\n")
        greenfield_transaction_path_boundary.atomic_write_bytes(
            repo_root,
            path.with_name(path.name + ".compiler-receipt.v1.json"),
            b"receipt\n",
        )
        return path

    def load_stub(path: Path, *, repo_root: Path) -> object:
        assert greenfield_transaction_path_boundary.read_bytes(repo_root, path) == b"transaction\n"
        assert greenfield_transaction_path_boundary.read_bytes(
            repo_root,
            path.with_name(path.name + ".compiler-receipt.v1.json"),
        ) == b"receipt\n"
        return transaction

    monkeypatch.setattr(
        greenfield_pending_transaction_store.greenfield_create_transaction,
        "write_compiled_product_create_transaction_file",
        write_stub,
    )
    monkeypatch.setattr(
        greenfield_pending_transaction_store.greenfield_create_transaction,
        "load_compiled_product_create_transaction_file",
        load_stub,
    )

    first = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=root,
        transaction=transaction,
    )
    second = greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=root,
        transaction=transaction,
    )
    assert first == second
    assert first.is_file()

    greenfield_pending_transaction_store.discard_pending_transaction(
        repo_root=root,
        transaction_hash=_DIGEST,
    )
    assert not first.parent.exists()


def test_pending_discard_rejects_nested_symlink_before_renaming_package(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside.txt"
    pending = greenfield_pending_transaction_store.pending_transaction_directory(root, _DIGEST)
    pending.mkdir(parents=True)
    _write(outside, "outside\n")
    (pending / "unexpected-link").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        greenfield_pending_transaction_store.discard_pending_transaction(
            repo_root=root,
            transaction_hash=_DIGEST,
        )

    assert pending.is_dir()
    assert (pending / "unexpected-link").is_symlink()
    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_managed_destination_parent_symlink_fails_before_outside_write(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside"
    target = root / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(root, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    outside_target = outside / "source/INDEX.md"
    _write(outside_target, "outside\n")
    before = outside_target.read_bytes()
    shutil.rmtree(root / "odylith/radar")
    (root / "odylith/radar").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="refuses managed symlink"):
        greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
            repo_root=root,
            write_set=write_set,
        )

    assert outside_target.read_bytes() == before


def test_managed_destination_leaf_symlink_fails_before_outside_write(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside.md"
    root.mkdir()
    _write(stage / "odylith/radar/source/INDEX.md", "sealed\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    _write(outside, "outside\n")
    target = root / "odylith/radar/source/INDEX.md"
    target.parent.mkdir(parents=True)
    target.symlink_to(outside)
    before = outside.read_bytes()

    with pytest.raises(ValueError, match="refuses managed symlink"):
        greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
            repo_root=root,
            write_set=write_set,
        )

    assert outside.read_bytes() == before


def test_symlinked_journal_staging_fails_before_destination_or_outside_write(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside"
    target = root / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(root, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    outside.mkdir()
    staging = root / ".odylith/runtime/greenfield/create-journal" / _DIGEST / "staging"
    staging.parent.mkdir(parents=True)
    staging.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
            repo_root=root,
            write_set=write_set,
            temporary_directory=staging,
        )

    assert target.read_text(encoding="utf-8") == "before\n"
    assert list(outside.iterdir()) == []


def test_symlinked_generation_destination_fails_before_outside_materialization(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside"
    root.mkdir()
    _write(stage / "odylith/radar/source/INDEX.md", "sealed\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    outside.mkdir()
    destination = root / ".odylith/runtime/greenfield/destination"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        greenfield_repository_write_set.materialize_compiled_greenfield_after_image(
            repo_root=root,
            destination_root=destination,
            write_set=write_set,
            temporary_directory=root / ".odylith/runtime/greenfield/staging",
        )

    assert list(outside.iterdir()) == []


def test_managed_readback_rejects_a_new_symlink_without_following_it(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside.md"
    target = root / "odylith/radar/source/INDEX.md"
    _write(target, "before\n")
    _stage_from_source(root, stage)
    _write(stage / "odylith/radar/source/INDEX.md", "after\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
    )
    _write(outside, "outside\n")
    target.unlink()
    target.symlink_to(outside)
    before = outside.read_bytes()

    with pytest.raises(ValueError, match="refuses managed symlink"):
        greenfield_repository_write_set.require_greenfield_repository_after_state(
            repo_root=root,
            write_set=write_set,
        )

    assert outside.read_bytes() == before


def test_post_lock_greenfield_ancestor_swap_cannot_publish_outside_repo(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    managed = root / ".odylith/runtime/greenfield"
    managed.mkdir(parents=True)
    outside.mkdir()

    with greenfield_repository_lock.greenfield_repository_lock(root):
        displaced = managed.with_name("greenfield-displaced")
        managed.rename(displaced)
        managed.symlink_to(outside, target_is_directory=True)
        with pytest.raises(ValueError, match="symlink"):
            greenfield_generation_state.publish_active_generation_state(
                repo_root=root,
                expected_identity=greenfield_generation_state.no_active_generation_identity(),
                transaction_hash=_DIGEST,
                write_set_hash="b" * 64,
                generation_manifest_sha256="c" * 64,
            )

    assert list(outside.iterdir()) == []


def test_generation_parent_swap_rejects_before_outside_manifest_read(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    _write(stage / "odylith/radar/source/INDEX.md", "sealed\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
        repo_root=root,
        transaction_hash=_DIGEST,
        write_set=write_set,
    )
    before = tuple(outside.iterdir())
    displaced = generation.generation_root.with_name(f"{_DIGEST}.displaced")
    generation.generation_root.rename(displaced)
    generation.generation_root.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        greenfield_generation_store.pin_greenfield_generation(
            repo_root=root,
            transaction_hash=_DIGEST,
            expected_write_set=write_set,
        )

    assert tuple(outside.iterdir()) == before


def test_journal_state_leaf_swap_rejects_before_outside_read(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    stage = tmp_path / "stage"
    outside = tmp_path / "outside-state.json"
    root.mkdir()
    _write(stage / "odylith/radar/source/INDEX.md", "sealed\n")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )
    journal = greenfield_commit_journal.GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash=_DIGEST,
        write_set=write_set,
    )
    journal.prepare()
    _write(outside, "outside journal\n")
    before = outside.read_bytes()
    journal.state_path.unlink()
    journal.state_path.symlink_to(outside)

    with pytest.raises(greenfield_commit_journal.GreenfieldCommitJournalError):
        journal.recover_or_return_committed()

    assert outside.read_bytes() == before


def test_rollback_parent_swap_cannot_delete_outside_tree(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    target = root / "odylith/index.html"
    outside = tmp_path / "outside"
    _write(target, "before\n")
    _write(outside / "index.html", "outside\n")
    transaction = GreenfieldApplyTransaction(root, paths=("odylith/index.html",))
    transaction.__enter__()
    target.write_text("after\n", encoding="utf-8")
    displaced = root / "odylith-displaced"
    (root / "odylith").rename(displaced)
    (root / "odylith").symlink_to(outside, target_is_directory=True)
    before = (outside / "index.html").read_bytes()

    with pytest.raises(ValueError, match="symlink"):
        transaction.__exit__(RuntimeError, RuntimeError("commit failed"), None)

    assert transaction.rollback_status == "rollback_failed"
    assert (outside / "index.html").read_bytes() == before
