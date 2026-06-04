"""Component label and context windows for Registry contract differentiation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_terms import domain_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


_LABEL_COMPOUND_STOPWORDS = {
    "adapter",
    "and",
    "client",
    "component",
    "engine",
    "for",
    "in",
    "of",
    "on",
    "service",
    "store",
    "surface",
    "system",
    "the",
    "to",
    "view",
    "with",
    "workspace",
}


def literal_label_compounds(label: Any, *, noise_terms: set[str]) -> list[str]:
    """Return adjacent component-label terms for fallback ownership clauses."""

    stopwords = set(noise_terms) | _LABEL_COMPOUND_STOPWORDS
    terms = ordered_terms(_clean(label), stopwords=stopwords, minimum=2)
    rows = [f"{terms[index]} {terms[index + 1]}" for index in range(max(0, len(terms) - 1))]
    return list(unique_text(rows))


def nearby_domain_terms(label_terms: Sequence[str], context: Any, *, noise_terms: set[str], window: int = 5) -> list[str]:
    """Return normalized context terms around mentions of component label terms."""

    if not label_terms:
        return []
    tokens = _domain_token_stream(context, noise_terms=noise_terms)
    label_set = set(label_terms)
    result: list[str] = []
    for index, token in enumerate(tokens):
        if token not in label_set:
            continue
        start = max(0, index - window)
        end = min(len(tokens), index + window + 1)
        result.extend(term for term in tokens[start:end] if term)
    return list(unique_text(result))


def _domain_token_stream(value: Any, *, noise_terms: set[str]) -> list[str]:
    tokens: list[str] = []
    for raw in re.findall(r"[a-z0-9][a-z0-9_-]*", _clean(value).casefold()):
        normalized = domain_terms(raw, noise_terms=noise_terms)
        tokens.append(normalized[0] if normalized else "")
    return tokens


def _clean(value: Any) -> str:
    return clean_text(value).replace("`", "")


__all__ = ["literal_label_compounds", "nearby_domain_terms"]
