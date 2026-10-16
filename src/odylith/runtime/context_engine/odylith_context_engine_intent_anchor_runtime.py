"""Intent-anchor path validation helpers for Context Engine startup routing."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

_PLANNED_FILE_SUFFIXES = {
    ".css",
    ".go",
    ".html",
    ".j2",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

_PLANNED_FILE_ROOTS = {
    "agents-guidelines",
    "app",
    "bin",
    "configs",
    "contracts",
    "docker",
    "docs",
    "infra",
    "mk",
    "mocks",
    "monitoring",
    "odylith",
    "policies",
    "scripts",
    "services",
    "skills",
    "src",
    "tests",
}


def path_ref_exists_or_is_planned(
    *,
    repo_root: Path,
    path_ref: str,
    repo_dirty_paths: Collection[str],
) -> bool:
    token = str(path_ref or "").strip().strip("/")
    if not token or token in {".", ".."}:
        return False
    path_parts = [part for part in token.split("/") if part]
    if not path_parts or any(part == ".." for part in path_parts):
        return False
    if token in repo_dirty_paths:
        return True

    target = repo_root / token
    if target.exists():
        return True
    if path_parts[0] not in _PLANNED_FILE_ROOTS:
        return False
    if target.suffix.lower() not in _PLANNED_FILE_SUFFIXES:
        return False
    if target.parent.exists():
        return True

    ancestor = target.parent
    while ancestor != repo_root and ancestor != ancestor.parent:
        if ancestor.exists():
            try:
                ancestor.relative_to(repo_root)
            except ValueError:
                return False
            return True
        ancestor = ancestor.parent
    return False
