"""Shared term indexing for greenfield artifact specificity checks."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
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
    aliases: Mapping[str, str] | None = None,
    prefix_aliases: Mapping[str, str] | None = None,
) -> list[str]:
    """Return stable normalized terms after applying caller-owned stopwords and aliases."""

    stop = tuple(sorted({str(item or "").casefold() for item in stopwords}))
    alias_rows = _alias_rows(aliases)
    prefix_alias_rows = tuple(
        sorted(_alias_rows(prefix_aliases), key=lambda row: (-len(row[0]), row[0], row[1]))
    )
    return list(
        _ordered_terms_cached(
            _clean(value).casefold(),
            stop,
            minimum,
            stem_ing,
            alias_rows,
            prefix_alias_rows,
        )
    )


def _alias_rows(aliases: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    return tuple(
        sorted(
            (str(key or "").strip().casefold(), str(alias or "").strip().casefold())
            for key, alias in (aliases or {}).items()
            if str(key or "").strip() and str(alias or "").strip()
        )
    )


@lru_cache(maxsize=4096)
def _ordered_terms_cached(
    cleaned_text: str,
    stopwords: tuple[str, ...],
    minimum: int,
    stem_ing: bool,
    aliases: tuple[tuple[str, str], ...],
    prefix_aliases: tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    alias_map = dict(aliases)
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", cleaned_text):
        token = normalize_domain_token(raw, minimum=minimum, stopwords=stopwords)
        if stem_ing and token.endswith("ing") and len(token) > 6:
            token = token[:-3]
        token = alias_map.get(token, token)
        for prefix, alias in prefix_aliases:
            if token.startswith(prefix):
                token = alias
                break
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
