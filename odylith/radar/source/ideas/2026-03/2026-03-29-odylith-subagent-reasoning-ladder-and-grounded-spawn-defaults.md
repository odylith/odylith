---
status: finished
idea_id: B-015
title: Odylith Subagent Reasoning Ladder and Grounded Spawn Defaults
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: Subagent Router, Subagent Orchestrator, Context Engine hot-path execution profiles, consumer agent guidance, consumer skills, and benchmark proof
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith already beats the raw repo-scan baseline, but its delegated execution ladder is still leaving leverage on the table. The runtime, router, orchestrator, and consumer guidance all need a tighter shared contract so grounded slices climb to stronger reasoning only when they have earned it, while fast bounded work stays cheap. This slice should improve routed accuracy, default delegation posture, and measured adoption proof without regressing the green benchmark.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-subagent-reasoning-ladder-and-grounded-spawn-defaults.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001, B-009, B-013
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
Odylith already has a routed delegation stack, but it is not yet as disciplined
or as leveraged as it should be. Deeper reasoning promotion is still too
additive instead of explicitly earned, the runtime execution profile does not
always align cleanly with router selection, prompt-level orchestration is still
more conservative than necessary on some grounded slices, and the consumer
guidance does not yet make "ground, then delegate by default in Codex" feel
like the obvious happy path.

## Customer
- Primary: Odylith consumers using Codex who want delegation to feel faster,
  sharper, and more reliable out of the box.
- Secondary: Odylith maintainers who need a tighter shared contract between the
  Context Engine, Router, Orchestrator, consumer guidance, and benchmark proof.

## Opportunity
If Odylith makes delegation depth something the runtime can earn and spend
judiciously, then bounded work can stay cheap, higher-risk slices can climb to
stronger reasoning only when the evidence cone supports it, and more grounded
prompts can take the delegated happy path by default. That should improve
quality and adoption without giving back the benchmark wins Odylith already has.

## Proposed Solution
Add explicit earned-depth and delegation-readiness posture to routed task
assessment, use that posture to tighten Router profile selection and
Orchestrator fan-out decisions, align the Context Engine's synthesized
execution-profile hints with the stronger routing ladder, and update consumer
guidance so Codex users default to Odylith-grounded delegation for most
substantive bounded prompts.

## Scope
- add explicit earned-depth and delegation-readiness signals to routed task
  assessment
- improve Router profile scoring and backstops so stronger tiers are only
  selected when grounded depth is earned
- tighten Orchestrator fan-out posture so grounded, route-ready slices delegate
  more often while guarded slices stay serial or local
- align hot-path execution-profile synthesis with the Router's stronger routing
  ladder
- update consumer-facing subagent guidance and skills so Codex users default to
  Odylith-backed delegation for most grounded prompts
- prove the change with focused router/orchestrator tests and benchmark runs

## Non-Goals
- enabling native subagent spawning in Claude Code
- broad redesign of the benchmark corpus
- changing the public surface contract away from Codex-only native spawn

## Risks
- over-promoting grounded slices into heavier models and giving back token or
  latency wins
- making delegation more aggressive without enough guardrails for ambiguous or
  merge-heavy slices
- drifting the consumer guidance away from the actual routed runtime contract

## Dependencies
- `B-009` established the benchmark proof lane and its current green baseline
- `B-013` centralized shared runtime-contract reuse so the execution-profile
  contract can be tightened once instead of in parallel local variants

## Success Metrics
- grounded delegated Codex slices climb the reasoning ladder more predictably
- guarded or low-yield slices stay on lighter or local lanes more often
- consumer guidance clearly defaults to Odylith-backed Codex delegation for
  most grounded substantive prompts
- benchmark proof stays green and improves on at least one measured adoption,
  token, or latency signal without regressing recall or validation

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_evaluation_ledger.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_subagent_surface_validation.py`
- `odylith benchmark --repo-root .`

## Rollout
Ship as a product-contract tightening slice. Keep the public native spawn
boundary Codex-only, align the consumer guidance to that contract, and close
the slice only after benchmark proof and source truth are updated together.

## Why Now
Odylith's biggest compounding advantage comes from grounded delegation. Leaving
that path conservative or inconsistently earned wastes product leverage and
benchmark headroom.

## Product View
Odylith should feel like a disciplined execution system, not just a richer
prompt bundle. The reasoning ladder has to be explicit, cheap when it can be,
and strong when it must be.

## Impacted Components
- `odylith-context-engine`
- `subagent-router`
- `subagent-orchestrator`
- `odylith`

## Interface Changes
- grounded Codex slices now promote into stronger delegated posture more
  deliberately
- consumer guidance now defaults to Odylith-backed Codex delegation more often
- Claude Code remains guidance-compatible but not native-spawn-enabled

## Migration/Compatibility
- no migration required
- Codex remains the only supported native spawn target
- existing local-only fallback posture remains available for guarded slices

## Test Strategy
- add focused router and orchestrator regression coverage
- rerun the evaluation ledger and benchmark harness
- verify no recall or validation regression accompanies the stronger spawn rate

## Open Questions
- should a later slice expose the earned-depth posture more directly in Compass
  or the shell for operator visibility

## Outcome
- grounded delegated adoption proof improved from `0.100` to `0.800`
- median prompt and total payload tokens improved to `-631.5` versus the
  full-scan baseline
- median latency improved to `-15.015 ms` with no recall or validation
  regression
- consumer-facing Odylith skills, agent guidance, and product surface paths now
  route as contract or implementation work instead of collapsing into local
  governance follow-up
