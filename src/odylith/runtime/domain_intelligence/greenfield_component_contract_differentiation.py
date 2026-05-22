"""Differentiate overlapping greenfield component contracts before writes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_contract import (
    boundary_from_contract,
    dependencies_from_contract,
    interfaces_from_contract,
    responsibility_from_contract,
    risks_from_contract,
    validation_from_contract,
)
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    normalize_contract,
    ordered_domain_terms,
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_semantic_contract import (
    derive_component_semantic_contract,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.governance.component_spec_rendering import build_component_spec


@dataclass(frozen=True)
class _Axis:
    key: str
    triggers: tuple[str, ...]
    owned_state: str
    accepted_inputs: str
    produced_outputs: str
    states_or_transitions: str
    outside_boundary: str
    local_proof: tuple[str, ...]
    unique_failure: str


_AXES: tuple[_Axis, ...] = (
    _Axis(
        key="submission_versioning",
        triggers=(
            "submission",
            "submit",
            "intake",
            "version",
            "versioning",
            "file",
            "upload",
        ),
        owned_state="submitted item identity, intake status, actor-supplied payload, file set, version chain, missing-field blocker, and intake handoff state",
        accepted_inputs="submitting actor identity, submitted payload, uploaded files, metadata, version reference, required-field answers, and intake command",
        produced_outputs="accepted submission, version snapshot, missing-input blocker, rejected intake signal, file association, and downstream review handoff",
        states_or_transitions="draft, submitted, validation-failed, missing-required-input, versioned, withdrawn, accepted-for-review, and handed-off",
        outside_boundary="assignment routing, permission grants, scoring rubric ownership, decision comparison, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "A submitted item carries the right actor, payload, file set, metadata, and version before downstream review begins.",
            "Missing required intake data blocks submission instead of creating trusted downstream state.",
            "Assignment, scoring, notification, and final decision changes do not mutate intake identity or version history.",
        ),
        unique_failure="A submitted item can enter review with the wrong identity, missing files, stale metadata, or an incorrect version snapshot.",
    ),
    _Axis(
        key="definition_rules",
        triggers=(
            "criteria",
            "criterion",
            "protocol",
            "rule",
            "definition",
            "eligibility",
            "inclusion",
            "exclusion",
            "threshold",
            "policy",
        ),
        owned_state="criteria definitions, protocol version, inclusion and exclusion rules, rule validity, exception notes, and rule-change history",
        accepted_inputs="domain question, rule draft, threshold, policy source, exception note, actor identity, and prior protocol version",
        produced_outputs="active criteria set, protocol version, rule validation result, exception blocker, and rule-change handoff",
        states_or_transitions="draft, active, revised, superseded, exception-blocked, invalid-rule, and retired",
        outside_boundary="assignment routing, permission grants, independent review decisions, evidence extraction, scoring output, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Criteria and protocol rules are versioned before downstream decisions use them.",
            "Invalid or missing rules block downstream review instead of creating trusted decisions.",
            "Changing assignment routing does not mutate criteria or protocol state.",
        ),
        unique_failure="The wrong rule version can drive downstream decisions, an invalid criterion can look active, or a protocol change can lose its audit context.",
    ),
    _Axis(
        key="intake_import",
        triggers=("ingestion", "ingest", "import", "deduplication", "dedupe", "citation", "metadata", "intake", "normalize", "record"),
        owned_state="import batch, source identity, normalized record, duplicate match, rejected input, provenance marker, and intake handoff state",
        accepted_inputs="source payload, import file, source timestamp, actor identity, deduplication key, normalization rule, and upstream source metadata",
        produced_outputs="normalized record, duplicate or rejected-input signal, provenance reference, import summary, and downstream intake handoff",
        states_or_transitions="not-imported, imported, normalized, duplicate-found, rejected, quarantined, provenance-attached, and handed-off",
        outside_boundary="criteria definition, assignment routing, review decisions, evidence extraction, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Accepted source input produces a normalized record with provenance.",
            "Duplicates and malformed inputs are rejected or quarantined before downstream state changes.",
            "Import provenance remains visible after handoff.",
        ),
        unique_failure="A duplicate or malformed source record can be trusted as new, provenance can be lost, or downstream review can use the wrong source identity.",
    ),
    _Axis(
        key="condition_model",
        triggers=("model", "profile", "health", "condition", "trend", "telemetry", "signal", "summary", "classification"),
        owned_state="derived condition model, measurement summary, trend signal, confidence marker, readiness classification, model input version, and model handoff state",
        accepted_inputs="normalized observations, prior state, measurement summary, inspection notes, model rule version, actor identity, and validation context",
        produced_outputs="condition profile, trend classification, confidence result, model blocker, readiness signal, and downstream alert or decision handoff",
        states_or_transitions="unmodeled, input-ready, modeled, low-confidence, trend-detected, validation-failed, classified, and handed-off",
        outside_boundary="raw source import, alert acknowledgement, operational decision authority, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "Accepted observations produce a derived condition profile with confidence and model-input provenance.",
            "Missing or invalid observations block model readiness instead of creating a trusted condition result.",
            "Alert, notification, and decision changes do not mutate the model input version or derived classification.",
        ),
        unique_failure="A stale or low-confidence model output can look ready, a condition trend can detach from its source inputs, or a downstream decision can trust an invalid classification.",
    ),
    _Axis(
        key="alert_signal",
        triggers=("alert", "warning", "degradation", "anomaly", "threshold", "flag", "indicator", "loss", "risk"),
        owned_state="alert rule, threshold evaluation, signal severity, warning state, acknowledgement marker, alert evidence, and escalation handoff state",
        accepted_inputs="condition signal, threshold rule, severity policy, source evidence, actor acknowledgement, prior alert state, and escalation trigger",
        produced_outputs="alert event, warning severity, acknowledged or blocked marker, escalation signal, alert evidence record, and downstream action handoff",
        states_or_transitions="inactive, evaluating, triggered, acknowledged, escalated, suppressed, stale, cleared, and handed-off",
        outside_boundary="raw source import, derived model ownership, final action decision, dashboard ranking, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "A qualifying signal creates an alert with threshold evidence, severity, and acknowledgement state.",
            "A stale, suppressed, or missing signal cannot appear as a current actionable warning.",
            "Model recalculation and final action decisions do not rewrite the alert event history.",
        ),
        unique_failure="A serious signal can fail to alert, a stale warning can look current, or an alert can lose the evidence needed for a safe downstream action.",
    ),
    _Axis(
        key="action_decision",
        triggers=("maintenance", "action", "recommendation", "clearance", "resolve", "resolution"),
        owned_state="action recommendation, decision rationale, approval or blocked outcome, required follow-up, responsible actor, and decision handoff evidence",
        accepted_inputs="condition profile, alert evidence, actor identity, policy constraint, decision command, unresolved blocker, and prior action state",
        produced_outputs="action decision, blocked or approved outcome, rationale note, follow-up requirement, reviewer-visible decision evidence, and release handoff",
        states_or_transitions="draft, review-ready, blocked, approved, rejected, watched, deferred, completed, and handed-off",
        outside_boundary="raw source import, model calculation, alert triggering, notification delivery, immutable audit retention, and sibling product responsibilities",
        local_proof=(
            "The action decision shows source condition, alert evidence, responsible actor, rationale, and final outcome.",
            "Unresolved blockers prevent an approved or cleared outcome from appearing final.",
            "Source import, model, and alert state changes do not silently rewrite the recorded decision rationale.",
        ),
        unique_failure="A decision can appear approved while blockers remain unresolved, the rationale can detach from evidence, or a follow-up requirement can disappear.",
    ),
    _Axis(
        key="assignment_permission",
        triggers=("assignment", "assign", "reviewer", "permission", "access", "role", "routing", "conflict", "grant"),
        owned_state="assignment reviewer eligibility, assignment routing, access grants, conflict constraints, permission state, and assignment state",
        accepted_inputs="assignment reviewer role, availability, conflict signal, permission request, source actor, and review assignment trigger",
        produced_outputs="assignment reviewer selection, permission decision, access grant or denial, conflict blocker, and assignment handoff",
        states_or_transitions="unassigned, eligible, assigned, access-granted, access-denied, conflict-blocked, and reassigned",
        outside_boundary="criteria definition, form layout, scoring rubric, score calculation, immutable audit storage, comparison dashboard, and sibling product responsibilities",
        local_proof=(
            "The right reviewer is assigned, permission limits are applied, and conflicts block assignment.",
            "A reviewer without permission cannot access or mutate the assigned review.",
            "Missing eligibility creates an assignment blocker instead of a valid assignment.",
        ),
        unique_failure="The wrong reviewer can receive access, a conflict can be hidden, or an unauthorized assignment can look valid.",
    ),
    _Axis(
        key="access_audit",
        triggers=("access", "permission", "role", "visibility", "rbac", "audit", "trail", "history", "retention"),
        owned_state="role policy, visibility rule, permission grant, protected access decision, audit event, version reference, and history retention state",
        accepted_inputs="actor identity, role attribute, visibility rule, access request, protected state reference, state-change event, timestamp, and retention rule",
        produced_outputs="access grant or denial, protected visibility decision, audit entry, version snapshot, retention decision, and replay evidence",
        states_or_transitions="requested, granted, denied, redacted, recorded, versioned, retained, expired, restored, and audit-blocked",
        outside_boundary="submission intake, reviewer selection, scoring rubric ownership, dashboard ranking, notification delivery, final decision authority, and sibling product responsibilities",
        local_proof=(
            "Only authorized actors can view or mutate protected state, and every access decision is replayable.",
            "A denied or redacted view blocks protected data exposure while preserving an audit entry.",
            "Audit history can reconstruct changes without rewriting sibling workflow or dashboard state.",
        ),
        unique_failure="Protected state can be exposed to the wrong actor, a permission decision can be untraceable, or retention can erase required audit evidence.",
    ),
    _Axis(
        key="screening_decision",
        triggers=("screening", "screen", "independent", "decision", "disagreement", "resolve", "resolution", "include", "exclude"),
        owned_state="independent review decision, reviewer response, disagreement marker, resolution reason, decision status, and decision handoff evidence",
        accepted_inputs="assigned item, active criteria version, reviewer identity, review answer, exclusion reason, disagreement signal, and resolution action",
        produced_outputs="screening decision, disagreement blocker, resolved outcome, decision reason, and downstream review handoff",
        states_or_transitions="not-screened, in-review, included, excluded, disagreed, resolution-needed, resolved, and handed-off",
        outside_boundary="criteria definition, assignment routing, permission grants, evidence extraction, scoring rubric ownership, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Independent decisions remain separate until a resolution reason is recorded.",
            "A disagreement blocks downstream completion until the resolution action is traceable.",
            "Changing criteria or assignment state does not silently rewrite recorded decisions.",
        ),
        unique_failure="A disagreement can disappear, an exclusion reason can be lost, or a downstream handoff can treat unresolved decisions as final.",
    ),
    _Axis(
        key="evidence_extraction",
        triggers=("annotation", "annotate", "extraction", "extract", "evidence", "field", "pdf", "document", "capture", "source"),
        owned_state="source annotation, extracted field, evidence reference, source location, missing-evidence blocker, extraction version, and handoff history",
        accepted_inputs="included source, source document, actor identity, extraction field definition, annotation target, evidence text, and provenance reference",
        produced_outputs="validated extraction field, annotation record, missing-evidence blocker, source reference, and downstream assessment handoff",
        states_or_transitions="not-started, annotated, extracted, missing-evidence, validation-failed, revised, source-linked, and handed-off",
        outside_boundary="criteria definition, assignment routing, screening inclusion decisions, score calculation, synthesis conclusions, and sibling product responsibilities",
        local_proof=(
            "Extracted fields stay attached to their source location and actor.",
            "Missing evidence blocks downstream assessment instead of producing trusted output.",
            "Screening decisions do not rewrite extraction provenance.",
        ),
        unique_failure="Evidence can be extracted from the wrong source, a missing field can pass as complete, or provenance can detach from the downstream claim.",
    ),
    _Axis(
        key="decision_review",
        triggers=("decision", "approval", "approve", "package", "blocker", "note", "readiness", "final", "outcome", "compare", "comparison"),
        owned_state="decision evidence package, reviewer notes, unresolved blockers, final approval state, decision readiness, and decision rationale",
        accepted_inputs="assembled evidence, reviewer note, blocker state, actor identity, readiness signal, approval command, and prior decision state",
        produced_outputs="decision package, approval or blocked outcome, reviewer-visible rationale, final decision state, and release handoff",
        states_or_transitions="draft, review-ready, blocked, returned, approved, rejected, finalized, and handed-off",
        outside_boundary="criteria definition, assignment routing, permission grants, revision intake, raw evidence extraction, scoring rubric ownership, immutable audit storage, and sibling product responsibilities",
        local_proof=(
            "The decision package shows evidence, reviewer notes, unresolved blockers, and final approval state before release handoff.",
            "Unresolved blockers prevent an approval outcome from appearing final.",
            "Changing upstream revision, assignment, or extraction state does not silently rewrite the recorded decision rationale.",
        ),
        unique_failure="A decision can appear approved while blockers remain unresolved, reviewer rationale can detach from evidence, or a final outcome can hide missing review context.",
    ),
    _Axis(
        key="form_scoring",
        triggers=("form", "scoring", "score", "template", "rubric", "assessment", "rating", "quality", "bias", "question"),
        owned_state="review fields, scoring rubric, scoring templates, validation rules, scoring inputs, and score outputs",
        accepted_inputs="review evidence, reviewer answers, rubric version, required fields, score input, and validation context",
        produced_outputs="validated review form, score output, missing-field blocker, rubric result, and scoring evidence handoff",
        states_or_transitions="not-started, in-progress, missing-required-field, validation-failed, scored, revised, and submitted",
        outside_boundary="form layout outside the scoring fields, reviewer assignment, assignment routing, permission grants, immutable audit storage, retention enforcement, dashboard ranking, and sibling product responsibilities",
        local_proof=(
            "Required review fields and rubric inputs produce the expected score output.",
            "Missing required fields block submission before a score is trusted.",
            "The scoring surface refuses reviewer assignment and permission grants while keeping rubric validation separate.",
            "Changing assignment or permission state does not mutate the scoring template.",
        ),
        unique_failure="A missing required field can be scored, the wrong rubric version can be used, or a score can be trusted without validation evidence.",
    ),
    _Axis(
        key="revision_lifecycle",
        triggers=("revision", "round", "resubmission", "revise", "changes", "response", "return", "requested"),
        owned_state="revision round, requested-change set, actor response, resubmission version, round deadline, unresolved revision blocker, and decision handoff state",
        accepted_inputs="prior decision, requested changes, actor identity, revised payload, response notes, deadline rule, and previous version reference",
        produced_outputs="revision request, resubmission snapshot, response package, round status, unresolved-change blocker, and downstream decision handoff",
        states_or_transitions="not-requested, requested, awaiting-response, resubmitted, under-review, incomplete, accepted, rejected, and handed-off",
        outside_boundary="initial submission identity, assignment routing, scoring rubric ownership, immutable audit retention, notification delivery, dashboard ranking, and sibling product responsibilities",
        local_proof=(
            "A requested change produces a traceable revision round with response notes and a resubmission version.",
            "Incomplete responses block the revision round before a downstream decision can treat it as ready.",
            "Initial intake, assignment, scoring, and audit records remain separate from revision-round state.",
        ),
        unique_failure="A revision round can lose the requested change, attach the wrong resubmission version, or make an incomplete actor response look decision-ready.",
    ),
    _Axis(
        key="notification_deadline",
        triggers=("notification", "notify", "deadline", "reminder", "due", "overdue", "email", "alert", "escalation"),
        owned_state="deadline rule, due date, reminder schedule, notification delivery request, delivery status, overdue marker, escalation state, and stale-work signal",
        accepted_inputs="lifecycle event, actor contact reference, deadline policy, due date, reminder preference, delivery provider status, and escalation trigger",
        produced_outputs="notification request, delivered or failed marker, overdue indicator, reminder event, escalation signal, and freshness handoff",
        states_or_transitions="scheduled, pending, sent, failed, acknowledged, overdue, escalated, stale, and resolved",
        outside_boundary="submission intake, assignment routing, scoring rubric ownership, final decision state, immutable audit retention, dashboard query ownership, and sibling product responsibilities",
        local_proof=(
            "A lifecycle event creates the right deadline, reminder, delivery status, and overdue marker.",
            "Failed or missing delivery leaves visible stale-work evidence instead of pretending the actor was notified.",
            "Deadline and notification changes do not mutate the underlying submission, review, score, or decision state.",
        ),
        unique_failure="A required actor can miss a deadline silently, a stale item can look current, or a failed notification can be treated as delivered.",
    ),
    _Axis(
        key="search_status_view",
        triggers=("search", "filter", "filtering", "dashboard", "dashboards", "status", "view", "queue", "list"),
        owned_state="search query, filter set, result list, status facet, visible dashboard state, next-action summary, blocked or stale indicator, and role-appropriate read model",
        accepted_inputs="indexed product state, status event, actor role, filter criteria, search query, blocker marker, freshness timestamp, and read-model request",
        produced_outputs="filtered result set, status summary, dashboard view, blocked or stale indicator, role-appropriate next action, and read-model handoff",
        states_or_transitions="empty, filtered, sorted, stale, blocked, needs-action, hidden-by-role, visible, refreshed, and exported",
        outside_boundary="submission mutation, assignment routing, scoring calculation, final decision authority, immutable audit retention, notification delivery, and sibling product responsibilities",
        local_proof=(
            "The dashboard renders filtered results, status facets, blocked or stale indicators, and next actions from current product state.",
            "Role-inappropriate or stale data is hidden or marked instead of appearing as current actionable truth.",
            "Search, filtering, and display changes do not mutate submission, assignment, scoring, decision, or audit ownership.",
        ),
        unique_failure="A stale or unauthorized dashboard view can look current, a blocked item can disappear from the queue, or search output can imply a decision that another component owns.",
    ),
    _Axis(
        key="synthesis_export",
        triggers=("synthesis", "table", "export", "package", "report", "summary", "output", "deliverable"),
        owned_state="synthesis table, export package, included evidence summary, output format, completeness marker, and release handoff evidence",
        accepted_inputs="validated evidence, assessment result, source references, actor identity, output format request, and completeness rule",
        produced_outputs="synthesis table, exportable package, completeness blocker, evidence summary, and release proof handoff",
        states_or_transitions="not-started, draft, incomplete, ready-for-export, exported, blocked, revised, and accepted",
        outside_boundary="source ingestion, criteria definition, assignment routing, raw extraction ownership, immutable audit storage, and sibling product responsibilities",
        local_proof=(
            "Synthesis output includes only validated upstream evidence.",
            "Incomplete evidence blocks export instead of creating a trusted package.",
            "Export format changes do not mutate upstream decisions or extraction state.",
        ),
        unique_failure="An export can omit required evidence, summarize unvalidated inputs, or make an incomplete synthesis look release-ready.",
    ),
    _Axis(
        key="dashboard_comparison",
        triggers=("dashboard", "comparison", "compare", "summary", "readiness", "display"),
        owned_state="current decision summary, comparison display, review readiness, user-facing decision state, visible blockers, and comparison filters",
        accepted_inputs="review status, score output, assignment status, evidence references, comparison criteria, and user role context",
        produced_outputs="decision summary, comparison view, readiness indicator, visible blocker, and user-facing next action",
        states_or_transitions="ready, blocked, needs-review, comparable, not-comparable, changed, and decided",
        outside_boundary="immutable audit storage, version chain, retention enforcement, scoring rubric ownership, permission grants, and sibling product responsibilities",
        local_proof=(
            "The dashboard shows the current decision summary, comparison display, readiness state, and blocker.",
            "A blocked or incomplete review cannot appear ready for decision.",
            "Audit retention or immutable history changes do not mutate the comparison view.",
        ),
        unique_failure="A stale summary can look current, an incomplete review can appear ready, or comparison output can hide the blocker behind a decision view.",
    ),
    _Axis(
        key="audit_retention",
        triggers=("audit", "trail", "version", "history", "retention", "archive", "provenance"),
        owned_state="immutable event history, version chain, retention policy state, audit reconstruction, change provenance, and replay evidence",
        accepted_inputs="state change event, actor identity, timestamp, prior version, retention rule, and provenance reference",
        produced_outputs="audit entry, version snapshot, retention decision, replay record, and immutable history evidence",
        states_or_transitions="recorded, versioned, retained, expired, restored, replayed, and audit-blocked",
        outside_boundary="dashboard ranking, comparison display, current decision summary, scoring rubric ownership, permission grants, and sibling product responsibilities",
        local_proof=(
            "Every state change creates an immutable audit entry with actor, timestamp, prior version, and provenance.",
            "Retention rules keep or expire history without changing the current decision view.",
            "Audit replay reconstructs the decision history without relying on dashboard text.",
        ),
        unique_failure="A version can disappear, retention can delete required evidence, or audit replay can reconstruct the wrong decision history.",
    ),
)

_FALLBACK_NOISE_TERMS = {
    "behavior",
    "candidate",
    "component",
    "first",
    "greenfield",
    "local",
    "odylith",
    "owned",
    "owns",
    "path",
    "planned",
    "product",
    "proof",
    "rationale",
    "record",
    "release",
    "relevant",
    "service",
    "state",
    "surface",
    "support",
    "supports",
    "system",
    "workspace",
}

_GENERATED_CONTRACT_MARKERS = (
    "accepted first-path input",
    "command or event result",
    "component proof",
    "comparison display",
    "current decision summary",
    "role-appropriate status views",
    "role-specific actor visibility",
    "status timeline",
    "representative input covering",
)


def differentiate_component_contracts(proposal: dict[str, Any], *, max_passes: int = 5) -> bool:
    """Repair interchangeable generated component contracts before quality gates run."""

    components = _component_rows(proposal)
    if len(components) < 2:
        return False
    changed = False
    for _pass in range(max_passes):
        targets = _contract_repair_targets(components, proposal=proposal)
        rows_by_label, indexes_by_label = _component_lookup(components)
        issues = rendered_component_spec_quality_issues(
            _render_component_specs(proposal),
            project_title=_project_title(proposal),
        )
        targets = [
            *targets,
            *_repair_targets(issues, rows_by_label=rows_by_label, indexes_by_label=indexes_by_label),
        ]
        if not targets:
            return changed
        before = _contract_fingerprint(components)
        for target in targets:
            _repair_row(
                target.row,
                proposal=proposal,
                sibling=target.sibling,
                previous_label=_adjacent_label(components, target.index - 1),
                next_label=_adjacent_label(components, target.index + 1),
            )
        changed |= before != _contract_fingerprint(components)
        if before == _contract_fingerprint(components):
            break
    return changed


def component_spec_preflight_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return operator-safe spec quality issues for the repaired proposal."""

    specs = _render_component_specs(proposal)
    if not specs:
        return []
    raw_issues = rendered_component_spec_quality_issues(specs, project_title=_project_title(proposal))
    return operator_component_spec_issues(raw_issues)


