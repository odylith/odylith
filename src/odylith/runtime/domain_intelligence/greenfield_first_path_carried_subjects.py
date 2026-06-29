"""Subject carry helpers for confirmed greenfield first paths."""

from __future__ import annotations

import re

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix

_SPLIT_ACTION_VERB_PATTERN = action_verb_pattern(exclude={"keep", "keeps"})


def carried_subject_prefix(value: str) -> str:
    subject = leading_subject_prefix(value)
    if subject:
        return subject
    text = clean_first_path_text(value).strip()
    pronoun = re.match(r"^(?P<subject>they|we|he|she|it)\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
    if pronoun and MATERIAL_ACTION_RE.match(pronoun.group("tail")):
        raw_subject = pronoun.group("subject").casefold()
        return raw_subject[:1].upper() + raw_subject[1:]
    for action in MATERIAL_ACTION_RE.finditer(text):
        prefix = text[: action.start()].strip(" .,;:")
        if len(label_terms(prefix)) >= 2 and looks_like_actor_led_subject_prefix(prefix, text):
            return prefix
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
