"""Shared scalar and mapping coercion helpers for runtime hot paths."""

from __future__ import annotations

from typing import Any, Mapping


def mapping_copy(value: Any) -> dict[str, Any]:
    """Return a mutable dict copy when the input behaves like a mapping."""
    return dict(value) if isinstance(value, Mapping) else {}


def int_value(value: Any) -> int:
    """Parse a scalar as an integer, falling back to zero on invalid input."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
