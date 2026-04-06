Status: Done

Created: 2026-03-28

Updated: 2026-03-28

Backlog: B-007

Goal: Promote Odylith's already-published `v0.1.0` contract from preview to GA
in source truth for the supported macOS Apple Silicon and Linux platform
matrix, while carrying the latest release-reset hardening onto the GA branch.

Assumptions:
- `v0.1.0` is already published and completed dogfood, consumer rehearsal, and
  `ga-gate` proof.
- Supported GA platforms remain macOS (Apple Silicon) and Linux
  (`x86_64`, `ARM64`).
- Intel macOS and Windows remain intentionally unsupported.

Constraints:
- Do not cut a new release number for this promotion.
- Preserve the existing `odylith` CLI and hosted `install.sh` public contract.
- Keep source truth consistent across product docs, bundle docs, Registry
  specs, backlog, and plans.

Reversibility: Reverting this slice means returning the public docs/specs to
preview wording and removing the GA-specific governance records. No runtime or
release-asset migration is required.

Boundary Conditions:
- Scope includes GA wording, supported-platform contract language, B-005 closeout,
  new B-007 governance records, and carrying the release-reset pin-realignment
  hardening onto the GA branch.
- Scope excludes new platform support, `1.0.0` renumbering, and any broad
  support-organization process.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] `v0.1.0` is published and already passed the full post-release proof lane.
- [x] Source-truth docs/specs still described the current contract as preview.
- [x] The latest release-reset hardening was still only on a side branch.

## Success Criteria
- [x] README/runbook/spec language no longer describes the supported contract as preview.
- [x] `v0.1.0` is described as the GA baseline for supported platforms.
- [x] `B-005` is closed as done.
- [x] The release-reset pin-realignment hardening is included in the GA promotion branch.
- [x] `make validate` passes after the source-truth update.

## Non-Goals
- [x] Shipping Windows or Intel macOS support.
- [x] Cutting a new version solely for the GA stance change.
- [x] Defining a broad support-team/process operating model.

## Impacted Areas
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [2026-03-27-odylith-public-release-dogfood-activation-and-consumer-rehearsal.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-27-odylith-public-release-dogfood-activation-and-consumer-rehearsal.md)
- [x] [2026-03-28-odylith-ga-promotion-and-supported-platform-contract.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-28-odylith-ga-promotion-and-supported-platform-contract.md)
- [x] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [tests/integration/install/test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)

## Traceability
### Runbooks
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)

### Developer Docs
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)

### Code References
- [x] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [tests/integration/install/test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)

## Risks & Mitigations

- [x] Risk: The repo could keep claiming preview and GA at the same time.
  - [x] Mitigation: update README, runbook, Registry specs, backlog, and plan records together in one slice.
- [x] Risk: The GA branch could omit the latest release-reset hardening and leave the published baseline harder to maintain after drift.
  - [x] Mitigation: cherry-pick the pin-realignment hardening into the GA promotion branch before final validation.

## Validation/Test Plan
- [x] `./.odylith/bin/odylith version --repo-root .`
- [x] `make validate`

## Rollout/Communication
- [x] Treat published `v0.1.0` as the GA baseline for supported platforms.
- [x] Keep unsupported platforms explicitly unsupported instead of implying broader availability.

## Dependencies/Preconditions
- [x] `B-005` completed the release reset and proof lane.
- [x] The published `v0.1.0` release and its dogfood/consumer proof already exist.

## Edge Cases
- [x] GA promotion does not imply Windows or Intel macOS support.
- [x] GA promotion does not require a new release artifact when the existing artifact is already published and proved.

## Open Questions/Decisions
- [x] Decision: `v0.1.0` is the GA baseline for the current supported platform matrix.
- [x] Decision: GA is a product/support stance here, not a forced semver jump to `1.0.0`.

## Current Outcome
- Source truth now describes Odylith's supported hosted install/release
  contract as GA for macOS Apple Silicon and Linux.
- The preview-relaunch workstream `B-005` is closed as complete.
- The release-reset pin-realignment hardening is included on the GA branch so
  the published baseline is easier to keep aligned after prelaunch drift.
