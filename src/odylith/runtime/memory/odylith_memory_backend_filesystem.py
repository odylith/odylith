"""Filesystem replacement helpers for Odylith's local memory backend."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterable

_STALE_REPLACEMENT_PREFIXES = (".lance.old-", ".tantivy.old-")
_STALE_BUILD_PREFIXES = ("odylith-lance-", "odylith-tantivy-")


@contextlib.contextmanager
def suppress_expected_lance_bootstrap_warnings() -> Iterable[None]:
    saved_stderr_fd: int | None = None
    devnull_handle = None
    try:
        saved_stderr_fd = os.dup(2)
        devnull_handle = open(os.devnull, "w", encoding="utf-8")
        os.dup2(devnull_handle.fileno(), 2)
        yield
    finally:
        if saved_stderr_fd is not None:
            with contextlib.suppress(OSError):
                os.dup2(saved_stderr_fd, 2)
            with contextlib.suppress(OSError):
                os.close(saved_stderr_fd)
        if devnull_handle is not None:
            with contextlib.suppress(OSError):
                devnull_handle.close()


def _reserve_replacement_path(*, target_root: Path) -> Path:
    parent = target_root.parent
    parent.mkdir(parents=True, exist_ok=True)
    candidate = Path(tempfile.mkdtemp(prefix=f".{target_root.name}.old-", dir=str(parent))).resolve()
    candidate.rmdir()
    return candidate


def remove_directory_best_effort(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(path, ignore_errors=True)


def cleanup_stale_backend_workdirs(*, backend_root: Path) -> None:
    if not backend_root.exists():
        return
    for child in backend_root.iterdir():
        if child.is_dir() and (
            child.name.startswith(_STALE_REPLACEMENT_PREFIXES)
            or child.name.startswith(_STALE_BUILD_PREFIXES)
        ):
            remove_directory_best_effort(child)


def replace_directory_tree(*, temp_root: Path, target_root: Path) -> None:
    temp = Path(temp_root).resolve()
    target = Path(target_root).resolve()
    backup: Path | None = None
    if target.exists():
        backup = _reserve_replacement_path(target_root=target)
        try:
            target.rename(backup)
        except Exception:
            remove_directory_best_effort(backup)
            raise
    try:
        temp.rename(target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            with contextlib.suppress(Exception):
                backup.rename(target)
        raise
    if backup is not None:
        remove_directory_best_effort(backup)
