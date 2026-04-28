# Migration Runtime

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
  evidence, migration-required blocking, and release-gate output.
- Unit: `tests/unit/install/test_versioning.py`,
  `tests/unit/install/test_lock_hygiene.py`, and
  `tests/unit/install/test_upgrade_reporting.py` cover shared version ordering,
  repair-class lock cleanup, and upgrade report observability.
- Unit: `tests/unit/install/test_value_engine_migration.py` covers the concrete
  value-engine artifact removal and idempotency behavior.
- Integration: `tests/integration/install/test_manager.py` and
  `tests/integration/install/test_lifecycle_simulator.py` prove upgrade
  dry-run/apply parity, same-version no-op behavior, migration-required
  fail-closed behavior, rollback retention, and failed-smoke recovery.
- CLI: `tests/unit/test_cli.py` proves `upgrade --dry-run --json` carries the
  additive migration plan fields and `release migration-gate --json` emits a
  machine-readable gate report.

## Feature History

- 2026-04-27: Created the migration-runtime release gate for 0.1.12, routing the v0.1.11 value-engine migration through registered dry-run/apply/doctor and release-gate contracts. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127))
- 2026-04-27: Hardened the 0.1.12 gate with legacy Odyssey repo-state migration, active-versus-historical version separation, explicit fixture markers, shared install versioning, and expanded scenario coverage. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-135)
- 2026-04-27: Added staged-runtime verification evidence to the migration plan contract after the full QA pass exposed false verification-missing blocks in upgrade integration fixtures. (Plan: [B-127](odylith/radar/radar.html?view=plan&workstream=B-127); Casebook: CB-135)
