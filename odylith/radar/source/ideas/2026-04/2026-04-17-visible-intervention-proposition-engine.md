status: implementation

idea_id: B-106

title: Visible Intervention Proposition Engine

date: 2026-04-17

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: governance-intervention-engine, conversation_surface, visibility_broker, host surfaces

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: This is the runtime core that makes multi-signal visible intervention useful instead of noisy.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on: B-105

workstream_blocks:

related_diagram_ids: D-038

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
The runtime must select visible Odylith blocks from distinct supported propositions, not from block labels or a hand-tuned pseudo-ML ranker.

## Customer
Operators using Codex and Claude who need high-value Odylith observations without duplicate, stale, unsupported, or hidden-only claims.

## Opportunity
Build the proposition ledger, hard gates, deterministic utility features, conflict graph, subset selector, and compact decision log as the v0.1.11 core.

## Proposed Solution
Create the workstream for Visible Intervention Proposition Engine and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Visible Intervention Proposition Engine.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
The value-engine package owns proposition contracts, hard gates, adaptive budget, duplicate collapse, proposal dependency checks, and p95 selector latency at or below 15 ms in focused tests, with contracts/scoring, selection, and corpus/reporting split into focused modules instead of one oversized runtime file.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should surface the smallest high-value set of true, timely, distinct propositions that materially improve the user's next move.

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