def operator_component_spec_issues(issues: Sequence[str]) -> list[str]:
    """Convert component spec quality failures into product-language blockers."""

    return [_operator_issue(issue) for issue in issues]


@dataclass(frozen=True)
class _RepairTarget:
    index: int
    row: dict[str, Any]
    sibling: Mapping[str, Any] | None


def _repair_targets(
    issues: Sequence[str],
    *,
    rows_by_label: Mapping[str, dict[str, Any]],
    indexes_by_label: Mapping[str, int],
) -> list[_RepairTarget]:
    targets: list[_RepairTarget] = []
    for issue in issues:
        pair = re.search(r"component specs `(?P<left>[^`]+)` and `(?P<right>[^`]+)` are too interchangeable", issue)
        if pair:
            left = pair.group("left")
            right = pair.group("right")
            for label, sibling in ((left, right), (right, left)):
                if label in rows_by_label:
                    targets.append(
                        _RepairTarget(
                            index=indexes_by_label.get(label, 0),
                            row=rows_by_label[label],
                            sibling=rows_by_label.get(sibling),
                        )
                    )
            continue
        local = re.search(r"component spec `(?P<label>[^`]+)` does not contain", issue)
        if local and local.group("label") in rows_by_label:
            label = local.group("label")
            targets.append(
                _RepairTarget(index=indexes_by_label.get(label, 0), row=rows_by_label[label], sibling=None)
            )
    return _dedupe_targets(targets)


