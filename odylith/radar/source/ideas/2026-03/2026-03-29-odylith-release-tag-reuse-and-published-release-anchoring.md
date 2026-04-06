---
status: finished
idea_id: B-026
title: Odylith Release Tag Reuse and Published Release Anchoring
date: 2026-03-29
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: canonical release versioning, maintainer release session truth, release runbook/spec accuracy, and published-vs-tag release integrity
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith cannot claim a trustworthy canonical GA lane if failed release attempts silently burn unpublished patch versions and push repo truth ahead of the actual published release history.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-release-tag-reuse-and-published-release-anchoring.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-005
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
---

## Problem
Odylith's release lane treated raw semver tags as canonical release truth. If a
maintainer reserved `v0.1.3` during preflight but never completed a GitHub
release, the next retry advanced to `v0.1.4` or `v0.1.5` instead of reusing the
same unpublished candidate. That made the repo look ahead of the real GA
history.

## Customer
- Primary: Odylith maintainers cutting canonical GA releases.
- Secondary: consumer repos and operators relying on truthful release/version
  guidance.

## Opportunity
If Odylith anchors auto-version progression on the highest published release and
reuses unpublished reserved tags across retries, then release numbering stays
truthful, recoverable, and easy to reason about.

## Proposed Solution
Make published GitHub releases the canonical auto-version anchor, not raw tags.
When the chosen tag already exists without a published release, reuse that tag
instead of burning the next patch version; if it points at an older retry
commit, rebind the unpublished reservation to the current release commit. Make
the maintainer state view show both published-release and raw-tag reality.

## Scope
- anchor auto patch progression on highest published canonical release
- reuse or rebind existing unpublished release tags instead of skipping them
- restore product source version truth to the truthful next GA candidate
- make maintainer release-version output expose published-vs-tag drift
- update release runbook/spec language and add regression tests

## Non-Goals
- deleting historical reserved tags from the remote
- changing the signed publication workflow itself
- broad release-policy redesign beyond version/session correctness

## Risks
- GitHub release discovery could fail and leave the lane unable to distinguish
  published from unpublished state
- forced unpublished-tag rebinding could be unsafe if applied to a tag that was
  already published
- maintainers could still misread raw tags as canonical history if the surface
  output stays vague

## Dependencies
- `B-005` introduced the canonical release session and maintainer runbook.

## Success Metrics
- `make release-version-show` reports the highest published release separately
  from the highest raw semver tag
- automatic next-version resolution returns `v0.1.3` while GitHub latest stays
  on `v0.1.2`, even if raw tags already include `v0.1.4` and `v0.1.5`
- retrying a failed unpublished release candidate reuses the same tag instead
  of consuming the next patch version
- release source truth stays aligned with the truthful next GA version

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/install/test_release_version_session.py`
- `make release-session-clear`
- `make release-version-show`
- `make release-version-preview`
- `odylith sync --repo-root . --force --impact-mode full`
- `git diff --check`

## Outcome
- Odylith now treats the highest published GitHub release as the auto-version
  anchor
- unpublished release tags are reusable reservations rather than consumed GA
  history
- maintainer release-version state now shows both published and raw-tag truth
- the repo source version floor is back on the truthful next GA candidate,
  `0.1.3`

## Rollout
Ship as release-session hardening. No consumer migration is required; the
behavior change is in maintainer release resolution and truth presentation.

## Why Now
Odylith was about to normalize an incorrect GA history. If a failed release
attempt can silently consume `v0.1.3`, the next real release numbering is no
longer trustworthy.

## Product View
If a release never completed, it did not earn a new version. The same tag
should stay live until the release is real.

## Impacted Components
- `release`

## Interface Changes
- `make release-version-show` now reports highest published release, highest raw
  semver tag, and which anchor drives the next automatic version
- auto preflight reuse is now sticky on an unpublished chosen tag

## Migration/Compatibility
- no consumer migration required
- published tags remain immutable
- unpublished reserved tags may be rebound to the current retry commit before
  dispatch

## Test Strategy
- prove retry reuse of the same unpublished tag
- prove safe rebinding of an unpublished tag to a fixed retry commit
- prove the maintainer state view prefers published-release anchoring over
  higher unpublished tags

## Open Questions
- should Odylith later add a maintainer cleanup helper for stale unpublished
  tags that are provably superseded and still lack a GitHub release
