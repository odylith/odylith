from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_commit_journal
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldCommitInterrupted
from tests.unit.runtime.test_greenfield_create_transaction import _transaction
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_set(root: Path) -> dict[str, object]:
    stage = root.parent / "stage"
    _write(root / "odylith/radar/source/first.md", "first before\n")
    _write(root / "odylith/radar/source/second.md", "second before\n")
    shutil.copytree(root / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/first.md", "first after\n")
    _write(stage / "odylith/radar/source/second.md", "second after\n")
    return greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )


def _new_directory_write_set(root: Path) -> dict[str, object]:
    stage = root.parent / "stage"
    _write(root / "odylith/radar/source/first.md", "first before\n")
    shutil.copytree(root / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/generated/first.md", "generated after\n")
    _write(stage / "odylith/radar/source/generated/second.md", "second generated after\n")
    return greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )


def _delete_write_set(root: Path) -> dict[str, object]:
    stage = root.parent / "stage"
    _write(root / "odylith/radar/source/first.md", "first before\n")
    _write(root / "odylith/radar/source/delete.md", "delete before\n")
    _write(root / "odylith/radar/source/delete-second.md", "delete second before\n")
    shutil.copytree(root / "odylith", stage / "odylith")
    _write(stage / "odylith/radar/source/first.md", "first after\n")
    (stage / "odylith/radar/source/delete.md").unlink()
    (stage / "odylith/radar/source/delete-second.md").unlink()
    return greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=root,
        staged_root=stage,
    )


def _prepared_journal(
    root: Path,
    write_set: dict[str, object],
) -> tuple[GreenfieldCommitJournal, GreenfieldApplyTransaction]:
    journal = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    )
    journal.prepare()
    transaction = GreenfieldApplyTransaction(
        root,
        paths=journal.paths,
        snapshot_root=journal.snapshot_root,
        retain_snapshot=True,
    )
    transaction.__enter__()
    journal.mark_prepared()
    return journal, transaction


def _release_signal_guard(transaction: GreenfieldApplyTransaction) -> None:
    transaction._restore_signal_handlers()  # noqa: SLF001
    assert signal.getsignal(signal.SIGINT) is not None


def _kill_commit_child(
    *,
    root: Path,
    write_set: dict[str, object],
    mode: str,
) -> subprocess.CompletedProcess[str]:
    write_set_path = root.parent / "write-set.json"
    write_set_path.write_text(json.dumps(write_set), encoding="utf-8")
    script = """
import json
import os
from pathlib import Path
import signal
import sys

from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction

root = Path(sys.argv[1])
write_set = json.loads(Path(sys.argv[2]).read_text(encoding=\"utf-8\"))
mode = sys.argv[3]
journal = GreenfieldCommitJournal(repo_root=root, transaction_hash=\"a\" * 64, write_set=write_set)
journal.prepare()
transaction = GreenfieldApplyTransaction(
    root,
    paths=journal.paths,
    snapshot_root=journal.snapshot_root,
    retain_snapshot=True,
)
with transaction:
    journal.mark_prepared()
    journal.mark_applying({\"repository_write_set\": {\"write_set_hash\": write_set[\"write_set_hash\"]}})
    if mode == \"first_write\":
        original = greenfield_repository_write_set.atomic_write_bytes
        calls = 0
        def kill_after_first(path, data, *, mode=None, temporary_directory=None):
            global calls
            calls += 1
            result = original(path, data, mode=mode, temporary_directory=temporary_directory)
            if calls == 1:
                os.kill(os.getpid(), signal.SIGKILL)
            return result
        greenfield_repository_write_set.atomic_write_bytes = kill_after_first
    if mode == "after_delete":
        original = Path.unlink
        deleted = root / "odylith/radar/source/delete-second.md"
        def kill_after_delete(path, *, missing_ok=False):
            result = original(path, missing_ok=missing_ok)
            if path == deleted:
                os.kill(os.getpid(), signal.SIGKILL)
            return result
        Path.unlink = kill_after_delete
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
    )
    if mode == \"after_readback\":
        os.kill(os.getpid(), signal.SIGKILL)
"""
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}
    return subprocess.run(
        [sys.executable, "-c", script, str(root), str(write_set_path), mode],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )


