status: finished

idea_id: B-127

title: Migration Runtime Release Gate

date: 2026-04-27

priority: P0

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: odylith

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-27-migration-runtime-release-gate.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids: D-042

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith release upgrades currently derive migration behavior from scattered install-manager branches, one-off migration helpers, manifest flags, doctor/version readouts, and lifecycle simulator fixtures. That makes first-adopter upgrades feel risky because dry-run, apply, doctor, and release proof can disagree about what must migrate.

## Customer
Odylith maintainers and downstream consumer-repo operators who need upgrades from 0.1.10, 0.1.11, source-local dogfood, legacy installs, or partial-failure states to be precise, idempotent, and auditable before mutation.

## Opportunity
Create a first-class migration runtime that classifies repo state, selects registered migrations, writes durable ledgers, and gates releases so every upgrade has one transaction-shaped source of truth.

## Proposed Solution
Create `migration-runtime` as the release/install migration component, route the
v0.1.11 visible-intervention value-engine migration through its registry, make
dry-run/apply/doctor consume one `MigrationPlan`, and add a release migration
gate that fails when manifest requirements, fixture coverage, or lifecycle
paths bypass the runtime.
The runtime also owns legacy Odyssey root migration, separates live active
state from historical migration range, and treats lock/cache sludge and
generated dashboard staleness as repair or refresh signals rather than release
migration failures.
The 2026-04-29 CB-136 follow-up adds an executable destructive-write scenario
matrix to the release gate so migration proof now covers host settings,
project-root skill pruning, symlinked host/project managed-asset destinations,
governance source preservation, legacy root/state conflict blocking, runtime
activation atomicity, ledger idempotency, repair-only cleanup, and
generated-surface separation.
The GitHub issue pipeline follow-up adds public issue intake and release
closeout to the same 0.1.12 adoption-risk lane so GitHub issue #21, CB-136,
labels, public comments, and release closure cannot drift apart.

## Scope
- Add the migration runtime contracts and registry.
- Wire upgrade dry-run, upgrade apply, reinstall fallback, doctor observability,
  and release migration-gate.
- Keep dashboard refresh as separate post-upgrade work, not migration state.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- Future releases with `migration_required=true` must register migration
  definitions and fixtures before publish; otherwise the gate fails closed.

## Dependencies
- CB-135 captures the adoption-risk failure.
- Atlas D-042 maps the transaction flow.
- Registry component `migration-runtime` owns the runtime boundary.

## Success Metrics
0.1.12 cannot close until migration-runtime exists as a governed component; upgrade --dry-run and --json expose scenario and migration_plan; v0.1.11 value-engine migration and legacy Odyssey root migration route through the registry; migration_required releases are blocked only when no registered migration satisfies them; fixture tests cover first install, skipped versions, stale ledger, missing ledger but satisfied artifacts, legacy installs, missing pin, missing state, missing launcher, stale live pointer, missing runtime verification, staged target verification evidence, missing rollback target, source-local, product dogfood, lock/cache sludge, generated-surface staleness, schema mismatch, and failed prior upgrade reports.

