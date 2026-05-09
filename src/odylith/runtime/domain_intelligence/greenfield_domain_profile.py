"""Prompt-derived component profiles for provider-free greenfield scaffolds."""

from __future__ import annotations

from dataclasses import dataclass

from odylith.runtime.analysis_engine.types import slugify


@dataclass(frozen=True)
class GreenfieldComponentProfile:
    suffix: str
    label: str
    kind: str
    path_prefix: str
    responsibility: str
    boundary: str
    dependencies: tuple[str, ...]
    interfaces: tuple[str, ...]
    validation: tuple[str, ...]
    risks: tuple[str, ...]


@dataclass(frozen=True)
class GreenfieldDomainProfile:
    family: str
    components: dict[str, GreenfieldComponentProfile]


def infer_greenfield_domain_profile(*, prompt: str, title: str, slug: str) -> GreenfieldDomainProfile:
    text = f"{prompt} {title} {slug}".casefold()
    if _is_defi_merchant_lending(text):
        return _defi_merchant_lending_profile(slug)
    if _contains_any(text, ("defi", "de-fi", "crypto", "wallet", "protocol", "liquidity", "stablecoin")) and _contains_any(
        text,
        ("risk", "sentinel", "alert", "exposure", "liquidation", "monitor"),
    ):
        return _defi_risk_profile(slug)
    if _contains_any(text, ("clinical trial", "patient matching", "oncology", "consent", "eligibility review")):
        return _clinical_trial_profile(slug)
    if _contains_any(text, ("legal intake", "immigration", "attorney review", "case triage", "document collection")):
        return _legal_intake_profile(slug)
    if _contains_any(text, ("bioinformatics", "variant", "sequencing", "vcf", "fastq", "genome", "sample qc")):
        return _bioinformatics_profile(slug)
    if _contains_any(text, ("commerce", "ecommerce", "checkout", "cart", "shop", "storefront", "payment")):
        return _commerce_profile(slug)
    return _default_profile(title=title, slug=slug)


def _is_defi_merchant_lending(text: str) -> bool:
    has_lending = _contains_any(
        text,
        (
            "lending",
            "loan",
            "credit",
            "borrow",
            "borrower",
            "underwriting",
            "working capital",
            "merchant cash advance",
            "repayment",
            "smb",
        ),
    )
    has_merchant = _contains_any(text, ("merchant", "shopify", "seller", "smb", "business"))
    has_defi_funding = _contains_any(
        text,
        ("defi", "de-fi", "stablecoin", "stable coin", "usdc", "liquidity", "protocol", "vault", "pool"),
    )
    return has_lending and has_merchant and has_defi_funding


