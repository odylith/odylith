"""Shared term indexing for greenfield artifact specificity checks."""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token


def ordered_terms(
    value: Any,
    *,
    stopwords: Iterable[str] = (),
    minimum: int = 4,
    stem_ing: bool = False,
) -> list[str]:
    """Return stable normalized terms after applying caller-owned stopwords."""

    stop = tuple(sorted({str(item or "").casefold() for item in stopwords}))
    return list(_ordered_terms_cached(_clean(value).casefold(), stop, minimum, stem_ing))


@lru_cache(maxsize=4096)
def _ordered_terms_cached(
    cleaned_text: str,
    stopwords: tuple[str, ...],
    minimum: int,
    stem_ing: bool,
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", cleaned_text):
        token = normalize_domain_token(raw, minimum=minimum, stopwords=stopwords)
        if stem_ing and token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        if token and token not in seen:
            seen.add(token)
            result.append(token)
    return tuple(result)


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "ordered_terms",
]
