"""Family-specific term tables for greenfield workstream intelligence."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile


def workstream_family_terms(*, domain_profile: GreenfieldDomainProfile, title: str) -> dict[str, Any]:
    """Return domain-specific terms used by workstream intelligence builders."""

    if domain_profile.family == "defi_risk":
        return _defi_terms()
    if domain_profile.family == "capital_merchant_lending":
        return _merchant_capital_terms()
    if domain_profile.family == "commerce":
        return _commerce_terms()
    return _generic_terms(title=title)


def _defi_terms() -> dict[str, Any]:
    return {
        "domain_phrase": "DeFi risk sentinel",
        "project_objective": "monitor wallet and protocol exposure, detect liquidation or liquidity risk, and surface trustworthy analyst actions.",
        "stakeholder_outcome": "an analyst can triage one monitored subject, understand stale or missing data, and acknowledge alerts without custody or trade execution claims.",
        "failure_mode": "analysts may trust incomplete oracle, indexer, liquidity, or protocol-health data as precise financial advice.",
        "non_goals": "no custody, no trading, no production financial advice, no live-chain dependency, no private-key handling in the first release.",
        "decision_pressure": "risk math needs deterministic fixtures before live providers or broad protocol coverage.",
        "primary_validation_command": "scenario replay plus contract/browser proof over risk snapshots and alert states",
        "topology_spine": "watchlist/console consumes the risk signal engine; the risk signal engine consumes fixture-backed oracle, liquidity, position, and protocol-health inputs; the replay harness validates both.",
        "constraints": [
            "No live RPC, wallet signing, custody, private keys, or production trade execution in the first release.",
            "Wallet identifiers are pseudonymous; positions, holdings, and derived risk readouts are sensitive financial data.",
            "Risk scores must carry freshness and confidence metadata so stale oracle or missing liquidity cannot look normal.",
        ],
        "evidence_counts": [
            "DeFi evidence must include threshold-crossing, stale-oracle, missing-indexer, liquidity-shock, and idempotent acknowledgement fixtures.",
        ],
        "assumptions": [
            "Assumption: first release monitors one subject with deterministic fixture data, not broad multi-chain indexing.",
            "Assumption: analyst acknowledgement is audit-relevant even before production authentication exists.",
        ],
        "invariants": [
            "A stale or missing price cannot produce a normal precision claim.",
            "A risk alert cannot be acknowledged without preserving actor, subject, severity, and timestamp evidence.",
            "Fixture replay must be deterministic for the same price, liquidity, oracle, and protocol-health inputs.",
        ],
        "risks": [
            "Data risk: provider drift or stale oracle values can understate exposure or mask liquidation paths.",
            "Compliance risk: the product can be misread as custody, trading, or financial advice unless boundaries stay explicit.",
            "Abuse risk: alert spam or acknowledgement replay can hide a real risk transition.",
        ],
        "validation_obligations": [
            "Claim: stale oracle data is degraded. Method: fixture where price age exceeds freshness threshold and numeric claims are suppressed.",
            "Claim: liquidity shock changes severity. Method: replay fixture with deterministic before/after liquidity depth and alert threshold.",
            "Claim: acknowledgements are idempotent. Method: repeated acknowledgement keeps one durable state transition with audit evidence.",
        ],
        "invalidation_rules": [
            "If oracle freshness, indexer provenance, chain support, liquidity model, or protocol-health inputs change, invalidate risk confidence, data_state proof, and architecture data-flow claims.",
            "If non-custody, no-advice, audit, or live-RPC posture changes, block release promotion until compliance risk, authority, and proof obligations are rewritten.",
        ],
        "metrics": [
            "Domain metric: stale or missing data detection rate across fixture scenarios.",
            "Risk metric: false-normal fixture count for liquidation, liquidity, and protocol-health stress cases.",
            "UX metric: analyst can distinguish fresh, stale, missing, and unsupported-chain states without hidden precision.",
        ],
        "transfer_priors": [
            "Pattern: keep risk math pure and deterministic before adding live providers.",
            "Pattern: treat freshness, confidence, and provenance as first-class fields in every derived financial readout.",
        ],
    }


def _commerce_terms() -> dict[str, Any]:
    return {
        "domain_phrase": "commerce checkout",
        "project_objective": "prove browse-to-checkout, order draft, payment handoff, and failed-payment recovery without production payment claims.",
        "stakeholder_outcome": "a shopper can move through the first purchase path while operators can verify idempotent recovery behavior.",
        "failure_mode": "orders can double-submit, payment failures can disappear, or shopper state can imply a purchase that never completed.",
        "non_goals": "no live payment credentials, production fulfillment, tax/shipping complexity, or broad merchandising automation in the first release.",
        "decision_pressure": "checkout correctness and recovery beat storefront breadth.",
        "primary_validation_command": "browser proof plus checkout/order contract tests",
        "topology_spine": "storefront consumes checkout/order core; checkout/order core consumes product and price snapshots; the proof harness replays payment success, failure, and callback duplication.",
        "constraints": [
            "Use sandbox payment fixtures only; never require live provider credentials for first-release proof.",
            "Order creation must be idempotent under retry and replay.",
            "Checkout reads immutable price and inventory snapshots rather than mutable merchandising state.",
        ],
        "evidence_counts": [
            "Commerce evidence must include happy path, empty cart, failed payment, and replayed callback proof.",
        ],
        "assumptions": [
            "Assumption: first release proves one checkout path before account, catalog, or fulfillment breadth expands.",
        ],
        "invariants": [
            "A payment callback replay cannot create a second order draft.",
            "A failed payment must remain visible and recoverable to the shopper.",
            "Checkout cannot mutate catalog truth or treat live inventory as already reserved without a reservation contract.",
        ],
        "risks": [
            "Payment risk: non-idempotent retries can double-create orders.",
            "Trust risk: storefront success state can hide provider failure or late callback recovery.",
        ],
        "validation_obligations": [
            "Claim: checkout is idempotent. Method: repeated checkout command and replayed callback produce one order draft.",
            "Claim: failed payment is recoverable. Method: browser proof shows explicit failure and retry state.",
            "Claim: price snapshot is stable. Method: contract test proves checkout uses immutable snapshot input.",
        ],
        "invalidation_rules": [
            "If payment provider, sandbox semantics, price snapshot, inventory reservation, or callback ordering changes, invalidate checkout idempotency and recovery proof.",
            "If production payment, fulfillment, tax, shipping, or irreversible reservation enters scope, block release promotion until provider and compliance gates are explicit.",
        ],
        "metrics": [
            "Domain metric: duplicate order count under retry and callback replay.",
            "UX metric: shopper-visible recovery states proven in browser.",
        ],
        "transfer_priors": [
            "Pattern: isolate payment handoff and order state before adding fulfillment breadth.",
        ],
    }


def _merchant_capital_terms() -> dict[str, Any]:
    return {
        "domain_phrase": "merchant capital",
        "project_objective": (
            "turn verified merchant performance into reviewable funding offers, approval decisions, payout status, "
            "and repayment evidence before live treasury automation."
        ),
        "stakeholder_outcome": (
            "a merchant can request funding, understand an offer or rejection, receive manually approved funding, "
            "and see repayment evidence without hidden credit or custody assumptions."
        ),
        "failure_mode": (
            "the product can imply approved credit, live payout, repayment obligation, lender-of-record certainty, "
            "or protocol safety before underwriting and treasury proof exist."
        ),
        "non_goals": (
            "no automated DeFi routing, production stablecoin custody, live bank movement, marketplace capital providers, "
            "or unreviewed lending compliance claims in the first release."
        ),
        "decision_pressure": "underwriting traceability and manual treasury approval beat live liquidity automation.",
        "primary_validation_command": "scenario replay plus eligibility, approval, settlement, repayment, and ledger proof",
        "topology_spine": (
            "merchant funding workspace consumes the underwriting and facility core; the facility core consumes source-backed "
            "store signals; the evidence harness proves offer, approval, payout, repayment, and reconciliation state."
        ),
        "constraints": [
            "Merchant source signals must carry provenance, consent, and freshness before underwriting claims can be trusted.",
            "Funding cannot be marked approved without explicit risk and treasury owner review.",
            "Stablecoin, bank, or DeFi protocol movement stays fixture-backed until custody, lender-of-record, and loss ownership are decided.",
        ],
        "evidence_counts": [
            "Merchant-capital evidence must include source-signal provenance, offer trace, manual approval, settlement status, repayment event, and ledger reconciliation.",
        ],
        "assumptions": [
            "Assumption: first release proves one merchant funding journey with manual approval, not automated capital routing.",
            "Assumption: repayment and ledger evidence are reviewable before collection automation exists.",
        ],
        "invariants": [
            "An offer cannot be treated as funded until treasury approval and settlement evidence exist.",
            "A repayment schedule cannot be hidden from the merchant or detached from the facility state.",
            "Any lender-of-record, loss-owner, custody, or protocol-exposure uncertainty remains visible as a blocker.",
        ],
        "risks": [
            "Credit risk: weak eligibility or offer semantics can approve the wrong merchant, amount, pricing, or repayment structure.",
            "Treasury risk: stablecoin or protocol movement can hide custody, liquidity, settlement, and loss ownership.",
            "Compliance risk: lending, KYB, AML, disclosure, and lender-of-record posture can be overstated before review.",
        ],
        "validation_obligations": [
            "Claim: offer trace is explainable. Method: fixture-backed store signals produce eligibility, amount, pricing, terms, and policy trace.",
            "Claim: funding is manually approved. Method: approval fixture records risk owner, treasury owner, funding source, and payout status.",
            "Claim: repayment evidence reconciles. Method: repayment event updates facility state and ledger report without live money movement.",
        ],
        "invalidation_rules": [
            "If lender of record, loss owner, repayment rail, settlement rail, custody model, or protocol exposure changes, invalidate offer, approval, and release-gate claims.",
            "If live merchant data, stablecoin movement, bank movement, or DeFi protocol execution enters scope, block promotion until security, compliance, treasury, and reconciliation proof are rewritten.",
        ],
        "metrics": [
            "Domain metric: percentage of offer terms explained by source-backed store signals and policy trace.",
            "Risk metric: unresolved lender, repayment, custody, loss-owner, and settlement questions before release.",
            "Evidence metric: first journey has offer, approval, funding-status, repayment, and ledger proof.",
        ],
        "transfer_priors": [
            "Pattern: prove underwriting and manual approval before automating liquidity or protocol routing.",
            "Pattern: treat lender-of-record, custody, repayment, and loss ownership as first-class project questions.",
        ],
    }


def _generic_terms(*, title: str) -> dict[str, Any]:
    compact = title.replace(" App", "").replace(" Platform", "").strip() or "product"
    lower = compact.lower()
    return {
        "domain_phrase": f"{lower} greenfield",
        "project_objective": f"turn the {lower} prompt into a coherent first workflow, product model, and evidence harness.",
        "stakeholder_outcome": f"the operator can start one {lower} implementation slice without rediscovering purpose, boundaries, proof, and risks.",
        "failure_mode": "agents may build plausible scaffolding that is disconnected from domain rules, users, state, and validation.",
        "non_goals": "no broad platform, production readiness, external integration, or source-backed claim until the first slice proves it.",
        "decision_pressure": "domain clarity and proof gates beat broad scaffold volume.",
        "primary_validation_command": "repo-native tests for normal, empty, degraded, and failure states",
        "topology_spine": "operator workspace consumes the product model; evidence harness proves both; release evidence preserves the trace.",
        "constraints": [
            "Keep the first slice small enough to prove with local fixtures and repository-native tests.",
            "Do not infer runtime, storage, or deployment ownership from project title alone.",
            "Keep data, auth, audit, accessibility, and recovery assumptions explicit until the operator confirms them.",
        ],
        "evidence_counts": [
            "Generic greenfield evidence must include behavior proof, contract proof, rendered topology, and refreshed release evidence.",
        ],
        "assumptions": [
            f"Assumption: {compact} starts with one product workflow and one domain object before wider architecture.",
        ],
        "invariants": [
            "Visible state must derive from domain contract outcomes, not UI-only assumptions.",
            "Domain contract remains narrower than storage, transport, and deployment choices until implementation proof lands.",
        ],
        "risks": [
            "Product risk: the first slice can become generic scaffolding instead of a meaningful domain workflow.",
            "Architecture risk: UI, storage, and domain logic can couple before ownership boundaries are proven.",
        ],
        "validation_obligations": [
            "Claim: first workflow is meaningful. Method: normal, empty, degraded, and failure state tests use real domain behavior.",
            "Claim: domain ownership is clear. Method: component spec names owned state, interfaces, dependencies, and non-goals.",
            "Claim: release gate is honest. Method: release target stays planning until proof and governance refresh pass.",
        ],
        "invalidation_rules": [
            "If first user, runtime, storage, deployment, data source, or proof target changes, invalidate affected component contracts, diagrams, validation commands, and release assumptions.",
            "If the prompt narrows into a regulated, safety-sensitive, or external-provider domain, regenerate security, privacy, compliance, and release-gate posture before source edits.",
        ],
        "metrics": [
            "Domain metric: first-slice states covered by tests.",
            "Epistemic metric: unresolved assumptions count before source edits.",
        ],
        "transfer_priors": [
            "Pattern: convert broad prompts into one workflow, one domain contract, one proof harness, and one release gate.",
        ],
    }


__all__ = [
    "workstream_family_terms",
]
