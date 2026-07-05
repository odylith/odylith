"""Short nominal visible-result phrase classification."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase
from odylith.runtime.domain_intelligence.greenfield_actor_roles import ACTOR_ROLE_NOUNS
from odylith.runtime.domain_intelligence.greenfield_text import normalize_reviewed_result_nouns

_SHORT_NOMINAL_RESULT_TERMS = frozenset(
    {
        "answer",
        "answers",
        "classification",
        "classifications",
        "decision",
        "decisions",
        "explanation",
        "explanations",
        "insight",
        "insights",
        "option",
        "options",
        "outcome",
        "outcomes",
        "package",
        "packages",
        "plan",
        "plans",
        "readiness",
        "recommendation",
        "recommendations",
        "record",
        "records",
        "report",
        "reports",
        "result",
        "results",
        "route",
        "routes",
        "state",
        "states",
        "status",
        "summary",
        "summaries",
        "view",
        "views",
    }
)
_SHORT_NOMINAL_RESULT_LEADS = frozenset(
    {
        "accepted",
        "approved",
        "blocked",
        "clear",
        "completed",
        "current",
        "final",
        "finished",
        "initial",
        "ready",
        "reviewable",
        "saved",
        "selected",
        "visible",
    }
)


def short_nominal_result_phrase(value: str, *, limit: int) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text or "," in text:
        return ""
    words = [word.strip(".,:;()[]{}").casefold() for word in text.split() if word.strip(".,:;()[]{}")]
    if len(words) < 2 or len(words) > 12:
        return ""
    result_indexes = [index for index, word in enumerate(words) if word in _SHORT_NOMINAL_RESULT_TERMS]
    if not result_indexes or words[0] in {"and", "or", "then", "while", "with", "without"}:
        return ""
    material_matches = tuple(MATERIAL_ACTION_RE.finditer(text))
    if material_matches and _has_actor_led_action_subject(text, material_matches[0].start()):
        return ""
    material_token_indexes = [
        index
        for match in material_matches
        for index, word in enumerate(words)
        if word == match.group(0).casefold().strip(".,:;")
    ]
    material_after_result = bool(result_indexes) and all(index >= result_indexes[0] for index in material_token_indexes)
    starts_with_article = words[0] in {"a", "an", "the"}
    content_lead = words[1] if starts_with_article and len(words) > 1 else words[0]
    noun_phrase_shape = (
        (starts_with_article and (not material_matches or content_lead in _SHORT_NOMINAL_RESULT_LEADS or material_after_result))
        or content_lead in _SHORT_NOMINAL_RESULT_LEADS
        or '"' in text
        or not material_matches
    )
    if not noun_phrase_shape:
        return ""
    return clip_first_path_phrase(normalize_reviewed_result_nouns(text).strip(" ."), limit=limit)


def _has_actor_led_action_subject(value: str, action_start: int) -> bool:
    prefix = clean_first_path_text(value)[:action_start].strip(" ,.")
    words = [word.strip(".,:;()[]{}").casefold() for word in prefix.split() if word.strip(".,:;()[]{}")]
    return bool(words and (set(words) & ACTOR_ROLE_NOUNS))


__all__ = ["short_nominal_result_phrase"]
