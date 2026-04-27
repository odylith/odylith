---
status: finished
idea_id: B-065
title: Current Active Release Visibility Until Explicit GA
date: 2026-04-08
priority: P1
commercial_value: 3
product_impact: 4
market_value: 3
impacted_parts: Compass release-target rendering, release-planning visibility contract, maintainer GA closeout guidance, and release-planning agent skills
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Release planning just landed, but the current release could disappear from Compass before the maintainer actually shipped it to GA. That turns active planning truth into a UI guess at exactly the moment release state needs to stay explicit, so the visibility contract needs a bounded follow-on fix immediately.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-08-current-active-release-visibility-until-explicit-ga.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-063
workstream_blocks:
related_diagram_ids:
workstream_reopens: B-063
workstream_reopened_by: B-066
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Compass could hide the `Release Targets` section for the current release as
soon as targeted workstreams dropped to zero, even if maintainers had not yet
explicitly shipped or closed that release. That made active release truth feel
derived from member count instead of the actual release lifecycle.

## Customer
- Primary: maintainers using Compass to track what release is still live before
  manual GA closeout.
- Secondary: agent workflows and operators who need the release-planning
  contract to stay explicit instead of inferring closure from empty membership.

## Opportunity
If the current active release remains visible until maintainers explicitly mark
it `shipped` or `closed`, Compass, guidance, and agent behavior all stay
aligned around one truthful release-closeout contract.

## Proposed Solution
Keep the current active release rendered in Compass even when it has zero
targeted workstreams, show an explicit empty state instead of removing the
section, and update the release-planning specs, runbook, and skills so GA
closure stays manual and lifecycle-driven.

## Scope
- Keep the current active release visible in Compass until explicit
  `shipped`/`closed` lifecycle transition.
- Render a minimal empty state when the active current release has zero
  targeted workstreams.
- Update release-planning governance docs, maintainer guidance, and skills to
  describe manual-close behavior.

## Non-Goals
- Reassigning finished workstreams back into an active release just to keep the
  section non-empty.
- Changing the one-active-release-per-workstream rule from `B-063`.
- Conflating release visibility with execution-wave program membership.

## Risks
- If the rule is documented only in UI code, future closeout work may regress
  back to member-count inference.
- If empty active releases are treated as implicitly terminal, maintainers can
  lose sight of the live lane before GA proof actually runs.

## Dependencies
- `B-063` introduced the release-planning contract that this slice tightens.
- no related bug found

## Success Metrics
- Compass continues showing the current active release until maintainers
  explicitly mark it `shipped` or `closed`.
- Empty active releases render an explicit empty state instead of disappearing.
- Release-planning guidance and skills describe GA closeout as an explicit
  lifecycle transition, not an inferred UI side effect.

## Validation
- Focused Compass shell and render tests for release-target visibility.
- Focused release-planning contract and guidance updates reviewed in the same
  change.
- `git diff --check`

## Rollout
Land the Compass visibility fix and the owned guidance updates in one slice so
the current behavior and the maintained contract agree immediately.

## Why Now
Release planning already made active release state a first-class concept. Letting
the current release vanish before explicit GA closeout undercuts that new truth
at the exact point where operators need it most.

## Product View
An active current release should disappear only when maintainers actually ship
or close it, not because a temporary member count hits zero.

## Impacted Components
- `compass`
- `release`

## Interface Changes
- Compass keeps `Release Targets` visible for the active current release until
  explicit `shipped` or `closed` lifecycle change.
- Empty active releases now show `No targeted workstreams.` instead of hiding
  the section.

## Migration/Compatibility
- Existing release source truth needs no schema migration; this is a visibility
  and guidance correction on top of the existing release contract.
- Active current releases with zero targeted workstreams now remain visible
  until manual GA closeout.

## Test Strategy
- Lock the Compass release renderer contract with focused shell assertions.
- Keep a render-level proof that the release shell still emits the updated
  release-target bundle.

## Open Questions
- Whether Compass should eventually surface a separate shipped-release archive
  panel after manual GA closeout, rather than only current and next planning
  views.
