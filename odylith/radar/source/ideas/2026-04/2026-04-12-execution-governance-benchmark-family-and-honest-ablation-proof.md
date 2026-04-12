status: implementation

idea_id: B-092

title: Execution Governance Benchmark Family and Honest Ablation Proof

date: 2026-04-12

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: benchmark corpus families, benchmark runner family gates, execution governance packet expectations, benchmark docs, and benchmark publication truth

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: The execution engine is now implemented, but the benchmark still cannot isolate whether execution governance materially improves grounded next-move quality versus the raw baseline. Odylith needs a first-class benchmark family that proves the engine's value on real packet-backed slices before its claims become release-safe benchmark narrative.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-12-odylith-execution-governance-benchmark-family-and-honest-ablation-proof.md

workstream_type: child

workstream_parent: B-021

workstream_children: 

workstream_depends_on: B-021,B-072,B-091

workstream_blocks: 

related_diagram_ids: D-024,D-030

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

## Problem
Odylith now has a real execution-governance engine, but the benchmark cannot
yet prove whether that engine improves agent behavior more than it adds cost or
friction. The current corpus has no family that directly measures admissibility,
frontier truth, closure posture, validation derivation, resumability, and
host-aware execution posture as benchmark quality signals.

## Customer
- Primary: Odylith maintainers who need benchmark proof that the execution
  engine is a net quality gain rather than a control-plane tax.
- Secondary: benchmark readers and release reviewers who need evidence that
  execution governance improves real grounded coding-agent behavior.

## Opportunity
If Odylith adds an execution-governance benchmark family now, the benchmark can
show whether the engine improves truthful next-move selection, fail-closed
scope control, validation discipline, and resumability on real current-repo
slices instead of relying on anecdote or broad benchmark aggregates.

## Proposed Solution
Add a dedicated `execution_governance` benchmark family with representative
packet scenarios, family metrics for outcome, mode, next move, closure,
validation, re-anchor, host carry-through, and resumability, plus runner
acceptance gates that treat execution-governance regressions as real benchmark
quality failures. Keep the family honest by benchmarking real current-repo
packet truth and by preserving the existing `odylith_on` versus
`raw_agent_baseline` matched-pair contract.

## Scope
- add an `execution_governance` family to the tracked benchmark corpus
- add benchmark-family metrics and comparison deltas for the execution engine
- extend packet expectation matching only where the current benchmark contract
  cannot yet score real execution-governance fields
- add current-repo packet probe tests so the family is grounded in live packet
  truth instead of synthetic expectations alone
- update benchmark docs, taxonomy, and benchmark component truth to describe the
  family and its gates
- keep the family additive to the benchmark contract and aligned with the
  governed-sync hot-path guarantees from `B-091`

## Non-Goals
- redesigning benchmark publication infrastructure
- inventing a second ablation system outside the existing benchmark harness
- weakening the raw-agent baseline just to make execution governance look better

## Risks
- the family could become redundant with generic expectation success if its
  metrics are not specific enough to execution governance
- execution-governance packet truth may still be too unstable on some live
  slices, which would surface real product issues immediately
- benchmark-family additions could accidentally reopen sync or publication
  churn if they are not kept additive and content-addressed

## Dependencies
- `B-021` already owns benchmark corpus expansion and weak-family proof
- `B-072` delivered the execution-governance runtime being measured
- `B-091` hardened governed-sync reuse and content-addressed surface writes that
  this benchmark slice must preserve

## Success Metrics
- the tracked benchmark corpus includes a first-class `execution_governance`
  family with real current-repo packet scenarios
- benchmark reports publish execution-governance family metrics for truthful
  next-move quality, closure posture, validation derivation, and resumability
- acceptance and family summaries can fail benchmark quality directly when the
  execution engine regresses
- focused unit, browser-safe benchmark suites, and governed-sync proof stay
  green with the new family in place

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_odylith_benchmark_execution_governance.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_corpus.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_execution_governance.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_subagent_reasoning_ladder.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `git diff --check`

## Rollout
Land the family metrics, corpus, and proof first. Then use the new family as
the benchmark floor for future execution-governance changes instead of relying
only on general expectation-success or surface regressions.

## Why Now
Odylith has already shipped the execution engine. The missing piece is proof
that the engine is better than not having it. That proof should exist before
later execution-governance narrative or optimization work compounds.

## Product View
Execution governance is a core claim about how Odylith grounds host agents,
adds guardrails, and keeps them focused. The benchmark should measure that
claim directly.

## Impacted Components
- `benchmark`
- `execution-governance`
- `odylith-context-engine`

## Interface Changes
- new benchmark family: `execution_governance`
- new execution-governance benchmark summary metrics and family-level hard gates

## Migration/Compatibility
- additive benchmark contract only
- no consumer migration required
- benchmark source and bundle mirrors must stay byte-aligned

## Test Strategy
- add focused unit coverage for execution-governance family metrics and
  acceptance behavior
- keep corpus-hardening tests honest about family presence and scenario ids
- add current-repo packet probe coverage so the family stays grounded in live
  execution-governance output
- rerun broader benchmark and governed-sync suites after the family lands

## Open Questions
- whether later benchmark waves should add deeper wait-state and external
  receipt scenarios once the product exposes more stable live wait semantics
