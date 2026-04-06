---
status: queued
idea_id: B-035
title: Odylith Decisions Tab and Architecture Decision Ledger
date: 2026-03-30
priority: P1
commercial_value: 4
product_impact: 4
market_value: 3
impacted_lanes: both
impacted_parts: shell navigation, architecture decision records, decision traceability, Atlas and Registry linkage, and governed summaries of durable technical choices
sizing: L
complexity: High
ordering_score: 89
ordering_rationale: Odylith already captures plans, specs, backlog, diagrams, and bugs, but it still lacks one durable surface for the architectural decisions that explain why the product looks the way it does. A Decisions tab would keep ADR-quality reasoning visible without forcing maintainers to rediscover old tradeoffs from commit history and scattered notes.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001,B-024
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
Odylith has accumulated important architecture choices around runtime posture,
governance boundaries, routing, memory, and product surfaces, but the durable
decision trail is still too implicit. Specs describe what exists, plans describe
what changed, and Atlas shows shape, yet the product is missing one place that
states the decision, the alternatives, and the chosen rationale in a form that
can survive handoffs and revisits.

## Customer
- Primary: maintainers making or revisiting cross-cutting architecture
  decisions.
- Secondary: contributors and agents who need to understand why a choice was
  made before proposing a contradictory one.
- Tertiary: evaluators of Odylith's product maturity who expect major decisions
  to be recorded, not guessed from code archaeology.

## Opportunity
By turning ADR-style reasoning into a first-class governed surface, Odylith can
make architectural context durable, reduce repetitive debate, and improve the
quality of future changes that build on old decisions.

## Proposed Solution
Add a Decisions tab that acts as the user-facing architecture decision ledger
for Odylith, backed by explicit ADR records instead of informal notes.

### Wave 1: Decision record contract
- define the canonical source for architecture decisions, including status,
  scope, options considered, and consequences
- distinguish durable architectural decisions from short-lived implementation
  notes or plan checklists
- establish lightweight traceability to related components, diagrams, and
  workstreams

### Wave 2: Shell presentation
- add a Decisions tab to the shell with search, filters, and one readable
  decision detail view
- surface the final decision, rationale, and related artifacts without making
  the tab feel like a raw markdown folder browser
- use plain language first and ADR detail second so the surface helps both
  operators and maintainers

### Wave 3: Lifecycle integration
- connect decisions to Registry component history, Atlas diagrams, and backlog
  workstreams where the relationship is durable
- make superseded, replaced, or reaffirmed decisions explicit instead of
  leaving them ambiguous in historical prose
- add validation so decision metadata stays structured and searchable

## Scope
- a dedicated Decisions tab in the Odylith shell
- a governed architecture decision record contract
- search, status, and detail readouts for ADR-style records
- traceability to components, diagrams, plans, and workstreams
- lifecycle support for active, accepted, and superseded decisions

## Non-Goals
- turning every plan or bug into an ADR
- replacing component specs, plans, or Atlas diagrams
- shipping a heavyweight enterprise governance workflow in the first pass
- forcing one formal ADR process onto every downstream consumer repo

## Risks
- decision records can become stale if they are not tied to living product
  truth
- the surface may duplicate too much spec and plan content if the contract is
  not narrow
- an overly academic ADR format could make the tab feel slower than useful
- ambiguous status transitions could make old decisions harder to trust

## Dependencies
- `B-001` established the local governed truth model this ledger should live
  inside
- `B-024` made governance upkeep a first-class product behavior, which this
  decision surface should extend rather than bypass

## Success Metrics
- Odylith exposes a first-class Decisions tab for architectural choices
- major cross-cutting design decisions are discoverable without commit-history
  archaeology
- decisions can link to the components, diagrams, and workstreams they affect
- superseded or replaced decisions are clearly marked
- decision records remain structured enough for search, filtering, and future
  automation

## Validation
- `odylith sync --repo-root . --check-only`
- targeted tests for decision-record parsing, status handling, and shell
  rendering
- traceability validation across decisions, Registry, Atlas, and backlog links
- manual shell walkthrough of Decisions search, detail, and superseded-state UX

## Rollout
Land the decision-record contract first, then ship the Decisions tab, then
tighten traceability and status transitions once real decisions are flowing
through the surface.

## Why Now
Odylith is increasingly opinionated about architecture, but those opinions are
still too easy to lose between workstreams. If the product wants to be a
governed engineering system, architectural reasoning has to become durable
product truth.

## Product View
The product should remember its big technical decisions on purpose. "We used to
know why" is not a serious operating model.

## Impacted Components
- `odylith`
- `dashboard`
- `atlas`
- `registry`

## Interface Changes
- add a Decisions tab as the user-facing label for ADR content
- render decision status, rationale, and consequence summaries in the shell
- add searchable links from decision records to related artifacts
- support stable deep links for individual decisions

## Migration/Compatibility
- keep existing specs and plans authoritative for their own domains
- make the first rollout additive so current markdown records can be normalized
  gradually
- preserve readable markdown authoring rather than requiring a database-backed
  system

## Test Strategy
- add contract tests for decision metadata, status transitions, and lineage
- add shell-render tests for summary and detail views
- validate traceability edges to components, diagrams, and workstreams

## Open Questions
- whether the final user-facing tab label should be `Decisions`, `Decision
  Log`, or `Architecture`
- how formal the ADR template needs to be before it becomes cumbersome
- whether accepted decisions should also appear inline in related Registry and
  Atlas views
