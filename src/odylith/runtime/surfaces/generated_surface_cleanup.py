"""Shared cleanup helpers for retired generated dashboard artifacts.

When a host repo moves a generated surface to a new canonical path, older generated
files should disappear as part of the same render/build run. Otherwise the repo
topology stays misleading, local file browsing shows stale entrypoints, and git
status keeps reporting dead artifacts that are no longer authoritative.

These helpers are intentionally filesystem-only and deterministic. They never
touch source-of-truth markdown, Mermaid source assets, or any active output
path passed by the caller.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import shutil


def remove_legacy_generated_paths(*, active_outputs: Iterable[Path], legacy_paths: Iterable[Path]) -> None:
    """Remove stale generated files/directories that no longer define the surface.

    The caller supplies the set of active outputs for the current render/build.
    Any legacy path that resolves to one of those active outputs is skipped so a
    custom output override cannot accidentally delete itself.
    """

    active = {path.resolve() for path in active_outputs}
    for legacy in legacy_paths:
        resolved = legacy.resolve()
        if resolved in active or not resolved.exists():
            continue
        if resolved.is_dir():
            shutil.rmtree(resolved)
        else:
            resolved.unlink()


def remove_empty_directory(path: Path) -> None:
    """Best-effort removal for an empty retired directory."""

    resolved = path.resolve()
    if not resolved.is_dir():
        return
    try:
        next(resolved.iterdir())
    except StopIteration:
        resolved.rmdir()
