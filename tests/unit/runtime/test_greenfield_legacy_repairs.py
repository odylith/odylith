from __future__ import annotations

from pathlib import Path

from odylith.runtime.governance.greenfield_legacy_repairs import repair_legacy_merchant_lending_checkout_workstreams
from odylith.runtime.governance.legacy_backlog_normalization import normalize_legacy_backlog_index


def test_legacy_merchant_lending_checkout_workstream_is_rewritten_to_lending_requirements(tmp_path: Path) -> None:
    idea = _write_legacy_idea(
        tmp_path,
        idea_id="B-003",
        title="Define domain contract and ownership",
        body=(
            "SMB Lending Application Pulling Stable Coins From DeFi Protocols To needs checkout order ownership. "
            "The workstream talks about shopper, cart, order draft, payment callback, checkout-order-core, "
            "and checkout proof harness even though this is merchant lending on Shopify."
        ),
    )

    result = repair_legacy_merchant_lending_checkout_workstreams(repo_root=tmp_path)

    text = idea.read_text(encoding="utf-8")
    assert result.changed is True
    assert result.repaired_specs == ("odylith/radar/source/ideas/2026-05/2026-05-07-define-domain-contract-and-ownership.md",)
    assert "title: Define credit facility, liquidity, and repayment contract" in text
    assert "Credit And Liquidity Core" in text
    assert "Shopify merchant" in text
    assert "stablecoin" in text
    assert "KYB" in text
    assert "repayment" in text
    _assert_no_retail_checkout_leakage(text)


def test_backlog_normalization_repairs_applied_legacy_merchant_lending_records_and_index(tmp_path: Path) -> None:
    _write_legacy_index(tmp_path)
    idea = _write_legacy_idea(
        tmp_path,
        idea_id="B-002",
        title="Define first operator workflow",
        body=(
            "SMB Lending Application Pulling Stable Coins From DeFi Protocols To was misread as a shopper checkout "
            "project with cart state, payment callback, storefront, and checkout proof harness."
        ),
    )

    result = normalize_legacy_backlog_index(repo_root=tmp_path)

    text = idea.read_text(encoding="utf-8")
    index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")
    assert result.changed is True
    assert result.normalized_idea_specs == (
        "odylith/radar/source/ideas/2026-05/2026-05-07-define-first-operator-workflow.md",
    )
    assert "title: Prove merchant borrower application and funding-status workflow" in text
    assert "| 1 | B-002 | Prove merchant borrower application and funding-status workflow |" in index
    assert "Merchant Capital Portal" in text
    assert "liquidity_blocked" in text
    assert "compliance_blocked" in text
    _assert_no_retail_checkout_leakage(text)


def _write_legacy_idea(tmp_path: Path, *, idea_id: str, title: str, body: str) -> Path:
    idea_dir = tmp_path / "odylith/radar/source/ideas/2026-05"
    idea_dir.mkdir(parents=True, exist_ok=True)
    path = idea_dir / f"2026-05-07-{title.lower().replace(' ', '-')}.md"
    path.write_text(
        f"""status: queued

idea_id: {idea_id}

title: {title}

date: 2026-05-07

priority: P1

commercial_value: 3

product_impact: 4

market_value: 3

impacted_parts: application,registry,atlas,radar

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Created from a confirmed Odylith greenfield proposal.

confidence: medium

founder_override: no

promoted_to_plan:

execution_model: standard

workstream_type: child

workstream_parent: B-001

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids: D-001,D-002

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
{body}

## Customer
Engineers and reviewers.

## Opportunity
Replace a broad label with a product-specific first slice.

## Proposed Solution
Build the retail checkout path.

## Research Signals
No external signal.

## Scope
Own shopper checkout, cart, order draft, payment callback, and checkout proof harness.

## Non-Goals
No live payment credentials.

## Risks
Payment callback replay can double-submit orders.

## Dependencies
Depends on checkout-order-core.

## Success Metrics
- Checkout proof exists.
- Shopper recovery is visible.

## Validation
- Browser proof covers checkout.

## Validation Evidence
No source proof yet.

## Migration/Compatibility
No migration impact recorded yet.

## Rollout
First governed slice.

## Why Now
The first operator workflow needs implementation.

## Impacted Components
- checkout-order-core

## Interface Changes
- Defines payment callback and cart contracts.

## Test Strategy
Run checkout smoke proof.

## Open Questions
- Which runtime?

## Domain Intelligence
Shopper checkout, cart, order draft, payment callback, and storefront ownership.
""",
        encoding="utf-8",
    )
    return path


def _write_legacy_index(tmp_path: Path) -> None:
    index = tmp_path / "odylith/radar/source/INDEX.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        """# Radar Source Index

Last updated (UTC): 2026-05-07

## Active Backlog

| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | B-002 | Define first operator workflow | P1 | 100 | 3 | 4 | 3 | M | Medium | queued | [Define first operator workflow](ideas/2026-05/2026-05-07-define-first-operator-workflow.md) |

## Execution Backlog

| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Finished Work

| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Parked Work

| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Reorder Rationale Log
""",
        encoding="utf-8",
    )


def _assert_no_retail_checkout_leakage(text: str) -> None:
    lowered = text.casefold()
    for token in (
        "shopper",
        "checkout",
        "cart",
        "order draft",
        "payment callback",
        "payment sandbox",
        "checkout-order-core",
        "checkout proof harness",
        "storefront",
    ):
        assert token not in lowered
