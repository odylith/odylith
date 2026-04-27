Status: Done

Created: 2026-04-08

Updated: 2026-04-08

Backlog: B-066

Goal: Show completed workstreams for the active current release in Compass
until explicit GA closeout, while keeping active release targeting distinct
from completed release history.

Assumptions:
- Finished work removed during release closeout still belongs in the release
  readout as completed release history.
- Queued or carried-forward items removed from the release should not be shown
  as completed members.
- The release read model is the right place to project completed-member ids
  rather than teaching Compass to infer them from prose alone.

Constraints:
- Do not re-add finished workstreams to active release targeting.
- Keep the manual `shipped` or `closed` closeout rule from `B-065`.
- Preserve compatibility with already-generated Compass runtime payloads until
  the next runtime refresh rewrites the explicit completed-member fields.

Reversibility: The completed-member projection is additive and can be removed
from the release read model and Compass renderer without changing release
source schema or assignment history.

Boundary Conditions:
- Scope includes release read-model shaping, Compass release rendering, focused
  tests, and the related governance guidance updates.
- Scope excludes non-finished carry-forward membership and shipped-release
  archive redesign.

Related Bugs:
- no related bug found

## Learnings
- [x] Showing the active release without its completed members still leaves the
      closeout story incomplete.
- [x] Completed-in-release history needs a distinct read-model lane from active
      release targeting or the UI will blur execution truth.

## Must-Ship
- [x] Project completed-member ids for finished workstreams whose latest
      release event is removal from that release.
- [x] Render `Completed Workstreams` in Compass for active releases when that
      history exists.
- [x] Keep queued carry-forward work like removed follow-ons out of the
      completed section.
- [x] Update the release and Compass specs plus release-facing guidance and
      skills to describe the split.

## Should-Ship
- [x] Keep a compatibility fallback in Compass for already-generated runtime
      payloads that only expose release-history summaries.
- [x] Cover the release-model and Compass shell contract with focused tests.

## Defer
- [x] Shipped-release archive redesign.
- [x] Broader release analytics beyond targeted versus completed membership.

## Success Criteria
- [x] Active current releases with finished removed members show those members
      in Compass.
- [x] Completed work is visible without becoming active targeting again.
- [x] The governed release contract now distinguishes targeted and completed
      release membership explicitly.

## Non-Goals
- [x] Reclassifying queued follow-on work as completed.
- [x] Weakening the one-active-release-per-workstream contract.

## Open Questions
- [x] No B-066-scoped open question remains.

## Impacted Areas
- [x] [2026-04-08-completed-release-members-stay-visible-until-explicit-ga.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-completed-release-members-stay-visible-until-explicit-ga.md)
- [x] [2026-04-08-completed-release-members-stay-visible-until-explicit-ga.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-08-completed-release-members-stay-visible-until-explicit-ga.md)
- [x] [AGENTS.md](/Users/freedom/code/odylith/odylith/radar/source/releases/AGENTS.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [DELIVERY_AND_GOVERNANCE_SURFACES.md](/Users/freedom/code/odylith/odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md)
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-release-planning/SKILL.md)
- [x] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/odylith-delivery-governance-surface-ops/SKILL.md)
- [x] [release_planning_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/release_planning_contract.py)
- [x] [release_planning_view_model.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/release_planning_view_model.py)
- [x] [compass-releases.v1.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js)
- [x] [test_release_planning.py](/Users/freedom/code/odylith/tests/unit/runtime/test_release_planning.py)
- [x] [test_compass_dashboard_shell.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_dashboard_shell.py)
- [x] [test_render_compass_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_compass_dashboard.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_compass_dashboard.py`
      (passed)
- [x] `git diff --check`
      (passed)

## Current Outcome
- [x] Compass now shows finished work completed in the current active release
      without pretending those items are still active targets.
- [x] Non-finished removed workstreams remain out of the completed section.
- [x] The release read model and guidance now distinguish targeted work from
      completed release history.
