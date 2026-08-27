"""Cross-process lock for Greenfield publication and pending decisions."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
from typing import Iterator

from odylith.runtime.domain_intelligence import greenfield_transaction_path_boundary


class GreenfieldRepositoryBusyError(RuntimeError):
    """Another process owns the Greenfield repository mutation boundary."""


class GreenfieldRepositoryLockError(RuntimeError):
    """The Greenfield repository mutation lock could not be opened or used."""


@contextmanager
def greenfield_repository_lock(repo_root: Path) -> Iterator[None]:
    """Serialize cooperating Greenfield publish, confirm, and reject operations."""

    with _repository_lock(repo_root, mode=fcntl.LOCK_EX):
        yield


@contextmanager
def greenfield_repository_read_lock(repo_root: Path) -> Iterator[None]:
    """Prevent a canonical reader from crossing a cooperating writer switch."""

    with _repository_lock(repo_root, mode=fcntl.LOCK_SH):
        yield


@contextmanager
def _repository_lock(repo_root: Path, *, mode: int) -> Iterator[None]:
    try:
        descriptor = greenfield_transaction_path_boundary.open_lock_file(
            repo_root,
            ".odylith/runtime/greenfield/create.lock",
        )
        handle = os.fdopen(descriptor, "a+b")
    except (OSError, greenfield_transaction_path_boundary.GreenfieldTransactionPathError) as exc:
        raise GreenfieldRepositoryLockError("Greenfield repository lock is unavailable") from exc
    with handle:
        try:
            fcntl.flock(handle.fileno(), mode | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GreenfieldRepositoryBusyError("Greenfield repository mutation is already in progress") from exc
        except OSError as exc:
            raise GreenfieldRepositoryLockError("Greenfield repository lock could not be acquired") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = [
    "GreenfieldRepositoryBusyError",
    "GreenfieldRepositoryLockError",
    "greenfield_repository_read_lock",
    "greenfield_repository_lock",
]
