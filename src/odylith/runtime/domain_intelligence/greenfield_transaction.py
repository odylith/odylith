"""Rollback guard for greenfield source-truth writes."""

from __future__ import annotations

import hashlib
import json
import signal
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from odylith.install.fs import atomic_write_text
from odylith.install.fs import fsync_directory
from odylith.install.fs import fsync_file


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
            self._snapshot_root = Path(tempfile.mkdtemp(prefix="odylith-greenfield-rollback-"))
        elif self._snapshot_root.exists() or self._snapshot_root.is_symlink():
            raise ValueError(f"greenfield rollback snapshot already exists: {self._snapshot_root}")
        else:
            self._snapshot_root.mkdir(parents=True, exist_ok=False)
            fsync_directory(self._snapshot_root.parent)
        for token in self._snapshot_paths:
            source = self.repo_root / token
            target = self._snapshot_root / token
            marker = _missing_marker(self._snapshot_root, token)
            marker.parent.mkdir(parents=True, exist_ok=True)
            if source.exists() or source.is_symlink():
                _copy_path(source, target)
                _sync_path(target)
            else:
                atomic_write_text(marker, "missing\n")
        atomic_write_text(
            self._snapshot_root / self._SNAPSHOT_MANIFEST,
            json.dumps(
                _snapshot_manifest(self._snapshot_root, self._snapshot_paths),
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        fsync_directory(self._snapshot_root)
        self._install_signal_guard()
        return self

    def commit(self) -> None:
        self._restore_signal_handlers()
        self._committed = True

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
                shutil.rmtree(self._snapshot_root, ignore_errors=True)
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
        manifest = _validated_snapshot_manifest(self._snapshot_root, self._snapshot_paths)
        for token in sorted(self._snapshot_paths, key=lambda item: len(Path(item).parts), reverse=True):
            target = self.repo_root / token
            snapshot = self._snapshot_root / token
            entry = manifest[token]
            if target.exists() or target.is_symlink():
                _remove_path(target)
                fsync_directory(target.parent)
            if entry["state"] == "present":
                _copy_path(snapshot, target)
                _sync_path(target)
                fsync_directory(target.parent)
                actual = _path_fingerprint(target)
                if actual != entry["sha256"]:
                    raise RuntimeError(f"greenfield rollback readback mismatch: {token}")
            elif target.exists() or target.is_symlink():
                raise RuntimeError(f"greenfield rollback expected an absent path: {token}")

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
        if transaction._snapshot_root is None or not transaction._snapshot_root.is_dir():
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


def _missing_marker(snapshot_root: Path, token: str) -> Path:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return snapshot_root / ".missing" / digest


def _snapshot_manifest(snapshot_root: Path, paths: Sequence[str]) -> dict[str, object]:
    entries: dict[str, dict[str, str]] = {}
    for token in paths:
        snapshot = snapshot_root / token
        marker = _missing_marker(snapshot_root, token)
        if snapshot.exists() or snapshot.is_symlink():
            entries[token] = {"state": "present", "sha256": _path_fingerprint(snapshot)}
        elif marker.is_file() and not marker.is_symlink() and marker.read_text(encoding="utf-8") == "missing\n":
            entries[token] = {"state": "missing", "sha256": ""}
        else:
            raise RuntimeError(f"greenfield rollback snapshot inventory is incomplete: {token}")
    return {"schema_version": 1, "entries": entries}


def _validated_snapshot_manifest(snapshot_root: Path, paths: Sequence[str]) -> dict[str, dict[str, str]]:
    manifest_path = snapshot_root / GreenfieldApplyTransaction._SNAPSHOT_MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("greenfield rollback snapshot manifest is missing or unsafe")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        snapshot = snapshot_root / token
        marker = _missing_marker(snapshot_root, token)
        snapshot_present = snapshot.exists() or snapshot.is_symlink()
        marker_valid = marker.is_file() and not marker.is_symlink() and marker.read_text(encoding="utf-8") == "missing\n"
        if state == "present":
            if not snapshot_present or marker.exists() or not expected_hash:
                raise RuntimeError(f"greenfield rollback snapshot inventory is invalid: {token}")
            if _path_fingerprint(snapshot) != expected_hash:
                raise RuntimeError(f"greenfield rollback snapshot integrity check failed: {token}")
        elif state == "missing":
            if snapshot_present or not marker_valid or expected_hash:
                raise RuntimeError(f"greenfield rollback missing-path marker is invalid: {token}")
        else:
            raise RuntimeError(f"greenfield rollback snapshot state is invalid: {token}")
        entries[token] = {"state": state, "sha256": expected_hash}
    return entries


def _path_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()

    def update(candidate: Path, relative: str) -> None:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if candidate.is_symlink():
            digest.update(b"symlink\0")
            digest.update(str(candidate.readlink()).encode("utf-8"))
            return
        if candidate.is_file():
            digest.update(b"file\0")
            with candidate.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return
        if candidate.is_dir():
            digest.update(b"directory\0")
            for child in sorted(candidate.iterdir(), key=lambda item: item.name):
                child_relative = f"{relative}/{child.name}" if relative else child.name
                update(child, child_relative)
            return
        raise RuntimeError(f"greenfield rollback snapshot path is unreadable: {candidate}")

    update(path, "")
    return digest.hexdigest()


class GreenfieldCommitInterrupted(RuntimeError):
    """Raised when a graceful termination signal interrupts a guarded commit."""


def _raise_greenfield_commit_interrupted(signum: int, _frame: object) -> None:
    raise GreenfieldCommitInterrupted(f"greenfield commit interrupted by signal {signum}")


def _copy_path(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(source.readlink())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def _remove_path(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def _sync_path(path: Path) -> None:
    if path.is_symlink():
        fsync_directory(path.parent)
        return
    if path.is_file():
        fsync_file(path)
        fsync_directory(path.parent)
        return
    if path.is_dir():
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            _sync_path(child)
        fsync_directory(path)
        fsync_directory(path.parent)


__all__ = ["GreenfieldApplyTransaction", "GreenfieldCommitInterrupted"]
