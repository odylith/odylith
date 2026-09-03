"""Read exact canonical Greenfield intent facts without semantic inference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

TERMINAL_RESULT_FACT_FIELDS = (
    "first_path",
    "product_story",
    "opportunity",
    "product_view",
    "success_metrics",
    "proof_boundary",
)


def intent_text_at_path(intent: Mapping[str, Any], path: str) -> str:
    """Return the exact string at one root or one-index-deep intent path."""

    if not path.startswith("/"):
        return ""
    parts = path.removeprefix("/").split("/")
    value = intent.get(parts[0])
    if len(parts) == 1:
        return value if isinstance(value, str) else ""
    if (
        len(parts) != 2
        or not parts[1].isdigit()
        or not isinstance(value, Sequence)
        or isinstance(value, (str, bytes, bytearray))
    ):
        return ""
    index = int(parts[1])
    return value[index] if index < len(value) and isinstance(value[index], str) else ""


def intent_text_rows(value: Any) -> tuple[str, ...]:
    """Return non-empty string rows from an optional intent list value."""

    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return ()
    return tuple(str(row) for row in value if str(row))


def intent_terminal_result_values(intent: Mapping[str, Any]) -> tuple[str, ...]:
    """Return exact selected output, path, and proof facts eligible as results."""

    values: list[str] = []
    for field in TERMINAL_RESULT_FACT_FIELDS:
        value = intent.get(field)
        if isinstance(value, str):
            if value:
                values.append(value)
        else:
            values.extend(intent_text_rows(value))
    return tuple(values)


__all__ = [
    "TERMINAL_RESULT_FACT_FIELDS",
    "intent_terminal_result_values",
    "intent_text_at_path",
    "intent_text_rows",
]
