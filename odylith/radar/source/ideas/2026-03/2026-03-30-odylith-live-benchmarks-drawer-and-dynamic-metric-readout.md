---
status: queued
idea_id: B-037
title: Live Benchmarks Drawer and Dynamic Metric Readout
date: 2026-03-30
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: shell drawer IA, benchmark compare surfaces, current metric visibility, dynamic refresh behavior, and maintainer-facing proof readouts
sizing: L
complexity: High
ordering_score: 98
ordering_rationale: Odylith already treats benchmark proof as product truth, but the current metric story is still too buried in reports, release workflow, and specialized status panels. A live Benchmarks drawer would make the current benchmark posture visible as a first-class product readout and keep it current as the underlying proof changes.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-021,B-022,B-033
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
Benchmark truth matters more than ever, but the current benchmark readout is
still fragmented across generated reports, release proof, and maintainer-only
status areas. The shell is missing one compact surface that answers the current
state clearly: what are the benchmark metrics we care about, how do they
compare, and when did they change?

## Customer
- Primary: maintainers and operators who need current benchmark posture without
  hunting through files and release flow output.
- Secondary: evaluators of Odylith's product credibility who want proof surfaced
  directly in the product.
- Tertiary: future contributors who need benchmark movement visible early when
  they change runtime or routing behavior.

## Opportunity
By adding a Benchmarks drawer with live metric readouts, Odylith can turn
benchmark proof from a hidden artifact into a durable product surface and make
performance, quality, and trust movement easier to inspect continuously.

## Proposed Solution
Add a Benchmarks drawer that renders the current benchmark metrics and refreshes
from the latest governed benchmark truth as it changes.

### Wave 1: Metric contract
- define the exact benchmark metrics, statuses, and comparison baselines that
  belong in the drawer
- distinguish current snapshot, delta versus baseline, and longer-lived history
  so the surface stays readable
- normalize the current benchmark report into a shell-friendly payload contract

### Wave 2: Drawer UX
- add a Benchmarks drawer that exposes headline status, key metrics, and recent
  movement at a glance
- make the drawer legible for both quick checks and deeper inspection without
  replacing full benchmark reports
- support empty, stale, or unavailable benchmark states cleanly

### Wave 3: Dynamic freshness
- refresh the drawer from the latest benchmark truth when new proof lands or
  when the shell reloads relevant state
- make stale timestamps and comparison provenance explicit
- connect the drawer to release and maintainer workflows where benchmark
  movement should be impossible to miss

## Scope
- a dedicated Benchmarks drawer in the shell
- a payload contract for current metrics, deltas, and freshness state
- dynamic refresh behavior from latest benchmark truth
- readable handling for pass, fail, stale, and unavailable states
- links from drawer readouts to fuller benchmark detail when needed

## Non-Goals
- replacing the full benchmark report or graph generation pipeline
- inventing a separate benchmark truth store outside the existing governed
  report path
- turning the first pass into a generic analytics dashboard
- showing every raw metric the harness can produce

## Risks
- the drawer can become misleading if freshness and provenance are not obvious
- dynamic refresh behavior may drift from the real benchmark report contract
  unless it fails closed
- too many metrics would make the drawer noisy and hard to scan
- maintainers might over-trust a summary drawer if it hides important baseline
  context

## Dependencies
- `B-021` is already expanding benchmark frontier and should define the current
  proof shape this drawer surfaces
- `B-022` is hardening benchmark integrity, which this drawer must preserve
  rather than water down
- `B-033` already calls for benchmark visibility in maintainer workflow and is
  the natural nearby umbrella for release-facing proof narrative

## Success Metrics
- Odylith exposes one Benchmarks drawer with current headline benchmark posture
- maintainers can inspect the key benchmark metrics without leaving the shell
- freshness timestamps and baseline provenance are obvious in the drawer
- benchmark updates appear in the drawer without manual file inspection
- the summary surface stays aligned with the governed benchmark report

## Validation
- `odylith sync --repo-root . --check-only`
- targeted tests for benchmark payload normalization, freshness handling, and
  drawer rendering
- integration coverage that proves the drawer updates from current benchmark
  truth
- manual shell walkthrough covering pass, fail, stale, and unavailable states

## Rollout
Land the metric contract first, ship the drawer UI second, then tighten dynamic
refresh and release-workflow integration once the readout is stable and
trustworthy.

## Why Now
Odylith now treats benchmark proof as part of its product credibility, so the
current benchmark story should not stay buried in files and release ceremony.
The product itself should surface the proof it expects people to trust.

## Product View
If benchmark truth matters enough to gate releases and shape the public story,
it matters enough to deserve a live product surface.

## Impacted Components
- `odylith`
- `dashboard`
- `benchmark`
- `release`

## Interface Changes
- add a Benchmarks drawer with headline status, metrics, deltas, and freshness
  readouts
- support links from drawer summaries to fuller benchmark detail
- add dynamic refresh hooks so the drawer follows current benchmark truth
- expose empty and stale states as explicit UI, not silent gaps

## Migration/Compatibility
- keep existing benchmark reports and release proof authoritative
- make the drawer additive so older flows still work while the shell catches up
- preserve benchmark compare semantics instead of inventing incompatible delta
  labels

## Test Strategy
- add contract tests for benchmark drawer payload fields and stale-state rules
- add UI tests for the drawer's summary, history, and fallback states
- verify dynamic refresh against the latest benchmark artifact path

## Open Questions
- whether the drawer should live as a global shell affordance or a maintainer
  mode affordance only
- which three to five metrics are the right default summary set
- how much history belongs in the drawer before it should hand off to a fuller
  benchmark detail view
