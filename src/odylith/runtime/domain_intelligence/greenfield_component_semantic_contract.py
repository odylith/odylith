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
    phrase_identity_terms as _component_phrase_identity_terms,
)
from odylith.runtime.domain_intelligence.greenfield_component_terms import strip_action as _strip_action
from odylith.runtime.domain_intelligence.greenfield_component_terms import trim_phrase as _trim_phrase
from odylith.runtime.domain_intelligence.greenfield_component_terms import (
    verb_forms_pattern as _verb_forms_pattern,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_domain_token
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
    clauses = _clauses(description or label)
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
    context_phrases = _context_object_phrases(
        proposal_context,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    label_phrases = _label_compound_phrases(label)
    bridge_phrases = _bridge_phrases(label, description)
    lifecycle_phrases = _lifecycle_phrases(label, description)
    context_required_phrases = _context_required_phrases(
        context_phrases,
        label_terms=label_terms,
        description_terms=description_terms,
    )
    context_compound_phrases = _context_anchor_compounds(
        proposal_context,
        anchor_terms=unique_text([*label_terms, *description_terms]),
    )
    local_phrases = [*description_phrases, *label_phrases, *bridge_phrases, *lifecycle_phrases]
    needs_context_backfill = _needs_context_backfill(
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
            *label_phrases[:2],
            *bridge_phrases[:2],
            *lifecycle_phrases,
            *([] if not needs_context_backfill else context_compound_phrases[:4]),
        ]
    else:
        required_seed = [
            *label_phrases[:2],
            *bridge_phrases[:2],
            *lifecycle_phrases,
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
    critical = summary_phrases[0] if summary_phrases else (_phrase(local_terms[:3]) or "local state")
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
    states = _states_for(
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
    fields = {
        "owned_state": _contract_list_text(
            f"{_clean(label).casefold()} state",
            *label_phrases[:1],
            *summary_phrases[:7],
            *evidence_phrases,
            "blocker state",
            "next-step context",
        ),
        "accepted_inputs": _accepted_inputs_text(input_focus),
        "produced_outputs": _produced_outputs_text(output_focus),
        "states_or_transitions": states,
        "outside_boundary": _outside_boundary(sibling_focus=sibling_focus),
        "local_proof": proof,
        "upstream_truth": previous_label or "accepted input context",
        "downstream_consumers": next_label or "release review",
        "unique_failure": (
            f"{label} can mislead users if {critical} is missing, stale, calculated from the wrong inputs, "
            "or shown without enough explanation to recover"
        ),
    }
    confidence = len(object_phrases) * 3 + len(action_terms) * 2 + min(len(local_terms), 8)
    return SemanticComponentContract(fields=fields, confidence=confidence, local_terms=tuple(local_terms))


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
    for key in ("source_system_description", "responsibility", "boundary"):
        text = _clean(row.get(key))
        if text and not _looks_generated_scaffold(text):
            return _scrub_description_scaffold(text)
    return ""


def _scrub_description_scaffold(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\bRelevant\s+behavior\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\bRationale\s*:\s*.+$", "", text, flags=re.IGNORECASE).strip()
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


def _clauses(value: str) -> list[str]:
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
        tail_match = re.search(r"\b(?:from|with)\s+(?P<tail>.+)$", phrase, flags=re.IGNORECASE)
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


def _context_object_phrases(
    value: str,
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> list[str]:
    anchors = set(label_terms[:5]) | set(description_terms[:8])
    anchors = _expanded_context_anchors(anchors)
    rows: list[str] = []
    carry = 0
    carry_base: tuple[str, ...] = ()
    for clause in _clauses(value):
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


def _context_required_phrases(
    values: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
    limit: int = 5,
) -> list[str]:
    """Select late path/proof phrases that add local detail beyond the label."""

    anchors = set(label_terms[:6]) | set(description_terms[:8])
    if not anchors:
        return []
    expanded = _expanded_context_anchors(anchors)
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


def _needs_context_backfill(
    *,
    description: str,
    description_phrases: Sequence[str],
    context_required_phrases: Sequence[str],
) -> bool:
    """Return whether local text needs first-path field detail backfill."""

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


def _context_anchor_compounds(value: str, *, anchor_terms: Sequence[str], limit: int = 8) -> list[str]:
    """Extract compact local compounds around label or description anchors."""

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


def _opens_detail_list(value: str) -> bool:
    """Return whether a clause is likely followed by list-item details."""

    return bool(re.search(r"\b(?:for|including|includes|with)\b", _clean(value), flags=re.IGNORECASE))


def _context_carry_base(
    terms: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> tuple[str, ...]:
    """Return a compact local noun base for list items following an anchored clause."""

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


def _expanded_context_anchors(anchors: set[str]) -> set[str]:
    """Add generic action neighbors so thin labels can find their path clause."""

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


def _actions(value: str) -> list[str]:
    text = _clean(value).casefold()
    result: list[str] = []
    for verb in _ACTION_VERBS:
        if re.search(rf"\b(?:{_verb_forms_pattern(verb)})\b", text):
            result.append(verb)
    return result


def _contract_focus(
    *,
    object_list: str,
    action_terms: Sequence[str],
    fallback: str,
    role: str,
    contract_terms: Sequence[str] = (),
) -> str:
    focus = _safe_artifact_focus(_clean(object_list) or _clean(fallback).casefold() or "accepted state")
    adjustment = _adjustment_artifact(focus) if _component_owns_adjustment(contract_terms) else ""
    if adjustment and any(action in action_terms for action in ("adjust", "calculate", "compute", "derive")):
        support = _supporting_artifacts(focus, exclude_terms=set(_content_terms(adjustment)))
        if role == "input":
            return f"{adjustment} request, {support}, prior state, and explanation context"
        rationale_terms = set(_content_terms(focus)) | set(contract_terms)
        rationale = "adjustment rationale" if "rationale" in rationale_terms else "review rationale"
        return f"{adjustment} result, {rationale}, blocked-state detail, and next-step context"
    if role == "input":
        if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "score")):
            return f"{focus} inputs, rule context, prior result, and validation command"
        if any(action in action_terms for action in ("capture", "create", "edit", "log", "record", "save", "store", "submit")):
            return f"required {focus} command, required fields, prior state, and explanation context"
        if any(action in action_terms for action in ("compare", "order", "rank")):
            return f"candidate {focus} set, comparison criteria, tie-break rule, and prior selection state"
        if any(action in action_terms for action in ("select", "choose")):
            return f"candidate {focus} set, selection criteria, tie-break rule, and prior selection state"
        if any(action in action_terms for action in ("export", "delete", "request")):
            return f"authorized {focus} request, actor authority, protected-state reference, and policy context"
        return f"required {focus} input, prior state, explanation context, and validation command"
    if any(action in action_terms for action in ("capture", "create", "edit", "log", "record", "save", "store", "submit")):
        return f"validated {focus} state, correction marker, and replayable change evidence"
    if any(action in action_terms for action in ("calculate", "compute", "derive", "evaluate", "score")):
        return f"{focus} result, rule explanation, and review evidence"
    if any(action in action_terms for action in ("compare", "order", "rank")):
        return f"ranked {focus} result, comparison explanation, and selection rationale"
    if any(action in action_terms for action in ("select", "choose")):
        return f"selected {focus} result, selection explanation, and selection rationale"
    if any(action in action_terms for action in ("export", "delete", "request")):
        return f"{focus} decision, allowed or blocked marker, and lifecycle evidence"
    return f"{focus} result, state update, and review detail"


def _safe_artifact_focus(value: str) -> str:
    """Avoid public contract artifacts that start with placeholder actor labels."""

    text = _clean(value).strip(" .")
    if re.match(
        r"^(?:operator|maintainer|reviewer|primary user|project operator|domain reviewer|implementation owner|"
        r"evidence owner|workflow operator|risk reviewer|proof reviewer)(?:\s|:|[-–—]|$)",
        text,
        flags=re.IGNORECASE,
    ):
        return f"local {text[:1].lower()}{text[1:]}"
    return text


def _produced_outputs_text(output_focus: str) -> str:
    text = _clean(output_focus).rstrip(" .")
    lowered = text.casefold()
    suffixes = []
    if "blocked-state" not in lowered and "blocker" not in lowered:
        suffixes.append("blocked-state detail")
    if "rationale" not in lowered and "explanation" not in lowered:
        suffixes.append("reviewer explanation")
    if "next-step context" not in lowered:
        suffixes.append("next-step context")
    if "handoff" not in lowered:
        suffixes.append("handoff context")
    if not suffixes:
        return text
    if len(suffixes) == 1:
        suffix_text = suffixes[0]
    else:
        suffix_text = f"{', '.join(suffixes[:-1])}, and {suffixes[-1]}"
    return f"{text}, {suffix_text}"


def _accepted_inputs_text(input_focus: str) -> str:
    rows = _contract_text_items(input_focus)
    required = ("authorized actor", "validation context")
    return _contract_list_text(*rows, *required)


def _contract_list_text(*values: str) -> str:
    return ", ".join(_contract_text_items(", ".join(value for value in values if _clean(value))))


def _contract_text_items(value: str) -> list[str]:
    rows: list[str] = []
    for raw in re.split(r",\s+|\s+and\s+", _clean(value), flags=re.IGNORECASE):
        phrase = _clean_artifact_phrase(raw)
        if phrase and phrase not in rows:
            rows.append(phrase)
    return rows


def _adjustment_artifact(value: str) -> str:
    phrases = [phrase.strip() for phrase in _clean(value).casefold().split(",") if phrase.strip()]
    primary_terms = _content_terms(", ".join(phrases[:5]))
    if "plan" in primary_terms and (
        "adjusted" in primary_terms or "adjustment" in primary_terms or "target" in primary_terms
    ):
        return "plan adjustment"
    for phrase in phrases[:5]:
        phrase_terms = _content_terms(phrase)
        if "adjusted" in phrase_terms and len(phrase_terms) >= 2:
            subject = next((term for term in phrase_terms if term != "adjusted"), "")
            if subject:
                return f"{subject} adjustment"
    return ""


def _component_owns_adjustment(terms: Sequence[str]) -> bool:
    local = set(terms)
    return bool(local & {"adjustment", "recommendation", "target"} and local & {"plan", "target", "recommendation"})


def _supporting_artifacts(value: str, *, exclude_terms: set[str]) -> str:
    phrases: list[str] = []
    for phrase in [part.strip() for part in _clean(value).casefold().split(",") if part.strip()]:
        terms = set(_content_terms(phrase))
        if not terms or terms & exclude_terms or "rationale" in terms:
            continue
        phrases.append(phrase)
        if len(phrases) >= 3:
            break
    return _phrase(phrases) or "accepted input detail"


def _evidence_phrase(value: str) -> str:
    text = _clean(value).rstrip(" .")
    if re.search(r"\bevidence$", text, flags=re.IGNORECASE):
        return text
    return f"{text} detail" if text else "review detail"


def _states_for(
    *,
    action_terms: Sequence[str],
    object_phrases: Sequence[str],
    context_text: str = "",
    anchor_terms: Sequence[str] = (),
) -> str:
    verbs = [_past_tense(verb) for verb in action_terms if verb != "sync"]
    transitions = _transition_terms(object_phrases, context_text=context_text, anchor_terms=anchor_terms)
    states = unique_text(
        [
            *transitions,
            "requested",
            "received",
            *verbs,
            "validated",
            "blocked",
            "revised",
            "ready-for-next-step",
        ]
    )
    return ", ".join(states[:18])


def _transition_terms(
    object_phrases: Sequence[str],
    *,
    context_text: str = "",
    anchor_terms: Sequence[str] = (),
) -> list[str]:
    state_words = {_past_tense(verb) for verb in _ACTION_VERBS if verb}
    state_words.update({"sent", "stale", "ready", "open", "closed", "pending", "visible", "hidden"})
    rows: list[str] = []
    phrases = [*_context_transition_clauses(context_text, anchor_terms=anchor_terms), *object_phrases]
    for phrase in phrases:
        for term in _transition_candidate_terms(phrase):
            if term in {"required", "succeed", "succeeded"}:
                continue
            if term in state_words or (len(term) > 4 and term.endswith("ed")):
                rows.append(term)
    return unique_text(rows)


def _transition_candidate_terms(value: str) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", _clean(value).casefold()):
        token = normalize_domain_token(raw, stopwords=())
        if token not in seen:
            seen.add(token)
            rows.append(token)
    return rows


def _context_transition_clauses(context_text: str, *, anchor_terms: Sequence[str]) -> list[str]:
    text = _clean(context_text)
    if not text:
        return []
    anchors = set(anchor_terms)
    anchors.update({"status", "lifecycle", "history", "timeline", "event", "progress"})
    rows: list[str] = []
    for clause in re.split(r"(?<=[.!?])\s+|;\s+", text):
        terms = set(_content_terms(clause))
        if terms & anchors:
            rows.append(clause)
    return rows[:8]


def _past_tense(value: str) -> str:
    verb = str(value or "").strip()
    if not verb:
        return ""
    if verb == "build":
        return "built"
    if verb == "choose":
        return "chosen"
    if verb == "log":
        return "logged"
    if verb == "make":
        return "made"
    if verb == "submit":
        return "submitted"
    if verb.endswith("e"):
        return f"{verb}d"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in {"a", "e", "i", "o", "u"}:
        return f"{verb[:-1]}ied"
    return f"{verb}ed"


def _outside_boundary(*, sibling_focus: str) -> str:
    rows = [
        "responsibilities not named by this component boundary",
        "adjacent component state and review evidence owned elsewhere",
        "mutation of upstream facts, silent overwrite of another component result, and release approval",
    ]
    if sibling_focus:
        rows[1] = sibling_focus
    return "; ".join(rows)


def _proof_rows(
    *,
    label: str,
    object_list: str,
    critical: str,
    input_focus: str,
    output_focus: str,
    sibling_label: str,
    sibling_focus: str,
) -> list[str]:
    rows = [
        f"Run one {label} example where {critical} reaches the visible result with a clear explanation.",
        f"Run one blocked {label} example where missing or malformed input explains what must change before the result can be trusted.",
        f"Replay one {label} result and confirm the actor, input facts, status, and explanation still agree.",
    ]
    if sibling_label:
        rows.append(
            f"{sibling_label} can consume the result but cannot rewrite {label}'s local state"
            + (f" while {sibling_focus} remains sibling-owned." if sibling_focus else ".")
        )
    return rows


def _sibling_focus(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    label = _label(row)
    description = _description(row)
    phrases = _object_phrases(_clauses(" ".join([label, description])), fallback=label)
    focus = _phrase(phrases[:4])
    return f"{label} ownership over {focus}" if focus and label else ""


def _bridge_phrases(label: str, description: str) -> list[str]:
    """Derive compact artifact nouns from label descriptors and local details."""

    label_terms = _content_terms(label)
    phrases = _object_phrases(_clauses(description), fallback=label)
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
        for term in _content_terms(label)
        if term not in {"adapter", "client", "engine", "service", "surface", "system", "viewer"}
    ]
    rows: list[str] = []
    for index in range(max(0, len(terms) - 1)):
        rows.append(f"{terms[index]} {terms[index + 1]}")
    return unique_text(rows[:3])


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
        if len(terms) <= 3 and any(terms < _phrase_identity_terms(existing) for existing in result):
            continue
        result = [
            existing
            for existing in result
            if not (len(_phrase_identity_terms(existing)) <= 3 and _phrase_identity_terms(existing) < terms)
        ]
        result.append(phrase)
    return result


def _phrase_identity_terms(value: str) -> set[str]:
    """Return phrase identity terms while keeping artifact-carrier nouns."""

    return _component_phrase_identity_terms(value)


def _prioritize_object_phrases(
    values: Sequence[str],
    *,
    label_terms: Sequence[str],
    description_terms: Sequence[str],
) -> list[str]:
    """Prefer phrases that add intent-derived detail to the component boundary."""

    label_set = _expanded_context_anchors(set(label_terms[:7]))
    description_set = _expanded_context_anchors(set(description_terms[:10]))

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

    required = unique_text(required_phrases)
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
    return result[:limit]


def _drop_actor_action_lead(terms: Sequence[str]) -> list[str]:
    """Remove actor/action prefixes that are not artifact nouns."""

    result = list(terms)
    if len(result) >= 2 and _looks_actor_term(result[0]) and _looks_action_term(result[1]):
        result = result[2:]
    if len(result) >= 2 and _looks_action_term(result[0]) and result[0] not in _ARTIFACT_CARRIER_TERMS:
        result = result[1:]
    return result


def _looks_actor_term(value: str) -> bool:
    token = str(value or "").casefold()
    return bool(re.search(r"(?:er|or|ist|ian|ant|ee)$", token))


def _phrase(values: Sequence[str]) -> str:
    return ", ".join(_clean(value) for value in values if _clean(value))


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "").replace("(", " ").replace(")", " ")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["SemanticComponentContract", "derive_component_semantic_contract"]
