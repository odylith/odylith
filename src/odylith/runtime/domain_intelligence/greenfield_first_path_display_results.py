"""Display-carrier visible-result extraction for greenfield first paths."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_result_objects import drop_result_recipient
from odylith.runtime.domain_intelligence.greenfield_text import normalize_reviewed_result_nouns
from odylith.runtime.domain_intelligence.greenfield_visible_result_focus import focused_visible_result_object

_DISPLAY_CARRIER_TERMS = (
    "app",
    "application",
    "card",
    "dashboard",
    "ledger",
    "page",
    "panel",
    "product",
    "record",
    "screen",
    "system",
    "tool",
    "view",
    "workspace",
)
_DISPLAY_ACTION_PATTERN = r"displays?|presents?|renders?|shows?|surfaces"


def display_carrier_result_object(value: str, *, limit: int) -> str:
    """Return the object shown by a visible-result carrier such as a record or view."""

    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    carrier_pattern = "|".join(re.escape(term) for term in _DISPLAY_CARRIER_TERMS)
    match = re.match(
        rf"^(?:a|an|the)?\s*(?:[a-z0-9_-]+\s+){{0,4}}(?:{carrier_pattern})\s+"
        rf"(?:{_DISPLAY_ACTION_PATTERN})\s+(?P<object>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    result = re.split(r"(?<=[.!?])\s+", match.group("object"), maxsplit=1)[0].strip(" .,;:")
    result = drop_result_recipient(result).strip(" .,;:") or result
    if not result:
        return ""
    result = focused_visible_result_object(normalize_reviewed_result_nouns(result).strip(" ."))
    return clip_first_path_phrase(result, limit=limit)


__all__ = ["display_carrier_result_object"]
