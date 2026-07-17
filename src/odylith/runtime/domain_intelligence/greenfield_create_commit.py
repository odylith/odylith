"""Commit-only executor for verified greenfield create transactions."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import time
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_compiler_provenance,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_verified,
)
from odylith.runtime.domain_intelligence.greenfield_create_manifest import (
    finalize_greenfield_commit_manifest,
)
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournalError
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldCommitInterrupted


class GreenfieldCreateCommitError(RuntimeError):
    """Post-confirm commit failure after the compiled transaction entered the write boundary."""

    def __init__(
        self,
        message: str,
        *,
        rollback_status: str,
        rollback_error: str = "",
        root_cause: BaseException | None = None,
        failure_kind: str = "post_confirm_commit_invariant_failure",
        recovery_path: str = "",
    ) -> None:
        super().__init__(message)
        self.rollback_status = rollback_status
        self.rollback_error = rollback_error
        self.root_cause_type = type(root_cause).__name__ if root_cause is not None else ""
        self.failure_kind = failure_kind
        self.recovery_path = recovery_path

    def to_dict(self) -> dict[str, str]:
        payload = {
            "failure_kind": self.failure_kind,
            "rollback_status": self.rollback_status,
            "root_cause_type": self.root_cause_type,
        }
        if self.rollback_error:
            payload["rollback_error"] = self.rollback_error
        if self.recovery_path:
            payload["recovery_path"] = self.recovery_path
        return payload


def commit_greenfield_create_transaction(
    *,
    repo_root: Path,
    transaction: ProductCreateTransaction,
    confirm: bool,
    started_at: float | None = None,
) -> dict[str, Any]:
    """Verify and commit an already compiled ProductCreateTransaction."""

    if not confirm:
        raise ValueError("--confirm is required before greenfield apply writes accepted product records")
    root = Path(repo_root).expanduser().resolve()
    require_product_create_transaction_verified(transaction)
    require_product_create_transaction_intent_authority(transaction, repo_root=root)
    require_product_create_transaction_compiler_provenance(transaction, repo_root=root)
    started = time.perf_counter() if started_at is None else float(started_at)
    write_transaction: GreenfieldApplyTransaction | None = None
    journal: GreenfieldCommitJournal | None = None
    try:
        with _greenfield_commit_lock(root):
            GreenfieldCommitJournal.recover_pending_journals(
                repo_root=root,
                excluding_transaction_hash=transaction.transaction_hash,
            )
            sealed_write_set = transaction.prewrite_package.repository_write_set
            journal = GreenfieldCommitJournal(
                repo_root=root,
                transaction_hash=transaction.transaction_hash,
                write_set=sealed_write_set,
            )
            committed_result = journal.recover_or_return_committed()
            if committed_result is not None:
                return committed_result
            write_set = greenfield_repository_write_set.require_greenfield_repository_preconditions(
                repo_root=root,
                write_set=sealed_write_set,
            )
            journal.prepare()
            write_transaction = GreenfieldApplyTransaction(
                root,
                paths=journal.paths,
                snapshot_root=journal.snapshot_root,
                retain_snapshot=True,
            )
            with write_transaction:
                journal.mark_prepared()
                result = greenfield_compiled_write.compiled_greenfield_commit_result(transaction=transaction)
                final_manifest = finalize_greenfield_commit_manifest(
                    transaction.quality_manifest,
                    whole_project_elapsed_seconds=time.perf_counter() - started,
                    write_transaction_status="committed",
                )
                final_manifest["product_create_transaction"] = transaction.summary()
                write_manifest = dict(final_manifest.get("write_transaction") or {})
                write_manifest["product_create_transaction_hash"] = transaction.transaction_hash
                write_manifest["repository_write_set_hash"] = str(write_set["write_set_hash"])
                write_manifest["commit_only"] = True
                final_manifest["write_transaction"] = write_manifest
                final_manifest["whole_project_elapsed_seconds"] = round(time.perf_counter() - started, 3)
                result["commit_manifest"] = final_manifest
                result["product_create_transaction"] = transaction.summary()
                journal.mark_applying(result)
                actual_result = greenfield_compiled_write.write_compiled_greenfield_package(
                    root=root,
                    transaction=transaction,
                    temporary_directory=journal.staging_root,
                )
                expected_result = greenfield_compiled_write.compiled_greenfield_commit_result(
                    transaction=transaction,
                )
                if actual_result != expected_result:
                    raise RuntimeError("compiled Greenfield commit result drifted after materialization")
                write_transaction.commit()
                result = journal.mark_committed(result)
            try:
                journal.discard_committed_snapshot()
            except OSError:
                pass
    except BaseException as exc:
        if isinstance(exc, GreenfieldCreateCommitError):
            raise
        if isinstance(exc, ValueError) and write_transaction is None:
            raise
        if (
            journal is not None
            and write_transaction is not None
            and write_transaction.rollback_status == "rolled_back"
        ):
            try:
                journal.mark_rolled_back()
            except GreenfieldCommitJournalError:
                pass
        rollback_status = write_transaction.rollback_status if write_transaction is not None else "not_started"
        rollback_phrase = (
            "rollback completed; no governed records were committed"
            if rollback_status == "rolled_back"
            else f"rollback_status={rollback_status}; commit did not complete"
        )
        raise GreenfieldCreateCommitError(
            "greenfield create failed while committing the verified ProductCreateTransaction; "
            f"{rollback_phrase}. "
            f"Root cause: {exc}",
            rollback_status=rollback_status,
            rollback_error=write_transaction.rollback_error if write_transaction is not None else "",
            root_cause=exc,
            failure_kind=(
                exc.failure_kind
                if isinstance(exc, GreenfieldCommitJournalError)
                else "post_confirm_commit_interrupted"
                if isinstance(exc, (GreenfieldCommitInterrupted, KeyboardInterrupt, SystemExit))
                else "post_confirm_commit_environment_or_io_failure"
                if isinstance(exc, OSError)
                else "post_confirm_commit_invariant_failure"
            ),
            recovery_path=(
                write_transaction.recovery_path
                if write_transaction is not None and write_transaction.recovery_path
                else exc.recovery_path
                if isinstance(exc, GreenfieldCommitJournalError)
                else journal.recovery_path
                if journal is not None
                else ""
            ),
        ) from exc
    return result


@contextmanager
def _greenfield_commit_lock(repo_root: Path):
    """Serialize cooperating create transactions across the exact write boundary."""

    lock_path = Path(repo_root) / ".odylith" / "runtime" / "greenfield" / "create.lock"
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
    except OSError as exc:
        raise GreenfieldCreateCommitError(
            "greenfield create could not acquire its repository commit lock; no governed records were written",
            rollback_status="not_started",
            root_cause=exc,
            failure_kind="post_confirm_commit_environment_or_io_failure",
        ) from exc
    with handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GreenfieldCreateCommitError(
                "another greenfield create transaction is already committing; retry after it finishes",
                rollback_status="not_started",
                root_cause=exc,
                failure_kind="post_confirm_repository_busy",
            ) from exc
        except OSError as exc:
            raise GreenfieldCreateCommitError(
                "greenfield create could not acquire its repository commit lock; no governed records were written",
                rollback_status="not_started",
                root_cause=exc,
                failure_kind="post_confirm_commit_environment_or_io_failure",
            ) from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = [
    "GreenfieldCreateCommitError",
    "commit_greenfield_create_transaction",
]
