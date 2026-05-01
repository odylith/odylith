# Migration Runtime
Last updated: 2026-04-29


## Overview

Migration Runtime is the install-owned release migration gate for Odylith
0.1.12 and later. It turns install, upgrade, reinstall, doctor, and release
validation from scattered one-off migration branches into one transaction-shaped
contract.

## Boundary

- **Logical boundary**: Own repo-state classification, migration registry
  lookup, dry-run planning, migration apply, durable ledger verification,
  doctor migration observability, and release migration gate validation.
- **Evidence anchors**: `src/odylith/install/migration_runtime.py`,
  `src/odylith/install/destructive_write_scenarios.py`,
  `src/odylith/install/legacy_install_migration.py`,
  `src/odylith/install/versioning.py`
- **Kind**: library
- **Status**: active

## Contract

- `MigrationDefinition` records the migration id, introduced version, version
  range, scenario predicates, required manifest fields, write set, rollback
  scope, validation commands, and fixture coverage.
- `MigrationPlan` is the single source of truth shared by dry-run and apply. It
  contains the repo scenario, selected/skipped/blocked decisions, planned paths,
  ledger state, no-op status, blocked reason, and plan fingerprint.
- `MigrationResult` records actual apply outcomes, written/removed paths,
  ledger path, verification result, and repair advice.
- The v0.1.11 visible-intervention value-engine migration is registered here
  and no longer called directly from the install manager or bootstrap asset
  layer.
- The legacy Odyssey root migration is registered here and applied as a
  pre-runtime repo-state migration before runtime activation.
- Scenario classification uses live active runtime state separately from
  historical migration range so repair, align-pin, source-local recovery, and
  already-current flows do not inherit stale predicates.
- Staged runtime verification evidence returned by the installer is accepted
  by the plan contract, so upgrade apply does not falsely block before the
  staged runtime writes its durable verification marker.
- Lock/cache sludge and generated dashboard staleness are reported as repair or
  refresh posture, not release migration failures.
- `migration_required=true` releases are blocked only when no registered
  migration can satisfy the declared requirement for the concrete from/to
  version window.
- `doctor` may report migration state, but repair-class cleanup must not run
  release migrations.
- `release migration-gate` fixture coverage is explicit per migration id and
  fixture token, so incidental test words cannot satisfy release-gate proof.
- Destructive-write scenarios are first-class gate input. The gate now tracks
  host config, managed project-root assets, governance source truth, legacy
  root/state migration conflicts, runtime activation, ledger idempotency,
  repair-only lock cleanup, and generated-surface separation as adoption-risk
  guardrails with required proof markers.
- Host-config and managed-asset destructive-write scenarios include symlinked
  project roots, symlinked managed files, symlinked cleanup roots, and symlinked
  product-tree targets. Install, upgrade, reinstall, and repair must skip those
  writes instead of following external dotfile-manager or enterprise-managed
  paths.
- `uninstall` preserves the repo-local `odylith/` governed source truth,
  removes `.odylith/` runtime state after detaching root guidance, and unlinks
  symlinked `.odylith/` without following the external target. It must not
  remove `.claude/`, `.codex/`, or `.agents/` as part of Odylith cleanup.
- Legacy `odyssey` root migration must preflight conflicts before moving or
  deleting either root. If an existing `odylith/` or `.odylith/` path would be
  overwritten or discarded, the migration plan blocks and direct apply raises
  before mutation.

## Dependencies

- Upstream: `odylith.install.state`, `odylith.install.runtime`,
  `odylith.install.value_engine_migration`,
  `odylith.install.legacy_install_migration`, and
  `odylith.install.versioning` for state, runtime, migration evidence, legacy
  root migration, and version-window decisions.
- Downstream: `odylith.install.manager`, `odylith.cli`, upgrade reports,
  doctor output, and release migration-gate validation.
- Governance: B-127, CB-135, and Atlas D-042.

## Test Coverage

- Unit: `tests/unit/install/test_migration_runtime.py` covers registered
  definitions, scenario classification, selected/skipped/blocked decisions,
  satisfied-unrecorded ledgers, stale ledgers, staged runtime verification
  evidence, migration-required blocking, legacy conflict blockers, destructive
  write fixture coverage, and release-gate output.
