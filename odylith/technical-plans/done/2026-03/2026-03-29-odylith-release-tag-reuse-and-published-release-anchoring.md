Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-026

Goal: Make Odylith's canonical release lane reuse unpublished release tags and
anchor automatic patch progression on published GitHub releases instead of raw
tag count.

Assumptions:
- The truthful GA history is the published GitHub release history, not every
  raw semver tag present in the repo.
- Reusing or rebinding an unpublished tag is safer than consuming another patch
  version.
- The maintainer state surface must show both published and raw-tag truth so
  drift is visible.

Constraints:
- Do not move any tag that already has a published GitHub release.
- Keep the canonical next version monotonic against published releases.
- Restore product source version truth to the truthful next GA candidate.

Reversibility: Reverting this slice restores the previous tag-burning behavior
and misleading release-version state output.

Boundary Conditions:
- Scope included release semver resolution, release-session retry behavior,
  release-version state output, source version truth, release docs/specs, and
  focused validation.
- Scope excluded remote cleanup of stale unpublished tags and broader release
  policy redesign.

Related Bugs:
- [2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-release-auto-tagging-burns-unpublished-patch-versions-and-skips-ga-candidates.md)

## Context/Problem Statement
- [x] Auto-version progression was using the highest raw semver tag, not the
  highest published release.
- [x] Retrying a failed unpublished release attempt could skip to the next patch
  version instead of reusing the same candidate.
- [x] Maintainer release-version state did not expose published-vs-tag drift.
- [x] Repo source version truth had been pushed ahead of the actual published
  release history.

## Success Criteria
- [x] Automatic next-version resolution is anchored on the highest published
  canonical release.
- [x] An existing unpublished chosen tag is reused instead of burning the next
  patch version.
- [x] An unpublished chosen tag on an older retry commit can be safely rebound
  to the current `HEAD`.
- [x] Maintainer state output shows both highest published release and highest
  raw semver tag.
- [x] Product version truth is restored to the truthful next GA candidate,
  `0.1.3`.

## Non-Goals
- [x] Cleaning up all stale remote unpublished tags.
- [x] Changing dispatch or GitHub workflow publication policy.
- [x] Reworking release notes or consumer upgrade behavior.

## Impacted Areas
- [x] release semver resolution helpers
- [x] release session state helpers
- [x] maintainer release-version preview/show contract
- [x] [test_release_version_session.py](/Users/freedom/code/odylith/tests/unit/install/test_release_version_session.py)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [pyproject.toml](/Users/freedom/code/odylith/pyproject.toml)
- [x] [__init__.py](/Users/freedom/code/odylith/src/odylith/__init__.py)
- [x] [product-version.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/product-version.v1.json)

## Risks & Mitigations

- [x] Risk: publication-state lookup could fail and make the lane unsafe.
  - [x] Mitigation: fail closed when publication state cannot be resolved for a
    conflicting existing tag.
- [x] Risk: tag rebinding could accidentally move a published release tag.
  - [x] Mitigation: only rebind when GitHub release lookup proves the tag is
    unpublished; published tags still fail closed.
- [x] Risk: maintainers still misread raw tags as canonical history.
  - [x] Mitigation: surface both highest published release and highest raw tag
    explicitly in the maintainer state output and docs.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_release_version_session.py`
- [x] `make release-session-clear`
- [x] `make release-version-show`
- [x] `make release-version-preview`
- [x] `odylith sync --repo-root . --force --impact-mode full`
- [x] `git diff --check`

## Rollout/Communication
- [x] Update the release component spec and maintainer runbook so the contract
  is explicit: unpublished tags are reusable reservations until a real release
  exists.
- [x] Restore source version truth before the next canonical GA attempt so the
  repo and maintainer surface stop implying `0.1.5` is real.

## Current Outcome
- Auto patch resolution now anchors on the highest published GitHub release,
  not the highest raw tag.
- The release session reuses or rebinds the same unpublished tag across retries
  instead of consuming a fresh patch version.
- Maintainers can now see published-vs-tag drift directly in the release-state
  view.
- Odylith is back on the truthful next GA candidate: `v0.1.3`.
