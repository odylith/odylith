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
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import is_external_dependency_clause
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import is_source_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import is_discarded_evidence_clause
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    looks_like_trailing_operator_instruction,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import sentence_fragments
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import (
    without_confirmation_evidence_label,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import PROMPT_FIELD_NAMES
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import prompt_field_mapping
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import prompt_field_values
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
_READ_ONLY_SOURCE_RE = re.compile(
    r"\bread\s+only\s+from\s+(?:the\s+)?[^.!?;]{1,120}",
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
_DIRECT_OBLIGATION_ACTIONS = frozenset({"keep", "preserve", "retain", "store"})
_OBLIGATION_MODALS = frozenset({"depend", "depends", "must", "need", "needs", "required", "requires", "shall"})
_LABELED_CONSTRAINT_FIELDS = ("constraint", "constraints", "gate", "rule")
_LABELED_PROHIBITION_FIELDS = ("non-goal", "non-goals", "safety", "safety boundary")
_NEGATIVE_OBLIGATION_WORDS = frozenset(
    {"can't", "cannot", "forbidden", "never", "not", "prohibited", "without"}
)
_WORD_PUNCTUATION = str.maketrans({character: " " for character in ",.;:!?()[]{}\""})


def operational_constraint_phrases(value: Any) -> tuple[str, ...]:
    """Return source-stated obligations, sites, and times for the first release."""

    text = clean_text(value).strip(" .")
    structured_json = str(value or "").lstrip().startswith(("{", "[")) and bool(
        prompt_field_mapping(value)
    )
    matches: list[tuple[int, str]] = []
    if not structured_json:
        matches.extend(
            (match.start(), match.group("site")) for match in _SITE_IDENTIFIER_RE.finditer(text)
        )
        matches.extend(
            (match.start(), match.group("window")) for match in _TIME_WINDOW_RE.finditer(text)
        )
        matches.extend(
            (match.start(), match.group("deadline")) for match in _DEADLINE_RE.finditer(text)
        )
        matches.extend((match.start(), match.group(0)) for match in _READ_ONLY_SOURCE_RE.finditer(text))
        matches.extend(
            (max(0, text.casefold().find(constraint.casefold())), constraint)
            for constraint in _positive_source_obligations(text)
        )
    matches.extend(
        (max(0, text.casefold().find(constraint.casefold())), constraint)
        for constraint in _labeled_constraint_phrases(value)
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
    labeled_clauses = _labeled_prohibition_phrases(value)
    clauses: list[str] = list(labeled_clauses)
    clauses.extend(
        clause.strip(" .;:")
        for clause in re.split(r"(?<=[.!?])\s+|;\s*", text)
        if not (len(prompt_field_mapping(clause)) > 1 and "//" in clause)
        and not prompt_field_values(clause, names=_LABELED_PROHIBITION_FIELDS)
        and (_PROHIBITED_CLAUSE_RE.search(clause) or _leading_no_obligation(clause))
    )
    for match in _WITHOUT_PROHIBITION_RE.finditer(text):
        clause_start = max(text.rfind(mark, 0, match.start()) for mark in ".!?;") + 1
        containing_clause = text[clause_start : match.end()]
        phrase = match.group(0).strip(" .;:")
        if (
            _PROHIBITED_CLAUSE_RE.search(containing_clause)
            or _leading_no_obligation(containing_clause)
            or _OPERATOR_PROCESS_WITHOUT_RE.search(phrase)
        ):
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

    constraint = _canonical_constraint_text(value)
    captured = clean_text(text)
    if not constraint or not captured:
        return False
    expression = re.escape(constraint).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![A-Za-z0-9]){expression}(?![A-Za-z0-9])", captured, flags=re.IGNORECASE))


def operational_constraint_kind(value: Any) -> str:
    """Classify a constraint so an edit can replace only its stated category."""

    text = _canonical_constraint_text(value)
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
    return [text for row in rows if (text := _canonical_constraint_text(row))]


def _positive_source_obligations(value: str) -> tuple[str, ...]:
    obligations: list[str] = []
    for sentence in sentence_fragments(value):
        mapping = prompt_field_mapping(sentence)
        if any(field in mapping for field in PROMPT_FIELD_NAMES):
            continue
        text = clean_text(without_confirmation_evidence_label(sentence)).strip(" .")
        if (
            _is_non_product_context_sentence(text)
            or is_discarded_evidence_clause(text)
            or is_external_dependency_clause(text)
        ):
            continue
        units = atomic_claim_units(text)
        atomic_units = units[1:] if units and clean_text(units[0]) == text else units
        eligible_units = tuple(unit for unit in atomic_units if not _is_non_product_control_sentence(unit))
        child_obligations = tuple(unit for unit in eligible_units if is_source_obligation_clause(unit))
        child_path_actions = tuple(
            unit
            for unit in eligible_units
            if unit not in child_obligations and _is_path_action(unit) and not _is_nominal_clause(unit)
        )
        words = _constraint_words(text)
        direct_obligation = bool(words and words[0] in _DIRECT_OBLIGATION_ACTIONS)
        if (
            is_source_obligation_clause(text)
            and len(child_obligations) <= 1
            and (direct_obligation or not child_path_actions)
        ):
            obligations.append(text)
        else:
            obligations.extend(child_obligations)
    return _unique_constraints(obligations)


def _labeled_constraint_phrases(value: Any) -> tuple[str, ...]:
    rows: list[str] = []
    for field_value in prompt_field_values(value, names=_LABELED_CONSTRAINT_FIELDS):
        for index, fragment in enumerate(sentence_fragments(field_value)):
            if index == 0 or is_source_obligation_clause(fragment):
                rows.append(fragment)
    return tuple(rows)


def _labeled_prohibition_phrases(value: Any) -> tuple[str, ...]:
    rows: list[str] = []
    for field_value in prompt_field_values(value, names=_LABELED_PROHIBITION_FIELDS):
        rows.extend(
            fragment
            for fragment in sentence_fragments(field_value)
            if _PROHIBITED_CLAUSE_RE.search(fragment) or _leading_no_obligation(fragment)
        )
    return tuple(rows)


def _constraint_words(value: str) -> tuple[str, ...]:
    return tuple(
        word.strip("'")
        for word in value.casefold().translate(_WORD_PUNCTUATION).split()
        if word.strip("'")
    )


def _leading_no_obligation(value: str) -> bool:
    words = _constraint_words(value)
    conditional_supply = re.search(
        r"\b(?:is|are)\s+(?:provided|specified|supplied)\s+(?:after|before|unless|until|when)\b",
        value,
        flags=re.IGNORECASE,
    )
    return bool(words and words[0] == "no" and (set(words) & {"can", "cannot", "may", "must", "shall"} or conditional_supply))


def _is_nominal_clause(value: str) -> bool:
    words = _constraint_words(value)
    return bool(words and words[0] in {"a", "an", "the"})


def _is_path_action(value: str) -> bool:
    model = first_path_model(value)
    return bool(model.material_action or model.visible_outcome)


def _is_non_product_control_sentence(value: str) -> bool:
    return bool(
        _is_non_product_context_sentence(value)
        or looks_like_trailing_operator_instruction(value)
    )


def _is_non_product_context_sentence(value: str) -> bool:
    return bool(
        is_source_metadata_clause(value)
        or contains_word_sense_metadata_clause(value)
        or is_operator_review_lens_step(value)
    )


def _unique_constraints(values: list[str]) -> tuple[str, ...]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _canonical_constraint_text(value)
        key = cleaned.casefold()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        rows.append(cleaned)
    return tuple(rows[:12])


def _canonical_constraint_text(value: Any) -> str:
    """Remove path sequencing syntax that is not part of an operating condition."""

    text = clean_text(value).strip(" .")
    lowered = text.casefold()
    for prefix in ("and then ", "then "):
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip(" .")
    return text


__all__ = [
    "operational_constraint_is_present",
    "operational_constraint_kind",
    "operational_constraint_phrases",
    "operational_constraints_after_first_path_edit",
    "is_source_obligation_clause",
    "prohibited_product_phrases",
]
