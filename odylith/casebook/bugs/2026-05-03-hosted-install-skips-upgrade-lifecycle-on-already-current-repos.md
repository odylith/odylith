- Bug ID: CB-161

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-03

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The hosted curl installer and direct `odylith install` path treated a complete existing Odylith repo as install rematerialization instead of upgrade. When pin and active runtime already matched the target release, that bypassed the authoritative upgrade lifecycle and any same-version migration checks registered in the target runtime.

- Impact: Consumer operators reinstalling or refreshing Odylith with the public curl command or the CLI install command can miss required migration checks even though Odylith is already present and the command should converge the repo through the upgrade lifecycle.

- Components Affected: release

- Environment(s): Consumer repos with a complete Odylith install shape, active version equal to the hosted release target, and new release-side migrations that must still run during reinstall or refresh.

- Detected By: Operator feedback on 2026-05-03 that rerunning curl -fsSL https://odylith.ai/install.sh | bash on an existing Odylith repo should trigger upgrade and the full migration cycle instead of fresh-install behavior.

- Failure Signature: Generated install.sh or direct CLI install branched to install_bundle/rematerialization for a complete existing consumer repo instead of invoking upgrade_install with release migrations and write-pin semantics.

- Trigger Path: curl -fsSL https://odylith.ai/install.sh | bash, or `odylith install --repo-root . --version <release>`, in an already-installed repo whose pin, active runtime, and target all resolve to a complete Odylith install shape.

- Ownership: Hosted installer generation and release upgrade lifecycle dispatch.

- Timeline: Captured 2026-05-03 after v0.1.13 consumer feedback exposed that reinstall-on-existing still felt like a fresh install and did not guarantee the full migration cycle.

- Blast Radius: All consumer repos using the public hosted installer as a refresh or reinstall path after Odylith is already installed, especially releases with same-version migration or source-truth normalization work.

- SLO/SLA Impact: High operator-trust and migration-safety impact; no app runtime outage expected, but local Odylith governance state may remain unmigrated after a successful public install command.

- Data Risk: Low application-data risk, medium local-governance-state risk because Casebook, Radar, Registry, Atlas, or runtime ledgers can stay in a legacy shape.

- Security/Compliance: No direct security issue; lifecycle auditability and release compliance are weakened when the public installer bypasses migration ledgers.

- Invariant Violated: The public hosted installer must treat complete existing Odylith installs as upgrade candidates and let the upgrade planner decide no-op versus migration, even when target and active versions match.

- Root Cause: The generated installer carried a same-version shortcut that read pin and install state, then called install instead of upgrade when both matched the release target. That shortcut predated registered same-version migration handling in upgrade_install.

- Solution: Remove the same-version shortcut from the generated install script and make the CLI install command detect complete existing consumer installs before install planning. Complete existing installs now dispatch to upgrade with `--write-pin`; incomplete or stale-uninstall residue keeps the fresh install repair path, and product-repo maintainer shape stays out of the consumer upgrade route.

- Rollback/Forward Fix: Forward fix in the hosted installer template for v0.1.14.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/test_cli.py::test_install_existing_complete_repo_routes_through_upgrade_lifecycle tests/unit/test_cli.py::test_install_dry_run_existing_complete_repo_previews_upgrade_lifecycle tests/unit/test_cli.py::test_install_product_repo_shape_does_not_route_through_consumer_upgrade tests/unit/install/test_release_bootstrap.py::test_generated_install_script_routes_complete_already_current_install_through_upgrade_lifecycle; python -m py_compile scripts/release/publish_release_assets.py.

- Prevention: Keep generated installer tests proving complete already-current installs route through upgrade, while incomplete install residue still routes through install repair.

- Regression Tests Added: tests/unit/install/test_release_bootstrap.py::test_generated_install_script_routes_complete_already_current_install_through_upgrade_lifecycle; tests/unit/test_cli.py::test_install_existing_complete_repo_routes_through_upgrade_lifecycle; tests/unit/test_cli.py::test_install_dry_run_existing_complete_repo_previews_upgrade_lifecycle; tests/unit/test_cli.py::test_install_product_repo_shape_does_not_route_through_consumer_upgrade

- Monitoring Updates: Watch hosted installer transcripts for complete existing repos and verify the terminal lifecycle line comes from upgrade rather than compact install.

- Related Incidents/Bugs: CB-064, CB-074, CB-135

- Fixed In: 0.1.14

- Code References: - scripts/release/publish_release_assets.py
- src/odylith/cli.py
- tests/unit/install/test_release_bootstrap.py
- tests/unit/test_cli.py
