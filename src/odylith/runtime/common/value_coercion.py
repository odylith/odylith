"""Shared scalar, token, and mapping coercion helpers for runtime hot paths."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def mapping_copy(value: Any) -> dict[str, Any]:
    """Return a mutable dict copy when the input behaves like a mapping."""
    return dict(value) if isinstance(value, Mapping) else {}


def normalize_string(value: Any) -> str:
    """Collapse internal whitespace and trim a scalar value."""
    return " ".join(str(value or "").split()).strip()


def normalize_token(value: Any) -> str:
    """Normalize free-form text into a lowercase underscore token."""
    return normalize_string(value).lower().replace(" ", "_").replace("-", "_")


def normalize_string_list(value: Any, *, limit: int | None = None) -> list[str]:
    """Normalize scalar or sequence input into a deduplicated string list."""
    cap = None if limit is None else max(1, int(limit))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if cap is not None and len(rows) >= cap:
            break
    return rows


def bool_value(value: Any, *, default: bool = False) -> bool:
    """Parse a scalar as a permissive boolean with a stable fallback."""
    if isinstance(value, bool):
        return value
    token = normalize_token(value)
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off"}:
        return False
    return default


def int_value(value: Any) -> int:
    """Parse a scalar as an integer, falling back to zero on invalid input."""
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
