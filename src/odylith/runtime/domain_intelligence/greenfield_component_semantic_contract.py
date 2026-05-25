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
    "adjust",
    "approve",
    "assemble",
    "assign",
    "audit",
    "block",
    "build",
    "calculate",
    "capture",
    "check",
    "choose",
    "close",
    "compare",
    "complete",
    "compute",
    "confirm",
    "coordinate",
    "collect",
    "deduplicate",
    "define",
    "detect",
    "display",
    "edit",
    "export",
    "grant",
    "handoff",
    "handle",
    "import",
    "keep",
    "link",
    "maintain",
    "normalize",
    "notify",
    "order",
    "preserve",
    "price",
    "present",
    "publish",
    "record",
    "recommend",
    "recompute",
    "render",
    "rank",
    "request",
    "restore",
    "return",
    "resolve",
    "route",
    "schedule",
    "score",
    "screen",
    "send",
    "store",
    "synthesize",
    "track",
    "validate",
    "verify",
    "select",
    "show",
    "submit",
    "view",
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
_ALERT_LIFECYCLE_PATTERN = r"\b(alert|warning|notification|breach|anomaly)\b"


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
        "produced_outputs": f"{_safe_leading_actor(output_focus)}, blocker signal, review-visible rationale, and downstream handoff",
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
    local_text = f"{label_text} {text.split('product behavior:', 1)[0]}"
    front_extras: list[str] = []
    tail_extras: list[str] = []
    label_has_alert = bool(re.search(_ALERT_LIFECYCLE_PATTERN, label_text))
    label_has_model = bool(re.search(r"\b(model|metric|estimator|classifier|trend|health)\b", label_text))
    if label_has_alert or re.search(rf"^\s*owns\s+[^.]*{_ALERT_LIFECYCLE_PATTERN}", text):
        front_extras.extend(("alert event", "threshold signal", "severity state", "acknowledgement state", "alert lifecycle"))
    if label_has_model or (
        not label_has_alert
        and re.search(r"^\s*owns\s+[^.]*\b(model|metric|assessment|estimator|classifier|trend|health)\b", text)
    ):
        front_extras.extend(("model input snapshot", "derived state estimate", "trend signal", "confidence marker", "readiness state"))
    if _is_plan_adjustment_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "plan adjustment request",
                "progress snapshot",
                "status window",
                "plan adjustment state",
                "adjustment rationale",
            )
        )
    if _is_intake_capture_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "intake request",
                "submitted answers",
                "required-input status",
                "validation context",
                "actor identity",
            )
        )
        tail_extras.extend(
            (
                "validated intake request",
                "missing-input blocker",
                "accepted answer set",
                "intake summary",
                "downstream handoff",
            )
        )
    if _is_option_ranking_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "candidate option set",
                "comparison criteria",
                "ranking rule",
                "selected option",
                "ordered alternatives",
            )
        )
        tail_extras.extend(
            (
                "ranked option list",
                "comparison explanation",
                "blocked-selection marker",
                "selection rationale",
                "downstream handoff",
            )
        )
    if _is_external_handoff_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "approved handoff payload",
                "recipient reference",
                "provider status",
                "failed-handoff marker",
                "provider reference",
            )
        )
        tail_extras.extend(
            (
                "provider handoff record",
                "accepted or failed marker",
                "retry blocker",
                "handoff evidence",
                "downstream status handoff",
            )
        )
    if _is_quote_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "quote request",
                "pricing inputs",
                "cost rule",
                "priced option",
                "calculated amount",
            )
        )
        tail_extras.extend(
            (
                "calculated quote",
                "cost breakdown",
                "quote explanation",
                "invalid-quote blocker",
                "pricing provenance reference",
            )
        )
        tail_extras.extend(
            (
                "plan adjustment result",
                "stale-input blocker",
                "input snapshot",
                "confidence marker",
                "downstream handoff",
            )
        )
    if _is_medication_relief_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "medication-taken record",
                "dose-as-recorded value",
                "relief attempt",
                "reminder preference",
                "missed-reminder marker",
                "side-effect note",
                "safety disclaimer marker",
            )
        )
        tail_extras.extend(
            (
                "validated medication fact",
                "relief tracking event",
                "reminder setting state",
                "missed-reminder state",
                "side-effect review marker",
                "downstream handoff",
            )
        )
    if _is_symptom_tracking_context(local_text, action_terms=action_terms):
        front_extras.extend(
            (
                "symptom entry",
                "episode timestamp",
                "intensity rating",
                "body location",
                "trigger note",
                "relief method",
                "medication-taken record",
                "dose-as-recorded value",
                "side-effect note",
            )
        )
        tail_extras.extend(
            (
                "validated symptom entry",
                "timeline event",
                "trend snapshot",
                "correction history",
                "safety disclaimer marker",
                "downstream handoff",
            )
        )
    if "define" in action_terms or re.search(r"\b(criteria|criterion)\b", local_text):
        front_extras.append("criteria definitions")
    if "define" in action_terms or re.search(r"\b(criteria|criterion|protocol|rule|policy|threshold)\b", local_text):
        tail_extras.extend(("protocol version", "rule validity"))
        if re.search(r"\binclusion\b", local_text):
            tail_extras.append("inclusion rules")
        if re.search(r"\bexclusion\b", local_text):
            tail_extras.append("exclusion rules")
        if re.search(r"\bexception\b", local_text):
            tail_extras.append("rule exceptions")
        if re.search(r"\bchange|history|version\b", local_text):
            tail_extras.append("rule-change history")
    assignment_context = bool(
        any(action in action_terms for action in ("assign", "route", "resolve"))
        or re.search(r"\b(assignment|assigned|conflict|routing|assignee eligibility|reviewer eligibility)\b", local_text)
    )
    access_context = bool(
        "grant" in action_terms
        or re.search(r"\b(permission|access|role|visibility|rbac|grant|redaction|subscription|entitlement|paid)\b", local_text)
    )
    if assignment_context:
        front_extras.extend(("assignee eligibility", "assignment routing", "access grants", "conflict constraints", "permission state"))
    elif access_context:
        front_extras.extend(("role policy", "visibility rule", "permission grant", "protected access decision", "audit event"))
    if "import" in action_terms or re.search(r"\b(import|dedupe|deduplicate|duplicate|normalize|metadata|provenance|source record)\b", local_text):
        tail_extras.extend(("source identity", "normalized record", "duplicate signal", "malformed input blocker", "provenance marker"))
    if re.search(r"\b(case\s+workspace|case\s+agenda|case\s+checklist)\b", local_text):
        tail_extras.extend(("case identity", "workspace status", "checklist progress", "actor notes", "readiness marker", "blocked item"))
    if re.search(r"\b(map|location|geospatial|geometry|boundary|overlay|layer|context)\b", local_text):
        tail_extras.extend(("location context", "spatial identity", "boundary geometry", "contextual overlay", "map layer selection", "source freshness"))
    if re.search(r"\b(recommendation|recommended|impact|findings?|summary|analysis|supporting)\b", local_text):
        tail_extras.extend(("recommendation text", "impact findings", "supporting source references", "comparison points", "summary handoff"))
    if re.search(r"\b(feedback|comments?|theme|grouping|cluster|concern)\b", local_text):
        tail_extras.extend(("feedback source", "comment grouping", "theme label", "duplicate marker", "concern summary", "visibility state"))
    followup_action_context = bool(
        re.search(r"\b(follow-up|followup)\b", local_text)
        and re.search(r"\b(action|planner|responsible|due date|blocked action|blocked-action)\b", local_text)
    )
    if followup_action_context:
        tail_extras.extend(("follow-up action", "responsible actor", "due date", "action rationale", "blocked-action marker"))
    if not followup_action_context and re.search(r"\b(questions?|issues?|follow-up|followup|response|answer)\b", local_text):
        tail_extras.extend(("question list", "issue category", "follow-up request", "answer status", "unresolved blocker", "response history"))
    if re.search(r"\b(screen|include|exclude|uncertain|disagreement|resolution)\b", local_text):
        tail_extras.extend(("separate reviewer decisions", "decision reasons", "disagreement markers", "resolution decision", "included-source handoff"))
    if "capture" in action_terms or re.search(r"\b(annotation|extraction|extract|field|source location|missing evidence|document)\b", local_text):
        tail_extras.extend(("source annotations", "extracted fields", "source locations", "missing-evidence blockers", "extraction provenance"))
    if "score" in action_terms or re.search(r"\b(score|scoring|rubric|rating|assessment|quality|required field|validation rule)\b", local_text):
        tail_extras.extend(("review fields", "scoring rubric", "required-field validation", "score inputs", "score outputs"))
    if any(action in action_terms for action in ("synthesize", "export")) or re.search(r"\b(synthesis|table|export|package|report|summary|output|deliverable)\b", local_text):
        tail_extras.extend(("synthesis table", "export package", "source references", "completeness blockers", "release handoff"))
    if "audit" in action_terms or "preserve" in action_terms or re.search(r"\b(audit|trail|version|history|retention|archive|replay)\b", local_text):
        tail_extras.extend(("immutable event history", "version chain", "retention policy state", "audit reconstruction", "replay evidence"))
    if re.search(r"\b(claims?|citations?|lineage|traceability|provenance|references?)\b", local_text):
        tail_extras.extend(("claim-source lineage", "citation set", "source reference history", "provenance marker", "replayable claim version"))
    if re.search(r"\b(dashboard|comparison|compare|readiness|display|current decision|visible blocker)\b", local_text):
        tail_extras.extend(("current decision summary", "comparison display", "review readiness", "visible blockers", "user-facing decision state"))
    if re.search(r"\b(vote|motion|rationale|abstain|abstention|final outcome|approval|denial)\b", local_text):
        tail_extras.extend(("decision rationale", "motion or decision command", "vote outcome", "condition set", "abstention marker", "final outcome state"))
    if "assemble" in action_terms or re.search(r"\b(decision package|approval|final approval|unresolved blocker|reviewer note|rationale)\b", local_text):
        tail_extras.extend(("evidence", "reviewer notes", "unresolved blockers", "final approval state", "decision rationale"))
    return _unique([*front_extras, *object_phrases, *tail_extras])


