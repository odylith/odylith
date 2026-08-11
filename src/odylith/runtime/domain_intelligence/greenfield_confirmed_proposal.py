"""Governed greenfield proposal construction after intent confirmation."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_actor_row_projection import canonical_first_path_actor_reference
from odylith.runtime.domain_intelligence.greenfield_actor_row_projection import canonical_human_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_backlog_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_evidence_record_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_release_plan
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_workstream_titles
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import join_actor_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import proof_claim_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import (
    confirmed_components,
    domain_label,
)
from odylith.runtime.domain_intelligence.greenfield_command_text import shell_quote
from odylith.runtime.domain_intelligence.greenfield_confirmed_project_brief import confirmed_project_brief
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels as _join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import object_reference_phrase as _object_reference_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import problem_text as _problem_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_label as _sentence_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary as _state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label as _title_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import (
    confirmed_intent_list,
    confirmed_intent_summary,
)
from odylith.runtime.domain_intelligence.greenfield_evaluation_semantics import evidence_anchor_phrases
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import health_safety_obligations
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import select_visible_result_candidate
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import canonical_product_actor_rows


def build_confirmed_greenfield_proposal(
    *,
    prompt: str,
    title: str,
    observed_source: Mapping[str, Any],
    release_selector: str = "",
    confirmed_intent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the governed proposal object built from accepted product intent."""

    if not isinstance(confirmed_intent, Mapping):
        raise ValueError("confirmed greenfield proposal requires accepted Product Intent Confirmation data.")
    release = str(release_selector or "").strip() or greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR
    intent_title = confirmed_intent_summary(confirmed_intent, "title", "")
    source_title = confirmed_intent_summary(confirmed_intent, "source_title", "")
    title_normalization = normalize_project_title(source_title or intent_title or str(title or "").strip(), fallback="Greenfield Project")
    product_title = title_normalization.canonical_title
    product_slug = slugify(product_title)
    command_prompt = product_title
    label = domain_label(product_title, "")
    label_lower = _sentence_label(label)
    label_slug = slugify(label)
    product_story = confirmed_intent_summary(
        confirmed_intent,
        "product_story",
        f"{label} gives a named user one accountable product path with owned state and reviewable proof.",
    )
    state_object = confirmed_intent_summary(confirmed_intent, "state_object", f"{label} record")
    first_path = confirmed_intent_summary(
        confirmed_intent,
        "first_path",
        f"One user completes the first {label_lower} path from intake through state update and evidence review.",
    )
    proof_boundary = confirmed_intent_summary(
        confirmed_intent,
        "proof_boundary",
        f"Release {release} is trustworthy only when the first path, {label_lower} record, and review evidence can be inspected together.",
    )
    human_actors = canonical_human_actor_rows(
        project_label=label,
        rows=canonical_product_actor_rows(confirmed_intent_list(confirmed_intent, "human_actors")),
    )
    first_path = canonical_first_path_actor_reference(
        project_label=label,
        first_path=first_path,
        actor_rows=human_actors,
        fallback=f"{label_lower} user",
    )
    external_systems = confirmed_intent_list(confirmed_intent, "external_systems")
    internal_systems = confirmed_intent_list(confirmed_intent, "internal_systems")
    assumptions = confirmed_intent_list(confirmed_intent, "assumptions")
    ambiguities = confirmed_intent_list(confirmed_intent, "ambiguities")
    non_goals = confirmed_intent_list(confirmed_intent, "non_goals")
    scope_constraints = list(non_goals)
    problem_summary = confirmed_intent_summary(confirmed_intent, "problem", "")
    customer_summary = confirmed_intent_summary(confirmed_intent, "customer", "")
    opportunity_summary = confirmed_intent_summary(confirmed_intent, "opportunity", "")
    product_view_summary = confirmed_intent_summary(confirmed_intent, "product_view", "")
    success_metrics = confirmed_intent_list(confirmed_intent, "success_metrics")
    evidence_requirements = list(
        evidence_anchor_phrases(
            "",
            source_anchors=confirmed_intent_list(confirmed_intent, "evidence_requirements"),
        )
    )
    operational_constraints = confirmed_intent_list(confirmed_intent, "operational_constraints")
    if not (product_story and state_object and first_path and proof_boundary and human_actors and len(internal_systems) >= 2):
        raise ValueError(
            "confirmed greenfield proposal requires product story, state object, first path, proof boundary, "
            "human actors, and at least two internal product systems from the accepted Product Intent Confirmation."
    )
    evidence_record = confirmed_evidence_record_label(label=label, proof_boundary=proof_boundary, internal_systems=internal_systems)
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    components = confirmed_components(
        label=label,
        label_slug=label_slug,
        internal_systems=internal_systems,
        first_path=first_path,
        state_object=state_object,
        proof_boundary=proof_boundary,
        external_systems=external_systems,
        non_goals=scope_constraints,
    )
    release_components = [dict(row) for row in active_release_components(components)]
    workflow_title, boundary_title, proof_title = confirmed_workstream_titles(
        label=label,
        components=release_components,
        internal_systems=internal_systems,
        first_path=first_path,
        state_object=state_object,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
    )
    parent_title = _parent_workstream_title(label=label, first_path=first_path)
    diagram_slugs = {
        "context": f"{label_slug}-system-context",
        "sequence": f"{label_slug}-first-path",
        "state_evidence": f"{label_slug}-state-evidence",
        "component_boundaries": f"{label_slug}-component-boundaries",
        "ownership": f"{label_slug}-ownership-proof",
        "proof_review": f"{label_slug}-release-proof-review",
    }
    visible_candidate = select_visible_result_candidate(
        first_path,
        proof_boundary=proof_boundary,
        product_view=product_view_summary,
        state_object=state_object,
    )
    semantic_visible_result = (
        visible_candidate.text
        if visible_candidate.source_path != "proof_boundary" and len(visible_candidate.text.split()) >= 2
        else ""
    )
    backlog_rows = confirmed_backlog_rows(
        label=label,
        parent_title=parent_title,
        workflow_title=workflow_title,
        boundary_title=boundary_title,
        proof_title=proof_title,
        state_object=state_object,
        evidence_record=evidence_record,
        product_story=product_story,
        first_path=first_path,
        proof_boundary=proof_boundary,
        problem=problem_summary,
        customer=customer_summary,
        opportunity=opportunity_summary,
        product_view=product_view_summary,
        success_metrics=success_metrics,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
        components=release_components,
        diagram_slugs=diagram_slugs,
        evidence_requirements=evidence_requirements,
        open_questions=ambiguities,
        visible_result=semantic_visible_result,
    )
    semantic_model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title=product_title,
            state_object=state_object,
            first_path=first_path,
            visible_result=semantic_visible_result,
            proof_boundary=proof_boundary,
            components=components,
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
            workstreams=backlog_rows,
            operational_constraints=operational_constraints,
            source_requirements=evidence_requirements,
        )
    )
    first_path_capability = first_path_capability_phrase(first_path, fallback=first_path, limit=260, gerund=True)
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "prompt": "",
            "title": product_title,
            "project_slug": product_slug,
            "reasoning_mode": "odylith_confirmed_governed_proposal",
            "evidence_tier": "user_intent",
            "summary": (
                f"{product_story} Release {release} stays bounded to: {first_path}"
            ),
            "product_story": product_story,
            "state_object": state_object,
            "first_path": first_path,
            "proof_boundary": proof_boundary,
            "human_actors": human_actors,
            "external_systems": external_systems,
            "internal_systems": internal_systems,
            "assumptions": assumptions,
            "ambiguities": ambiguities,
            "non_goals": non_goals,
            "problem": problem_summary,
            "customer": customer_summary,
            "opportunity": opportunity_summary,
            "product_view": product_view_summary,
            "success_metrics": success_metrics,
            "evidence_requirements": evidence_requirements,
            "operational_constraints": operational_constraints,
        },
        "observed_source": dict(observed_source),
        "classification": {
            "method": "confirmed_open_world_product_shape",
            "fit_policy": "Use product-specific nouns from the confirmed intent, then keep the first path narrow.",
            "provider_calls": 0,
        },
        "greenfield_ux": {
            "mode": "consumer_greenfield_confirmed_path",
            "write_guardrail": "No product records are written until confirmed create receives --confirm.",
            "next_best_action": f"Create accepted {label_lower} project records for release {release}.",
        },
        "assumptions": _assumption_rows(
            label=label,
            label_lower=label_lower,
            assumptions=assumptions,
        ),
        "open_questions": [
            {
                "id": f"OQ-{index:03d}",
                "question": ambiguity,
                "impact": "Changes the visible flow, permission model, and validation target.",
                "default_if_unanswered": "Resolve this before it changes the accepted first path.",
            }
            for index, ambiguity in enumerate(ambiguities[:2], start=1)
        ],
        "risks": build_product_risks(
            title=product_title,
            product_story=product_story,
            problem=problem_summary,
            first_path=first_path,
            state_object=state_object,
            proof_boundary=proof_boundary,
            human_actors=human_actors,
            external_systems=external_systems,
            internal_systems=internal_systems,
            non_goals=non_goals,
            release=release,
        ),
        "security_compliance": _security_compliance(
            label=label,
            label_lower=label_lower,
            first_path=first_path,
            state_object=state_object,
            proof_boundary=proof_boundary,
            safety_obligations=health_safety_obligations(
                product_title,
                product_story,
                state_object,
                first_path,
                proof_boundary,
                " ".join(internal_systems),
                " ".join(non_goals),
            ),
        ),
        "validation_strategy": [
            f"Success proof includes {first_path_capability}.",
            f"Replay proof reconstructs {state_label} with actor, timestamp, status, result, and review context.",
            f"The release proof must show this user-visible result: {proof_claim_summary(proof_boundary, limit=300)}.",
            *health_safety_obligations(
                product_title,
                product_story,
                state_object,
                first_path,
                proof_boundary,
                " ".join(internal_systems),
                " ".join(non_goals),
            ),
        ],
        "project_brief": confirmed_project_brief(
            label=label,
            prompt=command_prompt,
            release=release,
            state_object=state_object,
            evidence_record=evidence_record,
            product_story=product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
            problem=problem_summary,
            human_actors=human_actors,
            internal_systems=internal_systems,
            component_labels=[str(row.get("label") or "").strip() for row in release_components],
            external_systems=external_systems,
            assumptions=assumptions,
            ambiguities=ambiguities,
            non_goals=non_goals,
            evidence_requirements=evidence_requirements,
            operational_constraints=operational_constraints,
            visible_result=semantic_visible_result,
        ),
        "project_intelligence": _project_intelligence(
            label=label,
            release=release,
            state_object=state_object,
            evidence_record=evidence_record,
            product_story=product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
            problem=problem_summary,
            customer=customer_summary,
            opportunity=opportunity_summary,
            product_view=product_view_summary,
            success_metrics=success_metrics,
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
            visible_result=semantic_visible_result,
        ),
        "release_plan": confirmed_release_plan(
            label=label,
            label_slug=label_slug,
            release=release,
            workflow_title=workflow_title,
            boundary_title=boundary_title,
            proof_title=proof_title,
        ),
        "backlog": backlog_rows,
        "components": components,
        "semantic_model": semantic_model,
        "diagrams": confirmed_diagrams(
            label=label,
            components=components,
            diagram_slugs=diagram_slugs,
            workstream_titles={
                "parent": parent_title,
                "workflow": workflow_title,
                "boundary": boundary_title,
                "proof": proof_title,
            },
            product_story=product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
            state_object=state_object,
            evidence_record=evidence_record,
            human_actors=human_actors,
            external_systems=external_systems,
            internal_systems=internal_systems,
            non_goals=non_goals,
            semantic_model=semantic_model,
        ),
        "apply_commands": [
            "odylith greenfield propose --repo-root . --prompt " + shell_quote(command_prompt),
            "# Odylith compiles and validates the package before showing CONFIRM, EDIT, and REJECT.",
            "# CONFIRM commits the exact hash-bound transaction; EDIT rebuilds it from new evidence.",
        ],
    }
    if title_normalization.changed:
        proposal["intent"]["source_title"] = title_normalization.raw_title
    return proposal


