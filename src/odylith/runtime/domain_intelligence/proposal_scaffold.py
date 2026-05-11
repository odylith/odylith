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
from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings
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
    artifact_slug = _artifact_slug(slug=slug, title=title, domain_profile=domain_profile, robot_swarm_logistics=robot_swarm_logistics)
    components = _component_ids(slug=artifact_slug, domain_profile=domain_profile, robot_swarm_logistics=robot_swarm_logistics)
    diagrams = _diagram_ids(slug=artifact_slug)
    intent = _intent(prompt=prompt, title=title, slug=artifact_slug, robot_swarm_logistics=robot_swarm_logistics)
    assumptions = _base_assumptions()
    open_questions = _base_open_questions()
    risks = _base_risks(title=title, domain_profile=domain_profile)
    security_compliance = _base_security_compliance(title, domain_profile=domain_profile)
    validation_strategy = _base_validation_strategy()
    project_brief = build_project_brief(
        prompt=prompt,
        title=title,
        slug=artifact_slug,
        domain_profile=domain_profile,
        release_selector=selector,
    )
    program = _program(title=title, components=components, domain_profile=domain_profile)
    release_plan = _release_plan(
        selector=selector,
        slug=artifact_slug,
        experience_component=components["experience"],
        domain_component=components["domain"],
        domain_profile=domain_profile,
    )
    component_rows = _components(components, diagrams=diagrams, domain_profile=domain_profile)
    diagram_rows = _diagrams(components=components, diagrams=diagrams, domain_profile=domain_profile)
    project_intelligence = build_project_intelligence(
        prompt=prompt,
        title=title,
        slug=artifact_slug,
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
    proposal = attach_project_intelligence_bindings(proposal)
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


def _artifact_slug(
    *,
    slug: str,
    title: str,
    domain_profile: GreenfieldDomainProfile,
    robot_swarm_logistics: bool,
) -> str:
    if robot_swarm_logistics:
        return "robot-swarm-logistics"
    family_slugs = {
        "capital_merchant_lending": "merchant-capital",
        "defi_risk": "defi-risk-sentinel",
        "commerce": "checkout-commerce",
        "clinical_trial_matching": "clinical-trial-matching",
        "legal_intake": "legal-intake",
        "bioinformatics_variant_pipeline": "variant-analysis-pipeline",
    }
    family_slug = family_slugs.get(domain_profile.family, "")
    if family_slug:
        return family_slug
    compact = slugify(_compact_project_name(title)) or slugify(slug)
    tokens = [token for token in compact.split("-") if token]
    return "-".join(tokens[:5]) or "greenfield-project"


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
                    "deterministic replay proof, and refreshed release evidence before release promotion."
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
    if domain_profile.family == "capital_merchant_lending":
        return [
            {
                "id": "R1",
                "risk_class": "credit_and_offer_integrity",
                "severity": "high",
                "trigger": "merchant source signals, eligibility, offer terms, approval owner, or repayment model are unclear",
                "early_warning": "offer or funding language appears before policy trace, manual approval, and repayment evidence exist",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Merchant-capital implementation can misstate eligibility, amount, pricing, repayment terms, or approval "
                    "if underwriting evidence and policy trace are not bound before source edits."
                ),
                "mitigation": (
                    "Keep the first wave fixture-backed; require source-signal provenance, offer trace, manual risk approval, "
                    "manual treasury approval, repayment state, and ledger reconciliation before release promotion."
                ),
            },
            {
                "id": "R2",
                "risk_class": "treasury_compliance_boundary",
                "severity": "high",
                "trigger": "lender of record, loss ownership, custody, settlement rail, repayment rail, or protocol exposure is unresolved",
                "early_warning": "stablecoin, DeFi, or payout text appears without custody, treasury, compliance, and reconciliation proof",
                "evidence_tier": "odylith_assumption",
                "statement": (
                    "Funding movement can imply live lending, custody, or protocol safety before lender-of-record, "
                    "loss ownership, settlement, repayment, and compliance posture are decided."
                ),
                "mitigation": (
                    "Treat live stablecoin, bank, and DeFi movement as out of first-release scope unless operator-reviewed "
                    "custody, treasury, compliance, and ledger proof gates are explicit."
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
                "proof command, and refreshed release evidence."
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
    if domain_profile.family == "capital_merchant_lending":
        return {
            "domain": (
                f"{title} is a merchant-capital proposal with sensitive merchant performance, underwriting, offer, "
                "approval, funding, repayment, stablecoin or fiat settlement, and ledger evidence boundaries."
            ),
            "security": (
                "Security posture covers merchant data consent and provenance, KYB/AML input handling, approval audit, "
                "treasury controls, custody exclusion, replayable repayment evidence, and secret-free fixtures."
            ),
            "policy": (
                "Policy posture keeps lender of record, credit loss ownership, disclosures, jurisdiction, custody, "
                "settlement rail, repayment rail, and protocol exposure explicit before source edits."
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
        "The accepted product brief and release evidence must show the first release lane, active wave, start workstream, and proof gates after apply.",
    ]


def _program(*, title: str, components: Mapping[str, str], domain_profile: GreenfieldDomainProfile) -> dict[str, Any]:
    return {
        "name": title,
        "waves": [
            {
                "wave_id": "W1",
                "label": "First product slice",
                "goal": "Prove the smallest coherent product workflow with source-backed validation.",
                "validation_gate": (
                    "The first workstream has a technical plan, behavior proof, refreshed release evidence, "
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
    return {
        "selector": selector,
        "label": greenfield_programs.compact_release_target_label(selector),
        "provisional_release_id": f"release-{slug}-{slugify(selector)}",
        "strategy": "Promote only after the first product slice has source-backed tests and refreshed release evidence.",
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
            "Release evidence refreshes cleanly after source changes.",
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
    terms = _umbrella_backlog_terms(title=title, selector=selector, domain_profile=domain_profile)
    return {
        "id": "WS-00",
        "title": terms["title"],
        "workstream_type": "umbrella",
        "problem": terms["problem"],
        "customer": terms["customer"],
        "opportunity": terms["opportunity"],
        "product_view": terms["product_view"],
        "recommended_first_slice": terms["recommended_first_slice"],
        "success_metrics": terms["success_metrics"],
        "component_focus": [components["experience"], components["domain"], components["validation"]],
        "related_diagram_slugs": [
            diagrams["overview"],
            diagrams["slice"],
            diagrams["component_map"],
            diagrams["domain_state"],
            diagrams["validation_release"],
        ],
        "dependencies": terms["dependencies"],
        "interfaces": terms["interfaces"],
        "validation": terms["validation"],
        "domain_risk": terms["domain_risk"],
        "security_posture": terms["security_posture"],
        "priority": "P1",
        "sizing": "L",
        "complexity": "High",
        "evidence_tier": "user_intent",
    }


def _umbrella_backlog_terms(
    *,
    title: str,
    selector: str,
    domain_profile: GreenfieldDomainProfile,
) -> dict[str, Any]:
    experience = domain_profile.components["experience"]
    domain = domain_profile.components["domain"]
    validation = domain_profile.components["validation"]
    component_sentence = f"{experience.label}, {domain.label}, and {validation.label}"
    if domain_profile.family == "capital_merchant_lending":
        return {
            "title": "Shape merchant capital funding program",
            "problem": (
                "Merchants need a trustworthy path from verified store performance to a funding offer, manual approval, "
                "funding status, repayment record, and ledger reconciliation. Without that first path, the product can imply "
                "live lending, stablecoin custody, DeFi protocol safety, or repayment obligations before risk, treasury, "
                "compliance, and loss ownership are decided."
            ),
            "customer": (
                "Merchants seeking working capital, plus risk, treasury, compliance, and product reviewers who must know "
                "which funding claims are real before the first build starts."
            ),
            "opportunity": (
                "Prove one merchant funding journey: request capital, verify store signals, review eligibility and terms, "
                "require manual approval, show funding status, record repayment, and reconcile the ledger before any live "
                "stablecoin or protocol movement."
            ),
            "product_view": (
                f"The first product shape is a controlled merchant-capital system: {experience.label} owns the request and "
                f"offer experience, {domain.label} owns eligibility, approval, facility, and repayment state, and "
                f"{validation.label} proves funding, repayment, and ledger evidence. Live custody and protocol routing stay "
                "outside the first release until ownership and proof are explicit."
            ),
            "recommended_first_slice": (
                "Prove one fixture-backed merchant funding request from store-signal readiness through offer review, manual "
                "risk and treasury approval, funding status, repayment event, and ledger reconciliation."
            ),
            "success_metrics": [
                "A merchant can understand request status, eligibility, offer terms, approval state, funding status, and repayment state without hidden lender or custody assumptions.",
                "Risk, treasury, compliance, lender-of-record, custody, loss-owner, and repayment assumptions are visible before release promotion.",
                "The first release proves the funding journey with fixtures and ledger evidence, not live stablecoin custody, DeFi deposits, or production lending decisions.",
            ],
            "dependencies": [
                f"First-path implementation depends on {component_sentence} agreeing on merchant state, approval ownership, and proof boundaries.",
            ],
            "interfaces": [
                "The accepted program exposes merchant request, store-signal, offer, approval, facility, repayment, and reconciliation states as the first product contract.",
            ],
            "validation": [
                "Greenfield validation must prove the merchant funding story, component boundaries, architecture views, release target, and proof gates agree before coding starts.",
            ],
            "domain_risk": (
                "A capital product can create credit, treasury, custody, compliance, and merchant-trust risk if offer, approval, funding, repayment, and ledger claims are vague."
            ),
            "security_posture": (
                "Merchant data provenance, consent, KYB/AML inputs, approval audit, treasury controls, custody exclusion, and secret-free fixtures remain explicit until source-backed proof exists."
            ),
        }
    if domain_profile.family == "defi_risk":
        return {
            "title": "Shape DeFi risk sentinel program",
            "problem": (
                "Risk analysts need exposure, freshness, confidence, and alert state they can trust before the product touches live-chain providers. "
                "Without that path, the product can imply custody, trading, financial advice, or precise risk scoring from stale or incomplete data."
            ),
            "customer": "Risk analysts, protocol operators, and reviewers who need non-custodial risk posture before live-provider integration.",
            "opportunity": "Prove one analyst watchlist and alert journey with fixture-backed exposure snapshots, stale-data handling, acknowledgement, and audit evidence.",
            "product_view": (
                f"The first shape ties {component_sentence}: the console shows risk posture, the signal engine owns exposure and alert semantics, "
                "and the replay harness proves stale, missing, unsupported, and acknowledged states without custody or live execution."
            ),
            "recommended_first_slice": "Prove one monitored subject from watchlist entry to alert triage, degraded-data disclosure, acknowledgement, and replay proof.",
            "success_metrics": [
                "Risk cards disclose freshness, confidence, provenance, and degraded-data state.",
                "No first-release path requires custody, signing, trading, live RPC, or production financial-advice claims.",
                "Scenario replay proves normal, stale, missing, unsupported-chain, and acknowledgement states.",
            ],
            "dependencies": [f"The first path depends on {component_sentence} sharing exposure, alert, confidence, and proof semantics."],
            "interfaces": ["The accepted program exposes risk subject, exposure snapshot, alert state, acknowledgement, and replay-report contracts."],
            "validation": ["Validation must prove watchlist, risk signal, degraded-state, acknowledgement, and replay evidence agree before source work starts."],
            "domain_risk": "Weak freshness, confidence, custody, or no-advice boundaries can make incomplete data look actionable.",
            "security_posture": "No custody, no signing, no trading, live-provider exclusion, audit trail, and fixture provenance remain explicit until source-backed proof exists.",
        }
    if domain_profile.family == "clinical_trial_matching":
        return {
            "title": "Shape patient trial matching program",
            "problem": (
                "Oncology coordinators need one safe patient-to-trial review path that separates intake facts, consent, "
                "eligibility criteria, exclusion reasons, manual review, and match evidence. Without that path, the product "
                "can look like a clinical recommendation before protocol, consent, and safety proof exist."
            ),
            "customer": "Oncology coordinators, patient-review teams, trial operations staff, and clinical reviewers who need eligibility evidence before outreach or care decisions.",
            "opportunity": "Prove one patient matching journey with fixture-backed intake, consent status, protocol criteria, eligibility gaps, manual review, and outcome evidence.",
            "product_view": (
                f"The first shape ties {component_sentence}: the workbench owns coordinator review, the protocol engine owns eligibility semantics, "
                "and the proof harness validates consent, exclusion, stale-protocol, and manual-review states without production patient data."
            ),
            "recommended_first_slice": "Prove one oncology patient profile from intake through consent check, protocol eligibility review, match explanation, manual review, and proof report.",
            "success_metrics": [
                "A coordinator can see why a patient is eligible, ineligible, blocked by consent, missing data, or waiting for manual review.",
                "Protocol criteria, consent state, exclusion reasons, and review disposition are explicit before any outreach or clinical recommendation claim.",
                "The first release uses fixtures and review evidence, not production patient data, EHR access, or automated clinical approval.",
            ],
            "dependencies": [f"The first path depends on {component_sentence} sharing patient, protocol, consent, eligibility, and proof semantics."],
            "interfaces": ["The accepted program exposes patient intake, consent, protocol criteria, eligibility result, exclusion reason, and manual-review contracts."],
            "validation": ["Validation must prove eligible, ineligible, missing-consent, missing-data, stale-protocol, and manual-review scenarios before source work widens."],
            "domain_risk": "Clinical matching can become unsafe if consent, protocol criteria, eligibility confidence, or manual review ownership are vague.",
            "security_posture": "Patient privacy, consent boundaries, fixture-only health data, protocol provenance, and clinical-approval exclusion remain explicit until source-backed proof exists.",
        }
    if domain_profile.family == "legal_intake":
        return {
            "title": "Shape immigration intake program",
            "problem": (
                "Clients and attorneys need one confidential intake path that captures client facts, document gaps, consent, "
                "case-type risk, attorney handoff, and review evidence without implying legal advice or filing readiness."
            ),
            "customer": "Immigration clients, intake operators, attorneys, and confidentiality reviewers who need complete intake evidence before advice or filing decisions.",
            "opportunity": "Prove one client intake journey with fixture-backed profile capture, document checklist, consent gate, urgency or risk flag, and attorney-review handoff.",
            "product_view": (
                f"The first shape ties {component_sentence}: the workspace owns client intake, the case core owns document and eligibility semantics, "
                "and the proof harness validates privacy, consent, missing-document, conflict, and attorney-review states."
            ),
            "recommended_first_slice": "Prove one client case from intake through consent, document completeness, risk flagging, attorney review, and confidential proof report.",
            "success_metrics": [
                "A client or intake operator can see required documents, missing items, consent state, urgency, and attorney-review status.",
                "The product never presents legal advice, filing readiness, or representation acceptance before attorney review.",
                "The first release proves complete, missing-document, urgent-deadline, consent-blocked, conflict, and attorney-review paths with fixtures.",
            ],
            "dependencies": [f"The first path depends on {component_sentence} sharing client, document, consent, risk, and review semantics."],
            "interfaces": ["The accepted program exposes client intake, document inventory, consent state, case-type risk, missing-item, and attorney-review contracts."],
            "validation": ["Validation must prove complete intake, missing documents, urgent deadline, consent block, conflict flag, and attorney-review scenarios before source work widens."],
            "domain_risk": "Legal intake can create confidentiality, unauthorized-advice, or filing-readiness risk if consent, document state, or attorney authority are vague.",
            "security_posture": "PII handling, confidentiality, consent, conflict checks, fixture-only client data, and legal-advice exclusion remain explicit until source-backed proof exists.",
        }
    if domain_profile.family == "bioinformatics_variant_pipeline":
        return {
            "title": "Shape variant analysis pipeline program",
            "problem": (
                "Clinical genomics teams need one reproducible sample-to-variant review path that separates sample intake, "
                "QC, reference data, VCF output, annotation, analyst review, and proof of rerun stability."
            ),
            "customer": "Bioinformatics analysts, clinical genomics reviewers, pipeline maintainers, and quality owners who need reproducible variant evidence before interpretation claims.",
            "opportunity": "Prove one sample analysis journey with pinned fixtures for QC, reference selection, VCF generation, malformed input, annotation, and reproducibility evidence.",
            "product_view": (
                f"The first shape ties {component_sentence}: the workbench owns analyst review, the analysis core owns sample and variant semantics, "
                "and the proof harness validates QC failure, malformed VCF, reference mismatch, and deterministic rerun evidence."
            ),
            "recommended_first_slice": "Prove one sample fixture from intake through QC, variant output, annotation readiness, analyst review, and reproducibility report.",
            "success_metrics": [
                "An analyst can see sample status, QC outcome, variant output, reference provenance, failure reason, and review readiness.",
                "Reference, QC, VCF, annotation, and provenance claims are reproducible before clinical interpretation or production sample claims.",
                "The first release proves passing sample, failed QC, empty variants, malformed VCF, reference mismatch, and deterministic rerun paths.",
            ],
            "dependencies": [f"The first path depends on {component_sentence} sharing sample, QC, variant, reference, annotation, and proof semantics."],
            "interfaces": ["The accepted program exposes sample metadata, QC metrics, reference identity, VCF output, annotation state, and reproducibility-report contracts."],
            "validation": ["Validation must prove passing sample, failed QC, empty variants, malformed VCF, reference mismatch, and deterministic rerun scenarios before source work widens."],
            "domain_risk": "Variant analysis can become invalid or irreproducible if sample identity, QC thresholds, reference data, VCF semantics, or provenance are vague.",
            "security_posture": "Fixture-only samples, reference provenance, PHI exclusion, reproducibility, audit, and clinical-interpretation exclusion remain explicit until source-backed proof exists.",
        }
    if domain_profile.family == "commerce":
        return {
            "title": "Shape checkout recovery program",
            "problem": (
                "Shoppers need checkout to preserve cart, payment, retry, and order state without duplicate orders or misleading success messages. "
                "Without a first recovery path, the build can look like a storefront while payment failure and order truth remain unproven."
            ),
            "customer": "Shoppers, commerce operators, and reviewers who need checkout recovery proof before production payment claims.",
            "opportunity": "Prove one browse-to-checkout journey with empty, failed-payment, retry, callback replay, and completion states.",
            "product_view": (
                f"The first shape ties {component_sentence}: the storefront owns visible shopper state, the checkout core owns order and payment transitions, "
                "and the proof harness validates recovery without production credentials."
            ),
            "recommended_first_slice": "Prove one checkout path from browse to cart, checkout handoff, failed payment, retry, and completed order draft.",
            "success_metrics": [
                "Checkout proof shows happy path, empty cart, failed payment, retry, and callback replay.",
                "Order draft creation is idempotent under repeated checkout and provider callback duplication.",
                "No first release claims production payment readiness or live fulfillment.",
            ],
            "dependencies": [f"The first path depends on {component_sentence} sharing cart, order, payment, recovery, and proof semantics."],
            "interfaces": ["The accepted program exposes browse, cart-entry, checkout-entry, payment-result, retry, and order-status contracts."],
            "validation": ["Validation must prove visible checkout states, idempotent order handling, payment recovery, and release evidence before source work starts."],
            "domain_risk": "Payment, order, inventory, and recovery state can diverge if checkout proof is vague.",
            "security_posture": "Session, payment handoff, idempotency, callback replay, abuse control, accessibility, and secret-free sandbox posture remain explicit until source-backed proof exists.",
        }
    compact = _compact_project_name(title)
    return {
        "title": f"Shape {compact} program",
        "problem": (
            f"{compact} needs one credible first path before implementation starts: who it serves, what state changes, "
            "which boundaries own the work, and what proof makes the first slice real."
        ),
        "customer": "The first users and operators named by the proposal, plus reviewers and builders who need a coherent product boundary before code starts.",
        "opportunity": "Turn the initial intent into a concrete first journey, named ownership boundaries, topology views, release target, and validation gates.",
        "product_view": (
            f"The first shape ties {component_sentence}: each boundary owns a different part of the journey, and proof remains separate from assumptions until source exists."
        ),
        "recommended_first_slice": "Prove the smallest complete journey from actor need to verified outcome before widening scope.",
        "success_metrics": [
            "The first user, state object, boundary owners, topology views, and proof gates are explicit before source work starts.",
            "Components and diagrams agree on the same first path and do not repeat the whole project prompt.",
            f"Release {selector} promotes only after the first path has source-backed validation.",
        ],
        "dependencies": [f"The first path depends on {component_sentence} agreeing on ownership, interfaces, and proof obligations."],
        "interfaces": ["The accepted program exposes the first actor need, state object, handoff, evidence, and outcome contracts."],
        "validation": ["Greenfield validation must prove the product story, components, topology, release target, and proof gates agree before coding starts."],
        "domain_risk": "Implementation can become generic or misleading if the first user, state object, owner, risk, and proof are not explicit.",
        "security_posture": "Access, data sensitivity, privacy, audit, degraded behavior, and recovery posture remain explicit until source-backed proof exists.",
    }


def _compact_project_name(title: str) -> str:
    cleaned = " ".join(str(title or "").replace("_", " ").split()).strip()
    for suffix in (" Application", " Platform", " System", " App", " Product"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned or "project"


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
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
    domain_profile: GreenfieldDomainProfile,
) -> list[dict[str, Any]]:
    return [
        {
            "slug": diagrams["overview"],
            "title": "System Overview",
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
            "title": "First Slice Flow",
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
            "title": "Component Ownership Map",
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
            "title": "Domain State Model",
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
            "title": "Validation And Release Topology",
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


def _overview_mermaid(domain_profile: GreenfieldDomainProfile) -> str:
    experience = _profile_label(domain_profile, "experience", fallback="Workflow Boundary")
    domain = _profile_label(domain_profile, "domain", fallback="State Contract")
    validation = _profile_label(domain_profile, "validation", fallback="Proof Harness")
    return (
        "flowchart LR\n"
        "  Intent[Operator<br/>intent]:::actor --> Choices[Direction choices<br/>user data runtime proof]:::decision\n"
        "  Choices --> AcceptedBrief[Accepted product<br/>brief]:::planning\n"
        f"  AcceptedBrief --> Experience[\"{experience}\"]:::service\n"
        f"  AcceptedBrief --> Domain[\"{domain}\"]:::service\n"
        "  Experience --> Domain\n"
        f"  Domain --> Harness[\"{validation}\"]:::proof\n"
        "  Harness --> Review[Operator review<br/>accept gates before code]:::actor\n"
        "  Review --> CodeGate[Code gate<br/>plan paths tests rollback]:::gate\n"
        "  Evidence[Evidence boundary<br/>intent not source-backed]:::note -. constrains .-> AcceptedBrief\n"
        "  Evidence -. constrains .-> CodeGate\n"
        "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef planning fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;\n"
        "  classDef decision fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
        "  classDef gate fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
        "  classDef note fill:#FBFDFF,stroke:#D8E5F4,color:#475569,stroke-dasharray: 3 3;\n"
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
        "  classDef ux fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef core fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef note fill:#FBFDFF,stroke:#D8E5F4,color:#475569,stroke-dasharray: 3 3;\n"
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
        "  classDef proof fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;\n"
        "  classDef planning fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;\n"
        "  classDef release fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
        "  classDef gate fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
        "  classDef blocked fill:#FFF8E6,stroke:#F6D98B,color:#17233A;\n"
    )


def _profile_label(domain_profile: GreenfieldDomainProfile, role: str, *, fallback: str) -> str:
    profile = domain_profile.components.get(role)
    label = str(profile.label if profile else fallback).strip() or fallback
    words = label.replace("&", "and").replace("/", " ").split()
    if len(words) <= 3:
        return " ".join(words)
    midpoint = max(2, min(4, (len(words) + 1) // 2))
    return " ".join(words[:midpoint]) + "<br/>" + " ".join(words[midpoint:])


__all__ = ["build_apply_ready_proposal"]