def _strip_action(value: str) -> str:
    return _clean(re.sub(rf"^(?:{_action_forms_pattern()})\s+", "", value, flags=re.IGNORECASE))


def _strip_source_action(value: str) -> str:
    text = _clean(value)
    if re.match(r"^score\s+outputs?\b", text, flags=re.IGNORECASE):
        return text
    return _strip_action(text)


def _actions(value: str) -> list[str]:
    text = _clean(value).casefold()
    result: list[str] = []
    for verb in _ACTION_VERBS:
        if re.search(rf"\b(?:{_verb_forms_pattern(verb)})\b", text):
            result.append(verb)
    return result


def _action_forms_pattern() -> str:
    forms: list[str] = []
    for verb in _ACTION_VERBS:
        forms.extend(_verb_forms(verb))
    return "|".join(re.escape(form) for form in sorted(set(forms), key=lambda value: (-len(value), value)))


def _verb_forms_pattern(verb: str) -> str:
    return "|".join(re.escape(form) for form in sorted(_verb_forms(verb), key=lambda value: (-len(value), value)))


def _verb_forms(verb: str) -> set[str]:
    forms = {verb, f"{verb}s", f"{verb}es", f"{verb}ed", f"{verb}ing"}
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in {"a", "e", "i", "o", "u"}:
        stem = verb[:-1]
        forms.update({f"{stem}ies", f"{stem}ied"})
    if verb.endswith("e") and len(verb) > 1:
        stem = verb[:-1]
        forms.update({f"{verb}d", f"{stem}ing"})
    return forms


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
    if _mentions_plan_adjustment(object_text):
        return "plan adjustment request, progress snapshot, status window, blocker signal, and prior plan state"
    if _mentions_intake_capture(object_text):
        return "intake request, submitted answers, required fields, actor identity, validation context, and prior intake state"
    if _mentions_option_ranking(object_text):
        return "candidate options, comparison criteria, actor context, ranking command, tie-break rule, and prior selection state"
    if _mentions_external_handoff(object_text):
        return "approved handoff command, actor identity, recipient reference, payload snapshot, provider status, and prior handoff state"
    if _mentions_quote(object_text):
        return "quote request, priced item or option, quantity or usage context, cost rule, actor context, and validation context"
    if _mentions_medication_relief(object_text):
        return "medication fact command, dose-as-recorded value, relief attempt, reminder preference, side-effect note, actor identity, and validation context"
    if _mentions_symptom_tracking(object_text):
        return "symptom entry command, episode timestamp, intensity rating, body location, trigger note, relief method, medication-taken record, and actor identity"
    if "alert event" in object_text or "threshold signal" in object_text:
        return "derived signal, threshold rule, severity input, acknowledgement command, and prior alert state"
    if "model input snapshot" in object_text or "derived state estimate" in object_text:
        return "normalized input snapshot, observed measurements, baseline context, trend source, and confidence rule"
    if "import" in action_terms:
        return "source payload, source timestamp, provenance marker, malformed-input signal, and import request"
    if "assign" in action_terms or "route" in action_terms:
        return "assignee eligibility, role attribute, conflict signal, permission request, and assignment trigger"
    if "grant" in action_terms or re.search(r"\b(access|permission|role|visibility|grant|redaction|subscription|entitlement|paid)\b", object_text):
        return "actor identity, role attribute, visibility rule, access request, protected state reference, and retention rule"
    if "define" in action_terms:
        return "question, rule draft, threshold, policy source, exception note, and prior version"
    if "score" in action_terms:
        return "required fields, scoring rubric version, assessment evidence, score inputs, and reviewer answer"
    if "export" in action_terms or "synthesize" in action_terms:
        return "validated upstream evidence, source references, output format request, and completeness rule"
    if "audit" in action_terms or "preserve" in action_terms:
        return "state change event, actor identity, timestamp, prior version, retention rule, and provenance reference"
    focus = _phrase(object_phrases[:3]) or _clean(previous_label).casefold() or "accepted input"
    return _nominalized_contract_artifact(focus, role="input")


