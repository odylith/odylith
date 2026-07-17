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


def prewrite_path_leak_issues(owner: str, value: Any) -> list[str]:
    """Reject ephemeral staging paths in durable pre-confirm projections."""

    leaked = sorted(
        {
            token
            for token in text_values(value)
            if "odylith-greenfield-prewrite-" in token
        }
    )
    if not leaked:
        return []
    return [f"{owner} contains staged prewrite temp path(s) instead of durable target paths"]


__all__ = ["prewrite_path_leak_issues", "same_component_artifact_path"]
