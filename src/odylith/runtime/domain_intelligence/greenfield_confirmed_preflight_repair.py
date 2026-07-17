"""Targeted repair of confirmed greenfield preflight issues."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_confirmed_completion_text_model as completion_text
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_component_contract_differentiation import (
    differentiate_component_contracts,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_label_repair import (
    repair_generic_actor_labels,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import (
    validation_proof_summary,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_component_completion import (
    repair_component_sentence_lists,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import (
    actor_phrase_for_sentence,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import (
    path_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_helpers import (
    repair_bad_scalar,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    proof_boundary_is_weak,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    sequence_has_text_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    sequence_needs_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_quality import (
    validation_strategy_needs_repair,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_domain_intelligence_repair import (
    repair_domain_intelligence_metrics,
    repair_domain_intelligence_sentence_lists,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_list
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import set_sentence_text
from odylith.runtime.domain_intelligence.greenfield_rows import dict_rows


def repair_preflight_issues(
    proposal: dict[str, Any],
    *,
    issues: Sequence[str],
    release_selector: str,
    max_completion_passes: int,
) -> bool:
    """Repair the artifact families identified by confirmed-create preflight."""

    issue_text = " ".join(str(issue) for issue in issues).casefold()
    changed = False
    proof_or_validation = (
        validation_strategy_needs_repair(proposal)
        or "proof boundary" in issue_text
        or "validation_strategy" in issue_text
        or "validation-strategy" in issue_text
        or "validation strategy" in issue_text
        or "clipped" in issue_text
        or "unfinished" in issue_text
        or "concrete success" in issue_text
        or "success_metrics" in issue_text
        or "too shallow" in issue_text
        or "too thin to guide implementation" in issue_text
        or "not anchored to enough project-specific nouns" in issue_text
        or "repeats scaffold language" in issue_text
    )
    if proof_or_validation:
        changed |= repair_release_success_language(proposal, release_selector=release_selector)
        changed |= repair_validation_strategy(proposal, release_selector=release_selector)
        changed |= repair_backlog_success_language(proposal, release_selector=release_selector)
        changed |= repair_project_intelligence_validation(proposal, release_selector=release_selector)
    if (
        "too interchangeable" in issue_text
        or "too similar" in issue_text
        or "could not distinguish" in issue_text
        or "component-local" in issue_text
        or "clearer separation" in issue_text
    ):
        changed |= differentiate_component_contracts(proposal, max_passes=max_completion_passes)
    if (
        "generated prose" in issue_text
        or "malformed" in issue_text
        or "sentence" in issue_text
        or "semantic slop" in issue_text
        or "modal/base-form" in issue_text
    ):
        changed |= repair_generated_sentence_lists(proposal, release_selector=release_selector)
    if "generic actor label" in issue_text or "project-specific actor" in issue_text:
        changed |= repair_generic_actor_labels(proposal)
    return changed


def repair_release_success_language(proposal: dict[str, Any], *, release_selector: str) -> bool:
    """Replace weak release proof text across intent and release-plan artifacts."""

    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_reference(proposal)
    proof_summary = validation_proof_summary(completion_text.proof_boundary(proposal))
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    actor_phrase = actor_phrase_for_sentence(completion_text.actor_summary(proposal))
    proof_success = sentence_text(
        f"Release {release} succeeds only when {actor_phrase} can {action}, the product lets {actor_phrase} {outcome_action}, and {state_object} remains understandable when information is missing or corrected.",
        limit=520,
    )
    changed = False
    intent = proposal.get("intent")
    if isinstance(intent, dict):
        summary = sentence_text(
            f"{clean_generated_text(intent.get('product_story')) or label} {proof_success}",
            limit=620,
        )
        changed |= set_sentence_text(intent, "summary", summary)
        if proof_boundary_is_weak(clean_generated_text(intent.get("proof_boundary"))):
            changed |= set_sentence_text(intent, "proof_boundary", proof_success)
    release_plan = proposal.get("release_plan")
    if isinstance(release_plan, dict):
        criteria = [
            sentence_text(f"{label} success proof shows {actor_phrase} can {action} and {outcome_action}.", limit=520),
            sentence_text(f"{label} replay proof reconstructs {state_object} with actor, timestamp, status, result, and explanation.", limit=520),
            sentence_text(f"{label} blocked-path proof keeps missing input, failed validation, access limits, or privacy issues visible before a result is trusted.", limit=520),
            sentence_text(f"{label} release proof stays within the accepted product promise: {proof_summary}.", limit=520),
        ]
        changed |= set_sentence_list(release_plan, "promotion_criteria", criteria)
        stages = release_plan.get("release_stages")
        if isinstance(stages, list) and stages and isinstance(stages[0], dict):
            changed |= set_sentence_text(stages[0], "release_gate", proof_success)
    return changed


def repair_validation_strategy(proposal: dict[str, Any], *, release_selector: str) -> bool:
    """Restore release-scoped validation obligations for weak proof language."""

    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_reference(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    proof_capability = completion_text.proof_capability_phrase(proposal)
    proof_summary = validation_proof_summary(completion_text.proof_boundary(proposal))
    rows = [
        sentence_text(f"Success proof for release {release} includes {proof_capability}.", limit=700),
        sentence_text(f"Result proof confirms the user can {completion_text.outcome_action_phrase(outcome)} with the visible result explained.", limit=520),
        sentence_text(f"Evidence proof stays inside this first-release promise: {proof_summary}.", limit=620),
        sentence_text(f"Blocked-path proof: missing input, invalid state, failed validation, absent explanation, or unresolved review blocks readiness for {state_object}.", limit=520),
        sentence_text(f"Replay proof: {state_object} can be reconstructed with actor, timestamp, prior state, current state, result, and explanation.", limit=520),
        sentence_text(f"Access and privacy proof: only authorized actors can view or mutate protected state, and audit, retention, privacy, accessibility, and safety obligations stay visible.", limit=520),
        sentence_text(
            "Each owned product behavior must prove its successful path and explain what happens when required input is missing.",
            limit=520,
        ),
        sentence_text(f"Release proof: {label} cannot promote unless validation output proves the visible product outcome and stays inside the first-release promise.", limit=520),
    ]
    return set_sentence_list(proposal, "validation_strategy", rows)


def repair_backlog_success_language(proposal: dict[str, Any], *, release_selector: str) -> bool:
    """Restore backlog proof and validation text after a preflight failure."""

    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_reference(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    proof_capability = completion_text.proof_capability_phrase(proposal)
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    changed = False
    for row in dict_rows(proposal.get("backlog")):
        subject = completion_text.workstream_subject(row, fallback=label, components=components)
        metrics = [
            sentence_text(f"{subject} success proof for release {release} includes {proof_capability}.", limit=700),
            sentence_text(f"{subject} result proof confirms the user can {outcome_action} with a clear explanation.", limit=500),
            sentence_text(f"{subject} explains missing or invalid input before a result is presented.", limit=500),
            sentence_text(f"{subject} preserves enough {state_object} context to explain the actor, status, result, and recovery path.", limit=500),
            sentence_text(f"{subject} stays inside the first-release promise and keeps deferred outcomes out of the success claim.", limit=500),
        ]
        if sequence_needs_repair(row.get("success_metrics"), required_tokens=("success", "block", "replay", "evidence")):
            changed |= set_sentence_list(row, "success_metrics", metrics, limit=1000)
        validation = [
            sentence_text(f"Validate a successful {path_phrase(subject)}, a blocked path, replay, role access, privacy handling, and evidence visibility.", limit=360),
            sentence_text(f"Reject release readiness when {subject} cannot explain its result, changed state, access posture, or recovery path.", limit=420),
        ]
        if sequence_needs_repair(row.get("validation"), required_tokens=("success", "block", "replay")):
            changed |= set_sentence_list(row, "validation", validation)
    return changed


def repair_project_intelligence_validation(proposal: dict[str, Any], *, release_selector: str) -> bool:
    """Repair project-intelligence validation obligations after preflight failure."""

    intelligence = proposal.get("project_intelligence")
    if not isinstance(intelligence, dict):
        return False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    state_object = completion_text.state_reference(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    proof_capability = completion_text.proof_capability_phrase(proposal)
    rows = [
        sentence_text(f"Validate that success proof includes {proof_capability}.", limit=420),
        sentence_text(f"Validate that result proof confirms the user can {outcome_action} with a clear explanation.", limit=420),
        sentence_text(f"Validate a blocked path where missing input, invalid state, failed validation, or missing explanation prevents readiness.", limit=420),
        sentence_text(f"Validate replay for {state_object} with actor, timestamp, status, result, and explanation.", limit=420),
        sentence_text(f"Validate role-appropriate access, privacy, audit, retention, accessibility, safety, and recovery behavior before release {release}.", limit=420),
        sentence_text("Validate that release proof stays inside the accepted product promise without borrowing deferred outcomes.", limit=500),
    ]
    return set_sentence_list(intelligence, "validation_obligations", rows)


def repair_generated_sentence_lists(proposal: dict[str, Any], *, release_selector: str) -> bool:
    """Repair malformed generated prose across confirmed proposal artifacts."""

    changed = False
    release = greenfield_programs.proposal_release_selector(proposal, release_selector)
    label = completion_text.project_title(proposal)
    state_object = completion_text.state_reference(proposal)
    action = completion_text.action_phrase(proposal)
    outcome = completion_text.outcome_phrase(proposal)
    proof_boundary = completion_text.proof_boundary(proposal)
    proof_clause = clean_generated_text(proof_boundary).strip(" .")
    actors = completion_text.actor_summary(proposal)
    primary_actor = completion_text.primary_actor_phrase(proposal)
    actor_phrase = actor_phrase_for_sentence(actors)
    outcome_action = completion_text.outcome_action_phrase(outcome)
    components = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    intent = proposal.get("intent")
    if isinstance(intent, dict):
        changed |= repair_bad_scalar(
            intent,
            "summary",
            fallback=(
                f"{label} helps {actor_phrase} {action}, keeps {state_object} explainable, and proves that "
                f"{actor_phrase} can {outcome_action} without trusting incomplete information."
            ),
        )
        changed |= repair_bad_scalar(
            intent,
            "product_story",
            fallback=(
                f"{label} gives {actor_phrase} a first release path to {action}, {outcome_action}, and recover when "
                "required input, access, privacy, safety, or explanation is missing."
            ),
        )
    project_brief = proposal.get("project_brief")
    if isinstance(project_brief, dict):
        changed |= repair_bad_scalar(
            project_brief,
            "purpose",
            fallback=(
                f"{label} exists so {actor_phrase} can {action}, {outcome_action}, and keep the proof inside this "
                f"accepted boundary: {proof_clause}."
            ),
        )
    if validation_strategy_needs_repair(proposal):
        changed |= repair_validation_strategy(proposal, release_selector=release_selector)
    for row in dict_rows(proposal.get("backlog")):
        title = completion_text.workstream_subject(
            row,
            fallback=completion_text.project_title(proposal),
            components=components,
        )
        changed |= repair_bad_scalar(
            row,
            "problem",
            fallback=f"{title} matters because users need {outcome} to be correct, understandable, and recoverable when information is missing.",
        )
        changed |= repair_bad_scalar(row, "customer", fallback=completion_text.actor_summary(proposal))
        changed |= repair_bad_scalar(
            row,
            "opportunity",
            fallback=f"{title} gives the team a small release slice where {actor_phrase} can {action} before broader variants are added.",
        )
        changed |= repair_bad_scalar(
            row,
            "product_view",
            fallback=f"{title} is complete when users can {action}, {completion_text.outcome_action_phrase(outcome)}, and recover from bad or incomplete input.",
        )
        changed |= repair_bad_scalar(
            row,
            "domain_risk",
            fallback=f"Domain risk: {title} can mislead users if {state_object} changes without a clear result explanation and recovery path.",
        )
        changed |= repair_bad_scalar(
            row,
            "security_posture",
            fallback=(
                f"Security and privacy posture: {title} states who can see or change product state. "
                f"{title} keeps audit, retention, safety, and recovery obligations visible before release."
            ),
        )
        if sequence_has_text_repair(row.get("success_metrics")):
            proof_capability = completion_text.proof_capability_phrase(proposal)
            metrics = [
                f"{title} success proof for release {release} includes {proof_capability}.",
                f"{title} result proof confirms the user can {outcome_action} with a clear explanation.",
                f"{title} explains missing or invalid input before a result is presented.",
                f"{title} preserves enough {state_object} context to explain the actor, status, result, and recovery path.",
                f"{title} stays inside the first-release promise without borrowing deferred outcomes.",
            ]
            changed |= set_sentence_list(row, "success_metrics", metrics)
            changed |= repair_domain_intelligence_metrics(
                row,
                title=title,
                action=action,
                outcome=outcome,
                state_object=state_object,
            )
        if sequence_has_text_repair(row.get("validation")):
            changed |= set_sentence_list(
                row,
                "validation",
                [
                    f"Validate a successful {path_phrase(title)}, a blocked path, replay, role access, privacy handling, and evidence visibility.",
                    f"Reject release readiness when {title} cannot explain its result, changed state, access posture, or recovery path.",
                ],
            )
        changed |= repair_domain_intelligence_metrics(
            row,
            title=title,
            action=action,
            outcome=outcome,
            state_object=state_object,
        )
        changed |= repair_domain_intelligence_sentence_lists(
            row,
            title=title,
            action=action,
            outcome=outcome,
            state_object=state_object,
            proof_boundary=proof_boundary,
            actor_summary=actors,
            primary_actor=primary_actor,
        )
        if sequence_has_text_repair(row.get("rationale_lines")):
            changed |= set_sentence_list(
                row,
                "rationale_lines",
                [
                    f"- why now: {title} belongs in release {release} because it helps produce the first user-visible outcome.",
                    f"- expected outcome: {title} produces a visible result with blocked and recovery paths.",
                    f"- tradeoff: {title} keeps the first slice narrow while deferring broader variants until their own outcome is proven.",
                    f"- deferred for now: {title} does not expand into adjacent workflows outside the first-release promise.",
                    f"- ranking basis: {title} ranks ahead of optional work because it protects the result, recovery path, and user trust.",
                ],
            )
    changed |= repair_component_sentence_lists(proposal)
    for index, row in enumerate(dict_rows(proposal.get("diagrams")), start=1):
        changed |= repair_bad_scalar(
            row,
            "title",
            fallback=completion_text.diagram_title(row, proposal=proposal, index=index),
        )
        changed |= repair_bad_scalar(
            row,
            "summary",
            fallback=f"Shows how {completion_text.project_title(proposal)} preserves first-path state, evidence, and proof.",
        )
    return changed


__all__ = ["repair_preflight_issues"]
