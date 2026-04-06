Status: Done

Created: 2026-03-28

Updated: 2026-03-28

Backlog: B-005

Goal: Reset Odylith's release line to restart at `0.1.0`, keep install and
upgrade full-stack by default, split runtime transport into smaller managed
assets so release uploads/downloads and incremental updates stay lighter,
preserve a zero-friction first-install experience, keep the maintainer build
lane Hatch-based, and block canonical dispatch on a local hosted-asset proof
before GitHub release.

Assumptions:
- The abandoned `0.1.x` tags are treated locally as prelaunch rehearsal, not
  as canonical public product history.
- Full Odylith should be installed by default. The asset split exists to make
  transport and reuse lighter, not to ship a weaker default experience.
- Supported platforms for the managed runtime remain macOS (Apple Silicon) and
  Linux only in this slice.
- The managed runtime remains repo-local under `.odylith/`.

Constraints:
- Preserve the `odylith` CLI and hosted `install.sh` as the public operator
  contract.
- Keep canonical release authority restricted to
  `odylith/odylith` on `main`.
- Keep customer-owned `odylith/` truth separate from mutable `.odylith/`
  runtime state.
- Do not reintroduce consumer-machine Python as the install bootstrap for
  supported platforms.

Reversibility: The split packaging model is additive. Reverting it means
returning to a monolithic managed-runtime asset and removing the pack-reuse
logic without rewriting customer-owned repo truth.

Boundary Conditions:
- Scope includes version-floor reset, release-session reset, source-truth
  narrative rewrite, full-stack split asset packaging, runtime/cache retention,
  local hosted-asset preflight proof, and Registry/Casebook/Radar updates.
- Scope excludes Windows support, non-GitHub distribution, and GA policy.

## Context/Problem Statement
- [x] The source tree still carried a `0.1.3` version floor and a sticky local
  release session, which made the relaunch story incoherent.
- [x] The repo narrative still described the abandoned `0.1.x` rehearsal line
  as if it were the canonical public release history.
- [x] Runtime payloads were too large and too sticky for comfortable first
  install and incremental update behavior.
- [x] `make release-preflight` did not yet block on a local hosted-asset proof
  of the generated installer before dispatch.

## Success Criteria
- [x] Product source version and pinned repo version restart at `0.1.0`.
- [x] Sticky local release-session state for the abandoned `0.1.3` attempt is
  cleared.
- [x] README, backlog, active plan, bugs, and Registry source specs stop
  describing the abandoned `0.1.x` rehearsal line as canonical public history.
- [x] Canonical release assets now ship as a smaller base runtime plus a
  separately versioned managed context-engine pack.
- [x] `odylith install` and normal `odylith upgrade` still yield a full-stack
  runtime by default.
- [x] Upgrades may reuse an unchanged context-engine pack when its asset digest
  matches the previous installed pack.
- [x] After install, upgrade, or rollback, Odylith retains only the active
  runtime, one rollback target, and the matching cached release payloads.
- [x] `odylith version` and `odylith doctor` report context-engine mode and
  context-engine pack state.
- [x] The hosted installer remains one-command and non-interactive while still
  detecting platform/release context and selecting the correct managed assets
  automatically.
- [x] The hosted installer can resolve the target repo root from any
  subdirectory inside the repo instead of requiring an exact cwd match.
- [x] The maintainer wheel-build path is explicitly Hatch-based in preflight
  and release publication surfaces.
- [x] Repo CI now runs Odylith tests through the Hatch-managed environment
  instead of direct-pip bootstrap commands.
- [x] Verified release downloads, install-critical metadata writes, and
  same-version runtime restaging now use atomic stage-and-swap behavior,
  including parent-directory sync after file and runtime handoff, instead of
  destructive in-place mutation.
- [x] Fresh consumer install now stays fail-closed until the full stack passes
  activation smoke, and same-version upgrade no longer restages the live
  runtime in place.
