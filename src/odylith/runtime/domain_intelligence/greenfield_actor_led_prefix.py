"""Actor-prefix detection for first-path action rendering."""

from __future__ import annotations

from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_roles import ACTOR_ROLE_NOUNS
from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import actor_signature
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_text import plain_title_phrase

_SUBJECT_PREFIX_PREPOSITIONS = frozenset({"at", "by", "for", "from", "in", "of", "on", "through", "to", "via", "with", "without"})
_SUBORDINATE_SUBJECT_MARKERS = frozenset({"if", "that", "when", "where", "whether", "which", "while"})


def looks_like_actor_led_subject_prefix(prefix: str, full_text: str = "") -> bool:
    """Return whether a short prefix can be stripped before a finite actor action."""

    text = clean_first_path_text(prefix).strip(" .")
    if not text:
        return False
    if "," in text or ";" in text:
        return False
    words = [word.casefold().strip(".,:;") for word in text.split() if word.strip(".,:;")]
    has_role_noun = any(looks_like_actor_role_term(word) for word in words)
    if _has_unowned_action_tail(words):
        return False
    if (looks_like_action_clause(f"{text} placeholder") or base_gerund_clause(f"{text} placeholder")) and not has_role_noun:
        return False
    if not words or _contains_subordinate_subject_marker(words) or any(word in _SUBJECT_PREFIX_PREPOSITIONS for word in words):
        return False
    whole = clean_first_path_text(full_text).strip(" .")
    if whole and (leading_subject_prefix(whole) or actor_signature(whole)):
        return True
    if plain_title_phrase(text):
        return True
    return 2 <= len(words) <= 5 or (len(words) == 1 and _looks_like_plural_actor_term(words[0]))


def _contains_subordinate_subject_marker(words: list[str]) -> bool:
    return any(word in _SUBORDINATE_SUBJECT_MARKERS for word in words)


def _has_unowned_action_tail(words: list[str]) -> bool:
    if words and looks_like_action_clause(f"{words[0]} placeholder") and not any(
        looks_like_actor_role_term(word) for word in words[1:]
    ):
        return True
    for index in range(1, len(words)):
        token = words[index]
        if token in ACTOR_ROLE_NOUNS or looks_like_actor_role_term(token):
            continue
        if not looks_like_action_clause(f"{token} placeholder"):
            continue
        if (
            any(looks_like_actor_role_term(word) for word in words[index + 1 :])
            and not looks_like_finite_action_token(token)
        ):
            continue
        return True
    return False


def _looks_like_plural_actor_term(value: str) -> bool:
    term = str(value or "").casefold().strip(" .")
    return len(term) > 3 and term.endswith("s") and not term.endswith(("ics", "ss", "us"))


__all__ = ["looks_like_actor_led_subject_prefix"]
