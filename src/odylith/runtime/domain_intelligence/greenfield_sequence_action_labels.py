"""Action-label shaping for confirmed greenfield sequence diagrams."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import compact_text

_ACTION_VERB_PATTERN = action_verb_pattern()
_ROLE_SUBJECT_HEADS = {
    "actor",
    "administrator",
    "admin",
    "applicant",
    "coordinator",
    "customer",
    "editor",
    "lead",
    "manager",
    "operator",
    "owner",
    "participant",
    "person",
    "preparer",
    "requester",
    "reviewer",
    "supervisor",
    "user",
}
_ROLE_SUBJECT_SUFFIXES = ("ant", "ent", "er", "ian", "ist", "or", "ee")
_SUBJECT_PREFIX_PREPOSITIONS = {
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "through",
    "to",
    "via",
    "with",
    "without",
}
_SUBORDINATE_SUBJECT_MARKERS = {"if", "that", "when", "where", "whether", "which", "while"}
_COMPACT_RESULT_ACTIONS = {"display", "displays", "show", "shows", "view", "views"}
_COMPACT_RESULT_HEADS = {
    "card",
    "chart",
    "dashboard",
    "panel",
    "readout",
    "result",
    "screen",
    "status",
    "summary",
    "timeline",
    "view",
}
_RESULT_PRONOUNS = {"it", "them", "this", "that"}


def strip_actor_role_subject(value: str) -> str:
    """Strip short human-role subjects before the actual action verb."""

    text = compact_text(value).strip(" .")
    if not text:
        return ""
    for match in re.finditer(rf"\b(?P<verb>{_ACTION_VERB_PATTERN})\b(?!-)", text, flags=re.IGNORECASE):
        if match.start() == 0:
            continue
        prefix = text[: match.start()].strip(" ,")
        prefix_words = prefix.split(maxsplit=1)
        if prefix_words and prefix_words[0].casefold() in {"let", "lets"}:
            continue
        if _looks_like_bare_actor_role_subject(prefix):
            return f"{match.group('verb')}{text[match.end():]}".strip(" .")
    return text


def compact_result_object_label(value: str) -> str:
    """Return a compact result-object label for small visible-result actions."""

    words = [word.strip(".,:;()[]{}") for word in compact_text(value).split() if word.strip(".,:;()[]{}")]
    if len(words) < 2 or words[0].casefold() not in _COMPACT_RESULT_ACTIONS:
        return ""
    object_words = words[1:]
    if object_words[0].casefold() in _RESULT_PRONOUNS or object_words[0].casefold() in {"a", "an", "the"}:
        return ""
    if not 2 <= len(object_words) <= 4:
        return ""
    if object_words[-1].casefold() not in _COMPACT_RESULT_HEADS:
        return ""
    label = " ".join(object_words).strip(" .")
    return f"{label[:1].upper()}{label[1:]}" if label else ""


def _looks_like_bare_actor_role_subject(value: str) -> bool:
    words = [word.strip(".,:;()[]{}").casefold() for word in compact_text(value).split() if word.strip(".,:;()[]{}")]
    if not 2 <= len(words) <= 5:
        return False
    if any(word in _SUBJECT_PREFIX_PREPOSITIONS or word in _SUBORDINATE_SUBJECT_MARKERS for word in words):
        return False
    head = words[-1]
    return head in _ROLE_SUBJECT_HEADS or (len(head) >= 5 and head.endswith(_ROLE_SUBJECT_SUFFIXES))


__all__ = ["compact_result_object_label", "strip_actor_role_subject"]