def test_recovery_finalizes_applying_entry_when_after_state_is_already_durable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    expected_result = {"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}}
    journal.mark_applying(expected_result)
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
    )

    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert recovered == expected_result
    assert not journal.snapshot_root.exists()
    assert (journal.root / "state.v1.json").is_file()


def test_committed_receipt_recovery_cleans_retained_transaction_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    expected_result = {"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}}
    journal.mark_applying(expected_result)
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
        temporary_directory=journal.staging_root,
    )
    transaction.commit()
    journal.mark_committed(expected_result)

    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    assert recovered == expected_result
    assert not journal.snapshot_root.exists()
    assert not journal.staging_root.exists()


def test_committed_rollback_guard_preserves_after_state_when_interrupted(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
        temporary_directory=journal.staging_root,
    )
    transaction.commit()
    journal.mark_committed({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})

    transaction.__exit__(GreenfieldCommitInterrupted, GreenfieldCommitInterrupted("interrupt"), None)

    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first after\n"
    assert (root / "odylith/radar/source/second.md").read_text(encoding="utf-8") == "second after\n"


def test_same_hash_retry_discards_an_empty_prewrite_journal_orphan(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    )
    journal.root.mkdir(parents=True)

    recovered = journal.recover_or_return_committed()

    assert recovered is None
    assert not journal.root.exists()


def test_durable_recovery_ignores_snapshot_cleanup_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    expected_result = {"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}}
    journal.mark_applying(expected_result)
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
    )

    def fail_cleanup(_path: Path) -> None:
        raise OSError("snapshot cleanup failed")

    monkeypatch.setattr(greenfield_commit_journal.shutil, "rmtree", fail_cleanup)
    try:
        recovered = GreenfieldCommitJournal(
            repo_root=root,
            transaction_hash="a" * 64,
            write_set=write_set,
        ).recover_or_return_committed()
    finally:
        # ``shutil`` is a process-global module also used by pytest's tmp_path fixture.
        monkeypatch.undo()

    _release_signal_guard(transaction)
    assert recovered == expected_result


