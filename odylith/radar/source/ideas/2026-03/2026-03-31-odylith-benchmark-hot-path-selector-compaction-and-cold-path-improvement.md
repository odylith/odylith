---
status: implementation
idea_id: B-038
title: Odylith Benchmark Hot-Path Selector, Compaction, and Cold-Path Improvement
date: 2026-03-31
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: hot-path selection, guidance-memory recovery, governance packet compaction, warm/cold proof determinism, release publication latency, architecture packet cost, and benchmark weak-family quality
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: The biggest honest benchmark drag is now in Odylith's own hot-path selection, guidance-memory recovery, and packet shaping, especially on cold `release_publication` and other narrow proof slices. Fixing that is the fastest route to a materially better `odylith_on` versus `odylith_off` result without softening the eval.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-31-odylith-raw-codex-baseline-and-four-lane-benchmark-table.md
execution_model: standard
workstream_type: child
workstream_parent: B-022
workstream_children:
workstream_depends_on: B-022
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
`odylith_on` is currently winning the main proof metrics but still paying too
much cold-start and prompt-cost drag in the weak benchmark families,
especially `release_publication`, `component_governance`,
`compass_brief_freshness`, and other narrow proof slices. The runtime still
scans too much projection truth, previously compiled an effectively empty
guidance catalog on benchmark slices, and still lets warm/cold posture change
which truthful slice gets handed to the model.

## Customer
- Primary: Odylith maintainers who need the benchmark runtime to win honestly
  against `odylith_off` on the real same-task workload.
- Secondary: evaluators and users who need Odylith's extra cost to buy
  materially better grounding and validation instead of packet drag.

## Opportunity
The fastest honest benchmark improvement is not narrative tuning. It is making
the hot path more selective, the packet smaller, and the architecture output
more truthful about what the task actually needs.

## Proposed Solution
Improve the runtime slices that currently add the most avoidable cost:
- restore benchmark guidance memory through the canonical manifest at
  `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, with family
  hints flowing into retrieval and packet finalization
- require a non-empty guidance catalog during benchmark warm preflight so
  proof never runs with zero benchmark guidance chunks
- add fast deterministic path-scoped selectors, family-aware doc ceilings, and
  local cache reuse so Odylith stops broad-scanning projection truth on
  benchmark hot paths
- prune weak-family ballast in `release_publication`, explicit-workstream,
  `component_governance`, `consumer_profile_compatibility`,
  `daemon_security`, `compass_brief_freshness`, and governance-heavy closeout
  paths
- enforce strict bounded live handoff on exact-path and anchor-complete proof
  slices so validator-only tests, generated assets, support-doc spillover, and
  miss recovery do not become accidental first-pass reads
- make warm and cold choose the same truthful slice through deterministic
  candidate tie-breaking for docs, tests, and commands
- bias validation-backed developer-core slices such as `agent_activation` and
  `install_upgrade_runtime` toward validator-backed no-op closeout when the
  current tree already satisfies the grounded contract, and treat support docs
  as read-only unless they are explicit write anchors
- align live scenario metadata and scorer semantics with that same no-op
  contract so "already correct" does not still score as a write failure
- compact architecture dossier output specifically by removing non-required
  architecture reads while preserving required-path grounding and expectation
  quality

## Scope
- add fast deterministic selector indexes and process-local cacheing for
  path-scoped workstream and component lookup
- restore family-aware guidance retrieval and canonical benchmark guidance
  manifest resolution
- prune `release_publication` hot-path ballast that does not improve honest
  grounding or validation quality
- make required paths authoritative on weak proof slices when the slice is
  already grounded
- tighten explicit-workstream and governance closeout compaction so Odylith
  stops inflating observed-surface drift
- make warm/cold narrow-slice packets deterministic enough that cache posture
  changes latency, not first-pass truth selection
- compact architecture benchmark packet output without reducing required-path
  recall or expectation quality

## Non-Goals
- softening validators, scenario difficulty, or required reads to make Odylith
  look better
- adding hosted retrieval, hosted reranking, or benchmark-specific shortcuts
- changing the public benchmark contract away from `odylith_on` versus
  `odylith_off`

## Risks
- hot-path pruning could reduce grounding if the selector misses a required
  benchmark surface
- architecture compaction could improve token cost while harming expectation
  quality
- cache reuse could hide stale truth if the cache key is not grounded in the
  projection snapshot
- guidance-memory recovery could look green in unit tests while still leaving
  warm/cold proof slices unstable if deterministic tie-breaking is incomplete

## Dependencies
- `B-022` defines the umbrella honest-benchmark contract
- `B-020` established conservative benchmark publication
- `B-021` expanded the benchmark families that now expose the runtime drag

## Success Metrics
- cold `release_publication` median latency drops materially
- `explicit_workstream` precision improves and hallucinated-surface drift falls
- governance-heavy families keep or improve recall and validation while using
  fewer prompt tokens
- exact-path and narrow bounded proof slices stop flipping into broad
  validator-only or generated-surface widening across cache postures
- both cache profiles clear the hard proof quality gate and
  `within_budget_rate >= 0.80`
- weak families such as `component_governance`, `compass_brief_freshness`,
  `consumer_profile_compatibility`, `daemon_security`, and
  `cross_file_feature` stop widening beyond their truthful slices
- activation and install slices stop spending tokens on speculative guidance
  rewrites when focused validators already pass on the grounded tree
- repair-style live slices stop penalizing validator-backed no-op completion as
  failed expectation or failed write-surface precision
- architecture packet token cost drops without losing required-path recall

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_tooling_guidance_catalog.py tests/unit/runtime/test_tooling_context_retrieval_guidance.py tests/unit/runtime/test_odylith_benchmark_prompt_regressions.py tests/unit/runtime/test_odylith_benchmark_preflight.py`
- `PYTHONPATH=src python3 -m odylith.cli benchmark --repo-root .`
- `git diff --check`

