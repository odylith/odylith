"""Shared text coercion for greenfield proposal runtime paths."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

_LIST_SPLIT_RE = re.compile(r"(?:\r?\n|;)+")
_COMMA_LIST_SPLIT_RE = re.compile(r"(?:\r?\n|;|,)+")
_LIST_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def word_count(value: Any) -> int:
    return len(visible_words(value))


def visible_words(value: Any) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z0-9]+", clean_text(value)))


def normalize_domain_token(value: Any, *, minimum: int = 4, stopwords: Iterable[str] = ()) -> str:
    """Normalize one extracted product term without corrupting common nouns.

    Greenfield renderers use these tokens to derive artifact nouns from the
    accepted intent. The normalization must stay conservative because a bad
    stem leaks directly into human-visible governance text.
    """

    token = str(value or "").strip("-_").casefold()
    if len(token) < minimum or token.isdigit() or any(char.isdigit() for char in token):
        return ""
    stop = {str(item or "").casefold() for item in stopwords}
    if token in stop:
        return ""
    if token.endswith("ies") and len(token) > 5:
        token = f"{token[:-3]}y"
    elif token == "statuses":
        token = "status"
    elif token.endswith(("ches", "shes", "xes", "zes", "sses")) and len(token) > 5:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "us", "is")):
        token = token[:-1]
    return token if len(token) >= minimum and token not in stop else ""


def text_values(
    value: Any,
    *,
    split_scalar: bool = False,
    split_commas: bool = False,
    strip_bullets: bool = False,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, Mapping):
        values: list[str] = []
        for nested in value.values():
            values.extend(
                text_values(
                    nested,
                    split_scalar=split_scalar,
                    split_commas=split_commas,
                    strip_bullets=strip_bullets,
                )
            )
        return unique_text(values)
    if isinstance(value, (list, tuple, set)):
        values = []
        for nested in value:
            values.extend(
                text_values(
                    nested,
                    split_scalar=split_scalar,
                    split_commas=split_commas,
                    strip_bullets=strip_bullets,
                )
            )
        return unique_text(values)
    if not split_scalar:
        token = clean_text(value)
        return (token,) if token else ()
    splitter = _COMMA_LIST_SPLIT_RE if split_commas else _LIST_SPLIT_RE
    values = []
    for part in splitter.split(str(value or "").strip()):
        raw = _LIST_BULLET_RE.sub("", part) if strip_bullets else part
        token = clean_text(raw)
        if token:
            values.append(token)
    return unique_text(values)


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


def collect_text_values(
    row: Mapping[str, Any],
    fields: Iterable[str],
    *,
    split_scalar: bool = False,
    split_commas: bool = False,
) -> tuple[str, ...]:
    values: list[str] = []
    for field in fields:
        values.extend(text_values(row.get(field), split_scalar=split_scalar, split_commas=split_commas))
    return tuple(values)


def delimited_text_values(value: Any) -> tuple[str, ...]:
    return text_values(value, split_scalar=True, split_commas=True, strip_bullets=True)


def collect_delimited_text_values(row: Mapping[str, Any], fields: Iterable[str]) -> tuple[str, ...]:
    values: list[str] = []
    for field in fields:
        values.extend(delimited_text_values(row.get(field)))
    return tuple(values)


def join_sentence_text(value: Any) -> str:
    result = ""
    for token in text_values(value):
        if not result:
            result = token
            continue
        separator = " " if result[-1:] in {".", "!", "?"} else "; "
        result = f"{result}{separator}{token}"
    return result.strip()


def normalize_text_list(value: Any, *, split_commas: bool = False) -> list[str]:
    return list(
        text_values(
            value,
            split_scalar=True,
            split_commas=split_commas,
            strip_bullets=True,
        )
    )
