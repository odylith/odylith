Status: Done
Created: 2026-04-27
Updated: 2026-04-27
Backlog: B-127

# Migration Runtime Release Gate

## Goal
Make migration a first-class install-owned release gate for 0.1.12. Upgrade,
install, reinstall, doctor, and release validation must consume one
authoritative migration plan that answers the operator questions before
mutation: what repo state is this, which migrations apply, which are already
satisfied, what will write, what is blocked, how rollback works, and what proof
makes the transaction safe.

## Decisions
- Introduce a governed `migration-runtime` Registry component instead of adding
  more install-manager branches.
- Keep automatic release migrations allowed only when they are registered,
  predicate-verified, ledgered, idempotent, and fixture-proven.
- Treat generated dashboard refresh as a post-upgrade surface refresh, not a
  migration.
- Keep rollback scope for this wave to runtime activation and repo-local
  launcher state; repo-owned generated surfaces still revert through Git unless
  a future migration explicitly owns them.
- Do not keep compatibility shims for removed migration-era APIs unless a
  registered migration declares and tests a bounded compatibility window.

## Related Records
- Backlog: B-127.
- Casebook: CB-135.
- Registry: `migration-runtime`.
- Target release: 0.1.12.

## Must-Ship
- [x] Add `src/odylith/install/migration_runtime.py` with
      `MigrationDefinition`, `MigrationPlan`, `MigrationResult`, durable ledger
      helpers, scenario classification, migration selection, application, and
      release-gate validation.
- [x] Route the v0.1.11 visible-intervention value-engine migration through the
      registered migration runtime instead of direct install-manager calls.
- [x] Route the legacy Odyssey root migration through the migration runtime as
      a pre-runtime repo-state migration instead of leaving it as an
      install-manager side branch.
- [x] Make `plan_upgrade_lifecycle` and `upgrade_install` use the same
      migration plan and expose `scenario`, `migration_plan`, `ledger_state`,
      and blocked reasons in JSON.
- [x] Keep active repo-state classification separate from historical
      from-version migration range so align-pin, source-local recovery, and
      already-current flows do not produce false stale-state blocks.
- [x] Make `migration_required=true` releases block only when no registered
      migration plan can satisfy the declared requirement.
- [x] Report pending, stale, blocked, or satisfied-unrecorded migration state in
      doctor without letting `doctor --repair` run release migrations.
- [x] Add a release migration gate command that validates registered migration
      coverage, fixture coverage, and lifecycle bypasses.
- [x] Add unit and integration coverage for no-op, automatic apply,
      satisfied-unrecorded, stale ledger, blocked, source-local, missing pin,
      and migration-required cases.
- [x] Cover the staged-runtime verification edge case where activation has
      installer-returned verification evidence before the runtime verification
      marker exists on disk.
- [x] Harden the release gate fixture matrix so coverage requires explicit
      `migration-id:fixture` markers rather than incidental test vocabulary.
- [x] Consolidate install version comparison behind
      [versioning.py](/Users/freedom/code/odylith/src/odylith/install/versioning.py)
      and install-owned Git ignore rules behind
      [gitignore_rules.py](/Users/freedom/code/odylith/src/odylith/install/gitignore_rules.py).

## Should-Ship
- [x] Keep dry-run stdout exact and operator-readable: resolved target,
      scenario, migration IDs, selected/skipped/blocked reasons, exact write
      paths, rollback scope, and no-op state.
- [x] Keep JSON additive and backward compatible while making the new migration
      plan machine-readable.
- [x] Keep the install manager and CLI as thin callers into the migration
      runtime instead of adding new formatter-only inference.
- [x] Add Atlas coverage for the transaction flow and update the component spec
      with ownership and proof obligations.
- [x] Add GitHub issue intake and release closeout as the public-feedback gate
      for this adoption-risk lane, with CB-136 linked to odylith/odylith#21
      and closure blocked until v0.1.12 is public.

## Non-Goals
- Do not redesign dashboard refresh reviewability in this slice.
- Do not turn generated dashboard freshness into a migration failure.
- Do not introduce a new operator flag to request migration planning.
- Do not hand-copy host-repo-specific migration truth into the public Odylith
      product repo.

