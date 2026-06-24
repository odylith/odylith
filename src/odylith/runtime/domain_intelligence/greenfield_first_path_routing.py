"""Routing-action grammar helpers for first-path rendering."""

from __future__ import annotations

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text

_ROUTING_ACTION_VERBS = frozenset(
    {
        "deliver",
        "delivers",
        "export",
        "exports",
        "forward",
        "forwards",
        "hand",
        "hands",
        "publish",
        "publishes",
        "route",
        "routes",
        "send",
        "sends",
        "share",
        "shares",
        "submit",
        "submits",
    }
)
_ROUTING_PREPOSITIONS = frozenset({"for", "into", "through", "to", "via"})


def routing_action_clause(value: str, *, strip_subject: object) -> str:
    """Return a routed action as an action, not as a result object."""

    stripped = strip_subject(clean_first_path_text(value)) if callable(strip_subject) else clean_first_path_text(value)
    text = clean_first_path_text(stripped).strip(" .")
    words = [word.strip(".,:;").casefold() for word in text.split() if word.strip(".,:;")]
    if len(words) < 4 or words[0] not in _ROUTING_ACTION_VERBS:
        return ""
    for index, word in enumerate(words[2:], start=2):
        if word in _ROUTING_PREPOSITIONS and index + 1 < len(words):
            return base_action_clause(text).strip(" .")
    return ""


__all__ = ["routing_action_clause"]
