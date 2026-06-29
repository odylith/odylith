"""Non-goal derivation for completed greenfield Product Intent records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_confirmed_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def non_goal_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    candidates: list[str] = []
    del title
    for value in text_values(
        [
            intent.get("proof_boundary"),
            intent.get("assumptions"),
            intent.get("ambiguities"),
        ]
    ):
        for sentence in re.split(r"(?<=[.!?])\s+|;\s+", _clean(value)):
            row = _non_goal_row_from_sentence(sentence)
            if row:
                candidates.append(row)
    rows = [row for row in unique_text(candidates) if _word_count(row) >= 5]
    return rows[:4]


def _non_goal_row_from_sentence(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    lowered = text.casefold()
    for marker in ("without claiming", "without claim"):
        index = lowered.find(marker)
        if index >= 0:
            tail = text[index + len(marker) :].strip(" ,.;:")
            return _sentence(f"Do not claim {tail}") if tail else ""
    for marker in ("not claim", "not cover"):
        index = lowered.find(marker)
        if index >= 0:
            tail = text[index + len(marker) :].strip(" ,.;:")
            verb = "claim" if "claim" in marker else "cover"
            return _sentence(f"Do not {verb} {tail}") if tail else ""
    if _sentence_declares_deferred_scope(lowered):
        return _sentence(text)
    return ""


def _sentence_declares_deferred_scope(lowered: str) -> bool:
    if not lowered:
        return False
    if re.search(r"\bnot\s+later\b", lowered) and not re.search(
        r"\b(?:out\s+of\s+scope|deferred?|future|beyond\s+the\s+first|not\s+included|not\s+claim|without\s+claim)\b",
        lowered,
    ):
        return False
    if any(marker in lowered for marker in ("out of scope", "deferred", "defer ", "future", "beyond the first")):
        return True
    if re.search(r"\bnot\s+(?:required|needed|necessary)\b", lowered) and re.search(
        r"\b(?:first|release|path|scope|proof|live|integration|sync)\b",
        lowered,
    ):
        return True
    return bool(
        re.search(r"\b(?:later|future)\b", lowered)
        and re.search(r"\b(?:can|could|should|must|will|would|may|might|wait|outside|separate|after|until)\b", lowered)
    )


__all__ = ["non_goal_rows"]
