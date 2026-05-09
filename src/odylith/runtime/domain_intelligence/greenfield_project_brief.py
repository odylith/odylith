"""Project-first shaping contract for greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile
from odylith.runtime.domain_intelligence.greenfield_domain_profile import infer_greenfield_domain_profile
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_text_list


PROJECT_BRIEF_SCHEMA_VERSION = "odylith.greenfield.project_brief.v1"


def build_project_brief(
    *,
    prompt: str,
    title: str,
    slug: str,
    domain_profile: GreenfieldDomainProfile | None = None,
    release_selector: str,
) -> dict[str, Any]:
    """Return the project-shaping object that must be reviewed before code."""

    profile = domain_profile or infer_greenfield_domain_profile(prompt=prompt, title=title, slug=slug)
    family = _project_family(prompt=prompt, title=title, slug=slug, profile=profile)
    return {
        "schema_version": PROJECT_BRIEF_SCHEMA_VERSION,
        "purpose": (
            "Shape the project as a coherent product and architecture before the first source-backed "
            "implementation plan is started."
        ),
        "operating_principle": (
            "Do not treat greenfield apply as permission to code immediately. Apply creates the governed "
            "project control surface; implementation starts only after the project-first gates below are reviewed."
        ),
        "project_outcome": _project_outcome(title=title, family=family),
        "review_posture": (
            "Host independent: the same choices are visible in CLI text, JSON, Codex, and Claude Code because "
            "they live in the canonical proposal object."
        ),
        "blueprint_sections": _blueprint_sections(family=family),
        "customization_options": _customization_options(title=title, family=family),
        "customization_prompts": _customization_prompts(family=family),
        "pre_coding_checkpoints": _pre_coding_checkpoints(family=family),
        "coding_readiness_gates": _coding_readiness_gates(title=title, release_selector=release_selector),
        "host_independent_paths": _host_independent_paths(prompt=prompt, release_selector=release_selector),
    }


def normalize_project_brief(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str,
) -> dict[str, Any]:
    """Normalize or synthesize a project brief for legacy host-authored proposals."""

    title = clean_text(intent.get("title")) or clean_text(intent.get("name")) or "Greenfield Project"
    prompt = clean_text(intent.get("prompt")) or title
    slug = clean_text(intent.get("project_slug")) or title
    profile = infer_greenfield_domain_profile(prompt=prompt, title=title, slug=slug)
    default = build_project_brief(
        prompt=prompt,
        title=title,
        slug=slug,
        domain_profile=profile,
        release_selector=release_selector,
    )
    if not isinstance(value, Mapping):
        return default

    result = dict(value)
    result.setdefault("schema_version", PROJECT_BRIEF_SCHEMA_VERSION)
    result.setdefault("purpose", default["purpose"])
    result.setdefault("operating_principle", default["operating_principle"])
    result.setdefault("project_outcome", default["project_outcome"])
    result.setdefault("review_posture", default["review_posture"])
    result["blueprint_sections"] = _normalize_brief_rows(
        result.get("blueprint_sections"),
        defaults=default["blueprint_sections"],
        required_keys=("section", "must_capture", "why_it_matters"),
    )
    result["customization_options"] = _normalize_brief_rows(
        result.get("customization_options") or result.get("direction_options"),
        defaults=default["customization_options"],
        required_keys=("id", "decision", "recommended", "choices", "impact"),
    )
    result["customization_prompts"] = normalize_text_list(result.get("customization_prompts")) or list(
        default["customization_prompts"]
    )
    result["pre_coding_checkpoints"] = _normalize_brief_rows(
        result.get("pre_coding_checkpoints") or result.get("checkpoints"),
        defaults=default["pre_coding_checkpoints"],
        required_keys=("checkpoint", "operator_question", "done_when"),
    )
    result["coding_readiness_gates"] = normalize_text_list(result.get("coding_readiness_gates")) or list(
        default["coding_readiness_gates"]
    )
    result["host_independent_paths"] = _normalize_brief_rows(
        result.get("host_independent_paths"),
        defaults=default["host_independent_paths"],
        required_keys=("path", "command", "works_in", "use_when"),
    )
    return result


def project_brief_issues(value: Any) -> list[str]:
    """Return validation issues for the project-first greenfield brief."""

    issues: list[str] = []
    if not isinstance(value, Mapping):
        return ["proposal `project_brief` must be an object"]
    _require_text(value, "purpose", owner="proposal `project_brief`", issues=issues, min_words=10)
    _require_text(value, "operating_principle", owner="proposal `project_brief`", issues=issues, min_words=12)
    _require_text(value, "project_outcome", owner="proposal `project_brief`", issues=issues, min_words=10)
    _require_rows(
        value.get("blueprint_sections"),
        owner="proposal `project_brief.blueprint_sections`",
        issues=issues,
        min_rows=4,
        required_keys=("section", "must_capture", "why_it_matters"),
    )
    _require_rows(
        value.get("customization_options"),
        owner="proposal `project_brief.customization_options`",
        issues=issues,
        min_rows=5,
        required_keys=("id", "decision", "recommended", "choices", "impact"),
    )
    _require_rows(
        value.get("pre_coding_checkpoints"),
        owner="proposal `project_brief.pre_coding_checkpoints`",
        issues=issues,
        min_rows=4,
        required_keys=("checkpoint", "operator_question", "done_when"),
    )
    prompts = normalize_text_list(value.get("customization_prompts"))
    if len(prompts) < 3:
        issues.append("proposal `project_brief.customization_prompts` must include at least three host-independent examples")
    elif any(_word_count(prompt) < 6 for prompt in prompts):
        issues.append("proposal `project_brief.customization_prompts` contains a shallow example")
    gates = normalize_text_list(value.get("coding_readiness_gates"))
    if len(gates) < 4:
        issues.append("proposal `project_brief.coding_readiness_gates` must include at least four gates")
    elif any(_word_count(gate) < 6 for gate in gates):
        issues.append("proposal `project_brief.coding_readiness_gates` contains a shallow gate")
    _require_rows(
        value.get("host_independent_paths"),
        owner="proposal `project_brief.host_independent_paths`",
        issues=issues,
        min_rows=3,
        required_keys=("path", "command", "works_in", "use_when"),
    )
    return issues


def _project_outcome(*, title: str, family: str) -> str:
    if family == "robot_swarm":
        return (
            f"{title} should become a simulation-first robotics logistics product whose first release proves "
            "operator dispatch, fleet telemetry, reservation/coordination boundaries, safety envelope behavior, "
            "and replayable validation before hardware, yard operations, or production autonomy claims."
        )
    if family == "defi_risk":
        return (
            f"{title} should become a read-only, auditable risk-monitoring product whose first release proves "
            "analyst workflow, risk signal boundaries, stale-data behavior, and non-custodial posture before "
            "any live-chain or trading integration is considered."
        )
    if family == "defi_merchant_lending":
        return (
            f"{title} should become a merchant-capital product whose first release proves the SMB borrower journey, "
            "Shopify merchant-data boundary, credit eligibility, stablecoin funding state, repayment state, "
            "liquidity freshness, and compliance gates before live DeFi protocol or production lending claims."
        )
    if family == "commerce":
        return (
            f"{title} should become a commerce product whose first release proves the shopper path, checkout "
            "state, payment-failure recovery, catalog price snapshot boundaries, and accessible fallback states "
            "before production payment claims."
        )
    return (
        f"{title} should become a governed product with a named user outcome, explicit domain model, component "
        "ownership, proof strategy, release lane, and open questions resolved enough that agents can continue "
        "without rebuilding the project from scratch."
    )


def _blueprint_sections(*, family: str) -> list[dict[str, str]]:
    sections = [
        {
            "section": "Project spine",
            "must_capture": "Primary user, problem, outcome, non-goals, first release promise, and what must not be claimed yet.",
            "why_it_matters": "Keeps broad greenfield prompts from turning into generic tickets or premature source-backed claims.",
        },
        {
            "section": "Domain model",
            "must_capture": "Core entities, lifecycle states, allowed transitions, invalid states, and terms that must not be conflated.",
            "why_it_matters": "Gives future agents operational vocabulary instead of labels.",
        },
        {
            "section": "Architecture views",
            "must_capture": "Topology, first-slice sequence, component ownership, state/data contract, validation, and operational risk diagrams.",
            "why_it_matters": "Makes architectural disagreement visible before the first source directory exists.",
        },
        {
            "section": "Proof posture",
            "must_capture": "Behavior proof, contract proof, browser or CLI proof, fixture policy, acceptance threshold, and retest trigger.",
            "why_it_matters": "Defines what counts as evidence before implementation begins.",
        },
        {
            "section": "Project records",
            "must_capture": "Workstreams, component candidates, architecture diagrams, waves, release target, assumptions, risks, and decisions.",
            "why_it_matters": "Keeps Codex, Claude Code, and direct CLI users on the same project truth without turning tool internals into the product model.",
        },
    ]
    if family == "defi_risk":
        sections.insert(
            2,
            {
                "section": "Risk and data posture",
                "must_capture": "Custody boundary, oracle/indexer freshness, exposure semantics, financial-advice disclaimer, audit, and no-live-RPC gate.",
                "why_it_matters": "Prevents a risk product from sounding authoritative before data quality and regulatory posture are proven.",
            },
        )
    elif family == "defi_merchant_lending":
        sections.insert(
            2,
            {
                "section": "Credit, liquidity, and compliance posture",
                "must_capture": (
                    "Merchant borrower identity, Shopify data freshness, underwriting inputs, facility lifecycle, "
                    "stablecoin liquidity, disbursement, repayment, KYB/AML, no-custody, and no-live-protocol gates."
                ),
                "why_it_matters": (
                    "Prevents a merchant lending product from collapsing into a consumer retail flow or implying approved credit, "
                    "available funds, custody, or production lending before proof exists."
                ),
            },
        )
    elif family == "robot_swarm":
        sections.insert(
            2,
            {
                "section": "Safety and autonomy posture",
                "must_capture": "Simulation boundary, robot capability model, safety envelope, e-stop assumptions, telemetry freshness, and hardware-in-loop gate.",
                "why_it_matters": "Prevents coordination diagrams from implying safe physical autonomy before simulation and safety proof exist.",
            },
        )
    elif family == "commerce":
        sections.insert(
            2,
            {
                "section": "Transaction posture",
                "must_capture": "Payment sandbox, order idempotency, catalog snapshot, inventory visibility, retry, privacy, and accessibility posture.",
                "why_it_matters": "Prevents checkout and order claims from outrunning recovery and payment-provider proof.",
            },
        )
    return sections


def _customization_options(*, title: str, family: str) -> list[dict[str, Any]]:
    common = [
        _option(
            "D1",
            "Primary user or operator",
            "Name the first person who must succeed and the job they need done.",
            ["operator workflow", "end-user self-service", "admin/reviewer workflow"],
            "Changes the first workflow, visible states, security roles, and proof surface.",
        ),
        _option(
            "D2",
            "Runtime and deployment posture",
            "Keep the first release local and deterministic unless the operator chooses hosted runtime constraints.",
            ["local library plus CLI", "API service", "web app", "hybrid service and UI"],
            "Changes source paths, test harness, browser/API proof, and operational runbooks.",
        ),
        _option(
            "D3",
            "Data and integration boundary",
            "Use fixtures or request-body inputs before live providers unless live data is the explicit product objective.",
            ["fixture-only", "sandbox provider", "read-only live provider", "production integration later"],
            "Changes security posture, replay proof, migration risk, and what can be claimed as source-backed.",
        ),
        _option(
            "D4",
            "Proof bar",
            "Pick the minimum evidence that would convince a reviewer the project direction is real.",
            ["unit and contract proof", "browser matrix", "simulation replay", "migration and release smoke"],
            "Changes validation obligations, release gates, and what the progress view should show as complete.",
        ),
        _option(
            "D5",
            "First release ambition",
            "Keep release 0.0.1 as a thin governed slice unless the operator explicitly accepts more risk.",
            ["one workflow", "one workflow plus audit", "workflow plus integration stub", "multi-component vertical slice"],
            "Changes wave scope, release targeting, backlog sizing, and time to trustworthy proof.",
        ),
    ]
    if family == "defi_risk":
        return [
            _option(
                "D0",
                "Custody and advice boundary",
                "Default to non-custodial, read-only risk monitoring with no trade execution and no financial-advice claim.",
                ["non-custodial read-only", "research-only notebook", "ops alerting", "execution explicitly out of scope"],
                "Changes compliance, audit, copy, and which alerts may be shown as recommendations.",
            ),
            *common,
            _option(
                "D6",
                "Oracle and indexer freshness model",
                "Require stale/missing data states before numeric risk readouts are trusted.",
                ["fixture timestamps", "sandbox oracle adapter", "multi-source freshness", "human-reviewed data quality"],
                "Changes degraded-state UX, replay fixtures, confidence scoring, and release blockers.",
            ),
        ]
    if family == "defi_merchant_lending":
        return [
            _option(
                "D0",
                "Borrower and capital-ops boundary",
                "Default to the Shopify SMB merchant as borrower and capital-ops as reviewer; do not model retail buyers as the primary actor.",
                ["merchant borrower portal", "capital-ops review", "underwriter workflow", "embedded Shopify app"],
                "Changes the first workflow, authorization model, data consent, visible funding states, and proof surface.",
            ),
            *common,
            _option(
                "D6",
                "Stablecoin and DeFi liquidity posture",
                "Default to fixture-backed stablecoin ledger and liquidity snapshots before live protocol access.",
                ["fixture-only liquidity ledger", "sandbox vault adapter", "read-only protocol quote", "live protocol later"],
                "Changes treasury risk, no-custody proof, replay fixtures, compliance gates, and release blockers.",
            ),
            _option(
                "D7",
                "Compliance and lending posture",
                "Keep KYB, AML, sanctions, lending disclosures, audit, retention, and no-custody posture explicit before source edits.",
                ["strict regulated posture", "sandbox compliance gate", "research prototype", "production compliance later"],
                "Changes data classification, release approval, authority, evidence thresholds, and what funding claims are allowed.",
            ),
        ]
    if family == "robot_swarm":
        return [
            _option(
                "D0",
                "Simulation and hardware boundary",
                "Default to simulation-first with no hardware or production-yard control in release 0.0.1.",
                ["simulation-only", "hardware-in-loop later", "single demo robot", "mixed fleet explicitly deferred"],
                "Changes safety gates, telemetry fixtures, deployment architecture views, and what autonomy claims are allowed.",
            ),
            *common,
            _option(
                "D6",
                "Coordination and safety policy",
                "Choose the first conflict model and safety proof before coding task dispatch.",
                ["slot reservation", "zone reservation", "traffic lanes", "manual override and e-stop first"],
                "Changes swarm coordinator interfaces, deadlock/livelock tests, safety envelope contracts, and release blockers.",
            ),
        ]
    if family == "commerce":
        return [
            *common,
            _option(
                "D6",
                "Payment and order recovery model",
                "Default to sandbox payment and idempotent order draft recovery before production credentials exist.",
                ["payment sandbox", "mock provider", "manual invoice", "production payment later"],
                "Changes checkout proof, privacy posture, replay handling, and PCI/provider review gates.",
            ),
        ]
    return common + [
        _option(
            "D6",
            "Architecture depth",
            f"Choose how much of {title} should be architected before code.",
            ["minimal first slice", "full project blueprint", "regulated/safety review", "research-grade reproducibility"],
            "Changes diagram depth, risk register, assumption ledger, and whether coding can start this session.",
        )
    ]


def _option(identifier: str, decision: str, recommended: str, choices: Sequence[str], impact: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "decision": decision,
        "recommended": recommended,
        "choices": list(choices),
        "impact": impact,
        "evidence_tier": "odylith_assumption",
    }


def _customization_prompts(*, family: str) -> list[str]:
    if family == "defi_risk":
        return [
            "Use Python library plus FastAPI, strict regulated posture, fixture-only data, and audit-first proof.",
            "Keep release 0.0.1 non-custodial and read-only while deferring live RPC, trade execution, and advice language.",
            "Make stale oracle, missing indexer, unsupported chain, and confidence display mandatory first-wave states.",
        ]
    if family == "defi_merchant_lending":
        return [
            "Use Shopify merchant as borrower, fixture-backed Shopify sales data, sandbox stablecoin ledger, and no live DeFi protocol calls.",
            "Make KYB, AML, sanctions, lending disclosures, no-custody, and idempotent disbursement and repayment mandatory first-wave gates.",
            "Defer consumer retail flows, production lending decisions, live protocol deposits, custody keys, and real merchant data until release proof passes.",
        ]
    if family == "robot_swarm":
        return [
            "Use simulation-only release 0.0.1 with no hardware control, no live yard integration, and replayable safety proof.",
            "Prioritize dispatcher, reservation/conflict model, telemetry freshness, operator override, and incident replay.",
            "Defer hardware-in-loop and mixed-fleet autonomy until the safety envelope and scenario harness are source-backed.",
        ]
    if family == "commerce":
        return [
            "Use web app plus local checkout core, payment sandbox only, and browser proof for happy and failed payment paths.",
            "Make idempotent order draft recovery and accessible error states part of release 0.0.1.",
            "Defer production payment credentials, fulfillment automation, and live inventory sync until recovery proof passes.",
        ]
    return [
        "Use a local deterministic first release with one primary user, one source boundary, and repo-native proof.",
        "Make this a regulated or safety-sensitive project: require audit, data classification, abuse checks, and stronger gates.",
        "Make this a research-grade project: require reproducibility fixtures, benchmark evidence, provenance, and peer-review checkpoints.",
    ]


def _pre_coding_checkpoints(*, family: str) -> list[dict[str, str]]:
    checkpoints = [
        {
            "checkpoint": "Direction choices reviewed",
            "operator_question": "Which recommended options should change before the proposal is applied or planned?",
            "done_when": "The accepted proposal records the chosen runtime, user, data boundary, first release ambition, and proof bar.",
        },
        {
            "checkpoint": "Non-goals explicit",
            "operator_question": "What should the first release explicitly forbid even if the domain suggests it?",
            "done_when": "Workstream and component records name the excluded behaviors, integrations, and production claims.",
        },
        {
            "checkpoint": "Architecture diagrams reviewed",
            "operator_question": "Do the architecture views show the project shape well enough to catch the first architectural disagreement?",
            "done_when": "Topology, sequence, ownership, state/data, validation, and operational risk views are accepted or revised.",
        },
        {
            "checkpoint": "Evidence threshold accepted",
            "operator_question": "What proof must exist before the first wave can be called real?",
            "done_when": "Validation obligations name concrete tests, browser/simulation/API proof, fixtures, and failure conditions.",
        },
    ]
    if family == "defi_risk":
        checkpoints.append(
            {
                "checkpoint": "Risk-data posture accepted",
                "operator_question": "Which oracle, indexer, confidence, custody, and financial-advice boundaries are non-negotiable?",
                "done_when": "Degraded states, no-live-RPC posture, non-custody posture, and audit requirements are visible before code.",
            }
        )
    elif family == "defi_merchant_lending":
        checkpoints.append(
            {
                "checkpoint": "Merchant-lending posture accepted",
                "operator_question": (
                    "Which borrower role, Shopify data boundary, underwriting inputs, liquidity source, stablecoin rail, "
                    "repayment model, and compliance gates are non-negotiable?"
                ),
                "done_when": (
                    "Workstream, component, and architecture records show merchant borrower workflow, Shopify snapshot rules, no-custody posture, "
                    "KYB/AML gates, liquidity/disbursement/repayment proof, and no consumer-purchase scope before code."
                ),
            }
        )
    elif family == "robot_swarm":
        checkpoints.append(
            {
                "checkpoint": "Safety posture accepted",
                "operator_question": "Which simulation, fleet-scale, telemetry, e-stop, and hardware-in-loop boundaries are non-negotiable?",
                "done_when": "Architecture and workstream records show safety envelope, telemetry freshness, no-hardware-control posture, and first conflict scenario before code.",
            }
        )
    return checkpoints


def _project_family(*, prompt: str, title: str, slug: str, profile: GreenfieldDomainProfile) -> str:
    text = f"{prompt} {title} {slug}".casefold()
    if all(token in text for token in ("robot", "swarm")) or ("amr" in text and "logistics" in text):
        return "robot_swarm"
    return profile.family


def _coding_readiness_gates(*, title: str, release_selector: str) -> list[str]:
    release = release_selector or "0.0.1"
    return [
        f"{title} has an accepted project spine: primary operator, outcome, non-goals, first release promise, and unresolved ambiguities.",
        "Direction options that materially change architecture or validation are either answered or marked as accepted Odylith assumptions.",
        "Workstreams, component specs, architecture diagrams, progress view, and release targeting all describe the same first wave and no orphaned governance objects exist.",
        f"Release {release} has explicit promotion criteria and does not claim production readiness beyond the first governed slice.",
        "The first implementation plan names source paths, validation commands, degraded/error proof, and rollback or recovery posture before code edits.",
    ]


def _host_independent_paths(*, prompt: str, release_selector: str) -> list[dict[str, str]]:
    prompt_text = clean_text(prompt) or "<project intent>"
    release = release_selector or "0.0.1"
    return [
        {
            "path": "Review and customize",
            "command": f'odylith greenfield propose --repo-root . --prompt "{prompt_text}"',
            "works_in": "shell, Codex, Claude Code",
            "use_when": "Use before writes to inspect the project brief, decision options, diagrams, workstreams, and gates.",
        },
        {
            "path": "Emit canonical JSON",
            "command": f'odylith greenfield propose --repo-root . --prompt "{prompt_text}" --format json',
            "works_in": "shell, Codex, Claude Code",
            "use_when": "Use when another tool or reviewer needs the exact apply-ready object.",
        },
        {
            "path": "Apply after confirmation",
            "command": f'odylith greenfield create --repo-root . --prompt "{prompt_text}" --release {release} --confirm',
            "works_in": "shell, Codex, Claude Code",
            "use_when": "Use only after the operator accepts the project-first brief and wants governed records written.",
        },
    ]


def _normalize_brief_rows(value: Any, *, defaults: list[dict[str, Any]], required_keys: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return list(defaults)
    rows: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        if any(_has_text_or_list(row.get(key)) for key in required_keys):
            rows.append(row)
    return rows or list(defaults)


def _has_text_or_list(value: Any) -> bool:
    if isinstance(value, list):
        return any(clean_text(item) for item in value)
    return bool(clean_text(value))


def _require_rows(
    value: Any,
    *,
    owner: str,
    issues: list[str],
    min_rows: int,
    required_keys: Sequence[str],
) -> None:
    if not isinstance(value, list) or len(value) < min_rows:
        issues.append(f"{owner} must include at least {min_rows} rows")
        return
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"{owner}[{index}] must be an object")
            continue
        for key in required_keys:
            if not _has_text_or_list(raw.get(key)):
                issues.append(f"{owner}[{index}] `{key}` must be non-empty")


def _require_text(value: Mapping[str, Any], key: str, *, owner: str, issues: list[str], min_words: int) -> None:
    text = clean_text(value.get(key))
    if not text:
        issues.append(f"{owner} `{key}` must be non-empty")
        return
    if _word_count(text) < min_words:
        issues.append(f"{owner} `{key}` must contain at least {min_words} meaningful words")


def _word_count(value: str) -> int:
    return len([part for part in clean_text(value).replace("/", " ").split() if part.strip()])


__all__ = [
    "PROJECT_BRIEF_SCHEMA_VERSION",
    "build_project_brief",
    "normalize_project_brief",
    "project_brief_issues",
]
