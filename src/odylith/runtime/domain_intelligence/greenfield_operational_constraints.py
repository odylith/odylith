"""Extract source-stated operating constraints for confirmed greenfield intent."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import atomic_claim_units
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import (
    contains_word_sense_metadata_clause,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_operator_review_lens_step
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import is_source_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    looks_like_trailing_operator_instruction,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import sentence_fragments
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


_SITE_IDENTIFIER_RE = re.compile(
    r"\b(?:at|for|from|in|on|through|to|within)\s+(?:the\s+)?(?P<site>"
    r"(?:bay|berth|dock|gate|pier|room|site|station|terminal|unit|ward|zone)\s+"
    r"(?:(?-i:[A-Z][A-Za-z0-9-]*)|[A-Za-z0-9-]*\d[A-Za-z0-9-]*)"
    r")\b",
    flags=re.IGNORECASE,
)
_TIME_WINDOW_RE = re.compile(
    r"\b(?:during|for)\s+(?:the\s+)?(?P<window>"
    r"(?:morning|afternoon|evening|night)\s+(?:[A-Za-z-]+\s+){0,2}"
    r"(?:call|handoff|run|shift|window)"
    r")\b",
    flags=re.IGNORECASE,
)
_DEADLINE_RE = re.compile(
    r"\b(?P<deadline>before\s+(?:noon|midnight|[0-9]{1,2}(?::[0-9]{2})?\s*(?:a\.m\.|p\.m\.|am|pm)))\b",
    flags=re.IGNORECASE,
)
_PROHIBITED_CLAUSE_RE = re.compile(
    r"\b(?:must\s+not|may\s+not|cannot|can't|do\s+not|never)\b",
    flags=re.IGNORECASE,
)
_WITHOUT_PROHIBITION_RE = re.compile(r"\bwithout\s+[^.;!?]+", flags=re.IGNORECASE)
_OPERATOR_PROCESS_WITHOUT_RE = re.compile(
    r"\bwithout\s+(?:asking|requesting|requiring)\b[^.;!?]*\b(?:confirm|confirmation)\b",
    flags=re.IGNORECASE,
)
_DIRECT_OBLIGATION_ACTIONS = frozenset({"keep", "preserve", "retain"})
_OBLIGATION_MODALS = frozenset({"must", "required", "requires", "shall"})
_NEGATIVE_OBLIGATION_WORDS = frozenset(
    {"can't", "cannot", "forbidden", "never", "not", "prohibited", "without"}
)
_WORD_PUNCTUATION = str.maketrans({character: " " for character in ",.;:!?()[]{}\""})


def operational_constraint_phrases(value: Any) -> tuple[str, ...]:
    """Return source-stated obligations, sites, and times for the first release."""

    text = clean_text(value).strip(" .")
    matches = [
        (match.start(), match.group("site")) for match in _SITE_IDENTIFIER_RE.finditer(text)
    ]
    matches.extend(
        (match.start(), match.group("window")) for match in _TIME_WINDOW_RE.finditer(text)
    )
    matches.extend(
        (match.start(), match.group("deadline")) for match in _DEADLINE_RE.finditer(text)
    )
    matches.extend(
        (max(0, text.casefold().find(constraint.casefold())), constraint)
        for constraint in _positive_source_obligations(text)
    )
    values = [value for _start, value in sorted(matches)]
    return _unique_constraints(values)


def is_source_obligation_clause(value: Any) -> bool:
    """Return whether a clause states policy rather than a user-path event."""

    words = _constraint_words(clean_text(value).strip(" ."))
    if not words or set(words) & _NEGATIVE_OBLIGATION_WORDS:
        return False
    if words[0] in _DIRECT_OBLIGATION_ACTIONS:
        return True
    modal_index = next(
        (index for index, word in enumerate(words) if word in _OBLIGATION_MODALS),
        -1,
    )
    if modal_index < 0:
        return False
    subject = " ".join(words[:modal_index])
    modal_action = words[modal_index + 1] if modal_index + 1 < len(words) else ""
    if modal_action in _DIRECT_OBLIGATION_ACTIONS:
        return True
    return not subject or not has_human_actor_signal(subject)


def prohibited_product_phrases(value: Any) -> tuple[str, ...]:
    """Return exact source clauses that prohibit product behavior."""

    text = clean_text(value).strip(" .")
    clauses: list[str] = [
        clause.strip(" .;:")
        for clause in re.split(r"(?<=[.!?])\s+|;\s*", text)
        if _PROHIBITED_CLAUSE_RE.search(clause)
    ]
    for match in _WITHOUT_PROHIBITION_RE.finditer(text):
        clause_start = max(text.rfind(mark, 0, match.start()) for mark in ".!?;") + 1
        containing_clause = text[clause_start : match.end()]
        phrase = match.group(0).strip(" .;:")
        if _PROHIBITED_CLAUSE_RE.search(containing_clause) or _OPERATOR_PROCESS_WITHOUT_RE.search(phrase):
            continue
        clauses.append(phrase)
    return _unique_constraints(clauses)


def operational_constraints_after_first_path_edit(
    existing: Any,
    edited_first_path: Any,
) -> tuple[str, ...]:
    """Retain unedited conditions while replacing categories named in a new first path."""

    replacements = operational_constraint_phrases(edited_first_path)
    replacement_kinds = {operational_constraint_kind(value) for value in replacements}
    retained = [
        value
        for value in _constraint_values(existing)
        if operational_constraint_kind(value) not in replacement_kinds
    ]
    return _unique_constraints([*replacements, *retained])


def operational_constraint_is_present(value: Any, text: Any) -> bool:
    """Match a normalized constraint as a complete phrase, never as a substring."""

    constraint = clean_text(value).strip(" .")
    captured = clean_text(text)
    if not constraint or not captured:
        return False
    expression = re.escape(constraint).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![A-Za-z0-9]){expression}(?![A-Za-z0-9])", captured, flags=re.IGNORECASE))


def operational_constraint_kind(value: Any) -> str:
    """Classify a constraint so an edit can replace only its stated category."""

    text = clean_text(value).strip(" .")
    if not text:
        return ""
    if re.fullmatch(
        r"(?:bay|berth|dock|gate|pier|room|site|station|terminal|unit|ward|zone)\s+"
        r"(?:(?-i:[A-Z][A-Za-z0-9-]*)|[A-Za-z0-9-]*\d[A-Za-z0-9-]*)",
        text,
        flags=re.IGNORECASE,
    ):
        return "site"
    if re.fullmatch(
        r"(?:morning|afternoon|evening|night)\s+(?:[A-Za-z-]+\s+){0,2}(?:call|handoff|run|shift|window)",
        text,
        flags=re.IGNORECASE,
    ):
        return "time_window"
    if _DEADLINE_RE.fullmatch(text):
        return "deadline"
    return text.casefold()


def _constraint_values(value: Any) -> list[str]:
    rows = value if isinstance(value, (list, tuple)) else (value,)
    return [clean_text(row).strip(" .") for row in rows if clean_text(row).strip(" .")]


def _positive_source_obligations(value: str) -> tuple[str, ...]:
    obligations: list[str] = []
    for sentence in sentence_fragments(value):
        text = clean_text(sentence).strip(" .")
        if _is_non_product_control_sentence(text):
            continue
        units = atomic_claim_units(text)
        children = units[1:]
        child_obligations = tuple(unit for unit in children if is_source_obligation_clause(unit))
        child_path_actions = tuple(
            unit
            for unit in children
            if unit not in child_obligations and _is_path_action(unit)
        )
        if (
            is_source_obligation_clause(text)
            and len(child_obligations) <= 1
            and not child_path_actions
        ):
            obligations.append(text)
        else:
            obligations.extend(child_obligations)
    return _unique_constraints(obligations)


def _constraint_words(value: str) -> tuple[str, ...]:
    return tuple(
        word.strip("'")
        for word in value.casefold().translate(_WORD_PUNCTUATION).split()
        if word.strip("'")
    )


def _is_path_action(value: str) -> bool:
    model = first_path_model(value)
    return bool(model.material_action or model.visible_outcome)


def _is_non_product_control_sentence(value: str) -> bool:
    return bool(
        is_source_metadata_clause(value)
        or contains_word_sense_metadata_clause(value)
        or is_operator_review_lens_step(value)
        or looks_like_trailing_operator_instruction(value)
    )


def _unique_constraints(values: list[str]) -> tuple[str, ...]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value).strip(" .")
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        rows.append(cleaned)
    return tuple(rows[:12])


__all__ = [
    "operational_constraint_is_present",
    "operational_constraint_kind",
    "operational_constraint_phrases",
    "operational_constraints_after_first_path_edit",
    "is_source_obligation_clause",
    "prohibited_product_phrases",
]
