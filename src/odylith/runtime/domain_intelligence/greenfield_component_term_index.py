"""Component-local term indexing for Registry contract quality gates."""

from __future__ import annotations

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


def ordered_domain_terms(text: Any) -> list[str]:
    """Return stable, non-structural terms suitable for component-local prose."""

    return ordered_terms(text, stopwords=TERM_STOPWORDS)


__all__ = [
    "STRUCTURAL_TERMS",
    "TERM_STOPWORDS",
    "ordered_domain_terms",
]
