- Bug ID: CB-161

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-03

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The hosted curl installer treated a complete existing Odylith repo whose pin and active runtime already matched the target release as an install rematerialization instead of an upgrade. That bypassed the authoritative upgrade lifecycle and any same-version migration checks registered in the target runtime.

- Impact: Consumer operators reinstalling or refreshing Odylith with the public curl command can miss required migration checks even though Odylith is already present and the command should converge the repo through the upgrade lifecycle.

- Components Affected: release

- Environment(s): Consumer repos with a complete Odylith install shape, active version equal to the hosted release target, and new release-side migrations that must still run during reinstall or refresh.

- Detected By: Operator feedback on 2026-05-03 that rerunning curl -fsSL https://odylith.ai/install.sh | bash on an existing Odylith repo should trigger upgrade and the full migration cycle instead of fresh-install behavior.

- Failure Signature: Generated install.sh branched to odylith.cli install --repo-root <repo> --version <release> when installed_pin_version and installed_active_version both matched release_version; command-log coverage proved upgrade was not invoked.

- Trigger Path: curl -fsSL https://odylith.ai/install.sh | bash in an already-installed repo whose pin, active runtime, and hosted target all resolve to the same release.

- Ownership: Hosted installer generation and release upgrade lifecycle dispatch.

- Timeline: Captured 2026-05-03 after v0.1.13 consumer feedback exposed that reinstall-on-existing still felt like a fresh install and did not guarantee the full migration cycle.

- Blast Radius: All consumer repos using the public hosted installer as a refresh or reinstall path after Odylith is already installed, especially releases with same-version migration or source-truth normalization work.

- SLO/SLA Impact: High operator-trust and migration-safety impact; no app runtime outage expected, but local Odylith governance state may remain unmigrated after a successful public install command.

- Data Risk: Low application-data risk, medium local-governance-state risk because Casebook, Radar, Registry, Atlas, or runtime ledgers can stay in a legacy shape.

- Security/Compliance: No direct security issue; lifecycle auditability and release compliance are weakened when the public installer bypasses migration ledgers.

- Invariant Violated: The public hosted installer must treat complete existing Odylith installs as upgrade candidates and let the upgrade planner decide no-op versus migration, even when target and active versions match.

- Root Cause: The generated installer carried a same-version shortcut that read pin and install state, then called install instead of upgrade when both matched the release target. That shortcut predated registered same-version migration handling in upgrade_install.

- Solution: Remove the same-version shortcut from the generated install script. Complete existing installs now always dispatch to odylith upgrade --to <release> --write-pin; incomplete or stale-uninstall residue keeps the fresh install repair path.

- Rollback/Forward Fix: Forward fix in the hosted installer template for v0.1.14.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/install/test_release_bootstrap.py -k generated_install_script; python -m py_compile scripts/release/publish_release_assets.py.

- Prevention: Keep generated installer tests proving complete already-current installs route through upgrade, while incomplete install residue still routes through install repair.

- Regression Tests Added: tests/unit/install/test_release_bootstrap.py::test_generated_install_script_routes_complete_already_current_install_through_upgrade_lifecycle

- Monitoring Updates: Watch hosted installer transcripts for complete existing repos and verify the terminal lifecycle line comes from upgrade rather than compact install.

- Related Incidents/Bugs: CB-064, CB-074, CB-135

- Fixed In: 0.1.14

- Code References: - scripts/release/publish_release_assets.py
- tests/unit/install/test_release_bootstrap.py
