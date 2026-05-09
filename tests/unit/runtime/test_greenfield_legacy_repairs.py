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


def test_legacy_merchant_lending_repair_rewrites_registry_and_atlas_source(tmp_path: Path) -> None:
    _write_legacy_idea(
        tmp_path,
        idea_id="B-001",
        title="Govern SMB Lending Application Pulling Stable Coins From DeFi Protocols To",
        body=(
            "SMB Lending Application Pulling Stable Coins From DeFi Protocols To was applied as shopper "
            "checkout with storefront, cart, checkout-order-core, and checkout proof harness."
        ),
    )
    _write_legacy_registry(tmp_path)
    _write_legacy_atlas(tmp_path)
    _write_legacy_program(tmp_path)

    result = repair_legacy_merchant_lending_checkout_workstreams(repo_root=tmp_path)

    assert result.changed is True
    manifest = (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    atlas = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "odylith/atlas/source").glob("*.mmd"))
    catalog = (tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8")
    program = (tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json").read_text(encoding="utf-8")
    all_repaired = "\n".join([manifest, atlas, catalog, program])
    assert "merchant-capital-portal" in manifest
    assert "credit-liquidity-core" in manifest
    assert "lending-proof-harness" in manifest
    assert not (
        tmp_path
        / "odylith/registry/source/components/smb-lending-application-pulling-stable-coins-from-defi-protocols-to-storefront"
    ).exists()
    assert "Merchant Capital Portal" in atlas
    assert "Credit Liquidity Core" in atlas
    assert "Shopify Snapshot Fixture" in atlas
    assert "Stablecoin Liquidity Fixture" in atlas
    assert "KYB AML sanctions" in atlas
    assert "No live Shopify" in atlas
    assert "merchant lending" in catalog.casefold()
    assert "Merchant capital first slice" in program
    assert "Radar/Registry/Atlas/Compass" not in program
    assert not (tmp_path / "odylith/atlas/source/smb-lending-application-pulling-stable-coins-from-defi-protocols-to-system-overview.svg").exists()
    _assert_no_retail_checkout_leakage(all_repaired)
    for token in ("Radar", "Registry", "Atlas", "Compass", "Odylith Surfaces"):
        assert token not in atlas


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


def _write_legacy_registry(tmp_path: Path) -> None:
    root = tmp_path / "odylith/registry/source"
    component_root = root / "components"
    component_root.mkdir(parents=True, exist_ok=True)
    (root / "component_registry.v1.json").write_text(
        """{
  "components": [
    {
      "component_id": "smb-lending-application-pulling-stable-coins-from-defi-protocols-to-storefront",
      "name": "Commerce Storefront",
      "kind": "application",
      "category": "application",
      "qualification": "candidate",
      "path_prefixes": ["src/smb-lending-application-pulling-stable-coins-from-defi-protocols-to-storefront"],
      "workstreams": ["B-002"],
      "diagrams": ["D-002", "D-003"],
      "owner": "repo",
      "status": "planned",
      "what_it_is": "SMB Lending Application Pulling Stable Coins From DeFi Protocols To storefront owns shopper checkout cart state.",
      "why_tracked": "Checkout proof harness for merchant lending on Shopify.",
      "spec_ref": "odylith/registry/source/components/smb-lending-application-pulling-stable-coins-from-defi-protocols-to-storefront/CURRENT_SPEC.md",
      "sources": ["user_intent"],
      "subcomponents": [],
      "product_layer": "application"
    }
  ],
  "version": "v1"
}
""",
        encoding="utf-8",
    )
    spec_dir = component_root / "smb-lending-application-pulling-stable-coins-from-defi-protocols-to-storefront"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "CURRENT_SPEC.md").write_text(
        """# Commerce Storefront

SMB Lending Application Pulling Stable Coins From DeFi Protocols To was registered as shopper checkout.
Own browse, cart entry, checkout entry, order draft, payment callback, storefront, and checkout proof harness.
""",
        encoding="utf-8",
    )


def _write_legacy_atlas(tmp_path: Path) -> None:
    root = tmp_path / "odylith/atlas/source"
    (root / "catalog").mkdir(parents=True, exist_ok=True)
    slug = "smb-lending-application-pulling-stable-coins-from-defi-protocols-to-system-overview"
    (root / f"{slug}.mmd").write_text(
        """flowchart LR
  Intent[SMB Lending Application Pulling Stable Coins From DeFi Protocols To] --> Storefront[Commerce Storefront]
  Storefront --> Checkout[Checkout order core]
  Checkout --> Surfaces[Odylith surfaces<br/>Radar Registry Atlas Compass]
  classDef note fill:#f8fafc,stroke:#cbd5e1,color:#334155;
""",
        encoding="utf-8",
    )
    (root / f"{slug}.svg").write_text(
        "<svg><text>Odylith surfaces Radar Registry Atlas Compass checkout storefront</text></svg>\n",
        encoding="utf-8",
    )
    (root / "catalog/diagrams.v1.json").write_text(
        f"""{{
  "version": "v1",
  "diagrams": [
    {{
      "id": "D-001",
      "slug": "{slug}",
      "title": "SMB Lending Application Pulling Stable Coins From DeFi Protocols To System Overview",
      "summary": "Shopper checkout storefront and Odylith surfaces for merchant lending.",
      "source_mmd": "odylith/atlas/source/{slug}.mmd",
      "components": [{{"name": "smb-lending-application-pulling-stable-coins-from-defi-protocols-to-storefront"}}]
    }}
  ]
}}
""",
        encoding="utf-8",
    )


def _write_legacy_program(tmp_path: Path) -> None:
    root = tmp_path / "odylith/radar/source/programs"
    root.mkdir(parents=True, exist_ok=True)
    (root / "B-001.execution-waves.v1.json").write_text(
        """{
  "umbrella_id": "B-001",
  "version": "v1",
  "waves": [
    {
      "wave_id": "W1",
      "label": "First governed slice",
      "status": "active",
      "summary": "SMB Lending Application Pulling Stable Coins From DeFi Protocols To shopper checkout proof.",
      "exit_gate": "The first workstream has a technical plan, behavior proof, refreshed Radar/Registry/Atlas/Compass surfaces, and release-target validation.",
      "validation": [
        "The first workstream has a technical plan, behavior proof, refreshed Radar/Registry/Atlas/Compass surfaces, and release-target validation."
      ],
      "depends_on": [],
      "primary_workstreams": ["B-002", "B-003"],
      "carried_workstreams": [],
      "in_band_workstreams": [],
      "gate_refs": []
    }
  ]
}
""",
        encoding="utf-8",
    )


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
