"""Shared term indexing for greenfield artifact specificity checks."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token


_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def ordered_terms(
    value: Any,
    *,
    stopwords: Iterable[str] = (),
    minimum: int = 4,
    preserve_terms: Iterable[str] = (),
    stem_ing: bool = False,
    stem_ing_minimum_length: int = 6,
    aliases: Mapping[str, str] | None = None,
    prefix_aliases: Mapping[str, str] | None = None,
) -> list[str]:
    """Return stable normalized terms after applying caller-owned stopwords and aliases."""

    stop, preserved_terms, alias_rows, prefix_alias_rows = _index_inputs(
        stopwords=stopwords,
        preserve_terms=preserve_terms,
        aliases=aliases,
        prefix_aliases=prefix_aliases,
    )
    return list(
        _ordered_terms_cached(
            _clean(value).casefold(),
            stop,
            minimum,
            preserved_terms,
            stem_ing,
            stem_ing_minimum_length,
            alias_rows,
            prefix_alias_rows,
        )
    )


def label_terms(value: Any, *, stopwords: Iterable[str] = ()) -> list[str]:
    """Return display-label terms without semantic singularization or case folding."""

    stop = tuple(sorted({str(item or "").casefold() for item in stopwords}))
    return list(_label_terms_cached(_clean(value), stop))


def term_frequencies(
    value: Any,
    *,
    stopwords: Iterable[str] = (),
    minimum: int = 4,
    preserve_terms: Iterable[str] = (),
    stem_ing: bool = False,
    stem_ing_minimum_length: int = 6,
    aliases: Mapping[str, str] | None = None,
    prefix_aliases: Mapping[str, str] | None = None,
) -> dict[str, int]:
    """Return normalized term counts using the same token contract as ordered_terms."""

    stop, preserved_terms, alias_rows, prefix_alias_rows = _index_inputs(
        stopwords=stopwords,
        preserve_terms=preserve_terms,
        aliases=aliases,
        prefix_aliases=prefix_aliases,
    )
    counts: dict[str, int] = {}
    for term in _normalized_terms_cached(
        _clean(value).casefold(),
        stop,
        minimum,
        preserved_terms,
        stem_ing,
        stem_ing_minimum_length,
        alias_rows,
        prefix_alias_rows,
    ):
        counts[term] = counts.get(term, 0) + 1
    return counts


def _index_inputs(
    *,
    stopwords: Iterable[str],
    preserve_terms: Iterable[str],
    aliases: Mapping[str, str] | None,
    prefix_aliases: Mapping[str, str] | None,
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, str], ...],
    tuple[tuple[str, str], ...],
]:
    stop = tuple(sorted({str(item or "").casefold() for item in stopwords}))
    prefix_alias_rows = tuple(
        sorted(_alias_rows(prefix_aliases), key=lambda row: (-len(row[0]), row[0], row[1]))
    )
    return stop, _preserved_terms(preserve_terms), _alias_rows(aliases), prefix_alias_rows


def _preserved_terms(terms: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            term
            for item in terms
            if (term := str(item or "").strip("-_").casefold())
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
def _normalized_terms_cached(
    cleaned_text: str,
    stopwords: tuple[str, ...],
    minimum: int,
    preserve_terms: tuple[str, ...],
    stem_ing: bool,
    stem_ing_minimum_length: int,
    aliases: tuple[tuple[str, str], ...],
    prefix_aliases: tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    result: list[str] = []
    alias_map = dict(aliases)
    preserved = set(preserve_terms)
    for raw in _TOKEN_RE.findall(cleaned_text):
        raw_token = raw.strip("-_").casefold()
        if raw_token in preserved and raw_token not in stopwords:
            token = raw_token
        else:
            token = normalize_domain_token(raw_token, minimum=minimum, stopwords=stopwords)
        if stem_ing and token.endswith("ing") and len(token) > stem_ing_minimum_length:
            token = token[:-3]
        token = alias_map.get(token, token)
        for prefix, alias in prefix_aliases:
            if token.startswith(prefix):
                token = alias
                break
        if token:
            result.append(token)
    return tuple(result)


@lru_cache(maxsize=4096)
def _ordered_terms_cached(
    cleaned_text: str,
    stopwords: tuple[str, ...],
    minimum: int,
    preserve_terms: tuple[str, ...],
    stem_ing: bool,
    stem_ing_minimum_length: int,
    aliases: tuple[tuple[str, str], ...],
    prefix_aliases: tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for token in _normalized_terms_cached(
        cleaned_text,
        stopwords,
        minimum,
        preserve_terms,
        stem_ing,
        stem_ing_minimum_length,
        aliases,
        prefix_aliases,
    ):
        if token not in seen:
            seen.add(token)
            result.append(token)
    return tuple(result)


@lru_cache(maxsize=4096)
def _label_terms_cached(cleaned_text: str, stopwords: tuple[str, ...]) -> tuple[str, ...]:
    stop = set(stopwords)
    result: list[str] = []
    for raw in _TOKEN_RE.findall(cleaned_text):
        token = raw.strip("-_")
        if token and token.casefold() not in stop:
            result.append(token)
    return tuple(result)


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "label_terms",
    "ordered_terms",
    "term_frequencies",
]
