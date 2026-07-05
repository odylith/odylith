"""Actor-led open-class action recovery for first-path prose."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text

_OPEN_ACTION_BLOCKED_HEADS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "before",
        "by",
        "for",
        "from",
        "if",
        "in",
        "into",
        "of",
        "on",
        "or",
        "the",
        "then",
        "through",
        "to",
        "until",
        "via",
        "when",
        "where",
        "while",
        "with",
        "without",
    }
)
_SUBJECT_PREFIX_PREPOSITIONS = frozenset(
    {"at", "by", "for", "from", "in", "of", "on", "through", "to", "via", "with", "without"}
)
_SUBORDINATE_SUBJECT_MARKERS = frozenset({"if", "that", "when", "where", "whether", "which", "while"})
_SYSTEM_SUBJECT_TERMS = frozenset(
    "app application dashboard engine model os pipeline platform product service system tool view workspace".split()
)


def actor_led_open_action_parts(value: str) -> tuple[str, str]:
    text = clean_first_path_text(value).strip(" .")
    if not text or MATERIAL_ACTION_RE.search(text):
        return "", ""
    token_spans = list(re.finditer(r"[A-Za-z0-9][A-Za-z0-9'-]*", text))
    for index in range(1, min(len(token_spans), 6)):
        prefix = text[: token_spans[index].start()].strip(" .,;:")
        if not _looks_like_open_actor_prefix(prefix):
            continue
        candidate = text[token_spans[index].start() :].strip(" .,;:")
        if _looks_like_open_actor_action(candidate):
            return prefix, base_following_action_verbs(candidate)
    return "", ""


def _looks_like_open_actor_action(value: str) -> bool:
    words = [
        word.strip(".,:;()[]{}")
        for word in clean_first_path_text(value).split()
        if word.strip(".,:;()[]{}")
    ]
    if len(words) < 2:
        return False
    first = words[0].casefold()
    if (
        not first
        or first in _OPEN_ACTION_BLOCKED_HEADS
        or looks_like_base_action_token(first)
        or looks_like_finite_action_token(first)
        or first.endswith(("ed", "ing", "s"))
    ):
        return False
    return bool(re.match(r"^[a-z][a-z'-]{2,}$", first))


def _looks_like_open_actor_prefix(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    if not text or not _looks_like_actor_prefix(text):
        return False
    words = [word.casefold().strip(".,:;") for word in text.split() if word.strip(".,:;")]
    if not words or any(word in _SUBORDINATE_SUBJECT_MARKERS for word in words):
        return False
    if any(word in _SUBJECT_PREFIX_PREPOSITIONS for word in words):
        return False
    return _has_actor_role_signal(text) or _looks_like_plural_actor_term(words[-1])


def _looks_like_actor_prefix(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    terms = {term.casefold() for term in label_terms(value)}
    return bool(terms and len(terms) <= 6 and (not terms & _SYSTEM_SUBJECT_TERMS or _has_actor_role_signal(text)))


def _has_actor_role_signal(value: str) -> bool:
    return has_actor_role_word(value) or any(
        looks_like_actor_role_term(word) for word in clean_first_path_text(value).replace("-", " ").split()
    )


def _looks_like_plural_actor_term(value: str) -> bool:
    term = str(value or "").casefold().strip(" .")
    return len(term) > 3 and term.endswith("s") and not term.endswith(("ics", "ss", "us"))


__all__ = ["actor_led_open_action_parts"]
