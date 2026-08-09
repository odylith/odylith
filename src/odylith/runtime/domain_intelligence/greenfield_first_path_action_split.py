"""Action splitting and carried-subject repair for first-path clauses."""

from __future__ import annotations

import re
from typing import Sequence

from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_action_homonym_actor_role
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_carried_subjects import (
    carried_subject_action_verb as _carried_subject_action_verb,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_carried_subjects import (
    carried_subject_prefix as _carried_subject_prefix,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_carried_subjects import (
    looks_like_plural_subject as _looks_like_plural_subject,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_common import (
    MATERIAL_ACTION_RE as _MATERIAL_ACTION_RE,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text as _clean
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    leading_subject_prefix as _leading_subject_prefix,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_subject_kind import (
    preserve_system_subject_then_action,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import (
    action_word_inside_compound_noun as _action_word_inside_compound_noun,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import (
    starts_with_compound_noun_object as _starts_with_compound_noun_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_short_results import short_nominal_result_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_temporal import (
    base_from_gerund_action as _base_from_gerund_action,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_temporal import (
    temporal_head_can_split as _temporal_head_can_split,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_visible_results import (
    starts_with_result_object_modifier as _starts_with_result_object_modifier,
)
from odylith.runtime.domain_intelligence.greenfield_status_modifiers import RESULT_STATUS_MODIFIERS

_ACTION_BASE_VERB_PATTERN = action_base_verb_pattern()
_ACTION_CONTINUATION_SPLIT_RE = re.compile(r"\s*(?:;|\s+\bthen\b\s+)\s*", re.IGNORECASE)
_SPLIT_ACTION_VERB_PATTERN = action_verb_pattern(exclude={"keep", "keeps"})


def split_action_pieces(value: str) -> list[str]:
    pieces: list[str] = []
    previous_subject_prefix = ""
    for sentence in [part.strip(" .,;:") for part in re.split(r"(?<=[.!?])\s+", value) if part.strip(" .,;:")]:
        subject_prefix = previous_subject_prefix if _starts_with_carried_pronoun_subject(sentence) else ""
        raw_segments = (
            [sentence]
            if preserve_system_subject_then_action(sentence)
            else [
                part.strip(" .,;:")
                for part in _ACTION_CONTINUATION_SPLIT_RE.split(sentence)
                if part.strip(" .,;:")
            ]
        )
        for raw_segment in raw_segments:
            for purpose_segment in _split_purpose_action_tail(raw_segment):
                for segment in _split_temporal_action_tail(purpose_segment):
                    current = ""
                    for part in _merge_status_modifier_parts(
                        [piece.strip(" .,;:") for piece in re.split(r",\s+", segment) if piece.strip(" .,;:")]
                    ):
                        if current and _continues_adverbial_object_list(part, current):
                            current = f"{current}, {part}".strip(" .,;:")
                        elif current and _starts_new_action_clause(
                            part,
                            allow_homonym_subject=True,
                        ) and not _continues_subject_object_list(part, current):
                            pieces.append(current.strip(" .,;:"))
                            current = _with_carried_subject(part, subject_prefix)
                        else:
                            current = f"{current}, {part}" if current else _with_carried_subject(part, subject_prefix)
                        explicit_subject = _carried_subject_prefix(current)
                        if explicit_subject:
                            subject_prefix = explicit_subject
                            previous_subject_prefix = explicit_subject
                    if current:
                        pieces.append(current.strip(" .,;:"))
    return pieces


def normalize_role_can_step(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(
        r"^(?:(?:a|an|the|one)\s+)?(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,60}?)\s+can\s+"
        r"(?P<verb>[A-Za-z]+)\b(?P<rest>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    role = match.group("role").strip()
    role_words = {word.casefold().strip(".,:;") for word in role.split()}
    if role_words & {
        "how",
        "if",
        "that",
        "what",
        "when",
        "where",
        "whether",
        "which",
        "while",
        "who",
        "whom",
        "whose",
        "why",
    }:
        return text
    plural_subject = _looks_like_plural_subject(role)
    rest = _normalize_role_can_rest(match.group("rest"), third_person=not plural_subject)
    if plural_subject:
        return f"{role} can {base_action_clause(match.group('verb'))}{rest}".strip(" .")
    return f"{role} {third_person_action_verb(match.group('verb'))}{rest}".strip(" .")


def normalize_subjectless_action_step(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or _leading_subject_prefix(text) or _has_actor_led_subject_prefix(text):
        return text
    if _MATERIAL_ACTION_RE.match(text):
        text = base_action_clause(text)
    else:
        adverbial = re.match(
            r"^(?P<prefix>[A-Za-z]+ly\s+)(?P<verb>[A-Za-z]+s)\b(?P<tail>.*)$",
            text,
            flags=re.IGNORECASE,
        )
        if adverbial and _MATERIAL_ACTION_RE.match(adverbial.group("verb")):
            text = f"{adverbial.group('prefix')}{base_action_clause(adverbial.group('verb'))}{adverbial.group('tail')}"
    text = base_following_action_verbs(text)
    text = re.sub(r",\s+and\s+", " and ", text, flags=re.IGNORECASE)
    return text.strip(" .")


def connector_core_starts_action_clause(value: str) -> bool:
    text = _clean(value).strip(" .")
    if looks_like_finite_action(text):
        return True
    words = [word.strip(".,:;()[]{}").casefold() for word in text.split() if word.strip(".,:;()[]{}")]
    if len(words) < 2:
        return False
    if words[0] in {"at", "after", "before", "during", "on", "when"}:
        for index in range(1, min(len(words), 5)):
            if looks_like_finite_action(" ".join(words[index:])):
                return True
    return words[0].endswith("s") and words[1] in {
        "against",
        "as",
        "for",
        "from",
        "if",
        "into",
        "through",
        "to",
        "when",
        "with",
    }


def _starts_with_carried_pronoun_subject(value: str) -> bool:
    return bool(re.match(r"^(?:they|their|them)\b", _clean(value).strip(), flags=re.IGNORECASE))


def _merge_status_modifier_parts(parts: Sequence[str]) -> list[str]:
    rows = [_clean(part).strip(" .,;:") for part in parts if _clean(part).strip(" .,;:")]
    if len(rows) < 2:
        return rows
    merged: list[str] = []
    index = 0
    while index < len(rows):
        current = rows[index]
        if index + 1 < len(rows) and (_is_article_status_fragment(current) or _ends_with_article_status_fragment(current)):
            merged.append(f"{current}, {rows[index + 1][:1].casefold()}{rows[index + 1][1:]}".strip())
            index += 2
            continue
        merged.append(current)
        index += 1
    return merged


def _is_article_status_fragment(value: str) -> bool:
    words = [word.strip(".,:;()[]{}").casefold() for word in _clean(value).split() if word.strip(".,:;()[]{}")]
    return len(words) == 2 and words[0] in {"a", "an", "the"} and words[1] in RESULT_STATUS_MODIFIERS


def _ends_with_article_status_fragment(value: str) -> bool:
    words = [word.strip(".,:;()[]{}").casefold() for word in _clean(value).split() if word.strip(".,:;()[]{}")]
    return len(words) >= 3 and words[-2] in {"a", "an", "the"} and words[-1] in RESULT_STATUS_MODIFIERS


def _split_purpose_action_tail(value: str) -> list[str]:
    text = _clean(value).strip(" .")
    if not text:
        return []
    match = re.search(
        rf"\s+so\s+(?P<tail>(?:(?:a|an|the|one)\s+)?[A-Za-z][A-Za-z0-9 /&'()-]{{1,60}}?\s+can\s+"
        rf"(?:{_ACTION_BASE_VERB_PATTERN})\b.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match or not _MATERIAL_ACTION_RE.search(text[: match.start()]):
        return [text]
    head = text[: match.start()].strip(" ,")
    tail = _compact_final_list_comma(normalize_role_can_step(match.group("tail").strip(" ,")))
    return [part for part in (head, tail) if part]


def _split_temporal_action_tail(value: str) -> list[str]:
    text = _clean(value).strip(" .")
    if not text:
        return []
    match = re.search(
        r"\s+(?:before|after)\s+(?P<verb>[A-Za-z]+ing)\b(?P<tail>[^.;]*)$",
        text,
        flags=re.IGNORECASE,
    )
    head = text[: match.start()].strip(" ,") if match else ""
    if not match or not _temporal_head_can_split(head, actor_led_subject_prefix=_has_actor_led_subject_prefix(head)):
        return [text]
    base = _base_from_gerund_action(match.group("verb"))
    if not base:
        return [text]
    head = _compact_final_list_comma(head)
    tail = match.group("tail").strip(" ,")
    action = f"{base} {tail}".strip(" .")
    return [part for part in (head, action) if part]


def _with_carried_subject(value: str, subject_prefix: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    pronoun_action = re.match(
        rf"^they\s+(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if subject_prefix and pronoun_action and _MATERIAL_ACTION_RE.match(pronoun_action.group("verb")):
        return f"{subject_prefix} {_carried_action_verb(subject_prefix, pronoun_action.group('verb'))}{pronoun_action.group('tail')}"
    if not subject_prefix or _leading_subject_prefix(text) or _actor_role_subject_action(text):
        return text
    temporal_action = re.match(
        r"^(?P<prefix>(?:at|after|before|during|on|when)\s+[A-Za-z0-9][A-Za-z0-9 '/-]{1,40}?)\s+"
        r"(?P<verb>[A-Za-z]+)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if temporal_action and _MATERIAL_ACTION_RE.match(temporal_action.group("verb")):
        tail = temporal_action.group("tail").strip(" ,")
        tail = f" {tail}" if tail else ""
        return (
            f"{subject_prefix} {third_person_action_verb(temporal_action.group('verb'))}"
            f"{tail} {temporal_action.group('prefix').casefold()}"
        )
    adverbial = re.match(
        rf"^(?P<prefix>[A-Za-z]+ly\s+)(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if adverbial and _MATERIAL_ACTION_RE.match(adverbial.group("verb")):
        return (
            f"{subject_prefix} {adverbial.group('prefix').casefold()}"
            f"{_carried_action_verb(subject_prefix, adverbial.group('verb'))}{adverbial.group('tail')}"
        )
    finite_adverbial = re.match(
        r"^(?P<prefix>[A-Za-z]+ly\s+)(?P<verb>[A-Za-z]+)\b(?P<tail>.*)$",
        text,
        flags=re.IGNORECASE,
    )
    if finite_adverbial and _MATERIAL_ACTION_RE.match(finite_adverbial.group("verb")):
        return (
            f"{subject_prefix} {finite_adverbial.group('prefix').casefold()}"
            f"{finite_adverbial.group('verb')}{finite_adverbial.group('tail')}"
        )
    action = re.match(rf"^(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b(?P<tail>.*)$", text, flags=re.IGNORECASE)
    if action and _MATERIAL_ACTION_RE.match(action.group("verb")):
        if action.group("verb").casefold() in {"choose", "select"}:
            return text
        return f"{subject_prefix} {_carried_action_verb(subject_prefix, action.group('verb'))}{action.group('tail')}"
    if subject_prefix and connector_core_starts_action_clause(text):
        return f"{subject_prefix} {text[:1].lower()}{text[1:]}"
    if _MATERIAL_ACTION_RE.match(text):
        return f"{subject_prefix} {text[:1].lower()}{text[1:]}"
    return text


def _continues_subject_object_list(value: str, current: str) -> bool:
    words = [word.strip(".,:;()[]{}").casefold() for word in _clean(value).split() if word.strip(".,:;()[]{}")]
    if len(words) < 2 or words[0] not in {"and", "or"}:
        return False
    core = " ".join(words[1:]).strip()
    if not core:
        return False
    if _starts_new_action_clause(core):
        return False
    if _leading_subject_prefix(core) or _carried_subject_prefix(core):
        return False
    if connector_core_starts_action_clause(core):
        return False
    return bool(_carried_subject_prefix(current))


def _continues_adverbial_object_list(value: str, current: str) -> bool:
    current_text = _clean(current).strip(" .")
    if not re.search(
        r"\b(?:including|using|via|with)\s+[A-Za-z0-9]",
        current_text,
        flags=re.IGNORECASE,
    ):
        return False
    text = re.sub(r"^(?:and|or)\s+", "", _clean(value).strip(" ."), flags=re.IGNORECASE)
    if not text:
        return False
    if _has_internal_finite_action(text):
        return False
    if short_nominal_result_phrase(text, limit=180):
        return True
    first_word = text.split(maxsplit=1)[0].strip(".,:;()[]{}").casefold()
    if first_word.endswith("s") and _MATERIAL_ACTION_RE.match(text):
        return False
    if connector_core_starts_action_clause(text):
        return False
    if _has_explicit_subject_action(text):
        return False
    terms = label_terms(text)
    return 1 <= len(terms) <= 8


def _has_internal_finite_action(value: str) -> bool:
    words = [
        word.strip(".,:;()[]{}")
        for word in _clean(value).split()
        if word.strip(".,:;()[]{}")
    ]
    return any(
        0 < index < len(words) - 1 and looks_like_finite_action_token(word)
        for index, word in enumerate(words)
    )


def _has_explicit_subject_action(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if _actor_role_subject_action(text):
        return True
    if starts_subject_finite_action_clause(
        text,
        material_action_match=_MATERIAL_ACTION_RE.match,
    ):
        return True
    return bool(
        re.match(
            r"^(?:(?:a|an|the|one|this|that|each|another)\s+)?"
            r"(?:product|system|user|person|actor|app|application|workspace|engine|dashboard|view|"
            r"controller|service|platform|tool)\b"
            r"(?:\s+[A-Za-z0-9'-]+){0,5}\s+"
            rf"(?:{_SPLIT_ACTION_VERB_PATTERN})\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _actor_role_subject_action(value: str) -> bool:
    text = _clean(value).strip(" .")
    words = [word.strip(".,:;()[]{}") for word in text.split() if word.strip(".,:;()[]{}")]
    if len(words) < 3:
        return False
    for index in range(1, min(5, len(words) - 1)):
        subject = " ".join(words[:index]).strip(" .")
        action = " ".join(words[index:]).strip(" .")
        if not subject or not action:
            continue
        subject_words = subject.casefold().split()
        if subject_words and subject_words[-1] in {"a", "an", "the", "one"}:
            continue
        homonym_actor = has_action_homonym_actor_role(subject, action)
        if not (has_actor_role_word(subject) or homonym_actor):
            continue
        if not (looks_like_actor_led_subject_prefix(subject, text) or homonym_actor):
            continue
        if not _MATERIAL_ACTION_RE.match(action):
            continue
        action_words = [word for word in action.split() if word]
        if len(action_words) < 2:
            continue
        return True
    return False


def _carried_action_verb(subject_prefix: str, verb: str) -> str:
    if re.search(
        r"\b(?:can|could|may|might|must|should|will|would|needs?\s+to|has\s+to|have\s+to)\b",
        subject_prefix,
        flags=re.IGNORECASE,
    ):
        return base_action_clause(verb)
    return _carried_subject_action_verb(subject_prefix, verb)


def _starts_new_action_clause(value: str, *, allow_homonym_subject: bool = False) -> bool:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    if not text:
        return False
    words = [word.strip(".,:;()[]{}") for word in text.split() if word.strip(".,:;()[]{}")]
    if allow_homonym_subject and starts_subject_finite_action_clause(
        text,
        material_action_match=_MATERIAL_ACTION_RE.match,
    ):
        return True
    if len(words) >= 3 and any(
        _MATERIAL_ACTION_RE.match(" ".join(words[index:]))
        and looks_like_actor_led_subject_prefix(" ".join(words[:index]), text)
        for index in range(1, min(3, len(words) - 1))
    ):
        return True
    if len(words) >= 3 and words[0].casefold() not in {"a", "an", "and", "or", "the", "then"}:
        action_tail = " ".join(words[1:])
        action_match = _MATERIAL_ACTION_RE.match(action_tail)
        if action_match and not (
            _action_word_inside_compound_noun(action_tail, action_match.start())
            or _starts_with_compound_noun_object(action_tail)
        ):
            return True
    if _starts_with_compound_noun_object(text):
        return False
    if _starts_with_result_object_modifier(text):
        return False
    temporal_action = re.match(
        r"^(?:at|after|before|during|on|when)\s+[A-Za-z0-9][A-Za-z0-9 '/-]{1,40}?\s+"
        r"(?P<verb>[A-Za-z]+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if temporal_action and _MATERIAL_ACTION_RE.match(temporal_action.group("verb")):
        return True
    adverbial_action = re.match(r"^[A-Za-z]+ly\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
    if adverbial_action and _MATERIAL_ACTION_RE.match(adverbial_action.group("tail")) and len(label_terms(text)) >= 2:
        return True
    if re.match(
        r"^(?:(?:a|an|the|one|this|that|each|another|product|system|user|person|actor|app|application|workspace|engine|dashboard|view)|[A-Z][A-Za-z0-9_-]{2,})\s+"
        r"(?:[A-Za-z0-9'-]+\s+){0,5}?"
        rf"(?:{_SPLIT_ACTION_VERB_PATTERN})\b",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    return bool(_MATERIAL_ACTION_RE.match(text) and len(label_terms(text)) >= 2)


def _normalize_role_can_rest(value: str, *, third_person: bool = True) -> str:
    rest = str(value or "")
    normalize_verb = third_person_action_verb if third_person else base_action_clause

    def replace_comma(match: re.Match[str]) -> str:
        prefix = " and " if match.group("and") else ", "
        return f"{prefix}{normalize_verb(match.group('verb'))}"

    rest = re.sub(
        rf"\s*,\s+(?P<and>and\s+)?(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b",
        replace_comma,
        rest,
        flags=re.IGNORECASE,
    )
    return re.sub(
        rf"\s+and\s+(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b",
        lambda match: f" and {normalize_verb(match.group('verb'))}",
        rest,
        flags=re.IGNORECASE,
    )


def _compact_final_list_comma(value: str) -> str:
    return re.sub(r",\s+and\s+([^,.;:]+)$", r" and \1", _clean(value).strip(" ."), flags=re.IGNORECASE)


def _has_actor_led_subject_prefix(value: str) -> bool:
    text = _clean(value).strip(" .")
    match = _MATERIAL_ACTION_RE.search(text)
    if not match or match.start() <= 0:
        return False
    return looks_like_actor_led_subject_prefix(text[: match.start()].strip(), text)


def starts_subject_finite_action_clause(
    value: str,
    *,
    material_action_match,
) -> bool:
    """Return whether a comma piece starts a fresh subject-led finite action."""

    text = str(value or "").strip(" .")
    words = [word.strip(".,:;()[]{}") for word in text.split() if word.strip(".,:;()[]{}")]
    if len(words) < 3:
        return False
    subject = words[0].casefold()
    if subject in {"a", "an", "and", "or", "the", "then"}:
        return False
    action_tail = " ".join(words[1:])
    if not looks_like_finite_action(action_tail):
        return False
    if not material_action_match(action_tail):
        return False
    return bool(label_terms(subject))


__all__ = [
    "connector_core_starts_action_clause",
    "normalize_role_can_step",
    "normalize_subjectless_action_step",
    "split_action_pieces",
    "starts_subject_finite_action_clause",
]
