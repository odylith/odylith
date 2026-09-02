"""Read exact canonical Greenfield intent facts without semantic inference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


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


__all__ = ["intent_text_at_path", "intent_text_rows"]
