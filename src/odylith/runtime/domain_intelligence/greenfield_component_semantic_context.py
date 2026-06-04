"""Context phrase extraction for semantic Registry component contracts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term as _looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    ARTIFACT_CARRIER_TERMS as _ARTIFACT_CARRIER_TERMS,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms as _content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import looks_action_term as _looks_action_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    object_clause_focus as _object_clause_focus,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action as _strip_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import trim_phrase as _trim_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def clauses(value: str) -> list[str]:
    text = _clean(value)
    text = re.sub(r"\brationale\s*:\s*.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*owns\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brelevant\s+behavior\s*:\s*", "", text, flags=re.IGNORECASE)
    parts = re.split(r"[,;.]|\band\b|\bthen\b", text, flags=re.IGNORECASE)
    return unique_text(
        _trim_phrase(re.sub(r"^(?:and|or|the|a|an)\s+", "", part, flags=re.IGNORECASE))
        for part in parts
        if _trim_phrase(part)
    )


def context_object_phrases(
    value: str,
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> list[str]:
    anchors = set(label_terms[:5]) | set(description_terms[:8])
    anchors = expanded_context_anchors(anchors)
    rows: list[str] = []
    carry = 0
    carry_base: tuple[str, ...] = ()
    for clause in clauses(value):
        stripped_clause = _strip_action(_object_clause_focus(clause))
        stripped_clause = re.sub(
            r"\b(?:before|after|while|because|unless|without)\b.+$",
            "",
            stripped_clause,
            flags=re.IGNORECASE,
        )
        terms = _drop_actor_action_lead(_content_terms(stripped_clause or clause))
        if re.search(r"\balign(?:s|ed|ing)?\b", clause, flags=re.IGNORECASE) and re.search(
            r"\btimeline\b", clause, flags=re.IGNORECASE
        ):
            rows.append("aligned timeline")
        anchored = bool(terms and (not anchors or set(terms) & anchors))
        if anchored:
            carry = 3 if _opens_detail_list(clause) else 0
            carry_base = _context_carry_base(
                terms,
                label_terms=label_terms,
                description_terms=description_terms,
            )
        elif carry > 0:
            carry -= 1
        if not terms or not (anchored or carry > 0):
            continue
        if anchored:
            rows.append(" ".join(terms[:4]))
            if len(terms) > 4:
                rows.append(" ".join(terms[2:6]))
            continue
        if carry_base:
            detail_terms = [term for term in terms[:3] if term not in carry_base]
            if detail_terms:
                rows.append(" ".join((*carry_base, *detail_terms)))
        rows.append(" ".join(terms[:4]))
    return unique_text(rows)


def context_required_phrases(
    values: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
    limit: int = 5,
) -> list[str]:
    anchors = set(label_terms[:6]) | set(description_terms[:8])
    if not anchors:
        return []
    expanded = expanded_context_anchors(anchors)
    candidates: list[tuple[int, int, str]] = []
    for index, phrase in enumerate(values):
        terms = set(_content_terms(phrase))
        if not terms or not terms & expanded or not terms - anchors:
            continue
        lead = _content_terms(phrase)[:1]
        score = 0
        score += len(terms & anchors) * 10
        score += len(terms & expanded) * 4
        score += len(terms & _ARTIFACT_CARRIER_TERMS) * 8
        if 2 <= len(terms) <= 5:
            score += 4
        if lead and lead[0] in {"successful", "user"}:
            score -= 6
        candidates.append((-score, index, phrase))
    return unique_text(phrase for _score, _index, phrase in sorted(candidates)[:limit])


def needs_context_backfill(
    *,
    description: str,
    description_phrases: Sequence[str],
    context_required_phrases: Sequence[str],
) -> bool:
    if not _clean(description):
        return True
    broad_detail = re.compile(
        r"\b(?:central\s+object|details?|facts?|context|data|payload|information)\b",
        flags=re.IGNORECASE,
    )
    if broad_detail.search(_clean(description)) or any(broad_detail.search(_clean(phrase)) for phrase in description_phrases):
        return True
    local_terms = set(_content_terms(description))
    context_text = " ".join(context_required_phrases)
    if local_terms & {"measurement", "metric", "metrics", "value", "unit"} and re.search(
        r"\b(?:baseline|follow-up|followup|measurement|metric|value|unit|source)\b",
        context_text,
        flags=re.IGNORECASE,
    ):
        return True
    if any(set(_content_terms(phrase)) & _ARTIFACT_CARRIER_TERMS for phrase in description_phrases):
        return False
    return bool(len(description_phrases) <= 3 and context_required_phrases)


def context_anchor_compounds(value: str, *, anchor_terms: Sequence[str], limit: int = 8) -> list[str]:
    anchors = set(anchor_terms)
    if not anchors:
        return []
    rows: list[str] = []
    for clause in re.split(r"(?<=[.!?])\s+|[,;]", _clean(value)):
        clause = _object_clause_focus(clause)
        clause = re.sub(
            r"\b(?:before|after|while|because|unless|without)\b.+$",
            "",
            clause,
            flags=re.IGNORECASE,
        )
        terms = _drop_actor_action_lead(_content_terms(clause))
        if len(terms) < 2:
            continue
        for index, term in enumerate(terms):
            if term not in anchors:
                continue
            start = max(0, index - 2)
            phrase_terms = terms[start : index + 1]
            if len(phrase_terms) >= 2 and set(phrase_terms) - anchors:
                rows.append(" ".join(phrase_terms))
            if index + 1 < len(terms):
                phrase_terms = terms[index : min(len(terms), index + 3)]
                if len(phrase_terms) >= 2 and set(phrase_terms) - anchors:
                    rows.append(" ".join(phrase_terms))
            if len(rows) >= limit:
                return unique_text(rows)
    return unique_text(rows)


def expanded_context_anchors(anchors: set[str]) -> set[str]:
    expanded = set(anchors)
    if {"intake", "capture", "entry", "packet"} & anchors:
        expanded.update({"attach", "create", "draft", "import", "receive", "submit", "upload", "validate"})
    if {"follow", "list", "selected", "selection", "watch", "watchlist"} & anchors:
        expanded.update({"activity", "item", "selected", "signal", "source", "watchlist"})
    if {"status", "view", "dashboard", "timeline", "progress", "analytics"} & anchors:
        expanded.update(
            {
                "display",
                "entry",
                "event",
                "explain",
                "history",
                "measurement",
                "metric",
                "outcome",
                "point",
                "record",
                "show",
                "summary",
                "trend",
                "view",
            }
        )
    if {"metric", "measurement", "normalization", "generation", "signal", "quality"} & anchors:
        expanded.update({"aligned", "data", "reading", "readiness", "signal", "summary", "timeline", "trend", "value"})
    if {"quality", "review", "assessment", "check"} & anchors:
        expanded.update({"check", "evidence", "rule", "uncertainty", "validation"})
    if {"decision", "ledger", "journal", "rationale"} & anchors:
        expanded.update({"decide", "decision", "outcome", "rationale", "recheck", "release"})
    return expanded


def _opens_detail_list(value: str) -> bool:
    return bool(re.search(r"\b(?:for|including|includes|with)\b", _clean(value), flags=re.IGNORECASE))


def _context_carry_base(
    terms: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> tuple[str, ...]:
    anchors = set(label_terms[:5]) | set(description_terms[:8])
    if not terms:
        return ()
    for index, term in enumerate(terms):
        if term not in anchors:
            continue
        left = max(0, index - 1)
        right = min(len(terms), index + 2)
        candidate = tuple(terms[left:right])
        if len(candidate) >= 2:
            return candidate[:2]
        return (term,)
    return tuple(terms[:2])


def _drop_actor_action_lead(terms: Sequence[str]) -> list[str]:
    result = list(terms)
    while result and result[0] in _CONTEXT_METADATA_LEADS:
        result = result[1:]
    changed = True
    while changed:
        changed = False
        if len(result) >= 2 and _looks_actor_term(result[0]) and _looks_action_term(result[1]):
            result = result[2:]
            changed = True
            continue
        if result and _looks_action_term(result[0]) and result[0] not in _ARTIFACT_CARRIER_TERMS:
            result = result[1:]
            changed = True
    return result


_CONTEXT_METADATA_LEADS = frozenset(
    {
        "choice",
        "checkpoint",
        "command",
        "done_when",
        "impact",
        "must_capture",
        "operator_question",
        "path",
        "prompt",
        "recommended",
        "section",
        "use_when",
        "why_it_matter",
    }
)


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "").replace("(", " ").replace(")", " ")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "clauses",
    "context_anchor_compounds",
    "context_object_phrases",
    "context_required_phrases",
    "expanded_context_anchors",
    "needs_context_backfill",
]
