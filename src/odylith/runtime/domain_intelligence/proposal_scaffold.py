"""Deterministic apply-ready greenfield proposal scaffolding."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile
from odylith.runtime.domain_intelligence.greenfield_domain_profile import infer_greenfield_domain_profile
from odylith.runtime.domain_intelligence.greenfield_project_brief import build_project_brief
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import build_project_intelligence
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import enrich_backlog_rows
from odylith.runtime.domain_intelligence.proposal_rendering import build_apply_commands
from odylith.runtime.domain_intelligence.robot_swarm_profile import apply_robot_swarm_logistics_profile
from odylith.runtime.domain_intelligence.robot_swarm_profile import is_robot_swarm_logistics_prompt


def build_apply_ready_proposal(
    *,
    prompt: str,
    intent_title: str,
    project_slug: str,
    observed_source: Mapping[str, Any],
    release_selector: str = "",
) -> dict[str, Any]:
    """Build a conservative proposal object that can pass apply gates."""

    selector = str(release_selector or "").strip() or greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR
    title = str(intent_title or "").strip() or "Greenfield Project"
    slug = slugify(str(project_slug or "").strip() or title) or "greenfield-project"
    robot_swarm_logistics = is_robot_swarm_logistics_prompt(prompt)
    domain_profile = infer_greenfield_domain_profile(prompt=prompt, title=title, slug=slug)
    components = _component_ids(slug=slug, domain_profile=domain_profile, robot_swarm_logistics=robot_swarm_logistics)
    diagrams = _diagram_ids(slug=slug)
    intent = _intent(prompt=prompt, title=title, slug=slug, robot_swarm_logistics=robot_swarm_logistics)
    assumptions = _base_assumptions()
    open_questions = _base_open_questions()
    risks = _base_risks(title=title, domain_profile=domain_profile)
    security_compliance = _base_security_compliance(title, domain_profile=domain_profile)
    validation_strategy = _base_validation_strategy()
    project_brief = build_project_brief(
        prompt=prompt,
        title=title,
        slug=slug,
        domain_profile=domain_profile,
        release_selector=selector,
    )
    program = _program(title=title, components=components)
    release_plan = _release_plan(
        selector=selector,
        slug=slug,
        experience_component=components["experience"],
        domain_component=components["domain"],
    )
    component_rows = _components(components, diagrams=diagrams, domain_profile=domain_profile)
    diagram_rows = _diagrams(title=title, components=components, diagrams=diagrams)
    project_intelligence = build_project_intelligence(
        prompt=prompt,
        title=title,
        slug=slug,
        release_selector=selector,
        domain_profile=domain_profile,
        project_brief=project_brief,
        program=program,
        release_plan=release_plan,
        components=component_rows,
        diagrams=diagram_rows,
        observed_source=observed_source,
    )
    backlog_rows = enrich_backlog_rows(
        _backlog(
            title=title,
            selector=selector,
            components=components,
            diagrams=diagrams,
        ),
        intent=intent,
        program=program,
        release_plan=release_plan,
        validation_strategy=validation_strategy,
        security_compliance=security_compliance,
        components=component_rows,
        diagrams=diagram_rows,
        domain_profile=domain_profile,
    )
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.host_reasoned.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "proposal_first_confirm_before_apply",
        "intent": intent,
        "observed_source": dict(observed_source),
        "assumptions": assumptions,
        "open_questions": open_questions,
        "risks": risks,
        "security_compliance": security_compliance,
        "validation_strategy": validation_strategy,
        "project_brief": project_brief,
        "project_intelligence": project_intelligence,
        "program": program,
        "release_plan": release_plan,
        "backlog": backlog_rows,
        "components": component_rows,
        "diagrams": diagram_rows,
    }
    if robot_swarm_logistics:
        apply_robot_swarm_logistics_profile(
            proposal,
            title=title,
            selector=selector,
            experience_component=components["experience"],
            domain_component=components["domain"],
            validation_component=components["validation"],
            diagram_slugs=diagrams,
        )
    proposal["apply_commands"] = build_apply_commands(proposal)
    return proposal


def _component_ids(
    *,
    slug: str,
    domain_profile: GreenfieldDomainProfile,
    robot_swarm_logistics: bool,
) -> dict[str, str]:
    suffixes = (
        ("fleet-console", "coordination-core", "simulation-harness")
        if robot_swarm_logistics
        else (
            domain_profile.components["experience"].suffix,
            domain_profile.components["domain"].suffix,
            domain_profile.components["validation"].suffix,
        )
    )
    return {
        "experience": f"{slug}-{suffixes[0]}",
        "domain": f"{slug}-{suffixes[1]}",
        "validation": f"{slug}-{suffixes[2]}",
    }


def _diagram_ids(*, slug: str) -> dict[str, str]:
    return {
        "overview": f"{slug}-system-overview",
        "slice": f"{slug}-first-slice-flow",
        "component_map": f"{slug}-component-ownership-map",
        "domain_state": f"{slug}-domain-state-model",
        "validation_release": f"{slug}-validation-release-topology",
    }


def _intent(*, prompt: str, title: str, slug: str, robot_swarm_logistics: bool) -> dict[str, Any]:
    summary = (
        "Govern a simulation-first robot swarm logistics platform with operator dispatch, fleet telemetry, "
        "coordination contracts, and safety proof before hardware or production claims."
        if robot_swarm_logistics
        else f"Turn `{prompt}` into a governed greenfield program before source-backed implementation starts."
    )
    return {
        "prompt": prompt,
        "title": title,
        "project_slug": slug,
        "summary": summary,
        "reasoning_mode": "odylith_apply_ready_scaffold",
        "evidence_tier": "user_intent",
    }


def _base_assumptions() -> list[dict[str, str]]:
    return [
        {
            "id": "A1",
            "evidence_tier": "odylith_assumption",
            "statement": "The first release should prove a narrow operator-visible workflow before broad source architecture is claimed.",
        },
        {
            "id": "A2",
            "evidence_tier": "odylith_assumption",
            "statement": "Implementation starts with repository-native tests and one Odylith-governed technical plan per child workstream.",
        },
    ]


def _base_open_questions() -> list[dict[str, str]]:
    return [
        {
            "id": "Q1",
            "evidence_tier": "user_intent",
            "question": "Which runtime, deployment target, and user role should constrain the first implementation slice?",
        },
        {
            "id": "Q2",
            "evidence_tier": "user_intent",
            "question": "Which data, safety, privacy, or compliance constraints materially change the first release gate?",
        },
    ]


def _base_risks(*, title: str, domain_profile: GreenfieldDomainProfile) -> list[dict[str, str]]:
    if domain_profile.family == "defi_risk":
        return [
            {
                "id": "R1",
                "risk_class": "data_integrity",
                "severity": "high",
                "trigger": "watchlist, risk-signal, scenario-replay, release-gate, or no-live-chain boundaries diverge",
                "early_warning": "risk cards show numeric confidence without freshness, oracle, liquidity, or fixture provenance",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "DeFi risk sentinel implementation can create false confidence if exposure, oracle/indexer freshness, "
                    "liquidity stress, and release proof are not bound before source edits."
                ),
                "mitigation": (
                    "Keep the first wave fixture-backed and non-custodial; require freshness/confidence fields, "
                    "deterministic replay proof, and refreshed Radar/Registry/Atlas/Compass before release promotion."
                ),
            },
            {
                "id": "R2",
                "risk_class": "compliance_boundary",
                "severity": "high",
                "trigger": "custody, trading, advice, live RPC, private keys, or unaudited acknowledgement enters scope",
                "early_warning": "component specs or workstreams describe provider integration without no-advice/no-custody proof gates",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Strict regulated posture can be weakened if custody, trade execution, financial advice, private-key, "
                    "audit, or live-provider assumptions remain implicit."
                ),
                "mitigation": (
                    "Make no-custody, no-trading, no-advice, no-private-key, no-live-RPC, data-classification, "
                    "and audit obligations explicit before the first technical plan can open."
                ),
            },
        ]
    if domain_profile.family == "commerce":
        return [
            {
                "id": "R1",
                "risk_class": "payment_integrity",
                "severity": "high",
                "trigger": "checkout, order draft, payment callback, or retry ownership is unclear",
                "early_warning": "happy-path checkout text appears before failed-payment or replay proof exists",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Commerce implementation can double-submit orders or hide failed payments if checkout, "
                    "order draft, callback replay, and recovery states are not separated before source edits."
                ),
                "mitigation": (
                    "Keep the first wave sandbox-only; require idempotency, failed-payment recovery, callback replay, "
                    "and browser proof before any production payment or fulfillment claim."
                ),
            },
            {
                "id": "R2",
                "risk_class": "customer_trust",
                "severity": "medium",
                "trigger": "catalog price, inventory, order, or payment state is inferred from UI labels",
                "early_warning": "storefront success state appears without immutable price and inventory snapshot proof",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Shopper-visible success can outrun actual order/payment truth if price snapshots, inventory posture, "
                    "provider failures, and retry semantics stay implicit."
                ),
                "mitigation": (
                    "Bind storefront, checkout/order core, and proof harness workstreams to explicit sandbox fixtures, "
                    "immutable snapshot rules, and recovery-state validation."
                ),
            },
        ]
    return [
        {
            "id": "R1",
            "risk_class": "project_spine",
            "severity": "medium",
            "trigger": "workflow, domain contract, proof harness, release gate, or component ownership is still unnamed",
            "early_warning": "first implementation prompt names files before user, state, validation, and rollback choices are accepted",
            "evidence_tier": "odylith_assumption",
            "statement": (
                f"{title} can fragment into disconnected source slices if the first workflow, domain contract, "
                "component ownership, release gate, and proof harness are not accepted before implementation."
            ),
            "mitigation": (
                "Apply only after operator review, then bind every source change to a child workstream, component boundary, "
                "proof command, and refreshed Odylith surface."
            ),
        },
        {
            "id": "R2",
            "risk_class": "policy_and_operations",
            "severity": "medium",
            "trigger": "data, auth, audit, accessibility, recovery, or deployment choices are left to implicit defaults",
            "early_warning": "readiness gates mention tests but not data sensitivity, abuse, fallback, or operator review",
            "evidence_tier": "odylith_assumption",
            "statement": (
                f"{title} can make unsafe product claims if data sensitivity, access control, auditability, fallback, "
                "deployment, and recovery posture remain unresolved during the first release gate."
            ),
            "mitigation": (
                "Require explicit operator answers for runtime, data boundary, compliance posture, degraded behavior, "
                "and release proof before any production-readiness claim."
            ),
        },
    ]


def _base_security_compliance(title: str, *, domain_profile: GreenfieldDomainProfile) -> dict[str, str]:
    if domain_profile.family == "defi_risk":
        return {
            "domain": (
                f"{title} is a non-custodial DeFi risk-monitoring proposal with sensitive wallet, exposure, "
                "oracle/indexer, liquidity, derived-risk, and acknowledgement data."
            ),
            "security": (
                "Security posture covers operator identity, audit trails, fixture provenance, private-key exclusion, "
                "no live RPC in the first release, and abuse-resistant acknowledgement semantics."
            ),
            "policy": (
                "Strict regulated posture keeps no-custody, no-trading, no-financial-advice, data classification, "
                "freshness/confidence disclosure, retention, and release approval explicit before source edits."
            ),
        }
    if domain_profile.family == "commerce":
        return {
            "domain": (
                f"{title} is a commerce checkout proposal with shopper, cart, price snapshot, order, payment sandbox, "
                "retry, and recovery-state risk."
            ),
            "security": (
                "Security posture covers session boundaries, payment handoff, idempotency keys, callback replay, "
                "abuse controls, and secret-free sandbox fixtures."
            ),
            "policy": (
                "Policy posture keeps PCI/provider boundaries, privacy, accessibility, failed-payment recovery, "
                "retention, and production-payment approval explicit before release promotion."
            ),
        }
    return {
        "domain": f"{title} is at proposal stage with user-intent evidence only; domain and delivery risk stay explicit until source exists.",
        "security": (
            f"{title} security posture must name the first actor, access boundary, least-privilege write path, "
            "secret handling, abuse case, audit point, and degraded/recovery behavior before release promotion."
        ),
        "policy": (
            f"{title} policy posture must track data sensitivity, privacy, retention, accessibility, safety or "
            "regulatory review, operator approval, and production-readiness limits before source-backed claims."
        ),
    }


def _base_validation_strategy() -> list[str]:
    return [
        "First-wave workstreams must define source-backed behavior proof before implementation starts.",
        "Registry candidate specs must stay component-specific: interfaces, dependencies, failure modes, first coding slice, definition of done, and verification commands belong to the component, not copied project posture.",
        "Atlas diagrams must render after apply and remain traceable to Radar workstreams and Registry components.",
        "Compass and Radar must show the first release lane, active wave, start workstream, and proof gates after apply.",
    ]


def _program(*, title: str, components: Mapping[str, str]) -> dict[str, Any]:
    return {
        "name": title,
        "waves": [
            {
                "wave_id": "W1",
                "label": "First governed slice",
                "goal": "Prove the smallest coherent product workflow with source-backed validation.",
                "validation_gate": (
                    "The first workstream has a technical plan, behavior proof, refreshed Radar/Registry/Atlas/"
                    "Compass surfaces, and release-target validation."
                ),
                "workstreams": ["WS-01", "WS-02"],
                "component_focus": [components["experience"], components["domain"]],
                "evidence_tier": "odylith_assumption",
            },
            {
                "wave_id": "W2",
                "label": "Hardening and operations",
                "goal": "Add operational proof, fallback behavior, and release-readiness checks after the first slice works.",
                "validation_gate": (
                    "Operational, accessibility, security, and recovery checks pass without widening the first release scope."
                ),
                "workstreams": ["WS-03"],
                "component_focus": [components["validation"]],
                "evidence_tier": "odylith_assumption",
            },
        ],
    }


def _release_plan(
    *,
    selector: str,
    slug: str,
    experience_component: str,
    domain_component: str,
) -> dict[str, Any]:
    return {
        "selector": selector,
        "label": greenfield_programs.compact_release_target_label(selector),
        "provisional_release_id": f"release-{slug}-{slugify(selector)}",
        "strategy": "Promote only after the first governed slice has source-backed tests and refreshed Odylith surfaces.",
        "target_workstreams": ["WS-01", "WS-02"],
        "release_stages": [
            {
                "release": selector,
                "label": "First governed slice",
                "exit_criteria": "Product workflow, domain contract, Atlas render, Registry specs, Compass, and Radar all agree.",
            }
        ],
        "promotion_criteria": [
            "First workstream has a technical plan and repository-native behavior proof.",
            "Registry, Atlas, Radar, and Compass refresh cleanly after source changes.",
        ],
        "component_focus": [experience_component, domain_component],
        "evidence_tier": "odylith_assumption",
    }


def _backlog(*, title: str, selector: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        _umbrella_backlog_row(title=title, selector=selector, components=components, diagrams=diagrams),
        _workflow_backlog_row(title=title, components=components, diagrams=diagrams),
        _domain_backlog_row(title=title, components=components, diagrams=diagrams),
        _verification_backlog_row(title=title, components=components, diagrams=diagrams),
    ]


def _umbrella_backlog_row(
    *,
    title: str,
    selector: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "id": "WS-00",
        "title": f"Govern {title}",
        "workstream_type": "umbrella",
        "problem": (
            f"{title} needs a governed execution spine before source exists, otherwise first-wave implementation "
            "choices will not trace to product intent, components, diagrams, release gates, or validation proof."
        ),
        "customer": "The project operator, implementation agents, reviewers, and maintainers who need one trusted program view before code starts.",
        "opportunity": (
            "Create one umbrella program that ties user intent, first wave, release target, Radar workstreams, "
            "Registry candidates, Atlas topology, and proof gates together."
        ),
        "product_view": f"A proposal-first Odylith program for {title} with one active first wave, a {selector} release target, candidate components, and diagram traceability.",
        "recommended_first_slice": "Confirm the first governed slice, then open the first child workstream and author the technical plan before editing source.",
        "success_metrics": [
            "Compass shows the umbrella, first wave, and release target after apply.",
            "Radar, Registry, and Atlas all link the first-wave workstreams to the same component and diagram boundaries.",
            "The start workstream includes validation gates and a first implementation prompt.",
        ],
        "component_focus": [components["experience"], components["domain"], components["validation"]],
        "related_diagram_slugs": [
            diagrams["overview"],
            diagrams["slice"],
            diagrams["component_map"],
            diagrams["domain_state"],
            diagrams["validation_release"],
        ],
        "dependencies": ["Child workstreams depend on this umbrella for wave membership, release targeting, and proof sequencing."],
        "interfaces": ["Compass, Radar, Registry, and Atlas expose one shared greenfield program topology."],
        "validation": ["Greenfield apply Tribunal passes and all four dashboard surfaces refresh."],
        "domain_risk": "Greenfield governance can mislead source implementation if the first wave, component ownership, release target, or proof gates are vague.",
        "security_posture": "Security, privacy, accessibility, abuse, audit, and recovery posture stay explicit until source-backed implementation narrows them.",
        "priority": "P1",
        "sizing": "L",
        "complexity": "High",
        "evidence_tier": "user_intent",
    }


def _workflow_backlog_row(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> dict[str, Any]:
    return {
        "id": "WS-01",
        "title": "Define first operator workflow",
        "problem": f"{title} needs one concrete operator-visible workflow before implementation can avoid generic scaffolding.",
        "customer": "Primary users or operators of the proposed product and the engineers implementing the first slice.",
        "opportunity": "Turn broad intent into a narrow behavior path that can be implemented, tested, and reviewed without claiming the whole system is done.",
        "product_view": "The first workflow owns entry, happy path, empty or degraded state, and user-visible completion criteria.",
        "recommended_first_slice": "Implement the smallest operator-visible path with normal, empty, and degraded/error state proof.",
        "success_metrics": [
            "The first workflow has a source-backed test or browser proof before the next wave starts.",
            "The workflow boundary appears in Registry and Atlas with linked Radar traceability.",
        ],
        "component_focus": [components["experience"], components["domain"]],
        "related_diagram_slugs": [diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
        "dependencies": ["Depends on the domain contract workstream for the data and command boundary used by the first workflow."],
        "interfaces": ["Defines the first user-facing route, command, CLI, or service entrypoint plus visible fallback states."],
        "validation": ["Repository-native behavior proof covers the first workflow normal path and at least one degraded or empty state."],
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": "user_intent",
    }


def _domain_backlog_row(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> dict[str, Any]:
    return {
        "id": "WS-02",
        "title": "Define domain contract and ownership",
        "problem": f"{title} cannot scale beyond the first workflow without a named domain contract for state, commands, ownership, and invariants.",
        "customer": "Engineers implementing source boundaries and reviewers checking correctness of data and state transitions.",
        "opportunity": "Make the domain core explicit before storage, API, worker, or UI choices harden into accidental architecture.",
        "product_view": "A domain component owns the first state model, commands, invariants, and integration handoff used by the operator workflow.",
        "recommended_first_slice": "Write the domain contract and minimal implementation that the first workflow consumes.",
        "success_metrics": [
            "Domain contract tests prove the first state transition and invalid input rejection.",
            "Registry records the domain component interfaces, dependencies, and verification commands.",
        ],
        "component_focus": [components["domain"]],
        "related_diagram_slugs": [diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
        "dependencies": ["Depends on confirmed first-workflow semantics and defers storage selection until technical planning."],
        "interfaces": ["Defines the initial command, query, event, or file contract consumed by the first workflow."],
        "validation": ["Contract tests cover valid transition, invalid input, and idempotent or retry behavior where relevant."],
        "priority": "P1",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": "odylith_assumption",
    }


def _verification_backlog_row(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> dict[str, Any]:
    return {
        "id": "WS-03",
        "title": "Add release proof and operations harness",
        "problem": f"{title} needs repeatable proof, fallback checks, and release-readiness evidence before the first slice can be promoted.",
        "customer": "Maintainers, reviewers, and future operators who need reproducible validation instead of a one-off manual demo.",
        "opportunity": "Capture the first release verification commands, smoke fixtures, and dashboard refresh proof while the program is still small.",
        "product_view": "A verification harness records the first release smoke, regression checks, accessibility or safety gates, and operational recovery expectations.",
        "recommended_first_slice": "Create the first smoke or regression harness around the operator workflow and domain contract.",
        "success_metrics": [
            "Release proof runs locally with deterministic fixtures and no production credentials.",
            "Compass/Radar/Registry/Atlas refresh after the proof and show the same first release lane.",
        ],
        "component_focus": [components["validation"]],
        "related_diagram_slugs": [diagrams["validation_release"], diagrams["domain_state"]],
        "dependencies": ["Depends on WS-01 and WS-02 behavior proof before hardening expands scope."],
        "interfaces": ["Defines local smoke commands, fixture inputs, report output, and release-readiness checks."],
        "validation": ["Smoke proof runs under the repo-native toolchain and fails closed on missing fixtures or stale surfaces."],
        "priority": "P2",
        "sizing": "M",
        "complexity": "Medium",
        "evidence_tier": "odylith_assumption",
    }


def _components(
    components: Mapping[str, str],
    *,
    diagrams: Mapping[str, str],
    domain_profile: GreenfieldDomainProfile,
) -> list[dict[str, Any]]:
    experience = domain_profile.components["experience"]
    domain = domain_profile.components["domain"]
    validation = domain_profile.components["validation"]
    return [
        _component_row(
            component_id=components["experience"],
            label=experience.label,
            kind=experience.kind,
            path=f"{experience.path_prefix}/{components['experience']}",
            responsibility=experience.responsibility,
            boundary=experience.boundary,
            dependencies=list(experience.dependencies),
            interfaces=list(experience.interfaces),
            validation=list(experience.validation),
            risks=list(experience.risks),
            diagrams=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
        ),
        _component_row(
            component_id=components["domain"],
            label=domain.label,
            kind=domain.kind,
            path=f"{domain.path_prefix}/{components['domain']}",
            responsibility=domain.responsibility,
            boundary=domain.boundary,
            dependencies=list(domain.dependencies),
            interfaces=list(domain.interfaces),
            validation=list(domain.validation),
            risks=list(domain.risks),
            diagrams=[diagrams["overview"], diagrams["slice"], diagrams["component_map"], diagrams["domain_state"]],
        ),
        _component_row(
            component_id=components["validation"],
            label=validation.label,
            kind=validation.kind,
            path=f"{validation.path_prefix}/{components['validation']}",
            responsibility=validation.responsibility,
            boundary=validation.boundary,
            dependencies=list(validation.dependencies),
            interfaces=list(validation.interfaces),
            validation=list(validation.validation),
            risks=list(validation.risks),
            diagrams=[diagrams["overview"], diagrams["validation_release"]],
        ),
    ]


def _component_row(
    *,
    component_id: str,
    label: str,
    kind: str,
    path: str,
    responsibility: str,
    boundary: str,
    dependencies: list[str],
    interfaces: list[str],
    validation: list[str],
    risks: list[str],
    diagrams: list[str],
) -> dict[str, Any]:
    return {
        "component_id": component_id,
        "label": label,
        "kind": kind,
        "intended_path": path,
        "status": "planned",
        "qualification": "candidate",
        "responsibility": responsibility,
        "boundary": boundary,
        "dependencies": dependencies,
        "interfaces": interfaces,
        "validation": validation,
        "risks": risks,
        "related_diagram_slugs": diagrams,
        "evidence_tier": "user_intent",
    }


def _diagrams(*, title: str, components: Mapping[str, str], diagrams: Mapping[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "slug": diagrams["overview"],
            "title": f"{title} System Overview",
            "kind": "flowchart",
            "summary": "Top-level project formation map: intent becomes governed project truth first, then candidate components, proof, surfaces, and operator review.",
            "review_focus": "Use this view to confirm the project spine, evidence boundary, and no-code gate before any child plan is opened.",
            "operator_question": "Does this show the right first user, project truth, component path, and review gate?",
            "proof_gate": "No source-backed claim until the first child plan names paths, tests, degraded states, and rollback or recovery posture.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["experience"], "description": "Owns the first operator-visible workflow and visible states."},
                {"name": components["domain"], "description": "Owns the first domain contract, state model, and invariants."},
                {"name": components["validation"], "description": "Owns deterministic first-release proof and refresh checks."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _overview_mermaid(),
        },
        {
            "slug": diagrams["slice"],
            "title": f"{title} First Slice Flow",
            "kind": "sequenceDiagram",
            "summary": "First-slice sequence showing where the operator action, domain decision, proof harness, refresh, and handoff happen.",
            "review_focus": "Use this view to decide which interaction becomes B-002 and what normal, empty, degraded, and failure evidence must prove.",
            "operator_question": "Is this the first workflow the project should prove before broader platform work?",
            "proof_gate": "The technical plan must name behavior proof and contract proof before source edits start.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["experience"], "description": "Starts the operator-visible first workflow."},
                {"name": components["domain"], "description": "Validates state and command semantics for the workflow."},
                {"name": components["validation"], "description": "Runs proof and captures release-readiness evidence."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _slice_mermaid(),
        },
        {
            "slug": diagrams["component_map"],
            "title": f"{title} Component Ownership Map",
            "kind": "flowchart",
            "summary": "Ownership review map: separates experience, domain contract, proof harness, governance surfaces, and the split rules between them.",
            "review_focus": "Use this view to prevent broad project narrative from leaking into component specs.",
            "operator_question": "Are the component boundaries specific enough that future agents know who owns each interface and proof obligation?",
            "proof_gate": "Each candidate component stays planned until its own source path, tests, and refreshed Registry evidence exist.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["experience"], "description": "Owns the human-facing first workflow boundary and fallback behavior."},
                {"name": components["domain"], "description": "Owns domain state, command semantics, and invariant enforcement."},
                {"name": components["validation"], "description": "Owns deterministic proof fixtures and release-readiness reports."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _component_map_mermaid(),
        },
        {
            "slug": diagrams["domain_state"],
            "title": f"{title} Domain State Model",
            "kind": "stateDiagram",
            "summary": "Domain-state review: shows allowed, blocked, degraded, retry, and completed states before implementation chooses code paths.",
            "review_focus": "Use this view to catch fake progress and missing degraded/error states early.",
            "operator_question": "Which state transition would be unsafe, misleading, or unsupported for release 0.0.1?",
            "proof_gate": "Every promoted state transition needs a deterministic test, fixture, or review decision.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["domain"], "description": "Owns the domain states and valid transitions for the first slice."},
                {"name": components["experience"], "description": "Renders accepted, rejected, completed, and degraded states to the operator."},
                {"name": components["validation"], "description": "Exercises state transitions through deterministic contract proof."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _domain_state_mermaid(),
        },
        {
            "slug": diagrams["validation_release"],
            "title": f"{title} Validation And Release Topology",
            "kind": "flowchart",
            "summary": "Release-readiness control map tying plan, behavior proof, contract proof, refresh, Compass, and operator handoff together.",
            "review_focus": "Use this view to decide what must be proven before release 0.0.1 can advance.",
            "operator_question": "Are the acceptance gates strong enough for the chosen runtime, data boundary, and compliance posture?",
            "proof_gate": "Release movement is blocked until plan, proof, refreshed surfaces, and unresolved-risk review agree.",
            "link_state": "atlas_first_draft",
            "components": [
                {"name": components["validation"], "description": "Owns the proof command, fixtures, and release-readiness evidence."},
                {"name": components["experience"], "description": "Supplies behavior proof for normal, empty, and degraded states."},
                {"name": components["domain"], "description": "Supplies contract proof for state, commands, and invariant failures."},
            ],
            "related_workstreams": ["WS-00", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _validation_release_mermaid(),
        },
    ]


def _overview_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Intent[Operator<br/>intent]:::actor --> Choices[Direction choices<br/>user data runtime proof]:::decision\n"
        "  Choices --> ProjectTruth[Project intelligence<br/>Radar parent]:::governance\n"
        "  ProjectTruth --> Experience[Experience<br/>boundary]:::service\n"
        "  ProjectTruth --> Domain[Domain<br/>core]:::service\n"
        "  Experience --> Domain\n"
        "  Domain --> Harness[Verification<br/>harness]:::proof\n"
        "  Harness --> Surfaces[Odylith surfaces<br/>Radar Registry Atlas Compass]:::governance\n"
        "  Surfaces --> Review[Operator review<br/>accept gates before code]:::actor\n"
        "  Review --> CodeGate[Code gate<br/>plan paths tests rollback]:::gate\n"
        "  Evidence[Evidence boundary<br/>intent not source-backed]:::note -. constrains .-> ProjectTruth\n"
        "  Evidence -. constrains .-> CodeGate\n"
        "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef governance fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef decision fill:#eef2ff,stroke:#818cf8,color:#1e1b4b;\n"
        "  classDef gate fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
        "  classDef note fill:#f8fafc,stroke:#cbd5e1,color:#334155,stroke-dasharray: 3 3;\n"
    )


def _slice_mermaid() -> str:
    return (
        "sequenceDiagram\n"
        "  participant Operator as Operator\n"
        "  participant Experience as Experience Boundary\n"
        "  participant Domain as Domain Core\n"
        "  participant Harness as Verification Harness\n"
        "  participant Surfaces as Odylith Surfaces\n"
        "  Note over Operator,Surfaces: Project review and direction choices happen before source edits\n"
        "  Operator->>Experience: start first workflow\n"
        "  Experience->>Domain: execute command or query\n"
        "  Domain-->>Experience: validated state result\n"
        "  Note over Experience,Domain: Normal empty degraded and failure states must be explicit\n"
        "  Harness->>Experience: run behavior proof\n"
        "  Harness->>Domain: run contract proof\n"
        "  Harness->>Surfaces: refresh Radar Registry Atlas Compass\n"
        "  Note over Harness,Surfaces: Proof is not accepted until governed surfaces agree\n"
        "  Surfaces-->>Operator: show first wave and release lane\n"
    )


def _component_map_mermaid() -> str:
    return (
        "flowchart TB\n"
        "  Lens[Decision lens<br/>split by owner evidence risk gate]:::note\n"
        "  subgraph experience[Experience<br/>ownership]\n"
        "    Entry[First workflow<br/>entrypoint]:::ux\n"
        "    States[Visible normal empty<br/>and degraded states]:::ux\n"
        "  end\n"
        "  subgraph domain[Domain<br/>ownership]\n"
        "    Contract[Command query<br/>and event contract]:::core\n"
        "    Invariants[State invariants<br/>and rejection rules]:::core\n"
        "  end\n"
        "  subgraph proof[Proof<br/>ownership]\n"
        "    Fixtures[Deterministic<br/>fixtures]:::proof\n"
        "    Report[Release readiness<br/>report]:::proof\n"
        "  end\n"
        "  Entry --> Contract --> Invariants --> States\n"
        "  Fixtures --> Contract\n"
        "  Fixtures --> Entry\n"
        "  Report --> Surfaces[Compass Radar<br/>Registry Atlas]:::governance\n"
        "  Lens -. review .-> experience\n"
        "  Lens -. review .-> domain\n"
        "  Lens -. review .-> proof\n"
        "  classDef ux fill:#fff7df,stroke:#d7a93d,color:#52390a;\n"
        "  classDef core fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef governance fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef note fill:#f8fafc,stroke:#cbd5e1,color:#334155,stroke-dasharray: 3 3;\n"
    )


def _domain_state_mermaid() -> str:
    return (
        "stateDiagram-v2\n"
        "  [*] --> Draft\n"
        "  note right of Draft\n"
        "    Proposal state, not source proof\n"
        "  end note\n"
        "  Draft --> Accepted: valid command\n"
        "  Draft --> Rejected: invalid input\n"
        "  Accepted --> InProgress: workflow starts\n"
        "  InProgress --> Completed: success proof\n"
        "  InProgress --> Degraded: dependency missing\n"
        "  note right of Degraded\n"
        "    Must be visible, testable, and safe\n"
        "  end note\n"
        "  Degraded --> Retried: retry allowed\n"
        "  Retried --> Completed: recovery succeeds\n"
        "  Retried --> Rejected: retry exhausted\n"
        "  Completed --> [*]\n"
        "  Rejected --> [*]\n"
    )


def _validation_release_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Plan[Technical plan<br/>for first workstream]:::governance --> Behavior[Behavior proof<br/>normal empty degraded]:::proof\n"
        "  Plan --> Contract[Contract proof<br/>state and invariants]:::proof\n"
        "  Choices[Accepted choices<br/>runtime data proof]:::gate --> Plan\n"
        "  Behavior --> Harness[Verification<br/>harness]:::proof\n"
        "  Contract --> Harness\n"
        "  Harness --> Refresh[Surface refresh<br/>Radar Registry Atlas Compass]:::governance\n"
        "  Refresh --> Lane[Compass lane<br/>release 0.0.1]:::release\n"
        "  Lane --> Handoff[Operator handoff<br/>next command and gates]:::release\n"
        "  Blocked[Blocked if risks<br/>or choices unresolved]:::blocked -. prevents .-> Lane\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef governance fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef release fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef gate fill:#eef2ff,stroke:#818cf8,color:#1e1b4b;\n"
        "  classDef blocked fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
    )


__all__ = ["build_apply_ready_proposal"]
