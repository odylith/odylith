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


def build_confirmed_greenfield_proposal(
    *,
    prompt: str,
    title: str,
    observed_source: Mapping[str, Any],
    release_selector: str = "",
) -> dict[str, Any]:
    """Return the proposal object that ``greenfield apply`` consumes directly."""

    release = str(release_selector or "").strip() or greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR
    product_title = str(title or "").strip() or "Greenfield Project"
    product_slug = slugify(product_title)
    prompt_text = str(prompt or product_title).strip() or product_title
    label = domain_label(product_title, prompt_text)
    label_lower = label.lower()
    label_slug = slugify(label)
    state_object = f"{label} record"
    evidence_record = f"{label} evidence packet"
    workflow_title = f"Prove {label} First Workflow"
    boundary_title = f"Define {label} State And Evidence Boundaries"
    proof_title = f"Prepare {label} Release Proof"
    components = confirmed_components(label=label, label_slug=label_slug)
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
                f"{label} turns the confirmed request into a first usable workflow, "
                f"named state ownership, and reviewable proof for release {release}."
            ),
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
                "statement": (
                    f"{label} starts with one organization and one accountable workflow so the first release can "
                    "prove value before wider roles or integrations expand the scope."
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
                "question": f"Which person must complete the first {label_lower} workflow without assistance?",
                "impact": "Changes the visible flow, permission model, and validation target.",
                "default_if_unanswered": f"Use the {label_lower} workflow lead as the first operator.",
            },
            {
                "id": "OQ-002",
                "question": f"What source or external system must the first {label_lower} proof trust?",
                "impact": "Changes security, privacy, fixture, and integration expectations for the first release.",
                "default_if_unanswered": "Use deterministic local fixtures until a source-backed adapter is planned.",
            },
        ],
        "risks": [
            {
                "id": "RISK-001",
                "title": f"{label} workflow ambiguity",
                "statement": (
                    f"If the {label_lower} first workflow is not named tightly, implementation can sprawl into "
                    "unreviewed roles, states, and external dependencies."
                ),
                "severity": "high",
                "mitigation": "Keep release 0.0.1 limited to one complete workflow with explicit non-goals and proof gates.",
            },
            {
                "id": "RISK-002",
                "title": f"{label} evidence weakness",
                "statement": (
                    f"If {evidence_record.lower()} cannot reproduce the state decision, reviewers cannot trust "
                    "the release or safely promote the implementation."
                ),
                "severity": "high",
                "mitigation": "Require deterministic replay, audit identity, and source references for every release claim.",
            },
        ],
        "security_compliance": {
            "domain": (
                f"{label} carries domain risk around incorrect state, unreliable evidence, unsafe access, and "
                "operator decisions based on stale or incomplete data."
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
            f"The {label_lower} first workflow passes end to end with fixture-backed inputs and documented non-goals.",
            f"The {label_lower} state record can be reconstructed from accepted inputs and evidence references.",
            f"The {label_lower} release proof identifies owner, validation command, failure mode, and recovery expectation.",
        ],
        "project_brief": confirmed_project_brief(
            label=label,
            prompt=prompt_text,
            release=release,
            state_object=state_object,
            evidence_record=evidence_record,
        ),
        "project_intelligence": _project_intelligence(
            label=label,
            release=release,
            state_object=state_object,
            evidence_record=evidence_record,
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
            components=components,
            diagram_slugs=diagram_slugs,
        ),
        "components": components,
        "diagrams": confirmed_diagrams(label=label, components=components, diagram_slugs=diagram_slugs),
        "apply_commands": [
            "odylith greenfield create --repo-root . --prompt "
            + shell_quote(prompt_text)
            + " --confirm --release "
            + shell_quote(release),
            "# optional file workflow for review-only use: write `odylith greenfield propose --confirm-intent --format json` to a file, then pass that file to apply",
        ],
    }
    return proposal


