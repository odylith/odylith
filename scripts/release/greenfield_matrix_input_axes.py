"""Shared input-form and metamorphic-axis contracts for Greenfield matrices."""

from __future__ import annotations

from typing import Any


DEFAULT_INPUT_STYLE = "direct_request"
VALID_INPUT_STYLES = frozenset(
    {
        "direct_request",
        "edited_confirmation",
        "pasted_brief",
        "research_evidence",
        "thin_request",
    }
)
RELEASE_INPUT_STYLES = tuple(sorted(VALID_INPUT_STYLES))


def normalize_axis_token(value: Any) -> str:
    token = "_".join(str(value or "").strip().casefold().replace("-", " ").split())
    if not token:
        return ""
    if not all(character.isalnum() or character == "_" for character in token):
        raise ValueError("Greenfield matrix axis values must contain only letters, digits, spaces, hyphens, or underscores")
    return token


def normalize_input_style(value: Any) -> str:
    style = normalize_axis_token(value) or DEFAULT_INPUT_STYLE
    if style not in VALID_INPUT_STYLES:
        raise ValueError("Greenfield matrix input_style must be one of: " + ", ".join(RELEASE_INPUT_STYLES))
    return style


__all__ = [
    "DEFAULT_INPUT_STYLE",
    "RELEASE_INPUT_STYLES",
    "VALID_INPUT_STYLES",
    "normalize_axis_token",
    "normalize_input_style",
]