def _contract_repair_targets(rows: Sequence[dict[str, Any]], *, proposal: Mapping[str, Any]) -> list[_RepairTarget]:
    targets: list[_RepairTarget] = []
    for index, row in enumerate(rows):
        contract = row.get("component_contract")
        if isinstance(contract, Mapping) and (
            _contract_needs_repair(contract) or _contract_misses_local_axis(row=row, contract=contract, proposal=proposal)
        ):
            sibling = rows[index + 1] if index + 1 < len(rows) else (rows[index - 1] if index else None)
            targets.append(_RepairTarget(index=index, row=row, sibling=sibling))
    return targets


def _contract_needs_repair(contract: Mapping[str, Any]) -> bool:
    if public_prose_quality_issues(contract):
        return True
    values = text_values(contract)
    if any(_starts_with_generic_actor(value) for value in values):
        return True
    joined = " ".join(values).casefold()
    return any(
        marker in joined
        for marker in (
            "representative input covering",
            "component proof",
            "accepted first-path input and state object",
        )
    )


def _contract_misses_local_axis(*, row: Mapping[str, Any], contract: Mapping[str, Any], proposal: Mapping[str, Any]) -> bool:
    axis = _axis_for(row=row, proposal=proposal)
    if axis.key.startswith("fallback_"):
        return False
    label_text = _component_label(row, 0)
    description_text = _clean(row.get("source_system_description"))
    local_score = _axis_local_score(axis, label_text=label_text, description_text=description_text)
    if local_score < 24:
        return False
    expected_hits = min(4, max(2, _trigger_hits(axis.triggers, label_text)))
    return _trigger_hits(axis.triggers, " ".join(text_values(contract))) < expected_hits


