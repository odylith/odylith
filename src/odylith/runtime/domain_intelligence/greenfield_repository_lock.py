"""Cross-process lock for Greenfield publication and pending decisions."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
from typing import Iterator


class GreenfieldRepositoryBusyError(RuntimeError):
    """Another process owns the Greenfield repository mutation boundary."""


class GreenfieldRepositoryLockError(RuntimeError):
    """The Greenfield repository mutation lock could not be opened or used."""


@contextmanager
def greenfield_repository_lock(repo_root: Path) -> Iterator[int]:
    """Serialize cooperating Greenfield publish, confirm, and reject operations."""

    with _repository_lock(repo_root, mode=fcntl.LOCK_EX) as descriptor:
        yield descriptor


@contextmanager
def greenfield_repository_read_lock(repo_root: Path) -> Iterator[None]:
    """Prevent a canonical reader from crossing a cooperating writer switch."""

    with _repository_lock(repo_root, mode=fcntl.LOCK_SH):
        yield


@contextmanager
def _repository_lock(repo_root: Path, *, mode: int) -> Iterator[int]:
    lock_path = Path(repo_root).expanduser().resolve() / ".odylith/runtime/greenfield/create.lock"
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
    except OSError as exc:
        raise GreenfieldRepositoryLockError("Greenfield repository lock is unavailable") from exc
    with handle:
        try:
            fcntl.flock(handle.fileno(), mode | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GreenfieldRepositoryBusyError("BUSY_NO_WRITE: Greenfield repository mutation is already in progress") from exc
        except OSError as exc:
            raise GreenfieldRepositoryLockError("Greenfield repository lock could not be acquired") from exc
        # An explicitly inherited descriptor retains protection after owner death.
        # LOCK_UN would instead release every process sharing this description.
        yield handle.fileno()


@contextmanager
def inherited_greenfield_repository_lock(repo_root: Path, descriptor: int) -> Iterator[int]:
    """Consume a trusted parent's descriptor for one render-only child operation.

    This checks the repository lock object, not the identity of a same-UID caller.
    Only the parent admits working state and later publishes the completed result.
    """
    path = Path(repo_root).expanduser().resolve() / ".odylith/runtime/greenfield/create.lock"
    try:
        expected = path.lstat()
        actual = os.fstat(descriptor)
        writable = fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE in {os.O_WRONLY, os.O_RDWR}
        if not stat.S_ISREG(expected.st_mode) or not stat.S_ISREG(actual.st_mode) or not writable:
            raise GreenfieldRepositoryLockError("Inherited repository lock must be a writable regular file")
        if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
            raise GreenfieldRepositoryLockError("Inherited repository lock belongs to another repository")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise GreenfieldRepositoryBusyError("Inherited descriptor does not own the repository writer lock") from exc
    except OSError as exc:
        raise GreenfieldRepositoryLockError("Inherited repository lock is unavailable") from exc
    try:
        yield descriptor
    finally:
        os.close(descriptor)


__all__ = [
    "GreenfieldRepositoryBusyError",
    "GreenfieldRepositoryLockError",
    "greenfield_repository_read_lock",
    "greenfield_repository_lock",
    "inherited_greenfield_repository_lock",
]
