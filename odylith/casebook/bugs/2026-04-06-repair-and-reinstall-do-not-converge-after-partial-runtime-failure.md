- Bug ID: CB-055

- Status: Open

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

- Solution: Add narrow target-version residue cleanup for `.backup-*`, failed
  staging directories, and stale wrapper outputs before retrying replacement.
  Prove repeated repair and reinstall converge after injected partial failure.

- Verification: Unit and integration tests should inject partial staging
  residue, rerun repair or reinstall, and prove the repo returns to a single
  healthy pinned runtime.

- Prevention: Release-lifecycle code needs characterization tests for
  interrupted staging and retry convergence, not only first-pass success.

- Detected By: Real migration of `/Users/freedom/code/dentoai-orion` on
  2026-04-06 after the first runtime trust failure.

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

- Regression Tests Added: Pending.

- Monitoring Updates: Watch repeated repair attempts for backup-residue and
  staging-residue failure signatures.

- Residual Risk: Unexpected cross-version residue could still need explicit
  handling if later release lanes widen staging topology.

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

- Fix Commit/PR: Pending.
