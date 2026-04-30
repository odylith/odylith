status: queued

idea_id: B-133

title: v0.1.15+ Durable Decisions Annotations and Memory Hygiene

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: Memory Backend, Memory Contracts, Context Engine, Compass intervention stream, Casebook, Radar, technical plans, annotation capture, raw thread suppression, durable judgment memory, and collaboration summaries

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Shared memory becomes a liability unless Odylith distinguishes durable decisions and resolved annotations from raw conversation exhaust before enterprise collaboration inputs arrive.

confidence: high

founder_override: no

promoted_to_plan: 

execution_model: standard

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
Enterprise multi-agent workflows generate large amounts of conversational, review, trace, and tool-output data. If Odylith stores raw threads as durable memory, memory can become noisy, stale, secret-bearing, or prompt-injection contaminated. If it stores too little, handoffs lose decisions and policy rationale. Odylith needs a governed annotation and decision-memory contract that preserves distilled outcomes while suppressing raw exhaust.

## Customer
Primary customers are maintainers and agents that need decisions, approvals, reversals, contradictions, and review outcomes to survive across sessions. Secondary customers are enterprise teams that need defensible memory retention, redaction, and audit posture.

## Opportunity
Odylith can turn collaboration memory into a governed advantage by retaining only resolved summaries, durable decisions, contradiction records, proof outcomes, and provenance. That lets humans and agents operate from shared memory without turning every chat or trace into authoritative context.

## Proposed Solution
Create the workstream for v0.1.15+ Durable Decisions Annotations and Memory Hygiene and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Durable Decisions Annotations and Memory Hygiene.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Context Engine grounding prefers resolved decisions and durable annotations over raw threads. Memory validation rejects placeholder summaries, transcript-shaped durable refs, secret-bearing annotations, and unproven policy changes. Compass can show pending versus resolved annotations. Casebook and Radar can link decisions to bugs, plans, and workstreams. Benchmarks prove lower stale-memory and decision-loss rates.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Add a durable annotation and decision-memory contract. Raw comments, chat threads, and full traces remain transient or hosted-only. Tracked truth receives resolved annotation summaries with actor, artifact, timestamp, status, decision class, affected component, and evidence links. Memory Contracts compact those summaries into packets; Memory Backend retains freshness, contradiction, outcome, and provenance signals; Context Engine excludes transcript-shaped source refs from durable grounding.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- No migration impact recorded yet.

## Test Strategy
- Add targeted regression coverage when implementation begins.

## Open Questions
- Which existing workstreams or component specs should this attach to first?
