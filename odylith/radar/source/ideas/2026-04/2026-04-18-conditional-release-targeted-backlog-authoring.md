status: implementation

idea_id: B-126

title: Conditional Release-Targeted Backlog Authoring

date: 2026-04-18

priority: P1

commercial_value: 4

product_impact: 4

market_value: 3

impacted_parts: radar,release,compass,cli,governance

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Queued as a narrow v0.1.12 governance-authoring ergonomics slice attached to Governed Harness/release-prep; do not disturb the v0.1.11 release lane.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-18-conditional-release-targeted-backlog-authoring.md

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
Backlog authors can create queued workstreams and release planners can assign workstreams to a release, but today those are separate commands. That split creates avoidable friction and partial-write risk when a maintainer wants a new queued backlog record to be targeted at next or at an explicit release such as release-0-1-12 while preserving the workstream status as queued.

## Customer
Odylith maintainers planning v0.1.12 and later releases, plus Codex and Claude governance-authoring lanes that need the same CLI-first contract for backlog creation, release targeting, Radar visibility, and Compass visibility.

## Opportunity
Add an optional release selector to backlog creation so odylith backlog create without --release remains queue-only, while odylith backlog create --release next or --release release-0-1-12 validates the release target first, creates the queued records, assigns all newly created IDs to the selected release, and reports the refresh state in one explicit summary.

## Proposed Solution
Create the workstream for Conditional Release-Targeted Backlog Authoring and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for Conditional Release-Targeted Backlog Authoring.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Focused tests prove backlog create without --release does not touch release assignments; backlog create --release next creates release events for every created ID; queued release-targeted workstreams appear in release show next; Radar and Compass refresh is triggered or clearly queued after release targeting; invalid release selectors fail before any partial write; existing queue-only behavior remains unchanged for Codex, Claude, dev, dogfood, and consumer lanes.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
The backlog create command should gain a conditional release-targeting path: no --release means no release assignment writes; with --release it validates the selector before any write, creates queued records, appends release assignment events for every new ID, preserves status: queued, refreshes or queues Radar and Compass visibility, and prints created IDs, release target or none, queued status preserved, Radar refresh result, and Compass refresh result or status. Invalid release selectors must fail before backlog files or release event logs are mutated.

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