def _starts_with_generic_actor(value: str) -> bool:
    text = _clean(value)
    return bool(
        re.match(
            r"^(?:Operator|Maintainer|Reviewer|Primary user|Project operator|Domain reviewer|Implementation owner|Evidence owner|Workflow operator|Risk reviewer|Proof reviewer)(?:\s|:|[-–—]|$)",
            text,
        )
    )


def _render_component_specs(proposal: Mapping[str, Any]) -> dict[str, str]:
    rows = _component_rows(proposal)
    specs: dict[str, str] = {}
    for index, row in enumerate(rows):
        label = _component_label(row, index)
        specs[label] = build_component_spec(
            component_id=_clean(row.get("component_id")) or _slug(label),
            label=label,
            path=_clean(row.get("intended_path")) or _clean(row.get("path")),
            kind=_clean(row.get("kind")) or "service",
            status=_clean(row.get("status")) or "planned",
            sources=tuple(text_values(row.get("evidence_tier")) or ("user_intent",)),
            workstreams=tuple(text_values(row.get("workstreams"))),
            diagrams=tuple(text_values(row.get("diagrams"))),
            responsibility=_clean(row.get("responsibility")),
            boundary=_clean(row.get("boundary")),
            dependencies=tuple(text_values(row.get("dependencies"))),
            interfaces=tuple(text_values(row.get("interfaces"))),
            validation=tuple(text_values(row.get("validation"))),
            risks=tuple(text_values(row.get("risks"))),
            qualification=_clean(row.get("qualification")) or "candidate",
            component_contract=row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else None,
        )
    return specs


