Status: Done

Created: 2026-03-30

Updated: 2026-03-30

Backlog: B-005

Goal: Tighten the consumer release operator contract so reinstall, repo-pin
adoption, launcher-bootstrap recovery, and shipped install guidance stay
aligned for this release.

Assumptions:
- Consumer repos should keep the managed-runtime trust boundary and must not
  fall back into arbitrary host Python during reinstall or launcher recovery.
- A narrow dashboard refresh command is part of the operator release story
  because upgrade and reinstall need a low-friction way to refresh the local
  shell after runtime changes.

Constraints:
- Do not widen consumer support to `source-local`.
- Keep the canonical operator entrypoint as `./.odylith/bin/odylith`, with any
  bootstrap shim explicitly scoped to launcher recovery.
- Keep bundled docs and skills aligned with the CLI contract shipped in this
  repo.

Reversibility: Reverting this slice returns Odylith to the previous install and
recovery contract where reinstall and repo-pin adoption are split, launcher
recovery depends on the main launcher being present, and refresh guidance
continues to overload full governance sync.

Boundary Conditions:
- Scope includes consumer reinstall semantics, launcher-bootstrap recovery,
  explicit dashboard refresh UX, Mermaid worker legibility, and shipped
  install/help/skill copy.
- Scope excludes release publication workflow changes and product-repo
  maintainer-only source-local behavior.

Related Bugs:
- no related bug found for the missing-launcher reinstall/recovery contract;
  adjacent release/install bugs were reviewed as context.

## Context/Problem Statement
- [ ] `odylith install` on an existing consumer repo can leave runtime and repo
      pin semantics feeling split across install and upgrade.
- [ ] Missing `./.odylith/bin/odylith` still creates too much operator
      friction even when a trusted repo-local runtime exists.
- [ ] Operators need a render-only dashboard refresh path instead of overloading
      full governance sync for shell upkeep.
- [ ] Mermaid worker failures need clearer per-diagram attribution and fallback.
- [ ] Source docs, bundled docs, and installed skills must ship the same CLI
      contract.

## Success Criteria
- [ ] `odylith reinstall --repo-root .` adopts the latest verified release and
      aligned repo pin in one step for consumer repos.
- [ ] `odylith install --repo-root . --adopt-latest` exposes the same
      one-command pin-adopting flow from the install surface.
- [ ] A repo-local bootstrap shim can restore launcher access through
      `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair` without
      requiring a second Odylith checkout.
- [ ] `odylith dashboard refresh --repo-root . --surfaces tooling_shell,radar`
      refreshes selected local surfaces without Registry/forensics churn.
- [ ] Mermaid worker failures name the blocking diagram ids and degrade to
      one-shot rendering clearly.
- [ ] Source-owned install docs, bundle mirrors, and shipped skills match the
      released CLI contract.

## Non-Goals
- [ ] Changing release publication orchestration.
- [ ] Adding Windows or Intel macOS support.
- [ ] Making consumer repos support detached `source-local`.

## Impacted Areas
- [ ] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [ ] [runtime.py](/Users/freedom/code/odylith/src/odylith/install/runtime.py)
- [ ] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [ ] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [ ] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [ ] [INSTALL.md](/Users/freedom/code/odylith/odylith/INSTALL.md)
- [ ] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)
- [ ] [SKILL.md](/Users/freedom/code/odylith/odylith/skills/delivery-governance-surface-ops/SKILL.md)
- [ ] bundle mirrors under [src/odylith/bundle/assets/odylith](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith)
- [ ] [test_runtime.py](/Users/freedom/code/odylith/tests/unit/install/test_runtime.py)
- [ ] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)

## Risks & Mitigations

- [ ] Risk: launcher bootstrap recovery quietly widens consumer trust to host
  - [ ] Mitigation: TODO (add explicit mitigation).
      Python.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [ ] Mitigation: keep the bootstrap shim inside repo-local runtime discovery
    only and fail closed if no trusted runtime exists.
- [ ] Risk: a narrow refresh command drifts from the authoritative surface
  - [ ] Mitigation: TODO (add explicit mitigation).
      render path.
- [ ] Risk: Unspecified risk (legacy backfill).
  - [ ] Mitigation: reuse existing render helpers and runtime-mode wiring
    instead of cloning a second render implementation.
- [ ] Risk: bundle docs and source docs drift again.
  - [ ] Mitigation: update source-owned docs and bundle mirrors in the same
    change and keep targeted CLI coverage on the new contract.

## Validation/Test Plan
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/install/test_runtime.py tests/unit/test_cli.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_consumer_profile.py tests/unit/runtime/test_sync_cli_compat.py`
- [ ] `PYTHONPATH=src python -m pytest -q tests/integration/install/test_manager.py -k 'consumer_upgrade_without_target_advances_to_latest_and_updates_pin or doctor_bundle_repairs_missing_bootstrap_paths_without_copying_product_payload'`
- [ ] `python -m py_compile src/odylith/cli.py src/odylith/install/runtime.py src/odylith/runtime/governance/sync_workstream_artifacts.py src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`

## Rollout/Communication
- [ ] Call out `reinstall`, `install --adopt-latest`, `dashboard refresh`, and
      `odylith-bootstrap doctor --repair` together in release notes and
      operator guidance.
- [ ] Treat the new dashboard refresh path as the default UX for local shell
      upkeep; keep full `odylith sync --force --impact-mode full` for
      authoritative governance regeneration.

## Current Outcome
- [x] This standalone hardening scratch plan is closed as absorbed work.
- [x] The operator reinstall, launcher recovery, and dashboard-refresh scope
      moved into [2026-03-30-odylith-consumer-upgrade-release-spotlight-and-shell-refresh.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-consumer-upgrade-release-spotlight-and-shell-refresh.md).
- [x] The broader release-lane hardening and validation follow-through moved
      into [2026-03-30-odylith-v0-1-6-release-hardening-product-explanation-and-refactor-discipline.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-03/2026-03-30-odylith-v0-1-6-release-hardening-product-explanation-and-refactor-discipline.md).
- [x] Closing this duplicate record avoids reopening finished backlog `B-005`
      with an artificial successor workstream while preserving the authored
      planning context.
