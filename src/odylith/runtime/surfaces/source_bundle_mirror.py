"""Sync live checked-in surfaces into the source-owned bundle mirror.

The Odylith product repo tracks two copies of governed dashboard assets:
- live checked-in surfaces under ``odylith/...``
- source-owned install mirrors under ``src/odylith/bundle/assets/odylith/...``

When renderers only refresh the live copy, browser and install-time contract
tests can keep serving stale mirrored assets and reopen already-fixed UX bugs.
This module keeps the mirror update logic centralized so surface renderers can
write both destinations from one source of truth without local copy loops.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _live_surface_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / "odylith").resolve()


def source_bundle_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / "src" / "odylith" / "bundle" / "assets" / "odylith").resolve()


def _bundle_mirror_enabled(*, repo_root: Path) -> bool:
    return source_bundle_root(repo_root=repo_root).is_dir()


def _live_relative_path(*, repo_root: Path, live_path: Path) -> Path:
    live_root = _live_surface_root(repo_root=repo_root)
    resolved_live = Path(live_path).resolve()
    try:
        return resolved_live.relative_to(live_root)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"{resolved_live} is not under the live odylith surface root {live_root}") from exc


def bundle_mirror_path(*, repo_root: Path, live_path: Path) -> Path:
    return (source_bundle_root(repo_root=repo_root) / _live_relative_path(repo_root=repo_root, live_path=live_path)).resolve()


def bundle_mirror_dir(*, repo_root: Path, live_dir: Path) -> Path:
    return (source_bundle_root(repo_root=repo_root) / _live_relative_path(repo_root=repo_root, live_path=live_dir)).resolve()


def _write_bytes_if_changed(target: Path, content: bytes) -> None:
    if target.is_file() and target.read_bytes() == content:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def sync_live_paths(*, repo_root: Path, live_paths: Iterable[Path]) -> tuple[Path, ...]:
    root = Path(repo_root).resolve()
    if not _bundle_mirror_enabled(repo_root=root):
        return ()
    mirrored: list[Path] = []
    for live_path in live_paths:
        resolved_live = Path(live_path).resolve()
        if not resolved_live.is_file():
            continue
        mirror_path = bundle_mirror_path(repo_root=root, live_path=resolved_live)
        _write_bytes_if_changed(mirror_path, resolved_live.read_bytes())
        mirrored.append(mirror_path)
    return tuple(mirrored)


def sync_live_glob(*, repo_root: Path, live_dir: Path, pattern: str) -> tuple[Path, ...]:
    root = Path(repo_root).resolve()
    if not _bundle_mirror_enabled(repo_root=root):
        return ()
    live_parent = Path(live_dir).resolve()
    mirror_dir = bundle_mirror_dir(repo_root=root, live_dir=live_parent)
    live_matches = sorted(path for path in live_parent.glob(pattern) if path.is_file())
    mirrored = sync_live_paths(repo_root=root, live_paths=live_matches)
    live_names = {path.name for path in live_matches}
    if mirror_dir.is_dir():
        for stale_path in mirror_dir.glob(pattern):
            if stale_path.name in live_names:
                continue
            if stale_path.is_file():
                stale_path.unlink()
    return mirrored
