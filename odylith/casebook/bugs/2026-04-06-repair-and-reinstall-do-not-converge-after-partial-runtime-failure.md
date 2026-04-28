- Bug ID: CB-055

- Status: Closed

- Created: 2026-04-06

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: After one partial runtime replacement failure, repeated
  `reinstall --latest` or `doctor --repair` attempts can hit secondary errors
  under leftover `.backup-*`, failed staging directories, or stale wrapper
  outputs instead of converging to one valid runtime state.

- Impact: Supported recovery commands require manual filesystem cleanup after a
  failed attempt, which breaks the core operator promise of idempotent repair.

- Components Affected: `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, runtime replacement helpers, repair
  lifecycle, reinstall flow.

- Environment(s): Consumer repos and product-repo dogfood or detached posture
  where runtime replacement fails partway through staging.

- Root Cause: Runtime replacement only reasons about the happy-path backup and
  restore flow. It does not sweep leftover target-version residue from earlier
  failed attempts before restaging the runtime.

- Solution: Added narrow target-version residue cleanup for `.backup-*`, failed
  staging directories, and stale wrapper outputs before retrying replacement.
  The cleanup is literal-name based, scoped to the requested target version, and
  invoked before wrapped-runtime creation, runtime repair selection, and managed
  release restaging.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_runtime.py -k 'cleanup_runtime_versions_residue or install_release_runtime_cleans_stale_backup or install_release_runtime_replaces_stale_wrapper or doctor_runtime_repair_converges'`
    passed (`5 passed, 37 deselected`).
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/install/test_manager.py -k 'reinstall_install_converges_repeatedly_with_stale_target_residue or reinstall_install_repairs_same_version_runtime_when_upgrade_requires_doctor'`
    passed (`2 passed, 80 deselected`).
  - Closing validation also ran the focused install/runtime suite, Casebook,
    Radar backlog, technical-plan, component-registry, py_compile, and diff
    hygiene checks.

- Prevention: Release-lifecycle code needs characterization tests for
  interrupted staging and retry convergence, not only first-pass success.

- Detected By: Real downstream migration rehearsal on 2026-04-06 after the
  first runtime trust failure.

- Failure Signature: `Directory not empty` under
  `.odylith/runtime/versions/.<version>.backup-*` during repeated repair or
  reinstall.

- Trigger Path: runtime replacement during `odylith reinstall --latest` and
  `odylith doctor --repair`.

- Ownership: install manager and managed runtime replacement contract.

- Timeline: Odylith already hardened fail-closed runtime staging, but the retry
  path still assumes the prior attempt cleaned up completely.

- Blast Radius: Repair convergence, reinstall reliability, release recovery,
  and operator trust in the lifecycle contract.

- SLO/SLA Impact: High operator-blocking maintenance impact.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: Supported repair and reinstall commands should converge
  after partial failure without manual filesystem surgery.

- Workaround: Manually delete leftover `.backup-*` and staging residue, then
  rerun repair.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Cleanup must remain narrow to the target version and must
  not delete unrelated operator-owned runtime history.

- Preflight Checks: Inspect runtime replacement, backup handling, and launcher
  regeneration before widening any cleanup rule.

- Regression Tests Added:
  `test_cleanup_runtime_versions_residue_limits_scope_to_target_version`,
  `test_cleanup_runtime_versions_residue_matches_literal_version_names`,
  `test_install_release_runtime_cleans_stale_backup_and_stage_residue`,
  `test_install_release_runtime_replaces_stale_wrapper_target`,
  `test_doctor_runtime_repair_converges_with_target_residue`,
  `test_reinstall_install_converges_repeatedly_with_stale_target_residue`.

- Monitoring Updates: Watch repeated repair attempts for backup-residue and
  staging-residue failure signatures.

- Residual Risk: Low. Future residue classes still need explicit prefix
  registration; the cleanup intentionally refuses broad or cross-version
  deletion.

- Related Incidents/Bugs:
  [CB-003](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md),
  [CB-015](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-release-download-cache-and-runtime-restage-lose-atomicity-on-failure.md),
  [CB-023](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-product-repo-doctor-repair-rewrites-root-agents-to-stale-managed-block.md),
  [CB-026](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-01-runtime-launcher-wrapper-recursion-and-trust-boundary-hardening.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default repair and reinstall flows.

- Customer Comms: Odylith repair could get stuck on leftover local runtime
  residue after one failed attempt; the fix makes repeated supported recovery
  converge cleanly.

- Code References: `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, `tests/integration/install/test_manager.py`,
  `tests/unit/install/test_runtime.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: 0.1.12 branch closeout commit for B-050/CB-055.
