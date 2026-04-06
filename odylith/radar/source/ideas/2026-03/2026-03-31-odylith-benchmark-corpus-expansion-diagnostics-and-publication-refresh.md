---
status: queued
idea_id: B-039
title: Odylith Benchmark Corpus Expansion, Diagnostics, and Publication Refresh
date: 2026-03-31
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: benchmark corpus, benchmark report diagnostics, README publication, dashboard freshness, and benchmark review guidance
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Once B-022 moved to an honest `odylith_on` versus `odylith_off` benchmark, the next leverage is proving the result over a broader harder suite and publishing the real hotspot diagnostics that explain why Odylith wins or loses.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-022
workstream_children:
workstream_depends_on: B-021, B-022, B-038
workstream_blocks:
related_diagram_ids: D-024
workstream_reopens:
workstream_reopened_by:
workstream_split_from: B-022
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
The current 30-scenario suite is better than the older 24-case floor, but it
is still too thin to call a comprehensive proof across the weak families.
The report also does not yet publish enough hot-path diagnostics to show where
Odylith is still paying drag versus `odylith_off`.

## Customer
- Primary: Odylith maintainers and reviewers who need a broader and harder
  benchmark before trusting product claims.
- Secondary: users evaluating whether Odylith's extra tokens and latency are
  worth it across real repo-work families rather than a thin snapshot.

## Opportunity
A stronger corpus and clearer diagnostics make the benchmark harder to game and
more useful for product steering. The same refresh also fixes stale dashboard
and README surfaces so the public story cannot drift from the current report.

## Proposed Solution
Expand the benchmark suite in the weak families, publish the selector and
compaction diagnostics that explain the remaining wins and losses, and refresh
README and dashboard surfaces only from the rerun report that actually clears
the hardened contract.

## Scope
- grow the benchmark suite with more realistic scenarios in the weak families
- add report diagnostics for selector behavior, cache reuse, architecture
  compaction, and cold-versus-warm hotspots
- refresh README, benchmark docs, and dashboard-facing artifacts from the
  rerun report only
- keep the public story centered on `odylith_on` versus `odylith_off`

## Non-Goals
- reducing benchmark difficulty to make Odylith look better
- changing the public claim back to repo-scan as the primary baseline
- publishing a benchmark story that is ahead of the real rerun report

## Risks
- corpus growth could become shallow if the new scenarios do not cover distinct
  slices or validation postures
- more diagnostics could add noise instead of clarity if they are not bounded
  to the honest improvement story
- dashboard refreshes can drift again if the generated surfaces are not synced
  with the source truth in the same change

## Dependencies
- `B-022` defines the umbrella honest-benchmark contract
- `B-038` improves the weak-family runtime that the expanded benchmark will
  measure more harshly
- `B-021` already broadened the prior corpus and is the baseline this child
  extends

## Success Metrics
- the benchmark corpus becomes materially broader than the current 30-scenario
  suite
- the report publishes the diagnostic signals needed to explain hot-path wins
  and losses honestly
- README and benchmark surfaces refresh from the rerun without stale index or
  dashboard drift

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py tests/unit/runtime/test_hygiene.py`
- `PYTHONPATH=src python3 -m odylith.cli benchmark --repo-root .`
- `git diff --check`

## Rollout
Expand the corpus and diagnostics after the hot-path runtime improvements land,
rerun the benchmark, then refresh the README and dashboard surfaces from that
exact report and sync the generated Odylith views.

## Why Now
An honest benchmark needs both a stronger runtime and a harder scoreboard.

## Product View
If Odylith only looks good on a thin suite, then it does not actually look
good. This child exists to make the scoreboard harder while keeping the public
story tied to the real result.

## Impacted Components
- `benchmark`
- `dashboard`
- `odylith-context-engine`

## Interface Changes
- benchmark reports expose more selector, cache, and compaction diagnostics
- README and benchmark docs publish the latest honest `odylith_on` versus
  `odylith_off` rerun instead of stale snapshots
- dashboard-facing Odylith benchmark surfaces stay in sync with Radar and plan
  truth

## Migration/Compatibility
- no consumer migration required
- older benchmark history remains readable; the new diagnostics only enrich the
  current report contract

## Test Strategy
- add corpus tests that enforce the higher scenario floor and weak-family
  coverage
- add runner and hygiene tests for the new report diagnostics and sync posture
- rerun the full benchmark before regenerating any public-facing benchmark
  assets

## Open Questions
- whether the next corpus wave should introduce a separate adversarial family or
  continue folding anti-gaming cases into the existing families

## Current Status
- The current source-local full proof `52aa3f76538cf12f` is now
  `provisional_pass`, so the README, benchmark docs, graphs, and governed
  benchmark surfaces can refresh from a green proof floor instead of waiting on
  a blocked pass-recovery report.
- This child remains queued for the next broader wave after the current
  refresh: expand the corpus beyond the current `37` scenarios, publish richer
  diagnostics, and convert the source-local pass into a first shipped release
  baseline once pinned dogfood proof is complete.
