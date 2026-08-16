"""Validate bounded canonical state objects and their transition grammar."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import contains_subject_finite_action
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import past_action_verb
from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import CONFIRMED_DANGLING_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import CONFIRMED_INTENT_VALIDATION_STOPWORDS
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


_GENERIC_CANONICAL_STATE_TERMS = frozenset("detail details information item object record state status thing".split())
_STATE_CONDITION_WORDS = frozenset("after before if once until when while".split())
_STATE_ENDPOINT_CONTROL_WORDS = frozenset(
    CONFIRMED_DANGLING_WORDS
    | CONFIRMED_INTENT_VALIDATION_STOPWORDS
    | _STATE_CONDITION_WORDS
    | {"he", "her", "him", "once", "over", "she", "them", "they", "under", "via"}
)
_NOMINAL_CONDITION_MARKERS = frozenset({"after", "before"})
_STATE_TRANSITION_CONDITION_RE = re.compile(
    r"\s+(?P<marker>after|before|if|once|when|while|until)\s+(?P<tail>.+)",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'-]*")


def canonical_state_object_is_meaningful(value: str) -> bool:
    """Return whether a bounded canonical state sentence names a concrete object."""

    match = re.fullmatch(
        r"the primary state object is\s+(?:(?:a|an|the|one)\s+)?(?P<object>[^.;]+)\.?",
        clean_text(value).strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    object_text = match.group("object")
    transition = re.fullmatch(
        r"(?P<object>.+?)\s+that\s+(?:changes?|moves?|transitions?)\s+from\s+"
        r"(?P<before>.+?)\s+to\s+(?P<after>.+)",
        object_text,
        flags=re.IGNORECASE,
    )
    if transition:
        after_text = transition.group("after")
        condition = _STATE_TRANSITION_CONDITION_RE.search(after_text)
        after = after_text[: condition.start()] if condition else after_text
        condition_is_meaningful = not condition or _condition_tail_has_meaning(
            condition.group("tail"),
            marker=condition.group("marker"),
        )
        if (
            not _state_endpoint_has_meaning(transition.group("before"))
            or not _state_endpoint_has_meaning(after)
            or not condition_is_meaningful
        ):
            return False
    noun_text = transition.group("object") if transition else object_text
    object_words = _WORD_RE.findall(noun_text)
    if object_words and object_words[0].casefold() in {"he", "her", "him", "it", "she", "them", "they"}:
        return False
    if object_words and object_words[-1].casefold().endswith("ed") and past_action_verb(object_words[-1]):
        return False
    return any(word.casefold() not in _GENERIC_CANONICAL_STATE_TERMS for word in object_words)


def _state_endpoint_has_meaning(value: str) -> bool:
    words = _WORD_RE.findall(value)
    if not words or words[0].casefold() in _STATE_CONDITION_WORDS:
        return False
    return words[-1].casefold() not in _STATE_ENDPOINT_CONTROL_WORDS and any(
        word.casefold() not in _STATE_ENDPOINT_CONTROL_WORDS for word in words
    )


def _condition_tail_has_meaning(value: str, *, marker: str) -> bool:
    words = _WORD_RE.findall(value)
    if not words or words[-1].casefold() in CONFIRMED_DANGLING_WORDS | _STATE_CONDITION_WORDS:
        return False
    material = [word for word in words if word.casefold() not in _STATE_ENDPOINT_CONTROL_WORDS]
    has_predicate = contains_subject_finite_action(value) or bool(
        len(material) == 1 and past_action_verb(material[0])
    )
    allows_nominal_event = bool(
        marker.casefold() in _NOMINAL_CONDITION_MARKERS
        and material
        and not looks_like_actor_role_term(material[-1])
        and not looks_like_action_clause(value)
    )
    return bool(has_predicate or allows_nominal_event)


__all__ = ["canonical_state_object_is_meaningful"]
