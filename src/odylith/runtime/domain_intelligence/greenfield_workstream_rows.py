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
    if family == "defi_risk":
        return _defi_risk_rows(title=title, components=components, diagrams=diagrams)
    if family == "capital_merchant_lending":
        return _merchant_capital_rows(title=title, components=components, diagrams=diagrams)
    if family == "commerce":
        return _commerce_rows(title=title, components=components, diagrams=diagrams)
    if family == "clinical_trial_matching":
        return _profiled_rows(
            title=title,
            components=components,
            diagrams=diagrams,
            workflow_title="Prove patient-to-trial eligibility review workflow",
            contract_title="Define patient, protocol, consent, and eligibility contract",
            proof_title="Prove clinical matching fixtures and review harness",
            actor="patient coordinator",
            workflow_focus="patient intake, oncology protocol criteria, consent state, eligibility explanation, and manual review",
            domain_focus="patient profile, protocol criteria, inclusion/exclusion rules, consent gate, match confidence, and review disposition",
            proof_focus="eligible, excluded, missing-consent, missing-biomarker, stale-protocol, and manual-review scenarios",
            risk="clinical trial matching can imply eligibility or consent without protocol-backed evidence",
        )
    if family == "legal_intake":
        return _profiled_rows(
            title=title,
            components=components,
            diagrams=diagrams,
            workflow_title="Prove immigration client intake and attorney triage workflow",
            contract_title="Define case, document, consent, and review contract",
            proof_title="Prove confidential intake fixtures and privacy harness",
            actor="intake operator",
            workflow_focus="client intake, document collection, eligibility summary, urgency flags, consent, and attorney handoff",
            domain_focus="case type, document requirements, missing evidence, confidentiality state, risk flags, and attorney-review disposition",
            proof_focus="complete intake, missing documents, urgent deadline, consent block, conflict flag, and attorney-review scenarios",
            risk="legal intake can imply advice, filing readiness, or representation before attorney review",
        )
    if family == "bioinformatics_variant_pipeline":
        return _profiled_rows(
            title=title,
            components=components,
            diagrams=diagrams,
            workflow_title="Prove sample-to-variant review workflow",
            contract_title="Define sample, QC, variant, and VCF output contract",
            proof_title="Prove sequencing pipeline reproducibility harness",
            actor="bioinformatics analyst",
            workflow_focus="sample intake, sequencing run review, QC status, variant review, VCF output, and analyst handoff",
            domain_focus="sample metadata, QC thresholds, FASTQ/BAM/VCF fixture semantics, variant normalization, provenance, and reproducible output",
            proof_focus="passing sample, failed QC, empty variant set, malformed VCF, reference mismatch, and deterministic rerun scenarios",
            risk="variant analysis can imply reproducible biological findings before QC, reference, and VCF proof exists",
        )
    return _generic_rows(title=title, components=components, diagrams=diagrams)


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
                "The risk workflow needs one analyst-visible path before implementation can distinguish monitored "
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
                "Risk cards cannot be trustworthy without a domain contract for risk subject identity, "
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
            problem="The risk sentinel needs deterministic scenario proof before release movement can claim trustworthy risk detection.",
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
            problem="The checkout product needs a shopper-visible recovery path before implementation can avoid generic storefront scaffolding.",
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
            problem="Checkout cannot be proven without a named contract for cart, order draft, payment handoff, callback replay, and recovery state.",
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
            problem="The checkout slice needs repeatable proof, fallback checks, and release-readiness evidence before it can be promoted.",
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


