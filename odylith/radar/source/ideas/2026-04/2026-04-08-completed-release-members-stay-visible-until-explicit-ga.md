---
status: finished
idea_id: B-066
title: Completed Release Members Stay Visible Until Explicit GA
date: 2026-04-08
priority: P1
commercial_value: 3
product_impact: 4
market_value: 3
impacted_parts: Compass release-target rendering, Compass execution-wave progress chips, Radar backlog execution-wave summaries, release-planning read models, release closeout guidance, and release-planning skills
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Keeping the active current release visible fixed the disappearing-lane problem, but the view still looked empty because closeout removed finished workstreams from active targeting. The release surface now needs to show what actually completed in that release without lying about active membership.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-09-completed-release-members-source-truth-reconciliation-and-stale-runtime-guardrails.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-063
workstream_blocks:
related_diagram_ids:
workstream_reopens: B-065
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
After closeout removed finished workstreams from active release targeting,
Compass kept the current release visible but rendered it as effectively empty.
That hid the most important context for the lane: what actually shipped or
completed in that release before manual GA closeout.

The regression discovered on 2026-04-09 is sharper: when current source truth
and `odylith/compass/runtime/current.v1.json` drift apart, Compass can keep a
closed workstream in `Targeted Workstreams` with stale `implementation` status
and `0% progress` instead of reconciling the active/completed split against the
live release read model. The same null-to-zero coercion class also leaked into
execution-wave progress chips, so unknown plan progress could silently render
as `0%` in both Compass and Radar backlog execution-wave summaries.

## Customer
- Primary: maintainers reading Compass during release closeout who need to see
  completed release work without reactivating it as current targeting.
- Secondary: agents and operators who need release read models to distinguish
  active membership from completed-in-release history.

## Opportunity
If Compass can show completed workstreams from the active release alongside any
remaining targeted workstreams, refuse to trust stale runtime membership over
fresher release source truth, and keep unknown progress visibly unknown across
release/execution-wave views, release closeout becomes more truthful and much
easier to scan.

## Proposed Solution
Extend the release read model with completed-member ids for finished
workstreams whose latest release event is removal from that release, render
those items in a separate `Completed Workstreams` section under the active
release until explicit `shipped` or `closed` lifecycle transition, and harden
Compass plus shell-facing stale-runtime posture so stale runtime payloads are
reconciled or disclosed instead of reactivating closed members in the visible
release card. Treat missing `progress_ratio` as unknown rather than coercing it
to `0` in release-target and execution-wave readouts.

## Scope
- add completed-member projection to the release read model
- reconcile Compass release-target and current-workstream readouts against live
  release source truth when the runtime snapshot lags
- preserve unknown plan progress in Compass execution-wave chips and Radar
  backlog execution-wave summaries instead of rendering placeholder `0%`
- surface stale-runtime/source-truth mismatch in Compass, shell posture, and
  sync guidance so the stale state cannot look current
- update release and Compass specs, release guidance, and skills so operators
  understand the difference between active targets and completed release work

## Non-Goals
- restoring completed workstreams as active release targets
- showing non-finished removed workstreams like queued carry-forward items in
  the completed section
- changing the manual GA closeout rule from `B-065`

## Risks
- a frontend-only heuristic could misclassify release history if the read model
  does not carry completed-member truth explicitly
- mixing completed and active members into one undifferentiated list would blur
  the difference between release history and current targeting
- stale Compass runtime payloads can silently override correct release source
  truth unless the product has a live reconciliation or explicit stale warning

## Dependencies
- `B-063` established release planning
- `B-065` kept the active current release visible through manual closeout
- [CB-081](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md)

## Success Metrics
- active current releases show completed workstreams from that release instead
  of an empty panel after closeout
- queued or carried-forward non-finished workstreams do not appear in the
  completed section
- stale Compass runtime payloads do not keep closed workstreams in
  `Targeted Workstreams` after release source truth removes them
- Compass and Radar execution-wave views do not turn missing progress into
  synthetic `0%` badges
- release-planning guidance and skills describe active-target and
  completed-in-release membership as distinct read-model concepts

## Validation
- focused release-planning and Compass shell tests
- stale-runtime release-target browser proof
- live-to-bundle surface parity proof for Compass and Radar execution-wave
  assets
- targeted Compass render refresh
- standalone sync write plus check-only proof
- `git diff --check`

## Rollout
Land the release-model projection, Compass rendering, and guidance updates in
one slice so the UI and the maintained contract stay aligned.

## Why Now
The current release is visible again, but the operator still can’t tell what
actually got done in it. That leaves the closeout surface technically present
but not yet useful.

## Product View
Release closeout should show what completed in that release without pretending
that finished work is still an active target.

## Impacted Components
- `compass`
- `radar`
- `release`

## Interface Changes
- release catalog rows now carry completed-member ids for finished work removed
  from that release
- Compass renders a `Completed Workstreams` section for active current releases
  when release history proves finished membership
- Compass and Radar execution-wave views leave progress blank when no explicit
  `progress_ratio` exists instead of rendering synthetic `0%`

## Migration/Compatibility
- release source files do not need schema changes; completed members are a
  derived read-model addition
- Compass keeps a compatibility fallback for older runtime payloads until the
  next refresh writes the explicit completed-member catalog fields

## Test Strategy
- add direct release read-model coverage for completed-member projection
- extend Compass shell and render assertions for the completed-members section
- add regressions for execution-wave progress chips so missing progress stays
  unknown across Compass and Radar

## Open Questions
- whether future release archive views should preserve the same split between
  targeted and completed work once a release becomes `shipped` or `closed`