- Unit: `tests/unit/install/test_claude_effective_settings.py` and
  `tests/unit/install/test_codex_project_assets.py` cover host settings
  additive merge, invalid JSON/direct symlink refusal, symlinked `.claude/` and
  `.codex/` project-root refusal, preimage stability, existing Codex config
  preservation, custom `.agents/skills` preservation, symlinked managed asset
  destination refusal, symlinked skill-prune root refusal, and symlinked
  release-note cleanup refusal.
- Unit: `tests/unit/install/test_versioning.py`,
  `tests/unit/install/test_lock_hygiene.py`, and
  `tests/unit/install/test_upgrade_reporting.py` cover shared version ordering,
  repair-class lock cleanup, and upgrade report observability.
- Unit: `tests/unit/install/test_value_engine_migration.py` covers the concrete
  value-engine artifact removal and idempotency behavior.
- Integration: `tests/integration/install/test_manager.py` and
  `tests/integration/install/test_lifecycle_simulator.py` prove upgrade
  dry-run/apply parity, same-version no-op behavior, migration-required
  fail-closed behavior, rollback retention, failed-smoke recovery, and
  uninstall preservation of the repo-local `odylith/` tree and symlink-safe
  removal of `.odylith/` runtime state.
- CLI: `tests/unit/test_cli.py` proves `upgrade --dry-run --json` carries the
  additive migration plan fields and `release migration-gate --json` emits a
  machine-readable gate report.

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-27 · Implementation:** 0.1.12 migration-runtime QA pass closed with full pytest, release migration gate, doctor, Casebook, and component-registry validation green.
  - Scope: B-127
  - Evidence: odylith/casebook/bugs/2026-04-27-scattered-migration-logic-makes-upgrade-state-non-authoritative.md, src/odylith/install/migration_runtime.py +1 more
- **2026-04-27 · Implementation:** 0.1.12 migration runtime gate hardened with legacy root routing, explicit fixture markers, active-state classification, and expanded edge-case tests.
  - Scope: B-127
  - Evidence: odylith/technical-plans/in-progress/2026-04/2026-04-27-migration-runtime-release-gate.md, src/odylith/install/migration_runtime.py +1 more
- **2026-04-27 · Implementation:** Implemented the 0.1.12 migration-runtime release gate: dry-run/apply share one MigrationPlan, v0.1.11 value-engine migration routes through the registry, doctor reports ledger state, and release migration-gate validates fixture coverage and lifecycle bypasses.
  - Scope: B-127
  - Evidence: odylith/registry/source/components/migration-runtime/CURRENT_SPEC.md, src/odylith/install/migration_runtime.py +1 more
<!-- registry-requirements:end -->

## Feature History

- 2026-04-27: Created the migration-runtime release gate for 0.1.12, routing the v0.1.11 value-engine migration through registered dry-run/apply/doctor and release-gate contracts. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127))
- 2026-04-27: Hardened the 0.1.12 gate with legacy Odyssey repo-state migration, active-versus-historical version separation, explicit fixture markers, shared install versioning, and expanded scenario coverage. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-135)
- 2026-04-27: Added staged-runtime verification evidence to the migration plan contract after the full QA pass exposed false verification-missing blocks in upgrade integration fixtures. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-135)
- 2026-04-29: Added destructive-write scenario inventory and gate proof after CB-136 showed install could destroy host AI settings under enterprise SSL failure; also blocked legacy root/state conflict overwrites and narrowed `.agents/skills` pruning to known retired Odylith shims. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-136)
- 2026-04-29: Expanded CB-136 from direct settings overwrite into symlinked host/project managed-asset protection; the release gate now proves 21 destructive-write scenarios, including symlinked `.claude/`, `.codex/`, `.agents/`, `odylith/`, and release-note target paths. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-136)
- 2026-04-30: Corrected consumer uninstall to preserve repo-local `odylith/` governed source truth, remove `.odylith/` runtime state, and leave host config directories in place, with symlink-safe runtime-state proof in the destructive-write matrix. (Plan: [B-140](odylith/radar/radar.html?view=plan&workstream=B-140); Casebook: CB-143)
