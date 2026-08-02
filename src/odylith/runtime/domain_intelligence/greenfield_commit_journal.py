"""Crash recovery and idempotent receipts for sealed Greenfield commits."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text
from odylith.install.fs import fsync_directory
from odylith.runtime.domain_intelligence import greenfield_create_lifecycle
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


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
        self.root = (
            self.repo_root / ".odylith" / "runtime" / "greenfield" / "create-journal" / self.transaction_hash
        )
        self.snapshot_root = self.root / "snapshot"
        self.staging_root = self.root / "staging"
        self.state_path = self.root / "state.v1.json"

    @property
    def recovery_path(self) -> str:
        return str(self.root) if self.root.exists() else ""

    @classmethod
    def recover_pending_journals(cls, *, repo_root: Path, excluding_transaction_hash: str) -> None:
        """Settle stranded transactions before another create checks preconditions."""

        root = Path(repo_root).expanduser().resolve()
        journal_parent = root / ".odylith" / "runtime" / "greenfield" / "create-journal"
        if not journal_parent.exists():
            return
        if journal_parent.is_symlink() or not journal_parent.is_dir():
            raise GreenfieldCommitJournalError(
                "greenfield commit journal directory is not a safe directory",
                failure_kind="post_confirm_commit_environment_or_io_failure",
                recovery_path=str(journal_parent),
            )
        excluded = _require_digest(excluding_transaction_hash, label="transaction hash")
        for entry in sorted(journal_parent.iterdir(), key=lambda item: item.name):
            if entry.name == "manual-recovery":
                if entry.is_symlink() or not entry.is_dir():
                    raise GreenfieldCommitJournalError(
                        "greenfield commit journal manual-recovery directory is not safe",
                        failure_kind="post_confirm_commit_environment_or_io_failure",
                        recovery_path=str(entry),
                    )
                continue
            if entry.name.startswith(".prepare-") and entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
                fsync_directory(journal_parent)
                continue
            if entry.is_symlink() or not entry.is_dir():
                raise GreenfieldCommitJournalError(
                    "greenfield commit journal directory contains an unsafe entry",
                    failure_kind="post_confirm_commit_environment_or_io_failure",
                    recovery_path=str(entry),
                )
            if _is_empty_prewrite_orphan(entry):
                shutil.rmtree(entry)
                fsync_directory(journal_parent)
                continue
            record = _read_journal_record(entry)
            if str(record.get("version", "")) in _LEGACY_JOURNAL_VERSIONS:
                _quarantine_legacy_journal(entry, journal_parent=journal_parent)
                continue
            if str(record.get("version", "")) != JOURNAL_VERSION:
                raise GreenfieldCommitJournalError(
                    "greenfield commit journal version is unsupported",
                    failure_kind="post_confirm_commit_invariant_failure",
                    recovery_path=str(entry),
                )
            transaction_hash = _require_digest(
                str(record.get("transaction_hash", "")),
                label="transaction hash",
            )
            if str(record["state"]) == "closed":
                _discard_committed_journal_artifacts(entry)
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
                shutil.rmtree(entry)
                fsync_directory(journal_parent)
                continue
            raise GreenfieldCommitJournalError(
                "greenfield commit journal state is invalid",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(entry),
            )

    def recover_or_return_committed(self) -> dict[str, Any] | None:
        """Recover one interrupted apply, or return a verified same-hash receipt."""

        if not self.root.exists() and not self.root.is_symlink():
            return None
        if _is_empty_prewrite_orphan(self.root):
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
        if self.root.exists() or self.root.is_symlink():
            raise GreenfieldCommitJournalError(
                "greenfield commit journal already exists before prepare",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        self.root.parent.mkdir(parents=True, exist_ok=True)
        fsync_directory(self.root.parent)
        temporary_root = Path(tempfile.mkdtemp(prefix=".prepare-", dir=self.root.parent))
        try:
            _write_journal_record(temporary_root, self._record_payload(state="preparing"))
            temporary_root.replace(self.root)
            fsync_directory(self.root.parent)
        except BaseException:
            shutil.rmtree(temporary_root, ignore_errors=True)
            raise

    def mark_prepared(self) -> None:
        self._require_state("preparing")
        if not self.snapshot_root.is_dir():
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
        if not self.root.exists() or self._read_record().get("state") == "aborted":
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

        if not self.root.exists() and not self.root.is_symlink():
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
        if not self.snapshot_root.is_dir():
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
                before_files, before_directories = _snapshot_tree(self.snapshot_root, owner, required=True)
                current_files, current_directories = _snapshot_tree(self.repo_root, owner, required=False)
                if not _safe_interrupted_tree(
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
        if self.staging_root.exists() or self.staging_root.is_symlink():
            raise GreenfieldCommitJournalError(
                "greenfield commit journal staging directory already exists",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )
        self.staging_root.mkdir(parents=True, exist_ok=False)
        fsync_directory(self.root)

    def _discard_snapshot(self) -> None:
        try:
            if self.snapshot_root.exists() or self.snapshot_root.is_symlink():
                shutil.rmtree(self.snapshot_root)
                fsync_directory(self.root)
        except OSError:
            pass

    def _discard_staging(self) -> None:
        try:
            if self.staging_root.exists() or self.staging_root.is_symlink():
                shutil.rmtree(self.staging_root)
                fsync_directory(self.root)
        except OSError:
            pass

    def _discard_journal(self) -> None:
        shutil.rmtree(self.root)
        fsync_directory(self.root.parent)

    def _require_state(self, expected: str) -> None:
        actual = str(self._read_record().get("state") or "")
        if actual != expected:
            raise GreenfieldCommitJournalError(
                f"greenfield commit journal expected {expected} state but found {actual or 'missing'}",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=self.recovery_path,
            )

    def _read_record(self) -> dict[str, Any]:
        record = _read_journal_record(self.root)
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
            self.root,
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
        record["record_hash"] = _record_hash(record)
        return record


def _record_hash(record: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_journal_record(root: Path, record: Mapping[str, Any]) -> None:
    destination = Path(root)
    try:
        atomic_write_text(
            destination / "state.v1.json",
            json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        )
        fsync_directory(destination)
    except OSError as exc:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal could not persist its transaction state",
            failure_kind="post_confirm_commit_environment_or_io_failure",
            recovery_path=str(destination),
        ) from exc


def _is_empty_prewrite_orphan(root: Path) -> bool:
    candidate = Path(root)
    if candidate.is_symlink() or not candidate.is_dir() or (candidate / "state.v1.json").exists():
        return False
    try:
        return not any(candidate.iterdir())
    except OSError:
        return False


def _read_journal_record(root: Path) -> dict[str, Any]:
    state_path = Path(root) / "state.v1.json"
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state cannot be read",
            failure_kind="post_confirm_commit_environment_or_io_failure",
            recovery_path=str(root),
        ) from exc
    if not isinstance(payload, Mapping):
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state is malformed",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(root),
        )
    record = dict(payload)
    digest = str(record.pop("record_hash", "")).strip()
    if digest != _record_hash(record):
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state hash mismatch",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(root),
        )
    if str(record.get("version", "")) in _LEGACY_JOURNAL_VERSIONS:
        return record
    if str(record.get("state", "")) not in _STATES:
        raise GreenfieldCommitJournalError(
            "greenfield commit journal state is invalid",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(root),
        )
    lifecycle_version = str(record.get("lifecycle_version") or "")
    if lifecycle_version:
        if lifecycle_version != greenfield_create_lifecycle.CREATE_LIFECYCLE_VERSION:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal lifecycle version is unsupported",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(root),
            )
        try:
            history = greenfield_create_lifecycle.require_create_lifecycle_history(record.get("lifecycle_history"))
        except ValueError as exc:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal lifecycle history is invalid",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(root),
            ) from exc
        if str(record.get("lifecycle_state") or "") != history[-1]:
            raise GreenfieldCommitJournalError(
                "greenfield commit journal lifecycle state does not match its history",
                failure_kind="post_confirm_commit_invariant_failure",
                recovery_path=str(root),
            )
    return record


def _quarantine_legacy_journal(entry: Path, *, journal_parent: Path) -> None:
    manual_root = journal_parent / "manual-recovery"
    if manual_root.exists() and (manual_root.is_symlink() or not manual_root.is_dir()):
        raise GreenfieldCommitJournalError(
            "greenfield commit journal manual-recovery directory is not safe",
            failure_kind="post_confirm_commit_environment_or_io_failure",
            recovery_path=str(manual_root),
        )
    manual_root.mkdir(parents=True, exist_ok=True)
    destination = manual_root / entry.name
    if destination.exists() or destination.is_symlink():
        raise GreenfieldCommitJournalError(
            "greenfield commit journal legacy recovery entry already exists",
            failure_kind="post_confirm_commit_invariant_failure",
            recovery_path=str(destination),
        )
    entry.replace(destination)
    fsync_directory(manual_root)
    fsync_directory(journal_parent)


def _discard_committed_journal_artifacts(root: Path) -> None:
    journal_root = Path(root)
    for name in ("snapshot", "staging"):
        target = journal_root / name
        if not target.exists() and not target.is_symlink():
            continue
        if target.is_symlink() or not target.is_dir():
            raise GreenfieldCommitJournalError(
                "greenfield committed journal artifact is not a safe directory",
                failure_kind="post_confirm_commit_environment_or_io_failure",
                recovery_path=str(target),
            )
        shutil.rmtree(target)
        fsync_directory(journal_root)


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


def _snapshot_tree(
    root: Path,
    owner: str,
    *,
    required: bool,
) -> tuple[dict[str, tuple[bytes, int]], set[str]]:
    target_root = Path(root)
    marker = target_root / ".missing" / hashlib.sha256(owner.encode("utf-8")).hexdigest()
    target = target_root / owner
    if marker.exists():
        if not required or target.exists() or target.is_symlink():
            raise ValueError("greenfield commit snapshot has an invalid missing-path marker")
        return {}, set()
    if target.is_symlink():
        raise ValueError("greenfield commit recovery refuses a symlinked snapshot path")
    if not target.exists():
        if required:
            raise ValueError("greenfield commit recovery snapshot is missing a protected path")
        return {}, set()
    if target.is_file():
        return {owner: _file_state(target)}, set()
    if not target.is_dir():
        raise ValueError("greenfield commit recovery found an unsupported protected path")
    files: dict[str, tuple[bytes, int]] = {}
    directories = {owner}
    for candidate in sorted(target.rglob("*")):
        if candidate.is_symlink():
            raise ValueError("greenfield commit recovery refuses a symlinked protected path")
        token = candidate.relative_to(target_root).as_posix()
        if candidate.is_file():
            files[token] = _file_state(candidate)
        elif candidate.is_dir():
            directories.add(token)
        else:
            raise ValueError("greenfield commit recovery found an unsupported protected path")
    return files, directories


def _file_state(path: Path) -> tuple[bytes, int]:
    return path.read_bytes(), stat.S_IMODE(path.stat().st_mode)


def _safe_interrupted_tree(
    *,
    owner: str,
    before_files: Mapping[str, tuple[bytes, int]],
    before_directories: set[str],
    current_files: Mapping[str, tuple[bytes, int]],
    current_directories: set[str],
    writes: Mapping[str, tuple[bytes, int]],
    deletes: set[str],
    created_directories: set[str],
    deleted_directories: set[str],
) -> bool:
    owned = lambda token: token == owner or token.startswith(owner + "/")
    expected_writes = {path: state for path, state in writes.items() if owned(path)}
    expected_deletes = {path for path in deletes if owned(path)}
    expected_created_directories = {path for path in created_directories if owned(path)}
    expected_deleted_directories = {path for path in deleted_directories if owned(path)}
    allowed_files = set(before_files) | set(expected_writes)
    if set(current_files) - allowed_files:
        return False
    for path in allowed_files:
        before = before_files.get(path)
        current = current_files.get(path)
        after = expected_writes.get(path)
        if path in expected_deletes:
            if current not in {before, None}:
                return False
        elif current not in {before, after}:
            return False
    allowed_directories = before_directories | expected_created_directories
    if not current_directories <= allowed_directories:
        return False
    for path in before_directories - expected_deleted_directories:
        if path not in current_directories:
            return False
    return True


__all__ = ["GreenfieldCommitJournal", "GreenfieldCommitJournalError", "JOURNAL_VERSION"]
