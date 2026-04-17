status: implementation

idea_id: B-109

title: v0.1.11 Visible Intervention Release Proof

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: release proof, validation, Compass, Atlas, Registry, Casebook, Radar

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Release proof is required because the feature is a brand-visible trust surface.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on: B-107,B-108

workstream_blocks:

related_diagram_ids: D-038,D-002

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
The visible intervention value engine must ship with proof that runtime behavior, migration, governance truth, host parity, and generated surfaces agree before v0.1.11 closes.

## Customer
Odylith maintainers and downstream users who need the released intervention UX to be trustworthy on first use.

## Opportunity
Tie focused tests, migration checks, Atlas renders, Registry validation, Casebook/Radar validation, and Compass status into one release-proof wave.

## Proposed Solution
Create the workstream for v0.1.11 Visible Intervention Release Proof and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.11 Visible Intervention Release Proof.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Focused runtime, host-visible, install migration, corpus, benchmark report, Registry, Casebook, Radar, Atlas, py_compile, sync, and git diff checks pass with any skipped coverage explicitly named.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should leave v0.1.11 with visible intervention value as proven mechanism evidence, not a half-integrated runtime experiment.

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
