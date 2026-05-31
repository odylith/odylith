"""Workstream-intelligence contracts for confirmed greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_brief_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values


SECTION_TITLE = "Domain Intelligence"

_REQUIRED_LAYERS = (
    "intent",
    "scope",
    "ontology",
    "state",
    "operators",
    "constraints",
    "source_of_truth_map",
    "evidence_model",
    "decisions",
    "assumptions",
    "topology",
    "invariants",
    "risks",
    "validation_obligations",
    "artifacts",
    "authority",
    "owners",
    "execution_memory",
    "metrics",
    "change_model",
    "invalidation_rules",
    "conflict_model",
    "transfer_priors",
)

_LAYER_LABELS = {
    "intent": "Intent And Outcome",
    "scope": "Scope And Boundary",
    "ontology": "Domain Ontology",
    "state": "State Model",
    "operators": "Allowed Operators",
    "constraints": "Constraints And Boundary Conditions",
    "source_of_truth_map": "Source Of Truth Map",
    "evidence_model": "Evidence Model",
    "decisions": "Decision History",
    "assumptions": "Assumptions And Uncertainty",
    "topology": "Dependency Topology",
    "invariants": "Invariants",
    "risks": "Risk Register",
    "validation_obligations": "Validation Obligations",
    "artifacts": "Work Products And Artifact Contracts",
    "authority": "Stakeholders And Authority",
    "owners": "Ownership Map",
    "execution_memory": "Memory And Prior Executions",
    "metrics": "Metrics And Observables",
    "change_model": "Change Model",
    "invalidation_rules": "Invalidation Rules",
    "conflict_model": "Conflict Model",
    "transfer_priors": "Reuse And Transfer Priors",
}


def enrich_backlog_rows(
    rows: Sequence[Any],
    *,
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    validation_strategy: Sequence[Any],
    security_compliance: Any,
    components: Sequence[Any],
    diagrams: Sequence[Any],
    domain_profile: Any | None = None,
) -> list[Any]:
    """Preserve proposal workstream intelligence without synthesis."""

    _ = intent, program, release_plan, validation_strategy, security_compliance, components, diagrams, domain_profile
    return [dict(row) if isinstance(row, Mapping) else row for row in rows]


def render_domain_intelligence_section(value: Any) -> str:
    """Render a domain-intelligence mapping as workstream Markdown."""

    if not isinstance(value, Mapping):
        return ""
    lines: list[str] = []
    summary = clean_text(value.get("summary"))
    if summary:
        lines.append(summary)
    for key in _REQUIRED_LAYERS:
        rendered = _render_layer(value.get(key))
        if not rendered:
            continue
        if lines:
            lines.append("")
        lines.append(f"### {_LAYER_LABELS[key]}")
        lines.extend(rendered)
    return "\n".join(lines).strip()


def domain_intelligence_issues(value: Any, *, owner: str) -> list[str]:
    """Return actionable validation issues for one proposal payload."""

    if not isinstance(value, Mapping):
        return [f"{owner} must include domain_intelligence object"]
    issues: list[str] = []
    for key in _REQUIRED_LAYERS:
        nested = value.get(key)
        if not _layer_has_depth(nested):
            issues.append(f"{owner} domain_intelligence.{key} is missing or too shallow")
    if len(_list_values(value.get("ontology"))) < 4:
        issues.append(f"{owner} domain_intelligence.ontology must define at least four domain terms")
    if len(_list_values(value.get("operators"))) < 3:
        issues.append(f"{owner} domain_intelligence.operators must define at least three state-changing operations")
    if len(_list_values(value.get("validation_obligations"))) < 3:
        issues.append(f"{owner} domain_intelligence.validation_obligations must define at least three proof gates")
    duplicate_terms = _duplicate_ontology_terms(value.get("ontology"))
    if duplicate_terms:
        issues.append(
            f"{owner} domain_intelligence.ontology repeats operational term(s): {', '.join(duplicate_terms)}"
        )
    if _contains_malformed_ownership_phrase(value):
        issues.append(f"{owner} domain_intelligence contains malformed ownership phrase")
    return issues


def build_workstream_domain_intelligence(
    *,
    label: str,
    row_title: str,
    problem: str,
    opportunity: str,
    product_view: str,
    first_slice: str,
    metrics: list[str],
    dependencies: list[str],
    interfaces: list[str],
    validation: list[str],
    state_object: str,
    evidence_record: str,
    first_path: str,
    proof_boundary: str,
    human_actors: list[str],
    internal_systems: list[str],
    external_systems: list[str],
    non_goals: list[str],
) -> dict[str, Any]:
    """Render the domain-intelligence packet from one shared workstream contract."""

    actors = human_actors or [f"{label} product user: moves through the first product path."]
    internals = internal_systems or [f"{state_object}: owns domain state.", f"{evidence_record}: owns proof review."]
    internal_labels = join_system_labels(internals) or join_items(internals)
    externals = external_systems or ["No live external system is accepted for the first release."]
    non_goal_text = join_items(non_goals) or "unconfirmed broader platform behavior"
    focus = short_summary(product_view or first_slice or opportunity, limit=360)
    risk = short_summary(problem, limit=300) or f"{label} can fail if {row_title} is too vague to implement."
    build_scope = short_summary(first_slice or first_path, limit=320)
    metric_summary = join_brief_items(metrics, limit=3, item_limit=140)
    dependency_summary = join_brief_items(dependencies, limit=2, item_limit=150)
    interface_summary = join_brief_items(interfaces, limit=2, item_limit=150)
    validation_summary = join_brief_items(validation, limit=3, item_limit=150)
    actor_summary = _join_actor_labels(actors) or join_items(actors)
    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": slugify(label).replace("-", "_") or "confirmed_product",
        "summary": focus or f"{row_title} turns the accepted {label} slice into behavior the team can implement and verify.",
        "actors": actors,
        "intent": [
            focus or f"{row_title} advances {label} by building one concrete product slice.",
            f"The product problem is {risk}",
        ],
        "scope": [
            f"This slice starts with {build_scope}",
            f"Out of scope for now: {non_goal_text}.",
        ],
        "ontology": [
            f"Actors include {actor_summary}.",
            f"State object: {state_object}.",
            f"Evidence record: {evidence_record}.",
            f"Proof boundary: {proof_boundary}.",
        ],
        "state": [
            f"State focus: {build_scope}",
            f"Owned state remains trustworthy only when {state_object} and {evidence_record} explain the visible outcome.",
        ],
        "operators": [
            f"Runtime behavior to exercise: {interface_summary or build_scope}.",
            f"Internal systems involved here: {internal_labels}.",
            f"External source boundaries here: {join_items(externals)}.",
        ],
        "constraints": [
            f"Keep {row_title} inside the accepted first-release scope: {non_goal_text}.",
            f"Do not claim {row_title} ready until validation demonstrates: {validation_summary or proof_boundary}.",
        ],
        "source_of_truth_map": [
            f"{state_object} is the source of truth for current first-path state.",
            f"{evidence_record} is the source of truth for proof readiness and release confidence.",
        ],
        "evidence_model": [
            f"Proof evidence: {validation_summary or proof_boundary}.",
            f"{evidence_record} must show source input, state reference, validation result, release decision, and visible outcome.",
        ],
        "decisions": [
            f"Decide whether {row_title} delivers a visible success, blocked-input signal, recovery path, and reviewable proof.",
            f"Decide whether dependencies are ready: {dependency_summary or internal_labels}.",
        ],
        "assumptions": [
            "User intent is the evidence tier until source-backed implementation exists.",
            "External systems stay simulated, sandboxed, or deferred unless the confirmed first path requires them.",
        ],
        "topology": [
            f"Product-owned systems: {internal_labels}.",
            f"External systems: {join_items(externals)}.",
        ],
        "invariants": [
            f"Every state change touched by {row_title} names actor, source, status, and evidence expectation.",
            f"Every readiness assertion for {row_title} maps to {state_object}, {evidence_record}, validation output, and non-goals.",
        ],
        "risks": [
            risk,
            f"Trust fails if {row_title} hides missing state, source evidence, access limits, or deferred scope.",
        ],
        "validation_obligations": [
            *(validation or []),
            f"Validate that {row_title} preserves {state_object} and {evidence_record} in domain terms.",
            f"Validate that {row_title} proves success, blocked input, recovery, and handoff evidence without restating the full component contract.",
            f"Validate that {row_title} handles a blocked or recovery path without hiding missing evidence.",
        ],
        "artifacts": [
            f"{state_object} history captures the local states needed by {row_title}.",
            f"{evidence_record} captures validation output, replay output, release decision, and deferred scope.",
        ],
        "authority": [
            f"Only accepted actors or systems can move first-path state: {actor_summary}.",
            f"{row_title} can block the first release when validation, replay, access, or evidence is incomplete.",
        ],
        "owners": [
            f"Internal product systems own this slice: {internal_labels}.",
            f"Review ownership follows the accepted proof boundary and this row's local validation.",
        ],
        "execution_memory": [
            f"Future work starts from the product path and this row's local outcome.",
            f"Product-owner correction or source-backed contradiction invalidates stale assumptions.",
        ],
        "metrics": [
            metric_summary or f"{row_title} has a user-visible success, blocked, and recovery signal.",
            f"Every readiness assertion for {row_title} has state, evidence, validation, release-review, and non-goal references.",
        ],
        "change_model": [
            f"Changing the state object invalidates {row_title} validation and handoff assumptions.",
            f"Changing external dependencies invalidates access, privacy, recovery, and proof for {row_title}.",
        ],
        "invalidation_rules": [
            f"If {row_title} cannot run or be reviewed in product terms, release readiness stays blocked.",
            f"If evidence cannot explain {state_object}, {evidence_record}, or non-goals, this slice is incomplete.",
        ],
        "conflict_model": [
            f"Confirmed product intent beats generic builder fallback for {row_title}.",
            f"Source-backed validation beats narrative claims when {row_title} behavior disagrees.",
        ],
        "transfer_priors": [
            f"Keep {row_title} small enough for concrete behavior proof.",
            "Use confirmed actors, state, systems, evidence, and failure terms in this slice.",
        ],
    }


def _join_actor_labels(values: list[str] | None, *, limit: int = 5) -> str:
    rows = []
    for value in values or []:
        text = str(value or "").strip()
        if not text:
            continue
        label = text.split(":", 1)[0].split("—", 1)[0].strip(" -")
        if label:
            rows.append(label)
    rows = rows[:limit]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    return f"{', '.join(rows[:-1])}, {rows[-1]}"


def _render_layer(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        rows: list[str] = []
        for key, nested in value.items():
            rendered = "; ".join(text_values(nested))
            if rendered:
                rows.append(f"- {clean_text(key)}: {rendered}")
        return rows
    values = _list_values(value)
    return [f"- {item}" for item in values if item]


def _list_values(value: Any) -> list[str]:
    return [clean_text(item) for item in text_values(value) if clean_text(item)]


def _layer_has_depth(value: Any) -> bool:
    text = " ".join(text_values(value)).strip()
    return len(text.split()) >= 8


def _duplicate_ontology_terms(value: Any) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for row in _list_values(value):
        label = clean_text(row.split(":", 1)[0] if ":" in row else row)
        key = _ontology_term_key(row)
        if not key:
            continue
        if key in seen and seen[key] not in duplicates:
            duplicates.append(seen[key])
        else:
            seen[key] = label
    return duplicates


def _ontology_term_key(value: str) -> str:
    text = clean_text(value)
    label = text.split(":", 1)[0] if ":" in text else text
    return label.casefold()


def _contains_malformed_ownership_phrase(value: Any) -> bool:
    for token in text_values(value):
        lowered = token.casefold()
        if " owns own " in f" {lowered} " or " owns owns " in f" {lowered} ":
            return True
    return False


__all__ = [
    "SECTION_TITLE",
    "build_workstream_domain_intelligence",
    "domain_intelligence_issues",
    "enrich_backlog_rows",
    "render_domain_intelligence_section",
]
