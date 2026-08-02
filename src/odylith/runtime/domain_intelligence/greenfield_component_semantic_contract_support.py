"""Support helpers for generated Registry semantic component contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_component_semantic_context as semantic_context
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    status_only_artifact_fragment as _status_only_artifact_fragment,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase as _clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms as _content_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_action_splice_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words

_PROFILE_SUPPLEMENT_NOISE_TERMS = frozenset(
    {
        "and",
        "context",
        "history",
        "local",
        "metadata",
        "state",
        "states",
        "status",
        "the",
    }
)

_PROFILE_SOURCE_CONTEXT_TERMS = frozenset({"attachment", "document", "file", "packet", "upload"})

_PROFILE_MATERIAL_OBLIGATION_TERMS = frozenset(
    {
        "access",
        "attachment",
        "blocker",
        "blockers",
        "completeness",
        "complete",
        "missing",
        "provenance",
        "required",
        "restricted",
        "sensitive",
        "uploaded",
        "validation",
    }
)

_PROOF_OBLIGATION_TERMS = frozenset(
    {
        "access",
        "actor",
        "audit",
        "authorized",
        "blocked",
        "cannot",
        "consent",
        "hidden",
        "invalid",
        "missing",
        "mutate",
        "permission",
        "privacy",
        "reject",
        "rejected",
        "required",
        "role",
        "safety",
        "traceable",
        "unauthorized",
        "visible",
        "view",
    }
)


def sanitize_contract_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(value, list):
            sanitized[key] = [normalize_action_splice_phrase(str(item)) for item in value]
        elif isinstance(value, tuple):
            sanitized[key] = tuple(normalize_action_splice_phrase(str(item)) for item in value)
        elif isinstance(value, str):
            sanitized[key] = normalize_action_splice_phrase(value)
        else:
            sanitized[key] = value
    return sanitized


def restore_protected_phrase_surface(fields: Mapping[str, Any], protected_phrases: Sequence[str]) -> dict[str, Any]:
    replacements = tuple(_protected_replacements(protected_phrases))
    if not replacements:
        return dict(fields)
    restored: dict[str, Any] = {}
    for key, value in fields.items():
        if isinstance(value, list):
            restored[key] = [_restore_text_surface(str(item), replacements) for item in value]
        elif isinstance(value, tuple):
            restored[key] = tuple(_restore_text_surface(str(item), replacements) for item in value)
        elif isinstance(value, str):
            restored[key] = _restore_text_surface(value, replacements)
        else:
            restored[key] = value
    return restored


def prioritize_local_proof_rows(rows: Sequence[str]) -> list[str]:
    cleaned = tuple(dict.fromkeys(_clean(row).strip(" .") for row in rows if _clean(row)))
    core: list[str] = []
    obligations: list[str] = []
    handoff: list[str] = []
    supplemental: list[str] = []
    seen_core: set[str] = set()
    for row in cleaned:
        family = _proof_family(row)
        if family in {"successful", "blocked", "replay"}:
            if family in seen_core:
                supplemental.append(row)
                continue
            seen_core.add(family)
            core.append(row)
            continue
        if family == "obligation":
            obligations.append(row)
        elif family == "handoff":
            handoff.append(row)
        else:
            supplemental.append(row)
    return [f"{row.rstrip('.')}." for row in [*core, *obligations, *handoff, *supplemental]]


def merge_profile_contract_fields(
    base_fields: Mapping[str, Any],
    profile_fields: Mapping[str, Any],
    *,
    protected_phrases: Sequence[str] = (),
    field_limit: int = 12,
) -> dict[str, Any]:
    """Preserve profile custody obligations while keeping semantic fields authoritative."""

    normalized = dict(base_fields)
    for key in ("owned_state", "accepted_inputs", "produced_outputs"):
        normalized[key] = semantic_field_with_profile_supplements(
            normalized.get(key),
            profile_fields.get(key),
            limit=field_limit,
        )
    normalized["states_or_transitions"] = ", ".join(
        unique_text(contract_list_fragments(normalized.get("states_or_transitions"), profile_fields.get("states_or_transitions")))
    )
    normalized["local_proof"] = prioritize_local_proof_rows(
        unique_text([*text_values(normalized.get("local_proof")), *text_values(profile_fields.get("local_proof"))])
    )
    return restore_protected_phrase_surface(normalized, tuple(protected_phrases))


def semantic_field_with_profile_supplements(base_value: Any, profile_value: Any, *, limit: int = 12) -> str:
    base_fragments = list(contract_list_fragments(base_value))
    profile_fragments = list(contract_list_fragments(profile_value))
    if not base_fragments:
        return ", ".join(unique_text(profile_fragments)[:limit])
    selected_terms = _contract_content_terms(base_fragments)
    supplements: list[str] = []
    for fragment in profile_fragments:
        material_terms = set(visible_words(fragment.casefold())) - _PROFILE_SUPPLEMENT_NOISE_TERMS
        if not material_terms:
            continue
        if material_terms <= selected_terms:
            continue
        supplements.append(fragment)
        selected_terms.update(material_terms)
    if not supplements:
        return ", ".join(unique_text(base_fragments))
    supplement_limit = min(len(supplements), max(3, limit // 2))
    selected_supplements = supplements[:supplement_limit]
    return ", ".join(unique_text([*base_fragments, *selected_supplements]))


def with_required_local_proof_floor(contract: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    normalized = dict(contract)
    existing_rows = [_sentence_clause(item) for item in text_values(normalized.get("local_proof")) if _clean(item)]
    required = (
        (
            "successful path evidence",
            f"Successful path evidence for {label}: accepted input, visible result, persisted explanation, and reviewer context.",
        ),
        (
            "blocked input evidence",
            f"Blocked input evidence for {label}: missing or malformed input, stops before a trusted result, and recovery explanation.",
        ),
        (
            "replay evidence",
            f"Replay evidence for {label}: actor, input facts, status, explanation, and proof trail.",
        ),
    )
    proof_rows: list[str] = []
    for marker, row in required:
        existing = next((item for item in existing_rows if marker in item.casefold()), "")
        proof_rows.append(existing or _sentence_clause(row))
    proof_rows.extend(existing_rows)
    normalized["local_proof"] = list(unique_text(proof_rows))
    return normalized


def material_profile_obligations_survive(*, label: str, description: str, contract: Mapping[str, Any]) -> bool:
    source_text = f"{label} {description}".casefold()
    source_terms = set(visible_words(source_text))
    if not (source_terms & _PROFILE_SOURCE_CONTEXT_TERMS or "context handling" in source_text):
        return False
    contract_terms = set(
        visible_words(
            " ".join(
                text
                for key in ("owned_state", "accepted_inputs", "produced_outputs", "states_or_transitions")
                for text in text_values(contract.get(key))
            ).casefold()
        )
    )
    return len(contract_terms & _PROFILE_MATERIAL_OBLIGATION_TERMS) >= 3


def contract_list_fragments(*values: Any) -> tuple[str, ...]:
    rows: list[str] = []
    for value in values:
        for item in text_values(value, split_scalar=True, split_commas=True, strip_bullets=True):
            token = _clean(item).strip(" .,;:")
            if token:
                rows.append(token)
    return unique_text(rows)


def _contract_content_terms(fragments: Sequence[str]) -> set[str]:
    terms: set[str] = set()
    for fragment in fragments:
        terms.update(visible_words(str(fragment).casefold()))
    return terms


def result_like_phrase(value: str) -> str:
    result_terms = {
        "answer",
        "decision",
        "estimate",
        "evidence",
        "number",
        "outcome",
        "output",
        "recommendation",
        "result",
        "score",
        "suggestion",
        "summary",
    }
    best_score = 0
    best = ""
    for part in _clean(value).split(","):
        text = _dedupe_adjacent_words(_clean_artifact_phrase(part))
        if not text or _status_only_artifact_fragment(text):
            continue
        terms = set(_content_terms(text))
        score = len(terms & result_terms) * 10
        if "result" in terms:
            score += 20
        if "recommendation" in terms or "suggestion" in terms or "decision" in terms:
            score += 12
        if score > best_score:
            best_score = score
            best = text
    return best


def result_like_transition_phrase(value: str) -> str:
    result = result_like_phrase(value)
    pattern = (
        r"\s+(?:accepted|blocked|calculated|computed|converted|created|generated|logged|"
        r"received|returned|shown|updated|validated)\b$"
    )
    return re.sub(pattern, "", result, flags=re.IGNORECASE).strip(" .") if result else ""


def local_proof_boundary_rows(
    *,
    label: str,
    proof_boundary: str,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> list[str]:
    local_terms = set(label_terms) | set(description_terms)
    if not proof_boundary or not local_terms:
        return []
    rows: list[str] = []
    for clause in semantic_context.clauses(_proof_boundary_obligation_text(proof_boundary)):
        if not _proof_boundary_clause_belongs_to_component(clause, local_terms=local_terms):
            continue
        rows.append(f"Proof boundary evidence for {label}: {_sentence_clause(clause)}")
        if len(rows) >= 2:
            break
    return rows


def context_contract_terms(value: str, *, label_terms: Sequence[str], description_terms: Sequence[str]) -> tuple[str, ...]:
    context_terms = set(_content_terms(value))
    local_terms = set(label_terms) | set(description_terms)
    if context_terms & {"adjust", "adjusted", "adjusting", "adjustment"} and local_terms & {
        "decision",
        "plan",
        "rationale",
        "target",
    }:
        return ("adjustment",)
    return ()


def present_verb(value: str, *, singular: str, plural: str) -> str:
    words = [word.casefold() for word in re.findall(r"[a-z][a-z'-]*", _clean(value))]
    if not words:
        return singular
    head = next((word for word in reversed(words) if word not in {"context", "detail", "evidence", "state"}), words[-1])
    if head.endswith("s") and head not in {"status", "process"}:
        return plural
    if " and " in f" {_clean(value).casefold()} ":
        return plural
    return singular


def _proof_boundary_obligation_text(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(
        r"^(?:the\s+)?(?:first\s+)?release(?:\s+[A-Za-z0-9_.-]+)?\s+"
        r"(?:succeeds|works|passes|is\s+trusted|is\s+proven)\s+when\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip(" .")


def _proof_boundary_clause_belongs_to_component(clause: str, *, local_terms: set[str]) -> bool:
    terms = set(_content_terms(clause))
    if len(terms) < 3:
        return False
    obligation_overlap = bool(terms & _PROOF_OBLIGATION_TERMS)
    local_overlap = terms & local_terms
    return obligation_overlap and (len(local_overlap) >= 2 or (len(local_overlap) >= 1 and len(terms) <= 8))


def _sentence_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "local proof obligation remains reviewable."
    return f"{text.rstrip('.')}."


def _dedupe_adjacent_words(value: str) -> str:
    words = _clean(value).split()
    result: list[str] = []
    for word in words:
        current = word.casefold().strip(".,;:")
        previous = result[-1].casefold().strip(".,;:") if result else ""
        if current and current == previous:
            continue
        result.append(word)
    return " ".join(result).strip(" .,;")


def _clean(value: Any) -> str:
    return clean_artifact_text(value, split_parentheses=True)


def _protected_replacements(values: Sequence[str]) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for value in values:
        surface = _clean(value).casefold().strip(" .,;:")
        if "-" not in surface or not surface:
            continue
        normalized = surface.replace("-", " ")
        if normalized == surface or len(normalized.split()) < 2:
            continue
        rows.append((normalized, surface))
    return tuple(dict.fromkeys(rows))


def _restore_text_surface(value: str, replacements: Sequence[tuple[str, str]]) -> str:
    text = value
    for normalized, surface in replacements:
        text = _replace_casefold(text, normalized, surface)
    return text


def _replace_casefold(value: str, needle: str, replacement: str) -> str:
    if not needle:
        return value
    result: list[str] = []
    source = value
    lowered = source.casefold()
    search_from = 0
    while True:
        index = lowered.find(needle, search_from)
        if index < 0:
            result.append(source[search_from:])
            return "".join(result)
        result.append(source[search_from:index])
        matched = source[index : index + len(needle)]
        result.append(_replacement_for_surface_case(replacement, matched=matched))
        search_from = index + len(needle)


def _replacement_for_surface_case(replacement: str, *, matched: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9]*", matched)
    if len(words) < 2 or not all(word[:1].isupper() for word in words):
        return replacement
    return " ".join(
        "-".join(part[:1].upper() + part[1:] for part in token.split("-"))
        for token in replacement.split()
    )


def _proof_family(value: str) -> str:
    lowered = _clean(value).casefold()
    if lowered.startswith("successful path evidence"):
        return "successful"
    if lowered.startswith("blocked input evidence"):
        return "blocked"
    if lowered.startswith("replay evidence"):
        return "replay"
    if lowered.startswith("handoff evidence"):
        return "handoff"
    if lowered.startswith(("proof boundary evidence", "access evidence", "freshness evidence")):
        return "obligation"
    terms = set(_content_terms(lowered))
    return "obligation" if terms & _PROOF_OBLIGATION_TERMS else "supplemental"


__all__ = [
    "contract_list_fragments",
    "context_contract_terms",
    "local_proof_boundary_rows",
    "material_profile_obligations_survive",
    "merge_profile_contract_fields",
    "present_verb",
    "prioritize_local_proof_rows",
    "result_like_phrase",
    "result_like_transition_phrase",
    "restore_protected_phrase_surface",
    "sanitize_contract_fields",
    "semantic_field_with_profile_supplements",
    "with_required_local_proof_floor",
]
