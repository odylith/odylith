"""Compound noun disambiguation for first-path action parsing."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import base_action_verb
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words

ACTION_NOUNS = frozenset("audit capture change control record release replay report review test".split())
_ACTION_HOMONYM_OBJECT_MODIFIERS = ACTION_NOUNS | {"display", "export", "return"}
_SHORT_COMPOUND_NOUN_MODIFIERS = frozenset({"replay"})
_OBJECT_HEADS = frozenset(
    {
        "case",
        "cases",
        "decision",
        "decisions",
        "evidence",
        "finding",
        "findings",
        "note",
        "notes",
        "outcome",
        "outcomes",
        "order",
        "orders",
        "package",
        "packages",
        "proof",
        "record",
        "records",
        "result",
        "results",
        "signoff",
        "state",
        "status",
        "summary",
        "timeline",
        "timelines",
        "window",
        "windows",
    }
)
_LIST_RESULT_HEADS = frozenset(
    {
        *_OBJECT_HEADS,
        "approval",
        "approvals",
        "certificate",
        "certificates",
        "exclusion",
        "exclusions",
        "ledger",
        "ledgers",
        "recommendation",
        "recommendations",
        "readiness",
        "sign-off",
        "sign-offs",
    }
)
_SPECIFIC_DECISION_RESULT_HEADS = frozenset({"approval", "approvals", "decision", "decisions"})


def starts_with_compound_noun_object(value: str, *, allow_short: bool = False) -> bool:
    """Return true when an action-looking token is a noun modifier in an object phrase."""

    return _compound_noun_index(value, allow_short=allow_short) is not None


def action_homonym_result_object(value: str) -> bool:
    """Return true for a short artifact phrase whose modifier is also an action."""

    words = visible_words(clean_first_path_text(value))
    return bool(
        2 <= len(words) <= 4
        and words[0].casefold() in _ACTION_HOMONYM_OBJECT_MODIFIERS
        and words[-1].casefold() in _OBJECT_HEADS
    )


def action_word_inside_compound_noun(value: str, action_start: int) -> bool:
    """Return true when a matched action word is actually inside a compound noun."""

    words = _word_spans(value)
    for index, (_word, start, end) in enumerate(words):
        if start <= action_start < end:
            return _compound_noun_index(value, required_index=index) is not None
    return False


def action_word_starts_result_list_noun(value: str, action_start: int) -> bool:
    """Return true when an action-looking word starts a visible-result noun list."""

    text = clean_first_path_text(value)
    words = _word_spans(text)
    for index, (word, start, end) in enumerate(words):
        if not start <= action_start < end or word not in ACTION_NOUNS:
            continue
        if index + 1 >= len(words):
            return False
        boundary = text[end : words[index + 1][1]]
        if not any(marker in boundary for marker in (",", ";", ":")):
            return False
        tail_heads = {item[0] for item in words[index + 1 : index + 9]}
        return bool(tail_heads & _LIST_RESULT_HEADS)
    return False


def source_list_item_is_nominal(source: str, item: str) -> bool:
    """Return whether an action-shaped item belongs to an established object list."""

    segments = [clean_first_path_text(part).strip(" .") for part in clean_first_path_text(source).split(",")]
    item_key = _list_item_key(item)
    for index, segment in enumerate(segments):
        segment_key = _list_item_key(segment)
        if not segment_key.startswith(item_key) or index < 2:
            continue
        prior = [_list_item_key(row) for row in segments[index - 2 : index]]
        if all(not _starts_with_material_action(row) for row in prior):
            return True
    return False


def specific_decision_result_object(value: str) -> bool:
    words = [word.casefold() for word in visible_words(clean_first_path_text(value))]
    while words and words[0] in {"and", "or"}:
        words.pop(0)
    return bool(len(words) >= 2 and words[-1] in _SPECIFIC_DECISION_RESULT_HEADS)


def _starts_with_material_action(value: str) -> bool:
    words = visible_words(clean_first_path_text(value))
    if not words:
        return False
    if action_homonym_result_object(value):
        return False
    first = words[0].casefold()
    if looks_like_base_action_token(base_action_verb(first)) or looks_like_finite_action_token(first):
        return True
    for action_index in range(1, min(4, len(words))):
        subject = " ".join(words[:action_index])
        action = words[action_index].casefold()
        if has_actor_role_word(subject) and (
            looks_like_base_action_token(base_action_verb(action)) or looks_like_finite_action_token(action)
        ):
            return True
    return False


def _list_item_key(value: str) -> str:
    text = clean_first_path_text(value).strip(" .").casefold()
    for prefix in ("and ", "or "):
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text


def _compound_noun_index(
    value: str,
    *,
    required_index: int | None = None,
    allow_short: bool = False,
) -> int | None:
    words = _word_spans(value)
    if len(words) < (2 if allow_short else 3):
        return None
    if len(words) == 2 and words[0][0] not in _SHORT_COMPOUND_NOUN_MODIFIERS:
        return None
    start = 0 if required_index == 0 or required_index is None else 1
    for index, (word, _start, _end) in enumerate(words[start:-1], start=start):
        if required_index is not None and index != required_index:
            continue
        if word not in ACTION_NOUNS:
            continue
        if words[index + 1][0] in _OBJECT_HEADS:
            return index
    return None


def _word_spans(value: str) -> list[tuple[str, int, int]]:
    text = clean_first_path_text(value)
    return [
        (match.group(0).casefold(), match.start(), match.end())
        for match in re.finditer(r"[A-Za-z][A-Za-z0-9']*", text)
    ]


__all__ = [
    "ACTION_NOUNS",
    "action_word_inside_compound_noun",
    "action_word_starts_result_list_noun",
    "action_homonym_result_object",
    "source_list_item_is_nominal",
    "specific_decision_result_object",
    "starts_with_compound_noun_object",
]
