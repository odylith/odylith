"""Shared repo-path and href helpers for dashboard surfaces.

Several surface renderers need the same small path contract: resolve repo-local
tokens, build portable relative hrefs, and optionally preserve unresolved
references in UI payloads. Keeping those rules here avoids copy-paste across
the oversized renderer files.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from odylith.runtime.common import repo_path_resolver


def resolve_repo_path(*, repo_root: Path, token: str) -> Path:
    """Resolve one repo-relative or absolute token against `repo_root`."""

    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=token)


def relative_href(*, output_path: Path, target: Path) -> str:
    """Return a browser-friendly relative href from `output_path` to `target`."""

    rel = os.path.relpath(str(target), start=str(output_path.parent))
    return Path(rel).as_posix()


def portable_relative_href(*, output_path: Path, token: str) -> str:
    """Return a relative href for an explicit target path token."""

    path = Path(str(token or "").strip())
    if not path:
        return ""
    rel = os.path.relpath(str(path.resolve() if path.is_absolute() else path), start=str(output_path.parent))
    return Path(rel).as_posix()


def path_link(
    *,
    repo_root: Path,
    output_path: Path,
    token: str,
    allow_missing: bool = False,
) -> dict[str, str]:
    """Return one surface path/href row for a referenced repo token."""

    path = str(token or "").strip()
    target = resolve_repo_path(repo_root=repo_root, token=path)
    href = ""
    if target.exists() or allow_missing:
        href = repo_path_resolver.relative_href(repo_root=repo_root, output_path=output_path, value=target)
    return {
        "path": path,
        "href": href,
    }


def path_links(
    *,
    repo_root: Path,
    output_path: Path,
    values: Sequence[str],
    allow_missing: bool = False,
) -> list[dict[str, str]]:
    """Return path/href rows for a list of referenced repo tokens."""

    return [
        path_link(
            repo_root=repo_root,
            output_path=output_path,
            token=token,
            allow_missing=allow_missing,
        )
        for token in values
        if str(token or "").strip()
    ]
