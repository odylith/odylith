- Bug ID: CB-135

- Type: OperatorUX








- Status: Closed

- Created: 2026-04-27

- Severity: P0

- Reproducibility: Consistent


- Description: Scattered migration logic makes upgrade state non-authoritative

- Impact: Consumer operators and maintainers cannot trust a release upgrade when dry-run, apply, doctor, manifest migration_required handling, and one-off migration helpers can each derive migration state independently.

- Components Affected: migration-runtime

- Environment(s): Odylith 0.1.12 maintainer branch after 0.1.10 to 0.1.11 consumer upgrade feedback and implementation review of install manager migration paths.

- Detected By: Maintainer review of the 0.1.12 upgrade UX failure packet and source inspection showing migration decisions split across manager.py, value_engine_migration.py, legacy install migration, release manifest checks, and CLI reporting.

- Failure Signature: upgrade --dry-run can report or suppress migrations from inline predicates while upgrade applies a separately derived value-engine migration payload, legacy Odyssey root migration can bypass the release migration registry, doctor reports only partial migration/repair state, and migration_required releases hard-stop without a registered migration contract.

- Trigger Path: ./.odylith/bin/odylith upgrade --repo-root . --dry-run; ./.odylith/bin/odylith upgrade --repo-root .; ./.odylith/bin/odylith doctor --repo-root .; release manifest migration_required=true

- Ownership: Migration Runtime release-gating boundary for install, upgrade, reinstall, doctor, and release validation.

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: All Odylith consumer repositories crossing releases with state migrations, legacy installs, source-local dogfood, partial upgrade failure, missing ledger, missing pin, or migration_required release manifests.

- SLO/SLA Impact: High adoption and release-confidence impact: upgrades can succeed technically while still forcing operators to infer the true migration state and rollback posture.

- Data Risk: Low application-data risk, high local-governance and runtime-state trust risk because repo-owned generated truth and runtime state may be interpreted through inconsistent migration stories.

- Security/Compliance: No direct security vulnerability, but supply-chain and operational auditability are weakened when migration gates are not a single verifiable transaction contract.

- Invariant Violated: Every mutating release upgrade must use one authoritative migration plan for dry-run, apply, ledger, doctor, and release gate validation.

- Root Cause: Migration behavior evolved as one-off install-manager branches and migration helpers instead of a registered migration runtime with scenario classification, durable ledger verification, and release-gate coverage.

- Solution: Created the 0.1.12 `migration-runtime` component, routed the v0.1.11 value-engine migration and legacy Odyssey root migration through its registry, separated live repo-state classification from historical migration range, accepted installer-returned staged runtime verification as migration-plan evidence, exposed scenario and migration_plan in upgrade dry-run/json, wrote durable migration ledgers, added doctor migration observability, and added `release migration-gate` validation for registered migration coverage and lifecycle bypasses.

- Solution Update: A 2026-06-28 broad install-suite pass exposed a scenario
  ordering regression in the same migration-runtime custody boundary:
  consumer repos whose active runtime and pin already matched the target could
  be classified as `already_current_consumer` before the planner considered
  missing runtime verification or a `migration_required=true` release
  transition. The forward fix makes missing runtime verification outrank
  already-current classification, lets verified same-version reinstalls remain
  no-op, and passes `previous_version` into scenario classification so a
  release transition with `migration_required=true` still reaches the
  registered-migration blocker when no migration covers the concrete target.
  Failed mechanism recorded: do not let convenience no-op scenarios preempt
  fail-closed verification or manifest-custody states.

- Verification: `PYTHONPATH=src python3 -m pytest -q` passed with 3195 tests and 1 skipped; focused migration/CLI rerun passed with 304 tests; install manager, lifecycle simulator, and bundle integration passed with 91 tests; source `upgrade --dry-run --json`, `doctor`, and `release migration-gate --json` passed; `git diff --check`, `py_compile` on touched runtime/install/test files, Casebook validate, and component-registry validate passed.

- Verification Update: `tests/unit/install` passed with 383 tests after the
  ordering fix, including the three critical edges: verified same-version
  consumer reinstall stays `already_current_consumer`, same-version consumer
  runtime without verification blocks as
  `runtime_artifact_verification_missing`, and `migration_required=true`
  without a registered target migration blocks instead of no-oping.

- Prevention: Make migration-runtime validation a required 0.1.12 release gate so future migration_required releases cannot ship without registered definitions, fixture coverage, and dry-run/apply parity.

- Closed: 2026-04-27

- Version/Build: Target release 0.1.12; feedback originated from 0.1.10 to 0.1.11 consumer upgrade and post-GA migration UX review.

- Related Incidents/Bugs: CB-133, CB-134, B-127

- Code References: src/odylith/install/manager.py; src/odylith/install/migration_runtime.py; src/odylith/install/legacy_install_migration.py; src/odylith/install/versioning.py; src/odylith/install/value_engine_migration.py; src/odylith/install/release_assets.py; tests/integration/install/test_lifecycle_simulator.py
