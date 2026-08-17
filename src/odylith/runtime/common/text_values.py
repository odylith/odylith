"""Structural text collection without domain interpretation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def text_values(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        return unique_text(nested for nested_value in value.values() for nested in text_values(nested_value))
    if isinstance(value, (list, tuple, set)):
        return unique_text(nested for nested_value in value for nested in text_values(nested_value))
    token = clean_text(value)
    return (token,) if token else ()


def unique_text(values: Iterable[Any]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        for token in text_values(value):
            key = token.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(token)
    return tuple(result)


__all__ = ["clean_text", "text_values", "unique_text"]
