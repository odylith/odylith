"""Nominalize first-path result actions into stable visible-result objects."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import action_word_inside_compound_noun

_RESULT_ACTION_NOMINALS = {
    "capture": "captured",
    "captures": "captured",
    "close": "closed",
    "closes": "closed",
    "compare": "compared",
    "compares": "compared",
    "confirm": "confirmed",
    "confirms": "confirmed",
    "coordinate": "coordinated",
    "coordinates": "coordinated",
    "correlate": "correlated",
    "correlates": "correlated",
    "export": "exported",
    "exports": "exported",
    "emit": "emitted",
    "emits": "emitted",
    "preserve": "preserved",
    "preserves": "preserved",
    "prove": "proven",
    "proves": "proven",
    "publish": "published",
    "publishes": "published",
    "record": "recorded",
    "records": "recorded",
    "report": "reported",
    "reports": "reported",
    "save": "saved",
    "saves": "saved",
    "select": "selected",
    "selects": "selected",
    "store": "stored",
    "stores": "stored",
}


def nominal_action_result_object(value: str, result: str = "") -> str:
    """Return an action-state object for terse terminal results like `published proof`."""

    text = clean_first_path_text(value).strip(" .")
    result_object = _drop_leading_article(result).strip(" .")
    if not text:
        return ""
    action = "|".join(re.escape(verb) for verb in sorted(_RESULT_ACTION_NOMINALS, key=len, reverse=True))
    if result_object:
        object_pattern = re.escape(result_object)
        object_pattern = object_pattern.replace(r"\ ", r"\s+")
        match = re.search(
            rf"\b(?P<verb>{action})\s+(?P<object>(?:(?:a|an|the)\s+)?{object_pattern})$",
            text,
            flags=re.IGNORECASE,
        )
    else:
        match = re.search(rf"\b(?P<verb>{action})\s+(?P<object>[^.;]+)$", text, flags=re.IGNORECASE)
    if not match:
        return ""
    verb_start = match.start("verb")
    if action_word_inside_compound_noun(text, verb_start):
        return ""
    nominal = _RESULT_ACTION_NOMINALS.get(match.group("verb").casefold().strip(".,:;"))
    object_text = _drop_leading_article(match.group("object"))
    first_object_word = object_text.split(maxsplit=1)[0].casefold().strip(".,:;") if object_text.split() else ""
    if first_object_word in {"using", "with", "from", "by", "based", "backed", "supported"}:
        return ""
    if first_object_word and looks_like_actor_role_term(first_object_word):
        later_result = nominal_action_result_object(object_text, "")
        if later_result:
            return later_result
    if first_object_word in {"and", "or"}:
        return ""
    if not nominal or not object_text:
        return ""
    if nominal == "proven":
        predicate_result = _proof_predicate_result_object(object_text)
        if predicate_result:
            return predicate_result
    return f"{nominal} {object_text}".strip(" .")


def nominalize_leading_result_action(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    first, separator, rest = text.partition(" ")
    nominal = _RESULT_ACTION_NOMINALS.get(first.casefold().strip(".,:;"))
    if not nominal or not separator:
        return ""
    result = _drop_leading_article(rest.strip())
    if nominal == "proven":
        result = re.sub(r"^(?:all|each|every)\s+", "", result, flags=re.IGNORECASE).strip()
    return f"{nominal} {result}".strip()


def _drop_leading_article(value: str) -> str:
    first, separator, rest = clean_first_path_text(value).strip(" .").partition(" ")
    if separator and first.casefold() in {"a", "an", "the"}:
        return rest.strip()
    return clean_first_path_text(value).strip(" .")


def _proof_predicate_result_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    text = re.sub(r"^(?:that\s+)?", "", text, flags=re.IGNORECASE).strip(" .")
    if not text:
        return ""
    if re.match(
        r"^(?:it|this|that|they|both|each|all)\s+"
        r"(?:can\s+)?[a-z][a-z0-9'/-]+(?:s|ed|ing)?\b",
        text,
        flags=re.IGNORECASE,
    ):
        return text
    return ""


__all__ = ["nominal_action_result_object", "nominalize_leading_result_action"]
