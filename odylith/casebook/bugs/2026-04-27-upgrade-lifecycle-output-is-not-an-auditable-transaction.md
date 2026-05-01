- Bug ID: CB-133

- Type: OperatorUX


- Status: Closed

- Created: 2026-04-27

- Severity: P1

- Reproducibility: Consistent


- Description: Upgrade lifecycle output is not an auditable transaction

- Impact: Consumer operators can complete a remote Odylith upgrade but still cannot tell the exact dry-run target, verification evidence, no-op posture, rollback scope, dashboard fallback reason, or reviewable mutation footprint without inferring from later output and git churn.

- Components Affected: release

- Environment(s): 0.1.12 maintainer branch after feedback from a consumer repo upgraded from Odylith 0.1.10 to remote release 0.1.11.

- Detected By: Operator feedback packet from the successful 0.1.10 to 0.1.11 consumer upgrade.

- Failure Signature: Dry-run prints 'Target release: latest verified release' instead of v0.1.11 metadata; version prints ambiguous 'Available'; trust warning repeats before successful verification; repeated dry-run still lists v0.1.10 to v0.1.11 migration; dashboard refresh fallback timing is not persisted.

- Trigger Path: ./.odylith/bin/odylith upgrade --repo-root . --dry-run; ./.odylith/bin/odylith upgrade --repo-root .; ./.odylith/bin/odylith version --repo-root .; ./.odylith/bin/odylith doctor --repo-root .

- Ownership: Release/install upgrade lifecycle, managed-runtime verification, CLI report formatting, and doctor/version observability.

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: All consumer repos using remote upgrades, especially first-adoption repos evaluating Odylith trust, reviewability, and rollback confidence.

- SLO/SLA Impact: No runtime outage, but high adoption and release-confidence impact because the mutation plan is not precise before execution and the post-upgrade state is not auditable.

- Data Risk: Low application-data risk; moderate local-governance reviewability risk from large generated-surface churn and opaque runtime-state mutations.

- Security/Compliance: Supply-chain verification succeeds, but warning presentation weakens operator confidence in trust-root handling and should be explicit about whether verification degraded.

- Invariant Violated: A mutating remote upgrade must be precise before mutation, structured during execution, idempotent afterward, and reviewable in git without forcing the operator to infer target, verification, rollback, or fallback state.

- Solution: For v0.1.12, make upgrade dry-run resolve exact release metadata and digests, rename local version inventory, surface non-fatal trust warnings in version/doctor, suppress completed migrations from repeated dry-runs, add upgrade --json, persist upgrade reports under .odylith/runtime/logs, and print rollback scope/command.

- Root Cause: The upgrade lifecycle planner, formatter, version readout, doctor readout, dashboard refresh, and verification warning presentation each owned a piece of the operator story, but there was no shared transaction-shaped upgrade report contract tying the exact target, verification evidence, idempotency state, fallback details, rollback scope, and review paths together.

- Verification: pytest tests/unit/test_cli.py -k 'upgrade or version or doctor'; pytest tests/integration/install/test_manager.py -k 'upgrade_lifecycle or version_status or doctor_bundle_reports_trust'; python -m py_compile on touched install/CLI modules; casebook validate.

- Prevention: Keep regression coverage for exact target metadata, no-op dry-run, JSON reports, non-fatal trust warning wording, local-installed version wording, and persisted dashboard refresh details.

- Regression Tests Added: tests/unit/test_cli.py covers binding dry-run metadata, upgrade --json reports, version wording, and doctor trust warnings; tests/integration/install/test_manager.py covers exact latest release metadata and repeated no-op planning.

- Version/Build: Target release 0.1.12; feedback originated from 0.1.10 to 0.1.11 consumer upgrade.

- Related Incidents/Bugs: Related to B-030 consumer upgrade spotlight/shell refresh and B-040 runtime trust posture.

- Code References: - src/odylith/cli.py
- src/odylith/install/manager.py
- src/odylith/install/release_assets.py
