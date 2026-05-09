"""Family-specific term tables for greenfield workstream intelligence."""

from __future__ import annotations

from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_profile import GreenfieldDomainProfile


def workstream_family_terms(*, domain_profile: GreenfieldDomainProfile, title: str) -> dict[str, Any]:
    """Return domain-specific terms used by workstream intelligence builders."""

    if domain_profile.family == "defi_risk":
        return _defi_terms()
    if domain_profile.family == "defi_merchant_lending":
        return _defi_merchant_lending_terms()
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


def _defi_merchant_lending_terms() -> dict[str, Any]:
    return {
        "domain_phrase": "DeFi merchant lending",
        "project_objective": (
            "prove a Shopify SMB merchant borrowing path with explicit eligibility, stablecoin liquidity, "
            "disbursement, repayment, compliance, and no-custody boundaries."
        ),
        "stakeholder_outcome": (
            "a merchant borrower can understand application, offer, funding, and repayment state while capital operators "
            "can verify liquidity, freshness, compliance, and audit evidence."
        ),
        "failure_mode": (
            "the project can drift into a retail-purchase scaffold, misstate approved credit, duplicate money-movement events, "
            "or imply production lending and custody before proof exists."
        ),
        "non_goals": (
            "no consumer purchase flow, production lending approval, live DeFi protocol transactions, custody, private keys, "
            "financial advice, real Shopify merchant data, or production stablecoin movement in the first release."
        ),
        "decision_pressure": "credit integrity, liquidity proof, compliance posture, and no-custody boundaries beat app breadth.",
        "primary_validation_command": "merchant-lending fixture replay plus facility/disbursement/repayment contract proof",
        "topology_spine": (
            "merchant capital portal consumes the credit and liquidity core; the core consumes fixture-backed Shopify, "
            "compliance, stablecoin ledger, and liquidity snapshots; the lending proof harness validates both."
        ),
        "constraints": [
            "Shopify is merchant data and app-surface context, not evidence for consumer retail-flow ownership.",
            "No live Shopify access, live DeFi protocol calls, private keys, custody, or production stablecoin movement in release 0.0.1.",
            "Facility, disbursement, and repayment states must be idempotent under retry and replay.",
            "KYB/AML/sanctions, lending disclosure, audit, retention, and data classification gates must stay explicit.",
        ],
        "evidence_counts": [
            "Merchant-lending evidence must include eligible merchant, declined merchant, stale Shopify data, liquidity shortfall, duplicate disbursement, repayment replay, and compliance-blocked fixtures.",
        ],
        "assumptions": [
            "Assumption: first release uses fixture-backed Shopify snapshots and stablecoin/liquidity ledgers, not production merchant data or live protocol execution.",
            "Assumption: borrower-visible funding state is audit-relevant even before production authentication and compliance tooling exists.",
        ],
        "invariants": [
            "A stale Shopify snapshot cannot produce a normal eligibility or credit-limit claim.",
            "A disbursement or repayment replay cannot create a second money-movement state transition.",
            "A facility cannot move to approved or funded while KYB/AML, sanctions, or liquidity gates are blocked.",
            "No component may own private keys, custody, or production protocol execution in the first release.",
        ],
        "risks": [
            "Credit risk: stale or incomplete Shopify data can overstate eligibility or facility size.",
            "Treasury risk: liquidity shortfall or duplicate event handling can corrupt funding and repayment state.",
            "Compliance risk: KYB/AML, lending disclosure, money-transmission, securities, and no-custody obligations can be hidden by generic commerce language.",
        ],
        "validation_obligations": [
            "Claim: merchant eligibility is freshness-gated. Method: stale Shopify fixture blocks normal offer output.",
            "Claim: liquidity shortfall is degraded. Method: fixture where requested facility exceeds available stablecoin liquidity.",
            "Claim: disbursement and repayment are idempotent. Method: replayed events produce one state transition with audit evidence.",
            "Claim: compliance blocks funding. Method: KYB/AML/sanctions fault fixture prevents approved/funded states.",
        ],
        "invalidation_rules": [
            "If Shopify snapshot schema, underwriting inputs, stablecoin ledger semantics, liquidity source, disbursement rail, or repayment schedule changes, invalidate facility, funding, repayment, and architecture data-flow proof.",
            "If KYB/AML, lending, securities, money-transmission, custody, or live-protocol posture changes, block release promotion until authority, risks, proof, and non-goals are rewritten.",
        ],
        "metrics": [
            "Domain metric: stale Shopify, declined, liquidity-shortfall, duplicate-disbursement, and repayment-replay fixtures covered.",
            "Treasury metric: duplicate money-movement state transitions under replay remains zero.",
            "Compliance metric: every funding transition is blocked until required compliance fixture state is satisfied.",
            "UX metric: merchant can distinguish application, eligible, declined, liquidity-blocked, funded, and repayment states.",
        ],
        "transfer_priors": [
            "Pattern: treat borrower, underwriting input, facility, liquidity, disbursement, repayment, and compliance gate as separate domain objects.",
            "Pattern: stablecoin funding needs closed-world ledger and liquidity replay before live DeFi or production money movement.",
            "Pattern: Shopify merchant lending prompts should not inherit consumer-retail defaults.",
        ],
    }


