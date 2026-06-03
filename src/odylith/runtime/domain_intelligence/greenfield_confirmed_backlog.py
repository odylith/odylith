"""Build Radar, program, and release records for confirmed greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import system_component_name
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items as _join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import problem_text as _problem_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label as _title_label
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import _has_mechanical_need_to_turn
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
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
        _workstream_subject(str(row.get("label", "")).strip())
        for row in components
        if str(row.get("label", "")).strip()
    ]
    actor = _lead_actor_label(human_actors)
    action = _imperative_action_phrase(first_path)
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    proof_label = labels[-1] if len(labels) > 2 else (labels[0] if labels else label)
    outcome = _first_path_outcome(first_path, proof_boundary=proof_boundary)
    if outcome and not _generic_title_outcome(outcome):
        workflow_actor = actor or _actor_from_action(action) or "user"
        workflow = f"Let {workflow_actor} reach {outcome}"
    elif action:
        action_actor, action_tail = _actor_action_parts(action)
        workflow_actor = action_actor or actor or "user"
        workflow_action = _base_leading_action(action_tail or _strip_actor_prefix(action, workflow_actor) or action)
        workflow = f"Let {workflow_actor} {workflow_action}"
    elif labels:
        workflow = f"Make {labels[0]} usable in the first path"
    else:
        workflow = f"Make {label} usable in the first path"
    state_changer = _state_changer_label(labels, state_label=state_label)
    if state_changer:
        boundary = f"Keep {state_label} clear after {state_changer} changes it"
    else:
        boundary = f"Keep {state_label} clear and reviewable"
    proof_subject = state_label or _proof_title_object(proof_boundary) or proof_label
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
    proof_summary = proof_claim_summary(proof_boundary, limit=340)
    clauses = first_path_clauses(
        first_path_summary,
        proof_boundary=proof_summary,
        action_fallback=_first_action_clause(first_path_summary) or "complete the accepted product path",
        capability_fallback=_first_action_clause(first_path_summary) or "complete the accepted product path",
        capability_limit=340,
        outcome_limit=240,
    )
    actors = join_actor_labels(human_actors) or _short_summary(customer, limit=260) or f"{label} users and reviewers"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    primary_component = _workstream_subject(_component_label_at(components, 0, fallback=f"{label} first path"))
    second_component = _workstream_subject(_component_label_at(components, 1, fallback=primary_component))
    proof_component = _workstream_subject(
        _component_label_at(components, len(components) - 1, fallback=f"{label} proof review")
    )
    proof_record_label = _title_label(f"{proof_component} proof record") or evidence_label
    primary_user_action = _sentence_fragment(
        first_path_action_phrase(
            first_path_summary,
            fallback=clauses.action_chain or clauses.model.material_action or "complete the accepted product path",
            max_fragments=3,
            limit=180,
        )
    )
    first_path_entry_text = _sentence_fragment(clauses.model.material_action or primary_user_action or clauses.action_chain)
    first_path_capability = _capability_action_clause(
        primary_user_action or _sentence_fragment(clauses.capability_chain) or first_path_entry_text
    )
    first_path_full_capability = _capability_action_clause(_sentence_fragment(clauses.capability_chain) or first_path_capability)
    outcome_summary = _sentence_fragment(clauses.visible_result) or _first_path_outcome(first_path_summary, proof_boundary=proof_boundary)
    proof_focus = _proof_focus_phrase(proof_summary, fallback="release decision")
    dependency_outcome = outcome_summary or "the promised first-path result"
    first_path_action = _capability_action_clause(primary_user_action or first_path_entry_text or first_path_capability)
    path_entry_story = _sentence_fragment(first_path_entry_text or first_path_capability or first_path_summary)
    metric_actor = _problem_actor_subject(actors, fallback=f"{label} user")
    downstream_actor = _supporting_actor_label(human_actors)
    downstream_subject = _problem_actor_subject(downstream_actor, fallback="the next participant") if downstream_actor else "The next participant"
    parent_problem = _program_problem(
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
    if outcome_summary and not _shares_product_terms(first_slice_action, outcome_summary):
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
            f"{metric_actor} can {first_path_action} and reach {outcome_summary} without adjacent scope being pulled into the release.",
            f"{state_label} remains understandable when input is accepted, blocked, corrected, or reviewed.",
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
            f"reach {outcome_summary}, and see what to fix when required information is missing."
        ),
        metrics=[
            f"{metric_actor} can complete the first interaction and reach {outcome_summary}.",
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


def proof_claim_summary(value: str, *, limit: int = 260) -> str:
    text = _short_summary(value, limit=limit).strip(" .")
    text = re.sub(r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:release\s+[0-9.]+\s+)?(?:is\s+)?proven\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?proof\s+boundary\s+(?:is|means)\s*:?\s*", "", text, flags=re.IGNORECASE)
    return text or _short_summary(value, limit=limit).strip(" .")


def join_actor_labels(values: list[str] | None, *, limit: int = 5) -> str:
    labels: list[str] = []
    for value in values or []:
        label = _compact_text(str(value)).split("—", 1)[0].split(":", 1)[0].strip(" .")
        if label and label.casefold() not in {"other accepted items"}:
            labels.append(label)
    selected = list(dict.fromkeys(labels))[:limit]
    if not selected:
        return ""
    return ", ".join(selected)


def _actor_from_action(value: str) -> str:
    actor, _action = _actor_action_parts(value)
    return actor


def _generic_title_outcome(value: str) -> bool:
    text = _sentence_fragment(value).casefold()
    return bool(
        not text
        or text in {"next action", "next step", "what happens next", "a visible result", "a visible, useful result"}
        or re.fullmatch(r"(?:a|an|the)?\s*(?:result|outcome|summary|view|status)", text)
    )


def _state_changer_label(labels: Sequence[str], *, state_label: str) -> str:
    state_terms = _semantic_words(state_label)
    for label in labels[1:3]:
        cleaned = _sentence_fragment(label).strip(" .")
        if not cleaned:
            continue
        if re.search(r"\b(?:experience guide|product record|evidence log|release guardrail)\b", cleaned, re.IGNORECASE):
            continue
        if not re.search(
            r"\b(?:approval|assessment|check|comparison|decision|eligibility|evaluation|quality|review|risk|rule|scoring|validation)\b",
            cleaned,
            re.IGNORECASE,
        ):
            continue
        label_terms = _semantic_words(cleaned)
        if state_terms and label_terms and len(state_terms & label_terms) / max(1, min(len(state_terms), len(label_terms))) >= 0.75:
            continue
        if re.search(r"\b(?:queue|view|dashboard|summary|report|export|display)\b", cleaned, re.IGNORECASE):
            continue
        return cleaned
    return ""


def _semantic_words(value: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9][a-z0-9-]+", _compact_text(value).casefold()) if len(word) > 2}


def _lead_actor_label(values: list[str]) -> str:
    for value in values:
        text = _compact_text(str(value)).split("—", 1)[0].split(":", 1)[0].strip(" .")
        text = re.split(r"\b(?:who|that|with|for|and)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
        if not text:
            continue
        words = text.split()
        if len(words) > 4:
            text = " ".join(words[:4])
        return _sentence_fragment(text)
    return "someone"


def _supporting_actor_label(values: list[str]) -> str:
    for value in values[1:]:
        text = _compact_text(str(value)).split("—", 1)[0].split(":", 1)[0].strip(" .")
        text = re.split(r"\b(?:who|that|with|for|and)\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
        if not text:
            continue
        words = text.split()
        if len(words) > 4:
            text = " ".join(words[:4])
        return _sentence_fragment(text)
    return ""


def _imperative_action_phrase(first_path: str) -> str:
    text = _sentence_fragment(
        first_path_action_phrase(
            first_path,
            fallback=_first_action_clause(first_path) or "complete the accepted path",
            max_fragments=1,
            limit=120,
        )
    ).strip(" .")
    if not text:
        return ""
    actor, action_without_actor = _actor_action_parts(text)
    if actor and action_without_actor:
        return f"{actor} {action_without_actor}"
    return _capability_action_clause(text)


def _base_title_verb(value: str) -> str:
    token = str(value or "").casefold()
    overrides = {
        "chooses": "choose",
        "does": "do",
        "goes": "go",
        "has": "have",
        "is": "be",
        "receives": "receive",
        "sees": "see",
        "uses": "use",
    }
    if token in overrides:
        return overrides[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _actor_action_parts(value: str) -> tuple[str, str]:
    text = re.sub(r"^(?:a|an|the)\s+", "", _sentence_fragment(value), flags=re.IGNORECASE)
    words = text.split()
    for index in range(1, min(len(words), 6)):
        candidate = " ".join(words[index:]).strip(" .")
        if not looks_like_finite_action(candidate):
            continue
        verb = words[index].strip(".,;:")
        base = _base_title_verb(verb)
        if base != verb.casefold():
            actor = " ".join(words[:index]).strip(" .")
            tail = " ".join(words[index + 1 :]).strip(" .")
            action = " ".join(part for part in (base, tail) if part)
            return actor, action
    return "", ""


def _strip_actor_prefix(value: str, actor: str) -> str:
    text = _sentence_fragment(value)
    prefix = _sentence_fragment(actor)
    if prefix and text.casefold().startswith(prefix.casefold()):
        text = text[len(prefix) :].strip(" .")
    return text


def _base_leading_action(value: str) -> str:
    text = _sentence_fragment(value)
    words = text.split()
    if not words:
        return text
    base = _base_title_verb(words[0].strip(".,;:"))
    if base != words[0].casefold():
        words[0] = base
    return " ".join(words)


def _proof_title_object(value: str) -> str:
    text = _short_summary(value, limit=120).strip(" .")
    text = re.sub(r"^release\s+\S+\s+succeeds\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^proof\s+(?:boundary|must\s+show|means)\s*:?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwithout\b.+$", "", text, flags=re.IGNORECASE).strip(" .,;:")
    if len(text.split()) > 9:
        text = " ".join(text.split()[:9])
    return _sentence_fragment(text)


def _workstream_subject(value: str) -> str:
    text = _compact_text(value)
    text = re.sub(r"\s+(Service|Surface|Component|Boundary)$", "", text, flags=re.IGNORECASE).strip()
    return text or value


def _component_label_at(components: list[dict[str, Any]], index: int, *, fallback: str) -> str:
    if not components:
        return fallback
    bounded_index = min(max(index, 0), len(components) - 1)
    value = str(components[bounded_index].get("label", "")).strip()
    return value or fallback


def _first_clause(value: str) -> str:
    text = _short_summary(value, limit=220)
    parts = [part.strip(" .") for part in re.split(r"[.;]", text, maxsplit=1) if part.strip(" .")]
    return parts[0] if parts else text


def _first_action_clause(value: str) -> str:
    text = _first_clause(value)
    if not text:
        return text
    action_pattern = (
        r"the\s+product\s+(?:accepts?|assigns?|calculates?|completes?|estimates?|fetches?|highlights?|lets?|notifies?|preserves?|ranks?|records?|routes?|shows?|stores?|verifies?)|"
        r"(?:accepts?|assigns?|calculates?|chooses?|completes?|estimates?|fetches?|highlights?|lets?|logs?|notifies?|preserves?|ranks?|receives?|records?|reviews?|selects?|shows?|stores?|submits?|verifies?)\b"
    )
    return re.split(rf",\s+(?=(?:and\s+)?(?:{action_pattern}))", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")


def _first_path_outcome(value: str, *, proof_boundary: str = "") -> str:
    return _sentence_fragment(
        first_path_outcome_phrase(
            value,
            proof_boundary=proof_claim_summary(proof_boundary, limit=240),
            fallback="the promised user-visible result",
            limit=240,
        )
    )


def _program_problem(
    *,
    label: str,
    actors: str,
    story: str,
    capability: str,
    outcome: str,
    fallback: str,
) -> str:
    for candidate in (fallback, story):
        text = _short_summary(candidate, limit=360)
        if text and not _looks_mechanical_summary(text) and _has_problem_tension(text):
            return text
    actor_text = _problem_actor_subject(actors, fallback=f"{label} user")
    capability_text = capability or "complete the first product path"
    outcome_text = outcome or "the promised user-visible result"
    return (
        f"{actor_text} needs a clear way to {capability_text} and understand what to do next. "
        f"If {label} only captures activity, the product leaves that user with data but no trustworthy way to use {outcome_text}."
    )


def _problem_actor_subject(actors: str, *, fallback: str) -> str:
    text = _compact_text(actors)
    if not text:
        text = _compact_text(fallback)
    text = re.split(r"\s*,\s*|\s*;\s*|\s+\band\b\s+", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
    text = re.sub(r"\s*\((?:primary|secondary|optional|supporting|deferred)\)\s*$", "", text, flags=re.IGNORECASE).strip(" .")
    if not text:
        text = "first user"
    lowered = text.casefold()
    if re.match(r"^(?:a|an|the|one|this|that|each|people|users|customers|operators|reviewers)\b", lowered):
        return text[:1].upper() + text[1:]
    return f"The {lowered}"


def _capability_action_clause(value: str) -> str:
    text = _sentence_fragment(value)
    if not text:
        return "complete the accepted path"
    _actor, actor_action = _actor_action_parts(text)
    if actor_action:
        return _normalize_action_clause(actor_action)
    converted = base_action_clause(text)
    return _normalize_action_clause(converted or text)


def _normalize_action_clause(value: str) -> str:
    text = base_action_clause(_sentence_fragment(value))
    text = re.sub(
        r"^(?:a|an|the)\s+(?:user|owner|person|actor|customer|applicant|participant|operator)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    for inflected, base in {
        "adds": "add",
        "asks": "ask",
        "logs": "log",
        "enters": "enter",
        "selects": "select",
        "submits": "submit",
        "saves": "save",
        "chooses": "choose",
        "clicks": "click",
        "accepts": "accept",
        "dismisses": "dismiss",
        "records": "record",
        "captures": "capture",
        "reviews": "review",
    }.items():
        text = re.sub(rf"\b(and|then)\s+{re.escape(inflected)}\b", rf"\1 {base}", text, flags=re.IGNORECASE)
        text = re.sub(rf"\b(and|then)\s+manually\s+{re.escape(inflected)}\b", rf"\1 manually {base}", text, flags=re.IGNORECASE)
    text = re.sub(
        r",\s+and\s+(manually\s+)?(log|enter|select|submit|save|choose|click|accept|dismiss|record|capture|review)\b",
        r" and \1\2",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip(" .") or "complete the accepted path"


def _sentence_fragment(value: str) -> str:
    text = _short_summary(value, limit=260).strip(" .")
    if not text:
        return ""
    if re.match(r"^[A-Z]{2,}\b", text):
        return text
    return text[:1].casefold() + text[1:]


def _proof_focus_phrase(value: str, *, fallback: str) -> str:
    candidates: list[tuple[int, int, str]] = []
    for index, clause in enumerate(re.split(r"\s*,\s*|\s+\band\b\s+", _sentence_fragment(value))):
        text = _sentence_fragment(clause).strip(" .")
        if not text or len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text)) > 6:
            continue
        if not re.search(r"\b(?:approval|decision|judgment|outcome|reason|rejection|signoff|status)\b", text, re.I):
            continue
        score = 3
        if re.search(
            r"\b(?:actor|admin|administrator|coordinator|customer|human|manager|operator|owner|reviewer|user)\b",
            text,
            re.I,
        ):
            score += 4
        if re.search(r"\b(?:final|release|review|trusted)\b", text, re.I):
            score += 1
        candidates.append((score, -index, text))
    if not candidates:
        return fallback
    candidates.sort(reverse=True)
    return candidates[0][2]


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
        "rationale_lines": _rationale_lines(
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


def _rationale_lines(*, label: str, title: str, opportunity: str, first_slice: str, proof_boundary: str) -> list[str]:
    why_now = _short_summary(opportunity, limit=180).strip(" .")
    expected_outcome = _short_summary(first_slice, limit=200).strip(" .")
    if _looks_mechanical_summary(why_now):
        why_now = f"{title} proves a bounded part of the accepted {label} first path before adjacent scope expands"
    if _looks_mechanical_summary(expected_outcome):
        expected_outcome = f"{title} produces reviewable state, blocker behavior, recovery evidence, and handoff proof"
    if not why_now:
        why_now = "Clarify the accepted product boundary before implementation starts"
    if not expected_outcome:
        expected_outcome = "Produce the first reviewable release outcome"
    return [
        f"- why now: {why_now}.",
        f"- expected outcome: {expected_outcome}.",
        "- tradeoff: This stays narrow so the team can prove the promised user outcome before it widens the product promise.",
        "- deferred for now: Anything not needed for this reviewed behavior waits until the first outcome is proven.",
        f"- ranking basis: This work comes before optional scope because {label} needs the user outcome, product state, and release claim to agree.",
    ]


def _looks_mechanical_summary(value: str) -> bool:
    text = _compact_text(value)
    if not text:
        return False
    lowered = text.casefold()
    repeated_required = len(re.findall(r"\brequired\b", lowered))
    return bool(
        repeated_required >= 2
        or re.search(r"\bactor identity,\s+validation context,\s+and upstream handoff\b", lowered)
        or re.search(r"\bblocker signal,\s+review rationale,\s+and downstream handoff\b", lowered)
        or re.search(r"\b(?:accepted\s+first\s+path|accepted\s+proof\s+boundary|first\s+path\s+entry)\b", lowered)
        or re.search(r"\b(?:visible[- ]result\s+event|rendered\s+dashboard|dashboard\s+renders?\s+the\s+visible\s+result)\b", lowered)
        or re.search(r"\b(?:source\s+evidence,\s+visible\s+blockers|systems\s+that\s+own\s+the\s+handoff)\b", lowered)
        or re.search(r"\bis\s+not\s+trustworthy\s+when\b", lowered)
        or _has_mechanical_need_to_turn(text)
        or re.search(r"\bfirst\s+release\s+can\s+collect\s+activity\b", lowered)
        or re.search(r"^on\s+save\b", lowered)
    )


def _has_problem_tension(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:without|risk|harm|danger|fails?|failure|cannot|missing|unclear|blocked|drift|stale|unsupported|untrusted|needs?|must|if|when|unless|because|otherwise|prevents?|reduces?|no)\b",
            _compact_text(value).casefold(),
        )
    )


def _shares_product_terms(left: str, right: str) -> bool:
    stop = {
        "accepted",
        "action",
        "complete",
        "first",
        "path",
        "product",
        "release",
        "result",
        "state",
        "that",
        "their",
        "user",
        "when",
        "with",
    }
    left_terms = {token for token in re.findall(r"[a-z0-9][a-z0-9-]*", _compact_text(left).casefold()) if len(token) > 3 and token not in stop}
    right_terms = {token for token in re.findall(r"[a-z0-9][a-z0-9-]*", _compact_text(right).casefold()) if len(token) > 3 and token not in stop}
    if not left_terms or not right_terms:
        return False
    return len(left_terms & right_terms) >= min(3, len(right_terms))


__all__ = [
    "confirmed_backlog_rows",
    "confirmed_evidence_record_label",
    "confirmed_program",
    "confirmed_release_plan",
    "confirmed_workstream_titles",
    "join_actor_labels",
    "proof_claim_summary",
]
