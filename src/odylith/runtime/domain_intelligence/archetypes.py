"""Provider-free domain archetypes for Odylith greenfield proposals.

The catalog is intentionally data-first. Adding a future project domain should
mean adding an archetype here, not branching host-specific proposal logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ComponentBlueprint:
    component_id: str
    label: str
    kind: str
    path_suffix: str
    responsibility: str


@dataclass(frozen=True)
class DiagramBlueprint:
    slug_suffix: str
    title_suffix: str
    summary: str
    kind: str = "flowchart"


@dataclass(frozen=True)
class WaveBlueprint:
    label: str
    goal: str
    validation: str


@dataclass(frozen=True)
class Archetype:
    archetype_id: str
    label: str
    keywords: tuple[str, ...]
    components: tuple[ComponentBlueprint, ...]
    diagrams: tuple[DiagramBlueprint, ...]
    waves: tuple[WaveBlueprint, ...]
    validation_focus: tuple[str, ...]
    risks: tuple[str, ...]


_SCIENCE_VALIDATION = (
    "Pin reproducible inputs, random seeds, units, and environment metadata before comparing results.",
    "Define tolerance bands for numerical outputs instead of exact equality where floating point drift is expected.",
    "Keep benchmark datasets and reference outputs versioned so future sessions can distinguish algorithm changes from data drift.",
)


_PRODUCT_WAVES = (
    WaveBlueprint("Discovery", "Confirm users, first workflow, and success metrics.", "Backlog and topology reviewed before writes."),
    WaveBlueprint("Foundation", "Create the minimum source skeleton and component contracts.", "Smoke tests and ownership checks pass."),
    WaveBlueprint("First Slice", "Ship one end-to-end user workflow through the named components.", "Acceptance proof covers the slice."),
    WaveBlueprint("Hardening", "Add failure handling, security, observability, and release proof.", "Regression and browser/runtime proof pass."),
)


_RESEARCH_WAVES = (
    WaveBlueprint("Research Framing", "Record assumptions, reference material, and correctness oracles.", "Claims stay separated from project structure."),
    WaveBlueprint("Model And Data", "Create model, data, and provenance boundaries.", "Units, fixtures, and seeds are pinned."),
    WaveBlueprint("Execution And Validation", "Implement solver, experiment, or proof execution with reviewable outputs.", "Tolerance, invariant, and reference-output checks pass."),
    WaveBlueprint("Reproducibility", "Package notebooks, reports, and publication artifacts.", "Fresh checkout can reproduce the stated result envelope."),
)


ARCHETYPES: tuple[Archetype, ...] = (
    Archetype(
        archetype_id="commerce",
        label="Commerce Application",
        keywords=("ecommerce", "e-commerce", "commerce", "store", "shop", "marketplace", "checkout", "cart"),
        components=(
            ComponentBlueprint("storefront", "Storefront", "application", "apps/web", "Customer-facing catalog, cart, and checkout UI."),
            ComponentBlueprint("catalog", "Product Catalog", "service", "src/catalog", "Product, inventory, price, and merchandising boundary."),
            ComponentBlueprint("cart", "Cart", "service", "src/cart", "Session and saved-cart state boundary."),
            ComponentBlueprint("orders", "Orders", "service", "src/orders", "Order lifecycle, fulfillment handoff, and status history."),
            ComponentBlueprint("payments", "Payments Boundary", "integration", "src/payments", "Payment-provider adapter and payment-state contract."),
            ComponentBlueprint("customers", "Customer Accounts", "service", "src/customers", "Identity, profile, account, and consent boundary."),
        ),
        diagrams=(
            DiagramBlueprint("system-context", "System Context", "Show shoppers, admins, payment providers, catalog, cart, and order boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show discovery, foundation, first-slice, and hardening wave order."),
            DiagramBlueprint("checkout-runtime", "Checkout Runtime Flow", "Show cart-to-payment-to-order transitions and failure boundaries."),
            DiagramBlueprint("commerce-data-flow", "Commerce Data Flow", "Show catalog, cart, customer, payment, and order data movement."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Checkout happy path and payment-failure recovery.",
            "Catalog price/inventory consistency under concurrent cart updates.",
            "Order idempotency across retry and webhook flows.",
        ),
        risks=(
            "Payment, identity, and order state must not be collapsed into one vague application bucket.",
            "Inventory and price snapshots need explicit consistency rules before implementation starts.",
        ),
    ),
    Archetype(
        archetype_id="science_math",
        label="Science Or Math Project",
        keywords=(
            "science", "scientific", "math", "mathematics", "physics", "simulation", "solver",
            "ode", "pde", "differential", "theorem", "proof", "statistics", "econometrics",
            "notebook", "experiment", "computational", "biology", "chemistry", "model",
        ),
        components=(
            ComponentBlueprint("model-core", "Model Core", "library", "src/model", "Mathematical model, assumptions, equations, and domain objects."),
            ComponentBlueprint("solver-engine", "Solver Engine", "library", "src/solver", "Numerical, symbolic, or proof-search execution boundary."),
            ComponentBlueprint("experiment-runner", "Experiment Runner", "application", "src/experiments", "Reproducible experiment orchestration and run metadata."),
            ComponentBlueprint("data-io", "Data IO", "library", "src/data", "Dataset, fixture, import/export, and provenance boundary."),
            ComponentBlueprint("validation-suite", "Validation Suite", "test", "tests/validation", "Reference checks, tolerances, invariants, and benchmark fixtures."),
            ComponentBlueprint("visualization", "Visualization", "application", "src/visualization", "Plots, reports, notebooks, and explainability outputs."),
        ),
        diagrams=(
            DiagramBlueprint("research-system-context", "Research System Context", "Show inputs, model, solver, experiment runner, validation, and publication outputs."),
            DiagramBlueprint("research-waves", "Research Program Waves", "Show framing, model/data, execution/validation, and reproducibility wave order."),
            DiagramBlueprint("experiment-pipeline", "Experiment Pipeline", "Show data loading, model setup, execution, validation, and result capture."),
            DiagramBlueprint("validation-flow", "Validation Flow", "Show reference data, tolerances, benchmark runs, and review artifacts."),
        ),
        waves=_RESEARCH_WAVES,
        validation_focus=_SCIENCE_VALIDATION
        + (
            "Trace equations or proof obligations to tests, notebooks, or review notes before claiming scientific correctness.",
        ),
        risks=(
            "Scientific claims must not be invented from the prompt; only project structure and validation obligations are proposed.",
            "Numerical tolerances, units, datasets, and reproducibility metadata are first-class governance surfaces.",
        ),
    ),
    Archetype(
        archetype_id="data_platform",
        label="Data Platform",
        keywords=("data platform", "pipeline", "etl", "elt", "ingestion", "warehouse", "analytics", "streaming", "lakehouse"),
        components=(
            ComponentBlueprint("ingestion", "Ingestion", "service", "src/ingestion", "Source connectors, validation, and raw event capture."),
            ComponentBlueprint("transformations", "Transformations", "pipeline", "src/transforms", "Data normalization, enrichment, and quality checks."),
            ComponentBlueprint("storage", "Storage Boundary", "platform", "src/storage", "Warehouse, lake, retention, and schema lifecycle boundary."),
            ComponentBlueprint("serving", "Serving Layer", "service", "src/serving", "APIs, marts, exports, and downstream contracts."),
            ComponentBlueprint("observability", "Data Observability", "platform", "src/observability", "Freshness, volume, quality, and lineage monitoring."),
        ),
        diagrams=(
            DiagramBlueprint("data-flow", "Data Flow", "Show source systems, ingestion, transformation, storage, serving, and monitoring boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show ingestion, quality, serving, and observability delivery order."),
            DiagramBlueprint("lineage-topology", "Lineage Topology", "Show dataset ownership, schema contracts, and downstream consumers."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Schema compatibility and backfill safety.",
            "Freshness, duplicate, null-rate, and volume anomaly checks.",
            "Lineage from source records to served datasets.",
        ),
        risks=(
            "Pipeline ownership must separate ingestion, transformation, storage, and serving contracts.",
            "Backfills and schema changes need explicit forward-fix and rollback posture.",
        ),
    ),
    Archetype(
        archetype_id="ai_agent",
        label="AI Agent System",
        keywords=("ai agent", "agent", "assistant", "copilot", "rag", "retrieval", "llm", "memory", "tool use", "workflow agent"),
        components=(
            ComponentBlueprint("conversation-runtime", "Conversation Runtime", "service", "src/conversation", "Prompt/session orchestration and response lifecycle."),
            ComponentBlueprint("tool-router", "Tool Router", "service", "src/tools", "Tool selection, permissions, retries, and result shaping."),
            ComponentBlueprint("memory-retrieval", "Memory Retrieval", "service", "src/memory", "Hot/cold memory, retrieval, ranking, and provenance."),
            ComponentBlueprint("policy-guard", "Policy Guard", "library", "src/policy", "Safety, scope, and execution policy boundary."),
            ComponentBlueprint("evaluation", "Evaluation", "test", "tests/evaluation", "Benchmarks, regressions, scoring, and drift checks."),
        ),
        diagrams=(
            DiagramBlueprint("agent-runtime", "Agent Runtime Topology", "Show conversation, tools, memory, policy, and evaluation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show memory, tools, policy, evaluation, and release waves."),
            DiagramBlueprint("retrieval-flow", "Retrieval And Tool Flow", "Show retrieval, tool invocation, policy gates, and response synthesis."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Prompt fixtures for routing, memory recall, tool denial, and recovery behavior.",
            "Regression benchmarks for recall, precision, cost, and latency.",
            "Audit trail for tool use, memory provenance, and policy decisions.",
        ),
        risks=(
            "Memory and tool results must carry provenance so the agent does not overclaim.",
            "Latency and credit burn require benchmark gates, not anecdotal checks.",
        ),
    ),
    Archetype(
        archetype_id="cloud_infra",
        label="Cloud Or Infrastructure Platform",
        keywords=("cloud", "infra", "infrastructure", "kubernetes", "devops", "observability", "security", "platform engineering", "ci/cd", "serverless"),
        components=(
            ComponentBlueprint("control-plane", "Control Plane", "platform", "src/control_plane", "Operator API, desired state, and orchestration boundary."),
            ComponentBlueprint("runtime-plane", "Runtime Plane", "platform", "src/runtime", "Workers, schedulers, execution, and isolation boundary."),
            ComponentBlueprint("delivery-pipeline", "Delivery Pipeline", "platform", "src/delivery", "Build, release, deployment, and rollback contract."),
            ComponentBlueprint("observability", "Observability", "platform", "src/observability", "Metrics, traces, logs, SLOs, and incident evidence."),
            ComponentBlueprint("security-policy", "Security Policy", "library", "src/security", "Identity, authorization, secrets, and compliance controls."),
        ),
        diagrams=(
            DiagramBlueprint("platform-topology", "Platform Topology", "Show control plane, runtime plane, delivery, observability, and security boundaries."),
            DiagramBlueprint("delivery-flow", "Delivery Flow", "Show build, deploy, rollback, and evidence capture order."),
            DiagramBlueprint("incident-flow", "Incident Flow", "Show detection, triage, remediation, and postmortem evidence."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Provisioning, rollback, and disaster-recovery rehearsal.",
            "SLO, alert, trace, and audit evidence for critical paths.",
            "Security and policy tests before exposing privileged operations.",
        ),
        risks=(
            "Infrastructure projects need clear control-plane and runtime-plane separation from day one.",
            "Operational safety cannot depend on dashboards without runnable recovery proof.",
        ),
    ),
    Archetype(
        archetype_id="security_compliance",
        label="Security Or Compliance Program",
        keywords=("security", "compliance", "soc2", "audit", "privacy", "iam", "threat model", "risk", "scanner", "policy"),
        components=(
            ComponentBlueprint("asset-inventory", "Asset Inventory", "platform", "src/assets", "Systems, data, identities, and control ownership inventory."),
            ComponentBlueprint("policy-engine", "Policy Engine", "library", "src/policy", "Rules, exceptions, approval, and enforcement boundary."),
            ComponentBlueprint("detection", "Detection", "service", "src/detection", "Signals, findings, triage, and alerting boundary."),
            ComponentBlueprint("evidence-store", "Evidence Store", "platform", "src/evidence", "Audit evidence, retention, provenance, and export contract."),
            ComponentBlueprint("remediation", "Remediation", "service", "src/remediation", "Fix workflow, ownership assignment, and verification boundary."),
            ComponentBlueprint("reporting", "Reporting", "application", "src/reporting", "Controls, audit views, risk dashboards, and stakeholder readouts."),
        ),
        diagrams=(
            DiagramBlueprint("trust-boundary", "Trust Boundary", "Show actors, assets, policy, evidence, detection, and remediation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show inventory, controls, evidence, remediation, and audit-readiness waves."),
            DiagramBlueprint("evidence-flow", "Evidence Flow", "Show signal capture, control mapping, evidence storage, and audit export."),
            DiagramBlueprint("response-flow", "Response Flow", "Show finding triage, assignment, remediation, verification, and closeout."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Threat model and control mapping for each protected boundary.",
            "Evidence provenance, retention, and export tests.",
            "Detection and remediation workflow fixtures with negative cases.",
        ),
        risks=(
            "Compliance labels must map to actual controls and evidence, not generated prose.",
            "Security workflows need explicit ownership and denial paths before automation broadens.",
        ),
    ),
    Archetype(
        archetype_id="iot_instrumentation",
        label="IoT, Robotics, Or Scientific Instrument Workflow",
        keywords=("iot", "embedded", "device", "sensor", "robot", "robotics", "instrument", "telemetry", "edge", "calibration"),
        components=(
            ComponentBlueprint("device-runtime", "Device Runtime", "runtime", "src/device", "Firmware, embedded runtime, or device control boundary."),
            ComponentBlueprint("edge-gateway", "Edge Gateway", "service", "src/edge", "Local buffering, command mediation, and offline behavior."),
            ComponentBlueprint("telemetry-ingestion", "Telemetry Ingestion", "service", "src/telemetry", "Measurements, event capture, and time-series ingest boundary."),
            ComponentBlueprint("control-api", "Control API", "service", "src/control", "Command authorization, safety interlocks, and operator controls."),
            ComponentBlueprint("calibration-validation", "Calibration Validation", "test", "tests/calibration", "Calibration fixtures, tolerances, drift checks, and hardware-in-loop proof."),
            ComponentBlueprint("operations-dashboard", "Operations Dashboard", "application", "apps/dashboard", "Live device, telemetry, alert, and operator workflow surface."),
        ),
        diagrams=(
            DiagramBlueprint("device-edge-cloud", "Device Edge Cloud Topology", "Show device, gateway, ingestion, control, dashboard, and validation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show simulation, device integration, telemetry, control safety, and field-readiness waves."),
            DiagramBlueprint("telemetry-flow", "Telemetry Flow", "Show measurement capture, buffering, ingest, validation, and dashboard readout."),
            DiagramBlueprint("command-safety-flow", "Command Safety Flow", "Show operator command, authorization, interlock, device action, and rollback."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Simulation, hardware-in-loop, and offline recovery tests.",
            "Calibration, unit, tolerance, and sensor-drift checks.",
            "Latency, packet-loss, authorization, and safety-interlock proof.",
        ),
        risks=(
            "Device and control paths need safety gates before live actuation is proposed.",
            "Telemetry correctness depends on units, calibration, and clock/provenance metadata.",
        ),
    ),
    Archetype(
        archetype_id="saas_application",
        label="SaaS Application",
        keywords=("saas", "crm", "dashboard", "admin", "internal tool", "b2b", "tenant", "workflow", "portal"),
        components=(
            ComponentBlueprint("web-app", "Web App", "application", "apps/web", "User-facing screens, navigation, and client state."),
            ComponentBlueprint("api", "API", "service", "src/api", "HTTP/API contract, validation, and request orchestration."),
            ComponentBlueprint("domain-core", "Domain Core", "library", "src/domain", "Business rules, workflow state, and domain invariants."),
            ComponentBlueprint("persistence", "Persistence", "platform", "src/persistence", "Database access, migrations, and data contracts."),
            ComponentBlueprint("auth", "Authentication", "service", "src/auth", "Identity, tenancy, permissions, and session boundary."),
        ),
        diagrams=(
            DiagramBlueprint("system-context", "System Context", "Show users, admins, API, domain, persistence, auth, and external systems."),
            DiagramBlueprint("program-waves", "Program Waves", "Show discovery, foundation, first workflow, and hardening release order."),
            DiagramBlueprint("runtime-topology", "Runtime Topology", "Show web, API, domain, persistence, and auth request flow."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Core workflow acceptance tests across role and tenancy boundaries.",
            "Permission and data-isolation tests.",
            "Migration and rollback tests for persisted state.",
        ),
        risks=(
            "Tenant, auth, and domain boundaries need explicit ownership before implementation broadens.",
            "Dashboard UX should be proved with browser tests, not only unit tests.",
        ),
    ),
    Archetype(
        archetype_id="mobile_game_education",
        label="Mobile, Game, Or Education Experience",
        keywords=("mobile", "ios", "android", "game", "learning", "education", "course", "lesson", "student", "interactive"),
        components=(
            ComponentBlueprint("experience-shell", "Experience Shell", "application", "apps/client", "Primary interaction surface, navigation, and local state."),
            ComponentBlueprint("content-model", "Content Model", "library", "src/content", "Lessons, scenes, levels, exercises, and progression rules."),
            ComponentBlueprint("interaction-engine", "Interaction Engine", "library", "src/interactions", "Input, feedback, scoring, and session mechanics."),
            ComponentBlueprint("progress-sync", "Progress Sync", "service", "src/progress", "User progress, saves, achievements, and recovery."),
            ComponentBlueprint("quality-harness", "Quality Harness", "test", "tests/experience", "Device, browser, accessibility, and gameplay/lesson proof."),
        ),
        diagrams=(
            DiagramBlueprint("experience-topology", "Experience Topology", "Show client, content, interaction, progress, and quality boundaries."),
            DiagramBlueprint("session-flow", "Session Flow", "Show user session start, interaction, feedback, save, and recovery order."),
            DiagramBlueprint("program-waves", "Program Waves", "Show prototype, core loop, content, and launch-readiness waves."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "End-to-end interaction proof on target devices or browser viewports.",
            "Accessibility, save/recovery, and progression-state tests.",
            "Content correctness or gameplay-loop regression fixtures.",
        ),
        risks=(
            "Experience quality needs rendered proof, not just source-level tests.",
            "Progress and content boundaries should be explicit before adding many lessons or levels.",
        ),
    ),
    Archetype(
        archetype_id="cli_library",
        label="CLI Or Library Project",
        keywords=("cli", "command line", "library", "sdk", "package", "tool", "developer tool"),
        components=(
            ComponentBlueprint("command-surface", "Command Surface", "cli", "src/cli", "CLI commands, arguments, output, and error contracts."),
            ComponentBlueprint("core-library", "Core Library", "library", "src/core", "Reusable runtime behavior and public API."),
            ComponentBlueprint("config", "Configuration", "library", "src/config", "Configuration loading, validation, and defaults."),
            ComponentBlueprint("tests", "Contract Tests", "test", "tests", "CLI, API, and compatibility regression suite."),
        ),
        diagrams=(
            DiagramBlueprint("command-topology", "Command Topology", "Show CLI, core library, configuration, and test contracts."),
            DiagramBlueprint("program-waves", "Program Waves", "Show API contract, CLI contract, compatibility, and release waves."),
            DiagramBlueprint("execution-flow", "Execution Flow", "Show command parsing, core execution, output, and failure handling."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Golden CLI output and error-code tests.",
            "Public API compatibility tests.",
            "Install/import smoke tests across supported environments.",
        ),
        risks=(
            "CLI output and API contracts should stay stable before downstream users depend on them.",
            "Configuration defaults must be explicit to avoid hidden environment coupling.",
        ),
    ),
    Archetype(
        archetype_id="general_application",
        label="General Software Project",
        keywords=("app", "application", "project", "platform", "system", "website", "service", "product", "build"),
        components=(
            ComponentBlueprint("user-experience", "User Experience", "application", "apps/web", "Primary user workflow and interface boundary."),
            ComponentBlueprint("application-core", "Application Core", "service", "src/app", "Core use cases, orchestration, and domain state."),
            ComponentBlueprint("data-boundary", "Data Boundary", "platform", "src/data", "Persistence, data access, and schema lifecycle."),
            ComponentBlueprint("integration-boundary", "Integration Boundary", "integration", "src/integrations", "External APIs, adapters, and integration contracts."),
            ComponentBlueprint("validation", "Validation", "test", "tests", "Acceptance, contract, runtime, and regression proof."),
        ),
        diagrams=(
            DiagramBlueprint("system-context", "System Context", "Show users, core application, data, integrations, and validation boundaries."),
            DiagramBlueprint("program-waves", "Program Waves", "Show discovery, foundation, first slice, and hardening release order."),
            DiagramBlueprint("component-topology", "Component Topology", "Show proposed component ownership and intended source paths."),
        ),
        waves=_PRODUCT_WAVES,
        validation_focus=(
            "Acceptance tests for the first user workflow.",
            "Contract tests at external boundaries.",
            "Browser or runtime proof for user-facing behavior.",
        ),
        risks=(
            "The first slice needs a real user workflow so governance does not become a generic bucket.",
            "External integrations should stay behind named boundaries from the beginning.",
        ),
    ),
)


def _words(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", str(value or "").casefold()) if token}


def _score_archetype(prompt: str, archetype: Archetype) -> int:
    normalized = " ".join(str(prompt or "").casefold().split())
    score = 0
    for keyword in archetype.keywords:
        token = str(keyword).casefold()
        if token in normalized:
            score += 3 if " " in token else 2
    prompt_words = _words(normalized)
    for keyword in archetype.keywords:
        key_words = _words(keyword)
        if key_words and key_words <= prompt_words:
            score += len(key_words)
    return score


def select_archetype(prompt: str) -> tuple[Archetype, float]:
    """Return the highest-scoring archetype and a bounded confidence score."""

    ranked = sorted(
        ((_score_archetype(prompt, archetype), archetype) for archetype in ARCHETYPES),
        key=lambda row: (row[0], 0 if row[1].archetype_id == "general_application" else 1, row[1].archetype_id),
        reverse=True,
    )
    score, archetype = ranked[0]
    if score <= 0:
        archetype = next(item for item in ARCHETYPES if item.archetype_id == "general_application")
        return archetype, 0.42
    return archetype, min(0.92, 0.48 + (score * 0.06))
