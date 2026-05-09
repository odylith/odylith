"""Project-level domain intelligence for greenfield proposals.

Greenfield workstreams already carry detailed domain intelligence, but the
project itself also needs a product-requirements surface before source work starts.
This module builds that project object from the canonical proposal inputs so
CLI text, JSON, and applied project records all share the same project-first
truth.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.analysis_engine.types import slugify
from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile
from odylith.runtime.domain_intelligence.greenfield_domain_profile import infer_greenfield_domain_profile
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


PROJECT_INTELLIGENCE_SCHEMA_VERSION = "odylith.greenfield.project_intelligence.v1"
PROJECT_INTELLIGENCE_SECTION_TITLE = "Project Intelligence"

PROJECT_INTELLIGENCE_LAYERS: tuple[str, ...] = (
    "intent",
    "scope",
    "ontology",
    "state",
    "operators",
    "constraints",
    "source_of_truth_map",
    "evidence",
    "decisions",
    "assumptions",
    "topology",
    "invariants",
    "risks",
    "validation_obligations",
    "artifacts",
    "owners",
    "execution_memory",
    "metrics",
    "change_model",
    "invalidation_rules",
    "conflict_model",
    "transfer_priors",
)

_LAYER_LABELS = {
    "intent": "Intent",
    "scope": "Scope",
    "ontology": "Ontology",
    "state": "State",
    "operators": "Operators",
    "constraints": "Constraints",
    "source_of_truth_map": "Source Of Truth",
    "evidence": "Evidence",
    "decisions": "Decisions",
    "assumptions": "Assumptions",
    "topology": "Topology",
    "invariants": "Invariants",
    "risks": "Risks",
    "validation_obligations": "Validation",
    "artifacts": "Artifacts",
    "owners": "Owners",
    "execution_memory": "Memory",
    "metrics": "Metrics",
    "change_model": "Change",
    "invalidation_rules": "Invalidation Rules",
    "conflict_model": "Conflicts",
    "transfer_priors": "Transfer",
}

_PREVIEW_LAYER_LIMITS = {
    "intent": 6,
    "scope": 4,
    "ontology": 5,
    "state": 5,
    "operators": 5,
    "constraints": 4,
    "source_of_truth_map": 4,
    "evidence": 4,
    "decisions": 4,
    "assumptions": 3,
    "topology": 5,
    "invariants": 4,
    "risks": 4,
    "validation_obligations": 4,
    "artifacts": 4,
    "owners": 4,
    "execution_memory": 4,
    "metrics": 4,
    "change_model": 4,
    "invalidation_rules": 4,
    "conflict_model": 3,
    "transfer_priors": 3,
}


def build_project_intelligence(
    *,
    prompt: str,
    title: str,
    slug: str,
    release_selector: str,
    domain_profile: GreenfieldDomainProfile | None = None,
    project_brief: Mapping[str, Any] | None = None,
    program: Mapping[str, Any] | None = None,
    release_plan: Mapping[str, Any] | None = None,
    components: Sequence[Any] = (),
    diagrams: Sequence[Any] = (),
    observed_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the project-first intelligence object for a greenfield proposal."""

    profile = domain_profile or infer_greenfield_domain_profile(prompt=prompt, title=title, slug=slug)
    family = _family_terms(profile=profile, title=title)
    component_refs = _component_refs(components)
    diagram_refs = _diagram_refs(diagrams)
    wave_refs = _wave_refs(program or {})
    release = clean_text(release_selector) or clean_text((release_plan or {}).get("selector")) or "0.0.1"
    source_posture = clean_text((observed_source or {}).get("source_posture")) or "unknown"
    choice_refs = _choice_refs(project_brief or {})
    first_wave = wave_refs[0] if wave_refs else "first product slice"
    component_spine = ", ".join(component_refs[:4]) or "candidate components"
    diagram_spine = ", ".join(diagram_refs[:5]) or "architecture views"

    return {
        "schema_version": PROJECT_INTELLIGENCE_SCHEMA_VERSION,
        "purpose": (
            f"Make {title} a concrete product program before implementation starts: the project object captures intent, "
            "domain language, allowed change, invariants, proof, memory, and customization choices in one place."
        ),
        "coding_posture": (
            "Do not start coding from the proposal closeout. First review direction options, accept or revise the "
            "project shape, write accepted project records, then author a technical plan for the chosen first child workstream."
        ),
        "control_surface_summary": [
            f"What exists: {source_posture} repo evidence plus user-intent project truth for `{title}`.",
            "What may change: direction choices, runtime, first user, data boundary, proof bar, release ambition, and wave order.",
            "What must remain invariant: no source-backed claim without code paths, tests, component owner, and refreshed project records.",
            "What counts as proof: repo-native tests or fixtures, rendered architecture diagrams, validated component/workstream records, and explicit human decisions.",
            "What prior experience changes next action: avoid generic component specs, title-only workstreams, and premature coding handoff.",
        ],
        "customization_flow": _customization_flow(choice_refs=choice_refs, release=release),
        "intent": [
            f"Project objective: {family['project_objective']}",
            f"User or stakeholder outcome: {family['stakeholder_outcome']}",
            f"Success condition: {first_wave} produces source-backed proof without widening beyond release `{release}`.",
            f"Why this matters now: {title} has no trustworthy implementation path until {component_spine} and {diagram_spine} agree.",
            f"What breaks if it fails: {family['failure_mode']}",
            f"Non-goals: {family['non_goals']}",
        ],
        "scope": [
            f"In scope before coding: project spine, domain ontology, candidate components, architecture diagrams, waves, release target, assumptions, risks, and proof gates.",
            "Out of scope before coding: source-backed runtime claims, production readiness, live integrations, and broad implementation plans not tied to a child workstream.",
            f"First release boundary: release `{release}` targets the first product wave only until proof promotes later work.",
            "Customization boundary: the operator may change runtime, compliance posture, user role, data boundary, proof level, or first-release ambition before apply.",
        ],
        "ontology": [
            *family["ontology"],
            "Project parent: umbrella workstream that owns program intent, wave order, release target, and cross-slice proof sequencing.",
            "Child workstream: implementation candidate with a single first slice, component focus, dependencies, interfaces, and validation obligations.",
            "Candidate component: planned ownership boundary with user_intent evidence; not a source-backed module until code and proof land.",
            "Architecture view: product-topology claim that must link back to workstreams and components before it can guide implementation.",
            "Readiness gate: condition that must pass before the next transformation is allowed.",
        ],
        "state": [
            f"Current state: {source_posture}; project truth is user_intent plus labeled assumptions, not implementation evidence.",
            f"Desired state: accepted proposal with parent workstream, {first_wave}, release `{release}`, component specs, diagrams, and proof gates.",
            "Intermediate states: proposed -> customized -> confirmed -> applied -> planned -> source_backed -> release_gated.",
            "Blocked state: unresolved operator choice changes architecture, compliance, proof, data boundary, or first user.",
            "Invalid state: coding starts while direction choices, component boundaries, or proof obligations are still ambiguous.",
        ],
        "operators": [
            "Customize direction: precondition is proposal review; postcondition is updated prompt or canonical JSON before any write.",
            "Apply accepted project: precondition is explicit confirmation and passing validation; postcondition is accepted project, component, architecture, release, assumption, risk, and validation records written together.",
            "Open first plan: precondition is applied project truth and accepted readiness gates; postcondition is a child-workstream technical plan with source paths and proof commands.",
            "Promote source evidence: precondition is implementation plus repo-native tests; postcondition is project, component, architecture, and release records refreshed from source-backed proof.",
            "Split scope: precondition is different owner, evidence, risk, or release gate; postcondition is a new child workstream linked into topology.",
        ],
        "constraints": [
            *family["constraints"],
            "Keep proposal creation provider-free and deterministic; host reasoning may critique or customize but does not hand-reconstruct canonical proposal objects.",
            "Do not mark candidate components active until source paths and proof commands exist.",
            "Do not target every child workstream to release 0.0.1 unless the first wave truly owns them.",
            "Do not let generated views outrank source files when conflicts appear.",
        ],
        "source_of_truth_map": [
            "Project intelligence: canonical project-first requirements in proposal JSON and parent project workstream.",
            "Project brief: operator-facing choices, checkpoints, host-independent paths, and coding-readiness gates.",
            "Workstream source: canonical backlog intent, domain intelligence, dependencies, risks, and success metrics.",
            "Component specs: canonical component identity, ownership, interfaces, collaborators, failure modes, and proof.",
            "Architecture diagrams: canonical topology, sequence, state/data, validation, operational-risk, and release views.",
            "Progress view: derived live posture; useful for navigation, not source truth when stale.",
        ],
        "evidence": [
            "Observed source evidence comes only from the repo inventory.",
            "User intent comes from the operator prompt and explicit follow-up choices.",
            "Default assumptions must remain labeled until confirmed or source-backed.",
            "Strong proof means repository-native tests, fixture replays, browser/API/simulation proof where relevant, and rendered architecture diagrams plus validation passes.",
            "Weak proof means proposal prose, host summaries, generated views, or unlabeled assumptions.",
        ],
        "decisions": [
            f"Default decision: hold coding until {title} has an accepted project shape and readiness gates.",
            f"Release decision: keep the first selector as `{release}` unless the operator explicitly changes it.",
            "Architecture decision: start with named ownership boundaries before choosing storage, deployment, or live providers.",
            "Rejected path: jump from greenfield prompt straight to source files without project topology and proof posture.",
            "Reversal criteria: operator changes primary user, runtime, compliance posture, data boundary, or proof threshold.",
        ],
        "assumptions": [
            *family["assumptions"],
            "The first release should prove a narrow vertical slice before broad platform architecture claims.",
            "The operator wants customization choices visible outside any specific host model UI.",
            "The first technical plan should be authored after apply, not embedded as unreviewed code instructions in the proposal.",
        ],
        "topology": [
            f"Program topology: parent workstream -> {', '.join(wave_refs[:3]) or 'first wave'} -> child workstreams -> components -> diagrams -> validation.",
            f"Component topology: planned ownership currently spans {component_spine}; each component must keep its own boundary, dependencies, interfaces, and proof.",
            f"Diagram topology: architecture review currently spans {diagram_spine}; each view must remain traceable to workstreams and component owners.",
            "Proof topology: prompt -> proposal JSON -> validation -> accepted writes -> technical plan -> source paths -> repo-native proof -> refreshed project records.",
            "Release topology: release target points at first-wave workstreams and should not imply later-wave readiness.",
        ],
        "invariants": [
            "Every project claim keeps its evidence tier visible: observed_source, user_intent, odylith_assumption, or later source_backed.",
            "Every child workstream must name a first slice, components, diagrams, dependencies, interfaces, and validation.",
            "Every component spec stays component-specific instead of repeating the whole project narrative.",
            "Every architecture diagram must be purposeful, traceable, and rendered from Mermaid source.",
            "Every release promotion requires proof, not proposal confidence.",
        ],
        "risks": [
            *family["risks"],
            "UX risk: a one-command create path can feel like permission to code unless the handoff makes project review and readiness gates explicit.",
            "Governance risk: deep project text can become sludge if it is repetitive, not tied to topology, or not enforced by validation.",
            "Agent risk: future sessions can skip prior choices if project intelligence is not written into parent project truth.",
        ],
        "validation_obligations": [
            "Proposal validation must reject missing project intelligence, shallow readiness gates, and empty customization flow.",
            "Proposal validation must pass before writes and reject disconnected workstream, component, architecture, wave, or release topology.",
            "After apply, the parent workstream must contain Project Intelligence and child workstreams must contain Domain Intelligence.",
            "Before coding, the first technical plan must name source paths, tests, fallback/degraded proof, rollback or recovery path, and refresh commands.",
            "Before release promotion, repo-native proof and generated project records must agree with the accepted project topology.",
        ],
        "artifacts": [
            "Canonical proposal JSON: source object for project intelligence, project brief, workstreams, components, diagrams, waves, and release plan.",
            "Parent workstream: durable project intelligence and execution memory.",
            "Child workstreams: domain-specific product requirements.",
            "Candidate component specs: component-specific planned ownership and proof contracts.",
            "Architecture diagram suite: multi-view product review surface before source exists.",
            "Release target and progress posture: navigation and first-wave progress surface.",
        ],
        "owners": [
            "Operator owns product direction, customization choices, compliance posture, runtime target, and release ambition.",
            "Project tooling owns schema, normalization, validation, apply, rollback, refresh, and memory recording.",
            "Technical-plan author owns source paths, implementation sequence, proof commands, and rollback/recovery plan after apply.",
            "Component specs own component identity; architecture diagrams own topology; workstreams own intent; release records report derived state.",
        ],
        "execution_memory": [
            "Prior failure: agents produced decent prose, then manually reconstructed apply objects, hit validation failures, patched fields, and exposed implementation artifacts to users.",
            "Prior failure: component specs became templated and repeated project posture instead of component-specific boundaries.",
            "Prior failure: greenfield closeout pushed too quickly toward `start B-002` before deep project review.",
            "Reusable lesson: the canonical proposal object, validation report, project options, and applied memory must exist before implementation starts.",
        ],
        "metrics": [
            "Project-depth metric: every required project-intelligence layer has concrete rows, not labels.",
            "Traceability metric: orphaned workstreams, components, diagrams, release refs, and proof gates remain zero.",
            "UX metric: proposal text shows direction choices, checkpoints, readiness gates, and host-independent commands before coding handoff.",
            "Agent-quality metric: no visible canonical-object patching loop, no generic component specs, no title-only workstreams.",
            "Latency metric: proposal/create stays provider-free and performs one batched refresh after confirmed apply.",
        ],
        "change_model": [
            "If a customization choice changes, invalidate dependent wave, component, diagram, and release assumptions before coding.",
            "If runtime changes, recompute source paths, proof commands, component interfaces, and deployment architecture views.",
            "If compliance posture changes, update risks, validation obligations, component failure modes, and release gate before implementation.",
            "If source proof lands, promote only the affected claims from user_intent or assumption to source_backed.",
        ],
        "invalidation_rules": [
            *family["invalidation_rules"],
            "If the operator changes primary user, runtime, data boundary, compliance posture, proof threshold, or release ambition, invalidate the affected wave order, component boundaries, diagrams, and release assumptions before coding.",
            "If source-backed proof lands, changes, or disappears, reclassify only the claims tied to that proof and expire dependent component, workstream, architecture, and progress projections until refreshed.",
            "If a technical plan contradicts the accepted project intelligence, stop implementation and require an explicit proposal revision, plan revision, or human decision record.",
            "If a generated view disagrees with source files, treat the view as stale and repair source truth before using it for direction.",
        ],
        "conflict_model": [
            "Source-backed tests outrank proposal prose; source files outrank generated views; operator decisions outrank default assumptions.",
            "When workstream, component, architecture, or progress records disagree, block promotion and repair source truth rather than coding forward.",
            "When host chat contradicts canonical proposal JSON, the JSON wins until the operator confirms a revised proposal.",
            "When component scope conflicts with project posture, keep the component spec narrow and move project-wide concerns to the parent workstream.",
        ],
        "transfer_priors": [
            *family["transfer_priors"],
            "Reusable prior: first build the project requirements surface, then pick the first child implementation plan.",
            "Reusable prior: require normal, empty, degraded, and failure proof where the domain exposes user-visible states.",
            "Reusable prior: diagram suites should include topology, sequence, ownership, state/data, validation/release, and operational risk views when the project is complex.",
            "Reusable prior: a greenfield proposal should lower future agent context cost rather than create long prose that must be rediscovered.",
        ],
    }


