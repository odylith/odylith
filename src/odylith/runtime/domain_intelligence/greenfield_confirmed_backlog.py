"""Build Radar, program, and release records for confirmed greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_actions as backlog_actions
from odylith.runtime.domain_intelligence import greenfield_confirmed_backlog_text_model as backlog_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import (
    outcome_action_phrase as _outcome_action_phrase,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_row import (
    build_backlog_row as _backlog_row,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_row import (
    first_success_metric_rows as _first_success_metric_rows,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import system_component_name
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_domain_object_label as _compact_domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items as _join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import label_with_suffix as _label_with_suffix
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import problem_text as _problem_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label as _sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label as _title_label
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_sentence
from odylith.runtime.domain_intelligence.greenfield_text import clean_text as _clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values as _text_values
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_release_scope_limits import proof_boundary_limit_text


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
    actor_owned_action = backlog_actions.workflow_title_action(first_path=first_path, actor=actor, fallback=action)
    state_label = _compact_domain_object_label(state_object, fallback=f"{label} state")
    proof_label = labels[-1] if len(labels) > 2 else (labels[0] if labels else label)
    outcome = backlog_text.first_path_outcome(first_path, proof_boundary=proof_boundary)
    if (
        outcome
        and not backlog_text.generic_title_outcome(outcome)
        and (backlog_actions.prefer_outcome_title(outcome) or _malformed_workflow_title_action(actor_owned_action or action))
    ):
        workflow_actor = actor or backlog_text.actor_from_action(action) or "user"
        workflow = f"Let {workflow_actor} {_outcome_action_phrase(outcome)}"
    elif actor_owned_action:
        workflow_actor = actor or backlog_text.actor_from_action(actor_owned_action) or "user"
        workflow = f"Let {workflow_actor} {actor_owned_action}"
    elif outcome and not backlog_text.generic_title_outcome(outcome):
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
        _workstream_title_label(workflow),
        _title_label(boundary) or boundary,
        _title_label(proof) or proof,
    )


def _workstream_title_label(value: str) -> str:
    text = _compact_workstream_title_connector(str(value or ""))
    return _title_label(text) or text


def _compact_workstream_title_connector(value: str) -> str:
    text = value.strip()
    marker = "while keeping "
    search_from = 0
    while True:
        index = text.casefold().find(marker, search_from)
        if index < 0:
            return text
        if index > 0 and text[index - 1].isalnum():
            search_from = index + len(marker)
            continue
        before = text[:index].rstrip()
        after = text[index + len(marker) :].lstrip()
        text = f"{before} with {after}".strip() if before else f"with {after}".strip()
        search_from = max(len(before), 0)


def _malformed_workflow_title_action(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text.endswith(",") or re.search(r"\brecorded\s+attaches\b", text, flags=re.IGNORECASE))


def confirmed_evidence_record_label(*, label: str, proof_boundary: str, internal_systems: list[str]) -> str:
    for system in internal_systems:
        first = str(system).split("—", 1)[0].split("-", 1)[0].split(":", 1)[0].strip()
        name = first.casefold()
        if any(token in name for token in ("evidence", "audit", "proof", "ledger", "history", "trace")):
            if first:
                return _proof_record_label(first)
    if proof_boundary:
        return _proof_record_label(label)
    return _proof_record_label(label)


def _proof_record_label(value: str) -> str:
    base = _title_label(system_component_name(value)) or _title_label(value) or value.strip()
    lowered = base.casefold()
    if lowered.endswith(" proof record"):
        return base
    if lowered.endswith(" record") and " proof " in f" {lowered} ":
        return base
    if lowered.endswith((" audit ledger", " evidence ledger", " history ledger", " proof ledger", " trace ledger", " ledger")):
        return f"{base} Record"
    if lowered.endswith(" proof"):
        return f"{base} Record"
    return f"{base} Proof Record"


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
    label_ref = _sentence_label(label)
    component_ids = [str(row["component_id"]) for row in components]
    first_path_proof = _label_with_suffix(label, "first-path proof")
    state_boundary = _label_with_suffix(label, "state and evidence boundary")
    release_review = _label_with_suffix(label, "release review")
    release_proof = _label_with_suffix(label, "release proof")
    return {
        "shape": "program_with_waves",
        "wave_count": 3,
        "recommended_first_wave": first_path_proof,
        "blueprint": {
            "program_type": "greenfield_program",
            "parent_workstream": parent_title,
            "child_workstream_strategy": (
                f"Build the first usable {label_ref} path, then harden its state handoffs and proof review."
            ),
            "child_workstreams": [workflow_title, boundary_title, proof_title],
            "wave_to_workstream_policy": "Waves follow product build order; each child owns a distinct implementation slice.",
            "release_strategy": f"Target release {release} only after first-path, state replay, and proof review pass.",
            "recommended_wave_order": [
                first_path_proof,
                state_boundary,
                release_review,
            ],
            "evidence_tier": "odylith_assumption",
        },
        "waves": [
            {
                "wave": 1,
                "label": first_path_proof,
                "goal": f"Prove the accepted {label_ref} first path from intake to release-review outcome.",
                "validation_gate": f"{label} success, validation failure, and recovery path tests pass.",
                "workstream_titles": [workflow_title],
                "component_focus": component_ids[:2],
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave": 2,
                "label": state_boundary,
                "goal": f"Make {label_ref} state, proof packet, ownership, and review boundaries explicit.",
                "validation_gate": f"{label} state replay and release-evidence traceability tests pass.",
                "workstream_titles": [boundary_title],
                "component_focus": component_ids,
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave": 3,
                "label": release_review,
                "goal": f"Prepare release {release} evidence, access posture, non-goals, and promotion criteria.",
                "validation_gate": (
                    f"{release_proof} names validation result, release decision, failure mode, and recovery expectation."
                ),
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
    label_ref = _sentence_label(label)
    first_path_proof = _label_with_suffix(label, "first-path proof")
    release_review_accepted = _label_with_suffix(label, "release review accepted")
    release_evidence = _label_with_suffix(label, "release evidence")
    return {
        "selector": release,
        "label": f"{label} {release} first path",
        "provisional_release_id": f"release-{label_slug}-{slugify(release)}",
        "strategy": f"Promote {label_ref} only after first-path, state replay, access, and evidence review proof pass.",
        "target_workstream_titles": [workflow_title, boundary_title, proof_title],
        "release_stages": [
            {
                "stage": "wave-1",
                "label": first_path_proof,
                "release_gate": f"{label} first path passes success, failure, replay, and evidence checks.",
                "workstream_titles": [workflow_title],
            }
        ],
        "milestones": [
            {
                "name": release_review_accepted,
                "exit_criteria": f"The product owner accepts the {label_ref} first path, non-goals, and release proof.",
            }
        ],
        "promotion_criteria": [
            f"{label} first-path proof passes with representative inputs.",
            f"{label} state replay matches the release-review outcome decision.",
            f"{release_evidence} maps every readiness assertion to validation output.",
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
    state_label = _compact_domain_object_label(state_object, fallback=f"{label} state")
    evidence_label = _domain_object_label(evidence_record, fallback=evidence_record)
    first_release_human_actors = backlog_text.first_release_actor_rows(human_actors)
    problem_summary = _problem_text(label=label, problem=problem, product_story=product_story, first_path=first_path)
    problem_summary = _first_release_problem_summary(problem_summary, human_actors)
    opportunity_summary = _short_summary(opportunity, limit=360)
    product_view_summary = _short_summary(product_view, limit=360)
    first_path_summary = _short_summary(first_path, limit=380)
    first_path_for_clauses = first_path or first_path_summary
    proof_summary = backlog_text.proof_claim_summary(proof_boundary, limit=340)
    clauses = first_path_clauses(
        first_path_for_clauses,
        proof_boundary=proof_summary,
        action_fallback=backlog_text.first_action_clause(first_path_summary) or "complete the accepted product path",
        capability_fallback=backlog_text.first_action_clause(first_path_summary) or "complete the accepted product path",
        capability_limit=340,
        outcome_limit=240,
    )
    actors = backlog_text.join_actor_labels(first_release_human_actors) or _short_summary(customer, limit=260) or f"{label} users and reviewers"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    proof_limit = proof_boundary_limit_text(proof_boundary)
    proof_non_goal_text = _join_items([*non_goals, proof_limit]) or non_goal_text
    primary_component = backlog_text.workstream_subject(backlog_text.component_label_at(components, 0, fallback=f"{label} first path"))
    second_component = backlog_text.workstream_subject(backlog_text.component_label_at(components, 1, fallback=primary_component))
    proof_component = backlog_text.workstream_subject(
        backlog_text.component_label_at(components, len(components) - 1, fallback=f"{label} proof review")
    )
    proof_record_label = _proof_record_label(proof_component) or evidence_label
    primary_user_action = backlog_text.sentence_fragment(
        first_path_action_phrase(
            first_path_for_clauses,
            fallback=clauses.action_chain or clauses.model.material_action or "complete the accepted product path",
            max_fragments=3,
            limit=180,
        )
    )
    first_path_entry_text = backlog_text.sentence_fragment(clauses.model.material_action or primary_user_action or clauses.action_chain)
    first_path_capability = backlog_text.capability_action_clause(
        primary_user_action or backlog_text.sentence_fragment(clauses.capability_chain) or first_path_entry_text
    )
    first_path_full_capability = _dedupe_capability_phrase(
        backlog_text.capability_action_clause(backlog_text.sentence_fragment(clauses.capability_chain) or first_path_capability)
    )
    outcome_summary = backlog_text.sentence_fragment(clauses.visible_result) or backlog_text.first_path_outcome(first_path_summary, proof_boundary=proof_boundary)
    outcome_action = _outcome_action_phrase(outcome_summary)
    proof_focus = backlog_text.proof_focus_phrase(proof_summary, fallback="release decision")
    state_responsibility = backlog_actions.state_responsibility_label(state_label)
    dependency_outcome = outcome_summary or "the promised first-path result"
    first_path_action = backlog_text.capability_action_clause(primary_user_action or first_path_entry_text or first_path_capability)
    first_path_proof_capability = _dedupe_capability_phrase(
        first_path_capability_phrase(
            first_path_for_clauses,
            fallback=first_path_action,
            limit=240,
            max_fragments=4,
        )
    )
    readable_first_path_proof_capability = readable_action_chain_phrase(
        first_path_for_clauses,
        fallback=first_path_proof_capability or first_path_action,
        limit=220,
        max_steps=4,
    )
    metric_first_path_proof_text = readable_action_chain_sentence(
        first_path_for_clauses,
        fallback=readable_first_path_proof_capability or first_path_proof_capability or first_path_action,
        limit=220,
        max_steps=5,
        include_visible_results=True,
    )
    metric_first_path_proof_capability = _metric_capability_summary(metric_first_path_proof_text)
    path_entry_story = backlog_text.sentence_fragment(first_path_entry_text or first_path_capability or first_path_summary)
    workflow_actor_label = backlog_text.lead_actor_label(first_release_human_actors) or f"{label} user"
    metric_evidence_scope = _evidence_scope_phrase(
        metric_first_path_proof_capability,
        actor=workflow_actor_label,
    )
    metric_actor = backlog_text.problem_actor_subject(workflow_actor_label, fallback=f"{label} user")
    downstream_candidate = backlog_text.supporting_actor_label(first_release_human_actors)
    downstream_actor = downstream_candidate if backlog_actions.actor_appears_in_path(first_path_for_clauses, downstream_candidate) else ""
    downstream_subject = backlog_text.problem_actor_subject(downstream_actor, fallback="the next participant") if downstream_actor else "The next participant"
    outcome_recipient = downstream_subject if downstream_actor else metric_actor
    recipient_phrase = backlog_actions.recipient_phrase(outcome_recipient)
    actor_owned_outcome_event = backlog_actions.actor_owned_outcome_event(
        outcome=outcome_summary,
        outcome_action=outcome_action,
        known_actors=first_release_human_actors,
    )
    follow_up_subject = downstream_subject if downstream_actor else metric_actor
    follow_up_inline = backlog_text.inline_actor_subject(follow_up_subject)
    metric_actor_inline = backlog_text.inline_actor_subject(metric_actor)
    metric_actor_needs = backlog_actions.actor_verb(metric_actor, singular="needs", plural="need")
    follow_up_receives = backlog_actions.actor_verb(follow_up_subject, singular="receives", plural="receive")
    workflow_audience = backlog_actions.join_distinct_labels([workflow_actor_label, downstream_actor])
    boundary_audience = workflow_audience or f"{label} operators and reviewers"
    proof_audience = downstream_actor or f"{label} proof reviewer"
    parent_problem = backlog_text.program_problem(
        label=label,
        actors=actors,
        story=product_story,
        capability=first_path_action,
        outcome=outcome_summary,
        fallback=problem_summary,
    )
    parent_opportunity = backlog_actions.parent_opportunity_sentence(
        capability=readable_first_path_proof_capability,
        outcome=outcome_summary,
        outcome_action=outcome_action,
        outcome_event=actor_owned_outcome_event,
        state_label=state_label,
        recipient=recipient_phrase,
    )
    parent_view = backlog_actions.parent_product_view_sentence(
        label=label,
        capability=readable_first_path_proof_capability,
        outcome=outcome_summary,
        outcome_action=outcome_action,
        outcome_event=actor_owned_outcome_event,
        state_label=state_label,
        recipient=recipient_phrase,
    )
    first_slice_capability = first_path_full_capability or first_path_proof_capability or first_path_action
    readable_first_slice_capability = readable_action_chain_phrase(
        first_path_for_clauses,
        fallback=first_slice_capability,
        limit=320,
        max_steps=7,
        include_visible_results=True,
    )
    first_slice_action = readable_first_slice_capability or first_slice_capability
    outcome_already_covered = backlog_text.result_terms_covered(
        outcome_summary, first_slice_action
    ) or backlog_text.result_terms_covered(outcome_action, first_slice_action)
    if outcome_summary and not outcome_already_covered and not backlog_text.shares_product_terms(first_slice_action, outcome_summary):
        outcome_followup = (
            f"show that {actor_owned_outcome_event}"
            if actor_owned_outcome_event
            else f"let {recipient_phrase} {outcome_action}"
        )
        first_slice = f"Prove one first-release path: {first_slice_action}, then {outcome_followup}."
    else:
        first_slice = f"Prove one first-release path: {first_slice_action}."
    first_slice = backlog_actions.dedupe_repeated_visible_result_tail(first_slice)
    if backlog_text.result_terms_covered(outcome_summary, metric_first_path_proof_capability):
        result_metric = (
            f"Success proof keeps {state_label} and {evidence_label} reviewable without adjacent scope being pulled into the release."
        )
    else:
        result_metric = (
            f"Success proof includes the first path actions: {metric_first_path_proof_capability}. "
            f"Verified result: {outcome_summary}. Adjacent scope stays outside the release."
        )
    workflow_action = backlog_actions.actor_interaction_action(
        first_path=first_path_for_clauses,
        actor=workflow_actor_label,
        fallback=first_path_action,
    )
    workflow_outcome_action = backlog_actions.append_outcome_action(
        action=workflow_action,
        outcome=outcome_summary,
        outcome_action=outcome_action,
        recipient=outcome_recipient,
        known_actors=first_release_human_actors,
    )
    workflow_missing_input_tail = backlog_actions.missing_input_tail(
        action=workflow_action,
        outcome=outcome_summary,
        outcome_already_appended=bool(workflow_outcome_action),
    )
    workflow_result_sentence = backlog_actions.workflow_result_sentence(
        action=workflow_action,
        outcome=outcome_summary,
        outcome_action=outcome_action,
        recipient=outcome_recipient,
        known_actors=first_release_human_actors,
    )
    workflow_goal_phrase = (
        f"show that {actor_owned_outcome_event}"
        if actor_owned_outcome_event
        else f"let them {outcome_action}"
    )
    workflow_followup_clause = (
        f"the product shows that {actor_owned_outcome_event}"
        if actor_owned_outcome_event
        else (
            "keeps the saved result reviewable"
            if _outcome_repeats_action(
                action=workflow_action,
                outcome=outcome_summary,
                outcome_action=outcome_action,
            )
            else f"lets {recipient_phrase} {outcome_action}"
        )
    )
    workflow_metric_sentence = (
        f"The first interaction proves this path: {metric_first_path_proof_capability}. "
        f"It also shows that {actor_owned_outcome_event}."
        if actor_owned_outcome_event
        else (
            f"The first interaction proves this path: {metric_first_path_proof_capability}. It also keeps the saved result reviewable."
            if _outcome_repeats_action(
                action=metric_first_path_proof_capability,
                outcome=outcome_summary,
                outcome_action=outcome_action,
            )
            else f"The first interaction proves this path: {metric_first_path_proof_capability}. It also lets {recipient_phrase} {outcome_action}."
        )
    )
    parent = _backlog_row(
        label=label,
        title=parent_title,
        problem=parent_problem,
        customer=actors,
        opportunity=parent_opportunity,
        product_view=parent_view,
        first_slice=first_slice,
        metrics=[
            *_first_success_metric_rows(success_metrics),
            result_metric,
            f"{state_responsibility} remains understandable when input is accepted, blocked, corrected, or reviewed.",
            f"The proof ledger keeps {proof_component} success evidence replayable so a reviewer can see what happened and why.",
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
        human_actors=first_release_human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
        workstream_type="program_parent",
    )
    workflow = _backlog_row(
        label=label,
        title=workflow_title,
        problem=(
            f"{metric_actor} {metric_actor_needs} the first interaction to {workflow_goal_phrase}, not just captured input. "
            f"If the path accepts incomplete details or hides why it stopped, {follow_up_inline} cannot act on the result with confidence."
        ),
        customer=workflow_actor_label,
        opportunity=(
            f"Prove the first actor-owned action can complete with reviewable follow-up: {metric_actor_inline} can {workflow_action}. "
            f"Follow-up evidence remains reviewable because the product preserves the saved context: {workflow_followup_clause}."
        ),
        product_view=(
            f"{metric_actor} can {workflow_action}. The product checks the details, explains missing information before returning a result, "
            f"{workflow_result_sentence}. {follow_up_subject} {follow_up_receives} the saved context needed to continue without reinterpreting the user's intent."
        ),
        first_slice=(
            f"One representative path where {metric_actor_inline} can {workflow_action}"
            f"{workflow_outcome_action}{workflow_missing_input_tail}."
        ),
        metrics=[
            (
                f"First interaction evidence covers {metric_evidence_scope}. "
                "It includes success, blocked input, replay, and handoff checks."
                if backlog_text.result_terms_covered(outcome_action, metric_first_path_proof_capability)
                else workflow_metric_sentence
            ),
            "Missing or invalid information produces clear correction guidance instead of a misleading result.",
            f"{follow_up_subject} can use the saved context without asking the user to repeat the same details.",
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
        human_actors=first_release_human_actors,
        intelligence_actors=[value for value in (workflow_actor_label, downstream_actor) if value],
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    boundary = _backlog_row(
        label=label,
        title=boundary_title,
        problem=f"{state_label} becomes untrustworthy when a visible change cannot explain who made it, what status it reached, or why it is blocked.",
        customer=boundary_audience,
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
        dependencies=[
            f"{primary_component} supplies the first-path entry action; accepted external sources stay explicit when the first path names them."
        ],
        interfaces=[
            f"Keep state, review, and external-dependency interfaces separate; state owned by {second_component} stays behind its own boundary."
        ],
        validation=[f"Reject any transition that cannot explain {state_label}, actor, status, owner, and result."],
        state_object=state_label,
        evidence_record=evidence_label,
        first_path=first_path_summary,
        proof_boundary=proof_summary,
        human_actors=first_release_human_actors,
        intelligence_actors=[value for value in (workflow_actor_label, downstream_actor) if value],
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
        customer=proof_audience,
        opportunity=(
            "Turn the completed path into a reviewable release claim that connects validation results, state references, "
            "the release decision, and deferred scope."
        ),
        product_view=(
            f"{proof_component} explains why the outcome can be trusted. "
            f"It connects {state_label}, validation output, and {_proof_focus_summary(proof_focus)} to the promised result: {outcome_summary}."
        ),
        first_slice=(
            f"Produce one {proof_record_label} that links the first path, {_sentence_label(state_label)}, and validation result to release scope."
        ),
        metrics=[
            f"{proof_record_label} links accepted input, {_sentence_label(state_label)}, and validation output to the outcome.",
            "Missing evidence blocks proof review instead of producing a release-ready claim.",
            "The proof view checks the promised result without expanding deferred scope.",
            f"Deferred scope remains visible: {proof_non_goal_text}.",
        ],
        component_focus=[component_ids[-1]] if component_ids else [],
        diagram_focus=[diagram_slugs["ownership"], diagram_slugs["proof_review"], diagram_slugs["sequence"]],
        dependencies=[
            f"Depends on state replay from {second_component}, path proof from {primary_component}, and release-review access posture."
        ],
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
        human_actors=first_release_human_actors,
        intelligence_actors=[proof_audience],
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    return [parent, workflow, boundary, proof]


def _first_release_problem_summary(value: str, human_actors: list[str]) -> str:
    if not value:
        return ""
    deferred_labels = [
        backlog_text.actor_label(actor)
        for actor in human_actors
        if backlog_text.is_deferred_actor(actor) and backlog_text.actor_label(actor)
    ]
    if _mentions_actor_label(value, deferred_labels):
        return ""
    return value


def _mentions_actor_label(value: str, labels: list[str]) -> bool:
    text = str(value or "").casefold()
    for label in labels:
        normalized = str(label or "").strip(" .").casefold()
        if normalized and normalized in text:
            return True
    return False


def _dedupe_capability_phrase(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" .")
    if not text:
        return ""
    clauses = [part.strip(" ,") for part in re.split(r",\s+|\s+and\s+", text) if part.strip(" ,")]
    if len(clauses) <= 1:
        return text
    seen: set[str] = set()
    unique: list[str] = []
    for clause in clauses:
        key = _capability_clause_key(clause)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        unique.append(clause)
    if len(unique) == len(clauses):
        return text
    if len(unique) == 1:
        return unique[0]
    if len(unique) == 2:
        return f"{unique[0]} and {unique[1]}"
    return f"{', '.join(unique[:-1])}, and {unique[-1]}"


def _metric_capability_summary(value: str) -> str:
    text = _strip_leading_connector(_clean_text(value).strip(" ."))
    if text.casefold().startswith("the "):
        tail = text[4:].strip(" .")
        first_tail_word = tail.split(maxsplit=1)[0] if tail else ""
        if first_tail_word[:1].islower():
            text = tail
    if not text:
        return "the promised first-path result"
    parts = []
    for part in _text_values(text, split_scalar=True, split_commas=True):
        part = part.strip(" .")
        part = _strip_leading_connector(part)
        if part:
            parts.append(part)
    if len(parts) >= 2 and any(looks_like_action_clause(part) for part in parts):
        return "the completed first-path actions"
    if len(parts) >= 3:
        return f"{parts[0]} through the promised result"
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return parts[0] if parts else text


def _evidence_scope_phrase(value: str, *, actor: str) -> str:
    text = _strip_leading_connector(_clean_text(value).strip(" ."))
    if not text:
        return "the promised first-path result"
    lowered = text.casefold()
    if lowered.startswith(("a ", "an ", "one ", "the ", "this ", "that ")):
        return text
    actor_subject = backlog_text.problem_actor_subject(actor, fallback="the user").casefold()
    if lowered.startswith("can "):
        return f"the path where {actor_subject} {text}"
    if looks_like_action_clause(text):
        return f"the path where {actor_subject} can {text}"
    return f"the first-path evidence for {text}"


def _proof_focus_summary(value: str) -> str:
    text = _strip_leading_connector(_clean_text(value).strip(" ."))
    if not text:
        return "review evidence"
    parts: list[str] = []
    for part in _text_values(text, split_scalar=True, split_commas=True):
        parts.extend(
            normalized
            for candidate in part.split(" and ")
            if (normalized := _strip_leading_connector(candidate.strip(" .")))
        )
    if len(parts) >= 3:
        return f"{parts[0]}, {parts[1]}, and {parts[2]}"
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return parts[0] if parts else text


def _strip_leading_connector(value: str) -> str:
    text = _clean_text(value).strip(" .")
    lowered = text.casefold()
    for connector in ("and", "or", "then", "but"):
        prefix = f"{connector} "
        if lowered.startswith(prefix):
            return text[len(prefix) :].strip(" .")
    return text


def _capability_clause_key(value: str) -> str:
    tokens: list[str] = []
    for raw in re.sub(r"[-/]", " ", str(value or "")).split():
        token = raw.strip(".,:;()[]{}").casefold()
        if len(token) < 4:
            continue
        if token in {"prove", "proves", "proved", "proven", "proof"}:
            token = "proof"
        tokens.append(token)
    return " ".join(tokens)


def _outcome_repeats_action(*, action: str, outcome: str, outcome_action: str) -> bool:
    return bool(
        (outcome and backlog_text.result_terms_covered(outcome, action))
        or (outcome_action and backlog_text.result_terms_covered(outcome_action, action))
        or (outcome and backlog_text.shares_product_terms(action, outcome))
        or (outcome_action and backlog_text.shares_product_terms(action, outcome_action))
    )


__all__ = [
    "confirmed_backlog_rows",
    "confirmed_evidence_record_label",
    "confirmed_program",
    "confirmed_release_plan",
    "confirmed_workstream_titles",
]
