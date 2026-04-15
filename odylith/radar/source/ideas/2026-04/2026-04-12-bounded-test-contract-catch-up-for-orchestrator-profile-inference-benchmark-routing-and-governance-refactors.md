status: implementation

idea_id: B-090

title: Bounded test contract catch-up for orchestrator profile inference benchmark routing and governance refactors

date: 2026-04-12

priority: P1

commercial_value: 4

product_impact: 4

market_value: 3

impacted_parts: tests,orchestrator,subagent_router,benchmark_compare,governance_workstream_phase,hygiene,render_tooling_dashboard

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: medium

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-12-bounded-test-contract-catch-up-for-orchestrator-profile-inference-benchmark-routing-and-governance-refactors.md

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: 

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

## Problem
Twenty-seven unit tests were red after the recent orchestrator, benchmark, and
governance refactor wave. Most of the failures were contract drift in the tests
themselves, but the cluster could not simply be waved away because the hygiene
failures had the shape of a real product regression: bundle mirrors were
shipping source-truth backlog and plan files into consumer truth roots.

## Customer
Maintainers trying to keep the release lane honest when large refactors move the
runtime contract faster than the tests, and operators who need the unit suite
to distinguish real regressions from stale assertions.

## Opportunity
Bring the pre-existing failure clusters back to green with bounded test-side
updates, close the one real product leak in the bundle mirror contract, and
leave a documented trail for the CLI and governance gaps discovered during the
catch-up.

## Proposed Solution
- triage the hygiene failures first and ship the minimum product fix if they
  prove a real consumer-lane leak
- update the orchestrator, benchmark, governance, and dashboard tests to the
  live contracts without deleting intent
- keep the slice bounded to the failing clusters instead of widening into a
  broader refactor

## Scope
- the 27 failing tests across hygiene, orchestrator/router profile inference,
  benchmark dispatch, governance auto-promote, benchmark runner delegation, and
  tooling-dashboard compass refresh
- the minimum product-side fix required for a real public-tree bundle leak
- the governing sync and validation follow-through after the test catch-up

## Non-Goals
- do not rewrite the orchestrator/router runtime contracts just to satisfy old
  tests
- do not skip or delete failing tests instead of proving their current intent
- do not widen into unrelated benchmark or governance redesign

## Risks
- treating all 27 failures as test drift would miss the one real product
  regression in the bundle mirror contract
- widening beyond the observed failure clusters would turn a bounded catch-up
  slice into an unprovable cleanup wave

## Dependencies
- `B-089` and the surrounding refactor wave created the contract movement that
  the failing tests had to catch up with
- the sync/reconcile governance lane is part of the closeout because the slice
  touched source-truth and bundle-mirror behavior

## Success Metrics
- the 27 observed failures return to green without hiding a real regression
- the consumer bundle mirror stops shipping `radar/source/ideas/` and
  `technical-plans/in-progress/` into truth roots
- the final full unit sweep stays green

## Validation
- run the focused failing clusters first, then rerun the full unit suite
- run the affected sync/governance validation after the product-side leak fix

## Rollout
- land the bounded test catch-up and leak fix
- rerun the focused and full unit proof
- refresh the governed surfaces touched by the product-side fix

## Why Now
The release lane cannot tell real regressions from stale tests if the suite
stays red after the refactor wave, and one of the failures was a genuine
consumer-facing contract leak.

## Product View
Tests are only valuable if they are current enough to catch real product drift
without crying wolf on every refactor.

## Impacted Components
- `odylith`
- `dashboard`
- `release`

## Interface Changes
- no deliberate public interface change; the only product-side correction is
  the bundle-mirror exclude contract for consumer truth roots

## Migration/Compatibility
- consumer repos stop receiving the leaked source-truth mirror files; existing
  governed source records stay authoritative

## Test Strategy
- rerun each pre-existing failure cluster directly, then rerun the full unit
  suite as the release-proof closeout

## Open Questions
- should the plan-row insertion gap in `reconcile-plan-workstream-binding`
  become its own follow-on workstream now that this slice proved it live?
