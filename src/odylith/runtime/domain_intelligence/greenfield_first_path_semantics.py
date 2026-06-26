"""First-path parsing for confirmed greenfield generation."""

from __future__ import annotations

import re
from typing import Any, Sequence

from odylith.runtime.common.prose_grammar import action_base_verb_pattern
from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_following_action_verbs
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import repair_modal_base_form_drift
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE as _MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text as _clean
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment as _action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    clean_visible_result_phrase as _clean_visible_result_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import is_trivial_start as _is_trivial_start
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    leading_subject_prefix as _leading_subject_prefix,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    looks_like_visible_result as _looks_like_visible_result,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    nominal_visible_result_object as _nominal_visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    strip_action_subject as _strip_action_subject,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_action_clause as _visible_action_clause,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_result_object as _visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_text import unique_text

_ACTION_BASE_VERB_PATTERN = action_base_verb_pattern()
_ACTION_VERB_PATTERN = action_verb_pattern()
_SPLIT_ACTION_VERB_PATTERN = action_verb_pattern(exclude={"keep", "keeps"})

_OPEN_PLUS_MATERIAL_RE = re.compile(
    r"^\s*(?P<subject>(?:a|an|the)?\s*[^,.;]{0,80}?)\b(?:open|opens|launch|launches)\b"
    r"(?P<object>\s+[^,.;]{1,80}?)\s+\band\b\s+(?P<material>.+)$",
    re.IGNORECASE,
)

_ACTION_SPLIT_RE = re.compile(r"\s*(?:;|(?<=[.!?])\s+|\s+\bthen\b\s+)\s*", re.IGNORECASE)

_FIRST_PATH_PREFIXES = (
    r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
    r"^the first complete path starts? (?:when|with)\s+",
    r"^first complete path starts? (?:when|with)\s+",
    r"^the first complete path to prove should be\s*:?\s*",
    r"^first complete path to prove should be\s*:?\s*",
    r"^the first path starts? (?:when|with)\s+",
    r"^first path starts? (?:when|with)\s+",
    r"^the first path is\s+",
    r"^first path\s*:?\s*",
)


def first_path_model(value: Any) -> FirstPathModel:
    raw = _clean(value)
    steps = tuple(_first_path_steps(raw))
    material = _material_action(steps) or (steps[0] if steps else "")
    visible = _visible_outcome(steps)
    recovery = _recovery_action(steps)
    return FirstPathModel(
        raw_path=raw,
        steps=steps,
        material_action=material,
        visible_outcome=visible,
        recovery_action=recovery,
    )


def material_first_path_action(value: Any, *, fallback: str = "") -> str:
    model = first_path_model(value)
    return model.material_action or _clean(fallback)


def first_path_steps(value: Any) -> tuple[str, ...]:
    return first_path_model(value).steps


