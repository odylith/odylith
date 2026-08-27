"""Crash recovery and idempotent receipts for sealed Greenfield commits."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_create_lifecycle
from odylith.runtime.domain_intelligence import greenfield_commit_recovery
from odylith.runtime.domain_intelligence import greenfield_commit_journal_store
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.domain_intelligence.greenfield_transaction import snapshot_missing_marker_token


JOURNAL_VERSION = "odylith.greenfield.commit_journal.v3"
_LEGACY_JOURNAL_VERSIONS = frozenset(
    {"odylith.greenfield.commit_journal.v1", "odylith.greenfield.commit_journal.v2"}
)
_STATES = frozenset(
    {
        "preparing",
        "prepared",
        "projecting",
        "published",
        "verified",
        "closed",
        "aborted",
        "recovery_required",
    }
)


class GreenfieldCommitJournalError(RuntimeError):
    """A durable commit receipt is missing, malformed, or cannot be recovered."""

    def __init__(self, message: str, *, failure_kind: str, recovery_path: str = "") -> None:
        super().__init__(message)
        self.failure_kind = failure_kind
        self.recovery_path = recovery_path


class GreenfieldCommitJournal:
    """Own a transaction-hash journal across the commit-only write boundary."""

    def __init__(self, *, repo_root: Path, transaction_hash: str, write_set: object) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.write_set = greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(
            write_set,
        )
        self.transaction_hash = _require_digest(transaction_hash, label="transaction hash")
        self.write_set_hash = _require_digest(str(self.write_set["write_set_hash"]), label="write-set hash")
        self.paths = greenfield_repository_write_set.greenfield_repository_recovery_paths(self.write_set)
        self.root_token = f".odylith/runtime/greenfield/create-journal/{self.transaction_hash}"
        self.root = self.repo_root / self.root_token
        self.snapshot_token = f"{self.root_token}/snapshot"
        self.staging_token = f"{self.root_token}/staging"
        self.snapshot_root = self.root / "snapshot"
        self.staging_root = self.root / "staging"
        self.state_path = self.root / "state.v1.json"

    @property
    def recovery_path(self) -> str:
        return (
            str(self.root)
            if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.root_token)
            != "missing"
            else ""
        )

    @classmethod
    def recover_pending_journals(cls, *, repo_root: Path, excluding_transaction_hash: str) -> None:
        """Settle stranded transactions before another create checks preconditions."""

        root = Path(repo_root).expanduser().resolve()
        journal_parent_token = ".odylith/runtime/greenfield/create-journal"
        journal_parent = root / journal_parent_token
        if greenfield_transaction_path_boundary.path_kind(root, journal_parent_token) == "missing":
            return
        if greenfield_transaction_path_boundary.path_kind(root, journal_parent_token) != "directory":
            raise GreenfieldCommitJournalError(
                "greenfield commit journal directory is not a safe directory",
                failure_kind="post_confirm_commit_environment_or_io_failure",
                recovery_path=str(journal_parent),
            )
        excluded = _require_digest(excluding_transaction_hash, label="transaction hash")
        for entry in greenfield_transaction_path_boundary.list_directory(root, journal_parent_token):
            entry_token = entry.path
            entry_path = root / entry_token
            name = Path(entry_token).name
            if name == "manual-recovery":
                if entry.kind != "directory":
                    raise GreenfieldCommitJournalError(
                        "greenfield commit journal manual-recovery entry is unsafe",
                        failure_kind="post_confirm_commit_environment_or_io_failure",
                        recovery_path=str(entry_path),
                    )
                continue
            if name.startswith(".prepare-") and entry.kind == "directory":
                greenfield_transaction_path_boundary.remove_tree(root, entry_token)
                continue
            if entry.kind != "directory":
                raise GreenfieldCommitJournalError(
                    "greenfield commit journal directory contains an unsafe entry",
                    failure_kind="post_confirm_commit_environment_or_io_failure",
                    recovery_path=str(entry_path),
                )
            if greenfield_commit_journal_store.is_empty_prewrite_orphan(root, entry_token):
                greenfield_transaction_path_boundary.remove_tree(root, entry_token)
                continue
            record = _read_journal_record(root, entry_token)
            if str(record.get("version", "")) in _LEGACY_JOURNAL_VERSIONS:
                try:
                    greenfield_commit_journal_store.quarantine_legacy_journal(
                        root,
                        entry_token,
                        journal_parent_token=journal_parent_token,
                    )
                except ValueError as exc:
                    raise GreenfieldCommitJournalError(
                        str(exc),
                        failure_kind="post_confirm_commit_environment_or_io_failure",
                        recovery_path=str(entry_path),
                    ) from exc
                continue
            if str(record.get("version", "")) != JOURNAL_VERSION:
                raise GreenfieldCommitJournalError(
                    "greenfield commit journal version is unsupported",
                    failure_kind="post_confirm_commit_invariant_failure",
                    recovery_path=str(entry_path),
                )
            transaction_hash = _require_digest(
                str(record.get("transaction_hash", "")),
                label="transaction hash",
            )
            if str(record["state"]) == "closed":
                try:
                    greenfield_commit_journal_store.discard_committed_artifacts(root, entry_token)
                except ValueError as exc:
                    raise GreenfieldCommitJournalError(
                        str(exc),
                        failure_kind="post_confirm_commit_environment_or_io_failure",
                        recovery_path=str(entry_path),
                    ) from exc
                continue
            if transaction_hash == excluded:
                continue
            if str(record["state"]) in {"projecting", "published", "recovery_required"}:
                recovery_write_set = record.get("recovery_write_set")
                journal = cls(
                    repo_root=root,
                    transaction_hash=transaction_hash,
                    write_set=recovery_write_set,
                )
                journal.recover_or_return_committed()
                continue
            if str(record["state"]) in {"preparing", "prepared", "aborted"}:
                greenfield_transaction_path_boundary.remove_tree(root, entry_token)
                continue
            raise GreenfieldCommitJournalError(
                "greenfield commit journal state is invalid",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(entry_path),
            )

    def recover_or_return_committed(self) -> dict[str, Any] | None:
        """Recover one interrupted apply, or return a verified same-hash receipt."""

        if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.root_token) == "missing":
            return None
        if greenfield_commit_journal_store.is_empty_prewrite_orphan(
            self.repo_root,
            self.root_token,
        ):
            self._discard_journal()
            return None
        record = self._read_record()
        state = str(record["state"])
        if state == "closed":
            result = self._verified_published_result(record, drift_kind="post_confirm_committed_state_drift")
            self._discard_snapshot()
            self._discard_staging()
            return result
        if state == "projecting":
            if self._record_generation_is_active(record):
                self._write_record(
                    state="published",
                    commit_result=self._record_result(record),
                    recovery_write_set=self.write_set,
                    generation_manifest_sha256=self._record_generation_manifest_hash(record),
                )
                record = self._read_record()
                state = "published"
            else:
                self._abort_projecting_transaction()
                return None
        if state == "published":
            try:
                result = self._verified_published_result(
                    record,
                    drift_kind="post_confirm_published_state_drift",
                )
            except GreenfieldCommitJournalError:
                self._write_record(
                    state="recovery_required",
                    commit_result=self._record_result(record),
                    recovery_write_set=self.write_set,
                    generation_manifest_sha256=self._record_generation_manifest_hash(record),
                )
                raise
            self._write_record(
                state="closed",
                commit_result=result,
                recovery_write_set=self.write_set,
                generation_manifest_sha256=self._record_generation_manifest_hash(record),
            )
            self._discard_snapshot()
            self._discard_staging()
            return result
        if state == "recovery_required":
            raise GreenfieldCommitJournalError(
                "published Greenfield generation requires explicit recovery",
                failure_kind="post_confirm_published_recovery_required",
                recovery_path=self.recovery_path,
            )
        if state in {"preparing", "prepared", "aborted"}:
            self._discard_journal()
            return None
        raise GreenfieldCommitJournalError(
            f"greenfield commit journal has unsupported state: {state}",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=self.recovery_path,
        )

    def _verified_published_result(self, record: Mapping[str, Any], *, drift_kind: str) -> dict[str, Any]:
        result = self._record_result(record)
        try:
            if not self._record_generation_is_active(record):
                raise RuntimeError("active pointer does not name this transaction")
            pinned = greenfield_generation_store.pin_greenfield_generation(
                repo_root=self.repo_root,
                transaction_hash=self.transaction_hash,
                expected_write_set=self.write_set,
            )
            if pinned.manifest_sha256 != self._record_generation_manifest_hash(record):
                raise RuntimeError("generation manifest hash differs from the journal")
            greenfield_repository_write_set.require_greenfield_repository_after_state(
                repo_root=self.repo_root,
                write_set=self.write_set,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise GreenfieldCommitJournalError(
                "confirmed Greenfield transaction publication state changed",
                failure_kind=drift_kind,
                recovery_path=self.recovery_path,
            ) from exc
        return result

    def _abort_projecting_transaction(self) -> None:
        if not self._safe_to_restore_interrupted_snapshot():
            raise GreenfieldCommitJournalError(
                "greenfield commit recovery found a concurrent managed-path mutation; "
                "the retained snapshot was preserved without rollback",
                failure_kind="post_confirm_commit_recovery_conflict",
                recovery_path=self.recovery_path,
            )
        self._restore_interrupted_snapshot()
        try:
            greenfield_repository_write_set.require_greenfield_repository_recovery_preconditions(
                repo_root=self.repo_root,
                write_set=self.write_set,
            )
        except (OSError, ValueError) as exc:
            raise GreenfieldCommitJournalError(
                "greenfield commit recovery did not restore the repository to its pre-confirm state",
                failure_kind="post_confirm_commit_environment_or_io_failure",
                recovery_path=self.recovery_path,
            ) from exc
        self._write_record(state="aborted")
        greenfield_generation_store.discard_unpublished_greenfield_generation(
            repo_root=self.repo_root,
            transaction_hash=self.transaction_hash,
        )
        self._discard_snapshot()
        self._discard_staging()

    def _record_generation_is_active(self, record: Mapping[str, Any]) -> bool:
        return greenfield_generation_state.active_generation_is(
            repo_root=self.repo_root,
            transaction_hash=self.transaction_hash,
            write_set_hash=self.write_set_hash,
            generation_manifest_sha256=self._record_generation_manifest_hash(record),
        )

    def _record_result(self, record: Mapping[str, Any]) -> dict[str, Any]:
        result = record.get("commit_result")
        if not isinstance(result, Mapping):
            raise GreenfieldCommitJournalError(
                "Greenfield transaction journal is missing its sealed commit result",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        return _json_mapping(result)

    def _record_generation_manifest_hash(self, record: Mapping[str, Any]) -> str:
        return _require_digest(
            str(record.get("generation_manifest_sha256") or ""),
            label="generation manifest hash",
        )

    def prepare(self) -> None:
        if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.root_token) != "missing":
            raise GreenfieldCommitJournalError(
                "greenfield commit journal already exists before prepare",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        parent_token = str(Path(self.root_token).parent)
        greenfield_transaction_path_boundary.ensure_directory(self.repo_root, parent_token)
        temporary_token = greenfield_transaction_path_boundary.make_temporary_directory(
            self.repo_root,
            parent_token,
            prefix=".prepare-",
        )
        try:
            _write_journal_record(
                self.repo_root,
                temporary_token,
                self._record_payload(state="preparing"),
            )
            greenfield_transaction_path_boundary.rename_directory(
                self.repo_root,
                temporary_token,
                self.root_token,
            )
        except BaseException:
            try:
                greenfield_transaction_path_boundary.remove_tree(self.repo_root, temporary_token)
            except (FileNotFoundError, greenfield_transaction_path_boundary.GreenfieldTransactionPathError):
                pass
            raise

    def mark_prepared(self) -> None:
        self._require_state("preparing")
        if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.snapshot_token) != "directory":
            raise GreenfieldCommitJournalError(
                "greenfield commit journal cannot enter prepared state without a rollback snapshot",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        self._write_record(state="prepared")

    def mark_projecting(self, result: Mapping[str, Any], *, generation_manifest_sha256: str) -> None:
        self._require_state("prepared")
        self._prepare_staging_root()
        self._write_record(
            state="projecting",
            commit_result=result,
            recovery_write_set=self.write_set,
            generation_manifest_sha256=generation_manifest_sha256,
        )

    def mark_published(self, result: Mapping[str, Any], *, generation_manifest_sha256: str) -> None:
        self._require_state("projecting")
        self._write_record(
            state="published",
            commit_result=result,
            recovery_write_set=self.write_set,
            generation_manifest_sha256=generation_manifest_sha256,
        )

    def mark_closed(self, result: Mapping[str, Any], *, generation_manifest_sha256: str) -> dict[str, Any]:
        self._require_state("published")
        self._write_record(
            state="closed",
            commit_result=result,
            recovery_write_set=self.write_set,
            generation_manifest_sha256=generation_manifest_sha256,
        )
        return _json_mapping(result)

    def mark_recovery_required(
        self,
        result: Mapping[str, Any],
        *,
        generation_manifest_sha256: str,
    ) -> None:
        state = str(self._read_record().get("state") or "")
        if state == "recovery_required":
            return
        if state == "projecting" and greenfield_generation_state.active_generation_is(
            repo_root=self.repo_root,
            transaction_hash=self.transaction_hash,
            write_set_hash=self.write_set_hash,
            generation_manifest_sha256=generation_manifest_sha256,
        ):
            self.mark_published(
                result,
                generation_manifest_sha256=generation_manifest_sha256,
            )
            state = "published"
        if state != "published":
            raise GreenfieldCommitJournalError(
                "greenfield journal cannot require recovery before publication",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        self._write_record(
            state="recovery_required",
            commit_result=result,
            recovery_write_set=self.write_set,
            generation_manifest_sha256=generation_manifest_sha256,
        )

    def mark_aborted(self) -> None:
        if (
            greenfield_transaction_path_boundary.path_kind(self.repo_root, self.root_token) == "missing"
            or self._read_record().get("state") == "aborted"
        ):
            return
        self._write_record(state="aborted")
        greenfield_generation_store.discard_unpublished_greenfield_generation(
            repo_root=self.repo_root,
            transaction_hash=self.transaction_hash,
        )
        self._discard_snapshot()
        self._discard_staging()

    def discard_recovered_abort(self) -> None:
        """Remove a settled same-hash abort before retrying its sealed commit."""

        if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.root_token) == "missing":
            return
        if str(self._read_record().get("state") or "") != "aborted":
            raise GreenfieldCommitJournalError(
                "greenfield commit journal cannot discard a recovery that did not abort",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        self._discard_journal()

    def discard_committed_snapshot(self) -> None:
        """Remove retained rollback bytes after a committed receipt is durable."""

        self._require_state("closed")
        self._discard_snapshot()
        self._discard_staging()

    def _restore_interrupted_snapshot(self) -> None:
        if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.snapshot_token) != "directory":
            raise GreenfieldCommitJournalError(
                "greenfield commit recovery cannot find the durable rollback snapshot",
                failure_kind="post_confirm_commit_environment_or_io_failure",
                recovery_path=self.recovery_path,
            )
        try:
            GreenfieldApplyTransaction.restore_snapshot(
                self.repo_root,
                paths=self.paths,
                snapshot_root=self.snapshot_root,
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise GreenfieldCommitJournalError(
                "greenfield commit recovery could not restore the interrupted write set",
                failure_kind="post_confirm_commit_environment_or_io_failure",
                recovery_path=self.recovery_path,
            ) from exc

    def _safe_to_restore_interrupted_snapshot(self) -> bool:
        """Return whether every snapshot-owned path has only sealed pre/post states."""

        try:
            writes = {
                str(row["path"]): (
                    greenfield_repository_write_set._decoded_after_image_bytes(  # noqa: SLF001
                        {
                            str(item["path"]): item
                            for item in self.write_set["after_image"]["files"]
                        }[str(row["path"])]
                    ),
                    int(row["mode"]),
                )
                for row in self.write_set["writes"]
            }
            deletes = {str(row["path"]) for row in self.write_set["deletes"]}
            created_directories = {str(row["path"]) for row in self.write_set["directories"]}
            deleted_directories = {str(row["path"]) for row in self.write_set["directory_deletes"]}
            for owner in self.paths:
                before_files, before_directories = greenfield_commit_recovery.snapshot_tree(
                    self.repo_root,
                    f"{self.snapshot_token}/{owner}",
                    owner=owner,
                    required=True,
                    missing_marker=snapshot_missing_marker_token(self.snapshot_token, owner),
                )
                current_files, current_directories = greenfield_commit_recovery.snapshot_tree(
                    self.repo_root,
                    owner,
                    owner=owner,
                    required=False,
                )
                if not greenfield_commit_recovery.safe_interrupted_tree(
                    owner=owner,
                    before_files=before_files,
                    before_directories=before_directories,
                    current_files=current_files,
                    current_directories=current_directories,
                    writes=writes,
                    deletes=deletes,
                    created_directories=created_directories,
                    deleted_directories=deleted_directories,
                ):
                    return False
        except (OSError, RuntimeError, ValueError):
            return False
        return True

    def _prepare_staging_root(self) -> None:
        if greenfield_transaction_path_boundary.path_kind(self.repo_root, self.staging_token) != "missing":
            raise GreenfieldCommitJournalError(
                "greenfield commit journal staging directory already exists",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        greenfield_transaction_path_boundary.ensure_directory(self.repo_root, self.staging_token)

    def _discard_snapshot(self) -> None:
        try:
            greenfield_transaction_path_boundary.remove_path(
                self.repo_root,
                self.snapshot_token,
                missing_ok=True,
            )
        except (OSError, ValueError):
            pass

    def _discard_staging(self) -> None:
        try:
            greenfield_transaction_path_boundary.remove_path(
                self.repo_root,
                self.staging_token,
                missing_ok=True,
            )
        except (OSError, ValueError):
            pass

    def _discard_journal(self) -> None:
        greenfield_transaction_path_boundary.remove_tree(self.repo_root, self.root_token)

    def _require_state(self, expected: str) -> None:
        actual = str(self._read_record().get("state") or "")
        if actual != expected:
            raise GreenfieldCommitJournalError(
                f"greenfield commit journal expected {expected} state but found {actual or 'missing'}",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )

    def _read_record(self) -> dict[str, Any]:
        record = _read_journal_record(self.repo_root, self.root_token)
        if str(record.get("transaction_hash", "")) != self.transaction_hash:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal transaction hash does not match the confirmed transaction",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        if str(record.get("repository_write_set_hash", "")) != self.write_set_hash:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal write-set hash does not match the confirmed transaction",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        if tuple(record.get("snapshot_paths") or ()) != self.paths:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal snapshot boundary does not match the confirmed transaction",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        if str(record.get("state", "")) not in _STATES:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal state is invalid",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        if str(record["state"]) in {"projecting", "published", "closed", "recovery_required"}:
            try:
                recovery_write_set = greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(
                    record.get("recovery_write_set"),
                )
            except ValueError as exc:
                raise GreenfieldCommitJournalError(
                    "greenfield commit journal is missing its sealed recovery write set",
                    failure_kind="post_confirm_commit_invariant_failure",
                    recovery_path=self.recovery_path,
                ) from exc
            if str(recovery_write_set["write_set_hash"]) != self.write_set_hash:
                raise GreenfieldCommitJournalError(
                    "greenfield commit journal recovery write set does not match the confirmed transaction",
                    failure_kind="post_confirm_commit_invariant_failure",
                    recovery_path=self.recovery_path,
                )
            self._record_result(record)
            self._record_generation_manifest_hash(record)
        return record

    def _write_record(
        self,
        *,
        state: str,
        commit_result: Mapping[str, Any] | None = None,
        recovery_write_set: Mapping[str, Any] | None = None,
        generation_manifest_sha256: str = "",
    ) -> None:
        current = self._read_record()
        history = current.get("lifecycle_history")
        if not isinstance(history, list):
            history = list(greenfield_create_lifecycle.lifecycle_history_for_journal_state(str(current["state"])))
        lifecycle_history = greenfield_create_lifecycle.advance_lifecycle_for_journal_state(history, state)
        _write_journal_record(
            self.repo_root,
            self.root_token,
            self._record_payload(
                state=state,
                commit_result=commit_result,
                recovery_write_set=recovery_write_set,
                generation_manifest_sha256=generation_manifest_sha256,
                lifecycle_history=lifecycle_history,
            ),
        )

    def _record_payload(
        self,
        *,
        state: str,
        commit_result: Mapping[str, Any] | None = None,
        recovery_write_set: Mapping[str, Any] | None = None,
        generation_manifest_sha256: str = "",
        lifecycle_history: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        if state not in _STATES:
            raise ValueError(f"unsupported greenfield commit journal state: {state}")
        history = greenfield_create_lifecycle.require_create_lifecycle_history(
            lifecycle_history or greenfield_create_lifecycle.lifecycle_history_for_journal_state(state)
        )
        record: dict[str, Any] = {
            "version": JOURNAL_VERSION,
            "lifecycle_version": greenfield_create_lifecycle.CREATE_LIFECYCLE_VERSION,
            "lifecycle_state": history[-1],
            "lifecycle_history": list(history),
            "transaction_hash": self.transaction_hash,
            "repository_write_set_hash": self.write_set_hash,
            "snapshot_paths": list(self.paths),
            "state": state,
        }
        if commit_result is not None:
            record["commit_result"] = _json_mapping(commit_result)
        if recovery_write_set is not None:
            record["recovery_write_set"] = dict(recovery_write_set)
        if generation_manifest_sha256:
            record["generation_manifest_sha256"] = _require_digest(
                generation_manifest_sha256,
                label="generation manifest hash",
            )
        record["record_hash"] = greenfield_commit_journal_store.record_hash(record)
        return record


def _write_journal_record(repo_root: Path, journal_token: str, record: Mapping[str, Any]) -> None:
    try:
        greenfield_commit_journal_store.write_record(repo_root, journal_token, record)
    except (OSError, ValueError) as exc:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal could not persist its transaction state",
            failure_kind="post_confirm_commit_environment_or_io_failure",
            recovery_path=str(Path(repo_root) / journal_token),
        ) from exc


def _read_journal_record(repo_root: Path, journal_token: str) -> dict[str, Any]:
    state_path = f"{journal_token}/state.v1.json"
    try:
        payload = json.loads(
            greenfield_transaction_path_boundary.read_bytes(repo_root, state_path).decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state cannot be read",
            failure_kind="post_confirm_commit_environment_or_io_failure",
            recovery_path=str(Path(repo_root) / journal_token),
        ) from exc
    if not isinstance(payload, Mapping):
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state is malformed",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(Path(repo_root) / journal_token),
        )
    record = dict(payload)
    digest = str(record.pop("record_hash", "")).strip()
    if digest != greenfield_commit_journal_store.record_hash(record):
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state hash mismatch",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(Path(repo_root) / journal_token),
        )
    if str(record.get("version", "")) in _LEGACY_JOURNAL_VERSIONS:
        return record
    if str(record.get("state", "")) not in _STATES:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state is invalid",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(Path(repo_root) / journal_token),
        )
    lifecycle_version = str(record.get("lifecycle_version") or "")
    if lifecycle_version:
        if lifecycle_version != greenfield_create_lifecycle.CREATE_LIFECYCLE_VERSION:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal lifecycle version is unsupported",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(Path(repo_root) / journal_token),
            )
        try:
            history = greenfield_create_lifecycle.require_create_lifecycle_history(record.get("lifecycle_history"))
        except ValueError as exc:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal lifecycle history is invalid",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(Path(repo_root) / journal_token),
            ) from exc
        if str(record.get("lifecycle_state") or "") != history[-1]:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal lifecycle state does not match its history",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(Path(repo_root) / journal_token),
            )
    return record


def _require_digest(value: str, *, label: str) -> str:
    candidate = str(value).strip()
    if len(candidate) != 64 or any(character not in "0123456789abcdef" for character in candidate):
        raise ValueError(f"greenfield commit journal {label} is invalid")
    return candidate


def _json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(json.dumps(dict(value), sort_keys=True, ensure_ascii=True))
    except (TypeError, ValueError) as exc:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal result is not serializable",
            failure_kind="post_confirm_commit_invariant_failure",
        ) from exc
    if not isinstance(payload, dict):
        raise GreenfieldCommitJournalError(
            "greenfield commit journal result is malformed",
            failure_kind="post_confirm_commit_invariant_failure",
        )
    return payload


__all__ = ["GreenfieldCommitJournal", "GreenfieldCommitJournalError", "JOURNAL_VERSION"]
