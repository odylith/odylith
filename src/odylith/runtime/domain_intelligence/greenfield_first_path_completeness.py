"""Shared acceptance signals for concise but complete first-path behavior."""

from __future__ import annotations

import re
from collections.abc import Callable

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model


LOW_SPECIFICITY_FIRST_ACTIONS = frozenset(
    {
        "add",
        "capture",
        "collect",
        "enter",
        "provide",
        "record",
        "save",
        "store",
        "submit",
        "upload",
    }
)


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


def has_rich_material_first_path_action(
    value: str,
    *,
    semantic_term_count: int,
) -> bool:
    """Require enough action detail after excluding an actor-led subject."""

    text = clean_confirmed_text(value).strip(" .")
    if not text:
        return False
    _actor, action = actor_led_action_parts(text)
    action_text = clean_confirmed_text(action or text).strip(" .")
    if not action_text:
        return False
    first = action_text.split(maxsplit=1)[0].casefold().strip(".,:;")
    min_words = 8 if first in LOW_SPECIFICITY_FIRST_ACTIONS else 6
    min_terms = 6 if first in LOW_SPECIFICITY_FIRST_ACTIONS else 4
    return word_count(action_text) >= min_words and semantic_term_count >= min_terms


def first_path_has_distinct_outcome(
    path: str,
    outcome: str,
    *,
    semantic_terms_for: Callable[[str], set[str]] = semantic_terms,
) -> bool:
    """Return whether a one-step path names an outcome beyond its own action."""

    model = first_path_model(path)
    if len(model.steps) >= 2:
        return True
    _actor, actor_action = actor_led_action_parts(path)
    material = clean_confirmed_text(actor_action or model.material_action).strip(" .")
    result = clean_confirmed_text(outcome).strip(" .")
    if not material or not result:
        return False
    material_first = material.split(maxsplit=1)[0].casefold().strip(".,:;")
    result_first = result.split(maxsplit=1)[0].casefold().strip(".,:;")
    if result_first == _regular_action_state_form(material_first):
        return False
    return bool(semantic_terms_for(result) - semantic_terms_for(material))


def _has_coordinated_action(value: str) -> bool:
    """Require a second action, rather than accepting a noun-list tail as one."""

    clauses = re.split(r"\b(?:and|then)\b", clean_confirmed_text(value), flags=re.IGNORECASE)
    return any(
        looks_like_finite_action(clause.strip(" ,.;:"))
        or looks_like_action_clause(clause.strip(" ,.;:"))
        for clause in clauses[1:]
        if clause.strip(" ,.;:")
    )


def _regular_action_state_form(value: str) -> str:
    term = str(value or "").casefold().strip()
    if len(term) < 4:
        return ""
    if term.endswith("e"):
        return f"{term}d"
    if len(term) > 2 and term.endswith("y") and term[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{term[:-1]}ied"
    return f"{term}ed"


__all__ = [
    "first_path_has_distinct_outcome",
    "has_concise_coordinated_first_path",
    "has_rich_material_first_path_action",
]
