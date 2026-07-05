"""Transfer-clause semantics for greenfield artifact phrase extraction."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words

_FINITE_TRANSFER_ACTIONS = frozenset(
    {
        "delivered",
        "delivering",
        "delivers",
        "forward",
        "forwarded",
        "forwarding",
        "forwards",
        "move",
        "moved",
        "moves",
        "moving",
        "pass",
        "passed",
        "passes",
        "passing",
        "route",
        "routed",
        "routes",
        "routing",
        "send",
        "sending",
        "sends",
        "sent",
    }
)
_FINITE_HAND_ACTIONS = frozenset({"handed", "handing", "hands"})
_TRANSFER_RELATION_TERMS = frozenset({"for", "into", "onto", "through", "to", "toward", "towards", "with"})
_LEADING_OBJECT_FILLERS = frozenset({"a", "an", "one", "the"})


def transfer_object_phrase(value: str) -> str:
    """Return the carried object from a transfer clause, if one is present."""

    text = clean_text(value).strip(" .")
    words = [word.casefold().strip(".,:;()[]{}") for word in visible_words(text) if word.strip(".,:;()[]{}")]
    if len(words) < 2:
        return ""
    start = _transfer_object_start(words)
    if start <= 0 or start >= len(words):
        return ""
    while start < len(words) and words[start] in _LEADING_OBJECT_FILLERS:
        start += 1
    end = len(words)
    for index in range(start, len(words)):
        if words[index] in _TRANSFER_RELATION_TERMS:
            end = index
            break
    object_words = words[start:end]
    if not object_words or len(object_words) > 8:
        return ""
    return " ".join(object_words).strip(" .")


def _transfer_object_start(words: list[str]) -> int:
    first = words[0]
    if first in _FINITE_HAND_ACTIONS:
        return 1
    if first == "hand" and len(words) > 1 and words[1] == "off":
        return 2
    if first == "hand" and any(word in _TRANSFER_RELATION_TERMS for word in words[2:]):
        return 1
    if first in _FINITE_TRANSFER_ACTIONS and any(word in _TRANSFER_RELATION_TERMS for word in words[2:]):
        return 1
    return 0


__all__ = ["transfer_object_phrase"]
