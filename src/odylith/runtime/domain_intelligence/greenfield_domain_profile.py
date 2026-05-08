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
    if _contains_any(text, ("defi", "de-fi", "crypto", "wallet", "protocol", "liquidity", "stablecoin")) and _contains_any(
        text,
        ("risk", "sentinel", "alert", "exposure", "liquidation", "monitor"),
    ):
        return _defi_risk_profile(slug)
    if _contains_any(text, ("commerce", "ecommerce", "checkout", "cart", "shop", "storefront", "payment")):
        return _commerce_profile(slug)
    return _default_profile(title=title, slug=slug)


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
                interfaces=("Smoke command, payment sandbox fixture input, browser proof report, and surface refresh check.",),
                validation=("Proof covers happy path, failed payment, replayed callback, and stale surface refresh.",),
                risks=("A weak sandbox fixture can hide failed payment recovery or replay bugs.",),
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
                suffix="workbench",
                label=f"{compact} Workbench",
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
                    f"Depends on the {compact.lower()} domain core for state, commands, and invariant outcomes.",
                    "Depends on the verification harness for normal, empty, and degraded-state fixtures.",
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
                suffix="domain-core",
                label=f"{compact} Domain Core",
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
                suffix="verification-harness",
                label=f"{compact} Verification Harness",
                kind="tooling",
                path_prefix="tests",
                responsibility=(
                    f"Own deterministic {compact.lower()} fixtures, smoke/regression commands, proof reports, "
                    "and Odylith surface-refresh checks."
                ),
                boundary=f"Owns first-release proof evidence; excludes product runtime behavior and production data.",
                dependencies=(f"Depends on the {compact.lower()} workbench and domain core contracts.",),
                interfaces=("Local smoke command, fixture input, proof report, and Radar/Registry/Atlas/Compass refresh check.",),
                validation=("Proof command fails closed on missing fixtures, skipped assertions, or stale governance surfaces.",),
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
