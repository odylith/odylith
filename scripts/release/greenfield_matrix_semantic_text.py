"""Shared lexical normalization for Greenfield release-evaluator evidence."""

from __future__ import annotations

from collections.abc import Collection
import re
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
SEMANTIC_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "before",
        "by",
        "can",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "one",
        "or",
        "that",
        "the",
        "their",
        "this",
        "to",
        "with",
    }
)
_NEGATION_RE = re.compile(r"\b(?:cannot|never|no|not|without)\b|n['’]t\b", re.IGNORECASE)


def semantic_sequence(
    value: Any,
    *,
    stopwords: Collection[str] = SEMANTIC_STOPWORDS,
) -> tuple[str, ...]:
    return tuple(token for token, _start, _end in semantic_token_spans(value, stopwords=stopwords))


def semantic_token_spans(
    value: Any,
    *,
    stopwords: Collection[str] = SEMANTIC_STOPWORDS,
) -> tuple[tuple[str, int, int], ...]:
    text = str(value or "")
    return tuple(
        (stem_token(match.group(0).casefold()), match.start(), match.end())
        for match in TOKEN_RE.finditer(text)
        if match.group(0).casefold() not in stopwords
    )


def semantic_is_negated(value: Any) -> bool:
    return bool(_NEGATION_RE.search(str(value or "")))


def semantic_ordered_coverage(expected: Any, observed: Any) -> bool:
    expected_tokens = semantic_sequence(expected)
    if not expected_tokens:
        return False
    cursor = 0
    for token in semantic_sequence(observed):
        if token != expected_tokens[cursor]:
            continue
        cursor += 1
        if cursor == len(expected_tokens):
            return True
    return False


def stem_token(value: str) -> str:
    if len(value) > 5 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 5 and value.endswith("ing"):
        stem = value[:-3]
        return stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem
    if len(value) > 4 and value.endswith("ed"):
        stem = value[:-2]
        return stem[:-1] if len(stem) > 3 and stem[-1:] == stem[-2:-1] else stem
    if len(value) > 4 and value.endswith("es") and value[:-2].endswith(("ch", "o", "s", "sh", "x", "z")):
        value = value[:-2]
    elif len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        value = value[:-1]
    if len(value) > 5 and value.endswith("e"):
        return value[:-1]
    return value


__all__ = [
    "SEMANTIC_STOPWORDS",
    "TOKEN_RE",
    "semantic_is_negated",
    "semantic_ordered_coverage",
    "semantic_sequence",
    "semantic_token_spans",
    "stem_token",
]
