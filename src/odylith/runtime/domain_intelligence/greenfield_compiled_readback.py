"""Exact readback checks for compiled greenfield transaction writes."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage


def raise_for_compiled_backlog_and_atlas_readback(
    *,
    root: Path,
    package: GreenfieldCompletionPackage,
) -> None:
    """Verify committed text files match the hash-bound completion package."""

    repo_root = Path(root).expanduser().resolve()
    backlog_result = package.backlog_result if isinstance(package.backlog_result, Mapping) else {}
    _raise_for_text_map_readback(
        repo_root=repo_root,
        values=_mapping(backlog_result.get("existing_idea_files")),
        label="compiled backlog existing idea file",
    )
    _raise_for_text_map_readback(
        repo_root=repo_root,
        values=_mapping(backlog_result.get("idea_files")),
        label="compiled backlog idea file",
    )
    _raise_for_text_readback(
        path=_resolve(repo_root=repo_root, token=backlog_result.get("backlog_index")),
        expected=str(backlog_result.get("backlog_index_text", "")),
        label="compiled backlog index",
    )
    _raise_for_text_map_readback(
        repo_root=repo_root,
        values=_mapping(package.rendered_atlas_sources),
        label="compiled Atlas source",
    )


def _raise_for_text_map_readback(
    *,
    repo_root: Path,
    values: Mapping[Any, Any],
    label: str,
) -> None:
    for raw_path, expected in values.items():
        _raise_for_text_readback(
            path=_resolve(repo_root=repo_root, token=raw_path),
            expected=str(expected),
            label=label,
        )


def _raise_for_text_readback(*, path: Path, expected: str, label: str) -> None:
    if not str(path):
        raise ValueError(f"{label} readback path is missing")
    if not path.is_file():
        raise ValueError(f"{label} readback missing: {path}")
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        raise ValueError(f"{label} readback does not match compiled transaction payload: {path}")


def _resolve(*, repo_root: Path, token: Any) -> Path:
    path = Path(str(token or "").strip())
    if not path.is_absolute():
        path = repo_root / path
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"compiled readback path escapes repo root: {resolved}") from exc
    return resolved


def _mapping(value: Any) -> Mapping[Any, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["raise_for_compiled_backlog_and_atlas_readback"]