def _first_path_steps(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    text = _strip_first_path_frame(text)
    text = re.sub(r"\bthat\s+single\s+loop\s*[–—-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)(?:this|that)\s+(?:single\s+)?(?:path|loop|journey|flow)\s+[–—-]\s*.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    value_tail = ""
    value_match = re.search(
        r"\bso\s+the\s+(?:first\s+)?(?:end-to-end\s+)?value\s+is\s*:\s*(?P<tail>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if value_match:
        value_tail = value_match.group("tail")
        text = text[: value_match.start()].strip(" ,.;:")
    if not re.search(r"\b\d+[.)]\s*", text):
        text = re.sub(r"\s+(?:flow|journey|path)\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        pieces = numbered
        if ":" in pieces[0]:
            pieces[0] = pieces[0].rsplit(":", 1)[-1].strip(" .")
    else:
        pieces = _split_action_pieces(text)
    normalized: list[str] = []
    for piece in pieces:
        cleaned = _clean_step(piece)
        if _valid_step(cleaned):
            normalized.append(cleaned)
    if value_tail:
        for piece in _split_action_pieces(value_tail):
            cleaned = _clean_step(piece)
            if _valid_step(cleaned) and re.search(
                r"\b(?:see|sees|show|shows|view|views|review|reviews|receive|receives)\b",
                cleaned,
                re.IGNORECASE,
            ):
                normalized.append(cleaned)
    if len(normalized) > 1 and _is_trivial_start(normalized[0]):
        normalized = normalized[1:]
    return _unique(_drop_leading_context_fragments(_merge_leading_modifier_steps(normalized)))


def _merge_leading_modifier_steps(steps: Sequence[str]) -> list[str]:
    """Attach comma-split modifier tails back to the result they qualify."""

    merged: list[str] = []
    for step in steps:
        cleaned = _clean(step).strip(" .")
        if not cleaned:
            continue
        if merged and _is_leading_modifier_step(cleaned):
            merged[-1] = f"{merged[-1]} {_lower_initial(cleaned)}".strip()
            continue
        merged.append(cleaned)
    return merged


def _drop_leading_context_fragments(steps: Sequence[str]) -> list[str]:
    rows = list(steps)
    while len(rows) > 1 and _is_leading_context_fragment(rows[0]) and any(
        _step_has_action_signal(step) for step in rows[1:]
    ):
        rows.pop(0)
    return rows


def _is_leading_context_fragment(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or _step_has_action_signal(text):
        return False
    return len(label_terms(text)) <= 6


def _step_has_action_signal(value: str) -> bool:
    text = _clean(value).strip(" .")
    return bool(
        text
        and (
            _MATERIAL_ACTION_RE.search(text)
            or _looks_like_visible_result(text)
            or _connector_core_starts_action_clause(text)
            or looks_like_finite_action(text)
        )
    )


def _is_leading_modifier_step(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:alongside|as|at|by|during|for|from|including|inside|into|on|through|to|toward|towards|using|via|while|with|without)\b",
            _clean(value),
            flags=re.IGNORECASE,
        )
    )


def _lower_initial(value: str) -> str:
    text = _clean(value)
    return text[:1].casefold() + text[1:] if text else ""


def _strip_first_path_frame(value: str) -> str:
    text = _clean(value).strip()
    for pattern in _FIRST_PATH_PREFIXES:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    if ":" not in text:
        return text
    head, tail = text.split(":", 1)
    if _first_path_frame_head(head) and len(label_terms(tail)) >= 3:
        return tail.strip(" .:")
    return text


def _first_path_frame_head(value: str) -> bool:
    words = {
        word.strip(".,:;()[]{}").casefold()
        for word in _clean(value).replace("-", " ").split()
        if word.strip(".,:;()[]{}")
    }
    if "path" not in words:
        return False
    if not words & {"first", "release", "complete", "accepted"}:
        return False
    return bool(words & {"prove", "proves", "proven", "show", "shows", "demonstrate", "demonstrates", "validate", "validates"})


def _material_action(steps: Sequence[str]) -> str:
    if not steps:
        return ""
    for step in steps:
        if _is_trivial_start(step):
            continue
        match = _OPEN_PLUS_MATERIAL_RE.match(step)
        if match and _MATERIAL_ACTION_RE.search(match.group("material")):
            return _sentence_case(_action_chain_fragment(step))
        if _MATERIAL_ACTION_RE.search(step):
            return _sentence_case(_action_chain_fragment(step))
    return _sentence_case(_action_chain_fragment(steps[0]))


def _visible_outcome(steps: Sequence[str]) -> str:
    terminal_choice = _terminal_choice_outcome(steps)
    if terminal_choice:
        return _sentence_case(terminal_choice)
    preferred: list[str] = []
    fallback: list[str] = []
    for step in reversed(steps):
        if _is_meta_visible_result_summary(step) or _is_scope_or_deferred_statement(step):
            continue
        if _is_routing_handoff_step(step):
            continue
        if _looks_like_visible_result(step):
            cleaned = _clean_visible_result_phrase(step) or step
            if re.search(r"\b(?:compare|compares|display|displays|find|finds|produce|produces|publish|publishes|recompute|recomputes|report|reports|render|renders|return|returns|save|saves|see|sees|show|shows|update|updates|view|views|receive|receives)\b", cleaned, flags=re.IGNORECASE) and not re.search(
                r"\b(?:accept|accepts|click|clicks|choose|chooses|dismiss|dismisses)\b",
                cleaned,
                flags=re.IGNORECASE,
            ):
                preferred.append(_visible_action_clause(cleaned) or _visible_result_object(cleaned) or cleaned)
            else:
                fallback.append(_visible_action_clause(cleaned) or _visible_result_object(cleaned) or cleaned)
    if preferred:
        return _sentence_case(preferred[0])
    if fallback:
        return _sentence_case(fallback[0])
    for step in reversed(steps):
        if not _is_scope_or_deferred_statement(step):
            return _sentence_case(_nominal_material_outcome(step) or step)
    return ""


def _nominal_material_outcome(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    stripped = _strip_action_subject(text).strip(" .")
    if not stripped or not _MATERIAL_ACTION_RE.search(stripped):
        return ""
    nominal = _nominal_visible_result_object(stripped).strip(" .")
    return nominal if nominal and nominal != stripped else ""


def _terminal_choice_outcome(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        text = _clean(step).strip(" .")
        if not text or _is_scope_or_deferred_statement(text) or _is_routing_handoff_step(text):
            continue
        match = re.match(
            r"^(?:(?:a|an|the|one|this|that|each|another)\s+)?"
            r"(?:[A-Za-z][A-Za-z0-9'/-]*\s+){0,5}?"
            r"(?:choose|chooses|select|selects)\s+(?P<object>.+)$",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return ""
        result_object = re.sub(r"^(?:a|an|the)\s+", "", _clean(match.group("object")).strip(" ."), flags=re.IGNORECASE)
        return f"selected {result_object}" if result_object else ""
    return ""


def _is_routing_handoff_step(value: str) -> bool:
    words = {
        word.strip(".,:;").casefold()
        for word in _clean(value).replace("-", " ").split()
        if word.strip(".,:;")
    }
    return bool(words & {"route", "routed", "routes", "send", "sends"} and "to" in words)


def _is_meta_visible_result_summary(value: str) -> bool:
    """Return whether a step only names the parser's visible-result marker."""

    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    if _is_meta_loop_summary(text):
        return True
    if "visible-result event" in lowered:
        return True
    return bool(re.match(r"^(?:this|the)\s+.+\bis\s+the\s+visible\s+result\b", text, flags=re.IGNORECASE))


def _is_meta_loop_summary(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    lowered = text.casefold()
    if re.match(r"^(?:this|that)\s+(?:single\s+)?(?:path|loop|journey|flow)\b", lowered):
        return True
    return bool(
        re.search(
            r"\b(?:smallest\s+version\s+of\s+the\s+whole\s+product|whole\s+product\s+working\s+end\s+to\s+end)\b",
            lowered,
        )
        and re.search(r"\b(?:path|loop|journey|flow)\b", lowered)
    )


def _recovery_action(steps: Sequence[str]) -> str:
    for step in reversed(steps):
        if re.search(r"\b(?:edit|edits|correct|corrects|recover|recovers|retry|retries|delete|deletes|revise|revises)\b", step, re.IGNORECASE):
            return _sentence_case(step)
    return ""


def _clean_step(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"^(?:(?:release\s+\S+|the\s+first\s+release|first\s+release)\s+)?"
        r"(?:succeeds?|is\s+trusted|is\s+proven|works)\s+when\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^\d+[.)]\s*", "", text)
    text = re.sub(r"\bthat single loop\b\s*[–—-]?\s*", "", text, flags=re.IGNORECASE)
    if _is_meta_visible_result_summary(text):
        return ""
    text = _clean_visible_result_phrase(text) or text
    text = re.sub(
        r",?\s+and\s+(?:completes?|ends?|finishes?)\s+(?:the\s+)?(?:flow|journey|loop|moment|path|session)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")
    text = _normalize_role_can_step(text)
    text = _normalize_subjectless_action_step(text)
    text = repair_modal_base_form_drift(text)
    text = _strip_dangling_step_tail(text)
    return _sentence_case(text)


def _strip_dangling_step_tail(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    words = text.split()
    dangling = {"against", "alongside", "as", "at", "by", "for", "from", "in", "into", "of", "on", "to", "with", "without"}
    while len(words) > 3 and words[-1].casefold().strip(".,;:") in dangling:
        words.pop()
    return " ".join(words).strip(" .")


def _normalize_role_can_step(value: str) -> str:
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
    if role_words & {"how", "if", "that", "what", "when", "where", "whether", "which", "while", "who", "whom", "whose", "why"}:
        return text
    rest = _normalize_role_can_rest(match.group("rest"))
    return f"{role} {third_person_action_verb(match.group('verb'))}{rest}".strip(" .")


def _normalize_role_can_rest(value: str) -> str:
    rest = str(value or "")

    def replace_comma(match: re.Match[str]) -> str:
        prefix = " and " if match.group("and") else ", "
        return f"{prefix}{third_person_action_verb(match.group('verb'))}"

    rest = re.sub(
        rf"\s*,\s+(?P<and>and\s+)?(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b",
        replace_comma,
        rest,
        flags=re.IGNORECASE,
    )
    return re.sub(
        rf"\s+and\s+(?P<verb>{_ACTION_BASE_VERB_PATTERN})\b",
        lambda match: f" and {third_person_action_verb(match.group('verb'))}",
        rest,
        flags=re.IGNORECASE,
    )


def _normalize_subjectless_action_step(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or _leading_subject_prefix(text):
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


def _split_action_pieces(value: str) -> list[str]:
    pieces: list[str] = []
    subject_prefix = ""
    for raw_segment in [part.strip(" .") for part in _ACTION_SPLIT_RE.split(value) if part.strip(" .")]:
        for purpose_segment in _split_purpose_action_tail(raw_segment):
            for segment in _split_temporal_action_tail(purpose_segment):
                current = ""
                for part in [piece.strip(" .") for piece in re.split(r",\s+", segment) if piece.strip(" .")]:
                    if current and _starts_new_action_clause(part) and not _continues_subject_object_list(part, current):
                        pieces.append(current.strip(" ."))
                        current = _with_carried_subject(part, subject_prefix)
                    else:
                        current = f"{current}, {part}" if current else _with_carried_subject(part, subject_prefix)
                    explicit_subject = _carried_subject_prefix(current)
                    if explicit_subject:
                        subject_prefix = explicit_subject
                if current:
                    pieces.append(current.strip(" ."))
    return pieces


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
    tail = _normalize_role_can_step(match.group("tail").strip(" ,"))
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
    if not match or not _MATERIAL_ACTION_RE.search(text[: match.start()]):
        return [text]
    base = _base_from_gerund_action(match.group("verb"))
    if not base:
        return [text]
    head = text[: match.start()].strip(" ,")
    tail = match.group("tail").strip(" ,")
    action = f"{base} {tail}".strip(" .")
    return [part for part in (head, action) if part]


def _base_from_gerund_action(value: str) -> str:
    token = str(value or "").casefold().strip(".,;:")
    if not token.endswith("ing") or len(token) <= 5:
        return ""
    stem = token[:-3]
    candidates = [stem, f"{stem}e"]
    if len(stem) >= 3 and stem[-1:] == stem[-2:-1]:
        candidates.append(stem[:-1])
    for candidate in candidates:
        if _MATERIAL_ACTION_RE.fullmatch(candidate):
            return base_action_clause(candidate)
    return ""


def _with_carried_subject(value: str, subject_prefix: str) -> str:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    if not subject_prefix or _leading_subject_prefix(text):
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
            f"{_carried_subject_action_verb(subject_prefix, adverbial.group('verb'))}{adverbial.group('tail')}"
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
        return f"{subject_prefix} {_carried_subject_action_verb(subject_prefix, action.group('verb'))}{action.group('tail')}"
    if subject_prefix and _connector_core_starts_action_clause(text):
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
    if _leading_subject_prefix(core) or _carried_subject_prefix(core):
        return False
    if _connector_core_starts_action_clause(core):
        return False
    return bool(_carried_subject_prefix(current))


def _connector_core_starts_action_clause(value: str) -> bool:
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


def _carried_subject_action_verb(subject_prefix: str, verb: str) -> str:
    subject = _clean(subject_prefix).casefold()
    if subject in {"they", "we"} or _looks_like_plural_subject(subject):
        return base_action_clause(verb)
    return third_person_action_verb(verb)


def _looks_like_plural_subject(value: str) -> bool:
    words = [word.strip(".,:;").casefold() for word in _clean(value).split() if word.strip(".,:;")]
    if not words:
        return False
    head = words[-1]
    return len(head) > 3 and head.endswith("s") and not head.endswith(("ics", "ss", "us"))


def _carried_subject_prefix(value: str) -> str:
    subject = _leading_subject_prefix(value)
    if subject:
        return subject
    text = _clean(value).strip()
    pronoun = re.match(r"^(?P<subject>they|we|he|she|it)\s+(?P<tail>.+)$", text, flags=re.IGNORECASE)
    if pronoun and _MATERIAL_ACTION_RE.match(pronoun.group("tail")):
        raw_subject = pronoun.group("subject").casefold()
        return raw_subject[:1].upper() + raw_subject[1:]
    match = re.match(r"^(?P<subject>[A-Z][A-Za-z0-9_-]{2,})\s+(?P<tail>.+)$", text)
    if match and _MATERIAL_ACTION_RE.match(match.group("tail")):
        return match.group("subject")
    return ""


def _starts_new_action_clause(value: str) -> bool:
    text = re.sub(r"^(?:and|then|later|then\s+later)\s+", "", _clean(value), flags=re.IGNORECASE).strip()
    if not text:
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


def _valid_step(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if re.match(r"^(?:this|that)\s+is\s+one\s+full\s+loop\b", text, flags=re.IGNORECASE):
        return False
    if re.match(r"^one\s+full\s+loop\s+from\b", text, flags=re.IGNORECASE):
        return False
    if _is_meta_loop_summary(text):
        return False
    if _is_scope_or_deferred_statement(text):
        return False
    token_count = len(label_terms(text))
    if token_count < 2:
        return False
    if token_count <= 3 and not _MATERIAL_ACTION_RE.search(text):
        return False
    if re.fullmatch(r"(?:capture|view|edit|create|done|path|mean|person)(?:\s*,\s*(?:capture|view|edit|create|done|path|mean|person))*", text, re.IGNORECASE):
        return False
    return True


def _is_scope_or_deferred_statement(value: str) -> bool:
    """Return whether a clause describes release limits, not first-path behavior."""

    text = _clean(value).strip(" .")
    if not text:
        return False
    lowered = text.casefold()
    if re.search(r"\b(?:act|follow(?:-|\s+)up|research|respond|retry|return)\s+later\b", lowered) and _MATERIAL_ACTION_RE.search(
        text
    ):
        if not re.search(r"\b(?:defer|deferred|future|not\s+included|not\s+claim|outside|release|scope)\b", lowered):
            return False
    if re.search(
        r"\b(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?release|outside\s+scope|"
        r"stay\s+outside|stays\s+outside|deferred|future|not\s+included|not\s+claim|"
        r"must\s+not\s+claim|does\s+not\s+claim)\b",
        lowered,
    ):
        return True
    return bool(
        re.search(r"\b(?:multi|external|automated|long-term|broader|production-scale|fleet-wide)\b", lowered)
        and re.search(r"\b(?:scope|release|stay|stays|outside|deferred|later|future|not)\b", lowered)
    )


def _sentence_case(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return text[:1].upper() + text[1:]


def _unique(values: Sequence[str]) -> list[str]:
    return list(unique_text(_clean(value) for value in values))

__all__ = [
    "FirstPathModel",
    "first_path_model",
    "first_path_steps",
    "material_first_path_action",
]
