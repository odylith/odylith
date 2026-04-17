status: implementation

idea_id: B-105

title: Visible Intervention Value Engine Governance Binding

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: Radar, Casebook, technical plans, release assignment, governance-intervention-engine

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Governance binding must land before runtime and benchmark claims can be trusted.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on:

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
B-096 needs v0.1.11 governance truth to state that the visible intervention system is proposition-first deterministic value selection, not a calibrated ML ranker.

## Customer
Odylith maintainers and operators who need Radar, Casebook, Registry, Atlas, and release truth to agree before runtime claims change.

## Opportunity
Bind the program, release, Casebook recurrence, and technical plan so the implementation has one governed execution spine.

## Proposed Solution
Create the workstream for Visible Intervention Value Engine Governance Binding and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Visible Intervention Value Engine Governance Binding.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
B-096 is an execution-wave umbrella; v0.1.11 release assignment includes the work; CB-122 and the calibration-overclaim bug point at the forward fix; backlog validation passes.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should protect trust by making the visible intervention value engine explicit in governance before code and surface claims drift.

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
