---
status: queued
idea_id: B-081
title: Atlas Cold Real-Render Daemon Reuse and Sub-Second First-Render Budget
date: 2026-04-10
priority: P0
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: Atlas Mermaid real-render cold path, persistent browser reuse, render-worker lifecycle, auto-update render routing, and render-latency proof
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Atlas review-only refresh is now genuinely fast, which means the remaining product miss is no longer hidden by stale-churn noise. Real diagram edits still pay a multi-second cold Chromium startup tax, so Atlas still fails its strongest operator promise at the exact moment architecture truth actually changes.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: standard
workstream_type: child
workstream_parent: B-025
workstream_children:
workstream_depends_on: B-025,B-080
workstream_blocks:
related_diagram_ids: D-001,D-030
workstream_reopens: B-080
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Atlas now clears review-only freshness debt quickly, but a real Mermaid source
change still misses the sub-second target. The repaired worker writes correct
SVG and PNG outputs, yet the first genuine render still costs about `2.38s`
because each CLI invocation pays fresh Chromium startup and page bootstrap.

## Customer
- Primary: operators and maintainers who edit Atlas diagrams and need the
  topology surface to react like a live tool rather than a delayed batch job.
- Secondary: maintainers trying to keep the Atlas performance claim honest
  across both review-only sync and real render work.

## Opportunity
If Atlas can preserve a warm render runtime across CLI invocations without
weakening validation or stale-watch coverage, then real architecture edits can
clear the same sub-second bar that review-only refresh already hits.

## Proposed Solution
- design a reusable warm Mermaid render lane for Atlas that survives across CLI
  invocations instead of paying fresh browser startup every time
- keep SVG and PNG generation, stale-watch coverage, and validation semantics
  unchanged while changing only the latency posture of the correct path
- make worker ownership, liveness, and cleanup explicit so Atlas does not trade
  cold-start latency for hidden process leaks
- add honest cold-render proof that measures real diagram regeneration instead
  of only review-only sync

## Scope
- warm render-worker lifecycle and reuse contract for Atlas Mermaid renders
- Atlas auto-update routing into the warm lane when a real render is needed
- latency proof for cold first render, not just review-only refresh
- focused worker, lifecycle, and Atlas CLI regressions

## Non-Goals
- weakening `fail-on-stale` or watched-path freshness rules
- dropping PNG generation, validation, or other Atlas features to win the
  benchmark
- redefining review-only refresh as a proxy for real render performance

## Risks
- a warm worker can leak background processes if lifecycle ownership is loose
- shared render state can poison correctness if page or plugin initialization
  is not deterministic between jobs
- a daemon-only path can become brittle if Atlas cannot fail closed back to the
  truthful slower path

## Dependencies
- `B-025` owns the broader cross-surface refresh and runtime discipline
- `B-080` already removed the false stale and review-only taxes, exposing the
  remaining real-render bottleneck honestly
- residual bug: [CB-100](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-atlas-real-render-lane-still-misses-sub-second-bar-after-review-only-fast-path.md)

## Success Metrics
- real Atlas SVG and PNG regeneration stays below `1s` on a cold command path
- repeated real renders stay well below the current `2.38s` worker baseline
- review-only sync remains sub-second and does not regress
- worker reuse does not introduce process leaks or stale render state drift

## Validation
- direct real-render benchmark through the Atlas worker session
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/test_cli.py`
- `PYTHONPATH=src python3 -m odylith.cli atlas auto-update --repo-root . --all-stale`
- one real source-change Atlas render proof with measured wall-clock output

## Rollout
Prototype the reusable warm render lane first, prove it on one real diagram,
then wire it into Atlas auto-update and lock the lifecycle down with tests.

## Why Now
Atlas is already honest about review-only freshness. The remaining failure is
now narrow, measurable, and directly on the path that matters when topology
truth actually changed.

## Product View
The product promise is not "Atlas is fast when nothing real changed." The real
bar is "Atlas stays fast when architecture truth actually moved."

## Impacted Components
- `atlas`
- `odylith-context-engine`
- `dashboard`

## Interface Changes
- additive warm-render lifecycle or daemon ownership disclosure as needed for
  Atlas render reuse

## Migration/Compatibility
- Atlas must keep a truthful fallback when the warm lane is unavailable
- operator-visible semantics stay the same; only latency and lifecycle posture
  should change

## Test Strategy
- cold and warm real-render timing proof
- worker lifecycle and cleanup coverage
- regression proof that review-only sync and real render both stay correct

## Open Questions
- whether Atlas should reuse existing runtime-daemon transport or keep a
  narrower Atlas-specific render-runtime contract
- what idle timeout keeps the warm worker useful without turning it into a
  long-lived leak risk

## Outcome
- Residual cold real-render latency from `B-080` is now tracked as `B-081`
  under `B-025` and `CB-100`.
