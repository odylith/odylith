"""Actor and subject recovery for confirmed greenfield first-path clauses."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import ACTION_MODAL_WORDS
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_actor_led_open_action import (
    actor_led_open_action_parts as _actor_led_open_action_parts,
)
from odylith.runtime.domain_intelligence.greenfield_actor_roles import looks_like_actor_role_term
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import (
    action_word_starts_result_list_noun,
)

ACTOR_SIGNATURE_STOPWORDS = frozenset({"a", "an", "the", "one", "this", "that", "each", "another", "can"})
PRESERVED_SHORT_ACTOR_TERMS = frozenset({"ai", "ml", "ui", "ux"})
MODAL_ACTOR_MARKERS = ACTION_MODAL_WORDS
_MODAL_ACTOR_PATTERN = "|".join(re.escape(marker) for marker in sorted(MODAL_ACTOR_MARKERS))
SUBORDINATE_SUBJECT_MARKERS = frozenset({"if", "that", "when", "where", "whether", "which", "while"})
SYSTEM_SUBJECT_TERMS = frozenset(
    "app application dashboard engine model os pipeline platform product service system tool view workspace".split()
)


def strip_action_subject(value: str) -> str:
    text = clean_first_path_text(value)
    text = re.sub(r"^on\s+save,\s*", "save, ", text, flags=re.IGNORECASE)
    leading_action = MATERIAL_ACTION_RE.match(text)
    if (
        leading_action
        and not action_word_starts_result_list_noun(text, leading_action.start())
        and not _starts_with_action_shaped_actor_subject(text)
    ):
        return text
    _relative_actor, relative_action = _relative_actor_action_parts(text)
    if relative_action:
        return relative_action
    _modal_actor, modal_action = _modal_actor_action_parts(text)
    if modal_action:
        return modal_action
    _actor, actor_action = _actor_led_finite_action_parts(text)
    if actor_action:
        return actor_action
    _actor, actor_action = _actor_led_open_action_parts(text)
    if actor_action:
        return actor_action
    match = MATERIAL_ACTION_RE.search(text)
    if match and match.start() > 0:
        prefix = text[: match.start()].strip(" ,")
        modal_actor = _modal_actor_prefix(prefix)
        if match.end() == len(text):
            return text
        if modal_actor or looks_like_actor_subject_prefix(prefix):
            return text[match.start() :]
        if re.search(r"\b(?:if|that|when|where|which|while)\b", prefix, flags=re.IGNORECASE):
            return text
        if len(label_terms(prefix)) <= 6 and (
            re.search(
                r"\b(?:actor|applicant|coordinator|customer|operator|owner|participant|person|requester|reviewer|supervisor|user)\b",
                prefix,
                flags=re.IGNORECASE,
            )
            or re.search(
                r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
                prefix,
                flags=re.IGNORECASE,
            )
            or (
                re.match(r"^(?:a|an|the|one)\s+", prefix, flags=re.IGNORECASE)
                and not re.search(
                    r"\b(?:app|application|dashboard|engine|product|service|system|view|workspace)\b",
                    prefix,
                    flags=re.IGNORECASE,
                )
                and not re.search(
                    r"\b(?:at|by|for|from|in|of|on|through|to|via|with|without)\b",
                    prefix,
                    flags=re.IGNORECASE,
                )
            )
        ):
            text = text[match.start() :]
    return text


def _starts_with_action_shaped_actor_subject(value: str) -> bool:
    """Recognize role nouns such as ``release managers`` before their predicate."""

    text = clean_first_path_text(value).strip(" .")
    word_matches = list(re.finditer(r"[A-Za-z][A-Za-z0-9'-]*", text))
    if len(word_matches) < 3:
        return False
    words = [match.group(0) for match in word_matches]
    for predicate_index in range(2, min(5, len(words))):
        subject_words = words[1:predicate_index]
        if not any(looks_like_actor_role_term(word) for word in subject_words):
            continue
        if subject_words[-1].casefold() in {"a", "an", "the", "one"}:
            continue
        predicate_start = word_matches[predicate_index].start()
        if "," in text[:predicate_start]:
            continue
        if MATERIAL_ACTION_RE.match(text[predicate_start:]):
            return True
    return False


def actor_signature(value: str) -> str:
    subject = leading_subject_prefix(value)
    if not subject:
        text = clean_first_path_text(value)
        relative_actor, _relative_action = _relative_actor_action_parts(text)
        if relative_actor:
            subject = relative_actor
        modal_actor, _modal_action = _modal_actor_action_parts(text)
        if not subject and modal_actor:
            subject = modal_actor
        actor, _actor_action = _actor_led_action_parts(text)
        if not subject and actor:
            subject = actor
        match = MATERIAL_ACTION_RE.search(text)
        if not subject and match and match.start() > 0:
            if action_word_starts_result_list_noun(text, match.start()):
                return ""
            candidate = text[: match.start()].strip(" ,")
            modal_actor = _modal_actor_prefix(candidate)
            if modal_actor:
                subject = modal_actor
                candidate = ""
            if candidate and looks_like_actor_subject_prefix(candidate):
                subject = candidate
    if not subject:
        return ""
    subject = re.sub(r"^(?:a|an|the|one)\s+", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\s+can\s*$", "", subject, flags=re.IGNORECASE)
    subject = re.sub(
        r"\b(?:product|system|app|application|workspace|engine|dashboard|view)\b",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    return " ".join(
        ordered_terms(
            subject,
            minimum=3,
            stopwords=ACTOR_SIGNATURE_STOPWORDS,
            preserve_terms=PRESERVED_SHORT_ACTOR_TERMS,
        )
    )


def actor_led_action_parts(value: str) -> tuple[str, str]:
    actor, action = _actor_led_finite_action_parts(value)
    if actor and action:
        return actor, base_action_clause(action)
    return _actor_led_open_action_parts(value)


def modal_actor_action_parts(value: str) -> tuple[str, str]:
    return _modal_actor_action_parts(value)


def modal_action_fragment(value: str) -> str:
    _actor, action = _modal_actor_action_parts(value)
    return action


def looks_like_actor_subject_prefix(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    if not text or not _looks_like_actor_prefix(text):
        return False
    if re.search(rf"\b(?:{_MODAL_ACTOR_PATTERN})\s*$", text, flags=re.IGNORECASE):
        return False
    if re.search(r"[,;]", text):
        return False
    if _has_unowned_action_tail(text):
        return False
    if re.search(r"\b(?:if|that|when|where|which|while)\b", text, flags=re.IGNORECASE):
        return False
    if re.search(r"\b(?:at|by|for|from|in|of|on|through|to|via|with|without)\b", text, flags=re.IGNORECASE):
        return False
    if _has_actor_role_signal(text):
        return True
    terms = [term.casefold() for term in label_terms(text)]
    return len(terms) == 1 and _looks_like_plural_actor_term(terms[0])


def leading_subject_prefix(value: str) -> str:
    text = re.sub(
        r"^(?:and|then|later|then\s+later)\s+",
        "",
        clean_first_path_text(value),
        flags=re.IGNORECASE,
    ).strip()
    match = MATERIAL_ACTION_RE.search(text)
    if not match or match.start() == 0:
        return ""
    subject = text[: match.start()].strip()
    if not re.match(r"^(?:a|an|the|one|this|that|each|another)\s+", subject, flags=re.IGNORECASE):
        return ""
    subject = re.sub(
        r"\s+(?:[A-Za-z]+ly|again|already|eventually|finally|later|next|then)$",
        "",
        subject,
        flags=re.IGNORECASE,
    ).strip()
    if len(label_terms(subject)) > 6:
        return ""
    return subject


def _actor_led_finite_action_parts(value: str) -> tuple[str, str]:
    text = clean_first_path_text(value).strip(" .")
    for match in MATERIAL_ACTION_RE.finditer(text):
        prefix = text[: match.start()].strip(" ,")
        if not looks_like_actor_subject_prefix(prefix):
            continue
        if action_word_starts_result_list_noun(text, match.start()):
            continue
        action = text[match.start() :].strip(" .")
        if looks_like_finite_action(action) or looks_like_action_clause(action):
            return prefix, action
    return "", ""


def _actor_led_action_parts(value: str) -> tuple[str, str]:
    actor, action = _actor_led_finite_action_parts(value)
    if actor and action:
        return actor, base_action_clause(action)
    return _actor_led_open_action_parts(value)


def _modal_actor_prefix(value: str) -> str:
    words = [word.strip(".,:;") for word in clean_first_path_text(value).split() if word.strip(".,:;")]
    if len(words) < 2:
        return ""
    marker_start = -1
    if words[-1].casefold() in MODAL_ACTOR_MARKERS:
        marker_start = len(words) - 1
    elif len(words) >= 3 and words[-2].casefold() in {"need", "needs"} and words[-1].casefold() == "to":
        marker_start = len(words) - 2
    if marker_start <= 0:
        return ""
    actor = " ".join(words[:marker_start]).strip(" .")
    if not _looks_like_actor_prefix(actor):
        return ""
    return actor


def _relative_actor_action_parts(value: str) -> tuple[str, str]:
    pattern = r"^(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,100}?)\s+(?:who|that)\s+(?P<action>.+)$"
    match = re.match(pattern, clean_first_path_text(value).strip(" ."), flags=re.IGNORECASE)
    if not match:
        return "", ""
    actor = match.group("actor").strip(" .")
    action = match.group("action").strip(" .")
    return (actor, action) if action and MATERIAL_ACTION_RE.search(action) and _looks_like_actor_prefix(actor) else ("", "")


def _modal_actor_action_parts(value: str) -> tuple[str, str]:
    text = clean_first_path_text(value).strip(" .")
    words = [word.strip(".,:;") for word in text.split() if word.strip(".,:;")]
    if len(words) < 3:
        return "", ""
    for match in re.finditer(rf"\b(?:{_MODAL_ACTOR_PATTERN}|needs?\s+to)\b", text, flags=re.IGNORECASE):
        actor = text[: match.start()].strip(" .")
        action = text[match.end() :].strip(" .")
        if _looks_like_actor_prefix(actor) and action and not _contains_subordinate_subject_marker(actor):
            return actor, action
    return "", ""


def _contains_subordinate_subject_marker(value: str) -> bool:
    tokens = [word.casefold().strip(".,:;") for word in clean_first_path_text(value).split()]
    return any(token in SUBORDINATE_SUBJECT_MARKERS for token in tokens)


def _looks_like_actor_prefix(value: str) -> bool:
    text = clean_first_path_text(value).strip(" .")
    terms = {term.casefold() for term in label_terms(value)}
    return bool(terms and len(terms) <= 6 and (not terms & SYSTEM_SUBJECT_TERMS or _has_actor_role_signal(text)))


def _has_unowned_action_tail(value: str) -> bool:
    words = [word.casefold().strip(".,:;") for word in clean_first_path_text(value).split() if word.strip(".,:;")]
    if words and looks_like_action_clause(f"{words[0]} placeholder") and not any(
        looks_like_actor_role_term(word) for word in words[1:]
    ):
        return True
    for index in range(1, len(words)):
        token = words[index]
        if looks_like_actor_role_term(token):
            continue
        if not looks_like_action_clause(f"{token} placeholder"):
            continue
        if any(looks_like_actor_role_term(word) for word in words[index + 1 :]):
            continue
        return True
    return False


def _has_actor_role_signal(value: str) -> bool:
    return any(looks_like_actor_role_term(word) for word in clean_first_path_text(value).replace("-", " ").split())


def _looks_like_plural_actor_term(value: str) -> bool:
    term = str(value or "").casefold().strip(" .")
    return len(term) > 3 and term.endswith("s") and not term.endswith(("ics", "ss", "us"))


__all__ = [
    "SYSTEM_SUBJECT_TERMS",
    "actor_led_action_parts",
    "actor_signature",
    "leading_subject_prefix",
    "looks_like_actor_subject_prefix",
    "modal_action_fragment",
    "modal_actor_action_parts",
    "strip_action_subject",
]