def _merchant_capital_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        _row(
            row_id="WS-01",
            title="Prove merchant funding request and offer review workflow",
            problem=(
                "Merchants cannot trust a capital product unless one funding request clearly shows store-signal readiness, "
                "eligibility, offer terms, manual approval, funding status, repayment state, and unresolved capital risk."
            ),
            customer="Merchants, risk operators, treasury reviewers, and engineers implementing the first funding slice.",
            opportunity=(
                "Turn broad capital intent into a merchant request, underwriting review, offer, approval, payout status, "
                "repayment evidence, and ledger-reconciliation path."
            ),
            product_view=(
                "B-002 proves the visible merchant journey: request capital, review store-data readiness, see an offer or rejection, "
                "wait for manual risk and treasury approval, then track funding and repayment evidence."
            ),
            first_slice=(
                "Prove one merchant profile through requested, missing-data, eligible-offer, manual-risk-review, "
                "manual-treasury-approval, funded, repayment-recorded, and reconciled states."
            ),
            success_metrics=[
                "Merchant workflow has source-backed UI or API proof for request, offer, approval, funding status, and repayment evidence.",
                "Offer terms always carry source-signal provenance, policy trace, approval owner, and evidence tier.",
                "No first-release workflow implies live custody, automated protocol routing, or production lending compliance readiness.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=[
                "Depends on the underwriting and facility contract for eligibility, offer terms, approval state, facility state, and repayment schedule.",
                "Depends on funding evidence fixtures for source store data, settlement status, repayment event, and ledger reconciliation.",
            ],
            interfaces=[
                "Merchant funding request command with business profile, requested amount, store signal references, and consent posture.",
                "Offer review read model with eligibility, approved amount, pricing, repayment terms, policy trace, and funding status.",
                "Blocked-state contract for missing store data, unresolved lender-of-record, custody, repayment rail, or settlement rail.",
            ],
            validation=[
                "Behavior proof covers request created, missing store data, eligible offer, rejected request, manual approval, funded, repayment-recorded, and reconciled states.",
                "Negative proof confirms no production merchant data, live bank movement, stablecoin custody, or DeFi protocol execution is required for first-release proof.",
            ],
        ),
        _row(
            row_id="WS-02",
            title="Define eligibility, offer, approval, and repayment contract",
            problem=(
                "Funding offers cannot be trustworthy without a domain contract for merchant source signals, "
                "eligibility, pricing, repayment terms, risk approval, treasury approval, facility state, and ledger evidence."
            ),
            customer="Engineers implementing underwriting semantics and reviewers checking credit, treasury, and compliance boundaries.",
            opportunity="Make capital state explicit before live providers, custody choices, settlement rails, repayment collection, or UI choices blur the evidence boundary.",
            product_view=(
                "The underwriting and facility core owns deterministic merchant profile normalization, eligibility, offer trace, "
                "manual approval state, funding facility state, and repayment schedule semantics."
            ),
            first_slice=(
                "Write the funding contract and minimal implementation consumed by the merchant workflow: merchant profile, "
                "source signals, eligibility, offer, approval, facility state, repayment schedule, and ledger reference."
            ),
            success_metrics=[
                "Contract tests prove missing-data rejection, eligibility rejection, offer generation, manual approval, payout block, funding state, and repayment transition.",
                "Lender-of-record, risk owner, treasury owner, custody, settlement rail, repayment rail, and protocol exposure cannot remain hidden in a normal success claim.",
                "The contract has no live merchant data, production lending decision, stablecoin custody, bank movement, or DeFi execution dependency.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=["Depends on confirmed merchant workflow semantics and deterministic merchant, underwriting, approval, settlement, and repayment fixtures."],
            interfaces=[
                "Merchant profile schema with source signal provenance, consent, freshness, and risk flags.",
                "Eligibility and offer command returning decision state, amount, pricing, repayment terms, policy trace, and approval requirements.",
                "Facility state query for requested, eligible, offered, approved, funded, repaying, repaid, rejected, and blocked states.",
            ],
            validation=["Contract proof covers source signals, eligibility, offer trace, approval, settlement status, repayment state, and ledger reconciliation."],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title="Prove funding, repayment, and ledger evidence harness",
            problem="The capital-flow path needs deterministic proof before release movement can claim trustworthy funding or repayment behavior.",
            customer="Risk reviewers, treasury reviewers, maintainers, and future operators who need reproducible funding evidence instead of a one-off demo.",
            opportunity=(
                "Capture source store signals, underwriting scenarios, manual approval, payout status, repayment event, "
                "ledger reconciliation, and no-live-money proof while the product is still small."
            ),
            product_view=(
                "The funding evidence harness owns local fixtures, scenario replay, approval reports, settlement evidence, "
                "repayment evidence, ledger reconciliation, and release proof."
            ),
            first_slice=(
                "Create the first scenario replay harness for missing data, rejected request, eligible offer, manual approval, "
                "payout blocked, funded, repayment recorded, and ledger reconciliation."
            ),
            success_metrics=[
                "Replay proof runs locally with deterministic fixtures and no production merchant data, credentials, custody, bank movement, or live protocol calls.",
                "Harness fails closed on unlabeled lender-of-record, custody, loss-owner, settlement, repayment, or protocol-exposure assumptions.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=["Depends on the merchant workflow and underwriting/facility contract before hardening expands scope."],
            interfaces=["Defines scenario runner inputs, merchant fixture schema, expected funding states, repayment events, and release-readiness report output."],
            validation=[
                "Replay proof covers merchant source data, offer trace, manual approval, funding status, repayment event, and ledger reconciliation."
            ],
            priority="P2",
            evidence_tier="odylith_assumption",
        ),
    ]


def _profiled_rows(
    *,
    title: str,
    components: Mapping[str, str],
    diagrams: Mapping[str, str],
    workflow_title: str,
    contract_title: str,
    proof_title: str,
    actor: str,
    workflow_focus: str,
    domain_focus: str,
    proof_focus: str,
    risk: str,
) -> list[dict[str, Any]]:
    return [
        _row(
            row_id="WS-01",
            title=workflow_title,
            problem=f"The {actor} workflow needs a concrete first path before implementation can avoid generic scaffolding.",
            customer=f"{actor.title()}s, reviewers, and engineers implementing the first product slice.",
            opportunity=f"Turn broad intent into a narrow workflow around {workflow_focus}.",
            product_view=f"The first workflow owns {workflow_focus}.",
            first_slice=f"Prove {workflow_focus} with normal, missing-data, blocked, degraded, and review-ready states.",
            success_metrics=[
                f"The {actor} workflow has implementation-backed proof for {workflow_focus}.",
                "Visible states are derived from the domain contract, not presentation-only labels.",
                f"Release proof explicitly guards against the core risk: {risk}.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=[f"Depends on the domain contract for {domain_focus}."],
            interfaces=[f"Defines the first route or command for {workflow_focus}."],
            validation=[f"Behavior proof covers {proof_focus}."],
        ),
        _row(
            row_id="WS-02",
            title=contract_title,
            problem=f"The product cannot make trustworthy claims without a named contract for {domain_focus}.",
            customer="Engineers implementing source boundaries and reviewers checking correctness, safety, and evidence quality.",
            opportunity=f"Make {domain_focus} explicit before storage, provider, UI, or deployment choices harden into accidental architecture.",
            product_view=f"The domain component owns {domain_focus}.",
            first_slice=f"Write the domain contract and minimal implementation for {domain_focus}.",
            success_metrics=[
                f"Contract tests prove {proof_focus}.",
                "Invalid, stale, missing, or blocked inputs cannot produce a normal success claim.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=[f"Depends on confirmed {actor} workflow semantics and deterministic fixtures."],
            interfaces=[f"Defines command, query, schema, event, or module contracts for {domain_focus}."],
            validation=[f"Contract proof covers {proof_focus}."],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title=proof_title,
            problem="The first slice needs deterministic proof before release movement can claim it is real.",
            customer="Reviewers, maintainers, and future operators who need reproducible evidence instead of a one-off demo.",
            opportunity=f"Capture fixture, replay, report, and release-readiness evidence for {proof_focus}.",
            product_view=f"The proof harness owns deterministic scenarios for {proof_focus}.",
            first_slice=f"Create the first proof harness for {proof_focus}.",
            success_metrics=[
                "Proof runs locally with deterministic fixtures and no production data or credentials.",
                "Proof fails closed on missing fixtures, skipped assertions, or unpinned external data.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=["Depends on WS-01 behavior proof and WS-02 contract proof before hardening expands scope."],
            interfaces=["Defines scenario runner inputs, fixture schema, expected states, and proof report output."],
            validation=[f"Replay proof covers {proof_focus}."],
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
    project = title.strip() or "Greenfield Product"
    product_noun = project.removeprefix("A ").removeprefix("An ").strip() or project
    product_phrase = "the proposed product"
    return [
        _row(
            row_id="WS-01",
            title=f"Prove {product_noun} first workflow",
            problem="The proposed product needs one concrete workflow before implementation can avoid generic scaffolding.",
            customer=f"Primary {product_noun.lower()} users or operators and the engineers implementing the first slice.",
            opportunity=(
                f"Turn {product_noun.lower()} intent into a narrow behavior path that can be implemented, "
                "tested, and reviewed without claiming the whole system is done."
            ),
            product_view=(
                f"The first {product_noun.lower()} workflow owns entry, happy path, empty or degraded state, "
                "and user-visible completion criteria."
            ),
            first_slice=f"Implement the smallest {product_noun.lower()} path with normal, empty, and degraded/error state proof.",
            success_metrics=[
                f"The first {product_noun.lower()} workflow has a source-backed test or browser proof before the next wave starts.",
                f"The {product_noun.lower()} workflow boundary appears in component specs and architecture diagrams with linked workstream traceability.",
            ],
            component_focus=[components["experience"], components["domain"]],
            related_diagram_slugs=[diagrams["overview"], diagrams["slice"], diagrams["component_map"]],
            dependencies=[f"Depends on the {product_noun.lower()} product-model workstream for the data and command boundary used by the first workflow."],
            interfaces=[f"Defines the first {product_noun.lower()} user-facing route, command, CLI, or service entrypoint plus visible fallback states."],
            validation=[f"Repository-native behavior proof covers the first {product_noun.lower()} workflow normal path and at least one degraded or empty state."],
        ),
        _row(
            row_id="WS-02",
            title=f"Define {product_noun} product model and invariants",
            problem=f"{product_phrase.title()} cannot scale beyond the first workflow without a named product model for state, commands, ownership, and invariants.",
            customer=f"Engineers implementing {product_noun.lower()} source boundaries and reviewers checking correctness of data and state transitions.",
            opportunity=(
                f"Make the {product_noun.lower()} state model explicit before storage, API, worker, or UI choices "
                "harden into accidental architecture."
            ),
            product_view=f"The {product_noun.lower()} product model owns first state, commands, invariants, and integration handoff used by the first workflow.",
            first_slice=f"Write the {product_noun.lower()} model contract and minimal implementation that the first workflow consumes.",
            success_metrics=[
                f"{product_noun} model contract tests prove the first state transition and invalid input rejection.",
                f"Component records capture {product_noun.lower()} model interfaces, dependencies, and verification commands.",
            ],
            component_focus=[components["domain"]],
            related_diagram_slugs=[diagrams["component_map"], diagrams["domain_state"], diagrams["slice"]],
            dependencies=[f"Depends on confirmed {product_noun.lower()} first-workflow semantics and defers storage selection until technical planning."],
            interfaces=[f"Defines the initial {product_noun.lower()} command, query, event, or file contract consumed by the first workflow."],
            validation=[f"Contract tests cover valid {product_noun.lower()} transition, invalid input, and idempotent or retry behavior where relevant."],
            evidence_tier="odylith_assumption",
        ),
        _row(
            row_id="WS-03",
            title=f"Prove {product_noun} evidence harness",
            problem="The first slice needs repeatable proof, fallback checks, and release-readiness evidence before it can be promoted.",
            customer=f"Maintainers, reviewers, and future {product_noun.lower()} operators who need reproducible validation instead of a one-off manual demo.",
            opportunity=f"Capture {product_noun.lower()} verification commands, smoke fixtures, and release evidence while the program is still small.",
            product_view=f"The {product_noun.lower()} evidence harness records first-release smoke, regression checks, accessibility or safety gates, and operational recovery expectations.",
            first_slice=f"Create the first smoke or regression harness around the {product_noun.lower()} workflow and product model.",
            success_metrics=[
                f"{product_noun} release proof runs locally with deterministic fixtures and no production credentials.",
                f"{product_noun} release evidence shows the same first release lane after proof runs.",
            ],
            component_focus=[components["validation"]],
            related_diagram_slugs=[diagrams["validation_release"], diagrams["domain_state"]],
            dependencies=[f"Depends on {product_noun.lower()} behavior proof and product-model proof before hardening expands scope."],
            interfaces=[f"Defines local {product_noun.lower()} smoke commands, fixture inputs, report output, and release-readiness checks."],
            validation=[f"Smoke proof runs under the repo-native toolchain and fails closed on missing {product_noun.lower()} fixtures or stale release evidence."],
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
    rationale_lines: list[str] | None = None,
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
        "rationale_lines": rationale_lines
        or _product_rationale_lines(
            opportunity=opportunity,
            first_slice=first_slice,
            success_metrics=success_metrics,
            priority=priority,
        ),
    }


def _product_rationale_lines(
    *,
    opportunity: str,
    first_slice: str,
    success_metrics: list[str],
    priority: str,
) -> list[str]:
    proof = next((str(item).strip() for item in success_metrics if str(item).strip()), first_slice)
    deferred = (
        "Broader automation, live integrations, and release expansion stay outside this lane until the first proof path passes."
        if priority == "P1"
        else "Release hardening expands only after the first workflow and contract prove the product boundary."
    )
    return [
        f"- why now: {opportunity}",
        f"- expected outcome: {first_slice}",
        "- tradeoff: keep the first release narrow enough that a reviewer can see the user path, owner, risk, and proof together.",
        f"- deferred for now: {deferred}",
        f"- ranking basis: {proof}",
    ]