def _output_focus(*, object_phrases: Sequence[str], action_terms: Sequence[str], next_label: str) -> str:
    object_text = " ".join(object_phrases).casefold()
    if _mentions_plan_adjustment(object_text):
        return "plan adjustment result, adjustment rationale, stale-input blocker, input snapshot reference, and confidence marker"
    if _mentions_intake_capture(object_text):
        return "validated intake request, missing-input blocker, accepted answer set, intake summary, and downstream handoff"
    if _mentions_option_ranking(object_text):
        return "ranked option list, selected option, ordered alternatives, comparison explanation, and blocked-selection marker"
    if _mentions_external_handoff(object_text):
        return "provider handoff record, accepted or failed marker, provider reference, retry blocker, and handoff evidence"
    if _mentions_quote(object_text):
        return "calculated quote, cost breakdown, quote explanation, invalid-quote blocker, and pricing provenance reference"
    if _mentions_medication_relief(object_text):
        return "validated medication fact, relief tracking event, reminder setting state, missed-reminder state, safety disclaimer marker, and downstream handoff"
    if _mentions_symptom_tracking(object_text):
        return "validated symptom entry, timeline event, trend snapshot update, correction history, safety disclaimer marker, and downstream handoff"
    if "alert event" in object_text or "threshold signal" in object_text:
        return "alert event, severity state, acknowledgement requirement, resolution blocker, and alert handoff"
    if "model input snapshot" in object_text or "derived state estimate" in object_text:
        return "derived state estimate, trend signal, confidence marker, readiness state, and model handoff"
    if "import" in action_terms:
        return "normalized record, duplicate signal, rejected-input signal, provenance reference, and intake summary"
    if "assign" in action_terms or "route" in action_terms:
        return "assignee selection, access grant or denial, conflict blocker, and assignment handoff"
    if "grant" in action_terms or re.search(r"\b(access|permission|role|visibility|grant|redaction|subscription|entitlement|paid)\b", object_text):
        return "access grant or denial, protected visibility decision, audit entry, retention decision, and replay evidence"
    if "define" in action_terms:
        return "active rule set, versioned protocol, rule validation result, exception blocker, and rule-change handoff"
    if "score" in action_terms:
        return "validated assessment, score output, missing-field blocker, rubric result, and scoring handoff"
    if "export" in action_terms or "synthesize" in action_terms:
        return "synthesis table, exportable package, completeness blocker, evidence summary, and release handoff"
    if "audit" in action_terms or "preserve" in action_terms:
        return "audit entry, version snapshot, retention decision, replay record, and immutable history evidence"
    focus = _phrase(object_phrases[:3]) or _clean(next_label).casefold() or "local result"
    return _nominalized_contract_artifact(focus, role="output")


