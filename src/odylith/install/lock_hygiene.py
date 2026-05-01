"""Lock directory inventory and stale-placeholder cleanup for installed repos."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

LOCK_NOTE_THRESHOLD = 200
LOCK_COMPACTION_MIN_AGE_SECONDS = 60 * 60


@dataclass(frozen=True)
class LockHygieneSummary:
    locks_dir: Path
    total_files: int = 0
    zero_byte_files: int = 0
    stale_zero_byte_files: int = 0
    removed_files: int = 0
    scan_error: str = ""


def lock_hygiene_summary(
    *,
    repo_root: str | Path,
    stale_after_seconds: int = LOCK_COMPACTION_MIN_AGE_SECONDS,
) -> LockHygieneSummary:
    locks_dir = _locks_dir(repo_root=repo_root)
    now = time.time()
    return _scan_locks_dir(
        locks_dir=locks_dir,
        now=now,
        stale_after_seconds=stale_after_seconds,
        remove_stale=False,
    )


def compact_stale_zero_byte_locks(
    *,
    repo_root: str | Path,
    stale_after_seconds: int = LOCK_COMPACTION_MIN_AGE_SECONDS,
) -> LockHygieneSummary:
    locks_dir = _locks_dir(repo_root=repo_root)
    now = time.time()
    return _scan_locks_dir(
        locks_dir=locks_dir,
        now=now,
        stale_after_seconds=stale_after_seconds,
        remove_stale=True,
    )


def _locks_dir(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / ".odylith" / "locks"


def _scan_locks_dir(
    *,
    locks_dir: Path,
    now: float,
    stale_after_seconds: int,
    remove_stale: bool,
) -> LockHygieneSummary:
    if not locks_dir.is_dir():
        return LockHygieneSummary(locks_dir=locks_dir)
    total_files = 0
    zero_byte_files = 0
    stale_zero_byte_files = 0
    removed_files = 0
    try:
        paths = list(locks_dir.rglob("*"))
    except OSError as exc:
        return LockHygieneSummary(locks_dir=locks_dir, scan_error=str(exc))
    for path in paths:
        if path.is_symlink() or not path.is_file():
            continue
        total_files += 1
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size != 0:
            continue
        zero_byte_files += 1
        if _preserve_lock_path(path=path, locks_dir=locks_dir):
            continue
        if now - stat.st_mtime < max(0, int(stale_after_seconds)):
            continue
        stale_zero_byte_files += 1
        if not remove_stale:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            removed_files += 1
        except OSError:
            continue
        else:
            removed_files += 1
    return LockHygieneSummary(
        locks_dir=locks_dir,
        total_files=total_files,
        zero_byte_files=zero_byte_files,
        stale_zero_byte_files=stale_zero_byte_files,
        removed_files=removed_files,
    )


def _preserve_lock_path(*, path: Path, locks_dir: Path) -> bool:
    try:
        relative = path.relative_to(locks_dir)
    except ValueError:
        return True
    return relative == Path("install.lock")
