"""Rollback guard for greenfield source-truth writes."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


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

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self._snapshot_root: Path | None = None
        self._committed = False

    def __enter__(self) -> "GreenfieldApplyTransaction":
        self._tmp = tempfile.TemporaryDirectory(prefix="odylith-greenfield-rollback-")
        self._snapshot_root = Path(self._tmp.name)
        for token in self._SNAPSHOT_PATHS:
            source = self.repo_root / token
            target = self._snapshot_root / token
            marker = self._snapshot_root / f"{token}.missing"
            marker.parent.mkdir(parents=True, exist_ok=True)
            if source.exists() or source.is_symlink():
                _copy_path(source, target)
            else:
                marker.write_text("missing\n", encoding="utf-8")
        return self

    def commit(self) -> None:
        self._committed = True

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        try:
            if exc_type is not None and not self._committed:
                self._restore()
        finally:
            if self._tmp is not None:
                self._tmp.cleanup()
        return False

    def _restore(self) -> None:
        if self._snapshot_root is None:
            return
        for token in self._SNAPSHOT_PATHS:
            target = self.repo_root / token
            snapshot = self._snapshot_root / token
            marker = self._snapshot_root / f"{token}.missing"
            if target.exists() or target.is_symlink():
                _remove_path(target)
            if snapshot.exists() or snapshot.is_symlink():
                _copy_path(snapshot, target)
            elif not marker.exists():
                target.mkdir(parents=True, exist_ok=True)


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


__all__ = ["GreenfieldApplyTransaction"]
