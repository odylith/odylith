"""Component-local term indexing for Registry contract quality gates."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token

STRUCTURAL_TERMS = {
    "accepted",
    "actor",
    "application",
    "boundary",
    "candidate",
    "change",
    "component",
    "contract",
    "current",
    "detail",
    "evidence",
    "field",
    "first",
    "greenfield",
    "handoff",
    "handle",
    "implementation",
    "input",
    "local",
    "normal",
    "operator",
    "output",
    "owner",
    "planned",
    "product",
    "behavior",
    "prove",
    "service",
    "proof",
    "record",
    "release",
    "review",
    "reviewer",
    "source",
    "state",
    "status",
    "system",
    "technical",
    "traceable",
    "traced",
    "validation",
    "workstream",
}

TERM_STOPWORDS = STRUCTURAL_TERMS | {
    "about",
    "after",
    "also",
    "before",
    "between",
    "does",
    "each",
    "into",
    "must",
    "that",
    "this",
    "when",
    "where",
    "which",
    "while",
    "without",
}


def ordered_domain_terms(text: Any) -> list[str]:
    """Return stable, non-structural terms suitable for component-local prose."""

    return list(_ordered_domain_terms_cached(_clean(text).casefold()))


@lru_cache(maxsize=4096)
def _ordered_domain_terms_cached(cleaned_text: str) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", cleaned_text):
        token = normalize_domain_token(raw, stopwords=TERM_STOPWORDS)
        if token and token not in seen:
            seen.add(token)
            result.append(token)
    return tuple(result)


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "STRUCTURAL_TERMS",
    "TERM_STOPWORDS",
    "ordered_domain_terms",
]
