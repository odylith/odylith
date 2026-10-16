"""Backlog file commit helpers for confirmed greenfield writes."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings


def write_backlog_files(backlog_result: Mapping[str, Any], *, repo_root: Path | None = None) -> None:
    """Materialize already-rendered Radar backlog files into the target repo."""

    root = Path(repo_root).expanduser().resolve() if repo_root is not None else None
    for raw_path, text in _mapping(backlog_result.get("existing_idea_files")).items():
        _write_text_path(raw_path, text, repo_root=root)
    for raw_path, text in _mapping(backlog_result.get("idea_files")).items():
        _write_text_path(raw_path, text, repo_root=root)
    backlog_index_path = _resolve_path(backlog_result["backlog_index"], repo_root=root)
    backlog_index_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_index_path.write_text(str(backlog_result["backlog_index_text"]), encoding="utf-8")


def compiled_backlog_traceability_paths(*, repo_root: Path, backlog_result: Mapping[str, Any]) -> list[str]:
    """Return committed backlog paths from a precompiled package without mutating them."""

    paths: list[str] = []
    for row in _rows(backlog_result.get("created")):
        paths.append(str(row.get("idea_path", "")).strip())
    for key in ("idea_files", "existing_idea_files"):
        paths.extend(str(path).strip() for path in _mapping(backlog_result.get(key)).keys())
    return dedupe_strings(_repo_relative(repo_root=repo_root, path=path) for path in paths if path)


def _write_text_path(raw_path: object, text: object, *, repo_root: Path | None = None) -> None:
    path = _resolve_path(raw_path, repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text), encoding="utf-8")


def _resolve_path(raw_path: object, *, repo_root: Path | None = None) -> Path:
    path = Path(str(raw_path))
    if repo_root is None:
        return path
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"compiled backlog path escapes repo root: {resolved}") from exc
    return resolved


def _mapping(value: object) -> Mapping[Any, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(value: object) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list | tuple) else []


def _repo_relative(*, repo_root: Path, path: str) -> str:
    root = Path(repo_root).expanduser().resolve()
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        return str(candidate.resolve().relative_to(root))
    except ValueError:
        return str(candidate)
