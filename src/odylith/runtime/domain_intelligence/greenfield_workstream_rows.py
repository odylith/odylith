"""Family-specific greenfield child workstream rows."""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile


def build_child_backlog_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
    domain_profile: GreenfieldDomainProfile,
) -> list[dict[str, Any]]:
    """Return product-specific child workstreams for the inferred greenfield family."""

    family = domain_profile.family
    if family == "defi_merchant_lending":
        return _merchant_lending_rows(title=title, components=components, diagrams=diagrams)
    if family == "defi_risk":
        return _defi_risk_rows(title=title, components=components, diagrams=diagrams)
    if family == "commerce":
        return _commerce_rows(title=title, components=components, diagrams=diagrams)
    return _generic_rows(title=title, components=components, diagrams=diagrams)


def _merchant_lending_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        _row(
            row_id="WS-01",
            title="Prove merchant borrower application and funding-status workflow",
            problem=(
                f"{title} needs a merchant-borrower workflow before implementation can reason about Shopify "
                "data consent, eligibility, funding state, repayment visibility, or regulated blocked states."
            ),
            customer="Shopify SMB merchant borrowers, capital-ops reviewers, and engineers building the first merchant-capital slice.",
            opportunity=(
                "Turn the lending intent into a narrow borrower path: submit capital request, evaluate eligibility, "
                "show offer or decline, expose liquidity and compliance blocks, and display funding plus repayment state."
            ),
            product_view=(
                "The merchant capital portal owns borrower application intake, Shopify snapshot consent, offer review, "
                "funding-status visibility, repayment-state visibility, and degraded states for stale data, compliance, "
                "or insufficient stablecoin liquidity."
            ),
            first_slice=(
                "Prove fixture-backed merchant application through eligible, declined, stale-shopify, "
                "liquidity_blocked, compliance_blocked, funded, and repayment_due states."
            ),
            success_metrics=[
                "Merchant borrower workflow has source-backed UI or API proof for application, offer, blocked, funded, and repayment-visible states.",
                "Borrower-visible funding state is derived from the credit-liquidity contract, not presentation-only labels.",
                "No first-release workstream depends on retail-buyer, retail-purchase, or card-processing semantics.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=[
                "Depends on the credit-liquidity core for eligibility, facility, disbursement, repayment, liquidity, and compliance state.",
                "Depends on lending fixtures for Shopify snapshot freshness, compliance status, stablecoin liquidity, and replayed ledger events.",
            ],
            interfaces=[
                "Merchant application intake with shop identifier, consent posture, requested capital amount, and operator/audit context.",
                "Offer and funding-status read model with eligibility, limit, terms, liquidity state, compliance state, disbursement state, and repayment state.",
                "Borrower-visible degraded-state contract for stale Shopify data, missing KYB, sanctions block, liquidity shortfall, and paused disbursement.",
            ],
            validation=[
                "Behavior proof covers eligible merchant, declined merchant, stale Shopify data, liquidity shortfall, compliance block, funded state, and repayment_due state.",
                "Negative proof confirms the first workflow makes no live Shopify, live DeFi, custody, private-key, or production stablecoin movement call.",
            ],
        ),
        _row(
            row_id="WS-02",
            title="Define credit facility, liquidity, and repayment contract",
            problem=(
                f"{title} cannot make trustworthy lending claims without a domain contract for Shopify snapshot "
                "freshness, eligibility, facility terms, compliance gates, stablecoin liquidity, disbursement, and repayment."
            ),
            customer="Engineers implementing credit and liquidity rules, capital-ops reviewers, and regulated-release reviewers.",
            opportunity=(
                "Make the money-state model explicit before portal, storage, treasury, or provider-adapter choices harden into accidental lending architecture."
            ),
            product_view=(
                "The credit-liquidity core owns deterministic merchant snapshot evaluation, facility lifecycle, compliance block, "
                "liquidity allocation, idempotent disbursement, and repayment replay semantics."
            ),
            first_slice=(
                "Write the pure facility contract and fixture-backed implementation consumed by the merchant portal: "
                "eligibility, terms, compliance state, liquidity state, disbursement state, and repayment state."
            ),
            success_metrics=[
                "Contract tests prove eligible, declined, stale-shopify, liquidity_blocked, compliance_blocked, duplicate-disbursement, and repayment-replay outcomes.",
                "The contract has no live Shopify, live DeFi protocol, custody, private-key, production credential, or legal-approval dependency.",
                "Facility, disbursement, and repayment state transitions are idempotent under retry and replay.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=[
                "Depends on confirmed merchant borrower workflow semantics and fixture schemas for Shopify, compliance, liquidity, and ledger events.",
                "Defers provider adapters, custody posture, legal underwriting decisions, and production treasury execution until release gates are explicit.",
            ],
            interfaces=[
                "Merchant snapshot schema with shop identity, sales history, chargeback posture, currency, consent, and freshness.",
                "Credit facility command/query contract for eligibility, limit, terms, compliance status, liquidity status, facility state, and repayment schedule.",
                "Idempotent stablecoin disbursement and repayment event contract with replay key, actor, amount, currency, timestamp, and audit evidence.",
            ],
            validation=[
                "Contract proof covers eligibility, decline, stale Shopify snapshot, liquidity shortfall, compliance block, duplicate disbursement, and repayment replay.",
                "Negative proof fails closed if a first-release path tries live protocol execution, custody, private keys, or production merchant data.",
            ],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title="Prove merchant lending fixtures and regulated proof harness",
            problem=(
                f"{title} needs closed-world lending evidence before release movement can claim merchant capital, "
                "stablecoin funding, repayment, compliance, or no-custody posture."
            ),
            customer="Release reviewers, capital-ops reviewers, future operators, and engineers maintaining regulated lending proof.",
            opportunity=(
                "Capture deterministic merchant-lending fixtures, replay checks, negative live-access guards, and release evidence while scope is small."
            ),
            product_view=(
                "The lending proof harness owns Shopify snapshot fixtures, KYB/AML/sanctions fault cases, liquidity scenarios, "
                "stablecoin ledger replay, duplicate disbursement checks, repayment replay, and regulated release proof."
            ),
            first_slice=(
                "Create the first fixture replay harness for eligible funding, declined application, stale Shopify data, "
                "liquidity shortfall, compliance block, duplicate disbursement, and repayment replay."
            ),
            success_metrics=[
                "Release proof runs locally with deterministic merchant, compliance, liquidity, disbursement, and repayment fixtures.",
                "Harness fails closed on live Shopify access, live DeFi protocol access, custody keys, production credentials, or unpinned external data.",
                "Proof report distinguishes user_intent, assumptions, and source-backed evidence for regulated lending claims.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=[
                "Depends on merchant portal visible-state contract and credit-liquidity domain contract before release proof expands.",
                "Depends on fixture schemas for Shopify snapshot freshness, compliance block, liquidity state, stablecoin ledger events, and repayment schedule.",
            ],
            interfaces=[
                "Scenario runner with merchant fixture, liquidity fixture, compliance state, expected facility state, and proof report output.",
                "Fixture schema for Shopify merchant data freshness, stablecoin ledger events, liquidity source posture, and compliance gate outcomes.",
                "Release-readiness report that lists passed fixtures, blocked live-access attempts, unresolved regulated assumptions, and retest triggers.",
            ],
            validation=[
                "Replay proof covers eligible, declined, stale-shopify, liquidity-blocked, compliance-blocked, duplicate-disbursement, repayment-replay, and no-live-access cases.",
                "Proof fails closed when fixture provenance, compliance state, replay key, or liquidity timestamp is missing.",
            ],
            priority="P2",
            evidence_tier="odylith_assumption",
        ),
    ]


