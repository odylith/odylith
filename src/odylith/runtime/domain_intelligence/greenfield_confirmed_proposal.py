"""Governed greenfield proposal construction after intent confirmation."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_backlog_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_evidence_record_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog import confirmed_program
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items as _join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels as _join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import problem_text as _problem_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary as _state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label as _title_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import (
    confirmed_intent_list,
    confirmed_intent_summary,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import health_safety_obligations
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks


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
    prompt_text = str(prompt or product_title).strip() or product_title
    if title_normalization.changed:
        prompt_text = prompt_text.replace(title_normalization.raw_title, product_title).strip() or product_title
    label = domain_label(product_title, prompt_text)
    label_lower = label.lower()
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
    human_actors = _project_specific_actor_rows(
        label=label,
        rows=confirmed_intent_list(confirmed_intent, "human_actors"),
    )
    external_systems = confirmed_intent_list(confirmed_intent, "external_systems")
    internal_systems = confirmed_intent_list(confirmed_intent, "internal_systems")
    assumptions = confirmed_intent_list(confirmed_intent, "assumptions")
    ambiguities = confirmed_intent_list(confirmed_intent, "ambiguities")
    non_goals = confirmed_intent_list(confirmed_intent, "non_goals")
    problem_summary = confirmed_intent_summary(confirmed_intent, "problem", "")
    customer_summary = confirmed_intent_summary(confirmed_intent, "customer", "")
    opportunity_summary = confirmed_intent_summary(confirmed_intent, "opportunity", "")
    product_view_summary = confirmed_intent_summary(confirmed_intent, "product_view", "")
    success_metrics = confirmed_intent_list(confirmed_intent, "success_metrics")
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
        non_goals=non_goals,
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
    )
    semantic_model = semantic_model_mapping(
        build_greenfield_semantic_model(
            title=product_title,
            state_object=state_object,
            first_path=first_path,
            proof_boundary=proof_boundary,
            components=components,
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
            workstreams=backlog_rows,
        )
    )
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "prompt": prompt_text,
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
        "assumptions": [
            {
                "id": "ASM-001",
                "tier": "user_intent",
                "statement": assumptions[0] if assumptions else (
                    f"{label} starts with the user, first path, and proof boundary accepted in the product direction."
                ),
                "confirm_when": "The product owner confirms the first operating context and user group.",
            },
            {
                "id": "ASM-002",
                "tier": "odylith_assumption",
                "statement": (
                    f"External data, devices, services, or providers for {label_lower} stay simulated or "
                    "sandboxed until source-backed contracts and credentials are intentionally introduced."
                ),
                "confirm_when": "The implementation owner names a live integration and its proof boundary.",
            },
        ],
        "open_questions": [
            {
                "id": "OQ-001",
                "question": ambiguities[0] if ambiguities else f"Which person must complete the first {label_lower} path without assistance?",
                "impact": "Changes the visible flow, permission model, and validation target.",
                "default_if_unanswered": "Use the first confirmed operator named in the accepted product direction.",
            },
            {
                "id": "OQ-002",
                "question": ambiguities[1] if len(ambiguities) > 1 else f"What source or external system must the first {label_lower} proof trust?",
                "impact": "Changes security, privacy, fixture, and integration expectations for the first release.",
                "default_if_unanswered": "Use deterministic local fixtures until a source-backed adapter is planned.",
            },
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
            f"The accepted first path passes end to end: {first_path}",
            f"{state_label} can be reconstructed and reviewed.",
            f"The release proof explains the promised user-visible result: {proof_boundary}",
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
            prompt=prompt_text,
            release=release,
            state_object=state_object,
            evidence_record=evidence_record,
            product_story=product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
            problem=problem_summary,
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            assumptions=assumptions,
            ambiguities=ambiguities,
            non_goals=non_goals,
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
        ),
        "program": confirmed_program(
            label=label,
            parent_title=parent_title,
            release=release,
            workflow_title=workflow_title,
            boundary_title=boundary_title,
            proof_title=proof_title,
            components=release_components,
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
                "program": parent_title,
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
            "odylith greenfield create --repo-root . --prompt "
            + shell_quote(prompt_text)
            + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release "
            + shell_quote(release),
            "# optional review-only audit: odylith greenfield propose --repo-root . --prompt "
            + shell_quote(prompt_text)
            + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json",
        ],
    }
    if title_normalization.changed:
        proposal["intent"]["source_title"] = title_normalization.raw_title
    return proposal


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
    return {
        "domain": (
            f"{label} carries domain risk around {_short_summary(state_object, limit=180)}, evidence boundary, actors, "
            f"and decisions based on stale or incomplete data. First path: {_short_summary(first_path, limit=220)}."
            f"{safety_tail}"
        ),
        "security": (
            f"Security posture for {label_lower} covers authentication, authorization, ownership checks, "
            f"credential isolation, abuse prevention, and private data handling for {_short_summary(state_object, limit=180)}."
        ),
        "policy": (
            f"Compliance posture for {label_lower} names any privacy, retention, accessibility, safety, or operational-review duties "
            f"that apply to {_short_summary(state_object, limit=180)} before production claims are made."
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
) -> dict[str, Any]:
    label_lower = label.lower()
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    evidence_label = _domain_object_label(evidence_record, fallback=evidence_record)
    state_lower = state_label.lower()
    evidence_lower = evidence_label.lower()
    story_summary = _short_summary(product_story, limit=360)
    problem_summary = _problem_text(label=label, problem=problem, product_story=product_story, first_path=first_path)
    opportunity_summary = _short_summary(opportunity, limit=320) or "The accepted first path becomes the planning boundary for source work and proof."
    product_view_summary = _short_summary(product_view, limit=320) or "The first release stays narrow until source-backed behavior and review evidence exist."
    first_path_summary = _short_summary(first_path, limit=360)
    proof_summary = proof_claim_summary(proof_boundary, limit=320)
    state_summary = _state_detail_summary(state_object, state_label=state_label, limit=260)
    actors = join_actor_labels(human_actors) or _short_summary(customer, limit=220) or f"the first {label_lower} operator and reviewer"
    internals = _join_system_labels(internal_systems) or f"{state_lower} owner and {evidence_lower} owner"
    externals = _join_items(external_systems) or "explicitly deferred external systems"
    non_goal_text = _join_items(non_goals) or "broad platform automation and live irreversible integrations"
    rows = {
        "intent": [
            story_summary or f"{label} gives a named operator one accountable path instead of an unbounded product outcome.",
            problem_summary,
            f"Release {release} proves the accepted first path before wider automation, integrations, or scaling claims are allowed: {first_path_summary}",
            f"The product outcome is useful only when {actors} can see what changed, why it changed, and what evidence supports the result.",
        ],
        "scope": [
            f"In scope: {first_path_summary}",
            f"In scope systems: {internals}. External systems: {externals}.",
            f"Out of scope: {non_goal_text} until the first path holds.",
        ],
        "ontology": [
            f"{label} actor: one of the people or teams named in the confirmed intent: {actors}.",
            f"{state_label}: the domain object that changes through the accepted first journey. {state_summary}",
            f"{evidence_label}: the proof record that ties the first-path result, validation output, state replay, and release decision together.",
            f"{label} release gate: the decision point that blocks promotion when first-path, state, access, or evidence proof is missing.",
        ],
        "state": [
            f"{state_label} changes according to the confirmed first journey: {first_path_summary}",
            f"State changes stay versioned so the visible {label_lower} result can be replayed instead of explained from memory.",
        ],
        "operators": [
            f"Actors involved in the first release are {actors}.",
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
            f"Review evidence must show the promised product result: {proof_summary}",
            *[_short_summary(metric, limit=260) for metric in (success_metrics or [])[:3]],
            f"Simulated or sandbox evidence is acceptable for release {release}; live integrations need an explicit later contract.",
        ],
        "decisions": [
            f"Start with the smallest {label_lower} path that a real user can complete and review.",
            f"Delay broader platform behavior until {state_lower} and {evidence_lower} survive validation.",
        ],
        "assumptions": [
            f"The first actor set can be named before implementation starts: {actors}.",
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
            f"The first-release actors are: {actors}.",
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
            f"Source-backed validation beats narrative claims when implementation behavior disagrees with the proposal.",
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
            f"Coding starts only after the {label_lower} first path, state owner, evidence owner, source paths, "
            "failure handling, and validation commands agree."
        ),
        "control_surface_summary": [
            story_summary or f"{label} helps a named operator complete one accountable path instead of a vague platform promise.",
            problem_summary,
            product_view_summary or opportunity_summary,
            f"The first path is: {first_path_summary}",
            f"State ownership centers on {state_lower} and its version history.",
            f"Evidence review centers on {evidence_lower} and release proof: {proof_summary}",
            f"Security covers authorization, private data, credential isolation, and abuse resistance across {actors}.",
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
        _title_label(f"Make {label} useful for one complete outcome")
        or f"Make {label} useful for one complete outcome"
    )


def _project_specific_actor_rows(*, label: str, rows: list[str]) -> list[str]:
    focus = _actor_focus_label(label)
    result: list[str] = []
    for row in rows:
        text = str(row or "").strip()
        if not text:
            continue
        result.append(_project_specific_actor_row(text, focus=focus))
    return result


def _project_specific_actor_row(row: str, *, focus: str) -> str:
    return project_specific_actor_row(row, project_focus=focus) or row


def _actor_focus_label(label: str) -> str:
    text = re.sub(
        r"\b(?:workspace|tracker|platform|system|application|app|tool|service|product|program)\b",
        "",
        str(label or ""),
        flags=re.IGNORECASE,
    )
    text = " ".join(text.replace(":", " ").split()).strip(" -")
    return text or str(label or "Project").strip() or "Project"


__all__ = ["build_confirmed_greenfield_proposal"]