def _defi_risk_profile(slug: str) -> GreenfieldDomainProfile:
    return GreenfieldDomainProfile(
        family="defi_risk",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="risk-console",
                label="Risk Sentinel Console",
                kind="application",
                path_prefix="src",
                responsibility=(
                    "Own wallet/protocol watchlist setup, exposure triage, alert acknowledgement, "
                    "and degraded oracle or indexer states for the first analyst workflow."
                ),
                boundary=(
                    "Owns analyst-facing risk review and alert workflow; excludes risk scoring math, "
                    "chain indexing, custody, trading, and production transaction execution."
                ),
                dependencies=(
                    "Depends on the risk signal engine for exposure snapshots, alert state, and confidence metadata.",
                    "Depends on the scenario replay harness for deterministic oracle, protocol, and liquidity fixtures.",
                ),
                interfaces=(
                    "Watchlist route or command for adding wallet, protocol, pool, or strategy subjects.",
                    "Risk alert read model containing severity, exposure, trigger reason, confidence, and acknowledgement state.",
                    "Fallback-state contract for stale oracle data, missing indexer data, and unsupported chain fixtures.",
                ),
                validation=(
                    "Browser or UI proof covers normal triage, empty watchlist, stale oracle, and unsupported-chain states.",
                    "Alert acknowledgement writes are idempotent and preserve analyst identity in audit fixtures.",
                ),
                risks=(
                    "A false sense of precision can cause an analyst to trust incomplete oracle, liquidity, or protocol-state data.",
                    "The first release must not imply custody, trade execution, or production financial advice.",
                ),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="risk-signal-engine",
                label="Risk Signal Engine",
                kind="service",
                path_prefix="src",
                responsibility=(
                    "Own exposure normalization, protocol risk factors, alert threshold evaluation, "
                    "risk state transitions, and confidence scoring for the first monitored subject."
                ),
                boundary=(
                    "Owns deterministic risk calculations and alert state; excludes presentation, live chain adapters, "
                    "custody, trading, and external notification delivery."
                ),
                dependencies=(
                    "Consumes fixture-backed price, liquidity, position, oracle, and protocol-health inputs from the replay harness.",
                    "Feeds the console through a stable risk snapshot and alert-state contract.",
                ),
                interfaces=(
                    "Risk subject schema for wallet, protocol, pool, or strategy identifiers.",
                    "Exposure snapshot query with normalized assets, protocol, chain, timestamp, and confidence fields.",
                    "Alert evaluation command that returns severity, trigger reason, threshold, confidence, and next state.",
                ),
                validation=(
                    "Contract tests cover threshold crossing, stale oracle rejection, missing liquidity handling, and idempotent alert replay.",
                    "Fixtures prove deterministic output for the same price, liquidity, and protocol-health inputs.",
                ),
                risks=(
                    "Incorrect normalization can understate exposure, double-count positions, or mask liquidation paths.",
                    "Provider drift must not change risk math without fixture-backed contract proof.",
                ),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="scenario-replay-harness",
                label="Scenario Replay Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility=(
                    "Own deterministic DeFi risk scenarios, oracle/indexer fault fixtures, replay reports, "
                    "and release proof for console plus risk-engine behavior."
                ),
                boundary=(
                    "Owns local fixtures and proof reports; excludes live chain calls, production keys, "
                    "portfolio custody, and real trade execution."
                ),
                dependencies=(
                    "Depends on the risk signal engine contract and console visible-state contract.",
                    "Uses pinned local fixtures for price moves, liquidity shocks, stale oracle data, and protocol-health changes.",
                ),
                interfaces=(
                    "Scenario runner command with fixture set, seed, expected alert states, and report output.",
                    "Fixture schema for price, liquidity, oracle freshness, protocol health, and wallet exposure.",
                ),
                validation=(
                    "Replay proof covers price shock, liquidity drain, stale oracle, missing indexer, and alert acknowledgement.",
                    "Harness fails closed when fixtures require live network, production credentials, or unpinned external data.",
                ),
                risks=(
                    "Weak fixtures can make risk claims look verified while missing realistic oracle or liquidity failures.",
                    "Any production credential or live-chain dependency in the first release invalidates deterministic proof.",
                ),
            ),
        },
    )


