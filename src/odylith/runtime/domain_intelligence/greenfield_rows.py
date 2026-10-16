"""Shared row coercion for greenfield proposal surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    """Return mapping rows from generated greenfield list surfaces."""

    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def dict_rows(value: Any) -> list[dict[str, Any]]:
    """Return mutable dictionary rows from generated greenfield list surfaces."""

    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def row_count(value: Any) -> int:
    """Count mapping rows from generated greenfield list surfaces."""

    return len(mapping_rows(value))


def mapping_count(value: Any) -> int:
    """Count keys in generated greenfield mapping surfaces."""

    return len(value) if isinstance(value, Mapping) else 0
