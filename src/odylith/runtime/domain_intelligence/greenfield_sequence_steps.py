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
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import strip_action_subject
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_sentence
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


ACTION_VERB_PATTERN = action_verb_pattern()
_SPLIT_ACTION_VERB_PATTERN = action_verb_pattern(
    exclude={"keep", "keeps", "schedule", "schedules", "surface", "surfaces"}
)


def sequence_event_steps(
    first_path: str,
    *,
    semantic_model: Mapping[str, Any] | None = None,
    dedupe: bool = False,
) -> list[str]:
    """Return normalized first-path event steps for sequence-style Atlas diagrams."""

    steps = _drop_launcher_only_steps(_semantic_event_steps(semantic_model) or _first_path_steps(first_path))
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
    return _dedupe_steps(_expand_compound_steps(steps))


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
        return _dedupe_steps(_expand_compound_steps(semantic_steps))
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
                rf",\s+(?=(?:and\s+)?(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
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
                rf"\s+and\s+(?=(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
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
        parts = [
            part.strip(" .")
            for part in re.split(
                rf",\s+(?=(?:and\s+)?(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an|this|that)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
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
                    rf"\s+and\s+(?=(?:(?:{_SPLIT_ACTION_VERB_PATTERN})\b|(?:(?:the|a|an|this|that)\s+)?[A-Za-z][A-Za-z0-9/-]*\s+(?:{ACTION_VERB_PATTERN})\b))",
                    part,
                    flags=re.IGNORECASE,
                )
                if segment.strip(" .")
            )
        expanded.extend(_sentence(part).rstrip(".") for part in _carry_subject_across_parts(split_parts) if part)
    return expanded


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
        elif current_action and _looks_like_carried_object_fragment(core, has_connector=has_connector):
            text = f"{current_action[:1].upper()}{current_action[1:]} {core}".strip(" .")
        elif current_subject and has_connector and _starts_with_action_word(core):
            text = f"{current_subject} {_subject_action_clause(current_subject, core)}"
        elif current_subject and _starts_with_action_word(text):
            text = f"{current_subject} {_subject_action_clause(current_subject, text)}"
        rows.append(text)
    return rows


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
    if looks_like_finite_action(text):
        return False
    words = [word.strip(".,:;()[]{}").casefold() for word in text.split() if word.strip(".,:;()[]{}")]
    if has_connector and _connector_core_starts_action_clause(words):
        return False
    if looks_like_action_clause(text) and not has_connector:
        return False
    return True


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