def _defi_merchant_lending_profile(slug: str) -> GreenfieldDomainProfile:
    return GreenfieldDomainProfile(
        family="defi_merchant_lending",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="merchant-capital-portal",
                label="Merchant Capital Portal",
                kind="application",
                path_prefix="src",
                responsibility=(
                    "Shopify merchant onboarding, capital application intake, offer review, "
                    "stablecoin funding status, repayment visibility, and eligibility or liquidity degraded states."
                ),
                boundary=(
                    "Owns borrower-facing merchant workflow and visible funding state; excludes underwriting math, "
                    "treasury adapters, DeFi protocol execution, custody, private keys, and retail-buyer journeys."
                ),
                dependencies=(
                    "Depends on the credit and liquidity core for eligibility, facility, disbursement, and repayment state.",
                    "Depends on the lending proof harness for deterministic Shopify, liquidity, compliance, and repayment fixtures.",
                ),
                interfaces=(
                    "Merchant application route or command with Shopify shop identifier, consent posture, and requested capital amount.",
                    "Offer and funding-status read model containing eligibility, limit, terms, liquidity status, disbursement state, and repayment state.",
                    "Degraded-state contract for stale Shopify data, missing KYB, insufficient liquidity, declined eligibility, and paused disbursement.",
                ),
                validation=(
                    "Browser or API proof covers eligible merchant, declined merchant, stale Shopify data, liquidity shortfall, and repayment-visible states.",
                    "Borrower-visible funding and repayment states are derived from the domain contract, not local presentation assumptions.",
                ),
                risks=(
                    "Merchant workflow can imply approved credit or available funds before underwriting, liquidity, and compliance gates are proven.",
                    "Shopify commerce data must not be treated as retail-buyer workflow ownership or production lending evidence.",
                ),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="credit-liquidity-core",
                label="Credit And Liquidity Core",
                kind="service",
                path_prefix="src",
                responsibility=(
                    "Merchant eligibility inputs, Shopify sales snapshot semantics, credit facility state, stablecoin allocation, "
                    "idempotent disbursement, repayment lifecycle, and compliance-gated transitions."
                ),
                boundary=(
                    "Owns credit, liquidity, disbursement, and repayment invariants; excludes portal presentation, live Shopify adapters, "
                    "live DeFi protocol calls, custody, private keys, accounting ledger finality, and legal underwriting decisions."
                ),
                dependencies=(
                    "Consumes fixture-backed Shopify merchant snapshots, DeFi liquidity snapshots, compliance decisions, and stablecoin ledger events.",
                    "Feeds the merchant portal through stable application, offer, facility, disbursement, and repayment contracts.",
                ),
                interfaces=(
                    "Merchant snapshot schema with shop identity, sales history, chargeback posture, currency, and data freshness.",
                    "Credit facility command/query contract for eligibility, limit, terms, compliance status, and facility state.",
                    "Idempotent stablecoin disbursement and repayment event contract with actor, amount, currency, timestamp, and replay key.",
                ),
                validation=(
                    "Contract tests cover eligibility, declined application, stale Shopify snapshot, liquidity shortfall, duplicate disbursement, and repayment replay.",
                    "Tests prove no live protocol, custody, private-key, or production Shopify dependency is required for first-release proof.",
                ),
                risks=(
                    "Loose eligibility or liquidity semantics can overstate available credit, misprice a facility, or duplicate funding events.",
                    "Regulated lending, KYB/AML, stablecoin, and DeFi boundaries must stay explicit before any production claim.",
                ),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="lending-proof-harness",
                label="Lending Proof Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility=(
                    "Deterministic merchant-lending fixtures, Shopify snapshot replay, liquidity and stablecoin ledger scenarios, "
                    "compliance fault cases, and release proof for portal plus credit-liquidity behavior."
                ),
                boundary=(
                    "Owns local fixtures and proof reports; excludes production merchant data, live DeFi credentials, "
                    "custody keys, production disbursements, and real lending approval."
                ),
                dependencies=(
                    "Depends on merchant portal visible-state contracts and credit-liquidity core domain contracts.",
                    "Uses pinned local fixtures for Shopify sales snapshots, KYB/AML status, liquidity availability, disbursement replay, and repayment replay.",
                ),
                interfaces=(
                    "Scenario runner command with merchant fixture, liquidity fixture, compliance state, expected facility state, and proof report.",
                    "Fixture schema for Shopify merchant data freshness, stablecoin ledger events, liquidity source posture, and compliance gate outcomes.",
                ),
                validation=(
                    "Proof covers eligible funding, declined application, stale Shopify data, liquidity shortfall, duplicate disbursement, and repayment replay.",
                    "Harness fails closed on live Shopify access, live protocol access, production credentials, custody keys, or unpinned external data.",
                ),
                risks=(
                    "Weak fixtures can make credit, liquidity, disbursement, or repayment claims look verified while missing regulated edge cases.",
                    "Any production credential, private key, or live protocol dependency in release 0.0.1 invalidates deterministic proof.",
                ),
            ),
        },
    )


