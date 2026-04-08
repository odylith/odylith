- Bug ID: CB-063

- Status: Open

- Created: 2026-04-07

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Successful consumer install and upgrade can still fail at the
  retention-cleanup tail when an older staged runtime under
  `.odylith/runtime/versions/` contains read-only directories or files. The new
  runtime is already activated, but pruning the stale version raises
  `PermissionError` and turns a healthy upgrade into a reported failure.

- Impact: Operators on macOS Apple Silicon and any repo with read-only stale
  runtime trees can leave a successful activation believing the install failed.
  Cleanup tax blocks the happy path and can strand the repo in a confusing
  partially-upgraded narrative even though the active runtime is healthy.

- Components Affected: `src/odylith/install/manager.py`, retention cleanup for
  `.odylith/runtime/versions/` and `.odylith/cache/releases/`, hosted installer
  finish path, upgrade and reinstall lifecycle closeout.

- Environment(s): Consumer repos upgrading from an older pinned runtime where
  stale retained runtime trees include read-only directories or files.

- Root Cause: Runtime retention cleanup uses plain `shutil.rmtree` and
  `Path.unlink()` on stale runtime and cache entries. Permission-fix retries and
  best-effort cleanup semantics are missing even though retention cleanup is
  post-activation housekeeping rather than the critical proof path.

- Solution: Make retention cleanup best-effort. Retry removal through a narrow
  permission-fix handler for read-only paths, keep the new active runtime live
  even if stale cleanup still cannot finish, and surface exact remediation for
  any leftover paths instead of failing the whole lifecycle.

- Verification: Install-manager tests should prove read-only stale runtime trees
  no longer fail upgrade or reinstall and that retained-path remediation is
  surfaced when cleanup still cannot complete.

- Prevention: Post-activation retention cleanup must never be able to overturn a
  verified healthy runtime activation.

- Detected By: Real downstream consumer upgrade from `0.1.7` to `0.1.9` on
  2026-04-07 via the hosted installer.

- Failure Signature: `PermissionError` while pruning
  `.odylith/runtime/versions/<old-version>` after the new runtime already
  activated successfully.

- Trigger Path: `_prune_runtime_retention` during install, upgrade, reinstall,
  and repair state persistence.

- Ownership: install lifecycle closeout and runtime retention policy.

- Timeline: Earlier runtime hardening tightened side-by-side staging and
  rollback retention, but cleanup still assumes stale retained trees are fully
  writable.

- Blast Radius: Hosted installer reliability, upgrade confidence, and operator
  time spent recovering from a non-critical cleanup failure.

- SLO/SLA Impact: Medium operator-blocking impact on the main install path.

- Data Risk: Low.

- Security/Compliance: Cleanup should stay strict about what is retained, but it
  should not fail healthy activation over stale read-only residue.

- Invariant Violated: A verified successful runtime activation must not be
  reported as failed because stale retention cleanup could not remove an old
  tree.

- Workaround: Manually `chmod -R u+w` the stale runtime tree under
  `.odylith/runtime/versions/` and remove it, then rerun the lifecycle command.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Keep cleanup best-effort only for stale non-active targets;
  do not weaken verification or activation proof for the active runtime.

- Preflight Checks: Inspect current retention cleanup, upgrade/reinstall
  closeout, and existing retention tests before widening the delete path.

- Regression Tests Added:
  `tests/integration/install/test_manager.py`

- Monitoring Updates: Watch hosted installer and upgrade logs for retained-path
  remediation warnings after the best-effort cleanup lands.

- Residual Risk: Other filesystem edge cases may still need explicit cleanup
  policy later.

- Related Incidents/Bugs:
  [CB-003](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-first-install-and-same-version-upgrade-mutate-live-runtime-before-fail-closed-proof.md),
  [CB-005](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md)

- Version/Build: Odylith `0.1.9` observed on 2026-04-07 during downstream
  hosted-install upgrade from `0.1.7`.

- Config/Flags: Default hosted installer and retention cleanup path.

- Customer Comms: The new runtime activated correctly, but stale cleanup could
  still fail too loudly. The fix keeps the active runtime trustworthy and turns
  old-tree cleanup into a recoverable warning with exact remediation.

- Code References: `src/odylith/install/manager.py`,
  `tests/integration/install/test_manager.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