def merchant_lending_ontology_rows(kind: str) -> list[str]:
    rows_by_kind = {
        "program": [
            "Program parent: merchant borrower journey, Shopify data posture, credit facility, stablecoin liquidity, repayment, compliance, and release gate.",
            "Merchant lending path: application -> Shopify snapshot -> eligibility -> compliance gate -> offer -> funding state -> repayment state.",
            "Release gate: no production lending, custody, live protocol execution, or real merchant data before closed-world proof.",
            "Domain-family guard: Shopify merchant data does not imply consumer cart, retail order, or card-processing sandbox ownership.",
            "Execution wave: governed merchant-lending delivery checkpoint with portal, credit-liquidity, and proof-harness workstreams.",
            "Evidence tier: merchant intent, Odylith assumptions, and later source_backed claims kept visibly separate.",
        ],
        "experience": [
            "Merchant borrower: SMB Shopify seller applying for working capital and reviewing funding or repayment state.",
            "Capital-ops reviewer: operator who can inspect eligibility, liquidity, compliance, and audit evidence.",
            "Visible facility state: draft, in_review, declined, eligible, liquidity_blocked, compliance_blocked, funded, repayment_due, and repaid.",
            "Degraded state: stale Shopify data, missing KYB, sanctions block, insufficient liquidity, or paused disbursement shown without approved-funds language.",
            "Credit facility: governed eligibility, limit, terms, funding, and repayment lifecycle.",
            "Liquidity source: fixture-backed stablecoin availability context; not custody or production protocol execution.",
            "Compliance gate: KYB/AML/sanctions/lending/no-custody decision that can block funding.",
        ],
        "domain": [
            "Shopify merchant snapshot: fixture-backed sales, refund, chargeback, currency, and freshness input for underwriting.",
            "Credit facility: eligibility, limit, terms, compliance state, liquidity state, disbursement state, and repayment state.",
            "Stablecoin liquidity allocation: funding availability evidence from a fixture-backed pool, vault, or ledger; not a custody account.",
            "Disbursement event: idempotent stablecoin funding transition with replay key, actor, amount, currency, and timestamp.",
            "Repayment event: idempotent repayment transition tied to balance, schedule, replay key, and audit evidence.",
            "Compliance gate: KYB, AML, sanctions, lending disclosure, no-custody, and release-approval posture.",
            "Merchant borrower: SMB Shopify seller applying for working capital; not a retail buyer.",
        ],
        "validation": [
            "Merchant fixture: pinned Shopify shop snapshot with sales, refund, chargeback, currency, consent, and freshness metadata.",
            "Liquidity fixture: stablecoin availability, source posture, currency, timestamp, and no-live-protocol proof.",
            "Compliance fault case: KYB, AML, sanctions, lending disclosure, or no-custody blocker that prevents funding.",
            "Replay report: deterministic evidence for eligibility, declined application, liquidity shortfall, duplicate disbursement, and repayment replay.",
            "Merchant borrower: SMB Shopify seller applying for working capital; not a retail buyer.",
            "Credit facility: governed eligibility, limit, terms, funding, and repayment lifecycle.",
            "Compliance gate: KYB/AML/sanctions/lending/no-custody decision that can block funding.",
        ],
    }
    return list(rows_by_kind.get(kind, rows_by_kind["domain"]))


