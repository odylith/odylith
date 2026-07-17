"""Pure capability-summary operations for confirmed project briefs."""

from __future__ import annotations

import re

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text


def coverage_terms(value: str) -> set[str]:
    """Return normalized material terms used to compare brief clauses."""

    return {
        coverage_term(word)
        for word in compact_text(value).replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    }


def result_terms_covered(result: str, text: str) -> bool:
    """Return whether a result clause is already represented in a summary."""

    result_terms = coverage_terms(result)
    text_terms = coverage_terms(text)
    return bool(result_terms and result_terms <= text_terms)


def dedupe_action_rows(values: list[str]) -> list[str]:
    """Keep the first action row for each material-term identity."""

    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = compact_text(value).strip(" .")
        key = " ".join(sorted(coverage_terms(text)))
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


def prefer_more_complete_action_summary(primary: str, secondary: str) -> str:
    """Choose the action summary that carries more material terms."""

    first = compact_text(primary).strip(" .")
    second = compact_text(secondary).strip(" .")
    if not first:
        return second
    if not second:
        return first
    return first if len(coverage_terms(first)) >= len(coverage_terms(second)) else second


def dedupe_repeated_capability(value: str) -> str:
    """Remove repeated capability clauses while preserving readable join grammar."""

    text = compact_text(value).strip(" .")
    parts = text.split(" and ")
    for index in range(1, len(parts)):
        left = " and ".join(parts[:index]).strip()
        right = " and ".join(parts[index:]).strip()
        if left and left.casefold() == right.casefold():
            return left
    clauses = [part.strip(" ,") for part in re.split(r",\s+|\s+and\s+", text) if part.strip(" ,")]
    if len(clauses) <= 1:
        return text
    seen: set[str] = set()
    unique: list[str] = []
    for clause in clauses:
        key = capability_clause_key(clause)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(clause)
    if len(unique) != len(clauses):
        return join_capability_clauses(unique)
    return text


def capability_clause_key(value: str) -> str:
    """Return a stable material-term key for one capability clause."""

    tokens = [
        coverage_term(word)
        for word in compact_text(value).replace("-", " ").split()
        if len(word.strip(".,:;()[]{}")) >= 4
    ]
    return " ".join(tokens)


def join_capability_clauses(values: list[str]) -> str:
    """Join nonempty capability clauses as a compact English list."""

    rows = [row.strip(" ,") for row in values if row.strip(" ,")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def coverage_term(value: str) -> str:
    """Normalize the proof family without collapsing other literal terms."""

    token = value.strip(".,:;()[]{}").casefold()
    if token in {"prove", "proves", "proved", "proven", "proof"}:
        return "proof"
    return token


__all__ = [
    "capability_clause_key",
    "coverage_term",
    "coverage_terms",
    "dedupe_action_rows",
    "dedupe_repeated_capability",
    "join_capability_clauses",
    "prefer_more_complete_action_summary",
    "result_terms_covered",
]
