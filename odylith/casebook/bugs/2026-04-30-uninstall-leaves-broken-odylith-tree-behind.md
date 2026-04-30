- Bug ID: CB-143

- Status: Open

- Created: 2026-04-30

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The existing uninstall command only detached root guidance and left the repo-local odylith/ tree in place, so failed 0.1.11 installs could still show stale or empty browser surfaces after uninstall.

- Impact: Operators who uninstall after a bad first-run install still see odylith/index.html and dashboard files in the repo, making the product appear installed and broken.

- Components Affected: migration-runtime

- Environment(s): Odylith consumer repos installed on 0.1.11 or upgraded toward 0.1.12; observed during the dentoai-isb first-run recovery lane.

- Detected By: Operator escalation during 0.1.12 recovery work

- Failure Signature: `odylith uninstall` reported detachment but preserved `odylith/`, including empty or stale browser surfaces.

- Trigger Path: Run `odylith uninstall --repo-root .` after an incomplete or bad consumer install.

- Ownership: Install manager uninstall lifecycle

- Timeline: 2026-04-30: user rejected a separate purge UX and required the existing uninstall command to delete `odylith/`.

- Blast Radius: All consumer repos where operators use uninstall to escape a broken Odylith install.

- SLO/SLA Impact: P1 onboarding recovery regression: uninstall did not remove the visible broken product tree.

- Data Risk: Medium: uninstall now intentionally removes repo-local Odylith governance truth under `odylith/`.

- Security/Compliance: Symlink-safe removal is required so uninstall does not follow a linked `odylith/` target outside the repo.

- Invariant Violated: Uninstall must remove the visible installed Odylith tree, not merely turn off guidance while broken browser surfaces remain.

- Workaround: Before 0.1.12, manually remove `odylith/` after uninstall if the repo must look clean.

- Root Cause: The uninstall implementation only called root-guidance detach and set install state to detached, preserving customer truth and local state by design.

- Solution: Change `uninstall_bundle` so uninstall detaches root guidance, marks integration disabled, removes the repo-local `odylith/` entry, records the removed path in the install ledger, and refuses product-repo self-uninstall.

- Rollback/Forward Fix: Forward-fix in 0.1.12; no separate purge flag.

- Verification: PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py::test_uninstall_uses_uninstall_bundle tests/unit/test_cli.py::test_uninstall_reports_refusal_without_traceback tests/integration/install/test_manager.py::test_uninstall_bundle_detaches_and_removes_customer_odylith_tree tests/integration/install/test_manager.py::test_install_and_uninstall_remove_existing_customer_truth_tree tests/integration/install/test_manager.py::test_uninstall_bundle_unlinks_symlinked_odylith_without_following_target

- Prevention: Keep uninstall in the destructive-write scenario matrix with explicit proof for removing `odylith/` and unlinking symlinked targets without following them.

- Regression Tests Added: tests/unit/test_cli.py::test_uninstall_uses_uninstall_bundle; tests/unit/test_cli.py::test_uninstall_reports_refusal_without_traceback; tests/integration/install/test_manager.py::test_uninstall_bundle_detaches_and_removes_customer_odylith_tree; tests/integration/install/test_manager.py::test_install_and_uninstall_remove_existing_customer_truth_tree; tests/integration/install/test_manager.py::test_uninstall_bundle_unlinks_symlinked_odylith_without_following_target

- Monitoring Updates: Watch consumer uninstall audits for any remaining `odylith/` tree after uninstall.

- Version/Build: Observed in 0.1.11 behavior; fixed pending 0.1.12.

- Customer Comms: Tell affected operators that v0.1.12 `odylith uninstall` removes the visible local `odylith/` tree while keeping `.odylith/` launcher and audit state.

- Related Incidents/Bugs: Related to CB-139, CB-140, CB-141, and CB-142 as first-run 0.1.11 recovery failures.

- Code References: - src/odylith/install/manager.py
- src/odylith/cli.py
- tests/integration/install/test_manager.py
- tests/unit/test_cli.py
