"""Build Radar, program, and release records for confirmed greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_text_model as backlog_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import (
    outcome_action_phrase as _outcome_action_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import system_component_name
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items as _join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import problem_text as _problem_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label as _title_label
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import (
    build_workstream_domain_intelligence,
)


def confirmed_workstream_titles(
    *,
    label: str,
    components: list[dict[str, Any]],
    internal_systems: list[str],
    first_path: str,
    state_object: str,
    proof_boundary: str,
    human_actors: list[str],
) -> tuple[str, str, str]:
    labels = [
        backlog_text.workstream_subject(str(row.get("label", "")).strip())
        for row in components
        if str(row.get("label", "")).strip()
    ]
    actor = backlog_text.lead_actor_label(human_actors)
    action = backlog_text.imperative_action_phrase(first_path)
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    proof_label = labels[-1] if len(labels) > 2 else (labels[0] if labels else label)
    outcome = backlog_text.first_path_outcome(first_path, proof_boundary=proof_boundary)
    if outcome and not backlog_text.generic_title_outcome(outcome):
        workflow_actor = actor or backlog_text.actor_from_action(action) or "user"
        workflow = f"Let {workflow_actor} {_outcome_action_phrase(outcome)}"
    elif action:
        action_actor, action_tail = backlog_text.actor_action_parts(action)
        workflow_actor = action_actor or actor or "user"
        workflow_action = backlog_text.base_leading_action(
            action_tail or backlog_text.strip_actor_prefix(action, workflow_actor) or action
        )
        workflow = f"Let {workflow_actor} {workflow_action}"
    elif labels:
        workflow = f"Make {labels[0]} usable in the first path"
    else:
        workflow = f"Make {label} usable in the first path"
    state_changer = backlog_text.state_changer_label(labels, state_label=state_label)
    if state_changer:
        boundary = f"Keep {state_label} clear after {state_changer} changes it"
    else:
        boundary = f"Keep {state_label} clear and reviewable"
    proof_subject = state_label or backlog_text.proof_title_object(proof_boundary) or proof_label
    proof = f"Show why {proof_subject} can be trusted"
    return (
        _title_label(workflow) or workflow,
        _title_label(boundary) or boundary,
        _title_label(proof) or proof,
    )


def confirmed_evidence_record_label(*, label: str, proof_boundary: str, internal_systems: list[str]) -> str:
    for system in internal_systems:
        first = str(system).split("—", 1)[0].split("-", 1)[0].split(":", 1)[0].strip()
        name = first.casefold()
        if any(token in name for token in ("evidence", "audit", "proof", "ledger", "history", "trace")):
            if first:
                return f"{system_component_name(first)} proof record"
    if proof_boundary:
        return f"{label} proof record"
    return f"{label} proof record"


def confirmed_program(
    *,
    label: str,
    parent_title: str,
    release: str,
    workflow_title: str,
    boundary_title: str,
    proof_title: str,
    components: list[dict[str, Any]],
) -> dict[str, Any]:
    component_ids = [str(row["component_id"]) for row in components]
    return {
        "shape": "program_with_waves",
        "wave_count": 3,
        "recommended_first_wave": f"{label} first-path proof",
        "blueprint": {
            "program_type": "greenfield_program",
            "parent_workstream": parent_title,
            "child_workstream_strategy": (
                f"Build the first usable {label.lower()} path, then harden its state handoffs and proof review."
            ),
            "child_workstreams": [workflow_title, boundary_title, proof_title],
            "wave_to_workstream_policy": "Waves follow product build order; each child owns a distinct implementation slice.",
            "release_strategy": f"Target release {release} only after first-path, state replay, and proof review pass.",
            "recommended_wave_order": [
                f"{label} first-path proof",
                f"{label} state and evidence boundary",
                f"{label} release review",
            ],
            "evidence_tier": "odylith_assumption",
        },
        "waves": [
            {
                "wave": 1,
                "label": f"{label} first-path proof",
                "goal": f"Prove the accepted {label.lower()} first path from intake to release-review outcome.",
                "validation_gate": f"{label} success, validation failure, and recovery path tests pass.",
                "workstream_titles": [workflow_title],
                "component_focus": component_ids[:2],
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave": 2,
                "label": f"{label} state and evidence boundary",
                "goal": f"Make {label.lower()} state, proof packet, ownership, and review boundaries explicit.",
                "validation_gate": f"{label} state replay and release-evidence traceability tests pass.",
                "workstream_titles": [boundary_title],
                "component_focus": component_ids,
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave": 3,
                "label": f"{label} release review",
                "goal": f"Prepare release {release} evidence, access posture, non-goals, and promotion criteria.",
                "validation_gate": f"{label} release proof names validation result, release decision, failure mode, and recovery expectation.",
                "workstream_titles": [proof_title],
                "component_focus": [component_ids[-1]],
                "evidence_tier": "odylith_assumption",
            },
        ],
    }


def confirmed_release_plan(
    *,
    label: str,
    label_slug: str,
    release: str,
    workflow_title: str,
    boundary_title: str,
    proof_title: str,
) -> dict[str, Any]:
    return {
        "selector": release,
        "label": f"{label} {release} first path",
        "provisional_release_id": f"release-{label_slug}-{slugify(release)}",
        "strategy": f"Promote {label.lower()} only after first-path, state replay, access, and evidence review proof pass.",
        "target_workstream_titles": [workflow_title, boundary_title, proof_title],
        "release_stages": [
            {
                "stage": "wave-1",
                "label": f"{label} first-path proof",
                "release_gate": f"{label} first path passes success, failure, replay, and evidence checks.",
                "workstream_titles": [workflow_title],
            }
        ],
        "milestones": [
            {
                "name": f"{label} release review accepted",
                "exit_criteria": f"The product owner accepts the {label.lower()} first path, non-goals, and release proof.",
            }
        ],
        "promotion_criteria": [
            f"{label} first-path proof passes with representative inputs.",
            f"{label} state replay matches the release-review outcome decision.",
            f"{label} release evidence maps every readiness assertion to validation output.",
        ],
        "evidence_tier": "odylith_assumption",
    }


def confirmed_backlog_rows(
    *,
    label: str,
    parent_title: str,
    workflow_title: str,
    boundary_title: str,
    proof_title: str,
    state_object: str,
    evidence_record: str,
    product_story: str,
    first_path: str,
    proof_boundary: str,
    human_actors: list[str],
    internal_systems: list[str],
    external_systems: list[str],
    non_goals: list[str],
    components: list[dict[str, Any]],
    diagram_slugs: Mapping[str, str],
    problem: str = "",
    customer: str = "",
    opportunity: str = "",
    product_view: str = "",
    success_metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    component_ids = [str(row["component_id"]) for row in components]
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    evidence_label = _domain_object_label(evidence_record, fallback=evidence_record)
    problem_summary = _problem_text(label=label, problem=problem, product_story=product_story, first_path=first_path)
    opportunity_summary = _short_summary(opportunity, limit=360)
    product_view_summary = _short_summary(product_view, limit=360)
    first_path_summary = _short_summary(first_path, limit=380)
    proof_summary = backlog_text.proof_claim_summary(proof_boundary, limit=340)
    clauses = first_path_clauses(
        first_path_summary,
        proof_boundary=proof_summary,
        action_fallback=backlog_text.first_action_clause(first_path_summary) or "complete the accepted product path",
        capability_fallback=backlog_text.first_action_clause(first_path_summary) or "complete the accepted product path",
        capability_limit=340,
        outcome_limit=240,
    )
    actors = backlog_text.join_actor_labels(human_actors) or _short_summary(customer, limit=260) or f"{label} users and reviewers"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    primary_component = backlog_text.workstream_subject(backlog_text.component_label_at(components, 0, fallback=f"{label} first path"))
    second_component = backlog_text.workstream_subject(backlog_text.component_label_at(components, 1, fallback=primary_component))
    proof_component = backlog_text.workstream_subject(
        backlog_text.component_label_at(components, len(components) - 1, fallback=f"{label} proof review")
    )
    proof_record_label = _title_label(f"{proof_component} proof record") or evidence_label
    primary_user_action = backlog_text.sentence_fragment(
        first_path_action_phrase(
            first_path_summary,
            fallback=clauses.action_chain or clauses.model.material_action or "complete the accepted product path",
            max_fragments=3,
            limit=180,
        )
    )
    first_path_entry_text = backlog_text.sentence_fragment(clauses.model.material_action or primary_user_action or clauses.action_chain)
    first_path_capability = backlog_text.capability_action_clause(
        primary_user_action or backlog_text.sentence_fragment(clauses.capability_chain) or first_path_entry_text
    )
    first_path_full_capability = backlog_text.capability_action_clause(backlog_text.sentence_fragment(clauses.capability_chain) or first_path_capability)
    outcome_summary = backlog_text.sentence_fragment(clauses.visible_result) or backlog_text.first_path_outcome(first_path_summary, proof_boundary=proof_boundary)
    outcome_action = _outcome_action_phrase(outcome_summary)
    proof_focus = backlog_text.proof_focus_phrase(proof_summary, fallback="release decision")
    dependency_outcome = outcome_summary or "the promised first-path result"
    first_path_action = backlog_text.capability_action_clause(primary_user_action or first_path_entry_text or first_path_capability)
    first_path_proof_capability = first_path_capability_phrase(
        first_path_summary,
        fallback=first_path_action,
        gerund=True,
        limit=340,
    )
    path_entry_story = backlog_text.sentence_fragment(first_path_entry_text or first_path_capability or first_path_summary)
    metric_actor = backlog_text.problem_actor_subject(actors, fallback=f"{label} user")
    downstream_actor = backlog_text.supporting_actor_label(human_actors)
    downstream_subject = backlog_text.problem_actor_subject(downstream_actor, fallback="the next participant") if downstream_actor else "The next participant"
    parent_problem = backlog_text.program_problem(
        label=label,
        actors=actors,
        story=product_story,
        capability=first_path_action,
        outcome=outcome_summary,
        fallback=problem_summary,
    )
    parent_opportunity = f"Ship one complete outcome: a representative user can {first_path_action} and use {outcome_summary} to decide what to do next."
    parent_view = f"{label} should feel complete when {actors} can {first_path_action}, see {outcome_summary}, and understand what remains outside the first release."
    first_slice_action = first_path_full_capability or first_path_action
    if outcome_summary and not backlog_text.shares_product_terms(first_slice_action, outcome_summary):
        first_slice = f"Deliver one complete path where a user can {first_slice_action} and see {outcome_summary}."
    else:
        first_slice = f"Deliver one complete path where a user can {first_slice_action}."
    parent = _backlog_row(
        label=label,
        title=parent_title,
        problem=parent_problem,
        customer=actors,
        opportunity=parent_opportunity,
        product_view=parent_view,
        first_slice=first_slice,
        metrics=[
            *(success_metrics or [])[:1],
            f"Success proof connects {first_path_proof_capability} to {outcome_summary} without adjacent scope being pulled into the release.",
            f"{state_label} state responsibility remains understandable when input is accepted, blocked, corrected, or reviewed.",
            f"{proof_component} keeps the success evidence replayable so a reviewer can see what happened and why.",
        ],
        component_focus=component_ids,
        diagram_focus=list(diagram_slugs.values()),
        dependencies=[
            f"Depends on accepted participants, required source context, and product systems that can produce and review {dependency_outcome}."
        ],
        interfaces=[
            f"Release scope connects {primary_component}, {second_component}, and {proof_component} without absorbing deferred scope."
        ],
        validation=[
            f"Run the complete user path, the missing-input path, and the corrected-input path against the promised result: {outcome_summary}."
        ],
        state_object=state_label,
        evidence_record=evidence_label,
        first_path=first_path_summary,
        proof_boundary=proof_summary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
        workstream_type="program_parent",
    )
    workflow = _backlog_row(
        label=label,
        title=workflow_title,
        problem=(
            f"{metric_actor} needs the first interaction to end in {outcome_summary}, not just captured input. "
            f"If the path accepts incomplete details or hides why it stopped, {downstream_subject[:1].lower()}{downstream_subject[1:]} cannot act on the result with confidence."
        ),
        customer=actors,
        opportunity=(
            f"Turn the first user action into a complete, reviewable outcome: the user provides what the product needs, sees {outcome_summary}, and leaves enough context for follow-up."
        ),
        product_view=(
            f"{metric_actor} can {first_path_action}. The product checks the details, explains missing information before it produces a result, "
            f"and shows {outcome_summary}. {downstream_subject} receives the saved context needed to continue without reinterpreting the user's intent."
        ),
        first_slice=(
            f"Start with one representative path where {metric_actor[:1].lower()}{metric_actor[1:]} can {first_path_action}, "
            f"{outcome_action}, and see what to fix when required information is missing."
        ),
        metrics=[
            f"The first interaction proves {first_path_proof_capability} and {outcome_summary}.",
            "Missing or invalid information produces clear correction guidance instead of a misleading result.",
            f"{downstream_subject} can use the saved context without asking the user to repeat the same details.",
        ],
        component_focus=component_ids[: max(1, min(2, len(component_ids)))],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["sequence"], diagram_slugs["state_evidence"]],
        dependencies=[f"{second_component} must be ready to receive the state, blocker, and recovery context from this interaction."],
        interfaces=[f"Expose only the user entrypoints and commands needed for {path_entry_story}."],
        validation=[f"Exercise the completed path, missing-input path, correction path, and next-step context from {primary_component}."],
        state_object=state_label,
        evidence_record=evidence_label,
        first_path=first_path_summary,
        proof_boundary=proof_summary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    boundary = _backlog_row(
        label=label,
        title=boundary_title,
        problem=f"{state_label} becomes untrustworthy when a visible change cannot explain who made it, what status it reached, or why it is blocked.",
        customer=actors,
        opportunity=(
            f"Give the product a durable memory of {state_label}: current status, source reference, blocker, recovery note, and what should happen next."
        ),
        product_view=(
            f"{second_component} keeps {state_label} understandable after each change. A reviewer can see the current state, "
            "the reason behind it, the blocker if one exists, and the next useful action."
        ),
        first_slice=(
            f"Implement the smallest {state_label} lifecycle that can show a valid update, a blocked update, replay, and recovery context without rewriting sibling state."
        ),
        metrics=[
            f"Every {state_label} change names actor, source, status, owner, and expected result.",
            "Questionable input is accepted, quarantined, or rejected before it changes the result.",
            "Downstream consumers can distinguish success, blocked, stale, and review-needed states without reading implementation details.",
        ],
        component_focus=[component_ids[1]] if len(component_ids) > 1 else component_ids,
        diagram_focus=[
            diagram_slugs["state_evidence"],
            diagram_slugs["component_boundaries"],
            diagram_slugs["ownership"],
        ],
        dependencies=[f"{primary_component} supplies the user action; accepted external sources stay explicit when the first path names them."],
        interfaces=[f"Keep state, review, and external-dependency interfaces separate around {second_component}."],
        validation=[f"Reject any transition that cannot explain {state_label}, actor, status, owner, and result."],
        state_object=state_label,
        evidence_record=evidence_label,
        first_path=first_path_summary,
        proof_boundary=proof_summary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    proof = _backlog_row(
        label=label,
        title=proof_title,
        problem=(
            "Release review is not credible when the product can show an outcome but cannot explain the evidence, limits, and decision behind it."
        ),
        customer=actors,
        opportunity=(
            "Turn the completed path into a reviewable release claim that connects validation results, state references, "
            "the release decision, and deferred scope."
        ),
        product_view=(
            f"{proof_component} explains why the outcome can be trusted. It shows whether {state_label}, validation output, {proof_focus}, required context, "
            f"and deferred scope support the promised result: {outcome_summary}."
        ),
        first_slice=(
            f"Produce one {proof_record_label} that links the first path, {state_label}, validation result, release decision, and deferred scope."
        ),
        metrics=[
            f"{proof_record_label} links accepted input, {state_label}, validation output, release decision, and outcome.",
            "Missing evidence blocks proof review instead of producing a release-ready claim.",
            "The proof view checks the promised result without expanding deferred scope.",
            f"Deferred scope remains visible: {non_goal_text}.",
        ],
        component_focus=[component_ids[-1]] if component_ids else [],
        diagram_focus=[diagram_slugs["ownership"], diagram_slugs["proof_review"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on {second_component} state replay, {primary_component} path proof, and release-review access posture."],
        interfaces=[
            f"{proof_component} exposes validation summary, state references, evidence references, release decision, and deferred scope."
        ],
        validation=[
            "Proof review fails closed when success evidence, replay evidence, access proof, privacy proof, or review evidence is missing."
        ],
        state_object=state_label,
        evidence_record=proof_record_label,
        first_path=first_path_summary,
        proof_boundary=proof_summary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    return [parent, workflow, boundary, proof]


def _backlog_row(
    *,
    label: str,
    title: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    first_slice: str,
    metrics: list[str],
    component_focus: list[str],
    diagram_focus: list[str],
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
    workstream_type: str = "implementation",
) -> dict[str, Any]:
    return {
        "title": title,
        "workstream_type": workstream_type,
        "problem": problem,
        "customer": customer,
        "opportunity": opportunity,
        "product_view": product_view,
        "success_metrics": metrics,
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "recommended_first_slice": first_slice,
        "component_focus": component_focus,
        "related_diagram_slugs": diagram_focus,
        "dependencies": dependencies,
        "interfaces": interfaces,
        "validation": validation,
        "evidence_tier": "user_intent" if workstream_type == "program_parent" else "odylith_assumption",
        "rationale_lines": backlog_text.rationale_lines(
            label=label,
            title=title,
            opportunity=opportunity,
            first_slice=first_slice,
            proof_boundary=proof_boundary,
        ),
        "domain_intelligence": build_workstream_domain_intelligence(
            label=label,
            row_title=title,
            problem=problem,
            opportunity=opportunity,
            product_view=product_view,
            first_slice=first_slice,
            metrics=metrics,
            dependencies=dependencies,
            interfaces=interfaces,
            validation=validation,
            state_object=state_object,
            evidence_record=evidence_record,
            first_path=first_path,
            proof_boundary=proof_boundary,
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
        ),
    }


__all__ = [
    "confirmed_backlog_rows",
    "confirmed_evidence_record_label",
    "confirmed_program",
    "confirmed_release_plan",
    "confirmed_workstream_titles",
]