def _defi_risk_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        _row(
            row_id="WS-01",
            title="Prove analyst watchlist and alert triage workflow",
            problem=(
                f"{title} needs one analyst-visible risk workflow before implementation can distinguish monitored "
                "subjects, stale data, unsupported chains, alert severity, confidence, and acknowledgement semantics."
            ),
            customer="Risk analysts and engineers implementing the first non-custodial risk-sentinel slice.",
            opportunity=(
                "Turn the risk-sentinel intent into a watchlist and alert triage path that can be tested with "
                "oracle, liquidity, protocol-health, and indexer fixtures before live providers exist."
            ),
            product_view=(
                "The console owns watchlist setup, risk-card rendering, data freshness and confidence disclosure, "
                "unsupported-chain fallback, and idempotent alert acknowledgement."
            ),
            first_slice=(
                "Prove one monitored subject through normal, empty watchlist, stale_oracle, missing_indexer, "
                "liquidity_shock, unsupported_chain, and acknowledged-alert states."
            ),
            success_metrics=[
                "Analyst workflow has source-backed UI or API proof for watchlist, risk-card, degraded-data, and acknowledgement states.",
                "Risk cards always carry freshness, confidence, and provenance metadata from the risk-signal contract.",
                "No first-release workflow implies custody, trading, live RPC dependence, or production financial advice.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=[
                "Depends on the risk signal engine for exposure snapshots, alert state, confidence, and data_state semantics.",
                "Depends on scenario fixtures for oracle freshness, liquidity shock, missing indexer, unsupported chain, and alert replay.",
            ],
            interfaces=[
                "Watchlist route or command for wallet, protocol, pool, strategy, or position-set subjects.",
                "Risk alert read model with severity, exposure, trigger reason, confidence, freshness, and acknowledgement state.",
                "Degraded-state contract for stale oracle, missing indexer, unsupported chain, and missing liquidity.",
            ],
            validation=[
                "Behavior proof covers normal triage, empty watchlist, stale oracle, missing indexer, liquidity shock, unsupported chain, and acknowledgement replay.",
                "Negative proof confirms no live RPC, signing, custody, trading, or production-advice path is required for first-release proof.",
            ],
        ),
        _row(
            row_id="WS-02",
            title="Define exposure, freshness, and alert contract",
            problem=(
                f"{title} cannot produce trustworthy risk cards without a domain contract for risk subject identity, "
                "exposure normalization, oracle/indexer freshness, liquidity shock, confidence, and alert transitions."
            ),
            customer="Engineers implementing risk math and reviewers checking non-custodial, no-advice boundaries.",
            opportunity="Make risk state explicit before live providers, notifications, storage, or UI choices blur the evidence boundary.",
            product_view=(
                "The risk signal engine owns deterministic exposure snapshots, data_state, confidence metadata, alert thresholds, "
                "severity transitions, and idempotent acknowledgement semantics."
            ),
            first_slice=(
                "Write the risk contract and minimal implementation consumed by the analyst workflow: risk subject, exposure snapshot, "
                "freshness/confidence, alert severity, data_state, and acknowledgement state."
            ),
            success_metrics=[
                "Contract tests prove threshold crossing, stale oracle, missing indexer, liquidity shock, unsupported chain, and acknowledgement replay.",
                "Stale or missing data cannot produce a normal numeric precision claim.",
                "The contract has no live RPC, custody, trading, wallet-signing, or production-advice dependency.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=["Depends on confirmed analyst workflow semantics and deterministic oracle, liquidity, protocol-health, and exposure fixtures."],
            interfaces=[
                "Risk subject schema for wallet, protocol, pool, strategy, or position-set identifiers.",
                "Exposure snapshot query with normalized assets, debt, collateral, protocol, chain, timestamp, and confidence fields.",
                "Alert evaluation command returning severity, trigger reason, threshold, data_state, confidence, and next state.",
            ],
            validation=["Contract proof covers threshold, stale data, missing liquidity/indexer, unsupported chain, and idempotent acknowledgement."],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title="Prove scenario replay and risk release harness",
            problem=f"{title} needs deterministic DeFi scenario proof before release movement can claim trustworthy risk detection.",
            customer="Risk reviewers, maintainers, and future operators who need reproducible risk evidence instead of a one-off demo.",
            opportunity="Capture oracle, liquidity, protocol-health, exposure, acknowledgement, and no-live-network proof while the sentinel is still small.",
            product_view="The scenario replay harness owns local fixtures, fault cases, replay reports, and release proof for console plus risk-engine behavior.",
            first_slice="Create the first scenario replay harness for price shock, liquidity drain, stale oracle, missing indexer, unsupported chain, and acknowledgement replay.",
            success_metrics=[
                "Replay proof runs locally with deterministic fixtures and no production credentials or live RPC.",
                "Harness fails closed on unpinned external data, wallet signing, custody, trading, or production advice surfaces.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=["Depends on the analyst workflow and risk-signal contract before hardening expands scope."],
            interfaces=["Defines scenario runner inputs, fixture schema, expected alert states, and release-readiness report output."],
            validation=["Replay proof covers price shock, liquidity drain, stale oracle, missing indexer, unsupported chain, and acknowledgement replay."],
            priority="P2",
            evidence_tier="odylith_assumption",
        ),
    ]


def _commerce_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        _row(
            row_id="WS-01",
            title="Prove shopper checkout and recovery workflow",
            problem=f"{title} needs a shopper-visible checkout path before implementation can avoid generic storefront scaffolding.",
            customer="Shoppers, commerce operators, and engineers implementing the first checkout slice.",
            opportunity="Turn broad commerce intent into a browse, cart, checkout, failure, retry, and completion path.",
            product_view="The storefront owns shopper entry, cart state, checkout handoff, visible payment failure, retry, and completion criteria.",
            first_slice="Prove the smallest shopper checkout path with happy, empty-cart, failed-payment, retry, and completed states.",
            success_metrics=[
                "Checkout workflow has source-backed browser proof before the next wave starts.",
                "Failed-payment and retry states remain visible and do not create duplicate order drafts.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=["Depends on the checkout/order contract for cart, order draft, payment handoff, retry, and recovery state."],
            interfaces=["Defines the storefront route or command plus visible checkout fallback states."],
            validation=["Browser proof covers happy path, empty cart, failed payment, retry, and completion."],
        ),
        _row(
            row_id="WS-02",
            title="Define checkout order and payment-state contract",
            problem=f"{title} cannot prove checkout without a named contract for cart, order draft, payment handoff, callback replay, and recovery state.",
            customer="Engineers implementing checkout/order boundaries and reviewers checking payment correctness.",
            opportunity="Make checkout and order invariants explicit before storage, provider SDK, or UI choices harden into accidental architecture.",
            product_view="The checkout/order core owns cart validation, idempotent order draft creation, payment callback handling, and recovery transitions.",
            first_slice="Write the checkout/order contract and minimal implementation consumed by the shopper workflow.",
            success_metrics=[
                "Contract tests prove order-draft idempotency, failed-payment recovery, and callback replay.",
                "Component records capture checkout/order interfaces, dependencies, and verification commands.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=["Depends on confirmed checkout semantics and defers provider SDK selection until technical planning."],
            interfaces=["Defines cart, order draft, payment result, retry, and callback event contracts."],
            validation=["Contract tests cover valid checkout, invalid cart, failed payment, retry, and idempotent callback replay."],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title="Prove checkout replay and release harness",
            problem=f"{title} needs repeatable checkout proof, fallback checks, and release-readiness evidence before the first slice can be promoted.",
            customer="Maintainers, reviewers, and future operators who need reproducible validation instead of a one-off manual demo.",
            opportunity="Capture checkout smoke commands, sandbox fixtures, replay reports, and release proof while the program is still small.",
            product_view="A checkout proof harness records happy, empty-cart, failed-payment, retry, callback-replay, accessibility, and recovery checks.",
            first_slice="Create the first smoke and replay harness around the checkout workflow and order contract.",
            success_metrics=[
                "Release proof runs locally with deterministic fixtures and no production credentials.",
                "Replay proof shows one order draft under repeated checkout and callback duplication.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=["Depends on WS-01 and WS-02 behavior proof before hardening expands scope."],
            interfaces=["Defines local smoke commands, fixture inputs, report output, and release-readiness checks."],
            validation=["Smoke proof runs under the repo-native toolchain and fails closed on missing fixtures or stale proof."],
            priority="P2",
            evidence_tier="odylith_assumption",
        ),
    ]


def _generic_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        _row(
            row_id="WS-01",
            title="Prove first product workflow",
            problem=f"{title} needs one concrete product workflow before implementation can avoid generic scaffolding.",
            customer="Primary users or operators of the proposed product and the engineers implementing the first slice.",
            opportunity="Turn broad intent into a narrow behavior path that can be implemented, tested, and reviewed without claiming the whole system is done.",
            product_view="The first workflow owns entry, happy path, empty or degraded state, and user-visible completion criteria.",
            first_slice="Implement the smallest product path with normal, empty, and degraded/error state proof.",
            success_metrics=[
                "The first workflow has a source-backed test or browser proof before the next wave starts.",
                "The workflow boundary appears in component specs and architecture diagrams with linked workstream traceability.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=["Depends on the domain contract workstream for the data and command boundary used by the first workflow."],
            interfaces=["Defines the first user-facing route, command, CLI, or service entrypoint plus visible fallback states."],
            validation=["Repository-native behavior proof covers the first workflow normal path and at least one degraded or empty state."],
        ),
        _row(
            row_id="WS-02",
            title="Define first domain contract",
            problem=f"{title} cannot scale beyond the first workflow without a named domain contract for state, commands, ownership, and invariants.",
            customer="Engineers implementing source boundaries and reviewers checking correctness of data and state transitions.",
            opportunity="Make the domain core explicit before storage, API, worker, or UI choices harden into accidental architecture.",
            product_view="A domain component owns the first state model, commands, invariants, and integration handoff used by the first workflow.",
            first_slice="Write the domain contract and minimal implementation that the first workflow consumes.",
            success_metrics=[
                "Domain contract tests prove the first state transition and invalid input rejection.",
                "Component records capture the domain component interfaces, dependencies, and verification commands.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=["Depends on confirmed first-workflow semantics and defers storage selection until technical planning."],
            interfaces=["Defines the initial command, query, event, or file contract consumed by the first workflow."],
            validation=["Contract tests cover valid transition, invalid input, and idempotent or retry behavior where relevant."],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title="Prove release harness",
            problem=f"{title} needs repeatable proof, fallback checks, and release-readiness evidence before the first slice can be promoted.",
            customer="Maintainers, reviewers, and future operators who need reproducible validation instead of a one-off manual demo.",
            opportunity="Capture the first release verification commands, smoke fixtures, and dashboard refresh proof while the program is still small.",
            product_view="A verification harness records the first release smoke, regression checks, accessibility or safety gates, and operational recovery expectations.",
            first_slice="Create the first smoke or regression harness around the first workflow and domain contract.",
            success_metrics=[
                "Release proof runs locally with deterministic fixtures and no production credentials.",
                "Governance records refresh after the proof and show the same first release lane.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=["Depends on WS-01 and WS-02 behavior proof before hardening expands scope."],
            interfaces=["Defines local smoke commands, fixture inputs, report output, and release-readiness checks."],
            validation=["Smoke proof runs under the repo-native toolchain and fails closed on missing fixtures or stale surfaces."],
            priority="P2",
            evidence_tier="odylith_assumption",
        ),
    ]


def _row(
    *,
    row_id: str,
    title: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    first_slice: str,
    success_metrics: list[str],
    component_focus: list[str],
    related_diagram_slugs: list[str],
    dependencies: list[str],
    interfaces: list[str],
    validation: list[str],
    priority: str = "P1",
    sizing: str = "M",
    complexity: str = "Medium",
    evidence_tier: str = "user_intent",
) -> dict[str, Any]:
    return {
        "id": row_id,
        "title": title,
        "problem": problem,
        "customer": customer,
        "opportunity": opportunity,
        "product_view": product_view,
        "recommended_first_slice": first_slice,
        "success_metrics": success_metrics,
        "component_focus": component_focus,
        "related_diagram_slugs": related_diagram_slugs,
        "dependencies": dependencies,
        "interfaces": interfaces,
        "validation": validation,
        "priority": priority,
        "sizing": sizing,
        "complexity": complexity,
        "evidence_tier": evidence_tier,
    }
