"""Governed greenfield proposal construction after intent confirmation."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import (
    confirmed_components,
    confirmed_project_brief,
    domain_label,
    shell_quote,
    system_component_name,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import compact_text as _compact_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_brief_items as _join_brief_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_items as _join_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_system_labels as _join_system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import problem_text as _problem_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_summary as _short_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import state_detail_summary as _state_detail_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagrams import confirmed_diagrams
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import (
    confirmed_intent_list,
    confirmed_intent_summary,
)


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
    product_title = intent_title or str(title or "").strip() or "Greenfield Project"
    product_slug = slugify(product_title)
    prompt_text = str(prompt or product_title).strip() or product_title
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
        f"Release {release} is trustworthy only when the first path, state object, and evidence record can be reviewed together.",
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
    evidence_record = _evidence_record_label(label=label, proof_boundary=proof_boundary, internal_systems=internal_systems)
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    first_path_summary = _short_summary(first_path, limit=360)
    proof_boundary_summary = _short_summary(proof_boundary, limit=320)
    components = confirmed_components(
        label=label,
        label_slug=label_slug,
        internal_systems=internal_systems,
        first_path=first_path,
        state_object=state_object,
        proof_boundary=proof_boundary,
    )
    workflow_title, boundary_title, proof_title = _workstream_titles(
        label=label,
        components=components,
        internal_systems=internal_systems,
    )
    parent_title = _parent_workstream_title(label)
    diagram_slugs = {
        "context": f"{label_slug}-system-context",
        "sequence": f"{label_slug}-first-path",
        "state_evidence": f"{label_slug}-state-evidence",
        "component_boundaries": f"{label_slug}-component-boundaries",
        "ownership": f"{label_slug}-ownership-proof",
        "proof_review": f"{label_slug}-release-proof-review",
    }
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
            "first_path": first_path,
            "proof_boundary": proof_boundary,
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
        "risks": [
            {
                "id": "RISK-001",
                "title": f"{label} first-path ambiguity",
                "statement": (
                    f"If the accepted first path is ambiguous, {label.lower()} users cannot tell which state changed, "
                    f"which source produced the evidence, or which decision is safe to make: {first_path_summary}"
                ),
                "severity": "high",
                "mitigation": "Keep release 0.0.1 limited to one complete path with explicit non-goals and proof gates.",
            },
            {
                "id": "RISK-002",
                "title": f"{label} evidence weakness",
                "statement": (
                    f"If the accepted proof boundary is not visible in the release records, reviewers cannot trust "
                    f"release {release}: {proof_boundary_summary}"
                ),
                "severity": "high",
                "mitigation": "Require deterministic replay, audit identity, and source references for every readiness assertion.",
            },
        ],
        "security_compliance": {
            "domain": (
                f"{label} carries domain risk around the accepted state object, evidence boundary, actors, and "
                "decisions based on stale or incomplete data."
            ),
            "security": (
                f"Security posture for {label_lower} covers authentication, authorization, ownership checks, "
                "credential isolation, abuse prevention, and private data handling."
            ),
            "policy": (
                f"Compliance posture for {label_lower} keeps privacy, audit retention, accessibility, safety, "
                "and operational review visible before production claims are made."
            ),
        },
        "validation_strategy": [
            f"The accepted first path passes end to end: {first_path}",
            f"The state object can be reconstructed and reviewed: {state_label}.",
            f"The release proof matches the accepted proof boundary: {proof_boundary}",
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
        "program": _program(
            label=label,
            parent_title=parent_title,
            release=release,
            workflow_title=workflow_title,
            boundary_title=boundary_title,
            proof_title=proof_title,
            components=components,
        ),
        "release_plan": _release_plan(
            label=label,
            label_slug=label_slug,
            release=release,
            workflow_title=workflow_title,
            boundary_title=boundary_title,
            proof_title=proof_title,
        ),
        "backlog": _backlog(
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
            components=components,
            diagram_slugs=diagram_slugs,
        ),
        "components": components,
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
    return proposal


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
    proof_summary = _short_summary(proof_boundary, limit=320)
    state_summary = _state_detail_summary(state_object, state_label=state_label, limit=260)
    actors = _join_actor_labels(human_actors) or _short_summary(customer, limit=220) or f"the first {label_lower} operator and reviewer"
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
            f"{evidence_label}: the proof record that ties the first-path result, validation output, state replay, and reviewer decision together.",
            f"{label} release gate: the decision point that blocks promotion when first-path, state, access, or evidence proof is missing.",
        ],
        "state": [
            f"{state_label} changes according to the confirmed first journey: {first_path_summary}",
            f"State changes stay versioned so the visible {label_lower} result can be replayed instead of explained from memory.",
        ],
        "operators": [
            f"Actors involved in the first release are {actors}.",
            f"Route state-changing actions only through the systems named in the confirmed intent: {internals}.",
            f"Assemble {evidence_lower} from the first-path result, state replay, validation output, and reviewer decision.",
        ],
        "constraints": [
            f"Do not treat {label_lower} proposal text as working behavior; readiness assertions require validation output.",
            f"Do not let evidence review mutate {state_lower}; proof can approve or block, but state changes stay owned by the state path.",
        ],
        "source_of_truth_map": [
            f"{state_label} owns current first-path state, version history, and replay inputs.",
            f"{evidence_label} owns release readiness evidence, reviewer decision, and validation references.",
        ],
        "evidence": [
            f"The proof boundary is: {proof_summary}",
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
            f"The proof boundary blocks promotion when evidence is incomplete: {proof_summary}",
        ],
        "invariants": [
            f"Every {label_lower} state change names actor, command, timestamp, input reference, and expected validation.",
            f"Every readiness assertion maps to {state_lower}, {evidence_lower}, a validation result, and an explicit non-goal boundary.",
        ],
        "risks": [
            f"{label} can sprawl if the first path, state object, and reviewer decision are not named before coding starts.",
            f"Trust erodes if release evidence cannot reproduce the state decision or explain why a promotion was blocked.",
        ],
        "validation_obligations": [
            f"Validate the {label_lower} success path from first input to reviewer-visible outcome.",
            f"Validate at least one {label_lower} validation-failure path and recovery message.",
            f"Validate state replay and evidence review so release {release} cannot pass on a persuasive narrative alone.",
        ],
        "artifacts": [
            f"{state_label} history captures first-path status, owner, timestamp, version, and replay reference.",
            f"{evidence_label} captures validation output, replay output, reviewer decision, and release scope.",
        ],
        "owners": [
            f"The first-release actors are: {actors}.",
            f"The proof owner owns release-evidence completeness, reviewer decision, and release-readiness language.",
        ],
        "execution_memory": [
            f"Future {label_lower} work starts from the accepted first path, state object, and proof obligations.",
            f"Any source-backed contradiction invalidates the affected proposal assumption rather than being hidden as implementation detail.",
        ],
        "metrics": [
            f"The first path has zero unowned state transitions in release {release}.",
            f"Every readiness assertion has a state reference, evidence reference, validation reference, and reviewer outcome.",
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
            f"Make the {label_lower} operating reality clear enough that a user can understand the problem, first path, owned state, and proof boundary: {story_summary or product_view_summary}"
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
            f"Confirm the {label_lower} evidence source, reviewer, and replay requirement.",
            f"Confirm release {release} promotion gates and deferred integrations.",
        ],
        **rows,
    }


def _workstream_titles(*, label: str, components: list[dict[str, Any]], internal_systems: list[str]) -> tuple[str, str, str]:
    labels = [
        _workstream_subject(str(row.get("label", "")).strip())
        for row in components
        if str(row.get("label", "")).strip()
    ]
    if len(labels) >= 3 and internal_systems:
        proof_label = labels[-1] if len(labels) > 3 else labels[2]
        return (
            f"Build {labels[0]} First Path",
            f"Implement {labels[1]} State Handoffs",
            f"Build {proof_label} Proof Review",
        )
    return (
        f"Build {label} First Path",
        f"Implement {label} State Handoffs",
        f"Build {label} Proof Review",
    )


def _parent_workstream_title(label: str) -> str:
    return f"Ship {label} First Release"


def _workstream_subject(value: str) -> str:
    text = _compact_text(value)
    text = re.sub(r"\s+(Service|Surface|Component|Boundary)$", "", text, flags=re.IGNORECASE).strip()
    return text or value


def _evidence_record_label(*, label: str, proof_boundary: str, internal_systems: list[str]) -> str:
    for system in internal_systems:
        name = str(system).casefold()
        if any(token in name for token in ("evidence", "audit", "proof", "ledger", "history", "trace")):
            first = str(system).split("—", 1)[0].split("-", 1)[0].split(":", 1)[0].strip()
            if first:
                return f"{system_component_name(first)} proof record"
    if proof_boundary:
        return f"{label} proof record"
    return f"{label} proof record"


def _program(
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
                "goal": f"Prove the accepted {label.lower()} first path from intake to reviewer-visible outcome.",
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
                "validation_gate": f"{label} release proof names validation result, reviewer, failure mode, and recovery expectation.",
                "workstream_titles": [proof_title],
                "component_focus": [component_ids[-1]],
                "evidence_tier": "odylith_assumption",
            },
        ],
    }


def _release_plan(
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
            f"{label} state replay matches the reviewer-visible outcome decision.",
            f"{label} release evidence maps every readiness assertion to validation output.",
        ],
        "evidence_tier": "odylith_assumption",
    }


def _component_label_at(components: list[dict[str, Any]], index: int, *, fallback: str) -> str:
    if not components:
        return fallback
    bounded_index = min(max(index, 0), len(components) - 1)
    value = str(components[bounded_index].get("label", "")).strip()
    return value or fallback


def _component_contract_at(components: list[dict[str, Any]], index: int) -> Mapping[str, Any]:
    if not components:
        return {}
    bounded_index = min(max(index, 0), len(components) - 1)
    contract = components[bounded_index].get("component_contract")
    return contract if isinstance(contract, Mapping) else {}


def _contract_clause(contract: Mapping[str, Any], key: str, *, fallback: str) -> str:
    value = _short_summary(str(contract.get(key) or ""), limit=220)
    return value or fallback


def _first_clause(value: str) -> str:
    text = _short_summary(value, limit=220)
    parts = [part.strip(" .") for part in re.split(r"[,.;]", text, maxsplit=1) if part.strip(" .")]
    return parts[0] if parts else text


def _backlog(
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
    first_path_entry = _first_clause(first_path_summary)
    proof_summary = _short_summary(proof_boundary, limit=340)
    evidence_phrase = "quality evidence" if "quality evidence" in first_path_summary.casefold() else f"{state_label} evidence"
    actors = _join_actor_labels(human_actors) or _short_summary(customer, limit=260) or f"{label} users and reviewers"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    primary_component = _workstream_subject(_component_label_at(components, 0, fallback=f"{label} first path"))
    second_component = _workstream_subject(_component_label_at(components, 1, fallback=primary_component))
    proof_component = _workstream_subject(
        _component_label_at(components, len(components) - 1, fallback=f"{label} proof review")
    )
    primary_contract = _component_contract_at(components, 0)
    state_contract = _component_contract_at(components, 1 if len(components) > 1 else 0)
    proof_contract = _component_contract_at(components, len(components) - 1)
    primary_inputs = _contract_clause(primary_contract, "accepted_inputs", fallback="the first user action and required domain input")
    primary_outputs = _contract_clause(primary_contract, "produced_outputs", fallback=f"a visible {label.lower()} result")
    state_owned = _contract_clause(state_contract, "owned_state", fallback=f"{state_label} lifecycle and handoff state")
    state_outputs = _contract_clause(state_contract, "produced_outputs", fallback=f"{state_label} status, blockers, and handoff output")
    proof_outputs = _contract_clause(proof_contract, "produced_outputs", fallback=f"{evidence_label} review result")
    parent = _backlog_row(
        label=label,
        title=parent_title,
        problem=problem_summary,
        customer=actors,
        opportunity=opportunity_summary
        or f"Build the first release around {primary_component}, {second_component}, and {proof_component}.",
        product_view=product_view_summary
        or f"{label} is useful when {actors} can complete the first path and inspect the resulting {state_label}.",
        first_slice=first_path_summary,
        metrics=[
            *(success_metrics or [])[:1],
            f"{primary_component} runs from first user action to visible result: {first_path_summary}.",
            f"{second_component} keeps {state_label} success, blocked, and review states understandable.",
            f"{proof_component} shows evidence for the accepted release boundary: {proof_summary}.",
        ],
        component_focus=component_ids,
        diagram_focus=list(diagram_slugs.values()),
        dependencies=[
            f"Depends on the accepted actors, external sources, and product systems needed for {first_path_summary}."
        ],
        interfaces=[
            f"Release scope connects {primary_component}, {second_component}, and {proof_component} without absorbing deferred scope."
        ],
        validation=[
            f"Release review validates the accepted first path and proof boundary. First path: {first_path_summary}. Proof boundary: {proof_summary}."
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
        problem=f"{primary_component} can fail when the first accepted action is missing or unclear: {first_path_entry}.",
        customer=actors,
        opportunity=(
            f"Build the narrow {primary_component} entry, actions, feedback, and handoff before adding deferred scope."
        ),
        product_view=(
            f"{primary_component} accepts {primary_inputs}, keeps {evidence_phrase} visible for {state_label}, "
            f"coordinates with {second_component}, and produces {primary_outputs}."
        ),
        first_slice=f"Implement {primary_component} intake, validation feedback, blocked-state recovery, and handoff to {second_component}.",
        metrics=[
            f"A user completes the path through {primary_component} and sees a clear success, blocked, or recovery result.",
            f"Missing or invalid domain input is rejected before it corrupts {state_label}.",
            f"The first-path result hands the right state to {second_component}.",
        ],
        component_focus=component_ids[: max(1, min(2, len(component_ids)))],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["sequence"], diagram_slugs["state_evidence"]],
        dependencies=[f"Depends on {second_component} for durable state, blockers, and recovery handoff."],
        interfaces=[f"Expose the minimum user entrypoints and commands needed for {first_path_summary}."],
        validation=[f"End-to-end proof covers success, missing input, and recovery for {primary_component}."],
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
        problem=f"{label} can produce false confidence if {state_label} changes without actor, source, status, and evidence ownership.",
        customer=actors,
        opportunity=(
            f"Implement {second_component} as the state and handoff boundary for accepted inputs, outputs, blocked states, "
            "and external-source references."
        ),
        product_view=f"{second_component} keeps {state_label} trustworthy by owning {state_owned} and producing {state_outputs}.",
        first_slice=f"Implement {second_component} state transitions, ownership markers, blocked states, and downstream handoffs for {state_label}.",
        metrics=[
            f"Every {state_label} change names actor, source, status, owner, and evidence expectation.",
            f"External inputs are accepted, quarantined, or rejected before they change {state_label}.",
            f"Downstream consumers can distinguish success, blocked, stale, and review-needed states.",
        ],
        component_focus=[component_ids[1]] if len(component_ids) > 1 else component_ids,
        diagram_focus=[
            diagram_slugs["state_evidence"],
            diagram_slugs["component_boundaries"],
            diagram_slugs["ownership"],
        ],
        dependencies=[f"Depends on {primary_component} for user actions and on accepted external sources for source evidence."],
        interfaces=[f"State, evidence, review, and external-source interfaces stay separate around {second_component}."],
        validation=[f"State proof rejects transitions that cannot explain {state_label}, source evidence, or owner."],
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
            f"{proof_component} cannot support release review unless it replays source evidence, validation output, "
            "non-goals, and reviewer decision."
        ),
        customer=actors,
        opportunity=(
            f"Build the {proof_component} review output with validation results, state references, reviewer decision, and deferred scope."
        ),
        product_view=f"{proof_component} produces {proof_outputs} and shows whether the accepted proof boundary is satisfied.",
        first_slice=f"Implement one reviewable {evidence_label} output for the first path, validation result, and reviewer decision.",
        metrics=[
            f"{evidence_label} links source input, {state_label}, validation output, reviewer decision, and outcome.",
            f"Missing evidence blocks proof review instead of producing a release-ready claim.",
            "The proof view checks the accepted proof boundary without expanding deferred scope.",
            f"The proof view keeps deferred scope visible: {non_goal_text}.",
        ],
        component_focus=[component_ids[-1]] if component_ids else [],
        diagram_focus=[diagram_slugs["ownership"], diagram_slugs["proof_review"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on {second_component} state replay, {primary_component} path proof, and reviewer access posture."],
        interfaces=[
            f"{proof_component} exposes validation summary, state references, evidence references, reviewer decision, and deferred scope."
        ],
        validation=[
            "Proof review fails closed when success evidence, replay evidence, access proof, privacy proof, or reviewer evidence is missing."
        ],
        state_object=state_label,
        evidence_record=evidence_label,
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
        "rationale_lines": _rationale_lines(
            label=label,
            title=title,
            opportunity=opportunity,
            first_slice=first_slice,
            proof_boundary=proof_boundary,
        ),
        "domain_intelligence": _domain_intelligence(
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
    if not why_now:
        why_now = "Clarify the accepted product boundary before implementation starts"
    if not expected_outcome:
        expected_outcome = "Produce the first reviewable release outcome"
    return [
        f"- why now: {why_now}.",
        f"- expected outcome: {expected_outcome}.",
        f"- tradeoff: Keep {title} narrow enough to prove before adjacent product scope expands.",
        f"- deferred for now: Scope outside {title} waits for explicit product evidence.",
        f"- ranking basis: {title} unblocks the next build decision for {label}.",
    ]


def _domain_intelligence(
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
    actors = human_actors or [f"{label} product user: uses the accepted first path."]
    internals = internal_systems or [f"{state_object}: owns domain state.", f"{evidence_record}: owns proof review."]
    internal_labels = _join_system_labels(internals) or _join_items(internals)
    externals = external_systems or ["No live external system is accepted for the first release."]
    non_goal_text = _join_items(non_goals) or "unconfirmed broader platform behavior"
    focus = _short_summary(product_view or first_slice or opportunity, limit=360)
    risk = _short_summary(problem, limit=300) or f"{label} can fail if {row_title} is too vague to implement."
    build_scope = _short_summary(first_slice or first_path, limit=320)
    metric_summary = _join_brief_items(metrics, limit=3, item_limit=140)
    dependency_summary = _join_brief_items(dependencies, limit=2, item_limit=150)
    interface_summary = _join_brief_items(interfaces, limit=2, item_limit=150)
    validation_summary = _join_brief_items(validation, limit=3, item_limit=150)
    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": slugify(label).replace("-", "_") or "confirmed_product",
        "summary": focus or f"{row_title} turns the accepted {label} slice into buildable product behavior.",
        "actors": actors,
        "intent": [
            focus or f"{row_title} advances {label} by building one concrete product slice.",
            f"User problem: {risk}",
        ],
        "scope": [
            f"Build scope: {build_scope}",
            f"Out of scope for now: {non_goal_text}.",
        ],
        "ontology": [
            f"Actors include {_join_actor_labels(actors) or _join_items(actors)}.",
            f"State object: {state_object}.",
            f"Evidence record: {evidence_record}.",
            f"Proof boundary: {proof_boundary}.",
        ],
        "state": [
            f"State focus: {build_scope}",
            f"Owned state remains trustworthy only when {state_object} and {evidence_record} explain the visible outcome.",
        ],
        "operators": [
            f"Build operations: {interface_summary or build_scope}.",
            f"Internal systems involved here: {internal_labels}.",
            f"External source boundaries here: {_join_items(externals)}.",
        ],
        "constraints": [
            f"Keep {row_title} inside the accepted first-release scope: {non_goal_text}.",
            f"Do not claim {row_title} ready until validation demonstrates: {validation_summary or proof_boundary}.",
        ],
        "source_of_truth_map": [
            f"{state_object} is the source of truth for current first-path state.",
            f"{evidence_record} is the source of truth for proof readiness and reviewer confidence.",
        ],
        "evidence_model": [
            f"Evidence for this slice: {validation_summary or proof_boundary}.",
            f"{evidence_record} must show source input, state reference, validation result, reviewer decision, and visible outcome.",
        ],
        "decisions": [
            f"Decide whether {row_title} delivers its local outcome: {metric_summary or build_scope}.",
            f"Decide whether dependencies are ready: {dependency_summary or internal_labels}.",
        ],
        "assumptions": [
            f"User intent is the evidence tier until source-backed implementation exists.",
            f"External systems stay simulated, sandboxed, or deferred unless the confirmed first path requires them.",
        ],
        "topology": [
            f"Product-owned systems: {internal_labels}.",
            f"External systems: {_join_items(externals)}.",
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
            f"Validate that {row_title} satisfies its local success criteria: {metric_summary or build_scope}.",
            f"Validate that {row_title} handles a blocked or recovery path without hiding missing evidence.",
        ],
        "artifacts": [
            f"{state_object} history captures the local states needed by {row_title}.",
            f"{evidence_record} captures validation output, replay output, reviewer decision, and deferred scope.",
        ],
        "authority": [
            f"Only accepted actors or systems can move first-path state: {_join_actor_labels(actors) or _join_items(actors)}.",
            f"{row_title} can block the first release when validation, replay, access, or evidence is incomplete.",
        ],
        "owners": [
            f"Internal product systems own this slice: {internal_labels}.",
            f"Review ownership follows the accepted proof boundary and this row's local validation.",
        ],
        "execution_memory": [
            f"Future work starts from the accepted first path and this row's local build outcome.",
            f"Product-owner correction or source-backed contradiction invalidates stale assumptions.",
        ],
        "metrics": [
            metric_summary or f"{row_title} has a user-visible success, blocked, and recovery signal.",
            f"Every readiness assertion for {row_title} has state, evidence, validation, reviewer, and non-goal references.",
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
            f"Use confirmed actors, state, systems, evidence, and failure terms in this slice.",
        ],
    }


_GENERIC_ACTOR_PREFIXES: tuple[str, ...] = (
    "Operator",
    "Maintainer",
    "Reviewer",
    "Primary user",
    "Project operator",
    "Domain reviewer",
    "Implementation owner",
    "Evidence owner",
    "End-user advocate",
    "Workflow operator",
    "Risk reviewer",
    "Proof reviewer",
    "Build owner",
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


def _join_actor_labels(values: list[str] | None, *, limit: int = 5) -> str:
    labels: list[str] = []
    for value in values or []:
        label = _compact_text(str(value)).split("—", 1)[0].split(":", 1)[0].strip(" .")
        if label and label.casefold() not in {"other accepted items"}:
            labels.append(label)
    selected = list(dict.fromkeys(labels))[:limit]
    if not selected:
        return ""
    suffix = "" if len(labels) <= limit else ", and other accepted actors"
    return ", ".join(selected) + suffix


def _project_specific_actor_row(row: str, *, focus: str) -> str:
    for prefix in _GENERIC_ACTOR_PREFIXES:
        match = re.match(rf"^{re.escape(prefix)}(?P<tail>\s*(?::|[-–—/]|$).*)", row)
        if not match:
            continue
        replacement = f"{_role_focus(focus, prefix)} {prefix}"
        tail = re.sub(r"^\s+", " ", match.group("tail"))
        return f"{replacement}{tail}".strip()
    return row


def _actor_focus_label(label: str) -> str:
    text = re.sub(
        r"\b(?:workspace|tracker|platform|system|application|app|tool|service|product|program)\b",
        "",
        str(label or ""),
        flags=re.IGNORECASE,
    )
    text = " ".join(text.replace(":", " ").split()).strip(" -")
    return text or str(label or "Project").strip() or "Project"


def _role_focus(focus: str, role: str) -> str:
    text = str(focus or "").strip()
    if role.casefold() == "reviewer":
        text = re.sub(r"\breview$", "", text, flags=re.IGNORECASE).strip()
    return text or str(focus or "").strip() or "Project"



__all__ = ["build_confirmed_greenfield_proposal"]