def _commerce_profile(slug: str) -> GreenfieldDomainProfile:
    return GreenfieldDomainProfile(
        family="commerce",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="storefront",
                label="Commerce Storefront",
                kind="application",
                path_prefix="src",
                responsibility="Own browse, cart entry, checkout entry, user-visible errors, and recovery states for the first purchase path.",
                boundary="Owns shopper-facing flow and visible state; excludes payment-provider integration, order ledger internals, and fulfillment.",
                dependencies=("Depends on checkout/order core for cart, payment handoff, and order-draft state.",),
                interfaces=("Browse route, cart-entry command, checkout-entry command, and visible error-state contract.",),
                validation=("Browser proof covers browse-to-cart, checkout handoff, empty cart, and failed payment messaging.",),
                risks=("Misleading checkout state can double-submit orders or hide payment-provider failures.",),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="checkout-order-core",
                label="Checkout And Order Core",
                kind="service",
                path_prefix="src",
                responsibility="Own cart state, checkout handoff, idempotent order draft creation, payment callback recovery, and order status transitions.",
                boundary="Owns checkout and order invariants; excludes storefront presentation, payment-provider SDK ownership, and fulfillment execution.",
                dependencies=("Consumes product and price snapshot inputs; feeds storefront and payment sandbox contracts.",),
                interfaces=("Cart command, checkout command, payment callback contract, order-draft writer, and order-status query.",),
                validation=("Contract tests cover idempotent order draft creation, failed payment recovery, and callback replay.",),
                risks=("Non-idempotent checkout can double-create orders or lose failed-payment recovery state.",),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="checkout-proof-harness",
                label="Checkout Proof Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility="Own checkout fixtures, payment sandbox replay, browser smoke proof, and release-readiness report.",
                boundary="Owns local proof fixtures and reports; excludes live payment credentials and production order data.",
                dependencies=("Depends on storefront and checkout/order core contracts.",),
                interfaces=("Smoke command, payment sandbox fixture input, browser proof report, and release-readiness check.",),
                validation=("Proof covers happy path, failed payment, replayed callback, and stale release evidence.",),
                risks=("A weak sandbox fixture can hide failed payment recovery or replay bugs.",),
            ),
        },
    )


def _clinical_trial_profile(slug: str) -> GreenfieldDomainProfile:
    return GreenfieldDomainProfile(
        family="clinical_trial_matching",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="patient-match-review",
                label="Patient Match Review Workbench",
                kind="application",
                path_prefix="src",
                responsibility="Patient intake review, consent status, trial match explanation, eligibility gaps, and coordinator-visible next steps.",
                boundary="Owns coordinator-facing review workflow; excludes protocol-authoring, medical judgment, EHR integration, and patient outreach automation.",
                dependencies=("Depends on the eligibility protocol engine for inclusion, exclusion, consent, and confidence state.",),
                interfaces=("Patient intake route or command with diagnosis, biomarkers, consent posture, and candidate trial filters.",),
                validation=("UI or API proof covers eligible, ineligible, missing-consent, missing-data, and manual-review states.",),
                risks=("A weak workflow can imply clinical eligibility or consent where protocol evidence is incomplete.",),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="eligibility-protocol-engine",
                label="Eligibility Protocol Engine",
                kind="service",
                path_prefix="src",
                responsibility="Patient attributes, oncology protocol criteria, consent gates, inclusion/exclusion rules, match scoring, and review state transitions.",
                boundary="Owns deterministic eligibility semantics; excludes care decisions, live EHR access, recruitment messaging, and protocol authoring.",
                dependencies=("Consumes fixture-backed patient summaries, protocol criteria, consent state, and trial availability snapshots.",),
                interfaces=("Eligibility query with patient profile, protocol criteria, consent state, exclusion reasons, confidence, and review disposition.",),
                validation=("Contract tests cover inclusion match, exclusion rejection, missing consent, missing biomarker, stale protocol, and manual review.",),
                risks=("Loose protocol semantics can create unsafe or misleading trial recommendations.",),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="matching-proof-harness",
                label="Trial Matching Proof Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility="Deterministic patient, protocol, consent, biomarker, exclusion, and manual-review fixtures plus proof reports.",
                boundary="Owns local evidence only; excludes production patient data, EHR credentials, recruitment outreach, and clinical approval.",
                dependencies=("Depends on patient review workflow and eligibility protocol contract.",),
                interfaces=("Scenario runner with patient fixture, protocol fixture, consent state, expected disposition, and proof report.",),
                validation=("Proof covers eligible, excluded, missing-consent, missing-data, stale-protocol, and manual-review scenarios.",),
                risks=("Fixture gaps can make unsafe clinical matching claims look verified.",),
            ),
        },
    )