def _project_intelligence(
    *,
    label: str,
    release: str,
    state_object: str,
    evidence_record: str,
) -> dict[str, Any]:
    label_lower = label.lower()
    state_lower = state_object.lower()
    evidence_lower = evidence_record.lower()
    rows = {
        "intent": [
            f"{label} gives a named operator one accountable workflow instead of a broad, unbounded product promise.",
            f"Release {release} proves the first {label_lower} path before wider automation, integrations, or scaling claims are allowed.",
            f"The product promise is useful only when the user can see what changed, why it changed, and what evidence supports the result.",
        ],
        "scope": [
            f"In scope: one first workflow, {state_lower} ownership, {evidence_lower} assembly, and a reviewer-visible release decision.",
            f"Out of scope: broad platform administration, live irreversible integrations, and production scaling until the first path holds.",
        ],
        "ontology": [
            f"{label} operator: the person who moves the first workflow from intake to completion.",
            f"{state_object}: the durable object that records the current state and version history for the workflow.",
            f"{evidence_record}: the proof packet that ties workflow result, validation output, replay result, and reviewer decision together.",
            f"{label} release gate: the decision point that blocks promotion when workflow, state, access, or evidence proof is missing.",
        ],
        "state": [
            f"{state_object} starts as requested, becomes in-progress when an accountable command is accepted, and becomes reviewable only after proof is assembled.",
            f"State changes stay versioned so the visible {label_lower} result can be replayed instead of explained from memory.",
        ],
        "operators": [
            f"Submit a {label_lower} workflow request with actor identity and required input.",
            f"Apply a state-changing command that updates {state_lower} and records validation expectations.",
            f"Assemble {evidence_lower} from the workflow result, state replay, validation output, and reviewer decision.",
        ],
        "constraints": [
            f"Do not treat {label_lower} proposal text as working behavior; release claims require validation output.",
            f"Do not let evidence review mutate {state_lower}; proof can approve or block, but state changes stay owned by the state path.",
        ],
        "source_of_truth_map": [
            f"{state_object} owns current workflow state, version history, and replay inputs.",
            f"{evidence_record} owns release readiness evidence, reviewer decision, and validation references.",
        ],
        "evidence": [
            f"The minimum evidence set is workflow input, state version, replay result, validation output, and reviewer decision.",
            f"Fixture-backed or sandbox evidence is acceptable for release {release}; live integrations need an explicit later contract.",
        ],
        "decisions": [
            f"Start with the smallest {label_lower} workflow that a real user can complete and review.",
            f"Delay broader platform behavior until the first state object and evidence packet survive validation.",
        ],
        "assumptions": [
            f"The first {label_lower} operator and beneficiary can be named before implementation starts.",
            f"External systems remain fixture-backed, sandboxed, or deferred unless the first workflow cannot be proven without them.",
        ],
        "topology": [
            f"The workflow service accepts commands and visible status for {label_lower}.",
            f"The state store persists {state_lower} and replay data; it does not own release approval.",
            f"The evidence review component assembles {evidence_lower} and blocks promotion when proof is incomplete.",
        ],
        "invariants": [
            f"Every {label_lower} state change names actor, command, timestamp, input reference, and expected validation.",
            f"Every release claim maps to {state_lower}, {evidence_lower}, a validation result, and an explicit non-goal boundary.",
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
            f"The workflow owner owns user steps, command validation, visible status, and recovery messaging.",
            f"The proof owner owns evidence packet completeness, reviewer decision, and release-readiness language.",
        ],
        "execution_memory": [
            f"Future {label_lower} work starts from the accepted first workflow, state object, and proof obligations.",
            f"Any source-backed contradiction invalidates the affected proposal assumption rather than being hidden as implementation detail.",
        ],
        "metrics": [
            f"The first workflow has zero unowned state transitions in release {release}.",
            f"Every release claim has a state reference, evidence reference, validation reference, and reviewer outcome.",
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
            f"Make {label_lower} readable as one product story with first workflow, owned state, evidence, "
            "risk, and release proof before source work starts."
        ),
        "coding_posture": (
            f"Coding starts only after the {label_lower} workflow, state owner, evidence owner, source paths, "
            "failure handling, and validation commands agree."
        ),
        "control_surface_summary": [
            f"{label} helps a named operator complete one accountable workflow instead of a vague platform promise.",
            f"{label} state ownership centers on {state_object.lower()} and its version history.",
            f"{label} evidence review centers on {evidence_record.lower()} and release proof.",
            f"{label} security covers authorization, private data, credential isolation, and abuse resistance.",
            f"{label} release {release} remains limited to the first workflow and explicit non-goals.",
        ],
        "customization_flow": [
            f"Confirm the {label_lower} user, problem, first workflow, and non-goals.",
            f"Confirm the {label_lower} state object, owner, and versioning expectation.",
            f"Confirm the {label_lower} evidence source, reviewer, and replay requirement.",
            f"Confirm release {release} promotion gates and deferred integrations.",
        ],
        **rows,
    }


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
            "child_workstream_strategy": f"Separate {label.lower()} workflow, state ownership, and release proof before implementation.",
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
                "goal": f"Prove the first {label.lower()} operator workflow from intake to visible completion.",
                "validation_gate": f"{label} success, validation failure, and recovery path tests pass.",
                "workstream_titles": [workflow_title],
                "component_focus": component_ids[:2],
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave": 2,
                "label": f"{label} state and evidence boundary",
                "goal": f"Make {label.lower()} state, proof packet, ownership, and review boundaries explicit.",
                "validation_gate": f"{label} state replay and evidence packet traceability tests pass.",
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
            f"{label} workflow proof passes with fixture-backed inputs.",
            f"{label} state replay matches the visible completion decision.",
            f"{label} evidence packet maps every release claim to validation output.",
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
    components: list[dict[str, Any]],
    diagram_slugs: Mapping[str, str],
) -> list[dict[str, Any]]:
    component_ids = [str(row["component_id"]) for row in components]
    parent = _backlog_row(
        label=label,
        title=f"Establish {label} Program",
        problem=f"{label} needs a clear product story, first workflow, state owner, evidence owner, and release proof before implementation begins.",
        customer=f"{label} operators, beneficiaries, and release reviewers",
        opportunity=f"Turn {label.lower()} from broad intent into a narrow first workflow that can be implemented and reviewed safely.",
        product_view=f"{label} should let one operator move a {state_object.lower()} through intake, state change, evidence review, and release decision.",
        first_slice=f"Start with the {label.lower()} first workflow, then replay {state_object.lower()} and review {evidence_record.lower()}.",
        metrics=[
            f"The {label.lower()} first workflow has named owner, state object, evidence packet, and non-goals.",
            f"Release proof links {label.lower()} workstreams, components, diagrams, and validation gates without claiming production maturity.",
        ],
        component_focus=component_ids,
        diagram_focus=list(diagram_slugs.values()),
        dependencies=[f"Depends on the confirmed {label.lower()} product story and release proof boundary."],
        interfaces=[f"Program handoff names the {label.lower()} workflow, state record, evidence packet, and review decision."],
        validation=[f"Review confirms the {label.lower()} workflow, state, proof, and release gates describe the same first path."],
        state_object=state_object,
        evidence_record=evidence_record,
        workstream_type="program_parent",
    )
    workflow = _backlog_row(
        label=label,
        title=workflow_title,
        problem=f"The first {label.lower()} operator path needs a named owner before source work can safely begin.",
        customer=f"{label} workflow lead and beneficiary",
        opportunity=f"Prove one {label.lower()} journey from intake to visible completion with explicit recovery behavior.",
        product_view=f"The workflow service owns {label.lower()} commands, status, errors, and operator-facing completion.",
        first_slice=f"{label} workflow lead submits one request and sees success, validation failure, and recovery status.",
        metrics=[
            f"{label} workflow success and validation-failure paths are both testable.",
            f"{label} workflow status cites the state record and evidence packet that support the visible result.",
        ],
        component_focus=component_ids[:2],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on {components[1]['label']} for durable state and {components[2]['label']} for proof review."],
        interfaces=[f"Submit workflow command, read {label.lower()} status, and expose structured validation failures."],
        validation=[f"End-to-end {label.lower()} workflow test covers success, failure, and recovery messaging."],
        state_object=state_object,
        evidence_record=evidence_record,
    )
    boundary = _backlog_row(
        label=label,
        title=boundary_title,
        problem=f"{label} cannot be trusted if state, evidence, ownership, and review boundaries are mixed together.",
        customer=f"{label} state owner and proof lead",
        opportunity=f"Separate {state_object.lower()} ownership from {evidence_record.lower()} review before implementation grows.",
        product_view=f"The state store owns durable {label.lower()} facts while evidence review owns release proof and reviewer decision.",
        first_slice=f"Create a replayable {state_object.lower()} and assemble {evidence_record.lower()} from the same workflow outcome.",
        metrics=[
            f"{label} state replay reproduces the visible workflow result.",
            f"{label} evidence review rejects proof packets that lack state, owner, reviewer, or validation references.",
        ],
        component_focus=component_ids,
        diagram_focus=[diagram_slugs["ownership"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on workflow outputs, authorized actor identity, state snapshots, and validation results."],
        interfaces=[f"State replay interface and evidence packet assembly interface stay separate and auditable."],
        validation=[f"{label} state replay and evidence packet traceability tests pass before release promotion."],
        state_object=state_object,
        evidence_record=evidence_record,
    )
    proof = _backlog_row(
        label=label,
        title=proof_title,
        problem=f"{label} release readiness needs proof that reviewers can inspect without relying on implementation claims.",
        customer=f"{label} release reviewer and product owner",
        opportunity=f"Make release readiness depend on validation evidence, replay output, access posture, and explicit non-goals.",
        product_view=f"Release review shows what {label.lower()} can do now, what remains deferred, and why the first workflow is safe to start.",
        first_slice=f"Export one {evidence_record.lower()} that maps workflow result, state replay, validation output, and reviewer decision.",
        metrics=[
            f"{label} release proof lists validation commands, failure modes, reviewer identity, and recovery expectation.",
            f"{label} release scope blocks broader integrations until the first workflow proof remains stable.",
        ],
        component_focus=[component_ids[-1]],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["ownership"]],
        dependencies=[f"Depends on workflow validation, state replay, access policy, and evidence review output."],
        interfaces=[f"Release proof export contains {label.lower()} validation summary, state references, and reviewer decision."],
        validation=[f"{label} release proof review fails closed when validation output or state replay is missing."],
        state_object=state_object,
        evidence_record=evidence_record,
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
        "rationale_lines": _rationale_lines(label=label, title=title, opportunity=opportunity, first_slice=first_slice),
        "domain_intelligence": _domain_intelligence(
            label=label,
            row_title=title,
            state_object=state_object,
            evidence_record=evidence_record,
        ),
    }


def _rationale_lines(*, label: str, title: str, opportunity: str, first_slice: str) -> list[str]:
    return [
        f"- why now: {opportunity}",
        f"- expected outcome: {first_slice}",
        f"- tradeoff: {title} keeps {label.lower()} focused on one releaseable path while delaying wider automation.",
        f"- deferred for now: broad integrations, production scaling, and irreversible actions wait until {label.lower()} proof is stable.",
        f"- ranking basis: {label} release readiness depends on this work carrying a clear owner, state object, and validation gate.",
    ]


def _domain_intelligence(
    *,
    label: str,
    row_title: str,
    state_object: str,
    evidence_record: str,
) -> dict[str, Any]:
    label_lower = label.lower()
    actors = [
        f"{label} beneficiary: represents the person or team receiving value from the first workflow.",
        f"{label} workflow lead: owns day-to-day movement through intake, state change, and completion.",
        f"{label} safety reviewer: owns privacy, security, access, abuse, and operational risk for the first release.",
        f"{label} proof lead: decides whether evidence is strong enough to trust the release claim.",
        f"{label} build lead: owns source paths, interfaces, validation commands, and implementation sequence.",
    ]
    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": slugify(label).replace("-", "_") or "confirmed_product",
        "summary": f"{row_title} keeps {label_lower} tied to one first workflow, owned state, evidence review, and release proof.",
        "actors": actors,
        "intent": [
            f"{row_title} advances {label_lower} by making the first workflow and its user value explicit.",
            f"{row_title} keeps {state_object.lower()}, {evidence_record.lower()}, and release proof connected.",
        ],
        "scope": [
            f"{row_title} owns only the named {label_lower} slice and does not expand into unrelated platform behavior.",
            f"The boundary stays proposal-level until source paths, tests, and reviewer evidence exist.",
        ],
        "ontology": [
            f"{label} operator: person who moves the first workflow from intake to completion.",
            f"{label} state object: {state_object} that changes through the first workflow.",
            f"{label} evidence record: {evidence_record} that supports the release claim.",
            f"{label} release gate: validation result that blocks promotion when proof is missing.",
        ],
        "state": [
            f"{state_object} begins unreviewed, moves through workflow update, and becomes reviewable only with evidence.",
            f"{label} completion state is not trusted until replay and proof review agree.",
        ],
        "operators": [
            f"Intake {label.lower()} request with an accountable workflow lead.",
            f"Change {state_object.lower()} through a named workflow command and audit identity.",
            f"Assemble {evidence_record.lower()} from validation output, state replay, and reviewer decision.",
        ],
        "constraints": [
            f"Do not claim {label.lower()} production readiness from proposal prose or untested happy paths.",
            f"Do not let {label.lower()} evidence mutate state directly or bypass owner review.",
        ],
        "source_of_truth_map": [
            f"{state_object} is the source of truth for current {label.lower()} workflow state.",
            f"{evidence_record} is the source of truth for release readiness and reviewer confidence.",
        ],
        "evidence_model": [
            f"{label} proof lead: accepts evidence only when state replay and validation output match.",
            f"{evidence_record} includes input reference, state reference, validation result, and reviewer decision.",
        ],
        "decisions": [
            f"The first decision is whether {label.lower()} should start with this workflow and state object.",
            f"The next decision is whether release proof is strong enough to allow implementation planning.",
        ],
        "assumptions": [
            f"{label} starts with fixture-backed or sandboxed sources until live dependencies are intentionally introduced.",
            f"{label} external integrations stay deferred unless the first workflow cannot be proven without them.",
        ],
        "topology": [
            f"{label} workflow service changes state, state store persists facts, and evidence review evaluates release proof.",
            f"{row_title} links user value, component ownership, architecture views, validation, and release decision.",
        ],
        "invariants": [
            f"Every {label.lower()} state change must name actor, command, timestamp, and validation expectation.",
            f"Every {label.lower()} release claim must map to evidence, replay output, reviewer, and non-goal statement.",
        ],
        "risks": [
            f"{label} risk increases when broad integrations hide the first workflow or its failure mode.",
            f"{label} safety and privacy risk increase when access or reviewer identity is not explicit.",
        ],
        "validation_obligations": [
            f"Validate {label.lower()} workflow success and validation-failure paths.",
            f"Validate {label.lower()} state replay from accepted inputs and change history.",
            f"Validate {label.lower()} proof packet maps every release claim to evidence.",
        ],
        "artifacts": [
            f"{state_object} records workflow state, owner, status, and audit reference.",
            f"{evidence_record} records validation output, replay output, reviewer decision, and release scope.",
        ],
        "authority": [
            f"{label} workflow lead can submit and correct first-workflow inputs.",
            f"{label} proof lead can block release when validation, replay, or access evidence is incomplete.",
        ],
        "owners": [
            f"{label} workflow owner owns operator steps, visible status, and recovery messaging.",
            f"{label} evidence owner owns proof packet content, review decision, and release-readiness language.",
        ],
        "execution_memory": [
            f"Future {label.lower()} work must start from the accepted first workflow and state object.",
            f"Past {label.lower()} assumptions are invalidated when source proof or product owner correction disagrees.",
        ],
        "metrics": [
            f"{label} workflow has zero unowned state transitions in the first release.",
            f"{label} release claim has evidence, replay, reviewer, and validation references.",
        ],
        "change_model": [
            f"Changing the {label.lower()} state object invalidates workflow, proof, and release-readiness assumptions.",
            f"Changing external dependencies invalidates {label.lower()} security, privacy, access, and failure proof.",
        ],
        "invalidation_rules": [
            f"If {label.lower()} validation proof is missing, release readiness stays blocked.",
            f"If {label.lower()} source behavior contradicts proposal assumptions, the affected records must be corrected.",
        ],
        "conflict_model": [
            f"Product owner corrections beat stale {label.lower()} proposal assumptions.",
            f"Source-backed validation beats {label.lower()} narrative claims when they disagree.",
        ],
        "transfer_priors": [
            f"Keep {label.lower()} release scope small enough for concrete behavior proof.",
            f"Prefer explicit {label.lower()} state, owner, evidence, and failure terms over generic implementation labels.",
        ],
    }



__all__ = ["build_confirmed_greenfield_proposal"]
