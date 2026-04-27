"""Snapshot path expansion policies for disposable benchmark workspaces."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Sequence

_BROWSER_SURFACE_SNAPSHOT_PREFIXES = (
    "odylith/atlas/",
    "odylith/casebook/",
    "odylith/compass/",
    "odylith/radar/",
    "odylith/registry/",
)
_BROWSER_SURFACE_SNAPSHOT_FILES = frozenset({"odylith/index.html"})
_BROWSER_SURFACE_SNAPSHOT_SUFFIXES = frozenset({".css", ".html", ".js", ".json", ".jsonl", ".md", ".svg"})


def _dedupe_snapshot_paths(paths: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for raw in paths:
        token = str(raw or "").strip().replace("\\", "/")
        if not token:
            continue
        while token.startswith("./"):
            token = token[2:]
        normalized = Path(token).as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(normalized)
    return rows


def _git_path_lines(*, repo_root: Path, diff_filter: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"--diff-filter={diff_filter}", "HEAD", "--"],
        cwd=str(Path(repo_root).resolve()),
        text=True,
        capture_output=True,
        check=False,
    )
    if int(completed.returncode or 0) != 0:
        return []
    return _dedupe_snapshot_paths(
        [str(line).strip() for line in str(completed.stdout or "").splitlines() if str(line).strip()]
    )


def _untracked_repo_paths(repo_root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(Path(repo_root).resolve()),
        text=True,
        capture_output=True,
        check=False,
    )
    if int(completed.returncode or 0) != 0:
        return []
    return _dedupe_snapshot_paths(
        [str(line).strip() for line in str(completed.stdout or "").splitlines() if str(line).strip()]
    )


def _browser_surface_validator_requested(validation_paths: Sequence[str]) -> bool:
    return any("browser" in Path(str(path or "").strip()).name for path in validation_paths)


def _browser_surface_snapshot_candidate(path: str) -> bool:
    token = str(path or "").strip()
    if not token:
        return False
    if token in _BROWSER_SURFACE_SNAPSHOT_FILES:
        return True
    if Path(token).suffix.lower() not in _BROWSER_SURFACE_SNAPSHOT_SUFFIXES:
        return False
    return any(token.startswith(prefix) for prefix in _BROWSER_SURFACE_SNAPSHOT_PREFIXES)


def expand_browser_surface_snapshot_paths(
    *,
    repo_root: Path,
    snapshot_paths: Sequence[str],
    validation_paths: Sequence[str],
) -> list[str]:
    """Carry dirty browser fixture inputs into disposable worktrees without adding prompt credit."""
    base_paths = _dedupe_snapshot_paths(snapshot_paths)
    if not _browser_surface_validator_requested(validation_paths):
        return base_paths
    return _dedupe_snapshot_paths(
        [
            *base_paths,
            *[
                path
                for path in [
                    *_git_path_lines(repo_root=repo_root, diff_filter="ACMRTUXB"),
                    *_git_path_lines(repo_root=repo_root, diff_filter="D"),
                    *_untracked_repo_paths(repo_root),
                ]
                if _browser_surface_snapshot_candidate(path)
            ],
        ]
    )


def expand_deleted_repo_snapshot_paths(*, repo_root: Path, snapshot_paths: Sequence[str]) -> list[str]:
    """Preserve tracked deletions so disposable workspaces measure the current tree."""
    return _dedupe_snapshot_paths(
        [
            *_dedupe_snapshot_paths(snapshot_paths),
            *_git_path_lines(repo_root=repo_root, diff_filter="D"),
        ]
    )
