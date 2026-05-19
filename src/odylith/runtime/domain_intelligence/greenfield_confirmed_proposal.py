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
    )
    workflow_title, boundary_title, proof_title = _workstream_titles(
        label=label,
        components=components,
        internal_systems=internal_systems,
    )
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
                "program": f"Establish {label} Program",
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
    actors = _short_summary(customer, limit=220) or _join_items(human_actors) or f"the first {label_lower} operator and reviewer"
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
    labels = [str(row.get("label", "")).strip() for row in components if str(row.get("label", "")).strip()]
    if len(labels) >= 3 and internal_systems:
        return (
            f"Prove {labels[0]}",
            f"Define {labels[1]} Boundary",
            f"Prepare {labels[2]} Release Proof",
        )
    return (
        f"Prove {label} First Path",
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


def _compact_text(value: str) -> str:
    text = str(value or "").strip()
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return " ".join(text.split())


def _domain_object_label(value: str, *, fallback: str) -> str:
    text = _compact_text(value)
    if not text:
        return fallback
    first_clause = re.split(r"[.;\n]", text, maxsplit=1)[0].strip(" :.-")
    dash_head = re.split(r"\s+[—-]\s+", first_clause, maxsplit=1)[0].strip(" :.-")
    patterns = (
        r"\b(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?(?:domain\s+)?object\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
        r"\b(?:the\s+)?proof\s+record\s+is\s+(?:the\s+)?(?P<label>[^.;:]+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, dash_head, flags=re.IGNORECASE)
        if match:
            candidate = match.group("label").strip(" :.-")
            return _title_label(candidate) or fallback
    if dash_head and not re.search(r"\b(is|are|starts?|moves?|changes?|tracks?|records?|captures?|produces?)\b", dash_head, re.IGNORECASE):
        return _title_label(dash_head) or fallback
    words = text.split()
    if len(words) <= 7:
        return _title_label(text) or fallback
    return fallback


def _short_summary(value: str, *, limit: int = 280) -> str:
    text = _compact_text(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:state object|first path|proof boundary|product story)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^the first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^first complete path to prove should be\s*:?\s+", "", text, flags=re.IGNORECASE)
    if len(text) <= limit:
        return text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected: list[str] = []
    total = ""
    for sentence in sentences:
        candidate = " ".join([*selected, sentence]).strip()
        if len(candidate) > limit and selected:
            break
        selected.append(sentence)
        total = candidate
        if len(total) >= limit * 0.55:
            break
    if total:
        return total.strip(" .")
    clipped = text[: max(0, limit - 1)].rstrip(" ,;:")
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0].rstrip(" ,;:")
    return clipped + "…"


def _problem_text(*, label: str, problem: str, product_story: str, first_path: str) -> str:
    explicit = _short_summary(problem, limit=360)
    if explicit:
        return explicit
    story = _short_summary(product_story, limit=240)
    path = _short_summary(first_path, limit=180)
    if story and path:
        return f"Without a clear first path, users cannot trust whether {label.lower()} solves the accepted problem: {story} The proof path is {path}."
    if story:
        return f"Without source-backed proof, users cannot trust whether {label.lower()} solves the accepted problem: {story}."
    return f"Without an explicit problem, first path, and proof boundary, {label.lower()} cannot be trusted as implementation-ready."


def _state_detail_summary(value: str, *, state_label: str, limit: int = 280) -> str:
    summary = _short_summary(value, limit=limit)
    if not summary:
        return ""
    label_pattern = re.escape(state_label).replace(r"\ ", r"\s+")
    summary = re.sub(
        rf"^(?:the\s+)?(?:primary\s+)?state\s+object\s+is\s+(?:the\s+)?{label_pattern}\.?\s*",
        "",
        summary,
        flags=re.IGNORECASE,
    ).strip(" .")
    if summary.casefold() == state_label.casefold():
        return ""
    return summary


def _join_system_labels(items: list[str] | None, *, limit: int = 4) -> str:
    values: list[str] = []
    for item in items or []:
        text = _compact_text(item)
        if not text:
            continue
        values.append(_domain_object_label(text, fallback=text.split("—", 1)[0].split(":", 1)[0].strip()))
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return ", ".join(selected) + suffix


def _title_label(value: str) -> str:
    words = []
    for index, word in enumerate(_compact_text(value).strip(" .").split()):
        lower = word.casefold()
        if index == 0 and lower in {"a", "an", "the"}:
            continue
        if lower in {"and", "or", "of", "the", "to", "for", "in", "on", "with"} and words:
            words.append(lower)
            continue
        if lower in {"ai", "api", "crm", "gis", "iot", "llm", "ml", "pwa", "ui", "ux"}:
            words.append(lower.upper())
            continue
        words.append(word[:1].upper() + word[1:])
    return " ".join(words).strip()


def _join_items(items: list[str] | None, *, limit: int = 4) -> str:
    values = [str(item).strip().rstrip(".") for item in (items or []) if str(item).strip()]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return "; ".join(selected) + suffix


def _join_brief_items(items: list[str] | None, *, limit: int = 3, item_limit: int = 120) -> str:
    values = [
        re.sub(r"\s+[-*]\s+", " ", _short_summary(str(item), limit=item_limit)).strip(" ;")
        for item in (items or [])
        if str(item).strip()
    ]
    values = [value for value in values if value]
    if not values:
        return ""
    selected = values[:limit]
    suffix = "" if len(values) <= limit else f", plus {len(values) - limit} more"
    return ", ".join(selected) + suffix


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
        "recommended_first_wave": f"{label} first-path proof",
        "blueprint": {
            "program_type": "greenfield_program",
            "parent_workstream": f"Establish {label} Program",
            "child_workstream_strategy": f"Separate the accepted first path, {label.lower()} state ownership, and release proof before implementation.",
            "child_workstreams": [workflow_title, boundary_title, proof_title],
            "wave_to_workstream_policy": "Waves describe delivery order while child workstreams carry owned product slices.",
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
    problem: str = "",
    customer: str = "",
    opportunity: str = "",
    product_view: str = "",
    success_metrics: list[str] | None = None,
) -> list[dict[str, Any]]:
    component_ids = [str(row["component_id"]) for row in components]
    state_label = _domain_object_label(state_object, fallback=f"{label} state")
    evidence_label = _domain_object_label(evidence_record, fallback=evidence_record)
    story_summary = _short_summary(product_story, limit=420)
    problem_summary = _problem_text(label=label, problem=problem, product_story=product_story, first_path=first_path)
    opportunity_summary = _short_summary(opportunity, limit=360)
    product_view_summary = _short_summary(product_view, limit=360)
    first_path_summary = _short_summary(first_path, limit=380)
    proof_summary = _short_summary(proof_boundary, limit=340)
    actors = _short_summary(customer, limit=260) or _join_items(human_actors) or f"{label} users and reviewers"
    non_goal_text = _join_items(non_goals) or "broader automation, live integrations, and production-scale decisions"
    primary_component = str(components[0]["label"]) if components else f"{label} first component"
    proof_component = str(components[-1]["label"]) if components else f"{label} proof component"
    second_component = str(components[1]["label"]) if len(components) > 1 else primary_component
    parent = _backlog_row(
        label=label,
        title=f"Establish {label} Program",
        problem=problem_summary,
        customer=actors,
        opportunity=opportunity_summary
        or "Turn the accepted product story into a reviewed first-release boundary before source work starts.",
        product_view=product_view_summary
        or f"The first release is trustworthy only when the accepted path, {state_label}, and {evidence_label} can be reviewed together.",
        first_slice=first_path_summary,
        metrics=[
            *(success_metrics or [])[:2],
            "Release records preserve the accepted product story before implementation planning.",
            f"Release proof stays inside the accepted boundary for {evidence_label}.",
        ],
        component_focus=component_ids,
        diagram_focus=list(diagram_slugs.values()),
        dependencies=[
            "Depends on the confirmed actors, product-owned responsibilities, and proof boundary from the accepted intent."
        ],
        interfaces=[f"Program handoff names the first path, state object, proof boundary, non-goals, and internal systems."],
        validation=["Review confirms the story, first path, state object, component ownership, and proof boundary agree."],
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
        problem=f"Without the accepted first path in source-backed behavior, {actors} cannot trust that the product solves the confirmed problem: {problem_summary}",
        customer=actors,
        opportunity=opportunity_summary or "Prove the smallest usable product journey in source-backed behavior.",
        product_view=f"The first implementation plan should explain how {primary_component} works with {second_component} to complete the accepted path.",
        first_slice=first_path_summary,
        metrics=[
            "A user can complete the accepted first path and see a clear result.",
            f"At least one domain failure is rejected or recovered with evidence tied to {state_label}.",
        ],
        component_focus=component_ids[: max(1, min(2, len(component_ids)))],
        diagram_focus=[diagram_slugs["context"], diagram_slugs["sequence"], diagram_slugs["state_evidence"]],
        dependencies=[f"Depends on {second_component} where the first path needs durable state or supporting evidence."],
        interfaces=["Expose only the operations needed to run the accepted first path; keep deferred scope out of the first slice."],
        validation=[f"End-to-end proof covers the first path, at least one domain failure, and reviewer-visible recovery."],
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
        problem=f"{label} cannot be trusted if state, evidence, ownership, and review boundaries drift away from the confirmed problem: {problem_summary}",
        customer=actors,
        opportunity=(
            "Clarify what the product owns, what it consumes, and what stays outside the first release "
            "before implementation starts."
        ),
        product_view=f"{state_label} is the state boundary; {evidence_label} is the review boundary.",
        first_slice=f"Map how {state_label} changes through the first path and how {evidence_label} proves or blocks release readiness.",
        metrics=[
            f"Every state change names actor, source, owner, and evidence expectation.",
            f"Every owned system remains tied to the domain responsibility accepted in the product direction.",
        ],
        component_focus=component_ids,
        diagram_focus=[
            diagram_slugs["state_evidence"],
            diagram_slugs["component_boundaries"],
            diagram_slugs["ownership"],
        ],
        dependencies=["Depends on the confirmed internal systems and external boundaries from the accepted intent."],
        interfaces=[f"State, evidence, review, and external-source interfaces stay separate and traceable."],
        validation=[f"Boundary proof rejects records that cannot explain {state_label}, {evidence_label}, or {proof_summary}."],
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
        problem=f"Release readiness needs evidence a reviewer can inspect without trusting implementation claims; otherwise {actors} cannot verify the accepted result.",
        customer=actors,
        opportunity="Make release readiness depend on inspectable proof, not planning prose.",
        product_view=f"{proof_component} produces or participates in the evidence a reviewer needs before release work can proceed.",
        first_slice=f"Produce one reviewable proof record that maps the first path, {state_label}, validation output, and reviewer decision.",
        metrics=[
            f"Release proof lists the domain evidence required by the accepted product direction.",
            f"Release proof explicitly excludes non-goals until accepted later: {non_goal_text}.",
        ],
        component_focus=[component_ids[-1]] if component_ids else [],
        diagram_focus=[diagram_slugs["ownership"], diagram_slugs["proof_review"], diagram_slugs["sequence"]],
        dependencies=[f"Depends on first-path validation, state replay, access posture, and evidence review output."],
        interfaces=[f"Release proof export contains validation summary, state references, evidence references, reviewer decision, and deferred scope."],
        validation=[f"Release proof fails closed when any part of the accepted proof boundary is missing: {proof_summary}"],
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
        "- tradeoff: Keep the first release focused on the accepted path while deferring unconfirmed scope.",
        "- deferred for now: Scope outside the accepted proof boundary waits for explicit evidence.",
        "- ranking basis: Release readiness depends on the product story, domain state, evidence, and proof boundary staying aligned.",
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
    actors = human_actors or [f"{label} product user: uses the accepted first path."]
    internals = internal_systems or [f"{state_object}: owns domain state.", f"{evidence_record}: owns proof review."]
    internal_labels = _join_system_labels(internals) or _join_items(internals)
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
            f"First-path actors perform the accepted product path: {_join_items(actors)}.",
            f"Internal systems own product behavior: {internal_labels}.",
            f"External systems remain separate from product-owned truth: {_join_items(externals)}.",
        ],
        "constraints": [
            f"Do not derive product records from a thin prompt when confirmed product systems are required.",
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
            f"Decide whether each internal system has a clear responsibility: {internal_labels}.",
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
            f"Every state change must name actor, source, timestamp, and evidence expectation.",
            f"Every readiness assertion must map to {state_object}, {evidence_record}, validation output, reviewer decision, and non-goal boundary.",
        ],
        "risks": [
            f"Product comprehension fails if release records lose the confirmed domain terms, actors, state, and evidence.",
            f"Release confidence fails if evidence cannot explain the accepted proof boundary.",
        ],
        "validation_obligations": [
            f"Validate the accepted first path in domain terms.",
            f"Validate state replay for {state_object}.",
            f"Validate proof traceability for {evidence_record} against: {proof_boundary}",
        ],
        "artifacts": [
            f"{state_object} history captures actor, source, status, timestamp, and version history.",
            f"{evidence_record} captures validation output, replay output, reviewer decision, and release scope.",
        ],
        "authority": [
            f"Only accepted actors or systems can move first-path state: {_join_items(actors)}.",
            f"Proof review can block release when validation, replay, access, or evidence is incomplete.",
        ],
        "owners": [
            f"Internal product systems own release responsibilities: {internal_labels}.",
            f"Review ownership follows the accepted proof boundary, not generic implementation labels.",
        ],
        "execution_memory": [
            f"Future work starts from the accepted first path and state object.",
            f"Product-owner correction or source-backed contradiction invalidates stale assumptions.",
        ],
        "metrics": [
            f"Zero release records are written without confirmed product systems.",
            f"Every readiness assertion has state, evidence, validation, reviewer, and non-goal references.",
        ],
        "change_model": [
            f"Changing the state object invalidates first-path, proof, and release-readiness assumptions.",
            f"Changing external dependencies invalidates security, privacy, access, and failure proof.",
        ],
        "invalidation_rules": [
            f"If confirmed narrative is missing, no records may be written.",
            f"If release records cannot explain the accepted first path, release readiness stays blocked.",
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


def _project_specific_actor_row(row: str, *, focus: str) -> str:
    for prefix in _GENERIC_ACTOR_PREFIXES:
        match = re.match(rf"^{re.escape(prefix)}(?P<tail>(?:\s|:|[-–—/]|$).*)", row)
        if not match:
            continue
        replacement = f"{focus} {prefix.casefold()}"
        return f"{replacement}{match.group('tail')}".strip()
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



__all__ = ["build_confirmed_greenfield_proposal"]
