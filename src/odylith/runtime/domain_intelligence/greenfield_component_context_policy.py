"""Scope policy for candidate Registry component context clauses."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text


def is_deferred_or_outside_clause(value: Any) -> bool:
    """Exclude explicit non-release scope from component-owned context."""

    text = clean_artifact_text(value, split_parentheses=True).casefold()
    return bool(
        re.search(r"\b(?:outside|beyond|not\s+in|not\s+part\s+of)\s+(?:the\s+)?(?:first|initial|release|proof|scope|boundary)\b", text)
        or re.search(r"\b(?:deferred|out\s+of\s+scope|future\s+release|later\s+release)\b", text)
    )


def is_generic_proof_behavior_clause(value: Any) -> bool:
    """Exclude generic proof instructions from owned domain objects."""

    text = clean_artifact_text(value, split_parentheses=True).casefold()
    return bool(
        re.search(r"\b(?:can|must|should)\s+reproduc(?:e|es|ed|ing)\b", text)
        or re.search(r"\bexplains?\s+missing\s+or\s+invalid\s+input\s+with\s+a\s+clear\s+blocker\b", text)
        or re.search(r"\bkeeps?\s+replayable\s+evidence\s+for\s+review\b", text)
    )


__all__ = ["is_deferred_or_outside_clause", "is_generic_proof_behavior_clause"]
