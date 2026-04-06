Status: Done

Created: 2026-03-27

Updated: 2026-03-27

Goal: Make the Odylith product repo consume its own released install contract visibly and safely by deriving one authoritative self-host posture, exposing it in CLI and governed surfaces, and gating release cutting on source-level posture invariants.

Assumptions:
- The public Odylith repo is the only repo that should be classified as `product_repo`.
- The main product repo lane should dogfood the pinned release contract by default.
- `source-local` remains valid for unreleased development, but only as an explicit detached override.

Constraints:
- Do not add a new tracked self-host config file.
- Do not break consumer-repo install, upgrade, or rollback behavior.
- Keep release gating fail-closed without requiring `.odylith/` in CI.

Reversibility: The posture model is derived from existing runtime pointers, pins, and source metadata. CLI and surface readouts are additive, and the release gate is reversible by removing the validator invocation from the workflow if needed.

Boundary Conditions:
- Scope includes install/runtime posture derivation, CLI reporting, release validation, shell and Compass self-host payloads, and governance records for the new contract.
- Scope excludes broader GA process policy, support windows, or changes to downstream repo truth ownership.

## Context/Problem Statement
- [x] Odylith already has staged runtime versions, rollback, release verification, and a tracked repo pin.
- [x] The public product repo can still run in detached `source-local` mode while older status paths or shell surfaces under-report that posture.
- [x] Release discipline needs one explicit validator instead of relying on operator memory and ad hoc inspection.
- [x] Compass should treat detached or diverged self-host posture as a product-runtime risk, not as invisible background state.

## Success Criteria
- [x] `odylith version` reports `Repo role`, `Posture`, `Runtime source`, and `Release eligible`.
- [x] `odylith doctor` reports the same posture fields alongside health results.
- [x] `odylith validate self-host-posture --mode local-runtime|release` exists and fails closed on invalid posture.
- [x] `.github/workflows/release.yml` runs the release-mode validator before building and uploading release assets.
- [x] Tooling shell payload and Compass runtime payload expose a `self_host` block.
- [x] Compass surfaces a self-host runtime risk when the product repo is detached, diverged, or incomplete.
- [x] Atlas and Registry describe the same self-host posture contract the code now enforces.

## Non-Goals
- [x] Creating a hosted control plane for release authorization.
- [x] Turning every detached local dev checkout into a hard error for normal coding work.
- [x] Redesigning the full public GA program or OSS maintainer policy.

## Impacted Areas
- [x] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [odylith/technical-plans/INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [odylith/atlas/source/catalog/diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [odylith/registry/source/components/odylith/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [odylith/registry/source/components/dashboard/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/dashboard/CURRENT_SPEC.md)
- [x] [odylith/registry/source/components/compass/CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)

## Traceability
### Runbooks
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)

### Developer Docs
- [x] [odylith-repo-integration-contract.md](/Users/freedom/code/odylith/docs/specs/odylith-repo-integration-contract.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/dashboard/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)

### Atlas
- [x] [odylith-self-host-runtime-and-release-gate.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-self-host-runtime-and-release-gate.mmd)

### Code References
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [validate_self_host_posture.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_self_host_posture.py)
- [x] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [x] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [compass_dashboard_shell.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_shell.py)
- [x] [release.yml](/Users/freedom/code/odylith/.github/workflows/release.yml)

## Risks & Mitigations

- [x] Risk: product and consumer repos can be confused if repo-role detection is too loose.
  - [x] Mitigation: derive `product_repo` only from Odylith-specific repo shape, not from a loose `src/odylith` path check.
- [x] Risk: local runtime state and release gating can drift if shell, Compass, and CLI compute posture separately.
  - [x] Mitigation: derive posture once from install status helpers and reuse it in validator and surface payloads.
- [x] Risk: maintainers can keep developing from detached `source-local` and miss that release posture is blocked.
  - [x] Mitigation: make detached posture loud in `version`, `doctor`, Compass risks, and failed local preflight.
- [x] Risk: maintainers can still dispatch the GitHub workflow without running a local preflight first.
  - [x] Mitigation: keep the source-only release gate strict in CI and document local preflight in the install runbook.

## Validation/Test Plan
- [x] `pytest -q tests/unit/runtime/test_validate_self_host_posture.py tests/unit/test_cli.py tests/integration/install/test_manager.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py`
- [x] `pytest -q`
- [x] `odylith validate self-host-posture --repo-root . --mode release --expected-tag v0.1.0`
- [x] `odylith sync --repo-root . --force`

## Rollout/Communication
- [x] Land posture derivation and the validator before changing release workflow behavior.
- [x] Record the new contract in Radar, Atlas, Registry, and Compass.
- [x] Refresh the operator runbook and integration contract so maintainers have one explicit preflight path.

## Dependencies/Preconditions
- [x] Keep workstream `B-004` active in `odylith/radar/source/INDEX.md`.
- [x] Keep the tracked product pin in `odylith/runtime/source/product-version.v1.json`.

## Edge Cases
- [x] Live runtime pointer disagrees with `.odylith/install.json`: live pointer wins for active posture.
- [x] Product repo has no `.odylith/` in CI: release-mode validation stays source-only.
- [x] Product repo is detached `source-local` in a main checkout: visible, allowed for local work, release-ineligible.
- [x] Product repo rolled back to a previously verified version that no longer matches the pin: visible as diverged and blocked from release eligibility.
- [x] Consumer repos get the extra posture/readout fields without inheriting product-repo-only release gates.

## Open Questions/Decisions
- [x] Decision: the main product repo lane is pinned GA dogfood by default.
- [x] Decision: detached `source-local` is an explicit dev override, preferably in a separate worktree.
- [x] Decision: release workflow enforcement stays source-only in CI, while local runtime validation remains a maintainer preflight.
- [x] Follow-on question: Odylith may later add a maintainer helper to restage the product repo onto the newest locally verified pinned version after source-local work finishes.

## Current Outcome
- [x] Install status now derives `repo_role`, `posture`, `runtime_source`, and `release_eligible` from the live runtime pointer, tracked pin, and source version contract.
- [x] `odylith version` and `odylith doctor` now expose the self-host posture fields directly.
- [x] `odylith validate self-host-posture --mode local-runtime|release` now exists, and the release workflow runs the release-mode validator before building assets.
- [x] Tooling shell payload now carries a `self_host` block so product posture is available to shell consumers.
- [x] Compass runtime now carries the same `self_host` block and surfaces detached or diverged product-repo posture as an explicit risk.
- [x] Install/upgrade/rollback and failed local self-host release preflight now emit Compass timeline evidence for posture drift and blocked release posture.

## Residual Operational State
- [x] This checkout is still running detached `source-local`, and no public `v0.1.0` release exists yet to activate a verified pinned runtime for the main repo lane.

## Follow-on
- [x] Public release rehearsal, verified pinned dogfood activation, and first real consumer install/upgrade/rollback adoption are tracked separately in `B-005` so this repo-complete self-host posture contract can close without faking a release that does not exist.