def merchant_lending_operator_rows(kind: str) -> list[str]:
    rows_by_kind = {
        "program": [
            "Set merchant lending lane: precondition is confirmed borrower role, Shopify data boundary, stablecoin posture, and compliance posture; postcondition is release-gated merchant-capital topology.",
            "Defer production funding: precondition is absent compliance approval, live-protocol proof, or treasury approval; postcondition is fixture-only or sandbox-only release scope.",
            "Escalate regulated uncertainty: precondition is unclear lending, KYB/AML, sanctions, custody, money-transmission, or securities claim; postcondition is blocked release gate or explicit operator decision.",
        ],
        "experience": [
            "Submit merchant application: precondition is merchant identity, consent posture, requested capital amount, and Shopify snapshot reference; postcondition is visible review or rejection state.",
            "Review funding offer: precondition is eligibility, terms, compliance status, and liquidity status; postcondition is accepted, declined, or blocked facility state.",
            "Show funding and repayment state: precondition is facility state and ledger events; postcondition is borrower-visible funded, repayment_due, repaid, or degraded state without retail-purchase language.",
        ],
        "domain": [
            "Evaluate merchant eligibility: precondition is fresh Shopify snapshot and compliance input; postcondition is eligible, declined, stale_data, or compliance_blocked state.",
            "Reserve fixture liquidity: precondition is approved facility and available stablecoin liquidity; postcondition is liquidity_allocated or liquidity_blocked state without live protocol movement.",
            "Record disbursement event: precondition is compliance-approved facility and idempotency key; postcondition is one funding transition with audit evidence.",
            "Record repayment event: precondition is funded facility and replay key; postcondition is one repayment transition with balance and audit evidence.",
        ],
        "validation": [
            "Replay merchant application: precondition is pinned Shopify and compliance fixture; postcondition is deterministic eligibility or declined output.",
            "Replay liquidity shortfall: precondition is requested capital above stablecoin availability; postcondition is liquidity_blocked state and no funded claim.",
            "Replay duplicate disbursement or repayment: precondition is repeated ledger event; postcondition is one state transition with replay evidence.",
            "Assert no live funding surfaces: precondition is first-release proof run; postcondition is failure on live Shopify, protocol access, private keys, custody, or production credentials.",
        ],
    }
    return list(rows_by_kind.get(kind, rows_by_kind["domain"]))


def merchant_lending_validation_rows(kind: str) -> list[str]:
    rows_by_kind = {
        "program": [
            "Claim: merchant-lending first wave is coherent. Method: release target contains merchant portal, credit-liquidity core, proof harness, and no consumer-purchase or live-protocol scope.",
            "Claim: regulated posture is explicit. Method: KYB/AML/sanctions, lending disclosure, no-custody, no-private-key, no-live-protocol, and audit constraints appear in workstream and component records.",
        ],
        "experience": [
            "Claim: merchant borrower workflow is intelligible. Method: UI/API proof covers application, eligible offer, declined application, stale Shopify data, liquidity block, and repayment state.",
            "Claim: borrower-visible funding state is honest. Method: funded or repayment_due state derives from credit-liquidity contract output, not presentation-only labels.",
        ],
        "domain": [
            "Claim: facility state is deterministic. Method: same Shopify, compliance, liquidity, and ledger fixtures produce the same eligibility, funding, and repayment state.",
            "Claim: disbursement and repayment are idempotent. Method: replayed ledger events preserve one state transition with audit evidence.",
            "Claim: compliance blocks funding. Method: KYB/AML/sanctions fault fixture prevents approved or funded state.",
        ],
        "validation": [
            "Claim: lending proof harness is closed-world. Method: proof fails on live Shopify access, protocol calls, credentials, custody keys, or unpinned external data.",
            "Claim: scenario coverage is release-worthy. Method: eligible merchant, declined merchant, stale Shopify data, liquidity shortfall, duplicate disbursement, repayment replay, and compliance block all pass.",
        ],
    }
    return list(rows_by_kind.get(kind, rows_by_kind["domain"]))


def _generic_terms(*, title: str) -> dict[str, Any]:
    compact = title.replace(" App", "").replace(" Platform", "").strip() or "product"
    lower = compact.lower()
    return {
        "domain_phrase": f"{lower} greenfield",
        "project_objective": f"turn the {lower} prompt into a coherent first workflow, domain contract, and proof harness.",
        "stakeholder_outcome": f"the operator can start one {lower} implementation slice without rediscovering purpose, boundaries, proof, and risks.",
        "failure_mode": "agents may build plausible scaffolding that is disconnected from domain rules, users, state, and validation.",
        "non_goals": "no broad platform, production readiness, external integration, or source-backed claim until the first slice proves it.",
        "decision_pressure": "domain clarity and proof gates beat broad scaffold volume.",
        "primary_validation_command": "repo-native tests for normal, empty, degraded, and failure states",
        "topology_spine": "experience boundary consumes the domain core; validation harness proves both; release evidence preserves the trace.",
        "constraints": [
            "Keep the first slice small enough to prove with local fixtures and repository-native tests.",
            "Do not infer runtime, storage, or deployment ownership from project title alone.",
            "Keep data, auth, audit, accessibility, and recovery assumptions explicit until the operator confirms them.",
        ],
        "evidence_counts": [
            "Generic greenfield evidence must include behavior proof, contract proof, rendered topology, and refreshed governance records.",
        ],
        "assumptions": [
            f"Assumption: {compact} starts with one operator-visible workflow and one domain object before wider architecture.",
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
            "If first user, runtime, storage, deployment, data source, or proof surface changes, invalidate affected component contracts, diagrams, validation commands, and release assumptions.",
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
    "merchant_lending_ontology_rows",
    "merchant_lending_operator_rows",
    "merchant_lending_validation_rows",
    "workstream_family_terms",
]