def _assumption_rows(*, label: str, label_lower: str, assumptions: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    source_rows = assumptions or [
        f"{label} starts with the user, first path, and proof boundary accepted in the product direction."
    ]
    for index, statement in enumerate(source_rows, start=1):
        text = _compact_text(statement).strip(" .")
        if not text:
            continue
        rows.append(
            {
                "id": f"ASM-{index:03d}",
                "tier": "user_intent",
                "statement": f"{text}.",
                "confirm_when": "The product owner confirms the first operating context, user group, and release posture.",
            }
        )
    external_statement = (
        f"External data, devices, services, or providers for {label_lower} stay simulated or "
        "sandboxed until source-backed contracts and credentials are intentionally introduced."
    )
    if not _assumption_statement_already_covered(external_statement, rows):
        rows.append(
            {
                "id": f"ASM-{len(rows) + 1:03d}",
                "tier": "odylith_assumption",
                "statement": external_statement,
                "confirm_when": "The implementation owner names a live integration and its proof boundary.",
            }
        )
    return rows


def _assumption_statement_already_covered(statement: str, rows: list[dict[str, str]]) -> bool:
    terms = set(re.findall(r"[a-z0-9]{4,}", _compact_text(statement).casefold()))
    if not terms:
        return False
    for row in rows:
        row_terms = set(re.findall(r"[a-z0-9]{4,}", _compact_text(row.get("statement", "")).casefold()))
        if len(terms & row_terms) / max(1, len(terms)) >= 0.45:
            return True
    return False


def _security_compliance(
    *,
    label: str,
    label_lower: str,
    first_path: str,
    state_object: str,
    proof_boundary: str,
    safety_obligations: tuple[str, ...],
) -> dict[str, str]:
    obligations = " ".join(safety_obligations)
    safety_tail = f" {obligations}" if obligations else ""
    state_reference = _object_reference_phrase(_domain_object_label(state_object, fallback=_short_summary(state_object, limit=120)))
    return {
        "domain": (
            f"{label} carries domain risk around {state_reference}, evidence boundary, actors, "
            f"and decisions based on stale or incomplete data. First path: {_short_summary(first_path, limit=220)}."
            f"{safety_tail}"
        ),
        "security": (
            f"Security posture for {label_lower} covers authentication, authorization, ownership checks, "
            f"credential isolation, abuse prevention, and private data handling for {state_reference}."
        ),
        "policy": (
            f"Compliance posture for {label_lower} names any privacy, retention, accessibility, safety, or operational-review duties "
            f"that apply to {state_reference} before production claims are made."
            f"{safety_tail}"
        ),
    }


def _project_intelligence(
    *,
    label: str,
    release: str,
    state_object: str,
    evidence_record: str,
    product_story: str = "",
    first_path: str = "",
    proof_boundary: str = "",
    problem: str = "",
    customer: str = "",
    opportunity: str = "",
    product_view: str = "",
    success_metrics: list[str] | None = None,
    human_actors: list[str] | None = None,
    internal_systems: list[str] | None = None,
    external_systems: list[str] | None = None,
    non_goals: list[str] | None = None,
    visible_result: str = "",
) -> dict[str, Any]:
    label_lower = _sentence_label(label)
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    evidence_label = _domain_object_label(evidence_record, fallback=evidence_record)
    state_lower = _sentence_label(state_label)
    evidence_lower = _sentence_label(evidence_label)
    story_summary = _short_summary(product_story, limit=360)
    problem_summary = _problem_text(label=label, problem=problem, product_story=product_story, first_path=first_path)
    opportunity_summary = _short_summary(opportunity, limit=320) or "The accepted first path becomes the planning boundary for source work and proof."
    product_view_summary = _short_summary(product_view, limit=320) or "The first release stays narrow until source-backed behavior and review evidence exist."
    first_path_summary = _short_summary(first_path, limit=360)
    first_path_scope = _short_summary(first_path, limit=620) or first_path_summary
    proof_summary = proof_claim_summary(proof_boundary, limit=320)
    visible_result_text = _short_summary(visible_result, limit=260) or first_path_outcome_phrase(
        first_path,
        proof_boundary=proof_boundary,
        fallback=f"{state_lower} result",
    )
    visible_result_ref = _object_reference_phrase(visible_result_text) or f"the {state_lower} result"
    state_summary = _state_detail_summary(state_object, state_label=state_label, limit=260)
    actors = join_actor_labels(human_actors) or _short_summary(customer, limit=220) or f"the first {label_lower} operator and reviewer"
    actor_boundary = _actor_boundary_summary(human_actors, fallback=actors)
    internals = _join_system_labels(internal_systems) or f"{state_lower} owner and {evidence_lower} owner"
    externals = boundary_clause_text(external_systems) or "explicitly deferred external systems"
    non_goal_text = boundary_clause_text(non_goals) or "broad platform automation and live irreversible integrations"
    rows = {
        "intent": [
            story_summary or f"{label} gives a named operator one accountable path instead of an unbounded product outcome.",
            problem_summary,
            f"Release {release} proves the accepted first path before wider automation, integrations, or scaling claims are allowed: {first_path_summary}",
            "The product outcome is useful only when each accepted role can see its relevant result, explanation, and evidence.",
        ],
        "scope": [
            f"In scope: {first_path_scope}",
            f"In scope systems: {internals}. External systems: {externals}.",
            f"Out of scope after the accepted first path: {non_goal_text}.",
        ],
        "ontology": [
            f"{label} actor: one of the people or teams named in the confirmed intent. Boundary: {actor_boundary}.",
            f"{state_label}: the domain object that changes through the accepted first journey. {state_summary}",
            f"{evidence_label}: the proof record that ties the first-path result, validation output, state replay, and release decision together.",
            f"{label} release gate: the decision point that blocks promotion when first-path, state, access, or evidence proof is missing.",
        ],
        "state": [
            f"{state_label} changes according to the confirmed first journey: {first_path_summary}",
            f"State changes stay versioned so {visible_result_ref} can be replayed instead of explained from memory.",
        ],
        "operators": [
            f"Actors involved in the first release stay limited to {actor_boundary}.",
            f"Route state-changing actions only through the systems named in the confirmed intent: {internals}.",
            f"Assemble {evidence_lower} from the first-path result, state replay, validation output, and release decision.",
        ],
        "constraints": [
            f"Do not treat {label_lower} proposal text as working behavior; readiness assertions require validation output.",
            f"Do not let evidence review mutate {state_lower}; proof can approve or block, but state changes stay owned by the state path.",
        ],
        "source_of_truth_map": [
            f"{state_label} owns current first-path state, version history, and replay inputs.",
            f"{evidence_label} owns release readiness evidence, release decision, and validation references.",
        ],
        "evidence": [
            f"Review evidence must show the promised product result: {visible_result_ref}",
            f"Review evidence must prove blocked, replay, and release-decision behavior against the proof boundary: {proof_summary}",
            *[_short_summary(metric, limit=260) for metric in (success_metrics or [])[:3]],
            f"Simulated or sandbox evidence is acceptable for release {release}; live integrations need an explicit later contract.",
        ],
        "decisions": [
            f"Start with the smallest {label_lower} path that a real user can complete and review.",
            f"Delay broader platform behavior until {state_lower} and {evidence_lower} survive validation.",
        ],
        "assumptions": [
            f"The first actor set must stay explicit before implementation starts. Boundary: {actor_boundary}.",
            f"External systems remain simulated, sandboxed, or deferred unless the first path cannot be proven without them.",
        ],
        "topology": [
            f"Internal product systems come from the accepted product direction: {internals}.",
            f"External systems stay separate from product-owned state and proof: {externals}.",
            f"Promotion is blocked when the promised result is incomplete, unexplained, or wider than the accepted first release.",
        ],
        "invariants": [
            f"Every {label_lower} state change names actor, command, timestamp, input reference, and expected validation.",
            f"Every readiness assertion maps to {state_lower}, {evidence_lower}, a validation result, and an explicit non-goal boundary.",
        ],
        "risks": [
            f"{label} can sprawl if the first path, state object, and release decision are not named before coding starts.",
            f"Trust erodes if release evidence cannot reproduce the state decision or explain why a promotion was blocked.",
        ],
        "validation_obligations": [
            f"Validate the {label_lower} success path from first input to release-review outcome.",
            f"Validate at least one {label_lower} validation-failure path and recovery message.",
            f"Validate state replay and evidence review so release {release} cannot pass on a persuasive narrative alone.",
        ],
        "artifacts": [
            f"{state_label} history captures first-path status, owner, timestamp, version, and replay reference.",
            f"{evidence_label} captures validation output, replay output, release decision, and release scope.",
        ],
        "owners": [
            f"The release owner keeps the accepted actor boundary explicit before promotion: {actor_boundary}.",
            f"The proof owner owns release-evidence completeness, release decision, and release-readiness language.",
        ],
        "execution_memory": [
            f"Future {label_lower} work starts from the accepted first path, state object, and proof obligations.",
            f"Any source-backed contradiction invalidates the affected proposal assumption rather than being hidden as implementation detail.",
        ],
        "metrics": [
            f"The first path has zero unowned state transitions in release {release}.",
            f"Every readiness assertion has a state reference, evidence reference, validation reference, and release-review outcome.",
        ],
        "change_model": [
            f"Changing the state object requires revisiting first-path commands, replay proof, evidence review, and release gates.",
            f"Adding a live dependency requires new access, credential, privacy, failure, and validation proof.",
        ],
        "invalidation_rules": [
            f"If first-path validation is missing, {label_lower} implementation readiness stays blocked.",
            f"If replay output or evidence review disagrees with the visible result, release {release} cannot promote.",
        ],
        "conflict_model": [
            f"Product-owner correction beats stale proposal assumptions for {label_lower}.",
            f"Release evidence decides what changes when implementation behavior disagrees with the accepted proposal.",
        ],
        "transfer_priors": [
            f"Keep {label_lower} release scope small enough to prove with concrete behavior and evidence.",
            f"Prefer domain-specific state, owner, evidence, and failure terms over generic component labels.",
        ],
    }
    return {
        "schema_version": "odylith.greenfield.project_intelligence.v1",
        "purpose": (
            f"Explain why {label_lower} should exist, who uses it, what useful result it produces, and what stays outside the first release: {story_summary or product_view_summary}"
        ),
        "coding_posture": (
            f"Coding starts only after the {label_lower} first path, {state_lower}, {evidence_lower}, source paths, "
            "failure handling, and validation commands agree."
        ),
        "control_surface_summary": [
            story_summary or f"{label} helps a named operator complete one accountable path instead of a vague platform promise.",
            problem_summary,
            product_view_summary or opportunity_summary,
            f"The first path is: {first_path_summary}",
            f"State ownership centers on {state_lower} and its version history.",
            f"Evidence review centers on {evidence_lower} and release proof: {proof_summary}",
            f"Security covers authorization, private data, credential isolation, and abuse resistance across the accepted actor boundary: {actor_boundary}.",
            f"{label} release {release} remains limited to the first path and explicit non-goals.",
        ],
        "customization_flow": [
            f"Confirm the {label_lower} user, problem, first path, and non-goals: {non_goal_text}.",
            f"Confirm the {label_lower} state object, owner, and versioning expectation.",
            f"Confirm the {label_lower} evidence source, release-review actor, and replay requirement.",
            f"Confirm release {release} promotion gates and deferred integrations.",
        ],
        **rows,
    }

def _parent_workstream_title(*, label: str, first_path: str) -> str:
    return (
        _title_label(f"Prove one complete {label} path")
        or f"Prove one complete {label} path"
    )


def _actor_boundary_summary(values: list[str] | None, *, fallback: str) -> str:
    labels = [str(value or "").split("—", 1)[0].strip(" .") for value in values or [] if str(value or "").strip()]
    if not labels:
        return fallback
    if len(labels) == 1:
        return labels[0]
    first_two = join_actor_labels(labels[:2], limit=2)
    remaining = len(labels) - 2
    if remaining <= 0:
        return first_two
    return f"{first_two}, plus {remaining} additional accepted role{'s' if remaining != 1 else ''}"


__all__ = ["build_confirmed_greenfield_proposal"]