def _repair_row(
    row: dict[str, Any],
    *,
    proposal: Mapping[str, Any],
    sibling: Mapping[str, Any] | None,
    previous_label: str,
    next_label: str,
) -> None:
    label = _component_label(row, 0)
    sibling_label = _component_label(sibling, 0) if isinstance(sibling, Mapping) else ""
    axis = _axis_for(row=row, proposal=proposal)
    sibling_axis = _axis_for(row=sibling, proposal=proposal) if isinstance(sibling, Mapping) else None
    state_label = _state_label(_proposal_text(proposal, "state_object", "intent.state_object"), fallback="accepted state")
    upstream = previous_label or "accepted first-path input"
    downstream = next_label or "release proof review"
    outside = _outside_boundary(axis=axis, sibling_axis=sibling_axis, sibling_label=sibling_label)
    previous_contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
    axis_payload = {
        "owned_state": f"{axis.owned_state} for {state_label}",
        "accepted_inputs": axis.accepted_inputs,
        "produced_outputs": axis.produced_outputs,
        "states_or_transitions": axis.states_or_transitions,
        "outside_boundary": outside,
        "local_proof": _local_proof(axis=axis, label=label, sibling_label=sibling_label),
        "upstream_truth": upstream,
        "downstream_consumers": downstream,
        "unique_failure": axis.unique_failure,
    }
    semantic_contract = derive_component_semantic_contract(
        row,
        proposal=proposal,
        sibling=sibling,
        previous_label=previous_label,
        next_label=next_label,
        state_label=state_label,
    )
    contract = normalize_contract(
        _contract_payload(
            axis_payload,
            semantic_contract,
            axis=axis,
            local_score=_axis_local_score(
                axis,
                label_text=label,
                description_text=_clean(row.get("source_system_description")),
            ),
        )
    )
    row["component_contract"] = contract
    _sync_generated_component_fields(row, label=label, contract=contract, previous_contract=previous_contract)