def _states_for(description: str, *, object_phrases: Sequence[str]) -> str:
    text = " ".join([description, *object_phrases]).casefold()
    if _mentions_plan_adjustment(text):
        return "not-requested, input-ready, computed, stale-input-blocked, adjusted, safety-blocked, accepted, revised, and handed-off"
    if _mentions_intake_capture(text):
        return "not-started, in-progress, submitted, missing-required-input, validation-failed, accepted, corrected, withdrawn, and handed-off"
    if _mentions_option_ranking(text):
        return "empty, candidates-loaded, comparable, ranked, selected, tied, blocked, revised, and handed-off"
    if _mentions_external_handoff(text):
        return "not-requested, ready, sent, accepted, failed, retry-blocked, acknowledged, reconciled, and handed-off"
    if _mentions_quote(text):
        return "not-requested, input-ready, calculated, invalid-input-blocked, stale, revised, accepted, expired, and handed-off"
    if _mentions_medication_relief(text):
        return "not-recorded, recorded, validated, corrected, reminder-disabled, reminder-set, missed, side-effect-noted, safety-blocked, and handed-off"
    if _mentions_symptom_tracking(text):
        return "draft, recorded, validated, corrected, deleted, blocked, stale, visible-on-timeline, and handed-off"
    if re.search(r"\b(?:model input snapshot|derived state estimate|confidence marker|readiness state)\b", text):
        return "not-calculated, input-ready, calculated, low-confidence, stale, overridden, and handed-off"
    if re.search(r"\b(?:alert event|threshold signal|severity state|acknowledgement state|alert lifecycle)\b", text):
        return "not-triggered, triggered, acknowledged, escalated, suppressed, resolved, stale, and handed-off"
    if re.search(r"\b(?:access grant|protected visibility|permission grant|role policy|visibility rule|redaction|subscription|entitlement)\b", text):
        return "requested, granted, denied, redacted, recorded, retained, expired, restored, and audit-blocked"
    if re.search(r"\b(?:assign|assignment|conflict|route|routing|assignee eligibility|reviewer eligibility)\b", text):
        return "unassigned, eligible, assigned, access-granted, access-denied, conflict-blocked, and reassigned"
    if re.search(r"\b(?:criteria|protocol|rule|policy|threshold|definition)\b", text):
        return "draft, active, revised, superseded, exception-blocked, invalid-rule, and retired"
    if re.search(r"\b(?:claim-source lineage|citation set|source reference history|replayable claim)\b", text):
        return "uncited, cited, source-linked, disputed, versioned, replayed, retained, missing-source-blocked, and handed-off"
    if re.search(r"\b(?:import|dedupe|duplicate|normalize|metadata|source identity|source payload)\b", text):
        return "not-imported, imported, normalized, duplicate-found, rejected, quarantined, provenance-attached, and handed-off"
    if re.search(r"\b(?:case identity|workspace status|checklist progress|actor notes|readiness marker)\b", text):
        return "not-started, opened, in-review, noted, blocked, ready, revised, decided, closed, and handed-off"
    if re.search(r"\b(?:location context|spatial identity|boundary geometry|contextual overlay|map layer)\b", text):
        return "unlocated, located, layer-selected, source-stale, missing-context, context-ready, revised, and handed-off"
    if re.search(r"\b(?:recommendation text|impact findings|comparison points|summary handoff)\b", text):
        return "draft, source-linked, incomplete, ready-for-comparison, disputed, revised, accepted-for-decision, and handed-off"
    if re.search(r"\b(?:feedback source|comment grouping|theme label|concern summary)\b", text):
        return "received, grouped, duplicate-marked, hidden-by-policy, source-linked, disputed, summarized, and handed-off"
    if re.search(r"\b(?:question list|issue category|follow-up request|answer status|unresolved blocker)\b", text):
        return "draft, open, assigned, answered, unresolved, escalated, closed, stale, and handed-off"
    if re.search(r"\b(?:screen|include|exclude|disagree|resolution)\b", text):
        return "not-screened, in-review, included, excluded, disagreed, resolution-needed, resolved, and handed-off"
    if re.search(r"\b(?:extract|annotation|document|field|missing)\b", text):
        return "not-started, annotated, extracted, missing-evidence, validation-failed, revised, source-linked, and handed-off"
    if re.search(r"\b(?:score|rubric|assessment|rating|quality)\b", text):
        return "not-started, in-progress, missing-required-field, validation-failed, scored, revised, and submitted"
    if re.search(r"\b(?:decision rationale|motion or decision command|vote outcome|abstention marker)\b", text):
        return "draft, ready-for-decision, blocked, approved, denied, conditioned, abstained, finalized, and handed-off"
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
        "refused domain responsibilities: sibling-owned product responsibilities",
        "forbidden runtime authorities: upstream source truth",
        "release approval",
        "runtime implementation outside the accepted proof boundary",
    ]
    if sibling_focus:
        base.insert(1, f"sibling-owned state: {sibling_focus} owned by the sibling component")
    return "; ".join(base)


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
    focus_text = " ".join((object_list, critical, input_focus, output_focus, source_fact)).casefold()
    if _mentions_plan_adjustment(focus_text):
        rows = [
            f"Plan adjustment proof covers {input_focus}, {output_focus}, rationale visibility, and downstream handoff.",
            "Invalid input proof blocks downstream handoff when progress, status, actor, validation, or prior plan evidence is missing or stale.",
            "Provenance proof links the plan adjustment result to input snapshot, validation context, and review-visible rationale.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating plan adjustment state owned by {label}.")
        else:
            rows.append(f"Boundary proof keeps {label} separate from release approval and upstream source truth.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if _mentions_intake_capture(focus_text):
        rows = [
            f"Intake proof covers {input_focus}, {output_focus}, blocker state, and downstream handoff.",
            "Invalid input proof blocks downstream handoff when submitted answers, actor context, required fields, or validation evidence is missing or stale.",
            "Boundary proof keeps downstream calculation, ranking, decision, notification, and audit changes from rewriting the accepted intake answer set.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating intake state owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if _mentions_option_ranking(focus_text):
        rows = [
            f"Ranking proof covers {input_focus}, {output_focus}, explanation visibility, and downstream handoff.",
            "Invalid ranking proof blocks selection when candidates, comparison criteria, tie-break rule, or eligibility evidence is missing or stale.",
            "Boundary proof keeps intake, quote calculation, final commitment, and audit changes from rewriting ranking state or selection rationale.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating ranking state owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if _mentions_external_handoff(focus_text):
        rows = [
            f"Handoff proof covers {input_focus}, {output_focus}, provider acknowledgement, failure visibility, and downstream status handoff.",
            "Invalid handoff proof blocks downstream state when approval, recipient, payload, actor authority, or provider status is missing or stale.",
            "Boundary proof keeps upstream approval, provider execution, notification, and audit changes from rewriting handoff payload or failure evidence.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating handoff state owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if _mentions_quote(focus_text):
        rows = [
            f"Quote proof covers {input_focus}, {output_focus}, explanation visibility, and downstream handoff.",
            "Invalid quote proof blocks calculated output when price inputs, usage context, actor authority, validation context, or cost rules are missing or stale.",
            "Provenance proof links the calculated quote to pricing inputs, cost rule, validation context, and explanation.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating quote state owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if _mentions_medication_relief(focus_text):
        rows = [
            f"Medication fact proof covers {input_focus}, {output_focus}, correction handling, reminder visibility, and downstream handoff.",
            "Invalid medication proof blocks downstream use when actor, dose-as-recorded value, timestamp, side-effect note, reminder preference, or safety disclaimer evidence is missing or stale.",
            "Safety proof records medication facts exactly as user-entered while refusing diagnosis, prescribing, medication dosing advice, and emergency-care authority.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating medication and relief state owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if _mentions_symptom_tracking(focus_text):
        rows = [
            f"Symptom entry proof covers {input_focus}, {output_focus}, timeline visibility, correction history, and downstream handoff.",
            "Invalid health-entry proof blocks downstream trend or summary state when intensity, timestamp, actor, medication fact, validation context, or safety disclaimer evidence is missing or stale.",
            "Safety proof keeps user-entered medication facts separate from diagnosis, prescribing, dosing advice, and emergency escalation handling.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating symptom-entry state owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if re.search(r"\b(audit entry|version snapshot|immutable event history|audit reconstruction|replay evidence)\b", focus_text):
        rows = [
            f"Audit proof covers {input_focus}, {output_focus}, replay evidence, and downstream handoff.",
            "Invalid audit proof blocks release review when actor, timestamp, prior version, retention rule, or provenance is missing.",
            "Replay proof reconstructs state changes from immutable history without relying on dashboard or summary text.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating audit history owned by {label}.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    if re.search(r"\b(privacy|deletion|delete|protected-data|consent)\b", focus_text) or (
        re.search(r"\bexport\b", focus_text)
        and re.search(r"\b(data|privacy|protected|consent|retention|deletion|delete)\b", focus_text)
    ) or (
        "retention" in focus_text and re.search(r"\b(protected|privacy|consent|delete|deletion|export)\b", focus_text)
    ):
        rows = [
            f"Privacy lifecycle proof shows actor identity, consent history, protected-state reference, retention rule, lifecycle decision, and audit event for {label}.",
            "Deletion block proof keeps protected state unchanged when consent, retention, actor authority, or policy blocks the request.",
            "Lifecycle replay proof reconstructs requested, allowed, exported, deletion-pending, deleted, retained, restored, blocked, and handed-off states.",
        ]
        if sibling_label and sibling_focus:
            rows.append(f"Boundary proof keeps {sibling_label} from mutating privacy lifecycle state owned by {label}.")
        else:
            rows.append(f"Boundary proof keeps privacy lifecycle authority separate from domain guidance, analytics, release approval, and upstream source truth.")
        return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))
    rows = [
        f"{label} proof covers {_safe_leading_actor(object_list)}, {_safe_leading_actor(input_focus)}, {_safe_leading_actor(output_focus)}, blocker state, and downstream handoff.",
        f"Invalid input proof blocks downstream handoff when {_safe_leading_actor(critical)} is missing, malformed, stale, or assigned to the wrong boundary.",
    ]
    if source_fact and source_fact != object_list:
        rows.append(f"{label} preserves {_safe_leading_actor(source_fact)} as component-local state.")
    if sibling_label and sibling_focus:
        rows.append(f"{label} refuses {sibling_label} ownership over {sibling_focus}.")
    else:
        rows.append(f"{label} keeps its local proof separate from release approval and upstream source truth.")
    return tuple(_clean(row).rstrip(".") for row in rows if _clean(row))


def _is_plan_adjustment_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if any(action in action_terms for action in ("adjust", "calculate", "compute", "recommend", "recompute")) and re.search(
        r"\b(target|goal|plan|recommendation|progress|status)\b",
        lowered,
    ):
        return True
    return bool(
        re.search(r"\b(recompute|recomputed|adjustment|adjustments|computed|calculated)\b", lowered)
        and re.search(r"\b(target|goal|plan|recommendation|guidance)\b", lowered)
    )


def _is_intake_capture_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if any(action in action_terms for action in ("accept", "capture", "record")) and re.search(
        r"\b(intake|form|answer|answers|request|entry|input|required field|submitted)\b",
        lowered,
    ):
        return not re.search(r"\b(import|ingestion|dedupe|duplicate|normalize|metadata)\b", lowered)
    return bool(
        re.search(r"\b(intake|submitted answers|required-input|accepted answer set)\b", lowered)
        and not re.search(r"\b(import|ingestion|dedupe|duplicate|normalize|metadata)\b", lowered)
    )


def _is_option_ranking_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if any(action in action_terms for action in ("compare", "rank", "select", "order")):
        return bool(re.search(r"\b(options?|choices?|alternatives?|candidates?|comparison|ranking|selection)\b", lowered))
    return bool(re.search(r"\b(candidate option set|comparison criteria|ranked option|ordered alternatives|selected option)\b", lowered))


def _is_quote_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if any(action in action_terms for action in ("calculate", "compute", "price")):
        return bool(re.search(r"\b(price|pricing|quote|cost|estimate|rate|amount|charge)\b", lowered))
    return bool(re.search(r"\b(quote request|pricing inputs|cost rule|calculated quote|cost breakdown)\b", lowered))


def _is_external_handoff_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if re.match(r"^[^.]{0,90}\b(handoff|provider|delivery|fulfillment)\b", lowered):
        return True
    return bool(
        re.search(r"\b(approved handoff|provider|recipient|endpoint|fulfillment|delivery|dispatch|failed-handoff|external handoff)\b", lowered)
        and not re.search(r"\b(ranking|ranked|comparison criteria|candidate option|selected option)\b", lowered)
    )


def _is_symptom_tracking_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if any(action in action_terms for action in ("capture", "record", "track", "log", "edit")) and re.search(
        r"\b(symptom|pain|episode|intensity|body location|relief|medication|dose|side effect|trigger)\b",
        lowered,
    ):
        return True
    return bool(
        re.search(
            r"\b(symptom entry|pain entry|pain episode|intensity rating|body location|relief method|medication-taken|dose-as-recorded|timeline event)\b",
            lowered,
        )
    )


def _is_medication_relief_context(text: str, *, action_terms: Sequence[str]) -> bool:
    lowered = _clean(text).casefold()
    if re.search(r"\b(?:pain|symptom)\s+entry\b|\bentry\s+capture\b", lowered) and not re.search(
        r"\b(reminder|dose|dosage|side effect)\b",
        lowered,
    ):
        return False
    if re.search(r"\b(reminder|reminders|missed reminder|side effect|dose|dosage)\b", lowered) and re.search(
        r"\b(medication|medicine|relief|reminder|dose|side effect)\b",
        lowered,
    ):
        return True
    if "medication" in lowered and "relief" in lowered:
        return True
    return bool(
        any(action in action_terms for action in ("record", "track"))
        and re.search(r"\b(medication|medicine|relief|dose|side effect|reminder)\b", lowered)
    )


def _mentions_plan_adjustment(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(
        re.search(r"\b(?:plan|target)\s+adjustment\b", lowered)
        or (
            re.search(r"\b(recompute|computed|adjustment|calculated)\b", lowered)
            and re.search(r"\b(target|plan|goal|recommendation)\b", lowered)
        )
    )


def _mentions_intake_capture(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(re.search(r"\b(intake request|submitted answers|required-input|accepted answer set|validated intake)\b", lowered))


def _mentions_option_ranking(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(re.search(r"\b(candidate option set|comparison criteria|ranking rule|selected option|ordered alternatives|ranked option list)\b", lowered))


def _mentions_quote(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(re.search(r"\b(quote request|pricing inputs|cost rule|calculated amount|calculated quote|cost breakdown|quote explanation)\b", lowered))


def _mentions_external_handoff(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(
        re.search(
            r"\b(approved handoff payload|provider status|failed-handoff marker|provider handoff record|recipient reference|retry blocker|handoff evidence)\b",
            lowered,
        )
    )


def _mentions_symptom_tracking(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(
        re.search(
            r"\b(symptom entry|pain entry|pain episode|episode timestamp|intensity rating|body location|relief method|medication-taken record|dose-as-recorded|timeline event|trend snapshot)\b",
            lowered,
        )
    )


def _mentions_medication_relief(text: str) -> bool:
    lowered = _clean(text).casefold()
    return bool(
        re.search(
            r"\b(medication-taken record|dose-as-recorded|relief attempt|reminder preference|missed-reminder|side-effect|validated medication fact|relief tracking event|reminder setting state)\b",
            lowered,
        )
    )


def _nominalized_contract_artifact(value: str, *, role: str) -> str:
    """Turn capability phrases into artifact nouns before slot rendering."""

    text = _safe_leading_actor(_clean(value).casefold())
    if not text:
        return "accepted input" if role == "input" else "local result"
    stripped = _strip_action(text)
    if stripped != text:
        text = stripped
    if _mentions_plan_adjustment(text):
        if role == "input":
            return "plan adjustment request, progress snapshot, status window, blocker signal, and prior plan state"
        return "plan adjustment result, adjustment rationale, stale-input blocker, input snapshot reference, and confidence marker"
    if _mentions_external_handoff(text):
        if role == "input":
            return "approved handoff command, actor identity, recipient reference, payload snapshot, provider status, and prior handoff state"
        return "provider handoff record, accepted or failed marker, provider reference, retry blocker, and handoff evidence"
    if _mentions_medication_relief(text):
        if role == "input":
            return "medication fact command, dose-as-recorded value, relief attempt, reminder preference, side-effect note, actor identity, and validation context"
        return "validated medication fact, relief tracking event, reminder setting state, missed-reminder state, safety disclaimer marker, and downstream handoff"
    if _mentions_symptom_tracking(text):
        if role == "input":
            return "symptom entry command, episode timestamp, intensity rating, body location, trigger note, relief method, medication-taken record, and actor identity"
        return "validated symptom entry, timeline event, trend snapshot update, correction history, safety disclaimer marker, and downstream handoff"
    if role == "input":
        if re.search(r"\b(input|request|snapshot|context|command|payload|event|signal|reference)\b", text):
            return text
        return f"{text} request"
    if re.search(r"\b(result|output|decision|package|record|entry|summary|marker|handoff|snapshot|reference)\b", text):
        return text
    return f"{text} result"


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
