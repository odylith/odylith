"""First-path step derivation for confirmed greenfield Atlas output."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import third_person_action_verb
from odylith.runtime.common.value_coercion import dedupe_by_key
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import leading_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import modal_actor_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import strip_action_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_noun_compounds import starts_with_compound_noun_object
from odylith.runtime.domain_intelligence.greenfield_first_path_visible_results import starts_with_result_object_modifier
from odylith.runtime.domain_intelligence.greenfield_first_path_step_roles import drop_release_proof_control_steps
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_sentence
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


ACTION_VERB_PATTERN = action_verb_pattern()
_SPLIT_ACTION_VERB_PATTERN = action_verb_pattern(
    exclude={"keep", "keeps", "schedule", "schedules", "surface", "surfaces"}
)
_SUBJECT_ACTION_PREFIX = (
    rf"(?:(?:the|a|an|this|that|one)\s+)?"
    rf"(?:[A-Za-z][A-Za-z0-9/-]*\s+){{1,5}}(?:{ACTION_VERB_PATTERN})\b"
)
_VISIBLE_RESULT_ACTION_BASES = {
    "accepted": "Accept",
    "approved": "Approve",
    "captured": "Capture",
    "confirmed": "Confirm",
    "created": "Create",
    "generated": "Generate",
    "published": "Publish",
    "recorded": "Record",
    "saved": "Save",
    "submitted": "Submit",
    "verified": "Verify",
}
_VISIBLE_RESULT_OBJECT_NOUNS = {
    "decision",
    "evidence",
    "history",
    "proof",
    "readout",
    "record",
    "report",
    "result",
    "results",
    "status",
    "summary",
    "timeline",
    "view",
}


def sequence_event_steps(
    first_path: str,
    *,
    semantic_model: Mapping[str, Any] | None = None,
    dedupe: bool = False,
) -> list[str]:
    """Return normalized first-path event steps for sequence-style Atlas diagrams."""

    steps = drop_release_proof_control_steps(
        _drop_launcher_only_steps(_semantic_event_steps(semantic_model) or _first_path_steps(first_path))
    )
    return _dedupe_steps(steps) if dedupe else steps


def _semantic_event_steps(semantic_model: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(semantic_model, Mapping):
        return []
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return []
    rows = contract.get("events")
    if not isinstance(rows, list):
        return []
    visible_result = _compact_text(str(contract.get("visible_result") or ""))
    steps: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        text = _compact_text(str(row.get("text") or row.get("mutation") or ""))
        if _is_generated_floor_event(text, visible_result):
            continue
        if text:
            text = _normalize_event_step(text)
            text = _anchor_visible_result_step(text, visible_result)
            steps.append(text)
    rows = _dedupe_steps(drop_release_proof_control_steps(_expand_compound_steps(steps)))
    return _ensure_concise_visible_result_step(rows, visible_result)


def _is_generated_floor_event(value: str, visible_result: str) -> bool:
    target = _compact_text(visible_result).strip(" .")
    text = _compact_text(value).strip(" .")
    if not target or not text:
        return False
    target = f"{target[:1].lower()}{target[1:]}"
    return text.casefold() in {
        f"review evidence for {target}".casefold(),
        f"confirm proof for {target}".casefold(),
        f"keep {target} visible for review".casefold(),
    }


def _ensure_concise_visible_result_step(steps: list[str], visible_result: str) -> list[str]:
    rows = list(steps)
    if len(rows) >= 3:
        return rows
    candidate = _concise_visible_result_step(_terminal_result_object_phrase(rows)) or _concise_visible_result_step(visible_result)
    if not candidate:
        return rows
    candidate_key = _step_key(candidate)
    if any(_step_key(row) == candidate_key for row in rows):
        return rows
    if len(rows) == 1:
        rows.append("Review blockers, evidence, and next step")
    rows.append(candidate)
    return rows


def _terminal_result_object_phrase(steps: list[str]) -> str:
    if not steps:
        return ""
    tail = _visible_result_tail_object(steps[-1])
    if not tail:
        return ""
    return tail if _step_key(tail) != _step_key(steps[-1]) else ""


def _concise_visible_result_step(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    first, separator, rest = text.partition(" ")
    action = _VISIBLE_RESULT_ACTION_BASES.get(first.casefold().strip(".,;:"))
    if not action and separator:
        action = _default_visible_result_action(text)
        rest = text
    if not action or not separator:
        return ""
    result_object = _visible_result_tail_object(rest)
    return f"{action} {result_object}".strip() if result_object else ""


def _default_visible_result_action(value: str) -> str:
    tail = _visible_result_tail_object(value)
    if not tail:
        return ""
    words = [word.strip(".,:;()[]{}").casefold() for word in tail.split() if word.strip(".,:;()[]{}")]
    if not words:
        return ""
    if words[-1] in {"evidence", "history", "proof", "record"}:
        return "Record"
    if words[-1] in {"readout", "report", "result", "results", "status", "summary", "timeline", "view"}:
        return "Show"
    return ""


def _visible_result_tail_object(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    parts = [
        part.strip(" .,;:")
        for part in re.split(r",\s+(?:and\s+)?|\s+and\s+(?=[^,]{1,80}$)", text)
        if part.strip(" .,;:")
    ]
    for part in reversed(parts or [text]):
        words = [word.strip(".,:;()[]{}").casefold() for word in part.split() if word.strip(".,:;()[]{}")]
        if words and words[-1] in _VISIBLE_RESULT_OBJECT_NOUNS:
            return part
    return text if len(label_terms(text)) <= 5 else ""


def _step_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _compact_text(value).casefold()).strip()


def _drop_launcher_only_steps(values: list[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        if not rows and _launcher_only_step(value):
            continue
        rows.append(value)
    return rows


def _launcher_only_step(value: str) -> bool:
    text = _compact_text(value).strip(" .")
    return bool(
        len(label_terms(text)) <= 6
        and (
            re.search(r"\bopens?\s+(?:the\s+)?(?:app|web app|application|site|website|product)\b", text, flags=re.IGNORECASE)
            or re.search(r"\b(?:signs?\s+in|logs?\s+in|authenticates?)\b", text, flags=re.IGNORECASE)
        )
    )


def _normalize_event_step(value: str) -> str:
    text = _compact_text(value).strip(" .")
    if re.search(r"\bvisible-result\s+event\b", text, re.IGNORECASE):
        text = re.sub(r"\s+is\s+the\s+visible-result\s+event\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
        text = re.sub(r"^\s*this\s+", "Show the ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+[\u2014-]\s*", ": ", text, count=1)
    if re.search(r"\brenders?\s+the\s+visible\s+result\s*:", text, re.IGNORECASE):
        text = re.sub(
            r"^.*?\brenders?\s+the\s+visible\s+result\s*:\s*"
            r"(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer|[A-Za-z][A-Za-z0-9/-]*(?:\s+[A-Za-z][A-Za-z0-9/-]*){0,3})\s+"
            r"(?:sees?|views?|receives?|gets?|reads?)\s+",
            "Show ",
            text,
            flags=re.IGNORECASE,
        )
    text = normalize_visible_result_language(text)
    return text


def _anchor_visible_result_step(value: str, visible_result: str) -> str:
    text = _compact_text(value).strip(" .")
    anchored = _compact_text(visible_result).strip(" .")
    if not text or not anchored:
        return text
    result_action = _leading_result_action(text)
    if result_action:
        return f"{result_action} {anchored[:1].lower()}{anchored[1:]}"
    if not _starts_with_unanchored_result_pronoun(text):
        return text
    if _starts_with_action_word(anchored):
        return anchored
    return f"Show {anchored[:1].lower()}{anchored[1:]}"


def _leading_result_action(value: str) -> str:
    words = _leading_words(value, limit=2)
    if len(words) < 2 or words[1] not in {"it", "them", "this", "that"}:
        return ""
    if words[0] not in {"get", "gets", "read", "reads", "receive", "receives", "see", "sees", "show", "shows", "view", "views"}:
        return ""
    return _base_result_action(words[0]).capitalize()


def _base_result_action(value: str) -> str:
    return {
        "gets": "get",
        "reads": "read",
        "receives": "receive",
        "sees": "see",
        "shows": "show",
        "views": "view",
    }.get(value, value)


def _starts_with_unanchored_result_pronoun(value: str) -> bool:
    first = _leading_word(value)
    return first in {"it", "them", "this", "that"}


def _starts_with_action_word(value: str) -> bool:
    first = _leading_word(value)
    return bool(re.fullmatch(ACTION_VERB_PATTERN, first, flags=re.IGNORECASE))


def _leading_word(value: str) -> str:
    words = _leading_words(value, limit=1)
    return words[0] if words else ""


def _leading_words(value: str, *, limit: int) -> list[str]:
    words: list[str] = []
    for raw in _compact_text(value).split():
        word = raw.strip(".,;:()[]{}").casefold()
        if word:
            words.append(word)
        if len(words) >= limit:
            break
    return words


def _first_path_steps(value: str) -> list[str]:
    semantic_steps = list(first_path_steps(value))
    if semantic_steps:
        return _dedupe_steps(_expand_semantic_action_conjunctions(semantic_steps))
    text = _compact_text(value)
    if not text:
        return []
    numbered = [part.strip(" .") for part in re.split(r"(?:^|\s)\d+[.)]\s*", text) if part.strip(" .")]
    if len(numbered) > 1:
        first = numbered[0]
        if ":" in first:
            first = first.rsplit(":", 1)[-1].strip(" .")
        steps = [first, *numbered[1:]] if first else numbered[1:]
        return [_sentence(step).rstrip(".") for step in steps if len(label_terms(step)) >= 3]
    steps = [part.strip(" .") for part in re.split(r"(?<=[.!?])\s+|;\s+", text) if part.strip(" .")]
    expanded: list[str] = []
    for step in steps:
        expanded.extend(
            part.strip(" .")
            for part in re.split(r"\s+and\s+(?=(?:the\s+)?[A-Za-z]+\s+receives?\b)", step)
            if part.strip(" .")
        )
    steps = expanded
    split_steps: list[str] = []
    for step in steps:
        split_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|{_SUBJECT_ACTION_PREFIX}))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = split_steps
    expanded_steps: list[str] = []
    for step in steps:
        expanded_steps.extend(
            part.strip(" .")
            for part in re.split(
                rf"\s+and\s+(?=(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|{_SUBJECT_ACTION_PREFIX}))",
                step,
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        )
    steps = expanded_steps
    return [_sentence(step).rstrip(".") for step in steps if step]


def _expand_compound_steps(values: list[str]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        if _modal_actor_capability_step(value):
            expanded.append(_sentence(value).rstrip("."))
            continue
        parts = [
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|{_SUBJECT_ACTION_PREFIX}))",
                _compact_text(value),
                flags=re.IGNORECASE,
            )
            if part.strip(" .")
        ]
        split_parts: list[str] = []
        for part in parts or [value]:
            split_parts.extend(
                segment.strip(" .")
                for segment in re.split(
                    rf"\s+and\s+(?=(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|{_SUBJECT_ACTION_PREFIX}))",
                    part,
                    flags=re.IGNORECASE,
                )
                if segment.strip(" .")
            )
        expanded.extend(
            _sentence(part).rstrip(".")
            for part in _merge_compound_object_parts(_carry_subject_across_parts(split_parts))
            if part
        )
    return expanded


def _expand_semantic_action_conjunctions(values: list[str]) -> list[str]:
    expanded: list[str] = []
    for value in values:
        expanded.extend(_split_semantic_action_conjunction(value))
    return expanded


def _split_semantic_action_conjunction(value: str) -> list[str]:
    text = _compact_text(value).strip(" .")
    if not text:
        return []
    subject = leading_subject_prefix(text)
    action_text = strip_action_subject(text).strip(" .") if subject else text
    parts = [
        part.strip(" .")
        for part in re.split(
            rf"\s+and\s+(?=(?:{_SPLIT_ACTION_VERB_PATTERN})\b)",
            action_text,
            flags=re.IGNORECASE,
        )
        if part.strip(" .")
    ]
    if len(parts) <= 1 or not all(looks_like_action_clause(part) for part in parts):
        return [text]
    if not subject:
        return parts
    return [
        f"{subject} {_subject_action_clause(subject, part)}".strip(" .")
        for part in parts
    ]


def _merge_compound_object_parts(values: list[str]) -> list[str]:
    rows: list[str] = []
    for value in values:
        text = _compact_text(value).strip(" .")
        if not text:
            continue
        tail = re.sub(r"^(?:and|or)\s+", "", text, flags=re.IGNORECASE).strip(" .")
        if rows and starts_with_compound_noun_object(tail):
            rows[-1] = f"{rows[-1].rstrip(' .,;')} and {tail[:1].lower()}{tail[1:]}".strip()
            continue
        rows.append(text)
    return rows


def _modal_actor_capability_step(value: str) -> bool:
    actor, action = modal_actor_action_parts(_compact_text(value))
    return bool(actor and action)


def _carry_subject_across_parts(values: list[str]) -> list[str]:
    rows: list[str] = []
    current_subject = ""
    current_action = ""
    for value in values:
        text = _compact_text(value).strip(" .")
        if not text:
            continue
        subject = leading_subject_prefix(text)
        core, has_connector = _strip_leading_connector(text)
        if subject:
            current_subject = subject
            current_action = _leading_base_action(text)
        elif current_action in {"display", "show", "view"} and starts_with_result_object_modifier(core):
            rows.append(_result_object_step(core))
            continue
        elif current_action and (
            _looks_like_carried_object_fragment(core, has_connector=has_connector)
            or _looks_like_short_nonfinite_object_tail(core)
        ):
            if rows:
                rows[-1] = _append_carried_object_fragment(rows[-1], core, has_connector=has_connector)
                continue
            text = f"{current_action[:1].upper()}{current_action[1:]} {core}".strip(" .")
        elif current_subject and has_connector and _starts_with_action_word(core):
            text = f"{current_subject} {_subject_action_clause(current_subject, core)}"
        elif current_subject and _starts_with_action_word(text):
            text = f"{current_subject} {_subject_action_clause(current_subject, text)}"
        rows.append(text)
    return rows


def _result_object_step(value: str) -> str:
    return clean_markdown_sentence(value).rstrip(".")


def _append_carried_object_fragment(previous: str, fragment: str, *, has_connector: bool) -> str:
    head = _compact_text(previous).strip(" .")
    tail = _compact_text(fragment).strip(" .")
    if not head or not tail:
        return head or tail
    if has_connector:
        return f"{head} and {tail}".strip(" .")
    return f"{head}, {tail}".strip(" .")


def _subject_action_clause(subject: str, action: str) -> str:
    text = _compact_text(action).strip(" .")
    if not text:
        return ""
    first, separator, rest = text.partition(" ")
    verb = first.casefold().strip(".,:;")
    if separator and _subject_uses_singular_verb(subject):
        first = third_person_action_verb(verb)
    return f"{first}{separator}{rest}".strip(" .")


def _subject_uses_singular_verb(value: str) -> bool:
    words = [word.strip(".,:;()[]{}").casefold() for word in _compact_text(value).split() if word.strip(".,:;()[]{}")]
    if not words:
        return True
    if words[0] in {"a", "an", "one"}:
        return True
    head = words[-1]
    return not (head.endswith("s") and not head.endswith(("ss", "us", "is")))


def _leading_base_action(value: str) -> str:
    stripped = strip_action_subject(value).strip(" .")
    if not stripped or not looks_like_action_clause(stripped):
        return ""
    base = base_action_clause(stripped).strip(" .")
    first, _separator, _rest = base.partition(" ")
    return first.casefold().strip(".,:;")


def _strip_leading_connector(value: str) -> tuple[str, bool]:
    words = [word.strip(".,:;") for word in _compact_text(value).split() if word.strip(".,:;")]
    if words and words[0].casefold() in {"and", "or"}:
        return " ".join(words[1:]).strip(" ."), True
    return _compact_text(value).strip(" ."), False


def _looks_like_carried_object_fragment(value: str, *, has_connector: bool) -> bool:
    text = _compact_text(value).strip(" .")
    if len(label_terms(text)) < 2:
        return False
    if leading_subject_prefix(text):
        return False
    words = [word.strip(".,:;()[]{}").casefold() for word in text.split() if word.strip(".,:;()[]{}")]
    if words and words[-1] in _VISIBLE_RESULT_OBJECT_NOUNS and len(words) <= 5:
        return True
    if _looks_like_coordinated_object_tail(words):
        return True
    if not has_connector and _starts_with_subject_action_clause(text):
        return False
    if looks_like_finite_action(text):
        return False
    if has_connector and _connector_core_starts_action_clause(words):
        return False
    if looks_like_action_clause(text) and not has_connector:
        return False
    return True


def _looks_like_short_nonfinite_object_tail(value: str) -> bool:
    text = _compact_text(value).strip(" .")
    terms = label_terms(text)
    if len(terms) < 2 or len(terms) > 6:
        return False
    if leading_subject_prefix(text):
        return False
    if looks_like_finite_action(text):
        return False
    return True


def _looks_like_coordinated_object_tail(words: list[str]) -> bool:
    if len(words) < 3 or words[1] not in {"and", "or"}:
        return False
    return _starts_with_action_word(words[0]) and not _starts_with_action_word(words[2])


def _connector_core_starts_action_clause(words: list[str]) -> bool:
    if len(words) < 2:
        return False
    if words[0] in {"at", "after", "before", "during", "on", "when"}:
        for index in range(1, min(len(words), 5)):
            if looks_like_finite_action(" ".join(words[index:])):
                return True
    if words[0] in {"get", "gets", "read", "reads", "receive", "receives", "see", "sees", "show", "shows", "view", "views"}:
        return True
    return words[0].endswith("s") and words[1] in {
        "a",
        "an",
        "the",
        "this",
        "that",
        "one",
        "my",
        "your",
        "their",
        "his",
        "her",
        "our",
        "its",
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


def _starts_with_subject_action_clause(value: str) -> bool:
    return bool(re.match(rf"^{_SUBJECT_ACTION_PREFIX}", _compact_text(value), flags=re.IGNORECASE))


def _dedupe_steps(values: list[str]) -> list[str]:
    return dedupe_by_key(
        (text for value in values if (text := _compact_text(value).strip(" ."))),
        _step_dedupe_key,
    )


def _step_dedupe_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _sentence(value: str) -> str:
    return clean_markdown_sentence(value)


def _compact_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


__all__ = ["ACTION_VERB_PATTERN", "sequence_event_steps"]
