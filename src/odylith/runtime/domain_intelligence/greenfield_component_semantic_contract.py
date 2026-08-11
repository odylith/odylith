"""Derive component-local greenfield contracts from accepted product text.

This module intentionally avoids a baked catalog of product domains. It
extracts action/object language from the accepted intent and component
description, then renders a generic ownership contract around state, inputs,
outputs, blockers, handoff, and proof.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import strip_trailing_subject_modal

from odylith.runtime.domain_intelligence import greenfield_component_semantic_context as semantic_context
from odylith.runtime.domain_intelligence import greenfield_component_owned_state as owned_state_semantics
from odylith.runtime.domain_intelligence import greenfield_component_semantic_contract_support as contract_support
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    accepted_inputs_text as _accepted_inputs_text,
    component_shell_artifact as _component_shell_artifact,
    component_kind_echo_safe_phrase as _component_kind_echo_safe_phrase,
    contract_focus as _contract_focus,
    contract_list_text as _contract_list_text,
    label_compound_rank as _label_compound_rank,
    noun_slot_artifact_phrase as _noun_slot_artifact_phrase,
    outside_boundary as _outside_boundary,
    produced_outputs_text as _produced_outputs_text,
    proof_rows as _proof_rows,
    state_transition_text as _state_transition_text,
    status_only_artifact_fragment as _status_only_artifact_fragment,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms as _label_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    ARTIFACT_CARRIER_TERMS as _ARTIFACT_CARRIER_TERMS,
    GENERIC_TERMS as _GENERIC_TERMS,
    action_object_artifact_phrases as _action_object_artifact_phrases,
    clean_artifact_phrase as _clean_artifact_phrase,
    clean_artifact_phrases as _clean_artifact_phrases,
    content_terms as _content_terms,
    descriptor_anchor_phrases as _descriptor_anchor_phrases,
    drop_subsumed_singletons as _drop_subsumed_singletons,
    label_object_base as _label_object_base,
    local_terms as _local_terms,
    looks_action_term as _looks_action_term,
    material_contract_phrase as _material_contract_phrase,
    object_clause_focus as _object_clause_focus,
    phrase_identity_terms as _phrase_identity_terms,
    phrase as _phrase,
    strip_action as _strip_action,
    trim_phrase as _trim_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_component_outputs import (
    produced_output_artifact_phrases as _produced_output_artifact_phrases,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import (
    literal_label_terms as _literal_label_terms,
)
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import (
    artifact_phrase_has_clause_shape as _artifact_phrase_has_clause_shape,
    singularize_last_word,
)
from odylith.runtime.domain_intelligence.greenfield_relative_clause_artifacts import normalize_relative_clause_artifacts
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


@dataclass(frozen=True)
class SemanticComponentContract:
    """Component-local contract fields derived from accepted intent text."""

    fields: Mapping[str, Any]
    confidence: int
    local_terms: tuple[str, ...]


def derive_component_semantic_contract(
    row: Mapping[str, Any],
    *,
    proposal: Mapping[str, Any],
    sibling: Mapping[str, Any] | None,
    previous_label: str,
    next_label: str,
    state_label: str,
) -> SemanticComponentContract:
    """Derive a deterministic, product-local component contract."""

    label = _label(row)
    description = _description(row)
    gate_focus = semantic_context.validation_gate_focus(description)
    if gate_focus:
        return _validation_gate_contract(
            label=label,
            focus=gate_focus,
            previous_label=previous_label,
            next_label=next_label,
            state_label=state_label,
        )
    proposal_context = _proposal_context(proposal)
    proof_boundary = _proof_boundary_text(proposal)
    local_text = " ".join(text for text in (label, description) if text)
    clauses = semantic_context.clauses(description or label)
    action_terms = semantic_context.action_terms(" ".join(text for text in (label, description) if text)) or semantic_context.action_terms(local_text)
    relation_phrases = semantic_context.relation_phrases(description)
    protected_description_phrases = semantic_context.description_compound_phrases(description)
    protected_items = contract_support.protected_projection_items(protected_description_phrases)
    output_description_phrases = _produced_output_artifact_phrases(description)
    description_phrases = _clean_artifact_phrases(
        [
            *_object_phrases(clauses, fallback=label),
            *_action_object_artifact_phrases(description),
            *output_description_phrases,
            *_descriptor_anchor_phrases(label, description),
        ]
    )
    description_phrases = unique_text(
        [*relation_phrases, *output_description_phrases, *protected_description_phrases, *description_phrases]
    )
    label_terms = _content_terms(label)
    description_terms = _content_terms(description)
    context_terms = contract_support.context_contract_terms(
        proposal_context,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    contract_terms = (*label_terms, *description_terms, *context_terms)
    context_phrases = semantic_context.context_object_phrases(
        proposal_context,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    label_phrases = _label_compound_phrases(label)
    bridge_phrases = _bridge_phrases(label, description)
    context_required_phrases = semantic_context.context_required_phrases(
        context_phrases,
        label_terms=label_terms,
        description_terms=description_terms,
        limit=14,
    )
    context_identity_phrases = _context_identity_phrases(
        context_required_phrases,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    context_compound_phrases = semantic_context.context_anchor_compounds(
        proposal_context,
        anchor_terms=unique_text([*label_terms, *description_terms]),
    )
    local_phrases = [*description_phrases, *label_phrases, *bridge_phrases]
    needs_context_backfill = semantic_context.needs_context_backfill(
        description=description,
        description_phrases=description_phrases,
        context_required_phrases=context_required_phrases,
    )
    context_backfill = [*context_phrases[:5], *context_compound_phrases[:3]] if needs_context_backfill else []
    object_phrases = _clean_artifact_phrases([*local_phrases, *context_identity_phrases, *context_backfill])
    object_phrases = unique_text([*relation_phrases, *object_phrases])
    object_phrases = _dedupe_phrase_subsets(object_phrases)
    object_phrases = _prioritize_object_phrases(
        object_phrases,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    if description:
        required_seed = [
            *description_phrases[:10],
            *protected_description_phrases[:8],
            *context_identity_phrases[:4],
            *([] if not needs_context_backfill else context_phrases[:4]),
            *([] if not needs_context_backfill else context_required_phrases[:8]),
            *([] if not needs_context_backfill else context_phrases[:3]),
            *label_phrases[:3],
            *protected_description_phrases[:6],
            *context_identity_phrases[:4],
            *bridge_phrases[:2],
            *([] if not needs_context_backfill else context_compound_phrases[:4]),
        ]
    else:
        required_seed = [
            *label_phrases[:3],
            *bridge_phrases[:2],
            *context_required_phrases[:3],
            *context_compound_phrases[:3],
        ]
    summary_phrases = _summary_object_phrases(
        object_phrases,
        required_phrases=unique_text(required_seed),
        label_terms=label_terms,
        description_terms=description_terms,
        limit=10,
    )
    summary_phrases = _preserve_summary_phrases(
        summary_phrases,
        [*output_description_phrases, *protected_description_phrases, *context_identity_phrases],
        label_terms=label_terms,
        description_terms=description_terms,
        limit=10,
    )
    local_terms = _local_terms(label, description, proposal_context, object_phrases)
    object_list = _phrase(summary_phrases) or _phrase(local_terms[:10]) or _clean(label).casefold()
    focus_list = object_list
    critical = _clean_artifact_phrase(summary_phrases[0]) if summary_phrases else ""
    critical = critical or _phrase(local_terms[:3]) or "local state"
    input_focus = _contract_focus(
        object_list=focus_list,
        action_terms=action_terms,
        fallback=previous_label or "accepted upstream state",
        role="input",
        contract_terms=contract_terms,
    )
    output_focus = _contract_focus(
        object_list=focus_list,
        action_terms=action_terms,
        fallback=next_label or "downstream state",
        role="output",
        contract_terms=contract_terms,
    )
    accepted_inputs = _accepted_inputs_text(input_focus)
    produced_outputs = _produced_outputs_text(output_focus)
    contract_identity, accepted_inputs, produced_outputs = contract_support.component_contract_io_identity_repair(
        label,
        accepted_inputs=accepted_inputs,
        produced_outputs=produced_outputs,
    )
    if contract_identity:
        focus_list = contract_identity
        critical = contract_identity
        input_focus = f"{contract_identity} request"
        output_focus = f"{contract_identity} record"
    protected_focus = contract_support.protected_projection_focus(
        protected_items,
        [*output_description_phrases, output_focus, produced_outputs],
    )
    transition_context = semantic_context.transition_context_text(
        proposal_context,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    states = _state_transition_text(
        action_terms=action_terms,
        object_phrases=object_phrases,
        context_text=transition_context,
        anchor_terms=unique_text([*label_terms, *description_terms]),
    )
    transition_result = contract_support.result_like_transition_phrase(states)
    critical = _component_kind_echo_safe_phrase(
        label=label,
        phrase=transition_result or contract_support.result_like_phrase(output_focus) or critical,
    )
    sibling_label = _label(sibling) if isinstance(sibling, Mapping) else ""
    handoff_label = next_label or "release review"
    handoff_focus = _sibling_focus(sibling) if next_label and sibling_label == next_label else ""
    proof = _proof_rows(
        label=label,
        object_list=object_list,
        critical=critical,
        input_focus=input_focus,
        output_focus=output_focus,
        sibling_label=handoff_label,
        sibling_focus=handoff_focus,
        preferred_focus=protected_focus,
    )
    proof = unique_text(
        [
            *proof,
            *contract_support.local_proof_boundary_rows(
                label=label,
                proof_boundary=proof_boundary,
                label_terms=label_terms,
                description_terms=description_terms,
            ),
        ]
    )
    evidence_phrases = ("source evidence",) if semantic_context.needs_source_evidence(
        label=label,
        description=description,
        proposal_context=proposal_context,
        action_terms=action_terms,
    ) else ()
    owned_context_phrases = semantic_context.owned_context_detail_phrases(
        context_phrases,
        context_compound_phrases,
        label_terms=label_terms,
    )
    description_owned_phrases = semantic_context.description_owned_phrases(description)
    description_identities = tuple(map(_phrase_identity_terms, (*description_owned_phrases, *summary_phrases)))
    owned_context_phrases = tuple(
        phrase
        for phrase in owned_context_phrases
        if not any(_phrase_identity_terms(phrase) <= identity for identity in description_identities)
    )
    lifecycle_identity_phrases = owned_state_semantics.lifecycle_identity_phrases(description_owned_phrases)
    preserved_material_phrases = semantic_context.preserved_scaffold_material(description)
    owned_summary_phrases = summary_phrases[:7]
    title_identity_phrases = contract_support.title_identity_phrases(label_phrases, owned_summary_phrases)
    owned_seed = (
        (
            *title_identity_phrases,
            *([contract_identity] if contract_identity else []),
            *description_owned_phrases[:5],
            *lifecycle_identity_phrases,
            *protected_description_phrases[:6],
            *context_identity_phrases[:4],
            *owned_summary_phrases,
            *preserved_material_phrases[:3],
            *owned_context_phrases[:2],
            *evidence_phrases,
            "blocker state",
            "next-step context",
        )
        if summary_phrases
        else (f"{_clean(label).casefold()} state", *label_phrases[:1], *evidence_phrases, "blocker state")
    )
    owned_seed = owned_state_semantics.owned_state_phrases(owned_seed)
    owned_seed = tuple(_drop_subsumed_singletons(owned_seed))
    failure_cause = (
        "calculated from the wrong inputs"
        if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "score"))
        else "built from the wrong inputs"
    )
    critical_noun = protected_focus or _noun_slot_artifact_phrase(critical)
    fields = contract_support.sanitize_contract_fields(
        {
            "owned_state": _contract_list_text(*owned_seed),
            "accepted_inputs": accepted_inputs,
            "produced_outputs": produced_outputs,
            "states_or_transitions": states,
            "outside_boundary": _outside_boundary(sibling_focus=handoff_focus),
            "local_proof": proof,
            "upstream_truth": _upstream_truth(previous_label),
            "downstream_consumers": next_label or "release review",
            "unique_failure": (
                f"{label} can mislead users if {critical_noun} {contract_support.present_verb(critical_noun, singular='is', plural='are')} missing, stale, {failure_cause}, "
                "or shown without enough explanation to recover"
            ),
        }
    )
    fields = contract_support.restore_protected_contract_items(fields, protected_description_phrases)
    fields = contract_support.restore_protected_phrase_surface(fields, protected_description_phrases)
    confidence = len(object_phrases) * 3 + len(action_terms) * 2 + min(len(local_terms), 8)
    return SemanticComponentContract(fields=fields, confidence=confidence, local_terms=tuple(local_terms))


def _validation_gate_contract(
    *, label: str, focus: str, previous_label: str, next_label: str, state_label: str
) -> SemanticComponentContract:
    result = f"{singularize_last_word(focus)} result"
    state = _clean(state_label).casefold() or "accepted state"
    fields = contract_support.sanitize_contract_fields(
        {
            "owned_state": f"{result}, blocked reason, validation evidence, release status",
            "accepted_inputs": f"{state}, {focus} evidence, release criteria, prior release status, authorized actor",
            "produced_outputs": f"{result}, allowed or blocked release decision, validation evidence, release status",
            "states_or_transitions": "pending, evaluated, blocked, ready-for-release",
            "outside_boundary": f"upstream source truth; changes to {state}; final release approval and downstream delivery",
            "local_proof": [
                f"Successful path evidence for {label}: accepted {state} passes {focus} and records validation evidence before release.",
                f"Blocked input evidence for {label}: missing or failed {focus} keeps {state} blocked and explains the recovery action.",
                f"Replay evidence for {label}: {result}, source evidence, actor, criteria, and release status reproduce the gate decision.",
            ],
            "upstream_truth": previous_label or f"accepted {state} input",
            "downstream_consumers": next_label or "release review",
            "unique_failure": f"{label} can release {state} incorrectly when {focus} evidence is missing or stale, or when a blocked result is hidden.",
        }
    )
    local_terms = tuple(_content_terms(f"{focus} {result} blocked reason validation evidence release status"))
    return SemanticComponentContract(fields=fields, confidence=40, local_terms=local_terms)


def _label(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or "component"


def _description(row: Mapping[str, Any]) -> str:
    label = _label(row)
    for key in ("source_system_description", "responsibility", "boundary"):
        text = _clean(row.get(key))
        if not text:
            continue
        if _looks_generated_scaffold(text):
            scaffold_subject = semantic_context.generated_scaffold_subject(text, label=label)
            if scaffold_subject:
                return "; ".join(unique_text([scaffold_subject, *semantic_context.preserved_scaffold_material(text)]))
            continue
        return _scrub_description_scaffold(text)
    return ""


def _scrub_description_scaffold(value: str) -> str:
    text = _clean(value)
    if text.casefold().startswith("first-path action is "):
        _action, separator, remainder = text.partition("; ")
        text = remainder if separator else ""
    else:
        marker_index = text.casefold().rfind("; first-path action is ")
        if marker_index >= 0:
            text = text[:marker_index].rstrip()
    text = re.sub(r"\bRelevant\s+behavior\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"(?:^|(?<=[.;])\s*)Rationale\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^Rationale$", "", text, flags=re.IGNORECASE).strip()
    return text.rstrip(" .")


def _looks_generated_scaffold(value: str) -> bool:
    text = _clean(value).casefold()
    return bool(
        re.search(
            r"\b(?:owns\s+relevant\s+behavior|planned\s+from|tracked\s+from\s+user-stated|"
            r"component\s+planning\s+record|runtime\s+ownership\s+boundary|source-backed\s+claim)\b",
            text,
        )
        or ("required inputs" in text and "blocked-case evidence links" in text)
        or ("accepted inputs" in text and "local refusal evidence" in text)
        or ("adjacent product decisions stay outside" in text)
        or ("validation evidence" in text and "local handoff decisions" in text)
        or ("original input facts stays outside" in text)
        or ("preserves reviewable evidence" in text and "explains missing or stale inputs" in text)
        or ("handoff boundaries for the confirmed first path" in text)
        or ("failure avoided:" in text)
        or ("transitions" in text and "refusals stay as separate contract fields" in text)
    )


def _proposal_context(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    semantic_model = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    ontology = semantic_model.get("domain_ontology") if isinstance(semantic_model.get("domain_ontology"), Mapping) else {}
    values = [
        intent.get("first_path"),
        intent.get("state_object"),
        intent.get("product_story"),
        intent.get("external_systems"),
        proposal.get("external_systems"),
        *ontology.values(),
    ]
    return ". ".join(_clean(value).strip(" .") for value in values if _clean(value))


def _proof_boundary_text(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    semantic_model = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    ontology = semantic_model.get("domain_ontology") if isinstance(semantic_model.get("domain_ontology"), Mapping) else {}
    return ". ".join(
        _clean(value).strip(" .")
        for value in (
            proposal.get("proof_boundary"),
            intent.get("proof_boundary"),
            ontology.get("proof_boundary") if isinstance(ontology, Mapping) else "",
        )
        if _clean(value)
    )


def _object_phrases(clauses: Sequence[str], *, fallback: str) -> list[str]:
    rows: list[str] = []
    for clause in clauses:
        clause = normalize_relative_clause_artifacts(clause) or clause
        if _artifact_phrase_has_clause_shape(clause):
            continue
        cleaned_boundary = _clean_artifact_phrase(clause)
        if cleaned_boundary and {"boundary", "boundaries"} & set(cleaned_boundary.casefold().split()):
            rows.append(cleaned_boundary.casefold())
        align_match = re.search(
            r"\b(?P<action>aligns?|aligned|aligning)\s+(?P<body>[A-Za-z0-9][A-Za-z0-9 /&(),'-]{2,90}?)"
            r"(?:\s+against\s+(?P<target>[A-Za-z0-9][A-Za-z0-9 /&(),'-]{2,60}?))?(?:\s+[—-]\s+|[.;,]|$)",
            clause,
            flags=re.IGNORECASE,
        )
        if align_match:
            phrase = _trim_phrase(
                " ".join(
                    part
                    for part in (
                        align_match.group("action"),
                        align_match.group("body"),
                        f"against {align_match.group('target')}" if align_match.group("target") else "",
                    )
                    if part
                )
            )
            if 2 <= len(phrase.split()) <= 10:
                rows.append(phrase.casefold())
        focused_clause = _object_clause_focus(clause)
        phrase = _strip_action(focused_clause)
        if phrase.casefold() == focused_clause.casefold() and looks_like_action_clause(focused_clause):
            continue
        if not _content_terms(phrase):
            if focused_clause.casefold() != clause.casefold():
                continue
            phrase = clause
        phrase = re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", phrase, flags=re.IGNORECASE)
        tail_rows: list[str] = []
        relation_phrase = _trim_phrase(phrase)
        if re.search(r"\bto\s+(?:a|an|the)?\s*[A-Za-z0-9]", relation_phrase, flags=re.IGNORECASE):
            words = relation_phrase.split()
            if 4 <= len(words) <= 14 and len(_content_terms(relation_phrase)) >= 3:
                tail_rows.append(relation_phrase.casefold())
        tail_match = re.search(r"\b(?:from|into|with)\s+(?P<tail>.+)$", phrase, flags=re.IGNORECASE)
        if tail_match:
            tail = _trim_phrase(tail_match.group("tail"))
            if 1 <= len(tail.split()) <= 7 and _content_terms(tail):
                tail_rows.append(tail.casefold())
        phrase = re.sub(r"\b(?:for|from|into|to|with)\s+.+$", "", phrase, flags=re.IGNORECASE)
        phrase = _trim_phrase(phrase)
        if 1 <= len(phrase.split()) <= 7 and _content_terms(phrase):
            rows.append(phrase.casefold())
        rows.extend(tail_rows)
    if not rows:
        rows = _content_terms(fallback)[:5]
    return unique_text(rows)


def _sibling_focus(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    label = _label(row)
    if not label:
        return ""
    return f"{label} ownership of local state"


def _upstream_truth(value: str) -> str:
    label = _clean(value).strip(" .")
    if not label:
        return "accepted first-path input"
    if label.casefold().endswith("ownership"):
        return label
    return f"{label} ownership"


def _bridge_phrases(label: str, description: str) -> list[str]:
    """Derive compact artifact nouns from label descriptors and local details."""

    label_terms = _content_terms(label)
    phrases = _object_phrases(semantic_context.clauses(description), fallback=label)
    if not label_terms or not phrases:
        return []
    description_terms = set(_content_terms(description))
    bridge_terms = [term for term in reversed(label_terms[:5]) if term in description_terms]
    rows: list[str] = []
    if "scoring" in set(label_terms) | description_terms and "rubric" in description_terms:
        rows.append("scoring rubric")
    if "quality" in set(label_terms) | description_terms and "criteria" in description_terms:
        rows.append("quality criteria")
    if len(phrases) >= 3:
        return unique_text(rows)
    if not bridge_terms:
        return unique_text(rows)
    sorted_phrases = sorted(
        phrases[:8],
        key=_bridge_phrase_rank,
    )
    for left in bridge_terms[:2]:
        for phrase in sorted_phrases:
            phrase_terms = _content_terms(phrase)
            right = phrase_terms[0] if phrase_terms else ""
            if not right or left == right or left in phrase_terms:
                continue
            rows.append(f"{left} {right}")
            if len(rows) >= 2:
                return unique_text(rows)
    return unique_text(rows)


def _label_compound_phrases(label: str) -> list[str]:
    base = _clean_artifact_phrase(_label_object_base(label))
    rows: list[str] = []
    if base and _material_contract_phrase(base, label_terms=_content_terms(label), description_terms=()):
        rows.append(base)
    for group in re.split(r"\b(?:and|or)\b", label, flags=re.IGNORECASE):
        terms = [
            term
            for term in _literal_label_terms(group)
            if term not in {"adapter", "client", "engine", "service", "surface", "system", "viewer"}
        ]
        candidates = []
        if 2 <= len(terms) <= 5 and terms[-1] in _ARTIFACT_CARRIER_TERMS:
            candidates.append(" ".join(terms))
        candidates.extend(
            f"{terms[index]} {terms[index + 1]}"
            for index in range(max(0, len(terms) - 1))
            if not _descriptor_list_pair(terms[index], terms[index + 1])
        )
        for candidate in candidates:
            cleaned = strip_trailing_subject_modal(_clean_artifact_phrase(candidate))
            if (
                cleaned
                and len(cleaned.split()) >= 2
                and not _artifact_phrase_has_clause_shape(cleaned)
                and (
                    _material_contract_phrase(cleaned, label_terms=terms, description_terms=())
                    or (len(_content_terms(cleaned)) >= 2 and not looks_like_action_clause(cleaned))
                )
            ):
                rows.append(cleaned)
    rows = list(unique_text(rows))
    rows.sort(key=_label_compound_rank)
    return rows[:4]


def _descriptor_list_pair(left: str, right: str) -> bool:
    """Return whether adjacent label terms are list residue, not an artifact."""

    if right in {"typical", "relevant", "optional", "manual", "recent", "suggested", "recommended"}:
        return True
    return False


def _bridge_phrase_rank(phrase: str) -> tuple[int, str]:
    terms = set(_content_terms(phrase))
    for index, term in enumerate(("rubric", "rule", "policy", "threshold", "rationale", "criteria", "version")):
        if term in terms:
            return (index, phrase)
    return (20, phrase)


def _dedupe_phrase_subsets(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for phrase in values:
        terms = _phrase_identity_terms(phrase)
        if not terms:
            continue
        if any(terms == _phrase_identity_terms(existing) for existing in result):
            continue
        compact_artifact = _compact_artifact_phrase(phrase)
        if len(terms) <= 3 and not compact_artifact and any(terms < _phrase_identity_terms(existing) for existing in result):
            continue
        result = [
            existing
            for existing in result
            if not (
                len(_phrase_identity_terms(existing)) <= 3
                and _phrase_identity_terms(existing) < terms
                and not _compact_artifact_phrase(existing)
            )
        ]
        result.append(phrase)
    return result


def _compact_artifact_phrase(value: str) -> bool:
    words = [word.casefold() for word in _label_terms(_clean(value))]
    return bool(1 < len(words) <= 3 and set(words) & _ARTIFACT_CARRIER_TERMS)


def _prioritize_object_phrases(
    values: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> list[str]:
    label_set = semantic_context.expanded_context_anchors(set(label_terms[:7]))
    description_set = semantic_context.expanded_context_anchors(set(description_terms[:10]))

    def rank(index: int, phrase: str) -> tuple[int, int, int, int]:
        terms = _content_terms(phrase)
        term_set = set(terms)
        if not term_set:
            return (999, index, 0, 0)
        label_overlap = len(term_set & label_set)
        description_overlap = len(term_set & description_set)
        adds_beyond_label = bool(label_overlap and term_set - label_set)
        adds_beyond_description = bool(description_overlap and term_set - description_set)
        all_label = bool(term_set <= label_set)
        single = len(term_set) == 1
        score = 0
        score += label_overlap * 18
        score += description_overlap * 12
        if adds_beyond_label:
            score += 28
        if adds_beyond_description:
            score += 18
        if 2 <= len(term_set) <= 5:
            score += 8
        if all_label:
            score -= 12
        if single:
            score -= 10
        return (-score, index, -len(term_set), len(phrase))

    return [phrase for index, phrase in sorted(enumerate(values), key=lambda item: rank(item[0], item[1]))]


def _summary_object_phrases(
    values: Sequence[str],
    *,
    required_phrases: Sequence[str],
    label_terms: Sequence[str],
    description_terms: Sequence[str],
    limit: int = 12,
) -> list[str]:
    """Build the compact rendered object list without dropping stated responsibilities."""

    required = _dedupe_phrase_subsets(
        [
            phrase
            for phrase in _clean_artifact_phrases(required_phrases)
            if not _status_only_artifact_fragment(phrase)
            and _material_contract_phrase(phrase, label_terms=label_terms, description_terms=description_terms)
        ]
    )
    required = _prioritize_object_phrases(required, label_terms=(), description_terms=())
    values = [
        phrase
        for phrase in values
        if not _status_only_artifact_fragment(phrase)
        and _material_contract_phrase(phrase, label_terms=label_terms, description_terms=description_terms)
    ]
    result: list[str] = list(required[:limit])
    priority_budget = max(len(result), limit - max(0, len(required) - len(result)))
    for phrase in values:
        if len(result) >= priority_budget:
            break
        if phrase not in result:
            result.append(phrase)
    for phrase in required:
        if phrase not in result:
            result.append(phrase)
    for phrase in values:
        if len(result) >= limit:
            break
        if phrase not in result:
            result.append(phrase)
    result = semantic_context.prefer_richer_relation_phrases(result, values)
    return _drop_subsumed_singletons(result[:limit])


def _context_identity_phrases(
    values: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> tuple[str, ...]:
    """Keep qualified context objects needed to understand component ownership."""

    anchors = set(label_terms) | set(description_terms)
    rows: list[str] = []
    for value in values:
        words = [word.casefold().strip(".,;:") for word in _clean(value).split() if word.strip(".,;:")]
        for index, word in enumerate(words[:-1]):
            if word not in {"active", "candidate", "current", "ranked", "selected"}:
                continue
            right = words[index + 1]
            terms = set(_content_terms(right))
            if not terms or (anchors and not terms & semantic_context.expanded_context_anchors(anchors)):
                continue
            rows.append(f"{word} {right}")
    return tuple(unique_text(rows))


def _preserve_summary_phrases(
    summary_phrases: Sequence[str],
    protected_phrases: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
    limit: int,
) -> list[str]:
    """Keep accepted description facts that cleaners should not reinterpret."""

    protected: list[str] = []
    material_terms = set(label_terms) | set(description_terms)
    for phrase in protected_phrases:
        text = _clean(phrase).casefold().strip(" .,;")
        terms = set(_content_terms(text))
        if len(terms) < 2 or not (terms & material_terms):
            continue
        if _component_shell_artifact(text) or _status_only_artifact_fragment(text):
            continue
        protected.append(text)
    result = unique_text([*protected, *summary_phrases])
    if len(result) <= limit:
        return result
    protected_set = set(protected)
    kept = [phrase for phrase in result if phrase in protected_set]
    for phrase in result:
        if len(kept) >= limit:
            break
        if phrase not in kept:
            kept.append(phrase)
    return kept[:limit]


def _clean(value: Any) -> str:
    return clean_artifact_text(value, split_parentheses=True)


__all__ = ["SemanticComponentContract", "derive_component_semantic_contract"]
