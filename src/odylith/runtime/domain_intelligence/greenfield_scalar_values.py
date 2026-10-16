"""Regex-free scalar coercion for typed Greenfield validation paths."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string


def nested_text_values(value: Any) -> tuple[str, ...]:
    """Flatten nested typed values into unique non-empty scalar text."""

    if value is None:
        return ()
    if isinstance(value, Mapping):
        return unique_text_values(value.values())
    if isinstance(value, (list, tuple, set)):
        return unique_text_values(value)
    token = normalize_string(value)
    return (token,) if token else ()


def unique_text_values(values: Iterable[Any]) -> tuple[str, ...]:
    """Preserve the first spelling of each case-insensitive scalar value."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for token in nested_text_values(value):
            key = token.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(token)
    return tuple(result)


def scalar_word_count(value: Any) -> int:
    """Count ASCII alphanumeric runs without importing prose parsers."""

    count = 0
    inside_word = False
    for character in normalize_string(value):
        visible = character.isascii() and character.isalnum()
        if visible and not inside_word:
            count += 1
        inside_word = visible
    return count


__all__ = ["nested_text_values", "scalar_word_count", "unique_text_values"]
