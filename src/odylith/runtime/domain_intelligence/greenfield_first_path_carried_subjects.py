"""Subject carry helpers for confirmed greenfield first paths."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_actor_roles import ACTOR_ROLE_NOUNS
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import ACTOR_SIGNATURE_STOPWORDS
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import leading_subject_prefix

_SPLIT_ACTION_VERB_PATTERN = action_verb_pattern(exclude={"keep", "keeps"})
_SUBJECT_PREFIX_BOUNDARY_WORDS = frozenset(
    {
        "at",
        "by",
        "for",
        "from",
        "if",
        "in",
        "of",
        "on",
        "that",
        "through",
        "to",
        "via",
        "when",
        "where",
        "which",
        "while",
        "with",
        "without",
    }
)


def carried_subject_prefix(value: str) -> str:
    text = clean_first_path_text(value).strip()
    if re.match(r"^(?:after|before|during|once|until|when|while)\b", text, flags=re.IGNORECASE):
        return ""
    subject = leading_subject_prefix(value)
    if subject:
        return subject
    modal = re.match(
        r"^(?P<subject>[A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z][A-Za-z0-9'/-]*){0,5}?)\s+"
        r"(?:can|could|may|might|must|should|will|would|needs?\s+to|has\s+to|have\s+to)\s+"
        r"(?P<action>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if modal and MATERIAL_ACTION_RE.match(modal.group("action")):
        candidate = modal.group("subject").strip()
        candidate_terms = {
            term.casefold().strip(".,:;")
            for term in candidate.split()
            if term.strip(".,:;")
        }
        if not candidate_terms & _SUBJECT_PREFIX_BOUNDARY_WORDS:
            return candidate
    pronoun = re.match(r"^(?P<subject>they|we|he|she|it)\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
    if pronoun and MATERIAL_ACTION_RE.match(pronoun.group("tail")):
        raw_subject = pronoun.group("subject").casefold()
        return raw_subject[:1].upper() + raw_subject[1:]
    if MATERIAL_ACTION_RE.match(text):
        return ""
    candidates: list[str] = []
    for action in MATERIAL_ACTION_RE.finditer(text):
        prefix = text[: action.start()].strip(" .,;:")
        subject = _actor_subject_prefix_candidate(prefix, full_text=text)
        if subject:
            candidates.append(subject)
    if candidates:
        return max(candidates, key=lambda candidate: len(label_terms(candidate)))
    actor_action = re.match(
        rf"^(?P<subject>(?:(?:a|an|the|one|this|that|each|another)\s+)?"
        rf"[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){{1,5}}?)\s+"
        rf"(?P<tail>{_SPLIT_ACTION_VERB_PATTERN}\b.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if actor_action and MATERIAL_ACTION_RE.match(actor_action.group("tail")):
        return actor_action.group("subject").strip()
    match = re.match(r"^(?P<subject>[A-Z][A-Za-z0-9_-]{2,})\s+(?P<tail>.+)$", text)
    if match and MATERIAL_ACTION_RE.match(match.group("tail")):
        return match.group("subject")
    return ""


def _actor_subject_prefix_candidate(prefix: str, *, full_text: str) -> str:
    raw = clean_first_path_text(prefix).strip(" .,;:")
    if not raw:
        return ""
    raw_words = {word.casefold().strip(".,:;") for word in raw.split() if word.strip(".,:;")}
    if not raw_words - ACTOR_SIGNATURE_STOPWORDS:
        return ""
    candidates = tuple(dict.fromkeys((_trim_trailing_unowned_action_tail(raw), raw)))
    for candidate in candidates:
        if label_terms(candidate) and looks_like_actor_led_subject_prefix(candidate, full_text):
            return candidate
    return ""


def _trim_trailing_unowned_action_tail(value: str) -> str:
    text = clean_first_path_text(value).strip(" .,;:")
    words = [word.strip(".,:;()[]{}") for word in text.split() if word.strip(".,:;()[]{}")]
    if len(words) < 3:
        return text
    tail = words[-1].casefold()
    if tail in ACTOR_ROLE_NOUNS or tail in _SUBJECT_PREFIX_BOUNDARY_WORDS:
        return text
    head_words = words[:-1]
    if head_words[-1].casefold() not in ACTOR_ROLE_NOUNS:
        return text
    return " ".join(head_words).strip(" .,;:")


def carried_subject_action_verb(subject_prefix: str, verb: str) -> str:
    subject = clean_first_path_text(subject_prefix).casefold()
    if subject in {"they", "we"} or looks_like_plural_subject(subject):
        return base_action_clause(verb)
    return third_person_action_verb(verb)


def looks_like_plural_subject(value: str) -> bool:
    words = [word.strip(".,:;").casefold() for word in clean_first_path_text(value).split() if word.strip(".,:;")]
    if not words:
        return False
    head = words[-1]
    return len(head) > 3 and head.endswith("s") and not head.endswith(("ics", "ss", "us"))
