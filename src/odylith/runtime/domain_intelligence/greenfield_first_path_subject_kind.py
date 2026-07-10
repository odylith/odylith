"""Classify explicit product-system subjects before first-path action splitting."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text


_ACTION_VERB_PATTERN = action_verb_pattern()
_GENERIC_PRODUCT_SUBJECT_PATTERN = (
    r"app|application|dashboard|engine|platform|product|service|system|tool|view|workspace"
)
_GENERIC_PRODUCT_SUBJECT_QUALIFIER_PATTERN = r"(?:[a-z][a-z0-9']*(?:[-\s]+)){0,3}"
_SYSTEM_ACTION_MODIFIER_PATTERN = r"(?:[a-z][a-z0-9'-]*ly|then|later|also|immediately|now)"
_HUMAN_ROLE_PATTERN = r"administrator|developer|manager|operator|owner|reviewer|team|user"
_FINITE_ACTION_PATTERN = rf"(?:{_ACTION_VERB_PATTERN}|[a-z][a-z'-]*(?:ed|s)|can|must|will)"


def has_explicit_generic_product_subject(value: str) -> bool:
    """Return true when a sentence explicitly assigns action to a product system."""

    text = clean_markdown_text(value).strip(" .,;:")
    return bool(
        re.search(
            rf"(?:^|[,;]\s*|\bthen\s+)(?:the\s+)?"
            rf"{_GENERIC_PRODUCT_SUBJECT_QUALIFIER_PATTERN}(?:{_GENERIC_PRODUCT_SUBJECT_PATTERN})\s+"
            rf"(?!(?:{_HUMAN_ROLE_PATTERN})\b)"
            rf"(?:{_SYSTEM_ACTION_MODIFIER_PATTERN}\s+){{0,2}}"
            rf"{_FINITE_ACTION_PATTERN}\b",
            text,
            re.IGNORECASE,
        )
    )


def preserve_system_subject_then_action(value: str) -> bool:
    """Keep a system-owned `then` clause intact for downstream ownership classification."""

    text = clean_markdown_text(value).strip(" .,;:")
    return bool(
        re.match(
            rf"^(?:the\s+)?{_GENERIC_PRODUCT_SUBJECT_QUALIFIER_PATTERN}"
            rf"(?:{_GENERIC_PRODUCT_SUBJECT_PATTERN})\s+then\s+"
            rf"(?!(?:{_HUMAN_ROLE_PATTERN})\b){_FINITE_ACTION_PATTERN}\b",
            text,
            re.IGNORECASE,
        )
    )


__all__ = ["has_explicit_generic_product_subject", "preserve_system_subject_then_action"]
