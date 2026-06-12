"""Proposal repairs driven by Greenfield post-confirm reviewer lenses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as clean_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def repair_proposal_for_quality_lens_gaps(
    proposal: dict[str, Any],
    *,
    quality_lenses: Mapping[str, Any],
    release_selector: str,
) -> bool:
    """Strengthen proposal evidence for failed PM, architecture, engineering, or domain lenses."""

    failed_checks = _failed_check_names(quality_lenses)
    if not failed_checks:
        return False
    changed = False
    if failed_checks.intersection({"decision_boundary", "high_risk_assumptions", "domain_term_coverage"}):
        changed |= _ensure_decision_boundary(proposal)
        changed |= _carry_assumptions_into_validation(proposal, release_selector=release_selector)
    if failed_checks.intersection({"system_boundary", "component_topology"}):
        changed |= _ensure_system_boundaries(proposal)
    if failed_checks.intersection({"first_release_scope", "component_specs"}):
        changed |= _ensure_release_scope(proposal, release_selector=release_selector)
    if failed_checks.intersection({"proof_boundary", "visible_result", "domain_term_coverage"}):
        changed |= _ensure_proof_language(proposal, release_selector=release_selector)
    return changed


def _failed_check_names(quality_lenses: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    lenses = quality_lenses.get("lenses")
    if not isinstance(lenses, Mapping):
        return names
    for lens in lenses.values():
        if not isinstance(lens, Mapping):
            continue
        checks = lens.get("checks")
        if not isinstance(checks, list):
            continue
        for check in checks:
            if isinstance(check, Mapping) and clean_text(check.get("status")).casefold() != "passed":
                name = clean_text(check.get("name"))
                if name:
                    names.add(name)
    return names


def _ensure_decision_boundary(proposal: dict[str, Any]) -> bool:
    intent = _intent(proposal)
    title = completion_text.project_title(proposal)
    state = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    changed = False
    assumptions = proposal.get("assumptions")
    if not isinstance(assumptions, list):
        assumptions = []
        proposal["assumptions"] = assumptions
        changed = True
    existing = {clean_text(row.get("statement")) for row in dict_rows(assumptions)}
    required = [
        (
            "user_intent",
            f"Users can provide the information required to {action} before {title} presents a trusted result.",
        ),
        (
            "odylith_assumption",
            (
                f"{state} must preserve actor, status, result, and recovery context "
                f"when the user needs to {outcome_action}."
            ),
        ),
    ]
    for tier, statement in required:
        sentence = sentence_text(statement, limit=420)
        if sentence in existing:
            continue
        assumptions.append(
            {
                "id": f"A-{len(dict_rows(assumptions)) + 1:03d}",
                "tier": tier,
                "statement": sentence,
                "impact": "Shapes the first-release proof boundary and validation obligations.",
            }
        )
        existing.add(sentence)
        changed = True
    questions = proposal.get("open_questions")
    if not isinstance(questions, list):
        questions = []
        proposal["open_questions"] = questions
        changed = True
    if not dict_rows(questions):
        questions.append(
            {
                "id": "OQ-001",
                "question": sentence_text(
                    (
                        f"Which input, access, or integration boundary must be resolved "
                        f"before {title} implementation starts?"
                    ),
                    limit=360,
                ),
                "impact": "Changes the first release scope, permission model, fixtures, and validation target.",
                "default_if_unanswered": "Use the accepted first-path boundary and deterministic local fixtures.",
            }
        )
        changed = True
    if "human_actors" not in intent and text_values(proposal.get("human_actors")):
        intent["human_actors"] = list(text_values(proposal.get("human_actors")))
        changed = True
    return changed


def _carry_assumptions_into_validation(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    assumptions = [
        clean_text(row.get("statement"))
        for row in dict_rows(proposal.get("assumptions"))
        if clean_text(row.get("statement"))
    ]
    if not assumptions:
        return False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    title = completion_text.project_title(proposal)
    rows = text_values(proposal.get("validation_strategy"))
    additions = [
        sentence_text(
            f"Assumption proof for release {release} checks whether {statement.rstrip('.')}",
            limit=520,
        )
        for statement in assumptions[:3]
    ]
    additions.append(
        sentence_text(
            f"{title} cannot promote until accepted assumptions are visible in validation output and release review.",
            limit=520,
        )
    )
    merged = list(unique_text([*rows, *additions]))
    if list(rows) == merged:
        return False
    proposal["validation_strategy"] = merged
    return True


def _ensure_system_boundaries(proposal: dict[str, Any]) -> bool:
    intent = _intent(proposal)
    changed = False
    internal = text_values(intent.get("internal_systems"))
    if len(internal) < 2:
        internal = _component_labels(proposal)[:2] or [
            f"{completion_text.project_title(proposal)} workflow service",
            f"{completion_text.project_title(proposal)} evidence service",
        ]
        if len(internal) == 1:
            internal.append(f"{completion_text.project_title(proposal)} evidence service")
        intent["internal_systems"] = list(unique_text(internal[:2]))
        changed = True
    if "external_systems" not in intent:
        intent["external_systems"] = list(text_values(proposal.get("external_systems")))
        changed = True
    return changed


def _ensure_release_scope(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    changed = False
    release_plan = proposal.get("release_plan")
    if not isinstance(release_plan, dict):
        release_plan = {}
        proposal["release_plan"] = release_plan
        changed = True
    if clean_text(release_plan.get("selector")) != release:
        release_plan["selector"] = release
        changed = True
    titles = _workstream_titles(proposal)
    target_titles = text_values(release_plan.get("target_workstream_titles"))
    if titles and not target_titles:
        release_plan["target_workstream_titles"] = titles[:3]
        changed = True
    for index, row in enumerate(dict_rows(proposal.get("components"))):
        if clean_text(row.get("release_scope")):
            continue
        row["release_scope"] = "first_release" if index < 4 else "deferred"
        changed = True
    return changed


def _ensure_proof_language(
    proposal: dict[str, Any],
    *,
    release_selector: str,
) -> bool:
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    intent = _intent(proposal)
    title = completion_text.project_title(proposal)
    state = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    proof = clean_text(intent.get("proof_boundary"))
    if proof:
        return False
    intent["proof_boundary"] = sentence_text(
        (
            f"Release {release} proof succeeds when a representative user can {action}, "
            f"{title} records {state}, and the product explains {outcome}."
        ),
        limit=620,
    )
    return True


def _intent(proposal: dict[str, Any]) -> dict[str, Any]:
    intent = proposal.get("intent")
    if isinstance(intent, dict):
        return intent
    intent = {}
    proposal["intent"] = intent
    return intent


def _component_labels(proposal: Mapping[str, Any]) -> list[str]:
    return [
        label
        for row in dict_rows(proposal.get("components"))
        if (label := clean_text(row.get("label") or row.get("component_id")))
    ]


def _workstream_titles(proposal: Mapping[str, Any]) -> list[str]:
    return [
        title
        for row in dict_rows(proposal.get("backlog"))
        if (title := clean_text(row.get("title")))
    ]


__all__ = ["repair_proposal_for_quality_lens_gaps"]
