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
Bind B-096 to the v0.1.11 execution-wave program, release assignment,
technical plan, CB-122 visible-chat recurrence, CB-123 calibration-overclaim
risk, Registry component specs, Atlas D-038/D-002 topology, and Compass
execution log. Governance must say the runtime is proposition-first
`deterministic_utility_v1`, not ML-calibrated signal ranking.

## Scope
- Keep B-096 as the umbrella and B-105 through B-109 as child waves.
- Update source truth first, then regenerate Radar, Registry, Atlas, Casebook,
  Compass, and bundle mirrors through governed refresh/sync.
- Ensure the active plan, workstreams, Casebook, Registry, Atlas, and release
  assignment all name the same v0.1.11 contract.
- Carry Guidance Behavior Enhancements into the same governance spine when
  they feed the visible intervention evidence cone.
- Treat Guidance Behavior host/lane instructions as governed surface truth:
  Codex, Claude, installed command/skill shims, consumer pinned-runtime,
  pinned dogfood, and source-local maintainer mode must converge on the same
  CLI-first validator and quick benchmark proof path.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- Source records can drift into implementation-scaffold prose while generated
  dashboards look current. This wave is not complete until the source records
  are grounded and the generated surfaces are refreshed from them.

## Dependencies
- B-096 active technical plan.
- Existing release assignment for `release-0-1-11`.
- CB-122 and CB-123 as the trust and provenance bug anchors.

## Success Metrics
B-096 is an execution-wave umbrella; v0.1.11 release assignment includes the work; CB-122 and the calibration-overclaim bug point at the forward fix; Guidance Behavior host/lane proof is governed under the same plan; backlog validation passes.

## Validation
- Backlog, plan-traceability, Casebook, Registry, Atlas, Compass, and sync
  validation pass after the source updates.
- `git diff --check` passes after generated surface refresh.

## Rollout
- Keep this wave active until source truth and rendered governance surfaces
  agree on B-096, child workstreams, v0.1.11 release binding, and the
  deterministic value-engine posture.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should protect trust by making the visible intervention value engine explicit in governance before code and surface claims drift.

## Impacted Components
- `governance-intervention-engine`
- `compass`
- `radar`
- `casebook`
- `registry`
- `atlas`

## Interface Changes
- No runtime API is owned by this wave; it owns the governance binding for the
  v0.1.11 runtime API and proof posture.

## Migration/Compatibility
- Backward compatibility is intentionally cut for the old block-first
  signal-ranker narrative. Governance describes the v0.1.11 forward contract
  plus the v0.1.10-to-v0.1.11 migration lane.

## Test Strategy
- Treat governance validation as source-truth proof: the source records must
  validate before rendered dashboards or bundle mirrors are trusted.

## Open Questions
- No open governance-binding question remains for v0.1.11; remaining risk is
  release proof freshness.
