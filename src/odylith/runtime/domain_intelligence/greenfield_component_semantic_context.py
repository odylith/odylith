"""Context phrase extraction for semantic Registry component contracts."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term as _looks_actor_term, word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_component_terms import ACTION_VERBS as _ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    ARTIFACT_CARRIER_TERMS as _ARTIFACT_CARRIER_TERMS,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import action_forms_pattern as _action_forms_pattern
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase as _clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms as _content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import finite_action_clause as _finite_action_clause
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    finite_action_object_clause as _finite_action_object_clause,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import looks_action_term as _looks_action_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    object_clause_focus as _object_clause_focus,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase_identity_terms as _phrase_identity_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action as _strip_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import trim_phrase as _trim_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import verb_forms_pattern as _verb_forms_pattern
from odylith.runtime.domain_intelligence.greenfield_component_owned_state import owned_state_noun_phrase
from odylith.runtime.domain_intelligence.greenfield_relative_clause_artifacts import normalize_relative_clause_artifacts
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import artifact_phrase_has_clause_shape
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text, unique_text, visible_words
from odylith.runtime.domain_intelligence.greenfield_transfer_phrases import transfer_object_phrase as _transfer_object_phrase


def clauses(value: str) -> list[str]:
    text = _clean(value)
    text = normalize_relative_clause_artifacts(text) or text
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
        if _is_reproducibility_proof_clause(clause):
            continue
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


def relation_phrases(value: str) -> list[str]:
    """Preserve a compact relation only within one parsed action clause."""

    rows: list[str] = []
    text = _clean(value)
    if not text:
        return rows
    parsed_clauses = clauses(text)
    for index, clause in enumerate(parsed_clauses):
        action_clause, owns_action = _finite_action_clause(clause)
        if not owns_action:
            continue
        body_words = action_clause.split()[1:]
        if len(body_words) < 4:
            continue
        lowered = [word.casefold().strip(".,;:") for word in body_words]
        if "to" not in lowered:
            continue
        to_index = lowered.index("to")
        if to_index < 1 or to_index >= len(body_words) - 1:
            continue
        body = _trim_phrase(" ".join(body_words))
        if index + 1 < len(parsed_clauses) and parsed_clauses[index + 1].casefold().startswith("related "):
            body = f"{body} and {parsed_clauses[index + 1]}"
        if 4 <= len(body_words) <= 14 and len(_content_terms(body)) >= 3:
            rows.append(body.casefold())
    return unique_text(rows)


def action_terms(value: str) -> list[str]:
    text = _clean(value).casefold()
    result: list[str] = []
    for verb in _ACTION_VERBS:
        if re.search(rf"\b(?:{_verb_forms_pattern(verb)})\b", text):
            result.append(verb)
    return result


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
    description_text = _clean(description)
    if not description_text:
        return True
    generated_boundary = re.compile(
        r"\b(?:required\s+inputs|blocked-case\s+evidence|handoff\s+boundaries|confirmed\s+first\s+path)\b",
        flags=re.IGNORECASE,
    )
    if generated_boundary.search(description_text):
        return True
    local_terms = set(_content_terms(description_text))
    context_text = " ".join(context_required_phrases)
    if local_terms & {"measurement", "metric", "metrics", "value", "unit"} and re.search(
        r"\b(?:baseline|follow-up|followup|measurement|metric|value|unit|source)\b",
        context_text,
        flags=re.IGNORECASE,
    ):
        return True
    if _is_underspecified_detail(description_text) or any(
        _is_underspecified_detail(phrase) for phrase in description_phrases
    ):
        return True
    has_material_local_detail = (
        len(description_phrases) >= 2
        and any(
            _has_visible_artifact_carrier(phrase) and bool(_content_terms(phrase))
            for phrase in description_phrases
        )
    )
    if has_material_local_detail:
        return False
    if re.search(r"\bcontext\b", description_text, flags=re.IGNORECASE) or any(
        re.search(r"\bcontext\b", _clean(phrase), flags=re.IGNORECASE) for phrase in description_phrases
    ):
        return True
    if any(_has_visible_artifact_carrier(phrase) for phrase in description_phrases):
        return False
    return bool(len(description_phrases) <= 3 and context_required_phrases)


def _is_underspecified_detail(value: str) -> bool:
    words = {word.casefold().strip(".,;:") for word in visible_words(_clean(value))}
    words -= {"a", "an", "captures", "keeps", "owns", "stores", "the", "tracks"}
    broad_terms = {
        "central",
        "data",
        "detail",
        "details",
        "fact",
        "facts",
        "information",
        "object",
        "payload",
    }
    material_carriers = _ARTIFACT_CARRIER_TERMS - broad_terms
    return bool(words & broad_terms) and not bool(words & material_carriers) and len(words) <= 3


def _has_visible_artifact_carrier(value: str) -> bool:
    return bool(
        {
            word.casefold().strip(".,;:")
            for word in re.findall(r"[A-Za-z][A-Za-z'-]*", _clean(value))
        }
        & _ARTIFACT_CARRIER_TERMS
    )


def context_anchor_compounds(value: str, *, anchor_terms: Sequence[str], limit: int = 8) -> list[str]:
    anchors = set(anchor_terms)
    if not anchors:
        return []
    rows: list[str] = []
    for clause in re.split(r"(?<=[.!?])\s+|[,;]", _clean(value)):
        if _is_reproducibility_proof_clause(clause):
            continue
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
    strong_label_terms = label_term_set - _WEAK_CONTEXT_ANCHOR_TERMS
    for phrase in (*context_phrases, *context_compound_phrases):
        terms = list(_content_terms(phrase))
        terms = _preserve_explicit_detail_carrier(terms, phrase)
        if len(terms) < 2:
            continue
        if set(terms) & {"ignore", "ignored"}:
            continue
        decision_detail = bool(
            strong_label_terms & {"decision", "journal", "ledger"}
            and "decision" in terms
            and terms[0] not in {"first", "local", "next", "product", "release", "review", "source", "validation"}
        )
        overlap_detail = bool(strong_label_terms & set(terms) and terms[0] not in {"first", "local", "next", "product", "release"})
        if (
            terms[0] not in {"accepted", "current", "incomplete", "missing", "recent", "required", "selected", "unavailable"}
            and not decision_detail
            and not overlap_detail
        ):
            continue
        if set(terms) & {"context", "summary"}:
            continue
        if not set(terms) & _ARTIFACT_CARRIER_TERMS:
            continue
        if terms[-1] in {"link", "links"} and len(terms) > 2:
            terms = terms[:-1]
        rows.append(" ".join(terms[:4]))
        if len(rows) >= 8:
            break
    return tuple(sorted(unique_text(rows), key=lambda value: _owned_context_detail_rank(value, strong_label_terms or label_term_set)))


_WEAK_CONTEXT_ANCHOR_TERMS = frozenset({"adapter", "data", "engine", "model", "service", "system", "view", "workspace"})


def description_owned_phrases(value: str, *, label: str = "") -> tuple[str, ...]:
    text = _clean(value)
    if not text:
        return ()
    scaffold_subject = text.partition(";")[0] if label and text.casefold().startswith(("own ", "owns ")) else ""
    scaffold_phrase = re.sub(r"^owns?\s+", "", scaffold_subject, flags=re.IGNORECASE).strip(" .")
    scaffold_state, (scaffold_action_text, scaffold_action) = scaffold_phrase.casefold().endswith(" state"), _finite_action_clause(scaffold_phrase)
    scaffold_terms, label_terms = set(_content_terms(scaffold_phrase)), set(_content_terms(label))
    scaffold_label_action = scaffold_action and scaffold_action_text.split()[0].casefold() in label_terms and scaffold_terms - {"state"} <= label_terms and not word_has_actor_role_signal(scaffold_phrase.split()[0])
    rows: list[str] = [scaffold_phrase.casefold()] if scaffold_state and ((not scaffold_action and owned_state_noun_phrase(scaffold_phrase)) or scaffold_label_action) and scaffold_terms & label_terms else []
    scaffold_terms = set(_content_terms(rows[0])) if rows else set()
    for part in clauses(text.partition(";")[2] if scaffold_state and scaffold_action else text):
        transfer_focus = _transfer_object_phrase(part)
        finite_focus, owns_action = _finite_action_object_clause(part)
        actor_prefix = part.rsplit(maxsplit=1)[0]
        if owns_action and not finite_focus and looks_like_actor_led_subject_prefix(actor_prefix, part):
            continue
        part = transfer_focus or (finite_focus if owns_action and finite_focus else _object_clause_focus(part))
        phrase = clean_artifact_text(
            re.sub(r"^(?:owns?|records?|keeps?|tracks?|stores?|captures?)\s+", "", part, flags=re.IGNORECASE)
        ).strip(" .")
        phrase = re.sub(r"^(?:and|or)\s+", "", phrase, flags=re.IGNORECASE).strip(" .")
        cleaned_phrase = _clean_artifact_phrase(phrase)
        if not cleaned_phrase and phrase.split() and _looks_action_word(phrase.split()[0]):
            continue
        phrase = cleaned_phrase or phrase
        if not phrase:
            continue
        if not owned_state_noun_phrase(phrase):
            continue
        terms = list(_content_terms(phrase))
        has_carrier = _owned_phrase_has_carrier(phrase, terms)
        if not has_carrier or len(terms) > 5 or (terms and scaffold_terms and set(terms) < scaffold_terms):
            continue
        rows.append(phrase.casefold())
    return tuple(unique_text(rows))


def description_compound_phrases(value: str) -> tuple[str, ...]:
    """Preserve compact noun phrases from accepted component descriptions."""
    rows: list[str] = []
    for sentence in re.split(r"[.!?]+", _clean(value)):
        carry_object = False
        for clause in clauses(sentence):
            transfer_focus = _transfer_object_phrase(clause)
            finite_focus, finite_action = _finite_action_object_clause(clause)
            owns_action = bool(transfer_focus or finite_action)
            if not owns_action and not carry_object:
                continue
            if owns_action and not (transfer_focus or finite_focus):
                carry_object = False
                continue
            focused_clause = transfer_focus or finite_focus
            focused = _strip_action(focused_clause) if owns_action else clause
            if not focused:
                carry_object = False
                continue
            focused = re.sub(
                r"\b(?:before|after|while|because|unless|without)\b.+$",
                "",
                focused,
                flags=re.IGNORECASE,
            )
            relation_head = re.split(
                r"\b(?:against|from|into|to|using|with)\b",
                focused,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            row_count = len(rows)
            rows.extend(_qualified_noun_phrases(focused))
            for candidate in unique_text([relation_head, *re.split(r"\s*,\s*|\s+\band\s+\s*", relation_head)]):
                phrase = _preserved_compound_phrase(candidate)
                if phrase:
                    rows.append(phrase)
            carry_object = (owns_action or carry_object) and len(rows) > row_count
    return tuple(unique_text(rows))
def _preserved_compound_phrase(value: str) -> str:
    text = clean_artifact_text(value, split_parentheses=True).casefold().strip(" .,;:")
    if not text:
        return ""
    text = re.sub(r"^(?:a|an|the|and|or)\s+", "", text, flags=re.IGNORECASE).strip(" .,;:")
    text = re.sub(r"^(?:owns?|records?|keeps?|tracks?|stores?|captures?|validates?|verifies?)\s+", "", text, flags=re.IGNORECASE)
    first_word = text.split(maxsplit=1)[0].casefold()
    if first_word in {"how", "that", "when", "where", "whether", "which", "who"}:
        return ""
    text = _transfer_object_phrase(text) or text
    text = re.sub(r"\s+", " ", text).strip(" .,;:")
    if not text:
        return ""
    words = text.split()
    if any(
        index > 1 and _looks_action_word(words[index - 1])
        for index, word in enumerate(words)
        if word in {"a", "an", "the"}
    ):
        return ""
    while words and _looks_action_word(words[0]) and not _protected_modifier_lead(words):
        words = words[1:]
    text = " ".join(words).strip(" .,;:")
    if not text:
        return ""
    terms = [term for term in _content_terms(text) if term]
    if re.fullmatch(r"ranked\s+(?:alternatives?|candidates?|options?)", text, flags=re.IGNORECASE):
        return text
    if len(terms) < 2 or len(terms) > 6:
        return ""
    if len(words) > 8:
        return ""
    if _is_deferred_or_outside_clause(text) or not owned_state_noun_phrase(text):
        return ""
    if _looks_action_term(terms[0]) and not _protected_modifier_lead(words) and not set(terms) & _ARTIFACT_CARRIER_TERMS:
        return ""
    if terms[-1] in {"context", "detail", "details", "information"} and len(terms) <= 2:
        return ""
    return text


def _looks_action_word(value: str) -> bool:
    token = value.casefold().strip(".,;:")
    if looks_like_finite_action_token(token):
        return True
    if _looks_action_term(token):
        return True
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and _looks_action_term(token[: -len(suffix)]):
            return True
    return False


def _protected_modifier_lead(words: Sequence[str]) -> bool:
    if len(words) < 2:
        return False
    lead = words[0].casefold().strip(".,;:")
    return lead in {"active", "candidate", "current", "ranked", "selected"} and bool(_content_terms(words[1]))


def _qualified_noun_phrases(value: str) -> list[str]:
    words = [word.casefold().strip(".,;:") for word in clean_artifact_text(value).split() if word.strip(".,;:")]
    rows: list[str] = []
    for index, word in enumerate(words[:-1]):
        if word not in {"active", "candidate", "current", "ranked", "selected"}:
            continue
        right = words[index + 1]
        if not _content_terms(right):
            continue
        rows.append(f"{word} {right}")
    return unique_text(rows)


def prefer_richer_relation_phrases(result: Sequence[str], values: Sequence[str]) -> list[str]:
    rows = list(result)
    for phrase in values:
        if not re.search(r"\b(?:related|linked|mapped)\b", phrase, flags=re.I):
            continue
        phrase_terms = _phrase_identity_terms(phrase)
        if not phrase_terms:
            continue
        subsets = [
            existing
            for existing in rows
            if existing != phrase and _phrase_identity_terms(existing) < phrase_terms
        ]
        if not subsets:
            continue
        rows = [existing for existing in rows if existing not in subsets and existing != phrase]
        rows.insert(0, phrase)
    return unique_text(rows)


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


def _is_reproducibility_proof_clause(value: str) -> bool:
    text = _clean(value).casefold()
    return bool(re.search(r"\b(?:can|must|should)\s+reproduc(?:e|es|ed|ing)\b", text))


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
    visible = {word.casefold() for word in visible_words(phrase)}
    return bool((set(terms) | visible) & _ARTIFACT_CARRIER_TERMS)


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
    if "ledger" in anchors and not (anchors & {"decision", "journal", "rationale"}):
        expanded.update({"audit", "evidence", "proof", "provenance", "replay", "review", "source"})
    if {"decision", "journal", "rationale"} & anchors:
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


def validation_gate_focus(value: str) -> str:
    """Return the governed subject from a generated ``enforces X as ... gate`` clause."""

    words = visible_words(_clean(value))
    lowered = [word.casefold() for word in words]
    if len(words) < 4 or not looks_like_finite_action_token(words[0]) or "gate" not in lowered:
        return ""
    gate_index = lowered.index("gate")
    as_index = next((index for index, word in enumerate(lowered[1:gate_index], start=1) if word == "as"), -1)
    focus_words = words[1:as_index] if as_index > 1 else []
    if not 1 <= len(_content_terms(" ".join(focus_words))) <= 5:
        return ""
    return _clean_artifact_phrase(" ".join(focus_words)) or " ".join(focus_words).casefold()


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
    "action_terms",
    "context_anchor_compounds",
    "context_object_phrases",
    "context_required_phrases",
    "description_compound_phrases",
    "description_owned_phrases",
    "expanded_context_anchors",
    "generated_scaffold_subject",
    "needs_context_backfill",
    "needs_source_evidence",
    "owned_context_detail_phrases",
    "prefer_richer_relation_phrases",
    "preserved_scaffold_material",
    "relation_phrases",
    "transition_context_text",
    "validation_gate_focus",
]
