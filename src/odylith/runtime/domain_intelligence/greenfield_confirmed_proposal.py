"""Governed greenfield proposal construction after intent confirmation."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_confirmed_components import (
    confirmed_components,
    confirmed_project_brief,
    domain_label,
    shell_quote,
    system_component_name,
)
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
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import health_safety_obligations
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import material_first_path_action
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_semantic_model import build_greenfield_semantic_model
from odylith.runtime.domain_intelligence.greenfield_semantic_model import semantic_model_mapping
from odylith.runtime.domain_intelligence.greenfield_product_risks import build_product_risks
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import (
    build_workstream_domain_intelligence,
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
    evidence_record = _evidence_record_label(label=label, proof_boundary=proof_boundary, internal_systems=internal_systems)
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
    workflow_title, boundary_title, proof_title = _workstream_titles(
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
    backlog_rows = _backlog(
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
        "program": _program(
            label=label,
            parent_title=parent_title,
            release=release,
            workflow_title=workflow_title,
            boundary_title=boundary_title,
            proof_title=proof_title,
            components=release_components,
        ),
        "release_plan": _release_plan(
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
            f"Compliance posture for {label_lower} keeps privacy, audit retention, accessibility, safety, "
            f"and operational review visible before production claims are made. Release proof: {_proof_claim_summary(proof_boundary, limit=220)}."
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
    proof_summary = _proof_claim_summary(proof_boundary, limit=320)
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
            f"The release proof is: {proof_summary}",
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
            f"Promotion is blocked when the promised result is incomplete or unexplained: {proof_summary}",
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
            f"Confirm the {label_lower} evidence source, release-review actor, and replay requirement.",
            f"Confirm release {release} promotion gates and deferred integrations.",
        ],
        **rows,
    }


def _workstream_titles(
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
    if action:
        action_actor, action_tail = _actor_action_parts(action)
        workflow_actor = action_actor or actor or "user"
        workflow_action = _base_leading_action(action_tail or _strip_actor_prefix(action, workflow_actor) or action)
        workflow = f"Let {workflow_actor} {workflow_action}"
    elif labels:
        workflow = f"Make {labels[0]} usable in the first path"
    else:
        workflow = f"Make {label} usable in the first path"
    boundary_subject = labels[1] if len(labels) > 1 else state_label
    boundary = f"Keep {state_label} clear after {boundary_subject} changes it"
    proof_subject = state_label or _proof_title_object(proof_boundary) or proof_label
    proof = f"Show why {proof_subject} can be trusted"
    return (
        _title_label(workflow) or workflow,
        _title_label(boundary) or boundary,
        _title_label(proof) or proof,
    )


def _parent_workstream_title(*, label: str, first_path: str) -> str:
    return (
        _title_label(f"Make {label} useful for one complete outcome")
        or f"Make {label} useful for one complete outcome"
    )


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


def _imperative_action_phrase(first_path: str) -> str:
    action = material_first_path_action(first_path, fallback=_first_action_clause(first_path))
    text = _sentence_fragment(action).strip(" .")
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


def _evidence_record_label(*, label: str, proof_boundary: str, internal_systems: list[str]) -> str:
    for system in internal_systems:
        first = str(system).split("—", 1)[0].split("-", 1)[0].split(":", 1)[0].strip()
        name = first.casefold()
        if any(token in name for token in ("evidence", "audit", "proof", "ledger", "history", "trace")):
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
            f"{label} state replay matches the release-review outcome decision.",
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


def _first_path_capability(value: str) -> str:
    return _sentence_fragment(
        first_path_capability_phrase(
            value,
            fallback=_first_action_clause(value) or "the accepted first path",
        )
    )


def _proof_claim_summary(value: str, *, limit: int = 260) -> str:
    text = _short_summary(value, limit=limit).strip(" .")
    text = re.sub(r"^(?:the\s+)?first\s+version\s+is\s+proven\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:release\s+[0-9.]+\s+)?(?:is\s+)?proven\s+when\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?proof\s+boundary\s+(?:is|means)\s*:?\s*", "", text, flags=re.IGNORECASE)
    return text or _short_summary(value, limit=limit).strip(" .")


def _first_path_outcome(value: str, *, proof_boundary: str = "") -> str:
    model = first_path_model(value)
    candidates = (
        model.visible_outcome,
        _proof_claim_summary(proof_boundary, limit=240),
        _short_summary(value, limit=240),
    )
    for candidate in candidates:
        text = _sentence_fragment(candidate)
        text = re.sub(r"^on\s+save,\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+is\s+the\s+visible\s+result\b.*$", "", text, flags=re.IGNORECASE).strip(" .")
        text = re.sub(
            r"^(?:the\s+)?(?:user|owner|person|participant|actor|operator|applicant|customer)\s+"
            r"(?:sees?|views?|receives?|reads?|gets?)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip(" .")
        text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
        text = re.sub(r"\bon\s+screen,\s+alongside\b", "on screen with", text, flags=re.IGNORECASE)
        text = re.sub(r"\balongside\b", "with", text, flags=re.IGNORECASE)
        if text:
            return text
    return "the promised user-visible result"


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
    text = _sentence_fragment(value)
    text = re.sub(
        r"^(?:a|an|the)\s+(?:user|owner|person|actor|customer|applicant|participant|operator)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    for inflected, base in {
        "adds": "add",
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
    text = re.sub(r",\s+and\s+(manually\s+)?(log|enter|select|submit|save|choose|click|accept|dismiss|record|capture|review)\b", r" and \1\2", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip(" .") or "complete the accepted path"


def _sentence_fragment(value: str) -> str:
    text = _short_summary(value, limit=260).strip(" .")
    if not text:
        return ""
    if re.match(r"^[A-Z]{2,}\b", text):
        return text
    return text[:1].casefold() + text[1:]


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
    first_path_entry = material_first_path_action(first_path_summary, fallback=_first_action_clause(first_path_summary))
    proof_summary = _proof_claim_summary(proof_boundary, limit=340)
    evidence_phrase = "quality evidence" if "quality evidence" in first_path_summary.casefold() else f"{state_label} review context"
    actors = _join_actor_labels(human_actors) or _short_summary(customer, limit=260) or f"{label} users and reviewers"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    primary_component = _workstream_subject(_component_label_at(components, 0, fallback=f"{label} first path"))
    second_component = _workstream_subject(_component_label_at(components, 1, fallback=primary_component))
    proof_component = _workstream_subject(
        _component_label_at(components, len(components) - 1, fallback=f"{label} proof review")
    )
    proof_record_label = _title_label(f"{proof_component} proof record") or evidence_label
    first_path_entry_text = _sentence_fragment(first_path_entry)
    first_path_capability = _sentence_fragment(_first_path_capability(first_path_summary))
    first_path_full_capability = _sentence_fragment(
        first_path_capability_phrase(
            first_path_summary,
            fallback=first_path_capability or first_path_entry_text or "complete the accepted product path",
            limit=340,
            max_fragments=7,
        )
    )
    outcome_summary = _first_path_outcome(first_path_summary, proof_boundary=proof_boundary)
    first_path_action = _capability_action_clause(first_path_entry_text or first_path_capability)
    path_story = _sentence_fragment(first_path_summary or first_path_capability or first_path_entry_text)
    path_entry_story = _sentence_fragment(first_path_entry_text or first_path_capability or first_path_summary)
    metric_actor = _problem_actor_subject(actors, fallback=f"{label} user")
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
            f"Depends on the accepted actors, external sources, and product systems needed for {path_story}."
        ],
        interfaces=[
            f"Release scope connects {primary_component}, {second_component}, and {proof_component} without absorbing deferred scope."
        ],
        validation=[
            f"Run the complete user path, the missing-input path, and the corrected-input path against the promised result: {proof_summary}."
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
        problem=f"{primary_component} is where trust can be lost first: when someone tries to {first_path_action}, the product must leave clear feedback, a changed {state_label}, and a visible way to recover from missing or invalid input.",
        customer=actors,
        opportunity=(
            f"Make the opening interaction small enough to prove, but complete enough that the next participant is not guessing what happened."
        ),
        product_view=(
            f"A user can {first_path_action}. The product responds with clear feedback, records the state it changed, "
            f"and makes {state_label} available to {second_component} without hiding blocked or corrected input. "
            f"The next step can review {evidence_phrase} without replaying the whole workflow by hand."
        ),
        first_slice=(
            f"Start with one representative path: {path_story}. Include the success case, one missing-input case, "
            f"one correction, and the context {second_component} needs."
        ),
        metrics=[
            f"The opening action creates or updates {state_label} in a way a user can understand.",
            f"Missing or invalid input stops the product before it shows a misleading result.",
            f"{second_component} receives enough context to continue without reinterpreting the user's input.",
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
            f"Questionable input is accepted, quarantined, or rejected before it changes the result.",
            f"Downstream consumers can distinguish success, blocked, stale, and review-needed states without reading implementation details.",
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
            f"Turn the completed path into a reviewable release claim that connects validation results, state references, the release decision, and deferred scope."
        ),
        product_view=(
            f"{proof_component} explains why the outcome can be trusted. It shows whether {state_label}, validation output, required context, "
            f"and deferred scope support the promised result: {proof_summary}."
        ),
        first_slice=(
            f"Produce one {proof_record_label} that links the first path, {state_label}, validation result, release decision, and deferred scope."
        ),
        metrics=[
            f"{proof_record_label} links accepted input, {state_label}, validation output, release decision, and outcome.",
            f"Missing evidence blocks proof review instead of producing a release-ready claim.",
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
    proof = _proof_claim_summary(proof_boundary, limit=180).strip(" .")
    if _looks_mechanical_summary(why_now):
        why_now = f"{title} proves a bounded part of the accepted {label} first path before adjacent scope expands"
    if _looks_mechanical_summary(expected_outcome):
        expected_outcome = f"{title} produces reviewable state, blocker behavior, recovery evidence, and handoff proof"
    if not why_now:
        why_now = "Clarify the accepted product boundary before implementation starts"
    if not expected_outcome:
        expected_outcome = "Produce the first reviewable release outcome"
    if not proof:
        proof = f"{title} can be reviewed against the accepted {label} release boundary"
    return [
        f"- why now: {why_now}.",
        f"- expected outcome: {expected_outcome}.",
        f"- tradeoff: This stays narrow so the team can prove {proof} before it widens the product promise.",
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
        or re.search(r"\bneed\s+[A-Z]?[A-Za-z0-9][^.;]{0,120}\s+to\s+turn\b", text)
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


__all__ = ["build_confirmed_greenfield_proposal"]