def _axis_for(*, row: Mapping[str, Any] | None, proposal: Mapping[str, Any]) -> _Axis:
    if not isinstance(row, Mapping):
        return _fallback_axis("sibling", _proposal_context(proposal))
    label_text = _component_label(row, 0)
    description_text = _clean(row.get("source_system_description"))
    scored = [
        (
            _axis_local_score(axis, label_text=label_text, description_text=description_text),
            _trigger_hits(axis.triggers, label_text),
            _trigger_hits(axis.triggers, description_text),
            axis,
        )
        for axis in _AXES
    ]
    scored.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            -item[2],
            item[3].key,
        )
    )
    if scored and scored[0][0] > 0:
        return scored[0][3]
    return _fallback_axis(
        label_text,
        _fallback_context(row=row, proposal=proposal),
        focus=_focus_phrase(_scrub_generated_context(_clean(row.get("source_system_description")))),
    )


def _fallback_axis(label: str, context: str, *, focus: str = "") -> _Axis:
    label_terms = _content_terms(label)
    context_terms = _content_terms(context)
    nearby_terms = _nearby_content_terms(label_terms, context)
    extra_terms = _unique_terms(
        [
            *[term for term in nearby_terms if term not in label_terms],
            *[term for term in context_terms if term not in label_terms],
        ]
    )
    primary = " ".join(label_terms[:4]) or _clean(label).casefold() or "component"
    secondary = focus or _phrase(extra_terms[:4]) or _phrase(context_terms[:4]) or "local evidence and handoff"
    input_focus = _phrase(extra_terms[4:7]) or secondary
    output_focus = _phrase(extra_terms[7:10]) or secondary
    states = ", ".join(_unique_terms([*extra_terms[:5], "blocked", "validated", "handed-off"])[:7])
    return _Axis(
        key=f"fallback_{_slug(primary)}",
        triggers=(),
        owned_state=f"{primary} state, {secondary}, local blockers, and handoff evidence",
        accepted_inputs=f"{primary} input, {input_focus} evidence, actor identity, validation context, and upstream handoff",
        produced_outputs=f"{primary} result, {output_focus} update, blocker signal, and downstream handoff",
        states_or_transitions=states,
        outside_boundary="sibling product responsibilities, external-provider truth, presentation outside the accepted boundary, and release approval",
        local_proof=(
            f"{primary} input proves {secondary} before downstream handoff.",
            f"Invalid {input_focus} evidence blocks the {primary} result.",
            f"{primary} recovery evidence stays visible when {output_focus} changes.",
        ),
        unique_failure=f"{primary} can look complete while required {secondary} is missing, stale, or assigned to the wrong boundary.",
    )