## Rollout
Land guidance-memory recovery and deterministic packet-shaping improvements
first, validate the weak families with focused tests, rerun targeted weak
family proof shards, then feed the improved diagnostics into the broader B-022
publication refresh before the next full proof run.

## Why Now
Odylith will not honestly beat `odylith_off` by narrative. It has to do less
unnecessary work while staying just as grounded.

## Product View
If Odylith needs more time or tokens, those costs must buy real quality. This
child exists to remove the part of Odylith's cost that is just waste.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `tribunal`
- `compass`
- `odylith-memory-backend`

## Interface Changes
- benchmark hot-path impact selection becomes more bounded and diagnostics-aware
- benchmark architecture packets publish more compact truthful required reads
- weak-family packet shaping becomes more selective by family and task context
- canonical benchmark guidance now resolves from
  `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, with legacy
  fallback kept only for compatibility

## Migration/Compatibility
- no consumer migration required
- benchmark history remains readable because this changes runtime selection, not
  report schema compatibility

## Test Strategy
- add focused runner tests for selector diagnostics, cache hits, and compact
  architecture behavior
- rerun the benchmark and compare `odylith_on` versus `odylith_off` on the same
  corpus before refreshing publication surfaces

## Open Questions
- whether the remaining architecture weakness needs deeper architecture-mode
  shaping after the current compaction wave
- when deterministic boundary, selector, and packet-shaping gains plateau,
  whether a learned component or path reranker should enter between candidate
  collection and live prompt handoff rather than earlier in the pipeline

## Current Status
- Guidance-memory recovery, deterministic packet shaping, and strict bounded
  weak-family live handoff are already landed.
- `architecture` and `daemon_security` are no longer active weak families for
  this child; `daemon_security` now clears both warm proof
  (`f610654ed299d4f0`) and cold proof (`21d2c37e284693e4`) with validator-
  backed no-op, full recall, full precision, zero hallucinated surfaces, and
  zero widening against `odylith_off`.
- `component_governance`, `compass_brief_freshness`,
  `consumer_profile_compatibility`, and `governed_surface_sync` all recovered
  enough on the current tree for the full proof report `52aa3f76538cf12f` to
  clear the hard quality gate and secondary guardrails.
- The benchmark runner also now bounds the post-run adoption-proof finalizer,
  which closes the last infrastructure path that could keep a finished proof
  from being written after the runtime work already won.
- The remaining family list on the passing published view is advisory:
  `architecture`, `browser_surface_reliability`, `component_governance`,
  `cross_surface_governance_sync`, `governed_surface_sync`, and
  `orchestration_feedback`.
