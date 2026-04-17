status: implementation

idea_id: B-107

title: Host Visibility Integration And Ruler Canonicalization

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 5

impacted_parts: Codex host surfaces, Claude host surfaces, visibility_broker, host_surface_runtime, conversation_surface

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Visible delivery and formatting are the product contract the user is explicitly judging.

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
Codex and Claude can generate intervention payloads that remain hidden, and live blocks can lose their top or bottom Markdown ruler while Assist must remain closeout-owned.

## Customer
Users in live chats who need Odylith Observation, Proposal, Risks, History, and Insight to be visibly readable and consistently formatted.

## Opportunity
Make the visibility broker consume selected value-engine options, prove chat visibility, repair missing live rulers, and keep Assist outside ruled live blocks.

## Proposed Solution
Create the workstream for Host Visibility Integration And Ruler Canonicalization and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Host Visibility Integration And Ruler Canonicalization.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Codex and Claude consume the same selected options; hidden systemMessage/additionalContext never count as proof; Stop recovery replays unseen live blocks before Assist; ruled block tests pass.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should never claim success from hidden hook JSON; earned live blocks render visibly with canonical rulers while Assist stays at the final closeout.

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
