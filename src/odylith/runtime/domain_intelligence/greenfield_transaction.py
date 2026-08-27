"""Rollback guard for greenfield source-truth writes."""

from __future__ import annotations

import hashlib
import json
import os
import signal
from collections.abc import Callable, Sequence
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary


class GreenfieldApplyTransaction:
    """Restore greenfield-owned source truth when apply fails mid-write."""

    _SNAPSHOT_PATHS = (
        "odylith/radar",
        "odylith/technical-plans",
        "odylith/registry",
        "odylith/atlas",
        "odylith/compass",
        "odylith/surfaces/brand",
        "odylith/runtime/source",
        "odylith/runtime/delivery_intelligence.v4.json",
        "odylith/index.html",
        "odylith/tooling-payload.v1.js",
        "odylith/tooling-app.v1.js",
    )
    _SNAPSHOT_MANIFEST = ".snapshot-manifest.v1.json"

    def __init__(
        self,
        repo_root: Path,
        *,
        paths: Sequence[str] | None = None,
        snapshot_root: Path | None = None,
        retain_snapshot: bool = False,
    ) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self._snapshot_paths = _validated_snapshot_paths(paths or self._SNAPSHOT_PATHS)
        self._snapshot_root = Path(snapshot_root).expanduser().resolve() if snapshot_root is not None else None
        self._retain_snapshot = retain_snapshot
        self._committed = False
        self._rolled_back = False
        self._rollback_error = ""
        self._signal_handlers: dict[int, object] = {}

    @property
    def rollback_status(self) -> str:
        if self._committed:
            return "committed"
        if self._rolled_back:
            return "rolled_back"
        if self._rollback_error:
            return "rollback_failed"
        return "not_started"

    @property
    def rollback_error(self) -> str:
        return self._rollback_error

    @property
    def recovery_path(self) -> str:
        return str(self._snapshot_root) if self._rollback_error and self._snapshot_root is not None else ""

    @property
    def snapshot_root(self) -> Path | None:
        return self._snapshot_root

    def __enter__(self) -> "GreenfieldApplyTransaction":
        if self._snapshot_root is None:
            parent = ".odylith/runtime/greenfield/rollback"
            token = greenfield_transaction_path_boundary.make_temporary_directory(
                self.repo_root,
                parent,
                prefix=".prepare-",
            )
            self._snapshot_root = self.repo_root / token
        else:
            token = greenfield_transaction_path_boundary.relative_token(
                self.repo_root,
                self._snapshot_root,
            )
            if greenfield_transaction_path_boundary.path_kind(self.repo_root, token) != "missing":
                raise ValueError(f"greenfield rollback snapshot already exists: {self._snapshot_root}")
            greenfield_transaction_path_boundary.ensure_directory(self.repo_root, token)
        snapshot_token = self._snapshot_token()
        for token in self._snapshot_paths:
            source = self.repo_root / token
            target = self.repo_root / snapshot_token / token
            marker = snapshot_missing_marker_token(snapshot_token, token)
            if greenfield_transaction_path_boundary.path_kind(self.repo_root, token) != "missing":
                _copy_path(source, target)
            else:
                greenfield_transaction_path_boundary.atomic_write_bytes(
                    self.repo_root,
                    marker,
                    b"missing\n",
                )
        greenfield_transaction_path_boundary.atomic_write_bytes(
            self.repo_root,
            f"{snapshot_token}/{self._SNAPSHOT_MANIFEST}",
            (
                json.dumps(
                    _snapshot_manifest(self.repo_root, snapshot_token, self._snapshot_paths),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
        self._install_signal_guard()
        return self

    def commit(self) -> None:
        self._restore_signal_handlers()
        self._committed = True

    def publish(self, callback: Callable[[], object], *, published_probe: Callable[[], bool]) -> None:
        """Cross the publication boundary without rolling back an observed pointer."""

        try:
            callback()
            self.commit()
        except BaseException:
            if published_probe():
                self.commit()
            raise

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        self._restore_signal_handlers()
        try:
            if exc_type is not None and not self._committed:
                try:
                    self._restore()
                except BaseException as rollback_exc:
                    self._rollback_error = f"{type(rollback_exc).__name__}: {rollback_exc}"
                    raise
                self._rolled_back = True
        finally:
            if self._snapshot_root is not None and not self._rollback_error and not self._retain_snapshot:
                greenfield_transaction_path_boundary.remove_path(
                    self.repo_root,
                    self._snapshot_token(),
                    missing_ok=True,
                )
        return False

    def _install_signal_guard(self) -> None:
        for signum in (signal.SIGTERM, signal.SIGINT):
            try:
                previous = signal.getsignal(signum)
                signal.signal(signum, _raise_greenfield_commit_interrupted)
            except (ValueError, OSError):
                continue
            self._signal_handlers[int(signum)] = previous

    def _restore_signal_handlers(self) -> None:
        for signum, previous in self._signal_handlers.items():
            try:
                signal.signal(signum, previous)
            except (ValueError, OSError):
                pass
        self._signal_handlers.clear()

    def _restore(self) -> None:
        if self._snapshot_root is None:
            return
        snapshot_token = self._snapshot_token()
        manifest = _validated_snapshot_manifest(
            self.repo_root,
            snapshot_token,
            self._snapshot_paths,
        )
        for token in sorted(self._snapshot_paths, key=lambda item: len(Path(item).parts), reverse=True):
            target = self.repo_root / token
            snapshot = self._snapshot_root / token
            entry = manifest[token]
            if greenfield_transaction_path_boundary.path_kind(self.repo_root, token) != "missing":
                greenfield_transaction_path_boundary.remove_path(self.repo_root, token)
            if entry["state"] == "present":
                _copy_path(snapshot, target)
                actual = _path_fingerprint(self.repo_root, token)
                if actual != entry["sha256"]:
                    raise RuntimeError(f"greenfield rollback readback mismatch: {token}")
            elif greenfield_transaction_path_boundary.path_kind(self.repo_root, token) != "missing":
                raise RuntimeError(f"greenfield rollback expected an absent path: {token}")

    def _snapshot_token(self) -> str:
        if self._snapshot_root is None:
            raise RuntimeError("greenfield rollback snapshot is not initialized")
        return greenfield_transaction_path_boundary.relative_token(
            self.repo_root,
            self._snapshot_root,
        )

    @classmethod
    def restore_snapshot(
        cls,
        repo_root: Path,
        *,
        paths: Sequence[str],
        snapshot_root: Path,
    ) -> None:
        """Durably restore a snapshot retained by an interrupted commit."""

        transaction = cls(
            repo_root,
            paths=paths,
            snapshot_root=snapshot_root,
            retain_snapshot=True,
        )
        if (
            transaction._snapshot_root is None
            or greenfield_transaction_path_boundary.path_kind(
                transaction.repo_root,
                transaction._snapshot_token(),
            )
            != "directory"
        ):
            raise RuntimeError(f"greenfield rollback snapshot is missing: {snapshot_root}")
        transaction._restore()


def _validated_snapshot_paths(paths: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for raw_path in paths:
        token = str(raw_path).strip()
        path = Path(token)
        if not token or path.is_absolute() or ".." in path.parts:
            raise ValueError(f"greenfield rollback snapshot path escapes repo root: {raw_path}")
        if token not in result:
            result.append(token)
    return tuple(result)


def snapshot_missing_marker_token(snapshot_token: str, token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"{snapshot_token}/.missing/{digest}"


def _snapshot_manifest(
    repo_root: Path,
    snapshot_token: str,
    paths: Sequence[str],
) -> dict[str, object]:
    entries: dict[str, dict[str, str]] = {}
    for token in paths:
        snapshot = f"{snapshot_token}/{token}"
        marker = snapshot_missing_marker_token(snapshot_token, token)
        if greenfield_transaction_path_boundary.path_kind(repo_root, snapshot) != "missing":
            entries[token] = {
                "state": "present",
                "sha256": _path_fingerprint(repo_root, snapshot),
            }
        elif (
            greenfield_transaction_path_boundary.path_kind(repo_root, marker) == "file"
            and greenfield_transaction_path_boundary.read_bytes(repo_root, marker) == b"missing\n"
        ):
            entries[token] = {"state": "missing", "sha256": ""}
        else:
            raise RuntimeError(f"greenfield rollback snapshot inventory is incomplete: {token}")
    return {"schema_version": 1, "entries": entries}


def _validated_snapshot_manifest(
    repo_root: Path,
    snapshot_token: str,
    paths: Sequence[str],
) -> dict[str, dict[str, str]]:
    manifest_path = f"{snapshot_token}/{GreenfieldApplyTransaction._SNAPSHOT_MANIFEST}"
    if greenfield_transaction_path_boundary.path_kind(repo_root, manifest_path) != "file":
        raise RuntimeError("greenfield rollback snapshot manifest is missing or unsafe")
    try:
        payload = json.loads(
            greenfield_transaction_path_boundary.read_bytes(repo_root, manifest_path).decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("greenfield rollback snapshot manifest is unreadable") from exc
    raw_entries = payload.get("entries") if isinstance(payload, dict) and payload.get("schema_version") == 1 else None
    if not isinstance(raw_entries, dict) or set(raw_entries) != set(paths):
        raise RuntimeError("greenfield rollback snapshot manifest does not match the guarded write set")
    entries: dict[str, dict[str, str]] = {}
    for token in paths:
        raw_entry = raw_entries.get(token)
        state = str(raw_entry.get("state") or "") if isinstance(raw_entry, dict) else ""
        expected_hash = str(raw_entry.get("sha256") or "") if isinstance(raw_entry, dict) else ""
        snapshot = f"{snapshot_token}/{token}"
        marker = snapshot_missing_marker_token(snapshot_token, token)
        snapshot_present = greenfield_transaction_path_boundary.path_kind(repo_root, snapshot) != "missing"
        marker_valid = (
            greenfield_transaction_path_boundary.path_kind(repo_root, marker) == "file"
            and greenfield_transaction_path_boundary.read_bytes(repo_root, marker) == b"missing\n"
        )
        if state == "present":
            if not snapshot_present or marker_valid or not expected_hash:
                raise RuntimeError(f"greenfield rollback snapshot inventory is invalid: {token}")
            if _path_fingerprint(repo_root, snapshot) != expected_hash:
                raise RuntimeError(f"greenfield rollback snapshot integrity check failed: {token}")
        elif state == "missing":
            if snapshot_present or not marker_valid or expected_hash:
                raise RuntimeError(f"greenfield rollback missing-path marker is invalid: {token}")
        else:
            raise RuntimeError(f"greenfield rollback snapshot state is invalid: {token}")
        entries[token] = {"state": state, "sha256": expected_hash}
    return entries


def _path_fingerprint(repo_root: Path, path: Path | str) -> str:
    digest = hashlib.sha256()
    token = greenfield_transaction_path_boundary.relative_token(repo_root, path)
    entries = greenfield_transaction_path_boundary.scan_tree(
        repo_root,
        token,
        require_present=True,
    )
    for entry in entries:
        relative = Path(entry.path).relative_to(token).as_posix()
        if relative == ".":
            relative = ""
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if entry.kind == "file":
            digest.update(b"file\0")
            digest.update(entry.data)
        else:
            digest.update(b"directory\0")
    return digest.hexdigest()


class GreenfieldCommitInterrupted(RuntimeError):
    """Raised when a graceful termination signal interrupts a guarded commit."""


def _raise_greenfield_commit_interrupted(signum: int, _frame: object) -> None:
    raise GreenfieldCommitInterrupted(f"greenfield commit interrupted by signal {signum}")


def _copy_path(source: Path, target: Path) -> None:
    common = Path(os.path.commonpath((str(source), str(target)))).resolve(strict=False)
    greenfield_transaction_path_boundary.copy_tree(common, source, target)


__all__ = [
    "GreenfieldApplyTransaction",
    "GreenfieldCommitInterrupted",
    "snapshot_missing_marker_token",
]
