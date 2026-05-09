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
from odylith.runtime.domain_intelligence.greenfield_workstream_rows import build_child_backlog_rows
from odylith.runtime.domain_intelligence.proposal_rendering import build_apply_commands
from odylith.runtime.domain_intelligence.robot_swarm_profile import apply_robot_swarm_logistics_profile
from odylith.runtime.domain_intelligence.robot_swarm_profile import is_robot_swarm_logistics_prompt

_GREENFIELD_FIRST_DRAFT_LINK_STATE = "architecture_first_draft"


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
    program = _program(title=title, components=components, domain_profile=domain_profile)
    release_plan = _release_plan(
        selector=selector,
        slug=slug,
        experience_component=components["experience"],
        domain_component=components["domain"],
        domain_profile=domain_profile,
    )
    component_rows = _components(components, diagrams=diagrams, domain_profile=domain_profile)
    diagram_rows = _diagrams(title=title, components=components, diagrams=diagrams, domain_profile=domain_profile)
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
            domain_profile=domain_profile,
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
        else f"Turn `{prompt}` into an accepted greenfield product program before source-backed implementation starts."
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
            "statement": "The first release should prove a narrow product workflow before broad source architecture is claimed.",
        },
        {
            "id": "A2",
            "evidence_tier": "odylith_assumption",
            "statement": "Implementation starts with repository-native tests and one technical plan per child workstream.",
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
                    "deterministic replay proof, and refreshed project records before release promotion."
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
    if domain_profile.family == "defi_merchant_lending":
        return [
            {
                "id": "R1",
                "risk_class": "credit_liquidity_integrity",
                "severity": "high",
                "trigger": "merchant eligibility, underwriting inputs, liquidity, disbursement, repayment, or Shopify data boundaries are unclear",
                "early_warning": "retail-buyer or card-processing language appears before merchant facility, liquidity, and repayment proof exists",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Merchant lending implementation can misstate approved capital, over-commit stablecoin liquidity, "
                    "or duplicate disbursement/repayment events if credit, liquidity, and facility state are not separated before source edits."
                ),
                "mitigation": (
                    "Keep the first wave fixture-backed; require Shopify merchant snapshots, eligibility gates, liquidity snapshots, "
                    "idempotent disbursement/repayment replay, and refreshed project records before release promotion."
                ),
            },
            {
                "id": "R2",
                "risk_class": "compliance_treasury_boundary",
                "severity": "high",
                "trigger": "KYB, AML, sanctions, lending disclosure, no-custody, private-key, stablecoin, or live-protocol posture is implicit",
                "early_warning": "component specs describe DeFi funding or Shopify integration without regulated data, no-custody, and live-protocol proof gates",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Stablecoin merchant lending can imply production lending, custody, money movement, or financial advice before "
                    "KYB/AML, lending, treasury, and protocol-risk decisions are explicit."
                ),
                "mitigation": (
                    "Make KYB/AML/sanctions, lending disclosures, no-custody, no-private-key, no-live-protocol, data classification, "
                    "audit, retention, and release approval obligations explicit before the first technical plan can open."
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
                "proof command, and refreshed project record."
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
    if domain_profile.family == "defi_merchant_lending":
        return {
            "domain": (
                f"{title} is an SMB merchant lending proposal with sensitive Shopify merchant data, underwriting inputs, "
                "credit facility state, stablecoin funding, DeFi liquidity, disbursement, repayment, treasury, and audit data."
            ),
            "security": (
                "Security posture covers merchant identity and consent, Shopify app scopes, secret-free fixtures, audit trails, "
                "idempotency keys, private-key exclusion, no custody, and no live protocol or production disbursement in the first release."
            ),
            "policy": (
                "Strict regulated posture keeps KYB, AML, sanctions, lending disclosures, money-transmission or securities review, "
                "data classification, retention, stablecoin/DeFi risk disclosure, and release approval explicit before source edits."
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
        "First-wave workstreams must define implementation-backed behavior proof before implementation starts.",
        "Candidate component specs must stay component-specific: interfaces, dependencies, failure modes, first coding slice, definition of done, and verification commands belong to the component, not copied project posture.",
        "Architecture diagrams must render after apply and remain traceable to workstreams and component candidates.",
        "Project records must show the first release lane, active wave, start workstream, and proof gates after apply.",
    ]


def _program(*, title: str, components: Mapping[str, str], domain_profile: GreenfieldDomainProfile) -> dict[str, Any]:
    if domain_profile.family == "defi_merchant_lending":
        return {
            "name": title,
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "Merchant capital first slice",
                    "goal": (
                        "Prove merchant application, Shopify snapshot freshness, eligibility, compliance, "
                        "stablecoin liquidity, funding status, and repayment visibility with deterministic evidence."
                    ),
                    "validation_gate": (
                        "Eligible, declined, stale-data, liquidity-blocked, compliance-blocked, duplicate-disbursement, "
                        "and repayment-replay scenarios pass without live Shopify, live DeFi, custody keys, or production credentials."
                    ),
                    "workstreams": ["WS-01", "WS-02"],
                    "component_focus": [components["experience"], components["domain"]],
                    "evidence_tier": "odylith_assumption",
                },
                {
                    "wave_id": "W2",
                    "label": "Regulated operations hardening",
                    "goal": (
                        "Harden audit, replay, disclosure, fallback, liquidity-source, and repayment evidence after "
                        "the merchant capital slice is coherent."
                    ),
                    "validation_gate": (
                        "Closed-world proof covers regulated blockers, no-custody posture, no-live-protocol posture, "
                        "accessibility, audit evidence, and release non-goals without expanding production scope."
                    ),
                    "workstreams": ["WS-03"],
                    "component_focus": [components["validation"]],
                    "evidence_tier": "odylith_assumption",
                },
            ],
        }
    return {
        "name": title,
        "waves": [
            {
                "wave_id": "W1",
                "label": "First product slice",
                "goal": "Prove the smallest coherent product workflow with source-backed validation.",
                "validation_gate": (
                    "The first workstream has a technical plan, behavior proof, refreshed project records, "
                    "and release-target validation."
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
    domain_profile: GreenfieldDomainProfile,
) -> dict[str, Any]:
    if domain_profile.family == "defi_merchant_lending":
        return {
            "selector": selector,
            "label": greenfield_programs.compact_release_target_label(selector),
            "provisional_release_id": f"release-{slug}-{slugify(selector)}",
            "strategy": (
                "Promote only after merchant application, eligibility, compliance, stablecoin liquidity, "
                "funding status, and repayment proof pass with closed-world fixtures."
            ),
            "target_workstreams": ["WS-01", "WS-02"],
            "release_stages": [
                {
                    "release": selector,
                    "label": "Merchant capital first slice",
                    "exit_criteria": (
                        "Merchant portal, credit-liquidity contract, Shopify snapshot fixture, compliance fixture, "
                        "stablecoin liquidity fixture, and repayment replay agree."
                    ),
                }
            ],
            "promotion_criteria": [
                "Eligible, declined, stale Shopify, liquidity shortfall, compliance block, duplicate disbursement, and repayment replay scenarios pass.",
                "No live Shopify access, live DeFi protocol calls, custody keys, private keys, or production credentials are required.",
            ],
            "component_focus": [experience_component, domain_component],
            "evidence_tier": "odylith_assumption",
        }
    return {
        "selector": selector,
        "label": greenfield_programs.compact_release_target_label(selector),
        "provisional_release_id": f"release-{slug}-{slugify(selector)}",
        "strategy": "Promote only after the first product slice has source-backed tests and refreshed project records.",
        "target_workstreams": ["WS-01", "WS-02"],
        "release_stages": [
            {
                "release": selector,
                "label": "First product slice",
                "exit_criteria": "Product workflow, domain contract, architecture diagrams, component specs, and release records all agree.",
            }
        ],
        "promotion_criteria": [
            "First workstream has a technical plan and repository-native behavior proof.",
            "Project records refresh cleanly after source changes.",
        ],
        "component_focus": [experience_component, domain_component],
        "evidence_tier": "odylith_assumption",
    }


def _backlog(
    *,
    title: str,
    selector: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
    domain_profile: GreenfieldDomainProfile,
) -> list[dict[str, Any]]:
    return [
        _umbrella_backlog_row(
            title=title,
            selector=selector,
            components=components,
            diagrams=diagrams,
            domain_profile=domain_profile,
        ),
        *build_child_backlog_rows(
            title=title,
            components=components,
            diagrams=diagrams,
            domain_profile=domain_profile,
        ),
    ]


def _umbrella_backlog_row(
    *,
    title: str,
    selector: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
    domain_profile: GreenfieldDomainProfile,
) -> dict[str, Any]:
    if domain_profile.family == "defi_merchant_lending":
        return {
            "id": "WS-00",
            "title": f"Shape {title} merchant lending launch",
            "workstream_type": "umbrella",
            "problem": (
                f"{title} needs product requirements for SMB Shopify merchant borrowers, Shopify data consent, "
                "credit eligibility, stablecoin liquidity, compliance blockers, disbursement, and repayment before "
                "implementation can make any lending or funding claim."
            ),
            "customer": (
                "SMB Shopify merchants seeking working capital, capital-ops reviewers checking offer readiness, "
                "and compliance or treasury reviewers constraining regulated funding behavior."
            ),
            "opportunity": (
                "Turn broad DeFi-plus-Shopify lending intent into a concrete merchant-capital product lane with "
                "borrower states, credit-facility rules, stablecoin liquidity posture, repayment visibility, and "
                "regulated non-goals."
            ),
            "product_view": (
                f"A merchant capital product for Shopify sellers: application intake, Shopify sales snapshot, "
                "eligibility decision, compliance gate, stablecoin-funded offer, funding status, and repayment state."
            ),
            "recommended_first_slice": (
                "Start with the merchant application and funding-status path, then bind the credit-liquidity contract "
                "that proves eligibility, blocked states, disbursement replay, and repayment replay."
            ),
            "success_metrics": [
                "Merchant borrower states cover draft, in review, declined, eligible, liquidity blocked, compliance blocked, funded, repayment due, and repaid.",
                "Closed-world fixtures prove stale Shopify data, liquidity shortfall, compliance block, duplicate disbursement, and repayment replay.",
                "Release 0.0.1 makes no production lending, custody, private-key, live-protocol, or real-merchant-data claim.",
            ],
            "component_focus": [components["experience"], components["domain"], components["validation"]],
            "related_diagram_slugs": [
                diagrams["overview"],
                diagrams["slice"],
                diagrams["component_map"],
                diagrams["domain_state"],
                diagrams["validation_release"],
            ],
            "dependencies": [
                "Merchant borrower workflow depends on Shopify data consent, credit-liquidity semantics, compliance posture, and closed-world proof fixtures."
            ],
            "interfaces": [
                "Product requirements expose borrower application state, credit facility state, liquidity state, compliance state, disbursement events, and repayment events."
            ],
            "validation": [
                "Requirement review passes only when borrower workflow, credit-liquidity contract, fixtures, non-goals, and regulated blockers agree."
            ],
            "domain_risk": (
                "Generic commerce defaults can erase the actual lending domain, causing borrower states, regulated blockers, "
                "stablecoin liquidity, repayment, and no-custody constraints to disappear."
            ),
            "security_posture": (
                "KYB/AML/sanctions, lending disclosure, no-custody, no-private-key, no-live-protocol, audit, privacy, and repayment evidence stay explicit."
            ),
            "priority": "P1",
            "sizing": "L",
            "complexity": "High",
            "evidence_tier": "user_intent",
        }
    return {
        "id": "WS-00",
        "title": f"Govern {title}",
        "workstream_type": "umbrella",
        "problem": (
            f"{title} needs an accepted execution spine before source exists, otherwise first-wave implementation "
            "choices will not trace to product intent, components, diagrams, release gates, or validation proof."
        ),
        "customer": "The project operator, implementation agents, reviewers, and maintainers who need one trusted program view before code starts.",
        "opportunity": (
            "Create one umbrella program that ties user intent, first wave, release target, workstreams, "
            "component candidates, topology drafts, and proof gates together."
        ),
        "product_view": f"A proposal-first product program for {title} with one active first wave, a {selector} release target, candidate components, and diagram traceability.",
        "recommended_first_slice": "Confirm the first product slice, then open the first child workstream and author the technical plan before editing source.",
        "success_metrics": [
            "Project records show the umbrella, first wave, and release target after apply.",
            "Workstreams, component candidates, and diagrams all link the first wave to the same boundaries.",
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
        "interfaces": ["Accepted project records expose one shared greenfield program topology."],
        "validation": ["Greenfield proposal validation passes and project records refresh."],
        "domain_risk": "Greenfield planning can mislead source implementation if the first wave, component ownership, release target, or proof gates are vague.",
        "security_posture": "Security, privacy, accessibility, abuse, audit, and recovery posture stay explicit until source-backed implementation narrows them.",
        "priority": "P1",
        "sizing": "L",
        "complexity": "High",
        "evidence_tier": "user_intent",
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


def _diagrams(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
    domain_profile: GreenfieldDomainProfile,
) -> list[dict[str, Any]]:
    if domain_profile.family == "defi_merchant_lending":
        return _merchant_lending_diagrams(title=title, components=components, diagrams=diagrams)
    return [
        {
            "slug": diagrams["overview"],
            "title": f"{title} System Overview",
            "kind": "flowchart",
            "summary": "Top-level project formation map: intent becomes accepted project truth first, then candidate components, proof, and operator review.",
            "review_focus": "Use this view to confirm the project spine, evidence boundary, and no-code gate before any child plan is opened.",
            "operator_question": "Does this show the right first user, project truth, component path, and review gate?",
            "proof_gate": "No source-backed claim until the first child plan names paths, tests, degraded states, and rollback or recovery posture.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["experience"], "description": "Owns the first product workflow and visible states."},
                {"name": components["domain"], "description": "Owns the first domain contract, state model, and invariants."},
                {"name": components["validation"], "description": "Owns deterministic first-release proof and refresh checks."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _overview_mermaid(domain_profile),
        },
        {
            "slug": diagrams["slice"],
            "title": f"{title} First Slice Flow",
            "kind": "sequenceDiagram",
            "summary": "First-slice sequence showing where the operator action, domain decision, proof harness, and handoff happen.",
            "review_focus": "Use this view to decide which interaction becomes B-002 and what normal, empty, degraded, and failure evidence must prove.",
            "operator_question": "Is this the first workflow the project should prove before broader platform work?",
            "proof_gate": "The technical plan must name behavior proof and contract proof before source edits start.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["experience"], "description": "Starts the first product workflow."},
                {"name": components["domain"], "description": "Validates state and command semantics for the workflow."},
                {"name": components["validation"], "description": "Runs proof and captures release-readiness evidence."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _slice_mermaid(domain_profile),
        },
        {
            "slug": diagrams["component_map"],
            "title": f"{title} Component Ownership Map",
            "kind": "flowchart",
            "summary": "Ownership review map: separates experience, domain contract, proof harness, and the split rules between them.",
            "review_focus": "Use this view to prevent broad project narrative from leaking into component specs.",
            "operator_question": "Are the component boundaries specific enough that future agents know who owns each interface and proof obligation?",
            "proof_gate": "Each candidate component stays planned until its own source path, tests, and refreshed component evidence exist.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["experience"], "description": "Owns the human-facing first workflow boundary and fallback behavior."},
                {"name": components["domain"], "description": "Owns domain state, command semantics, and invariant enforcement."},
                {"name": components["validation"], "description": "Owns deterministic proof fixtures and release-readiness reports."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _component_map_mermaid(domain_profile),
        },
        {
            "slug": diagrams["domain_state"],
            "title": f"{title} Domain State Model",
            "kind": "stateDiagram",
            "summary": "Domain-state review: shows allowed, blocked, degraded, retry, and completed states before implementation chooses code paths.",
            "review_focus": "Use this view to catch fake progress and missing degraded/error states early.",
            "operator_question": "Which state transition would be unsafe, misleading, or unsupported for release 0.0.1?",
            "proof_gate": "Every promoted state transition needs a deterministic test, fixture, or review decision.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["domain"], "description": "Owns the domain states and valid transitions for the first slice."},
                {"name": components["experience"], "description": "Renders accepted, rejected, completed, and degraded states to the operator."},
                {"name": components["validation"], "description": "Exercises state transitions through deterministic contract proof."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _domain_state_mermaid(domain_profile),
        },
        {
            "slug": diagrams["validation_release"],
            "title": f"{title} Validation And Release Topology",
            "kind": "flowchart",
            "summary": "Release-readiness control map tying plan, behavior proof, contract proof, evidence bundle, release decision, and operator handoff together.",
            "review_focus": "Use this view to decide what must be proven before release 0.0.1 can advance.",
            "operator_question": "Are the acceptance gates strong enough for the chosen runtime, data boundary, and compliance posture?",
            "proof_gate": "Release movement is blocked until plan, proof, evidence, and unresolved-risk review agree.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["validation"], "description": "Owns the proof command, fixtures, and release-readiness evidence."},
                {"name": components["experience"], "description": "Supplies behavior proof for normal, empty, and degraded states."},
                {"name": components["domain"], "description": "Supplies contract proof for state, commands, and invariant failures."},
            ],
            "related_workstreams": ["WS-00", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _validation_release_mermaid(domain_profile),
        },
    ]


def _merchant_lending_diagrams(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "slug": diagrams["overview"],
            "title": f"{title} System Overview",
            "kind": "flowchart",
            "summary": "Merchant-capital map: Shopify merchant intent becomes borrower workflow, credit-liquidity state, fixture proof, and release review.",
            "review_focus": "Use this view to confirm borrower role, Shopify data boundary, stablecoin-liquidity posture, and no-custody gate.",
            "operator_question": "Does this show the merchant borrower and funding-state path instead of a retail purchase path?",
            "proof_gate": "No production lending, custody, live protocol, or real merchant-data claim before fixture proof exists.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["experience"], "description": "Owns merchant application intake and visible funding states."},
                {"name": components["domain"], "description": "Owns credit, liquidity, compliance, disbursement, and repayment invariants."},
                {"name": components["validation"], "description": "Owns merchant, liquidity, compliance, and ledger replay fixtures."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _merchant_lending_overview_mermaid(),
        },
        {
            "slug": diagrams["slice"],
            "title": f"{title} First Slice Flow",
            "kind": "sequenceDiagram",
            "summary": "First borrower slice: merchant application, Shopify snapshot, compliance gate, liquidity check, offer or blocked state, and proof replay.",
            "review_focus": "Use this view to decide which borrower-visible application and funding states release 0.0.1 must prove.",
            "operator_question": "Are the eligible, declined, stale-data, compliance-blocked, liquidity-blocked, funded, and repayment states right?",
            "proof_gate": "The technical plan must name fixture schemas and replay proof before source edits start.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["experience"], "description": "Starts the merchant borrower application and renders funding state."},
                {"name": components["domain"], "description": "Evaluates eligibility, compliance, liquidity, disbursement, and repayment state."},
                {"name": components["validation"], "description": "Replays fixtures for happy, blocked, stale, and duplicate-event cases."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _merchant_lending_slice_mermaid(),
        },
        {
            "slug": diagrams["component_map"],
            "title": f"{title} Component Ownership Map",
            "kind": "flowchart",
            "summary": "Ownership map separating merchant portal, credit-liquidity core, proof harness, and the regulated split rules between them.",
            "review_focus": "Use this view to keep borrower UX, credit decisions, liquidity, compliance, and proof ownership distinct.",
            "operator_question": "Are the component boundaries specific enough for implementation without re-learning the product?",
            "proof_gate": "Each candidate component stays planned until its own source path and merchant-lending proof exists.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["experience"], "description": "Owns borrower workflow, application status, offer review, funding and repayment visibility."},
                {"name": components["domain"], "description": "Owns credit facility, liquidity allocation, compliance gates, disbursement, and repayment."},
                {"name": components["validation"], "description": "Owns deterministic fixtures and regulated proof reports."},
            ],
            "related_workstreams": ["WS-00", "WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _merchant_lending_component_map_mermaid(),
        },
        {
            "slug": diagrams["domain_state"],
            "title": f"{title} Domain State Model",
            "kind": "stateDiagram",
            "summary": "Merchant facility state model covering draft, stale data, declined, compliance block, liquidity block, offer, funded, repayment due, and repaid.",
            "review_focus": "Use this view to catch unsafe transitions before source code chooses the state machine.",
            "operator_question": "Which facility state would be misleading without fixture or compliance proof?",
            "proof_gate": "Every promoted facility transition needs deterministic fixture proof.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["domain"], "description": "Owns facility states and valid transitions."},
                {"name": components["experience"], "description": "Renders application, blocked, funded, and repayment states to the merchant."},
                {"name": components["validation"], "description": "Exercises transitions through fixture replay."},
            ],
            "related_workstreams": ["WS-01", "WS-02", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _merchant_lending_state_mermaid(),
        },
        {
            "slug": diagrams["validation_release"],
            "title": f"{title} Validation And Release Topology",
            "kind": "flowchart",
            "summary": "Release-readiness map tying Shopify, compliance, liquidity, disbursement, repayment, negative live-access proof, and release decision together.",
            "review_focus": "Use this view to decide what must be proven before release 0.0.1 can claim merchant lending progress.",
            "operator_question": "Are the regulated acceptance gates strong enough for merchant lending and stablecoin funding?",
            "proof_gate": "Release movement is blocked until fixture proof, no-live-access guards, and unresolved-risk review agree.",
            "link_state": _GREENFIELD_FIRST_DRAFT_LINK_STATE,
            "components": [
                {"name": components["validation"], "description": "Owns fixture replay, negative live-access guards, and release evidence."},
                {"name": components["experience"], "description": "Supplies borrower-visible state proof."},
                {"name": components["domain"], "description": "Supplies facility, compliance, liquidity, disbursement, and repayment proof."},
            ],
            "related_workstreams": ["WS-00", "WS-03"],
            "evidence_tier": "user_intent",
            "mermaid_source": _merchant_lending_validation_mermaid(),
        },
    ]


def _overview_mermaid(domain_profile: GreenfieldDomainProfile) -> str:
    experience = _profile_label(domain_profile, "experience", fallback="Workflow Boundary")
    domain = _profile_label(domain_profile, "domain", fallback="State Contract")
    validation = _profile_label(domain_profile, "validation", fallback="Proof Harness")
    return (
        "flowchart LR\n"
        "  Intent[Operator<br/>intent]:::actor --> Choices[Direction choices<br/>user data runtime proof]:::decision\n"
        "  Choices --> ProjectTruth[Project intelligence<br/>accepted brief]:::planning\n"
        f"  ProjectTruth --> Experience[\"{experience}\"]:::service\n"
        f"  ProjectTruth --> Domain[\"{domain}\"]:::service\n"
        "  Experience --> Domain\n"
        f"  Domain --> Harness[\"{validation}\"]:::proof\n"
        "  Harness --> Review[Operator review<br/>accept gates before code]:::actor\n"
        "  Review --> CodeGate[Code gate<br/>plan paths tests rollback]:::gate\n"
        "  Evidence[Evidence boundary<br/>intent not source-backed]:::note -. constrains .-> ProjectTruth\n"
        "  Evidence -. constrains .-> CodeGate\n"
        "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef planning fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef decision fill:#eef2ff,stroke:#818cf8,color:#1e1b4b;\n"
        "  classDef gate fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
        "  classDef note fill:#f8fafc,stroke:#cbd5e1,color:#334155,stroke-dasharray: 3 3;\n"
    )


def _merchant_lending_overview_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Merchant[SMB merchant<br/>borrower]:::actor --> Portal[Merchant capital<br/>portal]:::portal\n"
        "  Portal --> Snapshot[Shopify snapshot<br/>fixture input]:::data\n"
        "  Snapshot --> Core[Credit liquidity<br/>core]:::core\n"
        "  Compliance[KYB AML sanctions<br/>fixture]:::risk --> Core\n"
        "  Liquidity[Stablecoin liquidity<br/>fixture]:::funding --> Core\n"
        "  Core --> Offer[Eligible declined<br/>or blocked state]:::decision\n"
        "  Offer --> Funding[Disbursement and<br/>repayment state]:::funding\n"
        "  Funding --> Proof[Lending proof<br/>harness]:::proof\n"
        "  Proof --> Review[Release review<br/>no live rails]:::gate\n"
        "  Custody[No custody keys<br/>or protocol calls]:::blocked -. blocks .-> Funding\n"
        "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef portal fill:#fff7df,stroke:#d7a93d,color:#52390a;\n"
        "  classDef data fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef core fill:#eef2ff,stroke:#818cf8,color:#1e1b4b;\n"
        "  classDef funding fill:#ecfdf5,stroke:#10b981,color:#064e3b;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef decision fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef gate fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
        "  classDef blocked fill:#f8fafc,stroke:#64748b,color:#334155,stroke-dasharray: 3 3;\n"
    )


def _slice_mermaid(domain_profile: GreenfieldDomainProfile) -> str:
    experience = _profile_label(domain_profile, "experience", fallback="Workflow")
    domain = _profile_label(domain_profile, "domain", fallback="State Contract")
    validation = _profile_label(domain_profile, "validation", fallback="Proof Harness")
    return (
        "sequenceDiagram\n"
        "  participant Operator as Operator\n"
        f"  participant Experience as {experience.replace('<br/>', ' ')}\n"
        f"  participant Domain as {domain.replace('<br/>', ' ')}\n"
        f"  participant Harness as {validation.replace('<br/>', ' ')}\n"
        "  Note over Operator,Harness: Project review and direction choices happen before source edits\n"
        "  Operator->>Experience: start first workflow\n"
        "  Experience->>Domain: execute command or query\n"
        "  Domain-->>Experience: validated state result\n"
        "  Note over Experience,Domain: Normal empty degraded and failure states must be explicit\n"
        "  Harness->>Experience: run behavior proof\n"
        "  Harness->>Domain: run contract proof\n"
        "  Harness-->>Operator: proof report and release gate evidence\n"
        "  Note over Harness,Operator: Proof is not accepted until behavior and contract evidence agree\n"
    )


def _merchant_lending_slice_mermaid() -> str:
    return (
        "sequenceDiagram\n"
        "  participant Merchant as Merchant Borrower\n"
        "  participant Portal as Merchant Capital Portal\n"
        "  participant Core as Credit Liquidity Core\n"
        "  participant Shopify as Shopify Snapshot Fixture\n"
        "  participant Compliance as Compliance Fixture\n"
        "  participant Liquidity as Stablecoin Liquidity Fixture\n"
        "  participant Harness as Lending Proof Harness\n"
        "  Merchant->>Portal: submit capital request and consent\n"
        "  Portal->>Core: evaluate facility request\n"
        "  Core->>Shopify: read sales freshness fixture\n"
        "  Core->>Compliance: check KYB AML sanctions state\n"
        "  Core->>Liquidity: check available stablecoin liquidity\n"
        "  Core-->>Portal: eligible declined stale or blocked state\n"
        "  Portal-->>Merchant: show offer funding or repayment state\n"
        "  Harness->>Core: replay disbursement and repayment events\n"
        "  Harness-->>Merchant: proof report uses fixture evidence only\n"
    )


def _component_map_mermaid(domain_profile: GreenfieldDomainProfile) -> str:
    experience = _profile_label(domain_profile, "experience", fallback="Workflow Boundary")
    domain = _profile_label(domain_profile, "domain", fallback="State Contract")
    validation = _profile_label(domain_profile, "validation", fallback="Proof Harness")
    return (
        "flowchart TB\n"
        "  Lens[Decision lens<br/>split by owner evidence risk gate]:::note\n"
        f"  subgraph experience[\"{experience}<br/>ownership\"]\n"
        "    Entry[First workflow<br/>entrypoint]:::ux\n"
        "    States[Visible normal empty<br/>and degraded states]:::ux\n"
        "  end\n"
        f"  subgraph domain[\"{domain}<br/>ownership\"]\n"
        "    Contract[Command query<br/>and event contract]:::core\n"
        "    Invariants[State invariants<br/>and rejection rules]:::core\n"
        "  end\n"
        f"  subgraph proof[\"{validation}<br/>ownership\"]\n"
        "    Fixtures[Deterministic<br/>fixtures]:::proof\n"
        "    Report[Release readiness<br/>report]:::proof\n"
        "  end\n"
        "  Entry --> Contract --> Invariants --> States\n"
        "  Fixtures --> Contract\n"
        "  Fixtures --> Entry\n"
        "  Fixtures --> Report\n"
        "  Report --> Lens\n"
        "  Lens -. review .-> experience\n"
        "  Lens -. review .-> domain\n"
        "  Lens -. review .-> proof\n"
        "  classDef ux fill:#fff7df,stroke:#d7a93d,color:#52390a;\n"
        "  classDef core fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef note fill:#f8fafc,stroke:#cbd5e1,color:#334155,stroke-dasharray: 3 3;\n"
    )


def _merchant_lending_component_map_mermaid() -> str:
    return (
        "flowchart TB\n"
        "  subgraph portal[Merchant capital<br/>portal]\n"
        "    Intake[Application intake<br/>and consent]:::portal\n"
        "    Visible[Funding status<br/>and repayment view]:::portal\n"
        "  end\n"
        "  subgraph core[Credit liquidity<br/>core]\n"
        "    Facility[Facility terms<br/>and eligibility]:::core\n"
        "    Rails[Disbursement and<br/>repayment invariants]:::core\n"
        "    Gates[KYB AML sanctions<br/>and no custody gates]:::risk\n"
        "  end\n"
        "  subgraph proof[Lending proof<br/>harness]\n"
        "    Fixtures[Shopify liquidity<br/>compliance fixtures]:::proof\n"
        "    Replay[Duplicate event<br/>replay report]:::proof\n"
        "  end\n"
        "  Intake --> Facility --> Gates --> Rails --> Visible\n"
        "  Fixtures --> Facility\n"
        "  Fixtures --> Gates\n"
        "  Fixtures --> Replay\n"
        "  Replay --> Rails\n"
        "  classDef portal fill:#fff7df,stroke:#d7a93d,color:#52390a;\n"
        "  classDef core fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef risk fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
    )


def _domain_state_mermaid(domain_profile: GreenfieldDomainProfile) -> str:
    domain = _profile_label(domain_profile, "domain", fallback="Domain")
    return (
        "stateDiagram-v2\n"
        "  [*] --> Draft\n"
        "  note right of Draft\n"
        "    Proposal state, not source proof\n"
        f"    {domain.replace('<br/>', ' ')} contract still needs implementation evidence\n"
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


def _merchant_lending_state_mermaid() -> str:
    return (
        "stateDiagram-v2\n"
        "  [*] --> DraftApplication\n"
        "  DraftApplication --> StaleData: Shopify snapshot stale\n"
        "  DraftApplication --> ComplianceBlocked: KYB AML blocked\n"
        "  DraftApplication --> Declined: eligibility fails\n"
        "  DraftApplication --> Eligible: eligible and compliant\n"
        "  Eligible --> LiquidityBlocked: stablecoin shortfall\n"
        "  Eligible --> OfferReady: liquidity available\n"
        "  OfferReady --> Funded: fixture disbursement accepted\n"
        "  Funded --> RepaymentDue: schedule opens\n"
        "  RepaymentDue --> Repaid: repayment replay accepted\n"
        "  RepaymentDue --> RepaymentBlocked: duplicate or invalid event\n"
        "  StaleData --> DraftApplication: fresh snapshot supplied\n"
        "  LiquidityBlocked --> Eligible: liquidity fixture refreshed\n"
        "  ComplianceBlocked --> DraftApplication: compliance proof supplied\n"
        "  Declined --> [*]\n"
        "  Repaid --> [*]\n"
        "  RepaymentBlocked --> [*]\n"
    )


def _validation_release_mermaid(domain_profile: GreenfieldDomainProfile) -> str:
    validation = _profile_label(domain_profile, "validation", fallback="Proof Harness")
    return (
        "flowchart LR\n"
        "  Plan[Technical plan<br/>for first workstream]:::planning --> Behavior[Behavior proof<br/>normal empty degraded]:::proof\n"
        "  Plan --> Contract[Contract proof<br/>state and invariants]:::proof\n"
        "  Choices[Accepted choices<br/>runtime data proof]:::gate --> Plan\n"
        f"  Behavior --> Harness[\"{validation}\"]:::proof\n"
        "  Contract --> Harness\n"
        "  Harness --> Evidence[Evidence bundle<br/>fixtures reports traces]:::proof\n"
        "  Evidence --> Decision[Release decision<br/>0.0.1 scope]:::release\n"
        "  Decision --> Handoff[Operator handoff<br/>next command and gates]:::release\n"
        "  Blocked[Blocked if risks<br/>or choices unresolved]:::blocked -. prevents .-> Decision\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef planning fill:#f1f5f9,stroke:#94a3b8,color:#1f2937;\n"
        "  classDef release fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef gate fill:#eef2ff,stroke:#818cf8,color:#1e1b4b;\n"
        "  classDef blocked fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
    )


def _profile_label(domain_profile: GreenfieldDomainProfile, role: str, *, fallback: str) -> str:
    profile = domain_profile.components.get(role)
    label = str(profile.label if profile else fallback).strip() or fallback
    words = label.replace("&", "and").replace("/", " ").split()
    if len(words) <= 3:
        return " ".join(words)
    midpoint = max(2, min(4, (len(words) + 1) // 2))
    return " ".join(words[:midpoint]) + "<br/>" + " ".join(words[midpoint:])


def _merchant_lending_validation_mermaid() -> str:
    return (
        "flowchart LR\n"
        "  Shopify[Shopify snapshot<br/>freshness fixtures]:::fixture --> Matrix[Scenario matrix<br/>merchant lending]:::proof\n"
        "  Compliance[KYB AML sanctions<br/>fault fixtures]:::fixture --> Matrix\n"
        "  Liquidity[Stablecoin liquidity<br/>shortfall fixtures]:::fixture --> Matrix\n"
        "  Ledger[Disbursement repayment<br/>replay fixtures]:::fixture --> Matrix\n"
        "  Matrix --> Guards[No live Shopify<br/>or DeFi access guards]:::blocked\n"
        "  Matrix --> Evidence[Eligible declined stale<br/>blocked funded repaid]:::proof\n"
        "  Guards --> Decision[Release decision<br/>0.0.1 merchant slice]:::release\n"
        "  Evidence --> Decision\n"
        "  Risk[Unresolved custody<br/>or lending review]:::risk -. blocks .-> Decision\n"
        "  classDef fixture fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
        "  classDef proof fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
        "  classDef blocked fill:#fee2e2,stroke:#dc2626,color:#5f1212;\n"
        "  classDef release fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
        "  classDef risk fill:#f8fafc,stroke:#64748b,color:#334155,stroke-dasharray: 3 3;\n"
    )


__all__ = ["build_apply_ready_proposal"]
