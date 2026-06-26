"""Parse human-actor responsibility text from confirmed intent rows."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_actor_terms import CONFIRMED_ACTOR_ROLE_TERMS as _ROLE_WORDS
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal as _word_has_role_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count


_INLINE_ACTION_DESCRIPTION_VERBS = {
    "acknowledging",
    "asking",
    "assigning",
    "checking",
    "classifying",
    "configuring",
    "coordinating",
    "creating",
    "drafting",
    "entering",
    "following",
    "handling",
    "helping",
    "logging",
    "managing",
    "monitoring",
    "owning",
    "preparing",
    "recording",
    "receiving",
    "requesting",
    "responding",
    "reviewing",
    "running",
    "sharing",
    "tracking",
    "using",
    "watching",
}


def actor_row_description(value: str) -> str:
    text = _clean(value)
    for separator in (":", " — ", " – ", " - "):
        head, sep, body = text.partition(separator)
        body = body.strip(" .")
        if (
            sep
            and _word_count(head) <= 10
            and _word_count(body) >= 4
            and not re.search(r"\b(can act|supports the accepted path|additional accepted items)\b", body, re.IGNORECASE)
        ):
            return body
    comma = re.match(
        r"^(?P<head>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?),\s+"
        r"(?P<body>(?:a|an|the|one)\s+[A-Za-z][A-Za-z0-9 /&'()-]{2,120})$",
        text,
        flags=re.IGNORECASE,
    )
    if comma and 1 <= _word_count(comma.group("head")) <= 5 and _word_count(comma.group("body")) >= 2:
        return comma.group("body").strip(" .")
    relative = re.match(
        r"^(?P<head>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+(?:who|that)\s+(?P<body>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if relative and 1 <= _word_count(relative.group("head")) <= 6 and _word_count(relative.group("body")) >= 3:
        return relative.group("body").strip(" .")
    inline = _inline_action_description(text)
    if inline:
        return inline
    return ""


def readable_actor_description(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    first = text.split(maxsplit=1)[0].casefold().strip(".,;:")
    if first.endswith("ing"):
        if " or " in text.casefold() and "," not in text and " and " not in text.casefold().replace(" or ", " "):
            return f"supports by {text}"
        return text
    return text


def actor_head_contains_role(value: str) -> bool:
    words = [word.casefold().strip(".,;:()") for word in _clean(value).replace("/", " ").split()]
    if not words:
        return False
    if _word_has_role_signal(words[-1]):
        return True
    if len(words) >= 2 and " ".join(words[-2:]) in _ROLE_WORDS:
        return True
    return 1 <= len(words) <= 4 and not all(word in {"a", "an", "the", "one"} for word in words)


def _inline_action_description(value: str) -> str:
    words = _clean(value).split()
    if len(words) < 3:
        return ""
    for index, word in enumerate(words[1:], start=1):
        token = word.casefold().strip(".,;:")
        head = " ".join(words[:index]).strip(" .")
        if token not in _INLINE_ACTION_DESCRIPTION_VERBS and not (
            token.endswith("ing") and _actor_head_has_explicit_role_signal(head)
        ):
            continue
        tail = " ".join(words[index:]).strip(" .")
        if not tail or not actor_head_contains_role(head):
            continue
        return tail
    return ""


def _actor_head_has_explicit_role_signal(value: str) -> bool:
    words = [word.casefold().strip(".,;:()") for word in _clean(value).replace("/", " ").split()]
    if not words:
        return False
    return _word_has_role_signal(words[-1]) or (len(words) >= 2 and " ".join(words[-2:]) in _ROLE_WORDS)


__all__ = ["actor_head_contains_role", "actor_row_description", "readable_actor_description"]
