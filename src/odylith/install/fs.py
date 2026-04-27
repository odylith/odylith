"""Filesystem helpers shared across Odylith install and repair paths."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def fsync_directory(path: Path) -> None:
    directory = Path(path)
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    destination = Path(path)
    if destination.is_symlink():
        raise ValueError(f"refusing to write through symlink: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(destination)
        fsync_directory(destination.parent)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return destination


def display_path(*, repo_root: Path, path: Path) -> str:
    """Render a path relative to the repo root when possible."""
    candidate = Path(path)
    try:
        return candidate.relative_to(repo_root).as_posix()
    except ValueError:
        return candidate.as_posix()


def remove_path(path: Path) -> None:
    candidate = Path(path)
    if candidate.is_symlink() or candidate.is_file():
        candidate.unlink(missing_ok=True)
        return
    if candidate.exists():
        shutil.rmtree(candidate)