def normalize_project_intelligence(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str,
    domain_profile: GreenfieldDomainProfile | None = None,
    project_brief: Mapping[str, Any] | None = None,
    program: Mapping[str, Any] | None = None,
    release_plan: Mapping[str, Any] | None = None,
    components: Sequence[Any] = (),
    diagrams: Sequence[Any] = (),
    observed_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize or synthesize project intelligence for legacy proposals."""

    title = clean_text(intent.get("title")) or clean_text(intent.get("name")) or "Greenfield Project"
    prompt = clean_text(intent.get("prompt")) or title
    slug = slugify(clean_text(intent.get("project_slug")) or title)
    profile = domain_profile or infer_greenfield_domain_profile(prompt=prompt, title=title, slug=slug)
    defaults = build_project_intelligence(
        prompt=prompt,
        title=title,
        slug=slug,
        release_selector=release_selector,
        domain_profile=profile,
        project_brief=project_brief,
        program=program,
        release_plan=release_plan,
        components=components,
        diagrams=diagrams,
        observed_source=observed_source,
    )
    if not isinstance(value, Mapping):
        return defaults
    result = dict(value)
    result.setdefault("schema_version", PROJECT_INTELLIGENCE_SCHEMA_VERSION)
    result.setdefault("purpose", defaults["purpose"])
    result.setdefault("coding_posture", defaults["coding_posture"])
    result["control_surface_summary"] = _normalized_rows(
        result.get("control_surface_summary"),
        default=defaults["control_surface_summary"],
        min_rows=5,
    )
    result["customization_flow"] = _normalized_rows(
        result.get("customization_flow"),
        default=defaults["customization_flow"],
        min_rows=4,
    )
    for key in PROJECT_INTELLIGENCE_LAYERS:
        result[key] = _normalized_rows(result.get(key), default=defaults[key], min_rows=2)
    return result


def project_intelligence_issues(value: Any) -> list[str]:
    """Return validation issues for the project-level intelligence object."""

    if not isinstance(value, Mapping):
        return ["proposal `project_intelligence` must be an object"]
    issues: list[str] = []
    _require_text(value, "purpose", issues=issues, min_words=12)
    _require_text(value, "coding_posture", issues=issues, min_words=14)
    if len(_row_list(value.get("control_surface_summary"))) < 5:
        issues.append("proposal `project_intelligence.control_surface_summary` must include at least five control-surface rows")
    if len(_row_list(value.get("customization_flow"))) < 4:
        issues.append("proposal `project_intelligence.customization_flow` must include at least four operator-visible steps")
    for key in PROJECT_INTELLIGENCE_LAYERS:
        rows = _row_list(value.get(key))
        minimum = 3 if key in {"intent", "ontology", "operators", "validation_obligations", "topology"} else 2
        if len(rows) < minimum:
            issues.append(f"proposal `project_intelligence.{key}` must include at least {minimum} rows")
        elif any(_word_count(row) < 5 for row in rows[:minimum]):
            issues.append(f"proposal `project_intelligence.{key}` contains shallow rows")
    return issues


def render_project_intelligence_section(value: Any, *, preview: bool = False) -> str:
    """Render project intelligence as Markdown for proposal text or workstream records."""

    if not isinstance(value, Mapping):
        return ""
    lines: list[str] = []
    purpose = clean_text(value.get("purpose"))
    coding_posture = clean_text(value.get("coding_posture"))
    if purpose:
        lines.append(purpose)
    if coding_posture:
        lines.extend(["", f"**Coding posture:** {coding_posture}"])
    _append_layer(lines, "Product Requirements", value.get("control_surface_summary"), limit=5 if preview else 0)
    _append_layer(lines, "Customization Flow", value.get("customization_flow"), limit=5 if preview else 0)
    for key in PROJECT_INTELLIGENCE_LAYERS:
        _append_layer(lines, _LAYER_LABELS[key], value.get(key), limit=_preview_layer_limit(key) if preview else 0)
    return "\n".join(lines).strip()


def _preview_layer_limit(key: str) -> int:
    return _PREVIEW_LAYER_LIMITS.get(key, 2)


def _append_layer(lines: list[str], label: str, value: Any, *, limit: int) -> None:
    rows = _row_list(value)
    if limit:
        rows = rows[:limit]
    if not rows:
        return
    if lines:
        lines.append("")
    lines.append(f"### {label}")
    lines.extend(f"- {row}" for row in rows)


def _customization_flow(*, choice_refs: Sequence[str], release: str) -> list[str]:
    choices = ", ".join(choice_refs[:8]) or "primary user, runtime, data boundary, proof bar, first-release ambition"
    return [
        f"Review: inspect project intelligence, project brief, workstreams, components, diagrams, waves, and release `{release}`.",
        f"Choose: adjust {choices} before apply if any default would misdirect architecture or proof.",
        "Confirm: run the one-command create path only after the operator accepts the direction and readiness gates.",
        "Plan: open the first child workstream technical plan after accepted project records exist.",
        "Code: edit source only after the plan names source paths, tests, failure states, and rollback or recovery posture.",
    ]


def _choice_refs(project_brief: Mapping[str, Any]) -> list[str]:
    rows = project_brief.get("customization_options", [])
    result: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, Mapping):
            continue
        decision = clean_text(row.get("decision"))
        if decision:
            result.append(decision)
    return result


def _component_refs(components: Sequence[Any]) -> list[str]:
    return [
        token
        for token in unique_text(
            clean_text(row.get("component_id")) or clean_text(row.get("label"))
            for row in components
            if isinstance(row, Mapping)
        )
        if token
    ]


def _diagram_refs(diagrams: Sequence[Any]) -> list[str]:
    return [
        token
        for token in unique_text(
            clean_text(row.get("slug")) or clean_text(row.get("title"))
            for row in diagrams
            if isinstance(row, Mapping)
        )
        if token
    ]


def _wave_refs(program: Mapping[str, Any]) -> list[str]:
    waves = program.get("waves", []) if isinstance(program.get("waves"), list) else []
    refs: list[str] = []
    for row in waves:
        if not isinstance(row, Mapping):
            continue
        refs.append(clean_text(row.get("label")) or clean_text(row.get("name")) or clean_text(row.get("wave_id")))
    return [item for item in refs if item]


def _normalized_rows(value: Any, *, default: Sequence[str], min_rows: int) -> list[str]:
    rows = _row_list(value)
    if len(rows) >= min_rows:
        return rows
    return list(default)


def _row_list(value: Any) -> list[str]:
    if isinstance(value, str):
        token = clean_text(value)
        return [token] if token else []
    rows = [clean_text(item) for item in text_values(value)]
    return [row for row in rows if row]


def _require_text(value: Mapping[str, Any], key: str, *, issues: list[str], min_words: int) -> None:
    text = clean_text(value.get(key))
    if not text:
        issues.append(f"proposal `project_intelligence.{key}` must be non-empty")
        return
    if _word_count(text) < min_words:
        issues.append(f"proposal `project_intelligence.{key}` must contain at least {min_words} meaningful words")


def _word_count(value: str) -> int:
    return len([part for part in clean_text(value).replace("/", " ").split() if part.strip()])


def _family_terms(*, profile: GreenfieldDomainProfile, title: str) -> dict[str, Any]:
    if profile.family == "defi_risk":
        return {
            "project_objective": "govern a non-custodial DeFi risk sentinel that makes exposure, stale data, and alert confidence reviewable before live-chain integration.",
            "stakeholder_outcome": "an analyst can understand risk posture without trusting incomplete oracle, indexer, liquidity, or protocol-health data.",
            "failure_mode": "the product can imply financial advice, custody, or false risk precision before data quality and audit posture are proven.",
            "non_goals": "trade execution, custody, private keys, production RPC, financial advice, and unpinned provider data in the first release.",
            "ontology": [
                "Risk subject: wallet, protocol, pool, strategy, or position set under observation; never a custody account.",
                "Exposure snapshot: normalized holdings, debt, collateral, chain, protocol, timestamp, and confidence.",
                "Oracle or indexer point: value plus freshness and provenance; stale or missing inputs degrade the readout.",
                "Alert: severity, trigger reason, threshold, confidence, acknowledgement state, and audit trail.",
            ],
            "constraints": [
                "No custody, private keys, transaction signing, or trade execution in the first release.",
                "Numeric risk readouts require freshness and confidence metadata.",
                "Fixtures and replay proof must fail closed on live network or credential access.",
            ],
            "assumptions": [
                "The first user is an analyst or operator, not an automated trading agent.",
                "The first data path is fixture-backed or sandboxed until the operator accepts live-provider risk.",
            ],
            "risks": [
                "Compliance risk: risk language can become financial-advice language if confidence and data limits are hidden.",
                "Data risk: stale oracle or missing indexer evidence can make exposure look safer than it is.",
            ],
            "invalidation_rules": [
                "If chain coverage, oracle provenance, indexer source, liquidity model, or live-RPC posture changes, invalidate risk confidence, stale/missing-state proof, data-flow diagrams, and release gates until replayed.",
                "If non-custody or no-advice posture changes, block release promotion until authority, audit, security, and compliance decisions are rewritten.",
            ],
            "transfer_priors": [
                "DeFi risk products should treat stale, missing, and unsupported-chain states as first-class UX and test cases.",
                "Non-custodial and no-advice boundaries belong in project truth before component work begins.",
            ],
        }
    if profile.family == "defi_merchant_lending":
        return {
            "project_objective": (
                "govern an SMB merchant lending product where Shopify merchant data, credit eligibility, "
                "stablecoin funding, DeFi liquidity, disbursement, repayment, and compliance gates stay explicit "
                "before live protocol or production lending claims."
            ),
            "stakeholder_outcome": (
                "an SMB merchant can understand application status, eligible capital, terms, funding state, and repayment obligations, "
                "while operators can trace liquidity, compliance, and data freshness without treating the product as a consumer purchase flow."
            ),
            "failure_mode": (
                "the product can become a generic retail-purchase scaffold, misstate credit availability, duplicate disbursements or repayments, "
                "or imply custody, live DeFi execution, or production lending readiness before proof exists."
            ),
            "non_goals": (
                "consumer purchase flow, production loan approval, live DeFi deposits or withdrawals, custody, private keys, "
                "financial advice, real Shopify merchant data, and production stablecoin disbursement in the first release."
            ),
            "ontology": [
                "Merchant borrower: SMB Shopify seller applying for working capital; not a retail consumer.",
                "Shopify commerce snapshot: fixture-backed shop sales, order, refund, chargeback, and freshness data used for underwriting inputs.",
                "Credit facility: eligibility, limit, terms, status, disbursement, and repayment state under compliance gates.",
                "DeFi liquidity source: stablecoin pool, vault, or protocol posture used as funding availability evidence; not a custody account.",
                "Stablecoin disbursement: idempotent funding event from an approved facility, replay-safe and blocked before compliance approval.",
                "Repayment event: scheduled or received repayment state tied to facility balance, replay key, and audit evidence.",
                "Compliance gate: KYB, AML, sanctions, lending disclosure, and no-custody checks that can block funding or release movement.",
            ],
            "constraints": [
                "No retail-buyer, retail-purchase, or card-processing sandbox framing for merchant lending prompts.",
                "First-release liquidity, Shopify, disbursement, and repayment proof stays fixture-backed or sandboxed unless the operator explicitly accepts live integration risk.",
                "No custody, private keys, protocol transactions, or production stablecoin movement in release 0.0.1.",
                "KYB/AML/sanctions, lending-disclosure, retention, audit, and data-classification posture must be visible before implementation planning.",
            ],
            "assumptions": [
                "The first user is an SMB merchant borrower or capital-ops reviewer, not a retail buyer.",
                "The first data path uses fixture-backed Shopify snapshots and stablecoin/liquidity ledgers, not live protocol or production merchant data.",
            ],
            "risks": [
                "Credit risk: stale Shopify data, weak eligibility rules, or missing compliance checks can overstate approved capital.",
                "Treasury risk: liquidity availability, disbursement, and repayment can drift without idempotent event proof.",
                "Compliance risk: KYB/AML, lending, money-transmission, securities, no-custody, and stablecoin obligations can be hidden by generic commerce language.",
            ],
            "invalidation_rules": [
                "If Shopify data scope, underwriting inputs, liquidity model, stablecoin ledger semantics, disbursement rail, or repayment rules change, invalidate facility-state proof, component interfaces, architecture data-flow views, and release gates.",
                "If KYB/AML, lending disclosure, custody, money-transmission, securities, or live-protocol posture changes, block release promotion until risks, authority, proof, and non-goals are rewritten.",
                "If a proposal introduces retail-buyer, retail-purchase, or card-processing semantics, treat it as a domain-family conflict and regenerate before coding.",
            ],
            "transfer_priors": [
                "Merchant lending projects must keep borrower workflow, underwriting inputs, liquidity availability, compliance gates, disbursement, and repayment as separate domain objects.",
                "Shopify in a lending prompt is usually merchant data and embedded-app context, not proof that the product is a retail purchase product.",
                "Stablecoin funding claims need closed-world liquidity and ledger replay before live DeFi integration or production disbursement.",
            ],
        }
    if profile.family == "commerce":
        return {
            "project_objective": f"govern {title} around a checkout-first path with idempotent order state, payment recovery, and accessible shopper feedback.",
            "stakeholder_outcome": "a shopper can move through browse, cart, checkout, failure, retry, and completion without duplicate orders or misleading payment state.",
            "failure_mode": "checkout can double-create orders, hide payment failure, or imply production payment readiness before sandbox proof exists.",
            "non_goals": "production payment credentials, live fulfillment, irreversible inventory reservation, and provider compliance claims in the first release.",
            "ontology": [
                "Shopper: browser actor moving through browse, cart, checkout, payment handoff, and recovery states.",
                "Cart: mutable shopper intent before checkout; not an order and not a payment record.",
                "Order draft: idempotent server-side state created before payment completion.",
                "Payment callback: sandbox provider event that can arrive once, late, duplicated, failed, or successful.",
            ],
            "constraints": [
                "Payment stays sandboxed until provider and compliance gates are explicit.",
                "Order creation must be idempotent under retry and callback replay.",
                "Browser proof must include empty, failed, retry, and completion states.",
            ],
            "assumptions": [
                "The first user is a shopper and the first proof target is browser-visible.",
                "The first release uses sandbox or mock provider behavior, not production credentials.",
            ],
            "risks": [
                "Transaction risk: duplicate or lost order state can silently corrupt checkout trust.",
                "Compliance risk: payment/provider claims can outrun sandbox evidence.",
            ],
            "invalidation_rules": [
                "If payment provider, sandbox contract, price snapshot, inventory reservation, or callback semantics change, invalidate checkout idempotency proof and recovery diagrams.",
                "If production payment or fulfillment moves into scope, block release promotion until provider compliance, recovery, and audit obligations are explicit.",
            ],
            "transfer_priors": [
                "Commerce projects need idempotency, payment failure recovery, and accessible error proof before scale features.",
                "Keep storefront, checkout, catalog snapshot, and payment provider boundaries distinct until source proof narrows them.",
            ],
        }
    compact = title.replace(" App", "").replace(" Platform", "").strip() or "product"
    return {
        "project_objective": f"govern {compact} as a coherent product with a named user outcome, domain model, architecture views, and proof gates before source work starts.",
        "stakeholder_outcome": f"a future operator, reviewer, or implementation agent can continue {compact} without rediscovering the project from a vague prompt.",
        "failure_mode": "implementation can become a collection of disconnected files, generic components, and unproven claims.",
        "non_goals": "production readiness, live external integration, broad platform scope, or source-backed ownership before the first plan and tests exist.",
        "ontology": [
            f"Operator: first person or system actor who must succeed with the {compact} workflow.",
            "Domain object: first product object whose state and transitions anchor the implementation.",
            "Command or query: first operation exposed by the product boundary and consumed by tests.",
            "Proof fixture: deterministic input used to demonstrate normal, empty, degraded, and failure behavior.",
        ],
        "constraints": [
            "Keep the first release small enough to prove with repository-native tests.",
            "Use fixtures or local proof before live providers unless live integration is the explicit project objective.",
            "Do not conflate UI, domain state, storage, and validation ownership in one vague component.",
        ],
        "assumptions": [
            "The first user role and runtime can be accepted as defaults unless the operator changes them.",
            "The first source slice should be a narrow vertical proof, not a full platform implementation.",
        ],
        "risks": [
            "Architecture risk: vague ownership can merge experience, domain, storage, and proof into one brittle surface.",
            "Proof risk: demo-like output can appear real while lacking tests, fixtures, or degraded-state behavior.",
        ],
        "invalidation_rules": [
            "If first user, runtime, storage, deployment, data source, or proof target changes, invalidate the affected source paths, component contracts, diagrams, and validation commands.",
            "If a broad prompt narrows into a regulated, safety-sensitive, or external-provider domain, regenerate the security, privacy, compliance, and release-gate posture before implementation.",
        ],
        "transfer_priors": [
            "Generic projects need explicit user, domain, proof, and source-of-truth hierarchy before code.",
            "If a prompt is broad, prefer options and gates over pretending certainty.",
        ],
    }


__all__ = [
    "PROJECT_INTELLIGENCE_SCHEMA_VERSION",
    "PROJECT_INTELLIGENCE_SECTION_TITLE",
    "PROJECT_INTELLIGENCE_LAYERS",
    "build_project_intelligence",
    "normalize_project_intelligence",
    "project_intelligence_issues",
    "render_project_intelligence_section",
]
