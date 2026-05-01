- Bug ID: CB-134

- Type: OperatorUX


- Status: Closed

- Created: 2026-04-27

- Severity: P2

- Reproducibility: Consistent


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

- Solution: Closed in 0.1.12. `odylith doctor` reports large recursive `.odylith/locks` zero-byte placeholder accumulation, and `odylith doctor --repair` compacts stale placeholders while preserving the active `install.lock` and non-empty lock files. Upgrade now writes `odylith/upgrade-generated-changes.v1.json` when post-upgrade dashboard refresh changes generated Odylith surfaces. The manifest is tracked repo truth and summarizes generated paths by surface category, byte count, line count, SHA-256 hash, aggregate byte count, and content fingerprint. `upgrade --json` and the persisted `.odylith/runtime/logs/upgrade-*.json` report include the same manifest summary, and `doctor` surfaces the last upgrade generated-change manifest so operators can review compact evidence before opening large generated JS/JSON diffs.

- Verification: Lock cleanup proof: `PYTHONPATH=src python3 -m odylith.cli doctor --repo-root . --repair` compacted 13,715 stale zero-byte lock placeholder(s) in the product repo, and the next doctor run reported healthy without the lock warning. Generated-change manifest proof: `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_upgrade_reporting.py` covers generated-surface classification, deterministic content fingerprints, tracked manifest writing, non-generated source-truth exclusion, and no-write behavior when only source truth changed. CLI proof: `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py -k 'upgrade_json_writes_auditable_report or doctor_prints_last_upgrade_report'` covers `upgrade --json` manifest inclusion, changed-path reviewability, and doctor readout of the last upgrade manifest. Compile proof: `PYTHONPATH=src python3 -m py_compile src/odylith/install/upgrade_reporting.py src/odylith/cli.py tests/unit/install/test_upgrade_reporting.py tests/unit/test_cli.py`.

- Prevention: Keep generated-surface reviewability and local lock hygiene covered by regression tests. Upgrade reports must keep `generated_change_manifest` machine-readable, and generated dashboard refresh churn must stay summarized by `odylith/upgrade-generated-changes.v1.json` instead of leaving operators with only large generated payload diffs.

- Regression Tests Added: `tests/unit/install/test_upgrade_reporting.py` covers generated-change manifest payloads, stable rewrite behavior, and source-truth exclusion. `tests/unit/test_cli.py` covers upgrade JSON manifest reporting and doctor generated-change observability.

- Version/Build: Target release 0.1.12; split out after CB-133 landed the auditable report and doctor observability foundation.

- Related Incidents/Bugs: CB-133

- Code References: - src/odylith/cli.py
- src/odylith/runtime/governance/sync_workstream_artifacts.py
- src/odylith/install/lock_hygiene.py
- src/odylith/install/upgrade_reporting.py
- src/odylith/install/manager.py
