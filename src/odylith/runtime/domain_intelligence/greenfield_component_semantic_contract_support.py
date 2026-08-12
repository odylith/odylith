"""Support helpers for generated Registry semantic component contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.common.prose_grammar import strip_trailing_subject_modal
from odylith.runtime.domain_intelligence import greenfield_component_semantic_context as semantic_context
from odylith.runtime.domain_intelligence.greenfield_actor_terms import looks_actor_term
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import component_shell_artifact
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    status_only_artifact_fragment as _status_only_artifact_fragment,
)
from odylith.runtime.domain_intelligence.greenfield_component_owned_state import owned_state_phrases
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import ARTIFACT_CARRIER_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_terms import clean_artifact_phrase as _clean_artifact_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms as _content_terms
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import generic_contract_placeholder_fragments
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import normalize_action_splice_phrase
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import dedupe_adjacent_words
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
        "recordkeeping",
        "state",
        "states",
        "status",
        "the",
    }
)

_PROFILE_SOURCE_CONTEXT_TERMS = frozenset({"attachment", "document", "file", "packet", "upload"})
_PROTECTED_RELATION_TERMS = frozenset({"against", "for", "from", "into", "to", "using", "with"})

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


def component_contract_io_identity_repair(
    label: str,
    *,
    accepted_inputs: str,
    produced_outputs: str,
) -> tuple[str, str, str]:
    """Replace compressed I/O filler with a clean multi-term component identity."""

    identity = _component_contract_identity_focus(label)
    if not identity:
        return "", accepted_inputs, produced_outputs
    repair_inputs = bool(generic_contract_placeholder_fragments(accepted_inputs))
    repair_outputs = bool(generic_contract_placeholder_fragments(produced_outputs))
    if not repair_inputs and not repair_outputs:
        return "", accepted_inputs, produced_outputs
    identity_text = clean_artifact_text(identity).casefold()
    identity_words = visible_words(identity_text)
    output_artifact = (
        identity_text
        if identity_words and identity_words[-1].casefold() == "record"
        else f"{identity_text} record"
    )
    return (
        identity,
        f"{identity_text} request, authorized actor, validation context" if repair_inputs else accepted_inputs,
        output_artifact if repair_outputs else produced_outputs,
    )


def _component_contract_identity_focus(label: str) -> str:
    candidate = _clean_artifact_phrase(label) or clean_artifact_text(label)
    without_modal = strip_trailing_subject_modal(candidate)
    if without_modal != candidate:
        candidate = " ".join(ordered_domain_terms(without_modal)) or without_modal
    words = visible_words(candidate)
    while len(words) > 2 and component_shell_artifact(candidate):
        trimmed = _clean_artifact_phrase(" ".join(words[:-1]))
        if len(visible_words(trimmed)) < 2:
            break
        candidate = trimmed
        words = visible_words(candidate)
    while len(words) > 2 and words[-1].casefold() in {"coordination", "recordkeeping", "support"}:
        words = words[:-1]
        candidate = _clean_artifact_phrase(" ".join(words))
    words = visible_words(candidate)
    role_words = {"coordination", "recordkeeping", "support", "workflow"}
    return candidate if len(words) >= 2 and any(word.casefold() not in role_words for word in words) else ""


def title_identity_phrases(
    label_phrases: Sequence[str],
    summary_phrases: Sequence[str],
) -> tuple[str, ...]:
    """Keep label-local artifact identity out of generic component state."""

    summary = {phrase.casefold() for phrase in summary_phrases}
    candidates: list[str] = []
    for phrase in label_phrases:
        words = phrase.split()
        if len(words) < 2 or phrase.casefold() in summary:
            continue
        if words[-1] not in ARTIFACT_CARRIER_TERMS and len(_content_terms(phrase)) < 2:
            continue
        if component_shell_artifact(phrase) or _status_only_artifact_fragment(phrase):
            continue
        candidates.append(phrase)
    non_actor_candidates = [
        phrase
        for phrase in candidates
        if not any(looks_actor_term(word) for word in _content_terms(phrase))
    ]
    return tuple((non_actor_candidates or candidates)[:2])


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


def restore_protected_phrase_values(values: Sequence[str], protected_phrases: Sequence[str]) -> tuple[str, ...]:
    """Restore exact accepted surfaces before semantic phrase classification."""

    replacements = tuple(_protected_replacements(protected_phrases))
    return tuple(_restore_text_surface(str(value), replacements) for value in values)


def protected_projection_items(values: Sequence[str]) -> tuple[tuple[str, str], ...]:
    surfaces = tuple(_clean(value).casefold().strip(" .,;:") for value in values if _clean(value))
    rows: list[tuple[str, str]] = []
    for surface in surfaces:
        projection = _clean_artifact_phrase(surface)
        if _middle_modifier_projection(surface, projection):
            if projection in surfaces:
                rows.append((projection, projection))
            rows.append((projection, surface))
    return tuple(dict.fromkeys(rows))


def protected_projection_focus(items: Sequence[tuple[str, str]], output_values: Sequence[str]) -> str:
    fragments = unique_text(fragment for value in output_values for fragment in contract_list_fragments(value))
    modified = tuple((projection, surface) for projection, surface in items if projection != surface)
    surfaces = {surface.casefold(): surface for _projection, surface in modified}
    for fragment in fragments:
        if surface := surfaces.get(fragment.casefold()):
            return surface
    groups: dict[str, list[str]] = {}
    for projection, surface in modified:
        groups.setdefault(projection, []).append(surface)
    for projection, candidates in groups.items():
        if len(set(candidates)) == 1 and any(
            _fragment_projects_phrase(fragment, projection) for fragment in fragments
        ):
            return candidates[0]
    return ""


def restore_protected_contract_items(fields: Mapping[str, Any], protected_phrases: Sequence[str]) -> dict[str, Any]:
    groups: dict[str, list[str]] = {}
    for projection, surface in protected_projection_items(protected_phrases):
        groups.setdefault(projection, []).append(surface)
    restored = dict(fields)
    for key in ("owned_state", "accepted_inputs", "produced_outputs"):
        fragments = contract_list_fragments(restored.get(key))
        fragment_keys = {fragment.casefold() for fragment in fragments}
        restored[key] = ", ".join(
            unique_text(
                surface
                for fragment in fragments
                for surface in _restored_contract_fragment(fragment, groups, fragment_keys=fragment_keys)
            )
        )
    return restored


def _restored_contract_fragment(
    fragment: str,
    groups: Mapping[str, Sequence[str]],
    *,
    fragment_keys: set[str],
) -> Sequence[str]:
    key = fragment.casefold()
    if key in groups:
        return groups[key]
    prefix, separator, suffix = key.rpartition(" ")
    if separator and suffix in ARTIFACT_CARRIER_TERMS and prefix in groups:
        if prefix in fragment_keys and suffix in {"input", "result"}:
            return ()
        return tuple(f"{surface} {suffix}" for surface in groups[prefix])
    for projection, surfaces in groups.items():
        relation_tail = key.removeprefix(f"{projection} ") if key.startswith(f"{projection} ") else ""
        relation, _, _ = relation_tail.partition(" ")
        if relation in _PROTECTED_RELATION_TERMS:
            return tuple(f"{surface} {relation_tail}" for surface in surfaces)
    return (fragment,)


def _fragment_projects_phrase(fragment: str, projection: str) -> bool:
    key = fragment.casefold()
    projected = projection.casefold()
    if key == projected:
        return True
    tail = key.removeprefix(f"{projected} ") if key.startswith(f"{projected} ") else ""
    relation, _, _ = tail.partition(" ")
    return bool(tail and (tail in ARTIFACT_CARRIER_TERMS or relation in _PROTECTED_RELATION_TERMS))


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
    accepted_owned_state: Sequence[str] = (),
    field_limit: int = 12,
) -> dict[str, Any]:
    """Preserve profile custody obligations while keeping semantic fields authoritative."""

    normalized = dict(base_fields)
    for key in ("owned_state", "accepted_inputs", "produced_outputs"):
        base_value = normalized.get(key)
        profile_value = profile_fields.get(key)
        if key == "owned_state":
            base_value = ", ".join(
                owned_state_phrases(
                    contract_list_fragments(base_value),
                    accepted_phrases=accepted_owned_state,
                )
            )
            profile_value = ", ".join(owned_state_phrases(contract_list_fragments(profile_value)))
        normalized[key] = semantic_field_with_profile_supplements(
            base_value,
            profile_value,
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
        text = dedupe_adjacent_words(_clean_artifact_phrase(part))
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


def _middle_modifier_projection(surface: str, projection: str) -> bool:
    source_words = visible_words(surface)
    projected_words = visible_words(projection)
    if not (2 <= len(projected_words) < len(source_words)):
        return False
    if source_words[0].casefold() != projected_words[0].casefold():
        return False
    if source_words[-1].casefold() != projected_words[-1].casefold():
        return False
    projected = iter(word.casefold() for word in projected_words)
    expected = next(projected, "")
    for word in source_words:
        if word.casefold() == expected:
            expected = next(projected, "")
    return not expected


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
    "protected_projection_focus",
    "protected_projection_items",
    "result_like_phrase",
    "result_like_transition_phrase",
    "restore_protected_contract_items",
    "restore_protected_phrase_surface",
    "restore_protected_phrase_values",
    "sanitize_contract_fields",
    "semantic_field_with_profile_supplements",
    "with_required_local_proof_floor",
]
