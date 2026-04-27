---
status: finished
idea_id: B-068
title: Context Engine Benchmark Family and Grounding Quality Gates
date: 2026-04-08
priority: P0
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: benchmark corpus families, benchmark runner quality gates, Context Engine packet summary contract, benchmark docs, and Context Engine benchmark regression coverage
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: The Context Engine just went through a hard structural refactor and is about to be used as the basis for deeper architecture work. Before more changes land, Odylith needs a dedicated benchmark family that measures whether the engine still picks the right packet lane, resolves the right scope, stays fail-closed on ambiguity, and keeps runtime-backed session scope disciplined.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-08-odylith-context-engine-benchmark-family-and-grounding-quality-gates.md
execution_model: standard
workstream_type: child
workstream_parent: B-021
workstream_children:
workstream_depends_on: B-021,B-063,B-067
workstream_blocks:
related_diagram_ids: D-002,D-024
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
Odylith now relies on the Context Engine for release resolution, proof-state
grounding, adaptive packet selection, and bounded scope control, but the
benchmark does not yet measure those behaviors as a first-class family. That
means the engine can regress in packet-lane selection, workstream resolution,
or ambiguity discipline without a dedicated benchmark signal calling it out.

## Customer
- Primary: Odylith maintainers changing Context Engine architecture, packet
  routing, and scope resolution.
- Secondary: benchmark readers who need to trust that Context Engine
  improvements are measured before they are narrated.

## Opportunity
If Odylith adds a dedicated Context Engine benchmark family now, later
architecture work can be judged against a hard grounding contract instead of
relying on anecdote or broad aggregate metrics.

## Proposed Solution
Add a `context_engine_grounding` benchmark family with representative packet
and architecture scenarios, family-specific accuracy metrics for packet-lane
selection and scope resolution, explicit ambiguity fail-closed checks, and
runner acceptance logic that treats those regressions as real benchmark
quality problems.

## Scope
- add Context Engine benchmark scenarios for adaptive split-boundary
  grounding, governance-slice grounding, release-resolution grounding, and
  fail-closed broad-scope behavior
- add family-specific benchmark metrics for packet-source accuracy,
  selection-state accuracy, workstream accuracy, ambiguity fail-closed
  behavior, and runtime-backed session namespacing
- expose any missing packet-summary fields needed for those metrics
- update benchmark docs and benchmark component truth to describe the new
  family and metrics
- prove the family with focused and broader benchmark plus Context Engine
  regressions

## Non-Goals
- deeper collaboration-memory architecture changes
- new public CLI features
- softening the benchmark to make Context Engine changes look cleaner

## Risks
- the first family may expose real regressions in the newly split Context
  Engine code
- a vague family definition could overlap too heavily with existing grounding
  families and dilute signal
- missing packet-summary fields could leave the benchmark measuring proxies
  instead of the actual Context Engine contract

## Dependencies
- `B-021` already owns benchmark corpus growth and weak-family proof
- `B-063` added release-resolution behavior that should now be benchmarked
- `B-067` changed the Context Engine's internal module boundaries and raised
  the need for direct benchmark coverage

## Success Metrics
- the tracked benchmark corpus includes a dedicated `context_engine_grounding`
  family with representative Context Engine scenarios
- benchmark reports now publish Context Engine packet-source, selection-state,
  workstream, and ambiguity fail-closed accuracy metrics
- acceptance and family summaries flag Context Engine grounding regressions
  explicitly instead of burying them in generic expectation rates
- the family is proven by focused and broader regression suites on the current
  repo truth

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_context_engine.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_context_engine_split_hardening.py tests/unit/runtime/test_context_engine_release_resolution.py tests/unit/runtime/test_context_engine_topology_contract.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `git diff --check`

## Rollout
Land the family, quality gates, and docs first, then use that benchmark family
as the proof floor for the next Context Engine architecture improvements.

## Why Now
The right time to benchmark the Context Engine directly is before another wave
of architecture changes, not after maintainers have already convinced
themselves the new behavior is better.

## Product View
The Context Engine is core product infrastructure now. It should have a
benchmark family that measures its actual contract the same way proof-state and
release planning now do.

## Impacted Components
- `benchmark`
- `odylith-context-engine`

## Interface Changes
- new benchmark family: `context_engine_grounding`
- new benchmark summary metrics and acceptance checks for Context Engine
  grounding quality

## Migration/Compatibility
- additive benchmark contract only
- no consumer migration required
- benchmark source and bundle mirrors must stay byte-aligned

## Test Strategy
- add focused unit coverage for the family metrics and current-repo packet
  probes
- keep corpus-hardening tests honest about family presence and scenario count
- rerun broader benchmark and Context Engine suites after the new family lands

## Open Questions
- whether a later live-proof or collaboration-memory wave should add more
  runtime-backed Context Engine scenarios once those capabilities exist as
  first-class benchmark surfaces
