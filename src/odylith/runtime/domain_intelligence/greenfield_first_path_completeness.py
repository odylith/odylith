"""Shared acceptance signals for concise but complete first-path behavior."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import actor_led_action_parts


def has_concise_coordinated_first_path(value: str) -> bool:
    """Accept an actor-led path with two concrete coordinated actions."""

    text = clean_confirmed_text(value)
    actor, action = actor_led_action_parts(text)
    return bool(
        actor
        and action
        and word_count(text) >= 6
        and _has_coordinated_action(text)
        and len(semantic_terms(text)) >= 4
    )


def _has_coordinated_action(value: str) -> bool:
    """Require a second action, rather than accepting a noun-list tail as one."""

    clauses = re.split(r"\b(?:and|then)\b", clean_confirmed_text(value), flags=re.IGNORECASE)
    return any(
        looks_like_finite_action(clause.strip(" ,.;:"))
        or looks_like_action_clause(clause.strip(" ,.;:"))
        for clause in clauses[1:]
        if clause.strip(" ,.;:")
    )


__all__ = ["has_concise_coordinated_first_path"]