- [x] `make release-preflight` now builds local release assets and proves
  `install -> version -> doctor -> sync` against hosted-style local assets.
- [x] `make consumer-rehearsal VERSION=X.Y.Z` proves the relaunched hosted
  contract after dispatch.

## Non-Goals
- [x] GA announcement or support policy remains out of scope for this slice.
- [x] Windows packaging remains out of scope in this slice.
- [x] Non-GitHub distribution channels remain out of scope in this slice.

## Impacted Areas
- [x] [pyproject.toml](/Users/freedom/code/odylith/pyproject.toml)
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [odylith/runtime/source/product-version.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/product-version.v1.json)
- [x] [odylith/INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [x] [odylith/MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)
- [x] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [odylith/casebook/bugs/INDEX.md](/Users/freedom/code/odylith/odylith/casebook/bugs/INDEX.md)
- [x] [odylith/registry/source/components/release/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [odylith/registry/source/components/odylith/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [src/odylith/install/managed_runtime.py](/Users/freedom/code/odylith/src/odylith/install/managed_runtime.py)
- [x] [src/odylith/install/fs.py](/Users/freedom/code/odylith/src/odylith/install/fs.py)
- [x] [src/odylith/install/release_assets.py](/Users/freedom/code/odylith/src/odylith/install/release_assets.py)
- [x] [src/odylith/install/runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [x] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [src/odylith/runtime/common/consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [x] [bin/release-preflight](/Users/freedom/code/odylith/bin/release-preflight)
- [x] [.github/workflows/release.yml](/Users/freedom/code/odylith/.github/workflows/release.yml)
- [x] [.github/workflows/test.yml](/Users/freedom/code/odylith/.github/workflows/test.yml)

## Traceability
### Runbooks
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [x] [MAINTAINER_RELEASE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/MAINTAINER_RELEASE_RUNBOOK.md)

### Developer Docs
- [x] [README.md](/Users/freedom/code/odylith/odylith/README.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/release/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)

### Code References
- [x] [src/odylith/install/managed_runtime.py](/Users/freedom/code/odylith/src/odylith/install/managed_runtime.py)
- [x] [src/odylith/install/release_assets.py](/Users/freedom/code/odylith/src/odylith/install/release_assets.py)
- [x] [src/odylith/install/runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [x] [src/odylith/install/manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [src/odylith/runtime/common/consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [x] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [tests/unit/install/test_release_assets.py](/Users/freedom/code/odylith/tests/unit/install/test_release_assets.py)
- [x] [tests/unit/install/test_runtime.py](/Users/freedom/code/odylith/tests/unit/install/test_runtime.py)
- [x] [tests/unit/test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [tests/integration/install/test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [.github/workflows/test.yml](/Users/freedom/code/odylith/.github/workflows/test.yml)

## Risks & Mitigations

- [x] Risk: split runtime assets could still regress into a broken installer contract.
  - [x] Mitigation: keep `make release-preflight` blocked on a hosted-style local installer proof, and validate that the manifest exposes exactly one Odylith wheel, rejects sidecar wheels, and carries the expected runtime and feature-pack metadata before activation.
- [x] Risk: full-stack upgrades could still redownload large payloads every time.
  - [x] Mitigation: reuse unchanged managed context-engine packs across upgrades, reuse verified cached assets for the same release version, and track feature-pack digest plus installed file list so an unchanged pack can be reused safely.
- [x] Risk: runtime and cache growth could continue even after the packaging split.
  - [x] Mitigation: prune staged runtimes and release caches down to the active version plus one rollback target after each successful lifecycle operation.
- [x] Risk: relaunch documentation could drift back into the old rehearsal narrative.
  - [x] Mitigation: update README, runbooks, component specs, backlog, bugs, and generated governance surfaces together in the same slice, then regenerate derived surfaces from those sources.

## Validation/Test Plan
- [x] `pytest -q tests/unit/install/test_release_assets.py tests/unit/install/test_runtime.py tests/unit/test_cli.py tests/integration/install/test_manager.py`
- [x] `make validate`
- [x] `make release-preflight VERSION=0.1.0`
- [x] `make consumer-rehearsal VERSION=0.1.0`
- [x] `make ga-gate VERSION=0.1.0`

## Rollout/Communication
- [x] Treat the abandoned `0.1.x` tags as prelaunch rehearsal only in local
  source truth.
- [x] Keep full-stack install as the default user-facing contract.
- [x] Split the managed runtime into smaller release assets so uploads and
  downloads stop stalling on one monolithic payload.
- [x] Cut the restarted `v0.1.0` line only after local hosted-asset
  preflight passes on `main`.

## Dependencies/Preconditions
- [x] `B-005` remains the governing relaunch workstream.
- [x] The self-host posture and canonical release authority guard from `B-004`
  remain in force.
- [x] Related bugs from the abandoned rehearsal line remain tracked in the
  public repo as prelaunch findings.
- [x] New oversized-payload bug was captured while implementing the relaunch.
- [x] New Hatch-posture CI drift bug was captured while closing relaunch
  validation gaps.
- [x] New atomic download/restage hardening bug was captured during the final
  reliability pass.
- [x] New first-install and same-version live-activation hardening bug was
  captured during the final reliability pass.

## Edge Cases
- [x] Unsupported platforms still fail clearly before mutating repo truth.
- [x] Consumer repos still may not activate `source-local`.
- [x] Full-stack install remains the default even though assets are split.
- [x] When the context-engine pack asset digest is unchanged, upgrade may reuse
  it instead of redownloading it.
- [x] When the context-engine pack is missing or stale, install and upgrade
  still restage the full managed runtime outcome.
- [x] Hosted `previous -> target -> rollback -> re-upgrade` proof depends on a
  previous published release; the local preflight covers that upgrade-cycle
  contract before the public lane accumulates that history.

## Open Questions/Decisions
- [x] Decision: full-stack install remains the default operator contract.
- [x] Decision: the asset split exists for transport, reuse, and retention, not
  for a weaker default install.
- [x] Decision: the hosted install script stays one-command and
  non-interactive; environment detection and asset selection are Odylith's job,
  not the developer's.
- [x] Decision: `watchdog` belongs in the full-stack path, with `watchman`,
  `git-fsmonitor`, and polling still available as watcher fallbacks.

## Current Outcome
- The source version floor and repo pin now restart at `0.1.0`.
- The release lane can build smaller split managed assets while still
  delivering a full-stack runtime on install and upgrade.
- The hosted installer now stays one-command and non-interactive while
  detecting the environment, selecting the right managed assets, and presenting
  clearer operator messaging.
- The maintainer build lane now treats Hatch as the canonical wheel-build
  frontend instead of a generic `python -m build` path.
- Repo CI now uses the Hatch-managed environment for test execution instead of
  direct-pip bootstrap commands.
- Version/doctor now surface context-engine pack state, and lifecycle
  operations prune retained runtimes plus cached release payloads.
- Release preflight now builds local hosted-style assets and runs the generated
  installer smoke before dispatch.
- Verified release downloads, install-state writes, and same-version runtime
  restaging now use atomic commit/swap behavior with bounded transient-network
  retry instead of delete-first mutation.
- Fresh consumer install now activates only after the full-stack runtime
  passes smoke, and same-version upgrade fails closed into repair guidance
  instead of live restage.
- The restarted `v0.1.0` line was published, dogfooded, consumer-rehearsed,
  and cleared through `ga-gate` from the canonical maintainer lane on `main`.
- Release-reset hardening now also includes repo-pin realignment support so a
  product checkout can return cleanly to the pinned baseline after prelaunch
  drift without keeping abandoned newer runtimes around as rollback targets.
