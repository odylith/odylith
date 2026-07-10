"""Shared acceptance signals for concise but complete first-path behavior."""

from __future__ import annotations

import re

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
        and re.search(r"\b(?:and|then)\s+[a-z][a-z'-]*(?:ed|s)\b", text, re.IGNORECASE)
        and len(semantic_terms(text)) >= 4
    )


__all__ = ["has_concise_coordinated_first_path"]
