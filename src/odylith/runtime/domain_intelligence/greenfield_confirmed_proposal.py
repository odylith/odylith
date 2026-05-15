"""Apply-ready greenfield proposal construction after intent confirmation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import (
    confirmed_components,
    confirmed_project_brief,
    domain_label,
    shell_quote,
)
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
    """Return the proposal object that ``greenfield apply`` consumes directly."""

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
        f"{label} gives a named user one accountable workflow with owned state and reviewable proof.",
    )
    state_object = confirmed_intent_summary(confirmed_intent, "state_object", f"{label} record")
    first_path = confirmed_intent_summary(
        confirmed_intent,
        "first_path",
        f"One user completes the first {label_lower} workflow from intake through state update and evidence review.",
    )
    proof_boundary = confirmed_intent_summary(
        confirmed_intent,
        "proof_boundary",
        f"Release {release} is trustworthy only when the first workflow, state object, and evidence record can be reviewed together.",
    )
    human_actors = confirmed_intent_list(confirmed_intent, "human_actors")
    external_systems = confirmed_intent_list(confirmed_intent, "external_systems")
    internal_systems = confirmed_intent_list(confirmed_intent, "internal_systems")
    assumptions = confirmed_intent_list(confirmed_intent, "assumptions")
    ambiguities = confirmed_intent_list(confirmed_intent, "ambiguities")
    non_goals = confirmed_intent_list(confirmed_intent, "non_goals")
    if not (product_story and state_object and first_path and proof_boundary and human_actors and len(internal_systems) >= 2):
        raise ValueError(
            "confirmed greenfield proposal requires product story, state object, first path, proof boundary, "
            "human actors, and at least two internal product systems from the accepted Product Intent Confirmation."
        )
    evidence_record = _evidence_record_label(label=label, proof_boundary=proof_boundary, internal_systems=internal_systems)
    components = confirmed_components(
        label=label,
        label_slug=label_slug,
        internal_systems=internal_systems,
        first_path=first_path,
    )
    workflow_title, boundary_title, proof_title = _workstream_titles(
        label=label,
        components=components,
        internal_systems=internal_systems,
    )
    diagram_slugs = {
        "context": f"{label_slug}-system-context",
        "sequence": f"{label_slug}-first-workflow",
        "ownership": f"{label_slug}-ownership-proof",
    }
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "proposal_first_confirm_before_apply",
        "intent": {
            "prompt": prompt_text,
            "title": product_title,
            "project_slug": product_slug,
            "reasoning_mode": "odylith_confirmed_apply_ready",
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
            "fit_policy": "Use product-specific nouns from the confirmed intent, then keep the first workflow narrow.",
            "provider_calls": 0,
        },
        "greenfield_ux": {
            "mode": "consumer_greenfield_confirmed_path",
            "write_guardrail": "No product records are written until create or apply receives --confirm.",
            "next_best_action": f"Apply the accepted {label_lower} first workflow through release {release}.",
        },
        "assumptions": [
            {
                "id": "ASM-001",
                "tier": "user_intent",
                "statement": assumptions[0] if assumptions else (
                    f"{label} starts with the user, workflow, and proof boundary accepted in the Product Intent Confirmation."
                ),
                "confirm_when": "The product owner confirms the first operating context and user group.",
            },
            {
                "id": "ASM-002",
                "tier": "odylith_assumption",
                "statement": (
                    f"External data, devices, services, or providers for {label_lower} stay fixture-backed or "
                    "sandboxed until source-backed contracts and credentials are intentionally introduced."
                ),
                "confirm_when": "The implementation owner names a live integration and its proof boundary.",
            },
        ],
        "open_questions": [
            {
                "id": "OQ-001",
                "question": ambiguities[0] if ambiguities else f"Which person must complete the first {label_lower} workflow without assistance?",
                "impact": "Changes the visible flow, permission model, and validation target.",
                "default_if_unanswered": "Use the first confirmed operator named in the Product Intent Confirmation.",
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
                "title": f"{label} workflow ambiguity",
                "statement": (
                    f"If implementation drifts from the accepted first workflow, the product can lose the user, "
                    f"problem, and domain evidence that made the confirmation trustworthy: {first_path}"
                ),
                "severity": "high",
                "mitigation": "Keep release 0.0.1 limited to one complete workflow with explicit non-goals and proof gates.",
            },
            {
                "id": "RISK-002",
                "title": f"{label} evidence weakness",
                "statement": (
                    f"If the accepted proof boundary is not visible in the generated records, reviewers cannot trust "
                    f"release {release}: {proof_boundary}"
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
            f"The state object can be reconstructed and reviewed: {state_object}",
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
            human_actors=human_actors,
            internal_systems=internal_systems,
            external_systems=external_systems,
            non_goals=non_goals,
        ),
        "program": _program(
            label=label,
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
            workflow_title=workflow_title,
            boundary_title=boundary_title,
            proof_title=proof_title,
            state_object=state_object,
            evidence_record=evidence_record,
            product_story=product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
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
            product_story=product_story,
            first_path=first_path,
            proof_boundary=proof_boundary,
            human_actors=human_actors,
            external_systems=external_systems,
            internal_systems=internal_systems,
        ),
        "apply_commands": [
            "odylith greenfield create --repo-root . --prompt "
            + shell_quote(prompt_text)
            + " --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release "
            + shell_quote(release),
            "# optional file workflow for review-only use: write `odylith greenfield propose --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm-intent --format json` to a file, then pass that file to apply",
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
    human_actors: list[str] | None = None,
    internal_systems: list[str] | None = None,
    external_systems: list[str] | None = None,
    non_goals: list[str] | None = None,
) -> dict[str, Any]:
    label_lower = label.lower()
    state_lower = state_object.lower()
    evidence_lower = evidence_record.lower()
    actors = _join_items(human_actors) or f"the first {label_lower} operator and reviewer"
    internals = _join_items(internal_systems) or f"{state_lower} owner and {evidence_lower} owner"
    externals = _join_items(external_systems) or "fixture-backed or deferred external systems"
    non_goal_text = _join_items(non_goals) or "broad platform automation and live irreversible integrations"
    rows = {
        "intent": [
            product_story or f"{label} gives a named operator one accountable workflow instead of an unbounded product outcome.",
            f"Release {release} proves the accepted first path before wider automation, integrations, or scaling claims are allowed: {first_path}",
            f"The product outcome is useful only when {actors} can see what changed, why it changed, and what evidence supports the result.",
        ],
        "scope": [
            f"In scope: {first_path}",
            f"In scope systems: {internals}. External systems: {externals}.",
            f"Out of scope: {non_goal_text} until the first path holds.",
        ],
        "ontology": [
            f"{label} actor: one of the people or teams named in the confirmed intent: {actors}.",
            f"{state_object}: the domain object that changes through the accepted first journey.",
            f"{evidence_record}: the proof record that ties the first-path result, validation output, state replay, and reviewer decision together.",
            f"{label} release gate: the decision point that blocks promotion when workflow, state, access, or evidence proof is missing.",
        ],
        "state": [
            f"{state_object} changes according to the confirmed first journey: {first_path}",
            f"State changes stay versioned so the visible {label_lower} result can be replayed instead of explained from memory.",
        ],
        "operators": [
            f"Actors involved in the first release are {actors}.",
            f"Apply state-changing actions only through the systems named in the confirmed intent: {internals}.",
            f"Assemble {evidence_lower} from the first-path result, state replay, validation output, and reviewer decision.",
        ],
        "constraints": [
            f"Do not treat {label_lower} proposal text as working behavior; readiness assertions require validation output.",
            f"Do not let evidence review mutate {state_lower}; proof can approve or block, but state changes stay owned by the state path.",
        ],
        "source_of_truth_map": [
            f"{state_object} owns current workflow state, version history, and replay inputs.",
            f"{evidence_record} owns release readiness evidence, reviewer decision, and validation references.",
        ],
        "evidence": [
            f"The proof boundary is: {proof_boundary}",
            f"Fixture-backed or sandbox evidence is acceptable for release {release}; live integrations need an explicit later contract.",
        ],
        "decisions": [
            f"Start with the smallest {label_lower} workflow that a real user can complete and review.",
            f"Delay broader platform behavior until {state_lower} and {evidence_lower} survive validation.",
        ],
        "assumptions": [
            f"The first actor set can be named before implementation starts: {actors}.",
            f"External systems remain fixture-backed, sandboxed, or deferred unless the first workflow cannot be proven without them.",
        ],
        "topology": [
            f"Internal product systems come from the Product Intent Confirmation: {internals}.",
            f"External systems stay separate from product-owned state and proof: {externals}.",
            f"The proof boundary blocks promotion when evidence is incomplete: {proof_boundary}",
        ],
        "invariants": [
            f"Every {label_lower} state change names actor, command, timestamp, input reference, and expected validation.",
            f"Every readiness assertion maps to {state_lower}, {evidence_lower}, a validation result, and an explicit non-goal boundary.",
        ],
        "risks": [
            f"{label} can sprawl if the first workflow, state object, and reviewer decision are not named before coding starts.",
            f"Trust erodes if release evidence cannot reproduce the state decision or explain why a promotion was blocked.",
        ],
        "validation_obligations": [
            f"Validate the {label_lower} success path from first input to visible completion.",
            f"Validate at least one {label_lower} validation-failure path and recovery message.",
            f"Validate state replay and evidence review so release {release} cannot pass on a persuasive narrative alone.",
        ],
        "artifacts": [
            f"{state_object} records workflow status, owner, timestamp, version, and replay reference.",
            f"{evidence_record} records validation output, state replay, reviewer decision, and release scope.",
        ],
        "owners": [
            f"The first-release actors are: {actors}.",
            f"The proof owner owns release-evidence completeness, reviewer decision, and release-readiness language.",
        ],
        "execution_memory": [
            f"Future {label_lower} work starts from the accepted first workflow, state object, and proof obligations.",
            f"Any source-backed contradiction invalidates the affected proposal assumption rather than being hidden as implementation detail.",
        ],
        "metrics": [
            f"The first workflow has zero unowned state transitions in release {release}.",
            f"Every readiness assertion has a state reference, evidence reference, validation reference, and reviewer outcome.",
        ],
        "change_model": [
            f"Changing the state object requires revisiting workflow commands, replay proof, evidence review, and release gates.",
            f"Adding a live dependency requires new access, credential, privacy, failure, and validation proof.",
        ],
        "invalidation_rules": [
            f"If workflow validation is missing, {label_lower} implementation readiness stays blocked.",
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
            f"Make the {label_lower} operating reality clear enough that a user can understand the problem, first path, owned state, and proof boundary: {product_story}"
        ),
        "coding_posture": (
            f"Coding starts only after the {label_lower} workflow, state owner, evidence owner, source paths, "
            "failure handling, and validation commands agree."
        ),
        "control_surface_summary": [
            product_story or f"{label} helps a named operator complete one accountable workflow instead of a vague platform promise.",
            f"The first workflow is: {first_path}",
            f"State ownership centers on {state_object.lower()} and its version history.",
            f"Evidence review centers on {evidence_record.lower()} and release proof: {proof_boundary}",
            f"Security covers authorization, private data, credential isolation, and abuse resistance across {actors}.",
            f"{label} release {release} remains limited to the first workflow and explicit non-goals.",
        ],
        "customization_flow": [
            f"Confirm the {label_lower} user, problem, first workflow, and non-goals: {non_goal_text}.",
            f"Confirm the {label_lower} state object, owner, and versioning expectation.",
            f"Confirm the {label_lower} evidence source, reviewer, and replay requirement.",
            f"Confirm release {release} promotion gates and deferred integrations.",
        ],
        **rows,
    }


def _workstream_titles(*, label: str, components: list[dict[str, Any]], internal_systems: list[str]) -> tuple[str, str, str]:
    labels = [str(row.get("label", "")).strip() for row in components if str(row.get("label", "")).strip()]
    if len(labels) >= 3 and internal_systems:
        return (
            f"Prove {labels[0]}",
            f"Define {labels[1]} Boundary",
            f"Prepare {labels[2]} Release Proof",
        )
    return (
        f"Prove {label} First Workflow",
        f"Define {label} State And Evidence Boundaries",
        f"Prepare {label} Release Proof",
    )


def _evidence_record_label(*, label: str, proof_boundary: str, internal_systems: list[str]) -> str:
    for system in internal_systems:
        name = str(system).casefold()
        if any(token in name for token in ("evidence", "audit", "proof", "review", "ledger")):
            first = str(system).split("—", 1)[0].split("-", 1)[0].split(":", 1)[0].strip()
            if first:
                return f"{first} proof record"
    if proof_boundary:
        return f"{label} proof record"
    return f"{label} proof record"


def _join_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [str(item).strip().rstrip(".") for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return "; ".join(selected) + suffix


def _program(
    *,
    label: str,
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
        "recommended_first_wave": f"{label} workflow proof",
        "blueprint": {
            "program_type": "greenfield_program",
            "parent_workstream": f"Establish {label} Program",
            "child_workstream_strategy": f"Separate the accepted first path, {label.lower()} state ownership, and release proof before implementation.",
            "child_workstreams": [workflow_title, boundary_title, proof_title],
            "wave_to_workstream_policy": "Waves describe delivery order while child workstreams carry owned product slices.",
            "release_strategy": f"Target release {release} only after first workflow, state replay, and proof review pass.",
            "recommended_wave_order": [
                f"{label} workflow proof",
                f"{label} state and evidence boundary",
                f"{label} release review",
            ],
            "evidence_tier": "odylith_assumption",
        },
        "waves": [
            {
                "wave": 1,
                "label": f"{label} workflow proof",
                "goal": f"Prove the accepted {label.lower()} first path from intake to visible completion.",
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
        "label": f"{label} {release} first workflow",
        "provisional_release_id": f"release-{label_slug}-{slugify(release)}",
        "strategy": f"Promote {label.lower()} only after workflow, state replay, access, and evidence review proof pass.",
        "target_workstream_titles": [workflow_title, boundary_title, proof_title],
        "release_stages": [
            {
                "stage": "wave-1",
                "label": f"{label} workflow proof",
                "release_gate": f"{label} first workflow passes success, failure, replay, and evidence checks.",
                "workstream_titles": [workflow_title],
            }
        ],
        "milestones": [
            {
                "name": f"{label} release review accepted",
                "exit_criteria": f"The product owner accepts the {label.lower()} workflow, non-goals, and release proof.",
            }
        ],
        "promotion_criteria": [
            f"{label} workflow proof passes with representative inputs.",
            f"{label} state replay matches the visible completion decision.",
            f"{label} release evidence maps every readiness assertion to validation output.",
        ],
        "evidence_tier": "odylith_assumption",
    }


def _backlog(
    *,
    label: str,
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
) -> list[dict[str, Any]]:
    component_ids = [str(row["component_id"]) for row in components]
    actors = _join_items(human_actors) or f"{label} users and reviewers"
    internals = _join_items(internal_systems) or f"{state_object} and {evidence_record}"
    externals = _join_items(external_systems) or "fixture-backed or deferred external systems"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    primary_component = str(components[0]["label"]) if components else f"{label} first component"
    proof_component = str(components[-1]["label"]) if components else f"{label} proof component"
    second_component = str(components[1]["label"]) if len(components) > 1 else primary_component
    parent = _backlog_row(
        label=label,
        title=f"Establish {label} Program",
        problem=product_story,
        customer=actors,
        opportunity=f"Make the accepted first workflow implementable without losing the user, problem, state object, or proof boundary: {first_path}",
        product_view=f"{label} should create this operational reality: {proof_boundary}",
        first_slice=first_path,
        metrics=[
            f"Release records preserve the product story before implementation planning: {product_story}",
            f"Release proof stays inside the accepted boundary: {proof_boundary}",
        ],
        component_focus=component_ids,
        diagram_focus=list(diagram_slugs.values()),
        dependencies=[f"Depends on confirmed human actors ({actors}) and product-owned systems ({internals})."],
        interfaces=[f"Program handoff names the first workflow, state object, proof boundary, non-goals, and internal systems."],
        validation=[f"Review confirms generated workstreams, component specs, and diagrams all explain the same first path: {first_path}"],
        state_object=state_object,
        evidence_record=evidence_record,
        first_path=first_path,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
        workstream_type="program_parent",
    )
    workflow = _backlog_row(
        label=label,
        title=workflow_title,
        problem=f"The first user path must be built around the accepted product workflow, not a generic workflow abstraction: {first_path}",
        customer=actors,
        opportunity=f"Prove the smallest usable product journey that makes the confirmed story real.",
        product_view=f"{primary_component} owns the first operational path needed by {actors}.",
        first_slice=first_path,
        metrics=[
            f"The first path can be completed, rejected, and corrected in domain terms: {first_path}",
            f"Every visible result cites {state_object} and {evidence_record}.",
        ],
        component_focus=component_ids[: max(1, min(2, len(component_ids)))],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on {second_component} where the first path needs durable state or supporting evidence."],
        interfaces=[f"Expose the first workflow operations required by the confirmed path: {first_path}"],
        validation=[f"End-to-end proof covers the first path, at least one domain failure, and reviewer-visible recovery."],
        state_object=state_object,
        evidence_record=evidence_record,
        first_path=first_path,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    boundary = _backlog_row(
        label=label,
        title=boundary_title,
        problem=f"{label} cannot be trusted if state, evidence, ownership, and review boundaries drift away from the confirmed product reality.",
        customer=actors,
        opportunity=f"Make product-owned systems explicit: {internals}. Keep external systems separate: {externals}.",
        product_view=f"The state object is {state_object}. The proof record is {evidence_record}. The release boundary is {proof_boundary}.",
        first_slice=f"Show how {state_object} changes through the first path and how {evidence_record} proves or blocks release readiness.",
        metrics=[
            f"Every state change names actor, source, owner, and evidence expectation.",
            f"Every owned system remains tied to the domain responsibility accepted in the Product Intent Confirmation.",
        ],
        component_focus=component_ids,
        diagram_focus=[diagram_slugs["ownership"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on internal product systems from the confirmed intent: {internals}."],
        interfaces=[f"State, evidence, review, and external-source interfaces stay separate and traceable."],
        validation=[f"Boundary proof rejects records that cannot explain {state_object}, {evidence_record}, or {proof_boundary}."],
        state_object=state_object,
        evidence_record=evidence_record,
        first_path=first_path,
        proof_boundary=proof_boundary,
        human_actors=human_actors,
        internal_systems=internal_systems,
        external_systems=external_systems,
        non_goals=non_goals,
    )
    proof = _backlog_row(
        label=label,
        title=proof_title,
        problem=f"Release readiness needs evidence a reviewer can inspect without trusting implementation claims.",
        customer=actors,
        opportunity=f"Make release readiness depend on the accepted proof boundary: {proof_boundary}",
        product_view=f"{proof_component} produces or participates in the evidence a reviewer needs before release work can proceed.",
        first_slice=f"Produce one proof package that maps the first path, {state_object}, validation output, and reviewer decision.",
        metrics=[
            f"Release proof lists the domain evidence required by the Product Intent Confirmation.",
            f"Release proof explicitly excludes non-goals until accepted later: {non_goal_text}.",
        ],
        component_focus=[component_ids[-1]] if component_ids else [],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["ownership"]],
        dependencies=[f"Depends on first-path validation, state replay, access posture, and evidence review output."],
        interfaces=[f"Release proof export contains validation summary, state references, evidence references, reviewer decision, and deferred scope."],
        validation=[f"Release proof fails closed when any part of the accepted proof boundary is missing: {proof_boundary}"],
        state_object=state_object,
        evidence_record=evidence_record,
        first_path=first_path,
        proof_boundary=proof_boundary,
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
    return [
        f"- why now: {opportunity}",
        f"- expected outcome: {first_slice}",
        f"- tradeoff: {title} keeps {label.lower()} focused on one releaseable path while delaying scope not accepted in the confirmation.",
        f"- deferred for now: anything outside this proof boundary waits: {proof_boundary}",
        f"- ranking basis: {label} release readiness depends on preserving the confirmed product story, domain state, evidence, and proof boundary.",
    ]


def _domain_intelligence(
    *,
    label: str,
    row_title: str,
    state_object: str,
    evidence_record: str,
    first_path: str,
    proof_boundary: str,
    human_actors: list[str],
    internal_systems: list[str],
    external_systems: list[str],
    non_goals: list[str],
) -> dict[str, Any]:
    label_lower = label.lower()
    actors = human_actors or [f"{label} product user: uses the accepted first workflow."]
    internals = internal_systems or [f"{state_object}: owns domain state.", f"{evidence_record}: owns proof review."]
    externals = external_systems or ["No live external system is accepted for the first release."]
    non_goal_text = _join_items(non_goals) or "unconfirmed broader platform behavior"
    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": slugify(label).replace("-", "_") or "confirmed_product",
        "summary": f"{row_title} preserves the accepted product story, first path, domain state, proof evidence, and non-goals.",
        "actors": actors,
        "intent": [
            f"{row_title} advances the product by making this first path real: {first_path}",
            f"{row_title} keeps {state_object}, {evidence_record}, and release proof connected to the confirmed user problem.",
        ],
        "scope": [
            f"In scope: {first_path}",
            f"Out of scope for now: {non_goal_text}.",
        ],
        "ontology": [
            f"Human actors: {_join_items(actors)}.",
            f"State object: {state_object}.",
            f"Evidence record: {evidence_record}.",
            f"Proof boundary: {proof_boundary}.",
        ],
        "state": [
            f"{state_object} changes through the accepted first journey: {first_path}",
            f"{label} state is not trusted unless the evidence record and proof boundary explain it.",
        ],
        "operators": [
            f"First-path actors perform the accepted workflow: {_join_items(actors)}.",
            f"Internal systems own product behavior: {_join_items(internals)}.",
            f"External systems remain separate from product-owned truth: {_join_items(externals)}.",
        ],
        "constraints": [
            f"Do not generate records from a thin prompt when confirmed product systems are required.",
            f"Do not claim implementation readiness from proposal prose; readiness assertions require validation output and proof evidence.",
        ],
        "source_of_truth_map": [
            f"{state_object} is the source of truth for current first-path state.",
            f"{evidence_record} is the source of truth for proof readiness and reviewer confidence.",
        ],
        "evidence_model": [
            f"{evidence_record} must show what happened, who or what produced the evidence, which state it supports, and how the reviewer can verify it.",
            f"Proof cannot pass outside the accepted boundary: {proof_boundary}",
        ],
        "decisions": [
            f"Decide whether the accepted first path is sufficient for release planning: {first_path}",
            f"Decide whether each internal system has a clear responsibility: {_join_items(internals)}.",
        ],
        "assumptions": [
            f"User intent is the evidence tier until source-backed implementation exists.",
            f"External systems stay fixture-backed, sandboxed, or deferred unless the confirmed first path requires them.",
        ],
        "topology": [
            f"Product-owned systems: {_join_items(internals)}.",
            f"External systems: {_join_items(externals)}.",
        ],
        "invariants": [
            f"Every state change must name actor, source, timestamp, and evidence expectation.",
            f"Every readiness assertion must map to {state_object}, {evidence_record}, validation output, reviewer decision, and non-goal boundary.",
        ],
        "risks": [
            f"Product comprehension fails if generated records lose the confirmed domain terms, actors, state, and evidence.",
            f"Release confidence fails if evidence cannot explain the accepted proof boundary.",
        ],
        "validation_obligations": [
            f"Validate the accepted first path in domain terms.",
            f"Validate state replay for {state_object}.",
            f"Validate proof traceability for {evidence_record} against: {proof_boundary}",
        ],
        "artifacts": [
            f"{state_object} record with actor, source, state, timestamp, and version history.",
            f"{evidence_record} with validation output, replay output, reviewer decision, and release scope.",
        ],
        "authority": [
            f"Only accepted actors or systems can move first-path state: {_join_items(actors)}.",
            f"Proof review can block release when validation, replay, access, or evidence is incomplete.",
        ],
        "owners": [
            f"Internal product systems own release responsibilities: {_join_items(internals)}.",
            f"Review ownership follows the accepted proof boundary, not generic implementation labels.",
        ],
        "execution_memory": [
            f"Future work starts from the accepted first workflow and state object.",
            f"Product-owner correction or source-backed contradiction invalidates stale assumptions.",
        ],
        "metrics": [
            f"Zero generated records are written without confirmed product systems.",
            f"Every readiness assertion has state, evidence, validation, reviewer, and non-goal references.",
        ],
        "change_model": [
            f"Changing the state object invalidates workflow, proof, and release-readiness assumptions.",
            f"Changing external dependencies invalidates security, privacy, access, and failure proof.",
        ],
        "invalidation_rules": [
            f"If confirmed narrative is missing, no records may be written.",
            f"If generated records cannot explain the accepted first path, release readiness stays blocked.",
        ],
        "conflict_model": [
            f"Confirmed product intent beats generic builder fallback.",
            f"Source-backed validation beats narrative claims when implementation behavior disagrees.",
        ],
        "transfer_priors": [
            f"Keep release scope small enough for concrete behavior proof.",
            f"Use the confirmed actors, state, systems, evidence, and failure terms in every generated record.",
        ],
    }



__all__ = ["build_confirmed_greenfield_proposal"]
