"""Context phrase extraction for semantic Registry component contracts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term as _looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    ARTIFACT_CARRIER_TERMS as _ARTIFACT_CARRIER_TERMS,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase as _clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms as _content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import looks_action_term as _looks_action_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    object_clause_focus as _object_clause_focus,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action as _strip_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import trim_phrase as _trim_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
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
        if _is_deferred_or_outside_clause(clause):
            continue
        truth_unit = _truth_unit_artifact(clause)
        if truth_unit:
            rows.append(truth_unit)
            continue
        data_source = re.search(r"\b(?P<head>[a-z0-9][a-z0-9 '-]{1,80}\s+data)\s+sources?\s+such\s+as\b", clause, flags=re.I)
        if data_source:
            source_phrase = f"{_trim_phrase(data_source.group('head'))} source".casefold()
            if set(_content_terms(source_phrase)) & anchors:
                rows.append(source_phrase)
                continue
        stripped_clause = _strip_action(_object_clause_focus(clause))
        stripped_clause = re.sub(
            r"\b(?:before|after|while|because|unless|without)\b.+$",
            "",
            stripped_clause,
            flags=re.IGNORECASE,
        )
        terms = _drop_actor_action_lead(_content_terms(stripped_clause or clause))
        terms = _preserve_missing_detail_carrier(terms, clause)
        if re.search(r"\balign(?:s|ed|ing)?\b", clause, flags=re.IGNORECASE) and re.search(
            r"\btimeline\b", clause, flags=re.IGNORECASE
        ):
            rows.append("aligned timeline")
            if re.search(r"\binterventions?\b", clause, flags=re.IGNORECASE):
                rows.append("aligns interventions")
            if re.search(r"\bmeasurements?\b", clause, flags=re.IGNORECASE):
                rows.append("aligns measurements")
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
    generated_boundary = re.compile(
        r"\b(?:required\s+inputs|blocked-case\s+evidence|handoff\s+boundaries|confirmed\s+first\s+path)\b",
        flags=re.IGNORECASE,
    )
    if generated_boundary.search(_clean(description)):
        return True
    local_terms = set(_content_terms(description))
    context_text = " ".join(context_required_phrases)
    if local_terms & {"measurement", "metric", "metrics", "value", "unit"} and re.search(
        r"\b(?:baseline|follow-up|followup|measurement|metric|value|unit|source)\b",
        context_text,
        flags=re.IGNORECASE,
    ):
        return True
    if description_phrases and len(local_terms) >= 5:
        return False
    if any(set(_content_terms(phrase)) & _ARTIFACT_CARRIER_TERMS for phrase in description_phrases):
        return False
    return bool(len(description_phrases) <= 3 and context_required_phrases)


def context_anchor_compounds(value: str, *, anchor_terms: Sequence[str], limit: int = 8) -> list[str]:
    anchors = set(anchor_terms)
    if not anchors:
        return []
    rows: list[str] = []
    for clause in re.split(r"(?<=[.!?])\s+|[,;]", _clean(value)):
        if _is_deferred_or_outside_clause(clause):
            continue
        truth_unit = _truth_unit_artifact(clause)
        if truth_unit:
            rows.append(truth_unit)
            continue
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


def owned_context_detail_phrases(
    context_phrases: Sequence[str],
    context_compound_phrases: Sequence[str],
    *,
    label_terms: Sequence[str],
) -> tuple[str, ...]:
    rows: list[str] = []
    label_term_set = set(label_terms)
    for phrase in (*context_phrases, *context_compound_phrases):
        terms = list(_content_terms(phrase))
        terms = _preserve_explicit_detail_carrier(terms, phrase)
        if len(terms) < 2:
            continue
        if set(terms) & {"ignore", "ignored"}:
            continue
        decision_detail = bool(
            label_term_set & {"decision", "journal", "ledger"}
            and "decision" in terms
            and terms[0] not in {"first", "local", "next", "product", "release", "review", "source", "validation"}
        )
        overlap_detail = bool(label_term_set & set(terms) and terms[0] not in {"first", "local", "next", "product", "release"})
        if (
            terms[0] not in {"accepted", "current", "incomplete", "missing", "recent", "required", "selected", "unavailable"}
            and not decision_detail
            and not overlap_detail
        ):
            continue
        if set(terms) & {"context", "summary"}:
            continue
        if not set(terms) & _ARTIFACT_CARRIER_TERMS and not overlap_detail:
            continue
        if terms[-1] in {"link", "links"} and len(terms) > 2:
            terms = terms[:-1]
        rows.append(" ".join(terms[:4]))
        if len(rows) >= 8:
            break
    return tuple(sorted(unique_text(rows), key=lambda value: _owned_context_detail_rank(value, label_term_set)))


def description_owned_phrases(value: str) -> tuple[str, ...]:
    rows: list[str] = []
    text = _clean(value)
    if not text:
        return ()
    for part in re.split(r"\s*,\s*|\s+\band\b\s+", text, flags=re.IGNORECASE):
        phrase = clean_artifact_text(
            re.sub(r"^(?:owns?|records?|keeps?|tracks?|stores?|captures?)\s+", "", part, flags=re.IGNORECASE)
        ).strip(" .")
        phrase = re.sub(r"^(?:and|or)\s+", "", phrase, flags=re.IGNORECASE).strip(" .")
        phrase = _clean_artifact_phrase(phrase) or phrase
        if not phrase:
            continue
        terms = list(_content_terms(phrase))
        has_carrier = _owned_phrase_has_carrier(phrase, terms)
        if (len(terms) < 2 and not has_carrier) or len(terms) > 5:
            continue
        if not has_carrier:
            continue
        rows.append(phrase.casefold())
    return tuple(unique_text(rows))


def generated_scaffold_subject(value: str, *, label: str) -> str:
    text = _clean(value)
    label_terms = set(_content_terms(label))
    patterns = (
        r"\bowns?\s+(?P<subject>.+?)\s+state,\s+required\s+inputs\b",
        r"\b(?P<subject>.+?)\s+state,\s+required\s+inputs\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        subject = _clean_artifact_phrase(match.group("subject")) or _clean(match.group("subject")).casefold()
        subject_terms = set(_content_terms(subject))
        if len(subject_terms) >= 2 and (not label_terms or subject_terms & label_terms):
            return f"owns {subject} state"
    return ""


def preserved_scaffold_material(value: str) -> tuple[str, ...]:
    return tuple(
        unique_text(
            phrase
            for clause in clauses(value)
            if (phrase := _clean_artifact_phrase(clause))
            and {"boundary", "boundaries"} & set(phrase.casefold().split())
        )
    )


def _is_deferred_or_outside_clause(value: str) -> bool:
    text = _clean(value).casefold()
    return bool(
        re.search(r"\b(?:outside|beyond|not\s+in|not\s+part\s+of)\s+(?:the\s+)?(?:first|initial|release|proof|scope|boundary)\b", text)
        or re.search(r"\b(?:deferred|out\s+of\s+scope|future\s+release|later\s+release)\b", text)
    )


def _preserve_explicit_detail_carrier(terms: Sequence[str], phrase: str) -> list[str]:
    result = list(terms)
    if set(result) & {"detail", "fact", "field", "information"}:
        return result
    if re.search(r"\b(?:details?|facts?|fields?|information)\b", _clean(phrase), flags=re.IGNORECASE):
        result.append("detail")
    return result


def _owned_context_detail_rank(value: str, label_terms: set[str]) -> tuple[int, int, str]:
    terms = set(_content_terms(value))
    if terms & {"blocked", "blocker", "incomplete", "missing", "unavailable"}:
        return (0, -len(terms & _ARTIFACT_CARRIER_TERMS), value)
    if label_terms & {"decision", "journal", "ledger"} and "decision" in terms and terms - label_terms:
        return (1, -len(terms & _ARTIFACT_CARRIER_TERMS), value)
    if terms & _ARTIFACT_CARRIER_TERMS:
        return (2, -len(terms & _ARTIFACT_CARRIER_TERMS), value)
    return (3, 0, value)


def _owned_phrase_has_carrier(phrase: str, terms: Sequence[str]) -> bool:
    return bool(
        set(terms) & _ARTIFACT_CARRIER_TERMS
        or re.search(r"\b(?:acknowledgement|acknowledgment|blockers?|events?|flags?|histories|history|notes?|states?)\b", phrase, flags=re.IGNORECASE)
    )


def _truth_unit_artifact(value: str) -> str:
    match = re.search(
        r"\b(?:core\s+)?(?:unit|source)\s+of\s+truth\s+is\s+(?:a|an|the)?\s*(?P<object>[^:.;,]+)",
        _clean(value),
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    terms = [
        term
        for term in _content_terms(match.group("object"))
        if term not in {"core", "truth", "unit", "source"}
    ]
    if not terms:
        return ""
    if terms[-1] in _ARTIFACT_CARRIER_TERMS:
        return " ".join(terms[:4])
    return f"{' '.join(terms[:3])} record"


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


def _preserve_missing_detail_carrier(terms: Sequence[str], clause: str) -> list[str]:
    result = list(terms)
    if "missing" not in result:
        return result
    if not re.search(r"\b(?:details?|facts?|fields?|information)\b", _clean(clause), flags=re.IGNORECASE):
        return result
    if set(result) & {"detail", "details", "fact", "facts", "field", "fields", "information"}:
        return result
    missing_index = result.index("missing")
    insert_at = min(len(result), missing_index + 3)
    return [*result[:insert_at], "detail", *result[insert_at:]]


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


def component_role_phrases(*, label: str, description: str) -> tuple[str, ...]:
    text = _clean(" ".join([label, description])).casefold()
    phrases: list[str] = []
    if re.search(r"\b(?:audit|evidence|ledger|log|proof|replay|reviewable|trace)\b", text):
        phrases.extend(["audit trail", "replay evidence", "decision ledger"])
    if re.search(r"\b(?:failure|blocked|invalid|missing|recovery)\b", text):
        phrases.append("failure reason ledger")
    if re.search(r"\b(?:guardrail|limit|rollout|release)\b", text):
        phrases.extend(["known-limit checkpoint", "recovery-condition ledger"])
    return tuple(unique_text(phrases))


def needs_source_evidence(
    *,
    label: str,
    description: str,
    proposal_context: str,
    action_terms: Sequence[str],
) -> bool:
    local_context = " ".join([label, description, proposal_context])
    if not re.search(r"\b(?:source|evidence|provenance|attachment|audit)\b", _clean(local_context), re.IGNORECASE):
        return False
    if re.search(r"\b(?:source|evidence|provenance|attachment|audit)\b", _clean(description), re.IGNORECASE):
        return True
    local_terms = set(_content_terms(" ".join([label, description])))
    record_actions = {"capture", "create", "edit", "import", "log", "record", "save", "store", "submit", "track"}
    return bool(record_actions & set(action_terms) or local_terms & {"entry", "history", "ledger", "log", "record", "store"})


_TRANSITION_CONTEXT_TERMS = frozenset(
    {
        "event",
        "events",
        "history",
        "lifecycle",
        "lifecycles",
        "progress",
        "stage",
        "stages",
        "status",
        "timeline",
        "timelines",
        "transition",
        "transitions",
        "workflow",
    }
)


def transition_context_text(
    value: str,
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> str:
    local_terms = set(label_terms) | set(description_terms)
    if not local_terms & _TRANSITION_CONTEXT_TERMS:
        return ""
    context_terms = set(_content_terms(value))
    if context_terms and not context_terms & expanded_context_anchors(local_terms):
        return ""
    return _clean(value)


def _clean(value: Any) -> str:
    return clean_artifact_text(value, split_parentheses=True)


__all__ = [
    "clauses",
    "component_role_phrases",
    "context_anchor_compounds",
    "context_object_phrases",
    "context_required_phrases",
    "description_owned_phrases",
    "expanded_context_anchors",
    "generated_scaffold_subject",
    "needs_context_backfill",
    "needs_source_evidence",
    "owned_context_detail_phrases",
    "preserved_scaffold_material",
    "transition_context_text",
]
