---
status: implementation
idea_id: B-110
title: Discipline, Credit-Safe And Benchmark-Proved
date: 2026-04-17
priority: P0
commercial_value: 5
product_impact: 5
market_value: 5
impacted_parts: Context Engine, Execution Engine, Proof State, memory substrate, subagent router/orchestrator, intervention engine, Chatter, Tribunal, Benchmark, Radar, Compass, Casebook, Registry, Atlas, Dashboard, Codex and Claude host guidance
sizing: XL
complexity: High
ordering_score: 83
ordering_rationale: v0.1.11 final alignment: Odylith needs Odylith Discipline, continuous learning, benchmark sovereignty, and zero hidden host-model credit burn as one release-bound platform layer.
confidence: high
founder_override: yes
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-17-adaptive-agent-operating-character-credit-safe-and-benchmark-proved.md
execution_model: umbrella_waves
workstream_type: umbrella
workstream_parent: 
workstream_children: B-111, B-112, B-113, B-114, B-115, B-116, B-117
workstream_depends_on: 
workstream_blocks: 
related_diagram_ids: D-039
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
Odylith now gives agents more context, tools, delegation, memory, interventions, and benchmark surfaces, but those capabilities are not yet governed by one adaptive runtime model of engineering discipline under pressure. Guidance behavior is testable, but it is still too easy for discipline, memory, proof, host parity, latency, credit safety, and public accountability to land as adjacent checks instead of one operating loop.

## Customer
Odylith maintainers, Codex and Claude Code users, and consumer-lane operators who need agents to become more grounded, restrained, decisive, honest, coordinated, memory-aware, proof-seeking, low-latency, high-signal, and credit-safe when work becomes ambiguous, risky, tempting, fast-moving, or novel.

## Opportunity
Make Odylith Discipline the v0.1.11 center of gravity: local pressure observations become an adaptive stance vector, deterministic hard laws constrain unsafe moves, ranked affordances keep admitted work moving, proof governs claims, compact learning changes the next run, Tribunal diagnoses recurrence, surfaces publish status, and benchmarks prove behavior lift without hidden host-model credit burn.

## Proposed Solution
Create a release-bound platform layer that runs local discipline checks, applies immutable hard laws, infers adaptive stance from open-world pressure features, records compact learning, stays silent unless signal is earned, and proves behavior through deterministic validation plus `guidance_behavior` and `agent_operating_character` benchmarks.

## Scope
- Define and land the bounded work for Odylith Discipline.
- Keep hard laws deterministic while stance, affordances, intervention visibility, and learning priors remain adaptive.
- Keep the hot path local, low-latency, and zero-credit.
- Prove durable learning through validators, benchmarks, or Tribunal doctrine before it changes future defaults.

## Non-Goals
- Do not widen this workstream into unrelated product cleanup.
- Do not convert named postures into a rigid runtime state machine.
- Do not add model/provider calls to hot discipline checks.
- Do not publish behavior claims from mechanism checks or diagnostic-only proof.

## Risks
- Existing pinned dogfood runtime integrity is degraded; shipped-runtime proof cannot be claimed until that is repaired.
- A stance kernel can become a noisy rule engine if intervention visibility is not gated by concrete user value.
- Continuous learning can become unsafe if weak session signals silently harden into durable doctrine.

## Dependencies
- B-096 remains the visible intervention umbrella.
- B-099 through B-104 provide execution, context, host parity, and release-proof grounding.
- B-105 through B-109 provide the visible intervention and guidance-behavior proof lane.
- CB-104 anchors CLI-first governed truth discipline.
- CB-121, CB-122, and CB-123 anchor the recent guidance/intervention proof context where applicable.

## Success Metrics
- `odylith validate agent-operating-character --repo-root .` passes deterministically and credit-free.
- `odylith validate guidance-behavior --repo-root .` remains green as the first pressure-family lane.
- `odylith benchmark --profile quick --family agent_operating_character --no-write-report --json` passes before merge.
- Hot-path discipline checks report zero provider calls, zero host model calls, zero broad scans, zero full validations, and zero projection expansion.
- Release proof uses full matched `odylith_on` versus `raw_agent_baseline` benchmarks before public claims.
- Compact learning events flow back into memory without raw transcript storage.
- Codex and Claude share the same Odylith Discipline contract across dev, dogfood, and consumer lanes.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This is the v0.1.11 brand-level center of gravity: more capability requires more discipline, and discipline only matters if it remains adaptive, low-latency, high-signal, credit-safe, and benchmark-proved.

## Product View
Odylith should feel like a disciplined engineering partner, not a louder rule engine. The product detects local pressure observations, infers an adaptive stance vector, applies deterministic hard laws, ranks the right tool affordances, blocks or redirects the wrong move, keeps admitted action moving, records compact practice memory, escalates repeated ambiguity, and proves the result through `guidance_behavior` and `agent_operating_character` benchmark families without burning hidden host credits.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `execution-engine`
- `proof-state`
- `odylith-memory-contracts`
- `odylith-memory-backend`
- `subagent-router`
- `subagent-orchestrator`
- `governance-intervention-engine`
- `odylith-chatter`
- `tribunal`
- `benchmark`
- `radar`
- `compass`
- `casebook`
- `registry`
- `atlas`
- `dashboard`

## Interface Changes
- Add `odylith_agent_operating_character.v1`.
- Add `odylith_agent_operating_character_learning.v1`.
- Add `odylith_agent_operating_character_runtime_budget.v1`.
- Add `odylith validate agent-operating-character --repo-root . [--case-id ID...] [--json]`.
- Add `odylith discipline status/check/explain`.
- Add `agent_operating_character` benchmark family.

## Migration/Compatibility
- Existing `guidance_behavior` commands and benchmark cases remain intact.
- New discipline checks are additive and deterministic.
- Durable learning is bench-gated; session hints cannot silently become doctrine.

## Test Strategy
- Add unit tests for hard laws, pressure observations, stance vectors, budget enforcement, learning events, and CLI output.
- Add validator tests for corpus shape, selected cases, JSON output, exit codes, bundle mirrors, unknown pressure, adaptive replay, and zero-credit hot paths.
- Add benchmark tests for family selection, hard gates, novelty/generalization, learning replay, false allow, false block, latency, provider/model call counts, and publication blocking.

## Open Questions
- Track this as its own v0.1.11 umbrella workstream, not a child of B-096.
- Keep B-096 as the visible intervention umbrella and consume it as one subsystem of the broader Odylith Discipline loop.
