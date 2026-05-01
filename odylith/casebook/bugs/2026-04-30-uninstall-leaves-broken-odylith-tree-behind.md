- Bug ID: CB-143

- Status: Fixed Pending Release

- Created: 2026-04-30

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The first 0.1.12 uninstall fix overcorrected by treating `odylith/` as disposable product output even though it is repo-local governed source truth. The second pass preserved `odylith/` but still left a race: active Claude hooks could write `.odylith/compass/standup-brief-maintenance-state.v1.json` while uninstall removed `.odylith/`, causing `OSError: Directory not empty`, and remaining project hooks then kept calling a missing launcher.

- Impact: Operators could lose Radar, Registry, Atlas, Casebook, Compass, or plan truth when uninstalling a repo-local Odylith install.

- Components Affected: migration-runtime

- Environment(s): Odylith consumer repos installed on 0.1.11 or upgraded toward 0.1.12; observed during the dentoai-isb first-run recovery lane.

- Detected By: Operator escalation during 0.1.12 recovery work

- Failure Signature: `odylith uninstall` reports that it removed `odylith/`, the consumer repo loses governed files under `odylith/` after uninstall, uninstall exits with `OSError: Directory not empty` while removing `.odylith/`, or Claude/Codex hooks print `Odylith host launcher could not find a usable launcher` after uninstall.

- Trigger Path: Run `odylith uninstall --repo-root .` after an incomplete or bad consumer install.

- Ownership: Install manager uninstall lifecycle

- Timeline: 2026-04-30: user rejected host-directory deletion prompts and then identified that removing `odylith/` was unsafe because it contains governed source truth.

- Blast Radius: All consumer repos where operators use uninstall to escape a broken Odylith install.

- SLO/SLA Impact: P1 recovery regression: uninstall could destroy governed repo truth instead of only removing local runtime state.

- Data Risk: High: `odylith/` contains governed source-of-truth records, not just generated browser output.

- Security/Compliance: Symlink-safe runtime-state removal is required, and uninstall must not follow or delete linked governed truth paths.

- Invariant Violated: Uninstall must preserve repo-owned governed truth under `odylith/`, remove disposable `.odylith/` runtime state, detach root guidance blocks, detach Odylith hook entries from host project settings, and leave already-loaded host hooks quiet after the repo is clearly uninstalled.

- Workaround: Do not manually delete `odylith/`. Remove `.odylith/` only if the runtime state must be purged outside the CLI.

- Root Cause: The recovery fix confused generated shell output inside `odylith/` with the governed source-truth tree that users must keep, then treated host project directories as preserved-but-still-active. That allowed already-loaded hooks to race `.odylith/` removal and kept hook commands live after the launcher was removed.

- Solution: Change `uninstall_bundle` so uninstall detaches root guidance, detaches Odylith hook entries from Claude/Codex project settings, marks integration disabled, removes `.odylith/` runtime state with retry tolerance for late hook writes, records the removed runtime-state path when the state root is not a symlink, preserves repo-local `odylith/` even when it is a symlink, and refuses product-repo self-uninstall. Host configuration directories are left in place, but their Odylith hook entries are disabled. The managed host launcher now no-ops silently when a repo has no launcher, no install state, and no Odylith root guidance, so already-loaded hooks do not print missing-launcher errors after uninstall.

- Rollback/Forward Fix: Forward-fix in 0.1.12; no separate purge flag.

- Verification: PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py::test_uninstall_uses_uninstall_bundle tests/unit/test_cli.py::test_uninstall_help_states_exact_scope tests/unit/test_cli.py::test_uninstall_dry_run_prints_scope_without_mutating tests/unit/test_cli.py::test_uninstall_reports_refusal_without_traceback tests/unit/install/test_host_worktree_launcher.py::test_helper_noops_after_uninstall_when_guidance_is_detached tests/unit/install/test_host_worktree_launcher.py::test_helper_reports_missing_launcher_when_guidance_is_still_active tests/integration/install/test_manager.py::test_uninstall_bundle_detaches_and_preserves_customer_odylith_tree tests/integration/install/test_manager.py::test_uninstall_bundle_retries_late_state_writes_from_active_hooks tests/integration/install/test_manager.py::test_install_and_uninstall_preserve_existing_customer_truth_tree tests/integration/install/test_manager.py::test_uninstall_bundle_preserves_symlinked_odylith_without_following_target tests/integration/install/test_manager.py::test_uninstall_bundle_unlinks_symlinked_state_root_without_following_target

- Prevention: Keep uninstall in the destructive-write scenario matrix with explicit proof for preserving `odylith/`, removing `.odylith/`, unlinking symlinked runtime state without following it, detaching Odylith hook entries while preserving host directories, and keeping post-uninstall host hooks silent when a current Claude/Codex session still has old hook commands loaded.

- Regression Tests Added: tests/unit/test_cli.py::test_uninstall_uses_uninstall_bundle; tests/unit/test_cli.py::test_uninstall_reports_refusal_without_traceback; tests/unit/install/test_host_worktree_launcher.py::test_helper_noops_after_uninstall_when_guidance_is_detached; tests/unit/install/test_host_worktree_launcher.py::test_helper_reports_missing_launcher_when_guidance_is_still_active; tests/integration/install/test_manager.py::test_uninstall_bundle_detaches_and_preserves_customer_odylith_tree; tests/integration/install/test_manager.py::test_uninstall_bundle_retries_late_state_writes_from_active_hooks; tests/integration/install/test_manager.py::test_install_and_uninstall_preserve_existing_customer_truth_tree; tests/integration/install/test_manager.py::test_uninstall_bundle_preserves_symlinked_odylith_without_following_target; tests/integration/install/test_manager.py::test_uninstall_bundle_unlinks_symlinked_state_root_without_following_target

- Monitoring Updates: Watch consumer uninstall audits for missing `odylith/` truth after uninstall and for stale `.odylith/` runtime state that should have been removed.

- Version/Build: Observed in 0.1.11 behavior; fixed pending 0.1.12.

- Customer Comms: Tell affected operators that v0.1.12 `odylith uninstall` preserves `odylith/`, removes `.odylith/`, detaches Odylith root guidance, disables Odylith host hook entries, and leaves `.claude/`, `.codex/`, and `.agents/` directories in place.

- Related Incidents/Bugs: Related to CB-139, CB-140, CB-141, and CB-142 as first-run 0.1.11 recovery failures.

- Code References: - src/odylith/install/manager.py
- src/odylith/cli.py
- tests/integration/install/test_manager.py
- tests/unit/test_cli.py
