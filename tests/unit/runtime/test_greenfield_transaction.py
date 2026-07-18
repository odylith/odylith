from __future__ import annotations

from pathlib import Path
import signal
import shutil

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_transaction
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from tests.unit.runtime.test_greenfield_create_transaction import _transaction
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction


def test_greenfield_apply_transaction_rolls_back_tooling_shell_outputs(tmp_path) -> None:
    shell_root = tmp_path / "odylith"
    shell_root.mkdir()
    index_path = shell_root / "index.html"
    payload_path = shell_root / "tooling-payload.v1.js"
    app_path = shell_root / "tooling-app.v1.js"
    index_path.write_text("old index\n", encoding="utf-8")
    payload_path.write_text("old payload\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="late refresh failure"):
        with GreenfieldApplyTransaction(tmp_path):
            index_path.write_text("new index\n", encoding="utf-8")
            payload_path.unlink()
            app_path.write_text("new app\n", encoding="utf-8")
            raise RuntimeError("late refresh failure")

    assert index_path.read_text(encoding="utf-8") == "old index\n"
    assert payload_path.read_text(encoding="utf-8") == "old payload\n"
    assert not app_path.exists()


def test_commit_transaction_reports_rollback_when_write_boundary_fails(tmp_path, monkeypatch) -> None:
    transaction = _transaction(repo_root=tmp_path)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def fail_write_boundary(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError("synthetic commit-boundary failure")

    monkeypatch.setattr(
        greenfield_create_commit.greenfield_compiled_write,
        "write_compiled_greenfield_package",
        fail_write_boundary,
    )

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc_info:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert exc_info.value.rollback_status == "rolled_back"
    assert exc_info.value.root_cause_type == "RuntimeError"
    assert exc_info.value.failure_kind == "post_confirm_commit_invariant_failure"
    assert "rollback completed; no governed records were committed" in str(exc_info.value)


def test_commit_transaction_maps_keyboard_interrupt_after_rollback(tmp_path, monkeypatch) -> None:
    transaction = _transaction(repo_root=tmp_path)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def interrupt_write_boundary(**_kwargs: object) -> dict[str, object]:
        raise KeyboardInterrupt()

    monkeypatch.setattr(
        greenfield_create_commit.greenfield_compiled_write,
        "write_compiled_greenfield_package",
        interrupt_write_boundary,
    )

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc_info:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert exc_info.value.rollback_status == "rolled_back"
    assert exc_info.value.root_cause_type == "KeyboardInterrupt"
    assert exc_info.value.failure_kind == "post_confirm_commit_interrupted"


@pytest.mark.parametrize("rollback_failure", [OSError("restore denied"), KeyboardInterrupt()])
def test_greenfield_transaction_preserves_snapshot_when_rollback_fails(
    tmp_path,
    monkeypatch,
    rollback_failure: BaseException,
) -> None:
    target = tmp_path / "odylith/index.html"
    target.parent.mkdir(parents=True)
    target.write_text("before\n", encoding="utf-8")
    transaction = GreenfieldApplyTransaction(tmp_path, paths=("odylith/index.html",))
    transaction.__enter__()
    target.write_text("after\n", encoding="utf-8")

    def fail_restore(_source: Path, _target: Path) -> None:
        raise rollback_failure

    monkeypatch.setattr(greenfield_transaction, "_copy_path", fail_restore)
    try:
        with pytest.raises(type(rollback_failure)):
            transaction.__exit__(RuntimeError, RuntimeError("commit failed"), None)
        assert transaction.rollback_status == "rollback_failed"
        assert transaction.recovery_path
        assert Path(transaction.recovery_path).is_dir()
    finally:
        if transaction.recovery_path:
            shutil.rmtree(transaction.recovery_path, ignore_errors=True)


def test_greenfield_transaction_rolls_back_graceful_termination(tmp_path) -> None:
    target = tmp_path / "odylith/index.html"
    target.parent.mkdir(parents=True)
    target.write_text("before\n", encoding="utf-8")
    transaction = GreenfieldApplyTransaction(tmp_path, paths=("odylith/index.html",))

    with pytest.raises(greenfield_transaction.GreenfieldCommitInterrupted, match="signal"):
        with transaction:
            target.write_text("partial\n", encoding="utf-8")
            greenfield_transaction._raise_greenfield_commit_interrupted(signal.SIGTERM, None)

    assert transaction.rollback_status == "rolled_back"
    assert target.read_text(encoding="utf-8") == "before\n"


def test_greenfield_transaction_guards_sigint_during_commit(tmp_path) -> None:
    transaction = GreenfieldApplyTransaction(tmp_path, paths=("odylith/index.html",))

    with transaction:
        assert int(signal.SIGINT) in transaction._signal_handlers  # noqa: SLF001
        transaction.commit()


def test_greenfield_transaction_removes_success_snapshot(tmp_path) -> None:
    transaction = GreenfieldApplyTransaction(tmp_path, paths=("odylith/index.html",))
    snapshot_root = None

    with transaction:
        snapshot_root = transaction._snapshot_root  # noqa: SLF001
        transaction.commit()

    assert snapshot_root is not None
    assert not snapshot_root.exists()
