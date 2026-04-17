status: implementation

idea_id: B-108

title: Intervention Adjudication Corpus And Advisory Benchmark

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: intervention adjudication corpus, benchmark reporting, value_engine tests, odylith_on proof story

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Without honest corpus provenance the value engine becomes fake ML and damages trust.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on: B-106

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
Selector quality cannot be honestly claimed from synthetic or sparse bootstrap cases, but v0.1.11 still needs regression coverage and advisory mechanism metrics.

## Customer
Maintainers deciding whether Odylith-visible signals are precise, useful, low-noise, and worth brand attention.

## Opportunity
Create a governed adjudication corpus with provenance, density gates, deterministic evaluation, and reports that separate advisory selector metrics from odylith_on outcome proof.

## Proposed Solution
Create the workstream for Intervention Adjudication Corpus And Advisory Benchmark and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Intervention Adjudication Corpus And Advisory Benchmark.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Corpus validation rejects missing provenance, contradictory labels, and synthetic calibration counting; advisory report includes precision, recall, duplicate rate, visibility recall, no-output accuracy, p95 latency, quality_state, and publishable flag.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should be brutally honest about signal quality: bootstrap cases catch regressions, real adjudication earns calibration later, and synthetic data never counts toward public precision claims.

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
