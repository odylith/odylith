- Bug ID: CB-134

- Status: Open

- Created: 2026-04-27

- Severity: P2

- Reproducibility: Consistent

- Type: operator-ux

- Description: Upgrade reviewability still needs generated-change manifest and lock compaction

- Impact: A successful consumer upgrade can still produce large generated dashboard churn and visible zero-byte lock accumulation that is technically harmless but hard to review and trust.

- Components Affected: odylith

- Environment(s): 0.1.12 maintainer branch after consumer upgrade feedback from 0.1.10 to 0.1.11.

- Detected By: Operator feedback packet calling out roughly 30 files changed with large generated insert/delete churn and 929 zero-byte lock files under .odylith/locks.

- Failure Signature: Upgrade command succeeds, but generated dashboard refresh can rewrite large Compass/Casebook/Registry payloads without a tracked review manifest. Before the 0.1.12 lock-hygiene patch, doctor also had no cleanup action for accumulated zero-byte lock files.

- Trigger Path: ./.odylith/bin/odylith upgrade --repo-root . followed by git diff review and ./.odylith/bin/odylith doctor --repo-root .

- Ownership: Install/runtime operational hygiene and generated surface reviewability.

- Timeline: Captured 2026-04-27 through `odylith bug capture`.

- Blast Radius: Consumer repos using Odylith upgrades where operators review generated shell churn in git or inspect .odylith operational state after upgrade.

- SLO/SLA Impact: No service outage, but review latency and operator confidence degrade because the mutation footprint is too noisy.

- Data Risk: Low data risk; local generated-surface reviewability and runtime-state hygiene risk.

- Security/Compliance: No direct security exposure; clearer manifests and lock compaction reduce false-positive operational concern.

- Invariant Violated: Upgrade review should separate runtime activation from generated dashboard refresh and should explain or compact local lock-state accumulation.

- Solution: Partial 0.1.12 fix landed: `odylith doctor` now reports large recursive `.odylith/locks` zero-byte placeholder accumulation, and `odylith doctor --repair` compacts stale placeholders while preserving the active `install.lock` and non-empty lock files. Remaining follow-up: add a tracked generated-change manifest or deterministic content-addressed dashboard summary for upgrade refreshes.

- Verification: Lock cleanup proof: `PYTHONPATH=src python3 -m odylith.cli doctor --repo-root . --repair` compacted 13,715 stale zero-byte lock placeholder(s) in the product repo, and the next doctor run reported healthy without the lock warning. Regression proof: `tests/unit/install/test_lock_hygiene.py`, `tests/unit/install/test_upgrade_reporting.py`, `tests/unit/test_cli.py`, and `tests/integration/install/test_manager.py` cover recursive lock inventory, stale-placeholder compaction, doctor warning copy, and repair behavior. Future fix should still prove deterministic generated manifest output and repeated no-op dashboard refresh stability.

- Prevention: Keep generated-surface reviewability as an explicit 0.1.12 follow-up acceptance criterion, and keep local lock hygiene covered by doctor warning/repair tests so zero-byte placeholder accumulation cannot regress into operator-facing sludge.

- Version/Build: Target release 0.1.12; split out after CB-133 landed the auditable report and doctor observability foundation.

- Related Incidents/Bugs: CB-133

- Code References: - src/odylith/cli.py
- src/odylith/runtime/governance/sync_workstream_artifacts.py
- src/odylith/install/lock_hygiene.py
- src/odylith/install/upgrade_reporting.py
- src/odylith/install/manager.py
