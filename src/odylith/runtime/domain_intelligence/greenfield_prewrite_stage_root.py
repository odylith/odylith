"""Temporary governed-source staging roots for greenfield prewrite compilation."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile

from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence.greenfield_repository_write_set import (
    GREENFIELD_REPOSITORY_WRITE_PATHS,
)


_PREWRITE_STAGE_PATHS = tuple(Path(token) for token in GREENFIELD_REPOSITORY_WRITE_PATHS)


def ensure_greenfield_create_baseline(root: Path) -> None:
    """Create missing governance indexes needed by the confirmed-create refresh path."""

    greenfield_create_baseline.ensure_greenfield_create_baseline(root)


@contextmanager
def staged_greenfield_prewrite_root(root: Path) -> Iterator[Path]:
    """Stage governed inputs so completion gates can run without target writes."""

    source_root = Path(root).expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="odylith-greenfield-prewrite-") as tmp:
        stage_root = (Path(tmp) / "repo").resolve()
        stage_root.mkdir(parents=True, exist_ok=True)
        for token in _PREWRITE_STAGE_PATHS:
            _copy_existing_path(source_root / token, stage_root / token)
        ensure_greenfield_create_baseline(stage_root)
        yield stage_root


def _copy_existing_path(source: Path, target: Path) -> None:
    if not source.exists() and not source.is_symlink():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(source.readlink())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


__all__ = ["ensure_greenfield_create_baseline", "staged_greenfield_prewrite_root"]
