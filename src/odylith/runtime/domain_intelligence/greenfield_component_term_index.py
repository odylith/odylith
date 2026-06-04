"""Component-local term indexing for Registry contract quality gates."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms

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

SECTION_TERM_STOPWORDS = TERM_STOPWORDS | {
    "accept",
    "block",
    "field",
    "refus",
    "source-backed",
    "structured",
}


def ordered_domain_terms(text: Any) -> list[str]:
    """Return stable, non-structural terms suitable for component-local prose."""

    return ordered_terms(text, stopwords=TERM_STOPWORDS)


def component_domain_terms(text: Any) -> set[str]:
    """Return normalized component-local terms as a set for overlap checks."""

    return set(ordered_domain_terms(text))


def section_domain_terms(text: Any) -> set[str]:
    """Return component spec section terms without reusable section scaffolding."""

    return {token for token in ordered_domain_terms(text) if token not in SECTION_TERM_STOPWORDS}


def component_local_terms(
    *,
    text_terms: set[str],
    name_terms: set[str],
    all_text_terms: Sequence[set[str]],
    repeated_name_terms: set[str],
) -> set[str]:
    """Return terms that make one component spec distinct from its siblings."""

    own_name_terms = name_terms - repeated_name_terms
    terms = text_terms - repeated_name_terms
    counts: dict[str, int] = {}
    for candidate in terms:
        counts[candidate] = sum(1 for body_terms in all_text_terms if candidate in body_terms)
    majority = 1 if len(all_text_terms) <= 1 else max(2, len(all_text_terms) // 2)
    return own_name_terms | {term for term in terms if counts.get(term, 0) <= majority and term not in TERM_STOPWORDS}


__all__ = [
    "SECTION_TERM_STOPWORDS",
    "STRUCTURAL_TERMS",
    "TERM_STOPWORDS",
    "component_domain_terms",
    "component_local_terms",
    "ordered_domain_terms",
    "section_domain_terms",
]
