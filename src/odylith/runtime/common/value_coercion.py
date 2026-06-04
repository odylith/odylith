"""Shared scalar, token, and mapping coercion helpers for runtime hot paths."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Mapping, Sequence, TypeVar

T = TypeVar("T")
K = TypeVar("K")

_SCALAR_SEQUENCE_TYPES = (str, bytes, bytearray)


def _trim_string(value: Any) -> str:
    return str(value or "").strip()


def mapping_copy(value: Any) -> dict[str, Any]:
    """Return a mutable dict copy when the input behaves like a mapping."""
    return dict(value) if isinstance(value, Mapping) else {}


def normalize_string(value: Any) -> str:
    """Collapse internal whitespace and trim a scalar value."""
    return " ".join(str(value or "").split()).strip()


def normalize_token(value: Any) -> str:
    """Normalize free-form text into a lowercase underscore token."""
    return normalize_string(value).lower().replace(" ", "_").replace("-", "_")


def dedupe_strings(values: Sequence[Any], *, limit: int | None = None) -> list[str]:
    """Trim, de-duplicate, and preserve string row order for list-like inputs."""
    cap = None if limit is None else max(1, int(limit))
    rows: list[str] = []
    seen: set[str] = set()
    for item in values:
        token = _trim_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if cap is not None and len(rows) >= cap:
            break
    return rows


def dedupe_by_key(values: Iterable[T], key: Callable[[T], K]) -> list[T]:
    """De-duplicate values by a caller-owned stable key while preserving order."""
    rows: list[T] = []
    seen: set[K] = set()
    for item in values:
        marker = key(item)
        if marker in seen:
            continue
        seen.add(marker)
        rows.append(item)
    return rows


def string_rows(
    value: Any,
    *,
    allow_scalar: bool = False,
    allow_sequence: bool = False,
    limit: int | None = None,
) -> list[str]:
    """Return trimmed string rows from list input, with explicit scalar or sequence opt-ins."""
    if isinstance(value, _SCALAR_SEQUENCE_TYPES):
        return dedupe_strings([value], limit=limit) if allow_scalar else []
    if isinstance(value, list):
        return dedupe_strings(value, limit=limit)
    if allow_sequence and isinstance(value, Sequence):
        return dedupe_strings(value, limit=limit)
    if not isinstance(value, Sequence):
        return []
    return []


def normalize_string_list(value: Any, *, limit: int | None = None) -> list[str]:
    """Normalize scalar or sequence input into a deduplicated string list."""
    cap = None if limit is None else max(1, int(limit))
    if not isinstance(value, Sequence) or isinstance(value, _SCALAR_SEQUENCE_TYPES):
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


def float_value(value: Any) -> float:
    """Parse a scalar as a float, falling back to zero on invalid input."""
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
