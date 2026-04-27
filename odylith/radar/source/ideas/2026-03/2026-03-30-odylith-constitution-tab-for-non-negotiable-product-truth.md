---
status: queued
idea_id: B-034
title: Constitution Tab for Non-Negotiable Product Truth
date: 2026-03-30
priority: P0
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: shell navigation, constitutional guidance, governed product truth, operator guardrails, and first-class visibility for non-negotiable product rules
sizing: L
complexity: High
ordering_score: 98
ordering_rationale: Odylith already carries high-signal truth across AGENTS, specs, plans, and workstreams, but the product still lacks one explicit surface for the rules that should never be bargained away. A Constitution tab would make the core non-negotiable contract visible before maintainers, operators, or agents accidentally optimize around it.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001,B-027
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith already has constitutional truth, but it is scattered across repo-root
guidance, Odylith-local guidance, Registry specs, and active workstreams. That
means the most important "must never be breached" product rules are readable
only if someone already knows where to look. The product is missing one durable
surface that states the core contract plainly and keeps it visible during
navigation, planning, and implementation.

## Customer
- Primary: maintainers and operators who need one trusted place to review the
  product rules before making consequential changes.
- Secondary: agents working inside Odylith-governed repos who need the
  non-negotiable contract visible without reconstructing it from scattered
  documents.
- Tertiary: evaluators and future contributors who need to understand what the
  product will protect even when priorities change.

## Opportunity
By promoting constitutional truth into a first-class tab, Odylith can make its
identity legible, reduce accidental contract drift, and turn governance from
background policy into an explicit operator surface.

## Proposed Solution
Add a dedicated Constitution tab that renders the current non-negotiable
project truths in one stable, readable surface.

### Wave 1: Constitution source model
- define the durable source(s) that feed the Constitution tab instead of
  duplicating truth into a new freeform document
- separate non-negotiable product rules from implementation notes, temporary
  release tasks, and ordinary backlog guidance
- establish a small, stable structure for principles, invariants, and hard
  boundaries

### Wave 2: Shell surface and navigation
- add a first-class Constitution tab in the shell with concise summaries and
  drill-down detail
- make the surface explain why each rule exists, not just what the rule says
- ensure the tab remains useful in both product-repo maintainer mode and
  consumer installs

### Wave 3: Trust and lifecycle integration
- link the Constitution surface to relevant plans, workstreams, specs, and
  diagrams without turning the tab into a cluttered document browser
- make important contract breaches easy to notice during upgrades, release
  proof, and product self-explanation
- add validation so the tab cannot silently drift from its source truth

## Scope
- a dedicated Constitution tab in the Odylith shell
- a structured source contract for non-negotiable product truth
- clear rendering of principles, invariants, and hard boundaries
- lightweight traceability from Constitution entries to existing governed truth
- validation that keeps the rendered surface synchronized

## Non-Goals
- replacing the full detail of AGENTS, specs, plans, or runbooks
- turning the Constitution tab into a generic documentation dump
- making every preference or workflow choice look constitution-level
- inventing a hosted policy system for this first pass

## Risks
- the surface could become redundant if it copies truth instead of rendering
  from canonical sources
- maintainers may over-promote ordinary guidance into constitution-level rules,
  which would make the tab noisy and weak
- a tab that sounds absolute but drifts from source truth would reduce trust
  rather than increase it
- too much prose could make the tab feel ceremonial instead of operationally
  useful

## Dependencies
- `B-001` established Odylith's self-governing product boundary and the local
  truth model this surface should draw from
- `B-027` is clarifying the lane and boundary contract that a Constitution tab
  should expose plainly instead of leaving implicit

## Success Metrics
- Odylith exposes one dedicated Constitution tab in the shell
- core non-negotiable rules are understandable without reading multiple source
  files first
- the tab points back to real canonical truth instead of becoming a duplicate
  ledger
- maintainers and operators can identify breach-level rules quickly during
  planning and review
- source changes that affect constitutional truth fail closed if the rendered
  surface is stale

## Validation
- `odylith sync --repo-root . --check-only`
- targeted renderer and shell tests for Constitution navigation, payload
  generation, and deep-link behavior
- source-truth contract checks that fail if Constitution content drifts from its
  canonical input
- manual shell walkthrough covering the Constitution tab in product-repo and
  consumer-lane views

## Rollout
Define the source contract first, add the shell tab second, then tighten
traceability and validation once the surface is useful enough to anchor real
operator behavior.

## Why Now
Odylith is no longer just proving that it can automate work. It is now shaping
how work gets governed. That makes the product's non-negotiable truth too
important to leave scattered across files that only experienced maintainers
know how to reconstruct.

## Product View
If Odylith claims to protect truth, then the truth that matters most should be
visible as a product surface, not hidden in institutional memory.

## Impacted Components
- `odylith`
- `dashboard`
- `registry`
- `compass`

## Interface Changes
- add a top-level Constitution tab in the Odylith shell
- render structured non-negotiable truth with summary and detail states
- add traceability links from Constitution entries to their canonical sources
- expose Constitution deep links as a stable part of the shell IA

## Migration/Compatibility
- keep existing AGENTS, specs, and docs authoritative until the Constitution
  source contract is finalized
- make the first rollout additive so existing links and workflows remain valid
- avoid storing local operator preference or transient release state as
  constitution-level truth

## Test Strategy
- add payload-level tests for Constitution source parsing and render shape
- add browser-visible tests for shell navigation and deep links
- add fail-closed validation around stale or contradictory Constitution input

## Open Questions
- whether the Constitution should render from one authored source or compose a
  small set of canonical sources
- how much policy detail belongs in the tab before it starts duplicating AGENTS
  and spec content
- whether breach-level rules should also surface inline during plan or backlog
  review flows