def _legal_intake_profile(slug: str) -> GreenfieldDomainProfile:
    return GreenfieldDomainProfile(
        family="legal_intake",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="client-intake-workspace",
                label="Client Intake Workspace",
                kind="application",
                path_prefix="src",
                responsibility="Immigration client intake, document checklist, eligibility summary, risk flags, and attorney-review handoff.",
                boundary="Owns client/operator intake workflow; excludes legal advice, filing submission, payment, and attorney decision authority.",
                dependencies=("Depends on the case eligibility and document core for intake state, required documents, and review disposition.",),
                interfaces=("Intake route or command with client profile, case type, document inventory, urgency, and consent posture.",),
                validation=("UI or API proof covers complete intake, missing documents, urgent risk, blocked consent, and attorney-review states.",),
                risks=("A weak workflow can imply legal advice or filing readiness before attorney review.",),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="case-document-core",
                label="Case Eligibility And Document Core",
                kind="service",
                path_prefix="src",
                responsibility="Immigration case type, document requirements, eligibility signals, risk flags, confidentiality state, and attorney-review routing.",
                boundary="Owns intake classification and document completeness semantics; excludes legal advice, live filing systems, and final representation decisions.",
                dependencies=("Consumes fixture-backed client facts, document inventory, consent state, and case-type rules.",),
                interfaces=("Case triage query with client facts, case type, required documents, missing items, risk flags, and review disposition.",),
                validation=("Contract tests cover complete intake, missing document, urgent deadline, consent block, conflict flag, and attorney review.",),
                risks=("Unclear eligibility semantics can create unauthorized-practice or confidentiality risk.",),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="confidential-intake-harness",
                label="Confidential Intake Proof Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility="Deterministic client, document, consent, deadline, conflict, and attorney-review fixtures plus privacy proof reports.",
                boundary="Owns local proof; excludes production client data, filing credentials, legal advice, and external case systems.",
                dependencies=("Depends on intake workspace visible-state contract and case-document core contract.",),
                interfaces=("Scenario runner with client fixture, document fixture, consent state, expected disposition, and confidentiality report.",),
                validation=("Proof covers complete intake, missing documents, urgent deadline, consent block, conflict flag, and attorney review.",),
                risks=("Weak privacy fixtures can hide PII handling, consent, or unauthorized-advice failures.",),
            ),
        },
    )


def _bioinformatics_profile(slug: str) -> GreenfieldDomainProfile:
    return GreenfieldDomainProfile(
        family="bioinformatics_variant_pipeline",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="variant-review-workbench",
                label="Variant Review Workbench",
                kind="application",
                path_prefix="src",
                responsibility="Sample run intake, QC status, variant review, VCF report access, failure explanation, and analyst handoff.",
                boundary="Owns analyst-facing review workflow; excludes sequencing execution, clinical interpretation, LIMS integration, and production storage.",
                dependencies=("Depends on the sequencing analysis core for sample, QC, variant, annotation, and report state.",),
                interfaces=("Run review route or command with sample id, sequencing fixture, QC state, VCF reference, and analyst notes.",),
                validation=("UI or API proof covers passing sample, failed QC, empty variants, malformed VCF, and review-ready states.",),
                risks=("A weak review workflow can imply valid biological interpretation before QC and reproducibility proof exist.",),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="sequencing-analysis-core",
                label="Sequencing Analysis Core",
                kind="service",
                path_prefix="src",
                responsibility="Sample metadata, FASTQ/BAM/VCF fixture semantics, QC thresholds, variant normalization, annotation state, and reproducible run outputs.",
                boundary="Owns deterministic pipeline state and file-contract semantics; excludes sequencer control, clinical interpretation, and live data lake access.",
                dependencies=("Consumes pinned sample, QC, reference, VCF, annotation, and expected-output fixtures.",),
                interfaces=("Pipeline query with sample metadata, QC metrics, variant list, VCF output, provenance, and review disposition.",),
                validation=("Contract tests cover passing QC, failed QC, empty variant set, malformed VCF, reference mismatch, and reproducible rerun.",),
                risks=("Unpinned references or loose QC can make variant claims unreproducible.",),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="pipeline-reproducibility-harness",
                label="Pipeline Reproducibility Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility="Pinned sample, QC, reference, VCF, annotation, malformed-input, and reproducibility fixtures plus proof reports.",
                boundary="Owns local proof; excludes production samples, external compute clusters, clinical sign-out, and live lab systems.",
                dependencies=("Depends on variant review workflow and sequencing analysis contract.",),
                interfaces=("Scenario runner with sample fixture, reference fixture, expected VCF/QC output, provenance, and reproducibility report.",),
                validation=("Proof covers passing sample, failed QC, empty variants, malformed VCF, reference mismatch, and deterministic rerun.",),
                risks=("Weak reproducibility proof can hide reference drift, sample mix-ups, or invalid VCF output.",),
            ),
        },
    )


