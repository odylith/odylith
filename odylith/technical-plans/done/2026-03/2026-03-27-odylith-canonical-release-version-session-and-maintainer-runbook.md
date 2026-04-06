Status: Done

Created: 2026-03-27

Updated: 2026-03-28

Backlog: B-005

Goal: Make Odylith's canonical release lane deterministic and repeatable by adding a sticky release-version session, safe next-patch auto-tagging, thin maintainer Make/bin orchestration, and one concise maintainer runbook that explains the exact order of operations.

Assumptions:
- Odylith canonical releases remain restricted to `odylith/odylith` on `main` as GitHub actor `freedom-research`.
- Maintainer release automation should stay thin and should not become a second product contract.
- The canonical release lane needs deterministic version reuse across retries before the first public release is cut.

Constraints:
- Do not weaken the existing canonical release authority guard.
- Keep the user-facing product contract on the `odylith` CLI; maintainer release wrappers live under `bin/` and `Makefile`.
- Keep the release-version session under `.odylith/` as mutable local maintainer state, not tracked repo truth.

Reversibility: The release-version session is local state under `.odylith/locks/`, the semver helper scripts are additive, and the Make/bin interface remains a thin orchestration layer over existing release controls.

Boundary Conditions:
- Scope includes canonical semver tag discovery, sticky release-session reuse, maintainer release targets, release runbook documentation, Registry/Atlas artifacts for the release lane, and the related B-005 governance updates.
- Scope excludes the actual first public release dispatch result, dogfood activation onto a published runtime, and downstream consumer rehearsal evidence from live hosted assets.

## Context/Problem Statement
- [x] Odylith already has signed release asset generation, release authority guards, and a maintainer `Makefile`, but the maintainer lane still depends on manually repeating a tag across steps.
- [x] A failed or partial release attempt can currently force maintainers to remember or re-enter the intended version manually.
- [x] Prior release-lane work already proved the value of sticky version-session reuse, next-version preview, and monotonic semver checks for release retry safety.
- [x] Odylith still needs its own slimmer version of that flow, plus explicit Registry/Atlas artifacts and a maintainers-only runbook.

## Success Criteria
- [x] Odylith has one sticky release-session file under `.odylith/locks/` that preflight and dispatch can both reuse.
- [x] Maintainers can preview the next auto version and inspect current session/highest-tag state before mutating anything.
- [x] `make release-preflight` can initialize or reuse the release session, with optional explicit `VERSION=X.Y.Z`.
- [x] `make release-dispatch` uses the active session version instead of requiring a repeated tag argument.
- [x] Session resolution enforces monotonic stable semver progression against the highest existing `vX.Y.Z` tag in the canonical repo.
- [x] Registry tracks a first-class `release` component and Atlas includes a dedicated release-session / canonical publish-lane diagram.
- [x] Odylith has a crisp maintainer runbook that lists the exact release order and the final set of Make targets.

## Non-Goals
- [ ] Publishing the first public release itself in this plan.
- [ ] Automatically cutting a GitHub release from ordinary development commands.
- [ ] Recreating a multi-environment platform release stack inside Odylith.

## Impacted Areas
- [x] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [odylith/technical-plans/INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [odylith/registry/source/component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [odylith/registry/source/components/release/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [odylith/atlas/source/catalog/diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [odylith/MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)

## Traceability
### Runbooks
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)

### Developer Docs
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)

### Atlas
- [x] [odylith-canonical-release-version-session-and-publish-lane.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-canonical-release-version-session-and-publish-lane.mmd)

### Code References
- [x] [Makefile](/Users/freedom/code/odylith/Makefile)
- [x] [bin/_odylith.sh](/Users/freedom/code/odylith/bin/_odylith.sh)
- [x] [bin/release-version-preview](/Users/freedom/code/odylith/bin/release-version-preview)
- [x] [bin/release-version-show](/Users/freedom/code/odylith/bin/release-version-show)
- [x] [bin/release-session-show](/Users/freedom/code/odylith/bin/release-session-show)
- [x] [bin/release-session-clear](/Users/freedom/code/odylith/bin/release-session-clear)
- [x] [release-preflight](/Users/freedom/code/odylith/bin/release-preflight)
- [x] [release-dispatch](/Users/freedom/code/odylith/bin/release-dispatch)
- [x] [validate_self_host_posture.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_self_host_posture.py)
- [x] [release.yml](/Users/freedom/code/odylith/.github/workflows/release.yml)

## Risks & Mitigations

- [x] Risk: maintainers can still drift across versions if preflight and dispatch compute their own version separately.
  - [x] Mitigation: make both targets reuse the same local release session file.
- [x] Risk: auto-tagging can create a surprising version if maintainers do not inspect the next patch before starting release work.
  - [x] Mitigation: add explicit `release-version-preview` and `release-version-show` targets and document them first in the runbook.
- [x] Risk: forks or clones can reuse the release-session scripts in a way that looks canonical.
  - [x] Mitigation: keep canonical release authority checks in preflight, dispatch, workflow, and signed provenance validation.
- [x] Risk: Odylith copies too much prior release-lane complexity.
  - [x] Mitigation: keep the Odylith lane to one canonical semver stream, one session file, and a small set of maintainer targets only.

## Validation/Test Plan
- [x] `pytest -q tests/unit/install/test_release_version_session.py tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py tests/unit/runtime/test_validate_self_host_posture.py`
- [x] `pytest -q tests/unit/test_cli.py tests/integration/install/test_manager.py tests/integration/install/test_lifecycle_simulator.py`
- [x] `make release-version-preview`
- [x] `make release-version-show`
- [x] `make release-preflight VERSION=0.1.0`

## Rollout/Communication
- [x] Land the local version-session/autotag helpers before attempting the first hosted public release.
- [x] Document the exact maintainer order in one concise runbook.
- [x] Keep the session file local and resettable so failed attempts stay deterministic but recoverable.

## Outcome
- [x] The canonical release session, autotagging, maintainer Make/bin wrappers,
  and release runbook all landed and were exercised during the abandoned
  prelaunch `v0.1.0` drill.
- [x] The local source tree has since been reset to restart the canonical
  preview line from `v0.1.0` rather than treating the abandoned drill as
  published public history.
- [x] The product repo returned to the pinned dog-food lane after the prelaunch
  drill.
- [x] The first real consumer rehearsal exposed a separate installer/runtime
  defect: first install still depended on consumer-machine Python instead of an
  Odylith-managed runtime. That defect is tracked separately as an open bug and
  the active follow-on plan remains under `B-005`.

## Dependencies/Preconditions
- [x] Keep workstream `B-005` active in `odylith/radar/source/INDEX.md`.
- [x] Keep canonical release authority restricted to `odylith/odylith` on `main` as actor `freedom-research`.
- [x] No related bug found.

## Edge Cases
- [x] Existing active release session plus a different explicit version request: fail closed.
- [x] No active session and dispatch target runs directly: fail closed and require preflight first.
- [x] Auto-tag race where a concurrent maintainer creates the same next tag first: retry safely.
- [x] Explicit version below highest existing stable semver tag: fail closed.
- [x] Maintainer wants to abandon a failed or stale session intentionally: provide a clear session-clear target.

## Open Questions/Decisions
- [x] Decision: Odylith keeps one global stable semver line (`vX.Y.Z`) for the canonical release lane.
- [x] Decision: `make release-preflight` is the release-session initializer; `make release-dispatch` only reuses an existing session.
- [x] Decision: maintainer release orchestration stays in `bin/` and `Makefile`, not in the public `odylith` CLI contract.
