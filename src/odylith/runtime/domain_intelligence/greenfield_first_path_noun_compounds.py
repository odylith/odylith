"""Compound noun disambiguation for first-path action parsing."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text

_ACTION_NOUNS = frozenset({"audit", "capture", "change", "control", "record", "replay", "report", "review", "test"})
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


def starts_with_compound_noun_object(value: str, *, allow_short: bool = False) -> bool:
    """Return true when an action-looking token is a noun modifier in an object phrase."""

    return _compound_noun_index(value, allow_short=allow_short) is not None


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
        if not start <= action_start < end or word not in _ACTION_NOUNS:
            continue
        if index + 1 >= len(words):
            return False
        boundary = text[end : words[index + 1][1]]
        if not any(marker in boundary for marker in (",", ";", ":")):
            return False
        tail_heads = {item[0] for item in words[index + 1 : index + 9]}
        return bool(tail_heads & _LIST_RESULT_HEADS)
    return False


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
        if word not in _ACTION_NOUNS:
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
    "action_word_inside_compound_noun",
    "action_word_starts_result_list_noun",
    "starts_with_compound_noun_object",
]
