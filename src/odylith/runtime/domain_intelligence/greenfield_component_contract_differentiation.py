"""Differentiate overlapping greenfield component contracts before writes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_axes import (
    COMPONENT_AXES,
    ComponentAxis,
)
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
    title_state = f"{_project_title(proposal)} state" if _project_title(proposal) else "accepted state"
    state_label = _state_label(_proposal_text(proposal, "state_object", "intent.state_object"), fallback=title_state)
    upstream = previous_label or "accepted first-path input"
    downstream = next_label or "release proof review"
    outside = _outside_boundary(axis=axis, sibling_axis=sibling_axis, sibling_label=sibling_label)
    previous_contract = row.get("component_contract") if isinstance(row.get("component_contract"), Mapping) else {}
    axis_payload = _axis_payload(
        axis=axis,
        row=row,
        label=label,
        state_label=state_label,
        outside=outside,
        sibling_label=sibling_label,
        upstream=upstream,
        downstream=downstream,
    )
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


def _axis_for(*, row: Mapping[str, Any] | None, proposal: Mapping[str, Any]) -> ComponentAxis:
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
        for axis in COMPONENT_AXES
    ]
    if re.search(r"\b(claim|claims|citation|citations|lineage|traceability|source-backed)\b", f"{label_text} {description_text}", flags=re.IGNORECASE):
        for score, _label_hits, _description_hits, axis in scored:
            if axis.key == "source_claim_lineage" and score > 0:
                return axis
    if re.search(r"\b(rationale|vote|motion|abstain|abstention)\b", label_text, flags=re.IGNORECASE):
        for score, _label_hits, _description_hits, axis in scored:
            if axis.key == "decision_rationale_vote" and score > 0:
                return axis
    priority_axis = _priority_axis(label_text)
    if priority_axis:
        for score, _label_hits, _description_hits, axis in scored:
            if axis.key == priority_axis and score > 0:
                return axis
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


def _priority_axis(label_text: str) -> str:
    """Resolve labels where one broad trigger would otherwise steal ownership."""

    text = _clean(label_text).casefold()
    if re.search(r"\b(criteria|criterion|protocol|rule|eligibility policy|inclusion|exclusion)\b", text):
        return "definition_rules"
    if re.search(r"\b(submission|submit|file upload|upload)\b", text):
        return "submission_versioning"
    if re.search(r"\b(admin|inspection|disputed|readiness|evidence review|review tools)\b", text) and re.search(
        r"\b(review|evidence|source|signal|quality|disputed|inspection)\b", text
    ):
        return "evidence_review"
    if re.search(r"\b(confidence|signal quality|quality signal)\b", text) or (
        re.search(r"\b(signal|signals|deduplication|dedupe|duplicate)\b", text)
        and not re.search(r"\b(intake|ingestion|ingest|import|source attribution|metadata import)\b", text)
    ):
        return "signal_quality_deduplication"
    if re.search(r"\b(intake|ingestion|ingest|import|deduplication|dedupe|normalize)\b", text):
        return "intake_import"
    if re.search(r"\b(access|permission|role|rbac|grant|visibility|redaction)\b", text) and re.search(
        r"\b(audit|history|version|retention|replay)\b", text
    ):
        return "access_audit"
    if re.search(r"\b(assignment|assign|permission|access|conflict|routing|eligibility)\b", text):
        return "assignment_permission"
    if re.search(r"\b(form|scoring|score|template|rubric|assessment)\b", text):
        return "form_scoring"
    if re.search(r"\b(case|workspace|agenda|checklist)\b", text):
        return "case_workspace"
    if re.search(r"\b(map|parcel|location|geospatial|geometry|overlay|layer|zoning)\b", text):
        return "spatial_context"
    if re.search(r"\b(question|issue|concern|follow-up|followup|response|answer|unresolved)\b", text):
        return "question_issue_tracking"
    if re.search(r"\b(feedback|comment|comments|theme|grouping|cluster|sentiment)\b", text):
        return "feedback_grouping"
    if re.search(r"\b(journal|decision note|decision journal|rationale journal)\b", text):
        return "user_decision_journal"
    if re.search(r"\b(dashboard|comparison|compare|display|readiness view)\b", text):
        return "dashboard_comparison"
    if re.search(r"\b(decision|approval|approve|final outcome|outcome|blocker)\b", text):
        return "decision_review"
    if re.search(r"\b(audit|trail|retention|archive|history)\b", text):
        return "audit_retention"
    if re.search(r"\b(risk|disclaimer|compliance|policy|privacy|guardrails?|safety|consent)\b", text):
        return "policy_risk_guardrails"
    if re.search(r"\b(follow list|watchlist|watch list|saved list|selected list|bookmark)\b", text):
        return "tracked_selection_list"
    return ""


def _fallback_axis(label: str, context: str, *, focus: str = "") -> ComponentAxis:
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
    return ComponentAxis(
        key=f"fallback_{_slug(primary)}",
        triggers=(),
        owned_state=f"{primary} state, {secondary}, local blockers, and handoff evidence",
        accepted_inputs=f"{primary} input, {input_focus} evidence, actor identity, validation context, and upstream handoff",
        produced_outputs=f"{primary} result, {output_focus} update, blocker signal, and downstream handoff",
        states_or_transitions=states,
        outside_boundary="sibling product responsibilities, upstream source truth, presentation outside the accepted boundary, and release approval",
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
    axis: ComponentAxis,
    local_score: int,
) -> Mapping[str, Any]:
    if not axis.key.startswith("fallback_") and local_score >= 24:
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


def _axis_payload(
    *,
    axis: ComponentAxis,
    row: Mapping[str, Any],
    label: str,
    state_label: str,
    outside: str,
    sibling_label: str,
    upstream: str,
    downstream: str,
) -> dict[str, Any]:
    owned_state = f"{axis.owned_state} for {state_label}"
    accepted_inputs = axis.accepted_inputs
    produced_outputs = axis.produced_outputs
    local_proof = _local_proof(axis=axis, label=label, sibling_label=sibling_label)
    unique_failure = axis.unique_failure
    if axis.key == "check_rule_ledger":
        subject = _check_subject(row)
        if subject:
            owned_state = f"{subject}, reviewer comments, rule references, and pass or block outcomes, check evidence, and handoff state for {state_label}"
            accepted_inputs = f"{subject} input, rule reference, reviewer comment, pass or block command, blocker signal, actor identity, and prior check state"
            produced_outputs = f"recorded {subject}, rule-linked comment, pass or block outcome, blocker signal, and downstream decision handoff"
            local_proof = [
                f"The check ledger records {subject}, reviewer comments, rule references, and pass or block outcomes with handoff evidence.",
                "Missing rule references or unresolved blockers prevent a pass outcome from appearing decision-ready.",
                "Submission, revision, assignment, and final decision changes do not silently rewrite the check record.",
            ]
            unique_failure = f"{subject} can look passed without the rule reference, reviewer comment, blocker state, or source evidence needed to trust the check."
            if sibling_label:
                local_proof.append(f"{label} refuses {sibling_label} ownership while preserving its own local proof.")
    if axis.key == "revision_lifecycle":
        subject = _revision_subject(row)
        if subject:
            owned_state = f"{subject}, revision round, actor response, resubmission version, unresolved revision blocker, and handoff state for {state_label}"
            accepted_inputs = f"{subject} input, prior decision, requested changes, actor identity, revised payload, response notes, and previous version reference"
            produced_outputs = f"linked {subject}, resubmission snapshot, response package, round status, unresolved-change blocker, and downstream decision handoff"
            local_proof = [
                f"The revision record links {subject} before downstream decision review.",
                "Incomplete responses or unresolved changes block the revision round before a downstream decision can treat it as ready.",
                "Initial intake, check ledger, assignment, and audit records remain separate from revision-round state.",
            ]
            unique_failure = f"{subject} can detach from the source item it was meant to address or make an incomplete response look decision-ready."
            if sibling_label:
                local_proof.append(f"{label} refuses {sibling_label} ownership while preserving its own local proof.")
    return {
        "owned_state": owned_state,
        "accepted_inputs": accepted_inputs,
        "produced_outputs": produced_outputs,
        "states_or_transitions": axis.states_or_transitions,
        "outside_boundary": outside,
        "local_proof": local_proof,
        "upstream_truth": upstream,
        "downstream_consumers": downstream,
        "unique_failure": unique_failure,
    }


def _check_subject(row: Mapping[str, Any]) -> str:
    description = _scrub_generated_context(_clean(row.get("source_system_description"))).casefold()
    for clause in re.split(r"[,.;]", description):
        phrase = re.sub(
            r"^(?:records?|checks?|validates?|evaluates?|owns?|tracks?|maintains?)\s+",
            "",
            _clean(clause),
            flags=re.IGNORECASE,
        )
        match = re.search(r"\b([a-z][a-z0-9 -]{1,50}\s+checks?)\b", phrase, flags=re.IGNORECASE)
        if match:
            return _clean(match.group(1)).casefold()
    label = _component_label(row, 0).casefold()
    label = re.sub(r"\b(?:ledger|service|surface|adapter|component)\b", "", label, flags=re.IGNORECASE)
    label = _clean(label)
    if re.search(r"\bcheck\b", label):
        return _clean(re.sub(r"\bcheck\b", "checks", label, flags=re.IGNORECASE)).casefold()
    if re.search(r"\bchecks\b", label):
        return label
    return ""


def _revision_subject(row: Mapping[str, Any]) -> str:
    description = _scrub_generated_context(_clean(row.get("source_system_description"))).casefold()
    for clause in re.split(r"[,.;]", description):
        phrase = re.sub(
            r"^(?:links?|tracks?|records?|maintains?|owns?)\s+",
            "",
            _clean(clause),
            flags=re.IGNORECASE,
        )
        if re.search(r"\b(revision|revisions|resubmission|response)\b", phrase, flags=re.IGNORECASE):
            phrase = _clean(phrase).strip(" .")
            if 2 <= len(phrase.split()) <= 16:
                return phrase.casefold()
    label = _component_label(row, 0).casefold()
    if re.search(r"\b(revision|resubmission|response)\b", label):
        return _clean(re.sub(r"\b(?:service|surface|adapter|component)\b", "", label, flags=re.IGNORECASE)).casefold()
    return ""


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


def _outside_boundary(*, axis: ComponentAxis, sibling_axis: ComponentAxis | None, sibling_label: str) -> str:
    outside = axis.outside_boundary
    if sibling_axis:
        sibling_focus = sibling_axis.owned_state.split(" for ", 1)[0]
        sibling_name = f" owned by {sibling_label}" if sibling_label else ""
        outside = f"{outside}, {sibling_focus}{sibling_name}"
    return outside


def _local_proof(*, axis: ComponentAxis, label: str, sibling_label: str) -> list[str]:
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


def _axis_local_score(axis: ComponentAxis, *, label_text: str, description_text: str) -> int:
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
            "required inputs, rejected or blocked cases",
            "handoff boundaries for the confirmed first path",
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