def test_recovery_rolls_back_partial_applying_entry_before_a_retry(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    _write(root / "odylith/radar/source/first.md", "first after\n")

    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert recovered is None
    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first before\n"
    assert (root / "odylith/radar/source/second.md").read_text(encoding="utf-8") == "second before\n"
    assert not journal.snapshot_root.exists()


def test_recovery_preserves_conflicting_operator_mutation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    changed = root / "odylith/radar/source/first.md"
    _write(changed, "operator mutation after interruption\n")

    with pytest.raises(greenfield_commit_journal.GreenfieldCommitJournalError) as exc_info:
        GreenfieldCommitJournal(
            repo_root=root,
            transaction_hash="a" * 64,
            write_set=write_set,
        ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert exc_info.value.failure_kind == "post_confirm_commit_recovery_conflict"
    assert changed.read_text(encoding="utf-8") == "operator mutation after interruption\n"
    assert journal.snapshot_root.is_dir()


def test_recovery_preserves_a_concurrent_mutation_elsewhere_in_the_governed_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    _write(root / "odylith/radar/source/first.md", "first after\n")
    changed = root / "odylith/radar/source/INDEX.md"
    _write(changed, "operator mutation after interruption\n")

    with pytest.raises(greenfield_commit_journal.GreenfieldCommitJournalError) as exc_info:
        GreenfieldCommitJournal(
            repo_root=root,
            transaction_hash="a" * 64,
            write_set=write_set,
        ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert exc_info.value.failure_kind == "post_confirm_commit_recovery_conflict"
    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first after\n"
    assert changed.read_text(encoding="utf-8") == "operator mutation after interruption\n"


def test_recovery_preserves_an_unknown_atomic_temp_sibling(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    temp = root / "odylith/radar/source/.first.md.interrupted.tmp"
    _write(temp, "first after\n")

    with pytest.raises(greenfield_commit_journal.GreenfieldCommitJournalError) as exc_info:
        GreenfieldCommitJournal(
            repo_root=root,
            transaction_hash="a" * 64,
            write_set=write_set,
        ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert exc_info.value.failure_kind == "post_confirm_commit_recovery_conflict"
    assert temp.read_text(encoding="utf-8") == "first after\n"


def test_recovery_preserves_an_unrelated_governed_root_mutation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    _write(root / "odylith/radar/source/first.md", "first after\n")
    changed = root / "odylith/casebook/INDEX.md"
    _write(changed, "operator mutation after interruption\n")

    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert recovered is None
    assert changed.read_text(encoding="utf-8") == "operator mutation after interruption\n"
    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first before\n"


def test_pending_v1_journal_moves_to_manual_recovery_without_blocking(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    transaction_hash = "a" * 64
    journal_root = root / ".odylith/runtime/greenfield/create-journal" / transaction_hash
    journal_root.mkdir(parents=True)
    record = {
        "version": "odylith.greenfield.commit_journal.v1",
        "transaction_hash": transaction_hash,
        "repository_write_set_hash": write_set["write_set_hash"],
        "snapshot_paths": list(greenfield_repository_write_set.greenfield_repository_write_paths(write_set)),
        "state": "prepared",
    }
    record["record_hash"] = greenfield_commit_journal._record_hash(record)  # noqa: SLF001
    (journal_root / "state.v1.json").write_text(json.dumps(record), encoding="utf-8")

    GreenfieldCommitJournal.recover_pending_journals(
        repo_root=root,
        excluding_transaction_hash="b" * 64,
    )

    quarantined = root / ".odylith/runtime/greenfield/create-journal/manual-recovery" / transaction_hash
    assert not journal_root.exists()
    assert (quarantined / "state.v1.json").is_file()


def test_recovery_rolls_back_a_safe_partial_new_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _new_directory_write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    _write(root / "odylith/radar/source/generated/first.md", "generated after\n")

    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert recovered is None
    assert not (root / "odylith/radar/source/generated").exists()


def test_recovery_preserves_an_unsealed_file_in_a_partial_new_directory(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _new_directory_write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    changed = root / "odylith/radar/source/generated/operator.md"
    _write(changed, "operator mutation after interruption\n")

    with pytest.raises(greenfield_commit_journal.GreenfieldCommitJournalError) as exc_info:
        GreenfieldCommitJournal(
            repo_root=root,
            transaction_hash="a" * 64,
            write_set=write_set,
        ).recover_or_return_committed()

    _release_signal_guard(transaction)
    assert exc_info.value.failure_kind == "post_confirm_commit_recovery_conflict"
    assert changed.read_text(encoding="utf-8") == "operator mutation after interruption\n"


def test_new_transaction_recovers_a_stranded_foreign_journal_before_preconditions(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal, transaction = _prepared_journal(root, write_set)
    journal.mark_applying({"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}})
    _write(root / "odylith/radar/source/first.md", "first after\n")

    GreenfieldCommitJournal.recover_pending_journals(
        repo_root=root,
        excluding_transaction_hash="b" * 64,
    )

    _release_signal_guard(transaction)
    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first before\n"
    assert (root / "odylith/radar/source/second.md").read_text(encoding="utf-8") == "second before\n"
    assert not journal.snapshot_root.exists()


def test_sigkill_after_first_sealed_write_recovers_the_preconfirm_tree(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)

    child = _kill_commit_child(root=root, write_set=write_set, mode="first_write")
    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    assert child.returncode == -signal.SIGKILL, child.stderr
    assert recovered is None
    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first before\n"
    assert (root / "odylith/radar/source/second.md").read_text(encoding="utf-8") == "second before\n"


def test_same_hash_recovery_releases_the_rolled_back_journal_for_reprepare(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    journal = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    )
    child = _kill_commit_child(root=root, write_set=write_set, mode="first_write")

    assert child.returncode == -signal.SIGKILL, child.stderr
    assert journal.recover_or_return_committed() is None
    assert json.loads(journal.state_path.read_text(encoding="utf-8"))["state"] == "rolled_back"

    journal.discard_recovered_rollback()
    assert not journal.root.exists()
    journal.prepare()
    assert json.loads(journal.state_path.read_text(encoding="utf-8"))["state"] == "preparing"


def test_sigkill_after_sealed_delete_recovers_the_preconfirm_tree(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    write_set = _delete_write_set(root)

    child = _kill_commit_child(root=root, write_set=write_set, mode="after_delete")
    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    assert child.returncode == -signal.SIGKILL, child.stderr
    assert recovered is None
    assert (root / "odylith/radar/source/first.md").read_text(encoding="utf-8") == "first before\n"
    assert (root / "odylith/radar/source/delete.md").read_text(encoding="utf-8") == "delete before\n"
    assert (
        root / "odylith/radar/source/delete-second.md"
    ).read_text(encoding="utf-8") == "delete second before\n"


def test_sigkill_after_final_readback_finalizes_the_durable_receipt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)

    child = _kill_commit_child(root=root, write_set=write_set, mode="after_readback")
    recovered = GreenfieldCommitJournal(
        repo_root=root,
        transaction_hash="a" * 64,
        write_set=write_set,
    ).recover_or_return_committed()

    assert child.returncode == -signal.SIGKILL, child.stderr
    assert recovered == {"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}}
    record_path = root / ".odylith/runtime/greenfield/create-journal" / ("a" * 64) / "state.v1.json"
    record = json.loads(record_path.read_text())
    assert "recovery_write_set" not in record
    greenfield_repository_write_set.require_greenfield_repository_after_state(
        repo_root=root,
        write_set=write_set,
    )


def test_same_hash_retry_returns_the_durable_result_without_reapplying(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(repo_root=tmp_path)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    first_result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction.transaction_file,
        transaction_hash=transaction.transaction_hash,
        confirm=True,
        started_at=0.0,
    )

    def forbidden_write(**_kwargs: object) -> dict[str, object]:
        raise AssertionError("a durable same-hash receipt must bypass the write path")

    monkeypatch.setattr(
        greenfield_create_commit.greenfield_compiled_write,
        "write_compiled_greenfield_package",
        forbidden_write,
    )
    retry_result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction.transaction_file,
        transaction_hash=transaction.transaction_hash,
        confirm=True,
        started_at=0.0,
    )

    assert retry_result == first_result


def test_commit_stages_atomic_writes_outside_governed_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    write_set = _write_set(root)
    staging_root = root / ".odylith/runtime/greenfield/create-journal" / ("a" * 64) / "staging"
    seen_staging_roots: list[Path | None] = []
    real_write = greenfield_repository_write_set.atomic_write_bytes

    def capture_staging(
        path: Path,
        data: bytes,
        *,
        mode: int | None = None,
        temporary_directory: Path | None = None,
    ) -> Path:
        seen_staging_roots.append(temporary_directory)
        return real_write(path, data, mode=mode, temporary_directory=temporary_directory)

    monkeypatch.setattr(greenfield_repository_write_set, "atomic_write_bytes", capture_staging)
    greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=root,
        write_set=write_set,
        temporary_directory=staging_root,
    )

    assert seen_staging_roots
    assert set(seen_staging_roots) == {staging_root}
    assert staging_root.is_dir()
    assert list(staging_root.iterdir()) == []


def test_same_hash_retry_refuses_to_hide_post_commit_repository_drift(tmp_path: Path) -> None:
    transaction = _transaction(repo_root=tmp_path)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=transaction.transaction_file,
        transaction_hash=transaction.transaction_hash,
        confirm=True,
        started_at=0.0,
    )
    changed = tmp_path / "odylith/radar/source/INDEX.md"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("operator change\n", encoding="utf-8")

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc_info:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert exc_info.value.failure_kind == "post_confirm_committed_state_drift"
    assert exc_info.value.rollback_status == "not_started"
