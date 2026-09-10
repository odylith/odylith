"""Small, typed metadata helpers for Atlas rendering."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from odylith.runtime.surfaces import display_text


def clean_display_text(value: Any) -> str:
    """Return Atlas display text without inline Markdown emphasis."""

    return display_text.strip_inline_markdown_emphasis(value)


def clean_display_rows(
    rows: Sequence[Mapping[str, Any]],
    fields: Sequence[str],
) -> list[dict[str, Any]]:
    """Clean selected display fields while preserving row structure."""

    cleaned_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        cleaned = dict(row)
        for field in fields:
            if field in cleaned:
                cleaned[field] = clean_display_text(cleaned.get(field, ""))
        cleaned_rows.append(cleaned)
    return cleaned_rows


def svg_viewbox_dimensions(svg_path: Path) -> tuple[float, float] | None:
    """Read positive SVG viewBox dimensions through the XML structure."""

    if not svg_path.is_file():
        return None
    try:
        root = ElementTree.parse(svg_path).getroot()
    except (OSError, ElementTree.ParseError):
        return None
    raw = next(
        (
            str(value).strip()
            for key, value in root.attrib.items()
            if key.casefold() == "viewbox"
        ),
        "",
    )
    parts = raw.replace(",", " ").split()
    if len(parts) != 4:
        return None
    try:
        width, height = float(parts[2]), float(parts[3])
    except ValueError:
        return None
    return (width, height) if width > 0 and height > 0 else None


__all__ = ["clean_display_rows", "clean_display_text", "svg_viewbox_dimensions"]
