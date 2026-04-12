status: implementation

idea_id: B-089

title: Claude Host Capability Layer Cli Backed Baked Hooks And Compatibility Surface

date: 2026-04-11

priority: P1

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: claude_host_runtime,runtime_common,runtime_surfaces,install_manager,claude_project_assets,slash_commands,agents_guidelines,tests

sizing: L

complexity: Medium

ordering_score: 100

ordering_rationale: Mirror the Codex capability+CLI-backed-hook parity (B-087, B-088) into the Claude lane so both first-class delegation hosts share the same dynamically introspected, CLI-backed posture, satisfying the operator directive to fully optimize Odylith to Claude when the host is detected as Claude.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-claude-host-capability-layer-cli-backed-baked-hooks-and-compatibility-surface.md

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
Odylith needs an explicit workstream for Claude Host Capability Layer Cli Backed Baked Hooks And Compatibility Surface instead of leaving the slice implicit.

## Customer
Odylith maintainers and operators who need this capability to exist as governed product truth.

## Opportunity
Bound Claude Host Capability Layer Cli Backed Baked Hooks And Compatibility Surface as a queued workstream so implementation can attach to one clear source record.

## Proposed Solution
Create the workstream for Claude Host Capability Layer Cli Backed Baked Hooks And Compatibility Surface and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Claude Host Capability Layer Cli Backed Baked Hooks And Compatibility Surface.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
- The workstream is specific enough to guide implementation and validation without further backlog surgery.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
If the team is already acting as if this work exists, the backlog should say so explicitly.

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
