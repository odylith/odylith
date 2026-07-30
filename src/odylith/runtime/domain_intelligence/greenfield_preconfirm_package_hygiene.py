"""Path and staging-hygiene checks for a compiled greenfield package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values


def same_component_artifact_path(expected: str, actual: str) -> bool:
    """Compare governed component artifact paths by filesystem identity when possible."""

    expected_text = clean_text(expected)
    actual_text = clean_text(actual)
    if expected_text == actual_text:
        return True
    expected_path = Path(expected_text).expanduser()
    actual_path = Path(actual_text).expanduser()
    if not expected_path.is_absolute() or not actual_path.is_absolute():
        return False
    return expected_path.resolve(strict=False) == actual_path.resolve(strict=False)


def managed_repo_path(value: Any, *, repo_root: Path | None = None) -> str:
    """Return a repo-relative path only when the path belongs to that repo."""

    token = str(value or "").strip()
    path = Path(token).expanduser()
    if not token or not path.is_absolute() or repo_root is None:
        return token
    try:
        return str(path.resolve(strict=False).relative_to(Path(repo_root).expanduser().resolve(strict=False)))
    except ValueError:
        return token


def prewrite_path_leak_issues(owner: str, value: Any) -> list[str]:
    """Reject ephemeral staging paths in durable pre-confirm projections."""

    leaked = sorted(
        {
            token
            for token in text_values(value)
            if "odylith-greenfield-prewrite-" in token
            or _is_ephemeral_absolute_path(token)
        }
    )
    if not leaked:
        return []
    return [f"{owner} contains staged prewrite temp path(s) instead of durable target paths"]


def _is_ephemeral_absolute_path(value: str) -> bool:
    path = Path(str(value or "").strip()).expanduser()
    if not path.is_absolute():
        return False
    return any(part.casefold() in {"tmp", "temporaryitems"} for part in path.parts)


__all__ = ["managed_repo_path", "prewrite_path_leak_issues", "same_component_artifact_path"]