## Validation
- `PYTHONPATH=src python3 -m pytest -q` passed with 3195 tests and 1 skipped.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_migration_runtime.py tests/unit/install/test_value_engine_migration.py tests/unit/install/test_versioning.py tests/unit/test_cli_audit.py tests/unit/test_cli.py` passed with 304 tests.
- `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py tests/integration/install/test_lifecycle_simulator.py tests/integration/install/test_bundle.py` passed with 91 tests.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py tests/unit/install/test_codex_project_assets.py tests/unit/install/test_claude_effective_settings.py` passed with 66 tests.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_show_capabilities.py tests/unit/runtime/test_incremental_import_graph.py` passed with 24 tests.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py tests/unit/runtime/test_shell_onboarding.py` passed with 64 tests.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_claude_effective_settings.py tests/unit/install/test_codex_project_assets.py tests/unit/install/test_migration_runtime.py` passed with 54 tests after the CB-136 destructive-write matrix follow-up.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_claude_effective_settings.py tests/unit/install/test_codex_project_assets.py tests/unit/install/test_migration_runtime.py` passed with 61 tests after the symlinked host/project managed-asset follow-up.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_release_assets.py tests/unit/install/test_release_bootstrap.py tests/integration/install/test_manager.py tests/integration/install/test_lifecycle_simulator.py` passed with 167 tests after the symlinked managed-asset guard follow-up.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_source_bundle_mirror.py tests/unit/runtime/test_hygiene.py` passed with 52 tests after the symlinked managed-asset guard follow-up.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_github_issue_pipeline.py` passed with 12 tests after the GitHub issue intake and release-closeout pipeline follow-up.
- `PYTHONPATH=src python3 -m odylith.cli github --repo-root . issue release-closeout --repo odylith/odylith --release current --json` reported CB-136 as pending release with validation evidence and no close eligibility while release-0-1-12 remains active.
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py tests/unit/runtime/test_shell_onboarding.py` passed with 65 tests after the symlinked managed-asset guard follow-up.
- `PYTHONPATH=src python3 -m odylith.cli upgrade --repo-root . --dry-run --json` passed and reported `scenario=product_repo_pinned_dogfood`.
- `PYTHONPATH=src python3 -m odylith.cli doctor --repo-root .` passed and reported migration scenario plus ledger state.
- `PYTHONPATH=src python3 -m odylith.cli release migration-gate --repo-root . --target-version 0.1.12 --json` passed with `ok=true`.
- `git diff --check`, `py_compile` on touched runtime/install/test files, `odylith casebook validate`, and `odylith validate component-registry` passed.

## Rollout
- Landed in 0.1.12 as the gating runtime for install/upgrade/reinstall
  migration behavior.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Migration becomes the first gating function for a release: upgrade dry-run, upgrade apply, doctor, reinstall, and release validation all consume the same migration plan and report the same scenario, selected migrations, skipped reasons, blocked reasons, write sets, ledger state, and rollback scope.

## Impacted Components
- `migration-runtime`
- `odylith`

## Interface Changes
- Add `release migration-gate`.
- Add `scenario`, `migration_plan`, `migration_results`, `ledger_state`,
  `blocked_reason`, and `plan_fingerprint` to upgrade dry-run/report JSON.
- Add migration scenario and ledger-state lines to doctor output.

## Migration/Compatibility
- The v0.1.11 value-engine migration remains backward compatible through the
  legacy install-ledger `value_engine_migration` payload, but migration decisions
  now originate from `migration_runtime`.
- Legacy Odyssey roots migrate through the same runtime as a pre-runtime
  repo-state migration with its own ledger and fixture coverage.

## Test Strategy
- Unit-test definitions, scenarios, decisions, stale ledger, shared version
  ordering, lock hygiene, and gate reports.
- Integration-test upgrade/reinstall lifecycle behavior and migration-required
  fail-closed behavior.

## Open Questions
- Whether 0.1.13 should fold migration-gate into a broader maintainer preflight
  wrapper; 0.1.12 keeps it focused and explicit.

## Outcome
- Completed and closed on 2026-04-27.
- Implemented the governed `migration-runtime` Registry component, migration
  definitions, shared plan/result contracts, release migration gate, doctor
  observability, durable ledgers, legacy Odyssey root migration routing,
  staged runtime verification evidence handling, and v0.1.11 value-engine
  migration routing through the registry.
- Split remaining generated-surface reviewability into CB-134 so B-127 stays
  scoped to release migration gating rather than dashboard refresh diff
  ergonomics.
- Extended the closed workstream on 2026-04-29 with CB-136 class coverage:
  destructive-write scenarios are now gate-visible JSON, custom `.agents/skills`
  are preserved, legacy root/state conflicts block before mutation, and the
  migration-runtime component spec records those guardrails.
