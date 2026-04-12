Status: Done

Created: 2026-04-08

Updated: 2026-04-08

Backlog: B-065

Goal: Keep the current active release visible in Compass until maintainers
explicitly ship or close it to GA, then align release-planning guidance,
runbooks, and skills around that manual-close contract.

Assumptions:
- Release lifecycle state, not member count, is the correct source of truth for
  whether a current release should remain visible.
- A current active release may truthfully have zero targeted workstreams for a
  period before manual GA closeout.
- Empty-state visibility is sufficient for v1; rehydrating removed workstreams
  into the release just for display would be misleading.

Constraints:
- Do not change the one-active-release-per-workstream contract from `B-063`.
- Do not treat zero targeted workstreams as an implicit `shipped` or `closed`
  transition anywhere in Compass or maintained guidance.
- Keep the rule expressed in owned governance docs and skills, not only in the
  frontend renderer.

Reversibility: If this contract proves wrong, Compass can revert to
member-count-driven filtering and the guidance can be narrowed without changing
release source schema or assignment history.

Boundary Conditions:
- Scope includes Compass release-target rendering, release and Compass specs,
  maintainer release guidance, release-planning guidance, and focused tests.
- Scope excludes release-history archive redesign and any change to release
  assignment semantics.

Related Bugs:
- no related bug found

## Learnings
- [x] Active release visibility has to be lifecycle-driven or the UI will guess
      at release closure before maintainers actually make that decision.
- [x] Empty-state release visibility is more truthful than silently hiding an
      active release with zero targeted workstreams.

## Must-Ship
- [x] Keep the current active release visible in Compass until explicit
      `shipped` or `closed` lifecycle update.
- [x] Render an explicit `No targeted workstreams.` empty state for active
      current releases with zero members.
- [x] Update the release and Compass component specs to describe manual-close
      visibility.
- [x] Update maintainer release guidance plus the release-facing skills so GA
      closure stays explicit.

## Should-Ship
- [x] Bind the change to its own follow-on workstream instead of mutating
      completed `B-063` history in place.
- [x] Add focused test coverage so the frontend contract does not drift back to
      member-count inference.

## Defer
- [x] Separate shipped-release archive views.
- [x] Any change to release membership history semantics.

## Success Criteria
- [x] Compass still shows the current active release when it has zero targeted
      workstreams.
- [x] Maintainers and agents are told to close the current release through
      explicit `shipped` or `closed` lifecycle updates, not by expecting the UI
      to hide it.
- [x] The release-planning contract stays aligned across source policy, specs,
      runbook, and skills.

## Non-Goals
- [x] Restoring removed workstreams just to populate the active release card.
- [x] Replacing execution-wave program semantics with release visibility.

## Open Questions
- [x] No B-065-scoped open question remains.

## Impacted Areas
- [x] [2026-04-08-current-active-release-visibility-until-explicit-ga.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-current-active-release-visibility-until-explicit-ga.md)
- [x] [2026-04-08-current-active-release-visibility-until-explicit-ga.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-08-current-active-release-visibility-until-explicit-ga.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/radar/source/releases/AGENTS.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [DELIVERY_AND_GOVERNANCE_SURFACES.md](/Users/freedom/code/odylith/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md)
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-release-planning/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [compass-releases.v1.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js)
- [x] [test_compass_dashboard_shell.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_dashboard_shell.py)
- [x] [test_render_compass_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_compass_dashboard.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_compass_dashboard.py`
      (passed)
- [x] `git diff --check`
      (passed)

## Current Outcome
- [x] Compass keeps the current active release visible until maintainers
      explicitly mark it `shipped` or `closed`.
- [x] Active current releases with zero targeted workstreams now render an
      explicit empty state instead of disappearing.
- [x] Release-planning governance, maintainer guidance, and agent skills all
      now describe release closeout as a manual GA transition.