def _contract_payload(
    axis_payload: Mapping[str, Any],
    semantic_contract: Any,
    *,
    axis: _Axis,
    local_score: int,
) -> Mapping[str, Any]:
    if not axis.key.startswith("fallback_") and local_score >= 12:
        return axis_payload
    if not _semantic_contract_is_strong(semantic_contract):
        return axis_payload
    semantic_fields = dict(semantic_contract.fields)
    semantic_fields["outside_boundary"] = _join_contract_clauses(
        axis_payload.get("outside_boundary"),
        semantic_fields.get("outside_boundary"),
    )
    semantic_fields["local_proof"] = list(
        _unique_terms([*text_values(semantic_fields.get("local_proof")), *text_values(axis_payload.get("local_proof"))[:1]])
    )
    return semantic_fields


def _semantic_contract_is_strong(semantic_contract: Any) -> bool:
    local_terms = getattr(semantic_contract, "local_terms", ())
    confidence = int(getattr(semantic_contract, "confidence", 0) or 0)
    return confidence >= 8 and len(tuple(local_terms)) >= 3


def _join_contract_clauses(*values: Any) -> str:
    clauses: list[str] = []
    for value in values:
        for clause in re.split(r",\s*(?=(?:and\s+)?[a-z0-9])", _clean(value)):
            cleaned = _clean(re.sub(r"^(?:and|or)\s+", "", clause, flags=re.IGNORECASE)).strip(" .")
            if cleaned:
                clauses.append(cleaned)
    return _phrase(_unique_terms(clauses))


def _outside_boundary(*, axis: _Axis, sibling_axis: _Axis | None, sibling_label: str) -> str:
    outside = axis.outside_boundary
    if sibling_axis:
        sibling_focus = sibling_axis.owned_state.split(" for ", 1)[0]
        sibling_name = f" owned by {sibling_label}" if sibling_label else ""
        outside = f"{outside}, {sibling_focus}{sibling_name}"
    return outside


def _local_proof(*, axis: _Axis, label: str, sibling_label: str) -> list[str]:
    proofs = list(axis.local_proof)
    if sibling_label:
        proofs.append(f"{label} refuses {sibling_label} ownership while preserving its own local proof.")
    return proofs


def _sync_generated_component_fields(
    row: dict[str, Any],
    *,
    label: str,
    contract: Mapping[str, Any],
    previous_contract: Mapping[str, Any],
) -> None:
    if _weak_text(row.get("responsibility")) or _reuses_contract_text(row.get("responsibility"), previous_contract):
        row["responsibility"] = responsibility_from_contract(label, contract)
    if _weak_text(row.get("boundary")) or _reuses_contract_text(row.get("boundary"), previous_contract):
        row["boundary"] = boundary_from_contract(label, contract)
    if _weak_sequence(row.get("interfaces")) or _sequence_reuses_contract_text(row.get("interfaces"), previous_contract):
        row["interfaces"] = interfaces_from_contract(contract)
    if _weak_sequence(row.get("dependencies")) or _sequence_reuses_contract_text(row.get("dependencies"), previous_contract):
        row["dependencies"] = dependencies_from_contract(contract)
    if _weak_sequence(row.get("validation")) or _sequence_reuses_contract_text(row.get("validation"), previous_contract):
        row["validation"] = validation_from_contract(contract)
    if _weak_sequence(row.get("risks")) or _sequence_reuses_contract_text(row.get("risks"), previous_contract):
        row["risks"] = risks_from_contract(label, contract)


def _operator_issue(issue: str) -> str:
    pair = re.search(r"component specs `(?P<left>[^`]+)` and `(?P<right>[^`]+)` are too interchangeable", issue)
    if pair:
        return (
            "Odylith could not distinguish duplicate internal systems from the accepted intent after deterministic "
            f"repair: {pair.group('left')} and {pair.group('right')} remained interchangeable."
        )
    local = re.search(r"component spec `(?P<label>[^`]+)` does not contain", issue)
    if local:
        return (
            "Odylith could not derive enough component-local product terms from the accepted intent after deterministic "
            f"repair: {local.group('label')} remained too generic."
        )
    return issue


def _dedupe_targets(values: Sequence[_RepairTarget]) -> list[_RepairTarget]:
    result: list[_RepairTarget] = []
    seen: set[int] = set()
    for target in values:
        marker = id(target.row)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(target)
    return result