def _default_profile(*, title: str, slug: str) -> GreenfieldDomainProfile:
    domain_name = _domain_label(title, slug=slug)
    compact = domain_name.replace(" App", "").replace(" Platform", "").strip() or "Product"
    return GreenfieldDomainProfile(
        family="generic",
        components={
            "experience": GreenfieldComponentProfile(
                suffix="operator-workspace",
                label=f"{compact} Operator Workspace",
                kind="application",
                path_prefix="src",
                responsibility=(
                    f"Own the first {compact.lower()} workflow entrypoint, visible state transitions, "
                    "empty/degraded/error handling, and operator-facing proof."
                ),
                boundary=(
                    f"Owns the human-facing {compact.lower()} interaction boundary; excludes domain invariants, "
                    "storage decisions, external integrations, and release proof ownership."
                ),
                dependencies=(
                    f"Depends on the {compact.lower()} product model for state, commands, and invariant outcomes.",
                    "Depends on the evidence harness for normal, empty, and degraded-state fixtures.",
                ),
                interfaces=(
                    f"{compact} workflow route or command plus visible normal, empty, degraded, and error state contract.",
                    "Read model for the first user-visible object, status, recovery hint, and audit or trace id.",
                ),
                validation=(
                    "Behavior proof covers the normal path and at least one empty or degraded state.",
                    "Visible state derives from the domain contract rather than local UI-only assumptions.",
                ),
                risks=(f"A generic {compact.lower()} screen can make unproven source behavior look complete.",),
            ),
            "domain": GreenfieldComponentProfile(
                suffix="product-model",
                label=f"{compact} Product Model",
                kind="service",
                path_prefix="src",
                responsibility=(
                    f"Own the first {compact.lower()} state model, command/query contract, invariants, "
                    "retry semantics, and integration handoff."
                ),
                boundary=(
                    f"Owns {compact.lower()} domain state and invariant enforcement; excludes presentation, "
                    "deployment, and proof-harness ownership."
                ),
                dependencies=("Depends on confirmed first-workflow semantics; external provider choices wait for technical planning.",),
                interfaces=("Command, query, schema, event, or module contract consumed by the first workflow.",),
                validation=("Contract tests cover valid transition, invalid input rejection, and retry or idempotency behavior.",),
                risks=(f"A loose {compact.lower()} domain contract can couple UI, storage, and integration choices too early.",),
            ),
            "validation": GreenfieldComponentProfile(
                suffix="evidence-harness",
                label=f"{compact} Evidence Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility=(
                    f"Own deterministic {compact.lower()} fixtures, smoke/regression commands, proof reports, "
                    "and release evidence checks."
                ),
                boundary=f"Owns first-release proof evidence; excludes product runtime behavior and production data.",
                dependencies=(f"Depends on the {compact.lower()} operator workspace and product model contracts.",),
                interfaces=("Local smoke command, fixture input, proof report, and release evidence check.",),
                validation=("Proof command fails closed on missing fixtures, skipped assertions, or stale release evidence.",),
                risks=("Weak proof can let proposal text outrun implementation evidence.",),
            ),
        },
    )


def _domain_label(title: str, *, slug: str) -> str:
    text = " ".join(str(title or "").split()).strip()
    if text:
        return text
    return " ".join(part.capitalize() for part in slugify(slug).split("-") if part) or "Greenfield Product"


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


__all__ = ["GreenfieldComponentProfile", "GreenfieldDomainProfile", "infer_greenfield_domain_profile"]
