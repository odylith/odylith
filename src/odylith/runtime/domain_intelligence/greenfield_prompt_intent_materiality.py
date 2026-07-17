"""Materiality rules for title-only greenfield prompt evidence."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms


PRODUCT_CONTAINER_TERMS = frozenset(
    {
        "app",
        "application",
        "board",
        "console",
        "dashboard",
        "engine",
        "platform",
        "portal",
        "product",
        "service",
        "system",
        "tool",
        "workbench",
        "workspace",
    }
)
GENERIC_SCOPE_TERMS = frozenset(
    {
        "build",
        "create",
        "dashboard",
        "manage",
        "planner",
        "proposal",
        "repair",
        "repairs",
        "schedule",
        "scheduling",
        "task",
        "team",
        "workspace",
    }
)
_MATERIAL_AMBIGUITY_RE = re.compile(
    r"\b(?:either|multiple|several|possible|unsure|unclear)\b[^.!?]{0,80}\b(?:path|product|workflow|option|direction)s?\b",
    re.IGNORECASE,
)
_PURPOSE_ONLY_REQUEST_RE = re.compile(r"\bto\s+use\s+for\b", re.IGNORECASE)


def title_supports_conservative_first_path(*, title: str, evidence: str) -> bool:
    """Return whether a domain-anchored product title can seed visible assumptions."""

    evidence_text = str(evidence or "")
    if _MATERIAL_AMBIGUITY_RE.search(evidence_text) or _PURPOSE_ONLY_REQUEST_RE.search(evidence_text):
        return False
    terms = [term.casefold() for term in label_terms(title)]
    if len(terms) < 4 or not set(terms) & PRODUCT_CONTAINER_TERMS:
        return False
    domain_terms = set(terms) - PRODUCT_CONTAINER_TERMS - GENERIC_SCOPE_TERMS
    return len(domain_terms) >= 3


__all__ = ["title_supports_conservative_first_path"]
