"""Derive component-local greenfield contracts from accepted product semantics."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text


@dataclass(frozen=True)
class SemanticComponentContract:
    """Component-local contract fields derived from accepted intent text."""

    fields: Mapping[str, Any]
    confidence: int
    local_terms: tuple[str, ...]


_ACTION_VERBS = (
    "accept",
    "assemble",
    "assign",
    "audit",
    "block",
    "build",
    "capture",
    "check",
    "compare",
    "coordinate",
    "deduplicate",
    "define",
    "detect",
    "display",
    "export",
    "grant",
    "handoff",
    "import",
    "link",
    "normalize",
    "preserve",
    "record",
    "resolve",
    "route",
    "score",
    "screen",
    "store",
    "synthesize",
    "track",
    "validate",
)

_GENERIC_TERMS = {
    "accepted",
    "actor",
    "application",
    "boundary",
    "candidate",
    "component",
    "contract",
    "domain",
    "evidence",
    "first",
    "greenfield",
    "handoff",
    "input",
    "local",
    "output",
    "planned",
    "product",
    "project",
    "proof",
    "record",
    "release",
    "review",
    "reviewer",
    "source",
    "state",
    "system",
    "validation",
    "workspace",
}

_DANGLING_TAILS = {"a", "an", "and", "for", "from", "of", "or", "the", "to", "with"}


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
    clauses = _clauses(description)
    action_terms = _actions(description)
    raw_object_phrases = _object_phrases(clauses, fallback=label)
    source_fact_phrases = _source_fact_phrases(clauses, fallback=label)
    object_phrases = _enrich_object_phrases(
        raw_object_phrases,
        action_terms=action_terms,
        description=description,
        label=label,
    )
    local_terms = _local_terms(label, description, object_phrases)
    object_list = _phrase(object_phrases[:6]) or _phrase(local_terms[:5]) or _clean(label).casefold()
    critical = object_phrases[0] if object_phrases else (_phrase(local_terms[:2]) or "local state")
    input_focus = _input_focus(object_phrases=object_phrases, action_terms=action_terms, previous_label=previous_label)
    output_focus = _output_focus(object_phrases=object_phrases, action_terms=action_terms, next_label=next_label)
    states = _states_for(description, object_phrases=object_phrases)
    sibling_focus = _sibling_focus(sibling)
    outside = _outside_boundary(sibling_focus=sibling_focus)
    proof = _proof_rows(
        label=label,
        object_list=object_list,
        critical=critical,
        input_focus=input_focus,
        output_focus=output_focus,
        sibling_label=_label(sibling) if isinstance(sibling, Mapping) else "",
        sibling_focus=sibling_focus,
        source_fact=_phrase(source_fact_phrases[:6]),
    )
    fields = {
        "owned_state": f"{_clean(label).casefold()} state, {object_list}, local blockers, and handoff evidence for {state_label}",
        "accepted_inputs": f"{_safe_leading_actor(input_focus)}, actor identity, validation context, and upstream handoff",
        "produced_outputs": f"{_safe_leading_actor(output_focus)}, blocker signal, reviewer-visible rationale, and downstream handoff",
        "states_or_transitions": states,
        "outside_boundary": outside,
        "local_proof": proof,
        "upstream_truth": previous_label or "accepted first-path input",
        "downstream_consumers": next_label or "release proof review",
        "unique_failure": (
            f"{label} can look complete while {critical} is missing, stale, assigned to the wrong boundary, "
            f"or released without {output_focus} evidence"
        ),
    }
    confidence = len(object_phrases) * 3 + len(action_terms) * 2 + min(len(local_terms), 8)
    return SemanticComponentContract(fields=fields, confidence=confidence, local_terms=tuple(local_terms))


def _label(row: Mapping[str, Any] | None) -> str:
    if not isinstance(row, Mapping):
        return ""
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or "component"


def _description(row: Mapping[str, Any]) -> str:
    return _clean(row.get("source_system_description") or row.get("responsibility") or row.get("boundary"))


def _clauses(value: str) -> list[str]:
    text = _clean(value)
    text = re.sub(r"\brationale\s*:\s*.+$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*owns\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\brelevant\s+behavior\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\.\s+", ", ", text)
    text = re.sub(r"\b(?:before|after|while|so)\b.+$", "", text, flags=re.IGNORECASE)
    parts = re.split(r"[,;]", text)
    result: list[str] = []
    for part in parts:
        cleaned_part = _clean(part)
        cleaned = _clean(re.sub(r"^(?:and|or)\s+", "", cleaned_part, flags=re.IGNORECASE))
        if cleaned:
            result.append(cleaned)
    return result


def _object_phrases(clauses: Sequence[str], *, fallback: str) -> list[str]:
    result: list[str] = []
    for clause in clauses:
        phrase = _strip_action(clause)
        phrase = re.sub(r"\b(?:for|from|into|to|with)\s+.+$", "", phrase, flags=re.IGNORECASE)
        phrase = _trim_tail(_clean(phrase).strip(" ."))
        if 1 <= len(phrase.split()) <= 6 and _content_terms(phrase):
            result.append(phrase.casefold())
    if not result:
        result = _content_terms(fallback)[:4]
    return _unique(result)


def _source_fact_phrases(clauses: Sequence[str], *, fallback: str) -> list[str]:
    result: list[str] = []
    for clause in clauses:
        phrase = _strip_source_action(clause)
        phrase = _trim_tail(_clean(phrase).strip(" ."))
        if 1 <= len(phrase.split()) <= 14 and _content_terms(phrase):
            result.append(phrase.casefold())
    if not result:
        result = _object_phrases(clauses, fallback=fallback)
    return _unique(result)


def _enrich_object_phrases(
    object_phrases: Sequence[str],
    *,
    action_terms: Sequence[str],
    description: str,
    label: str,
) -> list[str]:
    """Keep the contract anchored to concrete accepted product facts.

    The enrichments below are generic product semantics: they preserve
    high-signal nouns already implied by the component label or description
    without introducing project-specific defaults.
    """

    text = _clean(description).casefold()
    label_text = _clean(label).casefold()
    front_extras: list[str] = []
    tail_extras: list[str] = []
    label_has_alert = bool(re.search(r"\b(alert|warning|notification|ledger|threshold|breach|anomaly)\b", label_text))
    label_has_model = bool(re.search(r"\b(model|metric|assessment|estimator|classifier|trend|health)\b", label_text))
    if label_has_alert or re.search(r"^\s*owns\s+[^.]*\b(alert|warning|notification|ledger|threshold|breach|anomaly)\b", text):
        front_extras.extend(("alert event", "threshold signal", "severity state", "acknowledgement state", "alert lifecycle"))
    if label_has_model or (
        not label_has_alert
        and re.search(r"^\s*owns\s+[^.]*\b(model|metric|assessment|estimator|classifier|trend|health)\b", text)
    ):
        front_extras.extend(("model input snapshot", "derived state estimate", "trend signal", "confidence marker", "readiness state"))
    if "define" in action_terms or re.search(r"\b(criteria|criterion)\b", text):
        front_extras.append("criteria definitions")
    if "define" in action_terms or re.search(r"\b(criteria|criterion|protocol|rule|policy|threshold)\b", text):
        tail_extras.extend(("protocol version", "rule validity"))
        if re.search(r"\binclusion\b", text):
            tail_extras.append("inclusion rules")
        if re.search(r"\bexclusion\b", text):
            tail_extras.append("exclusion rules")
        if re.search(r"\bexception\b", text):
            tail_extras.append("rule exceptions")
        if re.search(r"\bchange|history|version\b", text):
            tail_extras.append("rule-change history")
    if (
        any(action in action_terms for action in ("assign", "grant", "route", "resolve"))
        or re.search(r"\b(assignment|assigned|permission|access|conflict|eligibility|role|routing)\b", text)
    ):
        front_extras.extend(("reviewer eligibility", "assignment routing", "access grants", "conflict constraints", "permission state"))
    if "import" in action_terms or re.search(r"\b(import|dedupe|deduplicate|duplicate|normalize|metadata|provenance|source record|intake)\b", text):
        tail_extras.extend(("source identity", "normalized record", "duplicate signal", "malformed input blocker", "provenance marker"))
    if re.search(r"\b(screen|include|exclude|uncertain|disagreement|resolution)\b", text):
        tail_extras.extend(("separate reviewer decisions", "decision reasons", "disagreement markers", "resolution decision", "included-source handoff"))
    if "capture" in action_terms or re.search(r"\b(annotation|extraction|extract|field|source location|missing evidence|document)\b", text):
        tail_extras.extend(("source annotations", "extracted fields", "source locations", "missing-evidence blockers", "extraction provenance"))
    if "score" in action_terms or re.search(r"\b(score|scoring|rubric|rating|assessment|quality|required field|validation rule)\b", text):
        tail_extras.extend(("review fields", "scoring rubric", "required-field validation", "score inputs", "score outputs"))
    if any(action in action_terms for action in ("synthesize", "export")) or re.search(r"\b(synthesis|table|export|package|report|summary|output|deliverable)\b", text):
        tail_extras.extend(("synthesis table", "export package", "source references", "completeness blockers", "release handoff"))
    if "audit" in action_terms or "preserve" in action_terms or re.search(r"\b(audit|trail|version|history|retention|archive|replay)\b", text):
        tail_extras.extend(("immutable event history", "version chain", "retention policy state", "audit reconstruction", "replay evidence"))
    if re.search(r"\b(dashboard|comparison|compare|readiness|display|current decision|visible blocker)\b", text):
        tail_extras.extend(("current decision summary", "comparison display", "review readiness", "visible blockers", "user-facing decision state"))
    if "assemble" in action_terms or re.search(r"\b(decision package|approval|final approval|unresolved blocker|reviewer note|rationale)\b", text):
        tail_extras.extend(("evidence", "reviewer notes", "unresolved blockers", "final approval state", "decision rationale"))
    return _unique([*front_extras, *object_phrases, *tail_extras])


def _strip_action(value: str) -> str:
    verbs = "|".join(re.escape(verb) for verb in _ACTION_VERBS)
    return _clean(re.sub(rf"^(?:{verbs})(?:s|es|ed|ing)?\s+", "", value, flags=re.IGNORECASE))


def _strip_source_action(value: str) -> str:
    text = _clean(value)
    if re.match(r"^score\s+outputs?\b", text, flags=re.IGNORECASE):
        return text
    return _strip_action(text)


def _actions(value: str) -> list[str]:
    text = _clean(value).casefold()
    result: list[str] = []
    for verb in _ACTION_VERBS:
        if re.search(rf"\b{re.escape(verb)}(?:s|es|ed|ing)?\b", text):
            result.append(verb)
    return result


def _local_terms(label: str, description: str, object_phrases: Sequence[str]) -> list[str]:
    values = [label, description, *object_phrases]
    return _unique(
        [
            term
            for term in ordered_domain_terms(" ".join(values))
            if term not in _GENERIC_TERMS and not term.isdigit()
        ]
    )


def _input_focus(*, object_phrases: Sequence[str], action_terms: Sequence[str], previous_label: str) -> str:
    object_text = " ".join(object_phrases).casefold()
    if "alert event" in object_text or "threshold signal" in object_text:
        return "derived signal, threshold rule, severity input, acknowledgement command, and prior alert state"
    if "model input snapshot" in object_text or "derived state estimate" in object_text:
        return "normalized input snapshot, observed measurements, baseline context, trend source, and confidence rule"
    if "import" in action_terms:
        return "source payload, source timestamp, provenance marker, malformed-input signal, and import request"
    if "assign" in action_terms or "grant" in action_terms or "route" in action_terms:
        return "eligible actor, role attribute, conflict signal, permission request, and assignment trigger"
    if "define" in action_terms:
        return "question, rule draft, threshold, policy source, exception note, and prior version"
    if "score" in action_terms:
        return "required fields, rubric version, assessment evidence, score input, and reviewer answer"
    if "export" in action_terms or "synthesize" in action_terms:
        return "validated upstream evidence, source references, output format request, and completeness rule"
    if "audit" in action_terms or "preserve" in action_terms:
        return "state change event, actor identity, timestamp, prior version, retention rule, and provenance reference"
    focus = _phrase(object_phrases[:3]) or _clean(previous_label).casefold() or "accepted input"
    return f"{_safe_leading_actor(focus)} input"


def _output_focus(*, object_phrases: Sequence[str], action_terms: Sequence[str], next_label: str) -> str:
    object_text = " ".join(object_phrases).casefold()
    if "alert event" in object_text or "threshold signal" in object_text:
        return "alert event, severity state, acknowledgement requirement, resolution blocker, and alert handoff"
    if "model input snapshot" in object_text or "derived state estimate" in object_text:
        return "derived state estimate, trend signal, confidence marker, readiness state, and model handoff"
    if "import" in action_terms:
        return "normalized record, duplicate signal, rejected-input signal, provenance reference, and intake summary"
    if "assign" in action_terms or "grant" in action_terms or "route" in action_terms:
        return "assignment decision, access grant or denial, conflict blocker, and assignment handoff"
    if "define" in action_terms:
        return "active rule set, versioned protocol, rule validation result, exception blocker, and rule-change handoff"
    if "score" in action_terms:
        return "validated assessment, score output, missing-field blocker, rubric result, and scoring handoff"
    if "export" in action_terms or "synthesize" in action_terms:
        return "synthesis table, exportable package, completeness blocker, evidence summary, and release handoff"
    if "audit" in action_terms or "preserve" in action_terms:
        return "audit entry, version snapshot, retention decision, replay record, and immutable history evidence"
    focus = _phrase(object_phrases[:3]) or _clean(next_label).casefold() or "local result"
    return f"{_safe_leading_actor(focus)} result"


def _states_for(description: str, *, object_phrases: Sequence[str]) -> str:
    text = " ".join([description, *object_phrases]).casefold()
    if re.search(r"\b(?:model input snapshot|derived state estimate|confidence marker|readiness state)\b", text):
        return "not-calculated, input-ready, calculated, low-confidence, stale, overridden, and handed-off"
    if re.search(r"\b(?:alert event|threshold signal|severity state|acknowledgement state|alert lifecycle)\b", text):
        return "not-triggered, triggered, acknowledged, escalated, suppressed, resolved, stale, and handed-off"
    if re.search(r"\b(?:assign|permission|access|conflict|role|route)\b", text):
        return "unassigned, eligible, assigned, access-granted, access-denied, conflict-blocked, and reassigned"
    if re.search(r"\b(?:criteria|protocol|rule|policy|threshold|definition)\b", text):
        return "draft, active, revised, superseded, exception-blocked, invalid-rule, and retired"
    if re.search(r"\b(?:import|dedupe|duplicate|normalize|source|metadata)\b", text):
        return "not-imported, imported, normalized, duplicate-found, rejected, quarantined, provenance-attached, and handed-off"
    if re.search(r"\b(?:screen|include|exclude|disagree|resolution)\b", text):
        return "not-screened, in-review, included, excluded, disagreed, resolution-needed, resolved, and handed-off"
    if re.search(r"\b(?:extract|annotation|document|field|missing)\b", text):
        return "not-started, annotated, extracted, missing-evidence, validation-failed, revised, source-linked, and handed-off"
    if re.search(r"\b(?:score|rubric|assessment|rating|quality)\b", text):
        return "not-started, in-progress, missing-required-field, validation-failed, scored, revised, and submitted"
    if re.search(r"\b(?:decision|approval|approve|blocker|final|outcome)\b", text):
        return "draft, review-ready, blocked, returned, approved, rejected, finalized, and handed-off"
    if re.search(r"\b(?:synthesis|export|package|report|table|summary)\b", text):
        return "not-started, draft, incomplete, ready-for-export, exported, blocked, revised, and accepted"
    if re.search(r"\b(?:audit|trail|version|history|retention|archive)\b", text):
        return "recorded, versioned, retained, expired, restored, replayed, and audit-blocked"
    return "not-started, active, blocked, validation-failed, revised, and handed-off"


def _sibling_focus(sibling: Mapping[str, Any] | None) -> str:
    if not isinstance(sibling, Mapping):
        return ""
    description = _description(sibling)
    phrases = _enrich_object_phrases(
        _object_phrases(_clauses(description), fallback=_label(sibling)),
        action_terms=_actions(description),
        description=description,
        label=_label(sibling),
    )
    return _safe_leading_actor(_phrase(phrases[:4]) or _clean(_label(sibling)).casefold())


def _outside_boundary(*, sibling_focus: str) -> str:
    base = [
        "sibling-owned product responsibilities",
        "external-provider truth",
        "release approval",
        "runtime implementation outside the accepted proof boundary",
    ]
    if sibling_focus:
        base.insert(0, f"{sibling_focus} owned by the sibling component")
    return _phrase(base)


def _proof_rows(
    *,
    label: str,
    object_list: str,
    critical: str,
    input_focus: str,
    output_focus: str,
    sibling_label: str,
    sibling_focus: str,
    source_fact: str,
) -> tuple[str, ...]:
    rows = [
        f"{label} proves {_safe_leading_actor(object_list)} by accepting {_safe_leading_actor(input_focus)} and producing {_safe_leading_actor(output_focus)}.",
        f"Missing or invalid {_safe_leading_actor(critical)} blocks {_safe_leading_actor(output_focus)} before downstream handoff.",
    ]
    if source_fact and source_fact != object_list:
        rows.append(f"{label} preserves {_safe_leading_actor(source_fact)} as component-local state.")
    if sibling_label and sibling_focus:
        rows.append(f"{label} refuses {sibling_label} ownership over {sibling_focus}.")
    else:
        rows.append(f"{label} keeps its local proof separate from release approval and external-provider truth.")
    return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))


def _content_terms(value: str) -> list[str]:
    return [
        term
        for term in ordered_domain_terms(value)
        if term not in _GENERIC_TERMS and not term.isdigit()
    ]


def _phrase(values: Sequence[str]) -> str:
    rows = [_clean(value).casefold() for value in values if _clean(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _safe_leading_actor(value: str) -> str:
    """Avoid public leaves that begin with placeholder actor labels."""

    text = _clean(value)
    if re.match(
        r"^(?:Operator|Maintainer|Reviewer|Primary user|Project operator|Domain reviewer|Implementation owner|Evidence owner|End-user advocate|Workflow operator|Risk reviewer|Proof reviewer|Build owner)(?:\s|:|[-–—]|$)",
        text,
        flags=re.IGNORECASE,
    ):
        return f"local {text[:1].casefold()}{text[1:]}"
    return text


def _unique(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean(value).casefold()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _trim_tail(value: str) -> str:
    words = value.split()
    while words and words[-1].casefold().strip(".,;:") in _DANGLING_TAILS:
        words.pop()
    return " ".join(words)


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = ["SemanticComponentContract", "derive_component_semantic_contract"]
