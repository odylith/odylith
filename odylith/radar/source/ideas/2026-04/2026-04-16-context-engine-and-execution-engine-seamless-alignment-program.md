---
status: queued
idea_id: B-099
title: Context Engine and Execution Engine Seamless Alignment Program
date: 2026-04-16
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: Context Engine packets, Execution Engine snapshots, benchmark execution-engine family, Codex and Claude host profiles, router and orchestrator guards, remediator checks, shell and Compass summaries, Registry specs, Atlas diagrams, Radar programs, technical plans, and release benchmark docs
sizing: XL
complexity: VeryHigh
ordering_score: 70
ordering_rationale: The product already has separate Context Engine and Execution Engine surfaces, but the strongest user value only appears when they align with measured, host-general precision. Benchmark proof first prevents the alignment program from becoming a narrative-only cleanup and catches live drift before enforcement and cost tuning build on it.
confidence: high
founder_override: no
promoted_to_plan:
execution_model: umbrella_waves
workstream_type: umbrella
workstream_parent:
workstream_children: B-100,B-101,B-102,B-103,B-104
workstream_depends_on: B-072,B-084,B-092,B-093
workstream_blocks:
related_diagram_ids: D-002,D-024,D-030,D-031
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
The Context Engine and Execution Engine are now both first-class product components, but their strongest guarantees are spread across finished execution-engine work, active benchmark proof, host parity plans, and packet/runtime surfaces. The current focused proof already shows drift: a benchmark scenario that still uses the stale noncanonical component id resolves to recover/unknown_component while the canonical execution-engine id resolves to the intended verify posture. That drift means host agents can lose precision exactly at the boundary between grounded context and admissible execution.

## Customer
Primary: Odylith operators using Codex and Claude Code who need grounded context to turn into the right next action without extra latency, token burn, or host-specific drift. Secondary: Odylith maintainers who need one governed program that coordinates benchmark proof, handshake normalization, execution guards, host parity, hot-path cost, and release-proof truth without swelling red-zone runtime files.

## Opportunity
Build a benchmark-backed alignment program that proves the Context Engine to Execution Engine handshake first, then hardens enforcement coverage, host parity, and snapshot reuse from measured evidence. The program should make `execution-engine` the only accepted component id and make every downstream guard consume the same execution snapshot.

## Proposed Solution
Create the workstream for Context Engine and Execution Engine Seamless Alignment Program and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Context Engine and Execution Engine Seamless Alignment Program.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
The execution benchmark family catches stale-identifier drift, false admits, false denies, wrong next moves, wrong closure, wrong validation posture, missing resume tokens, and host-family mismatches. Only `execution-engine` resolves to route-ready packet posture; stale identifiers fail closed before execution. Codex and Claude share policy semantics while differing only through capability-gated host fields. Context/Execution packet handoffs reuse one compact snapshot across surfaces. Focused execution tests, host parity tests, benchmark family tests, registry validation, backlog validation, atlas checks, sync checks, and git diff checks pass.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should treat the Context Engine as the deterministic evidence-cone compiler and the Execution Engine as the admissible-motion contract. This program makes that split product-real across packet builders, benchmark families, router and orchestrator guards, remediator checks, shell and Compass summaries, Codex and Claude host profiles, and release docs. New implementation logic must live in focused helpers rather than adding business logic to the already oversized benchmark runner or context store.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- Hard cut: the program does not carry historical execution identifiers forward. `execution-engine` is the only accepted component id across the alignment work.

## Test Strategy
- Add targeted regression coverage when implementation begins.

## Open Questions
- Which existing workstreams or component specs should this attach to first?