## Impacted Areas
- [x] [migration_runtime.py](/Users/freedom/code/odylith/src/odylith/install/migration_runtime.py)
- [x] [legacy_install_migration.py](/Users/freedom/code/odylith/src/odylith/install/legacy_install_migration.py)
- [x] [gitignore_rules.py](/Users/freedom/code/odylith/src/odylith/install/gitignore_rules.py)
- [x] [versioning.py](/Users/freedom/code/odylith/src/odylith/install/versioning.py)
- [x] [manager.py](/Users/freedom/code/odylith/src/odylith/install/manager.py)
- [x] [value_engine_migration.py](/Users/freedom/code/odylith/src/odylith/install/value_engine_migration.py)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [test_migration_runtime.py](/Users/freedom/code/odylith/tests/unit/install/test_migration_runtime.py)
- [x] [test_manager.py](/Users/freedom/code/odylith/tests/integration/install/test_manager.py)
- [x] [test_lifecycle_simulator.py](/Users/freedom/code/odylith/tests/integration/install/test_lifecycle_simulator.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q` passed with 3195 tests and 1 skipped.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_migration_runtime.py tests/unit/install/test_value_engine_migration.py tests/unit/install/test_versioning.py tests/unit/test_cli_audit.py tests/unit/test_cli.py` passed with 304 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py tests/integration/install/test_lifecycle_simulator.py tests/integration/install/test_bundle.py` passed with 91 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py tests/unit/install/test_codex_project_assets.py tests/unit/install/test_claude_effective_settings.py` passed with 66 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_show_capabilities.py tests/unit/runtime/test_incremental_import_graph.py` passed with 24 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py tests/unit/runtime/test_shell_onboarding.py` passed with 64 tests.
- [x] `PYTHONPATH=src python3 -m py_compile src/odylith/install/__init__.py src/odylith/install/migration_runtime.py src/odylith/install/manager.py src/odylith/install/value_engine_migration.py src/odylith/install/versioning.py src/odylith/install/legacy_install_migration.py src/odylith/install/gitignore_rules.py src/odylith/install/lock_hygiene.py src/odylith/install/upgrade_reporting.py src/odylith/cli.py tests/unit/install/test_migration_runtime.py tests/integration/install/test_manager.py tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/unit/test_cli_audit.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli upgrade --repo-root . --dry-run --json` passed and reported `scenario=product_repo_pinned_dogfood`.
- [x] `PYTHONPATH=src python3 -m odylith.cli doctor --repo-root .` passed and reported migration scenario plus ledger state.
- [x] `PYTHONPATH=src python3 -m odylith.cli release migration-gate --repo-root . --target-version 0.1.12 --json` passed with `ok=true`.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_github_issue_pipeline.py` passed with 12 tests.
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_github_issue_pipeline.py` passed with 19 tests after the GitHub issue pipeline boundary-hardening follow-up.
- [x] `PYTHONPATH=src python3 -m odylith.cli github --repo-root . issue triage 21 --repo odylith/odylith --json` produced a draft-only P0/data-loss/install plan matching CB-136.
- [x] `PYTHONPATH=src python3 -m odylith.cli github --repo-root . issue release-closeout --repo odylith/odylith --release current --json` reported odylith/odylith#21 pending release, with validation evidence present and no closure before public release availability.
- [x] `git diff --check`
- [x] `./.odylith/bin/odylith casebook validate --repo-root .` passed with 134 records checked.
- [x] `./.odylith/bin/odylith validate component-registry --repo-root .` passed with 28 components and 399 events after the GitHub issue pipeline follow-up.

## Implementation Notes
- `release migration-gate` reports the registered migrations, covered version
  ranges, fixture matrix, manual blocks, and lifecycle bypass scan.
- The install manager no longer calls release migration helpers directly; it
  plans and applies through `migration_runtime`. Legacy root migration is owned
  by `legacy_install_migration.py` and invoked through the repo-state migration
  plan.
- The GitHub issue pipeline now owns issue fetch, classification, Casebook
  linkage, public label/comment drafts, and fixed-in-release closeout for
  linked public issues.
- The GitHub issue pipeline is now split into durable phase owners: models,
  reference parsing, Casebook/release truth, classification/public-response
  policy, REST transport, orchestration, and CLI adaptation. Public GitHub
  apply fails closed without a linked Casebook record, and release closeout
  blocks closure when public release artifacts exist but issue state cannot be
  confirmed open.
- `upgrade --dry-run --json` exposes `scenario`, `migration_plan`,
  `migration_results`, `ledger_state`, `blocked_reason`, and
  `plan_fingerprint`.
- Scenario tests now cover missing pin, missing install state, missing
  launcher, stale live pointer, failed prior upgrade report, schema mismatch,
  runtime verification missing, staged target verification evidence, missing
  rollback target, generated-surface staleness, lock/cache sludge,
  source-local, product dogfood, legacy roots, migration-required registered
  targets, and migration-required unknown targets.

## Closure
- Closed on 2026-04-27 after the branch-level QA pass proved full pytest,
  focused migration/install suites, release migration gate, doctor, Casebook,
  component-registry, py_compile, and diff hygiene.
- Remaining generated dashboard reviewability is intentionally tracked outside
  this migration gate in CB-134.

## Open Questions
- [x] Whether the final release gate should be part of a broader maintainer
      preflight command in 0.1.13. For 0.1.12, it remains a focused migration
      gate.
