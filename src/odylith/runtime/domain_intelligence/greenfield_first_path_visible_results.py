"""Visible-result disambiguation for confirmed greenfield first paths."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_status_modifiers import RESULT_STATE_MODIFIER_LEADS

_RESULT_OBJECT_MODIFIER_LEADS = RESULT_STATE_MODIFIER_LEADS | frozenset(
    {"clear", "explainable", "progress", "reviewable", "trend", "understandable"}
)
_RESULT_OBJECT_TERMS = frozenset(
    (
        "dashboard estimate estimates evidence explanation explanations history insight insights marker markers "
        "pattern patterns proof readout record report result results status summary timeline trend trends view"
    ).split()
)


def prefer_visible_result_object(value: str, action_value: str) -> bool:
    visible = clean_first_path_text(value).strip(" .")
    action = clean_first_path_text(action_value).strip(" .")
    if not visible or not action:
        return bool(visible)
    visible_words = _words(visible)
    action_words = _words(action)
    if not visible_words or not action_words:
        return False
    if ('"' in visible or "'" in visible) and len(visible_words) <= len(action_words):
        return True
    return len(visible_words) + 3 <= len(action_words) and bool(set(visible_words) & _RESULT_OBJECT_TERMS)


def starts_with_result_object_modifier(value: str) -> bool:
    words = _words(value)
    if len(words) < 2 or words[0] not in _RESULT_OBJECT_MODIFIER_LEADS:
        return False
    return bool(set(words[1:]) & _RESULT_OBJECT_TERMS)


def _words(value: str) -> list[str]:
    return [
        word.strip(".,:;()[]{}\"'").casefold()
        for word in clean_first_path_text(value).split()
        if word.strip(".,:;()[]{}\"'")
    ]
