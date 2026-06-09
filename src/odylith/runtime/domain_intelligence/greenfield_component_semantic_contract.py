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

from odylith.runtime.domain_intelligence import greenfield_component_semantic_context as semantic_context
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    accepted_inputs_text as _accepted_inputs_text,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    component_shell_artifact as _component_shell_artifact,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    contract_focus as _contract_focus,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    contract_list_text as _contract_list_text,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    label_compound_rank as _label_compound_rank,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    outside_boundary as _outside_boundary,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    produced_outputs_text as _produced_outputs_text,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import proof_rows as _proof_rows
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    state_transition_text as _state_transition_text,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import (
    status_only_artifact_fragment as _status_only_artifact_fragment,
)
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms as _label_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import ACTION_VERBS as _ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    ARTIFACT_CARRIER_TERMS as _ARTIFACT_CARRIER_TERMS,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import GENERIC_TERMS as _GENERIC_TERMS
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    action_forms_pattern as _action_forms_pattern,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    action_object_artifact_phrases as _action_object_artifact_phrases,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    clean_artifact_phrase as _clean_artifact_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    clean_artifact_phrases as _clean_artifact_phrases,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import content_terms as _content_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    descriptor_anchor_phrases as _descriptor_anchor_phrases,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import local_terms as _local_terms
from odylith.runtime.domain_intelligence.greenfield_component_terms import looks_action_term as _looks_action_term
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    object_clause_focus as _object_clause_focus,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    phrase_identity_terms as _phrase_identity_terms,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase as _phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action as _strip_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import trim_phrase as _trim_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    verb_forms_pattern as _verb_forms_pattern,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import (
    literal_label_terms as _literal_label_terms,
)
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
    proposal_context = _proposal_context(proposal)
    local_text = " ".join(text for text in (label, description, proposal_context) if text)
    clauses = semantic_context.clauses(description or label)
    action_terms = _actions(" ".join(text for text in (label, description) if text)) or _actions(local_text)
    description_phrases = _clean_artifact_phrases(
        [
            *_relation_phrases(description),
            *_object_phrases(clauses, fallback=label),
            *_action_object_artifact_phrases(description),
            *_descriptor_anchor_phrases(label, description),
        ]
    )
    label_terms = _content_terms(label)
    description_terms = _content_terms(description)
    context_phrases = semantic_context.context_object_phrases(
        proposal_context,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    label_phrases = _label_compound_phrases(label)
    bridge_phrases = _bridge_phrases(label, description)
    lifecycle_phrases = _lifecycle_phrases(label, description)
    role_phrases = _component_role_phrases(label=label, description=description)
    context_required_phrases = semantic_context.context_required_phrases(
        context_phrases,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    context_compound_phrases = semantic_context.context_anchor_compounds(
        proposal_context,
        anchor_terms=unique_text([*label_terms, *description_terms]),
    )
    local_phrases = [*description_phrases, *label_phrases, *bridge_phrases, *lifecycle_phrases, *role_phrases]
    needs_context_backfill = semantic_context.needs_context_backfill(
        description=description,
        description_phrases=description_phrases,
        context_required_phrases=context_required_phrases,
    )
    context_backfill = [*context_phrases[:5], *context_compound_phrases[:3]] if needs_context_backfill else []
    object_phrases = _clean_artifact_phrases([*local_phrases, *context_backfill])
    object_phrases = _dedupe_phrase_subsets(object_phrases)
    object_phrases = _prioritize_object_phrases(
        object_phrases,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    if description:
        required_seed = [
            *description_phrases[:10],
            *([] if not needs_context_backfill else context_phrases[:4]),
            *([] if not needs_context_backfill else context_required_phrases[:8]),
            *([] if not needs_context_backfill else context_phrases[:3]),
            *label_phrases[:3],
            *bridge_phrases[:2],
            *lifecycle_phrases,
            *role_phrases,
            *([] if not needs_context_backfill else context_compound_phrases[:4]),
        ]
    else:
        required_seed = [
            *label_phrases[:3],
            *bridge_phrases[:2],
            *lifecycle_phrases,
            *role_phrases,
            *context_required_phrases[:3],
            *context_compound_phrases[:3],
        ]
    summary_phrases = _summary_object_phrases(
        object_phrases,
        required_phrases=unique_text(required_seed),
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
        contract_terms=(*label_terms, *description_terms),
    )
    output_focus = _contract_focus(
        object_list=focus_list,
        action_terms=action_terms,
        fallback=next_label or "downstream state",
        role="output",
        contract_terms=(*label_terms, *description_terms),
    )
    critical = _result_like_phrase(output_focus) or critical
    states = _state_transition_text(
        action_terms=action_terms,
        object_phrases=object_phrases,
        context_text=proposal_context,
        anchor_terms=(*_content_terms(label), *_content_terms(description)),
    )
    sibling_label = _label(sibling) if isinstance(sibling, Mapping) else ""
    sibling_focus = _sibling_focus(sibling)
    proof = _proof_rows(
        label=label,
        object_list=object_list,
        critical=critical,
        input_focus=input_focus,
        output_focus=output_focus,
        sibling_label=sibling_label,
        sibling_focus=sibling_focus,
    )
    evidence_phrases = ("source evidence",) if _needs_source_evidence(
        label=label,
        description=description,
        proposal_context=proposal_context,
        action_terms=action_terms,
    ) else ()
    owned_context_phrases = _owned_context_detail_phrases(
        context_phrases,
        context_compound_phrases,
        label_terms=label_terms,
    )
    owned_summary_phrases = summary_phrases[:7]
    title_identity_phrases = _title_identity_phrases(label_phrases, owned_summary_phrases)
    owned_seed = (
        (
            *title_identity_phrases,
            *owned_summary_phrases,
            *role_phrases[:3],
            *owned_context_phrases[:2],
            *evidence_phrases,
            "blocker state",
            "next-step context",
        )
        if summary_phrases
        else (f"{_clean(label).casefold()} state", *label_phrases[:1], *evidence_phrases, "blocker state")
    )
    owned_seed = tuple(_drop_subsumed_singletons(owned_seed))
    failure_cause = (
        "calculated from the wrong inputs"
        if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "score"))
        else "built from the wrong inputs"
    )
    fields = {
        "owned_state": _contract_list_text(*owned_seed),
        "accepted_inputs": _accepted_inputs_text(input_focus),
        "produced_outputs": _produced_outputs_text(output_focus),
        "states_or_transitions": states,
        "outside_boundary": _outside_boundary(sibling_focus=sibling_focus),
        "local_proof": proof,
        "upstream_truth": previous_label or "accepted first-path input",
        "downstream_consumers": next_label or "release review",
        "unique_failure": (
            f"{label} can mislead users if {critical} {_present_verb(critical, singular='is', plural='are')} missing, stale, {failure_cause}, "
            "or shown without enough explanation to recover"
        ),
    }
    confidence = len(object_phrases) * 3 + len(action_terms) * 2 + min(len(local_terms), 8)
    return SemanticComponentContract(fields=fields, confidence=confidence, local_terms=tuple(local_terms))


def _result_like_phrase(value: str) -> str:
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


def _component_role_phrases(*, label: str, description: str) -> tuple[str, ...]:
    text = _clean(" ".join([label, description])).casefold()
    phrases: list[str] = []
    if re.search(r"\b(?:audit|evidence|ledger|log|proof|replay|reviewable|trace)\b", text):
        phrases.extend(["audit trail", "replay packet", "decision ledger"])
    if re.search(r"\b(?:failure|blocked|invalid|missing|recovery)\b", text):
        phrases.append("failure reason ledger")
    if re.search(r"\b(?:guardrail|limit|rollout|release)\b", text):
        phrases.extend(["known-limit checkpoint", "recovery-condition ledger"])
    return tuple(unique_text(phrases))


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


def _needs_source_evidence(
    *,
    label: str,
    description: str,
    proposal_context: str,
    action_terms: Sequence[str],
) -> bool:
    """Return whether the local record must retain source/evidence context."""

    local_context = " ".join([label, description, proposal_context])
    if not re.search(r"\b(?:source|evidence|provenance|attachment|audit)\b", _clean(local_context), re.IGNORECASE):
        return False
    if re.search(r"\b(?:source|evidence|provenance|attachment|audit)\b", _clean(description), re.IGNORECASE):
        return True
    local_terms = set(_content_terms(" ".join([label, description])))
    record_actions = {"capture", "create", "edit", "import", "log", "record", "save", "store", "submit", "track"}
    return bool(record_actions & set(action_terms) or local_terms & {"entry", "history", "ledger", "log", "record", "store"})


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
            scaffold_subject = _generated_scaffold_subject(text, label=label)
            if scaffold_subject:
                return scaffold_subject
            continue
        return _scrub_description_scaffold(text)
    return ""


def _scrub_description_scaffold(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\bRelevant\s+behavior\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\bRationale\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip()
    return text.rstrip(" .")


def _generated_scaffold_subject(value: str, *, label: str) -> str:
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
    project_brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    semantic_model = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    ontology = semantic_model.get("domain_ontology") if isinstance(semantic_model.get("domain_ontology"), Mapping) else {}
    values = [
        intent.get("first_path"),
        intent.get("proof_boundary"),
        intent.get("state_object"),
        intent.get("product_story"),
        intent.get("external_systems"),
        proposal.get("external_systems"),
        *project_brief.values(),
        *ontology.values(),
    ]
    return " ".join(_clean(value) for value in values if _clean(value))


def _object_phrases(clauses: Sequence[str], *, fallback: str) -> list[str]:
    rows: list[str] = []
    for clause in clauses:
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
        phrase = _strip_action(_object_clause_focus(clause))
        if not _content_terms(phrase):
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


def _full_list_phrases(value: str) -> list[str]:
    """Preserve compact ownership lists before comma splitting breaks meaning."""

    rows: list[str] = []
    text = _clean(value)
    action_pattern = _action_forms_pattern()
    for match in re.finditer(
        rf"\b(?:{action_pattern})\s+(?P<body>[^.]+?,\s+[^.]+?,\s+(?:and\s+)?[^.]+)",
        text,
        flags=re.IGNORECASE,
    ):
        phrase = re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", match.group("body"), flags=re.IGNORECASE)
        phrase = _trim_phrase(phrase)
        words = phrase.split()
        if 4 <= len(words) <= 18 and len(_content_terms(phrase)) >= 4:
            rows.append(phrase.casefold())
    return unique_text(rows)


def _relation_phrases(value: str) -> list[str]:
    """Preserve compact "thing to thing" phrases before clause splitting."""

    rows: list[str] = []
    text = _clean(value)
    if not text:
        return rows
    action_pattern = _action_forms_pattern()
    for clause in re.split(r"[.;]", text):
        segment = _trim_phrase(re.sub(r"\b(?:before|after|while|because|unless|without)\b.+$", "", clause, flags=re.I))
        if not segment:
            continue
        action_match = re.search(rf"\b(?:{action_pattern})\s+(?P<body>.+\bto\s+.+)$", segment, flags=re.I)
        body = action_match.group("body") if action_match else segment
        body = _trim_phrase(body)
        if not re.search(r"\bto\s+(?:a|an|the)?\s*[A-Za-z0-9]", body, flags=re.I):
            continue
        words = body.split()
        if 4 <= len(words) <= 18 and len(_content_terms(body)) >= 4:
            rows.append(body.casefold())
    return unique_text(rows)


def _actions(value: str) -> list[str]:
    text = _clean(value).casefold()
    result: list[str] = []
    for verb in _ACTION_VERBS:
        if re.search(rf"\b(?:{_verb_forms_pattern(verb)})\b", text):
            result.append(verb)
    return result


def _sibling_focus(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    label = _label(row)
    if not label:
        return ""
    return f"{label} ownership of local state"


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
    terms = [
        term
        for term in _literal_label_terms(label)
        if term not in {"adapter", "client", "engine", "service", "surface", "system", "viewer"}
    ]
    rows: list[str] = []
    if 2 <= len(terms) <= 5 and terms[-1] in _ARTIFACT_CARRIER_TERMS:
        rows.append(" ".join(terms))
    for index in range(max(0, len(terms) - 1)):
        left = terms[index]
        right = terms[index + 1]
        if _descriptor_list_pair(left, right):
            continue
        rows.append(f"{left} {right}")
    rows = list(unique_text(rows))
    rows.sort(key=_label_compound_rank)
    return rows[:4]


def _descriptor_list_pair(left: str, right: str) -> bool:
    """Return whether adjacent label terms are list residue, not an artifact."""

    if right in {"typical", "relevant", "optional", "manual", "recent", "suggested", "recommended"}:
        return True
    return False


def _title_identity_phrases(label_phrases: Sequence[str], summary_phrases: Sequence[str]) -> tuple[str, ...]:
    summary = {phrase.casefold() for phrase in summary_phrases}
    rows: list[str] = []
    for phrase in label_phrases:
        words = phrase.split()
        if len(words) < 2:
            continue
        if phrase.casefold() in summary:
            continue
        if words[-1] not in _ARTIFACT_CARRIER_TERMS and len(_content_terms(phrase)) < 2:
            continue
        if _component_shell_artifact(phrase) or _status_only_artifact_fragment(phrase):
            continue
        rows.append(phrase)
        if len(rows) >= 2:
            break
    return tuple(rows)


def _owned_context_detail_phrases(
    context_phrases: Sequence[str],
    context_compound_phrases: Sequence[str],
    *,
    label_terms: Sequence[str],
) -> tuple[str, ...]:
    rows: list[str] = []
    label_term_set = set(label_terms)
    for phrase in (*context_phrases, *context_compound_phrases):
        terms = list(_content_terms(phrase))
        if len(terms) < 2:
            continue
        decision_detail = bool(
            label_term_set & {"decision", "journal", "ledger"}
            and "decision" in terms
            and terms[0] not in {"first", "local", "next", "product", "release", "review", "source", "validation"}
        )
        if (
            terms[0] not in {"accepted", "current", "incomplete", "missing", "recent", "required", "selected", "unavailable"}
            and not decision_detail
        ):
            continue
        if set(terms) & {"context", "summary"}:
            continue
        if not set(terms) & _ARTIFACT_CARRIER_TERMS:
            continue
        if terms[-1] in {"link", "links"} and len(terms) > 2:
            terms = terms[:-1]
        if terms == ["missing", "contact"]:
            terms.append("detail")
        rows.append(" ".join(terms[:4]))
        if len(rows) >= 3:
            break
    return tuple(unique_text(rows))


def _bridge_phrase_rank(phrase: str) -> tuple[int, str]:
    terms = set(_content_terms(phrase))
    for index, term in enumerate(("rubric", "rule", "policy", "threshold", "rationale", "criteria", "version")):
        if term in terms:
            return (index, phrase)
    return (20, phrase)


def _lifecycle_phrases(label: str, description: str) -> list[str]:
    """Add a compact lifecycle noun when local text names event/history flow."""

    description_terms = set(_content_terms(description))
    if not description_terms & {"event", "history", "resolution", "transition"}:
        return []
    for term in _content_terms(label):
        if term in description_terms:
            return [f"{term} lifecycle"]
    return []


def _dedupe_phrase_subsets(values: Sequence[str]) -> list[str]:
    """Deduplicate phrases without erasing richer component-local details."""

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
    """Prefer phrases that add intent-derived detail to the component boundary."""

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


def _summary_object_phrases(values: Sequence[str], *, required_phrases: Sequence[str], limit: int = 12) -> list[str]:
    """Build the compact rendered object list without dropping stated responsibilities."""

    required = _dedupe_phrase_subsets(_clean_artifact_phrases(required_phrases))
    required = _prioritize_object_phrases(required, label_terms=(), description_terms=())
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
    return _drop_subsumed_singletons(result[:limit])


def _drop_subsumed_singletons(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    identities = [(phrase, _phrase_identity_terms(phrase)) for phrase in values]
    for phrase, terms in identities:
        if len(terms) == 1 and any(terms < other_terms for other_phrase, other_terms in identities if other_phrase != phrase):
            continue
        if terms & {"incomplete", "missing", "recent", "unavailable"} and any(
            terms < other_terms for other_phrase, other_terms in identities if other_phrase != phrase
        ):
            continue
        result.append(phrase)
    return result


def _clean(value: Any) -> str:
    return clean_artifact_text(value, split_parentheses=True)


def _present_verb(value: str, *, singular: str, plural: str) -> str:
    words = [word.casefold() for word in re.findall(r"[a-z][a-z'-]*", _clean(value))]
    if not words:
        return singular
    head = next((word for word in reversed(words) if word not in {"context", "detail", "evidence", "state"}), words[-1])
    if head.endswith("s") and head not in {"status", "process"}:
        return plural
    if " and " in f" {_clean(value).casefold()} ":
        return plural
    return singular


__all__ = ["SemanticComponentContract", "derive_component_semantic_contract"]