def _component_rows(proposal: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = proposal.get("components")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _component_lookup(rows: Sequence[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    rows_by_label: dict[str, dict[str, Any]] = {}
    indexes_by_label: dict[str, int] = {}
    for index, row in enumerate(rows):
        label = _component_label(row, index)
        rows_by_label[label] = row
        indexes_by_label[label] = index
    return rows_by_label, indexes_by_label


def _component_label(row: Mapping[str, Any] | None, index: int) -> str:
    if not isinstance(row, Mapping):
        return ""
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or f"Component {index + 1}"


def _adjacent_label(rows: Sequence[Mapping[str, Any]], index: int) -> str:
    if index < 0 or index >= len(rows):
        return ""
    return _component_label(rows[index], index)


def _contract_fingerprint(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(row.get("component_contract", "")) for row in rows)


def _project_title(proposal: Mapping[str, Any]) -> str:
    return _proposal_text(proposal, "title", "intent.title")


def _proposal_context(proposal: Mapping[str, Any]) -> str:
    return " ".join(
        _proposal_text(proposal, key)
        for key in ("title", "intent.title", "state_object", "intent.state_object", "first_path", "intent.first_path", "proof_boundary", "intent.proof_boundary")
    )


def _fallback_context(*, row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    return " ".join(
        text
        for text in (
            _component_label(row, 0),
            _scrub_generated_context(_clean(row.get("source_system_description"))),
            _proposal_context(proposal),
        )
        if text
    )


def _axis_local_score(axis: _Axis, *, label_text: str, description_text: str) -> int:
    label_hits = _trigger_hits(axis.triggers, label_text)
    description_hits = _trigger_hits(axis.triggers, description_text)
    return label_hits * 12 + description_hits * 8


def _trigger_hits(triggers: Sequence[str], text: str) -> int:
    tokens = re.findall(r"[a-z0-9]+", _clean(text).casefold())
    hits = 0
    for trigger in triggers:
        normalized = trigger.casefold()
        if any(token == normalized or token.startswith(normalized) for token in tokens):
            hits += 1
    return hits


def _scrub_generated_context(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"\bRationale:\s*supports\s+the\s+accepted\s+first\s+path\s+and\s+proof\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRelevant\s+behavior:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Owns\s+[^.]+[.]\s*", "", text, flags=re.IGNORECASE)
    return _clean(text)


def _focus_phrase(context: str) -> str:
    text = _clean(context).strip(" .")
    text = re.sub(r"^[A-Z][A-Za-z0-9 ]{2,80}\s+[-–—]\s*", "", text)
    text = re.sub(
        r"^(?:accepts?|captures?|checks?|coordinates?|creates?|displays?|evaluates?|helps?|imports?|keeps?|"
        r"maintains?|normalizes?|owns?|presents?|records?|renders?|routes?|shows?|stores?|tracks?|validates?)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    return first if 4 <= len(first.split()) <= 18 else ""


def _content_terms(value: str) -> list[str]:
    return [
        term
        for term in ordered_domain_terms(value)
        if term not in _FALLBACK_NOISE_TERMS and not term.isdigit()
    ]


def _nearby_content_terms(label_terms: Sequence[str], context: str, *, window: int = 5) -> list[str]:
    if not label_terms:
        return []
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", _clean(context).casefold())
    result: list[str] = []
    label_set = set(label_terms)
    for index, token in enumerate(tokens):
        normalized = _content_terms(token)
        if not normalized or normalized[0] not in label_set:
            continue
        start = max(0, index - window)
        end = min(len(tokens), index + window + 1)
        result.extend(_content_terms(" ".join(tokens[start:end])))
    return _unique_terms(result)


def _unique_terms(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value).casefold()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _proposal_text(proposal: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        current: Any = proposal
        for part in key.split("."):
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(part)
        text = _clean(current)
        if text:
            return text
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    for key in keys:
        text = _clean(intent.get(key))
        if text:
            return text
    return ""


def _state_label(value: str, *, fallback: str) -> str:
    text = _clean(value)
    if not text:
        return fallback
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    match = re.search(
        r"^(?:a|an|the)\s+(?P<label>.+?)\s+(?:tracks|records|stores|moves|captures|keeps|contains)\b",
        first,
        re.IGNORECASE,
    )
    if match:
        return _clean(match.group("label")).strip(" .") or fallback
    return first if len(first.split()) <= 10 else fallback


def _weak_text(value: Any) -> bool:
    text = _clean(value).casefold()
    if not text:
        return True
    return any(
        marker in text
        for marker in (
            "representative input covering",
            "first implementation plan",
            "accepted first path",
            "responsibility and keeps it tied",
            "component proof",
        )
    )


def _weak_sequence(value: Any) -> bool:
    return _weak_text(" ".join(text_values(value)))


def _sequence_reuses_contract_text(value: Any, contract: Mapping[str, Any]) -> bool:
    return _reuses_contract_text(" ".join(text_values(value)), contract)


def _reuses_contract_text(value: Any, contract: Mapping[str, Any]) -> bool:
    text = _clean(value).casefold()
    if not text or not isinstance(contract, Mapping):
        return False
    for candidate in text_values(contract):
        marker = _contract_marker(candidate)
        if marker and marker in text:
            return True
    return False


def _contract_marker(value: str) -> str:
    text = _clean(value).casefold()
    for marker in _GENERATED_CONTRACT_MARKERS:
        if marker in text:
            return marker
    return ""


def _phrase(values: Sequence[str]) -> str:
    rows = [_clean(value).casefold() for value in values if _clean(value)]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _clean(value).casefold()).strip("-") or "component"


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


__all__ = [
    "component_spec_preflight_issues",
    "differentiate_component_contracts",
    "operator_component_spec_issues",
]
