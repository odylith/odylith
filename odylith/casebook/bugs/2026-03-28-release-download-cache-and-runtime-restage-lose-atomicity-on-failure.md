- Bug ID: CB-015

- Status: Open

- Created: 2026-03-28

- Severity: P1

- Reproducibility: Intermittent

- Type: Product

- Description: Verified release downloads and same-version runtime restaging
  were still too fragile under interruption: release-asset downloads lacked a
  bounded retry loop and same-version restaging could discard the existing
  staged runtime before the replacement tree had been built successfully.

- Impact: First install, repair, or upgrade could fail harder than necessary on
  transient network issues, and an interrupted or failed same-version restage
  could leave the target version directory missing instead of preserving the
  last good local runtime until the replacement was ready.

- Components Affected: `src/odylith/install/release_assets.py`,
  `src/odylith/install/runtime.py`, install-state file writes, local release
  smoke coverage.

- Environment(s): Consumer install/upgrade/repair flows and maintainer local
  hosted-asset rehearsals.

- Root Cause: The verified asset path buffered downloads eagerly and retried
  nothing in the Python release-fetch layer, while runtime restage used a
  delete-then-extract posture instead of staging a full replacement beside the
  current tree first.

- Solution: Stream downloads to temporary files, retry bounded transient
  network failures, commit cache/state files atomically, and stage replacement
  runtimes beside the current version before swapping them into place.

- Verification: Added regression coverage for transient-download retry,
  temporary-file cleanup, and preserving an existing staged runtime when
  restaging fails before replacement.

- Prevention: Keep verified install/update paths atomic by default. Cache
  writes, state writes, and runtime replacement should all prefer stage-then-
  swap over destructive in-place mutation.

- Detected By: Final relaunch hardening pass on
  `2026/freedom/release-reset-runtime-footprint`.

- Failure Signature: Transient `URLError`/timeout conditions aborted the
  verified asset path immediately, and a same-version restage failure after
  target cleanup could leave `.odylith/runtime/versions/<version>` absent.

- Trigger Path: `odylith install`, `odylith upgrade`, `odylith doctor
  --repair`, or release-proof rehearsal under transient network failure or a
  failed restage of an already named local runtime version.

- Ownership: Install/runtime reliability contract.

- Timeline: The relaunch slice already enforced verification and layered
  transport; this follow-on hardening pass closed the remaining atomicity gap
  in the download/cache/restage path.

- Blast Radius: First install, pinned upgrade, repair, and release rehearsal.

- SLO/SLA Impact: Reliability and recovery posture degrade under network or
  local-restage failure.

- Data Risk: Low but real. A failed restage could unnecessarily discard the
  previously staged runtime for the same version.

- Security/Compliance: Atomic verified writes reduce ambiguity around cached
  assets and state files after interrupted downloads.

- Invariant Violated: Verified install/update should never destructively remove
  the current target before the replacement is fully staged and validated.

- Workaround: Re-run the command. The forward fix now makes the path safer and
  more recoverable.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not revert to delete-first restaging or direct
  non-atomic writes for install-critical metadata.

- Preflight Checks: Inspect the Install and Upgrade runbook plus the Release
  component spec before changing verified download or runtime swap behavior.

- Regression Tests Added: `tests/unit/install/test_release_assets.py`,
  `tests/unit/install/test_runtime.py`

- Monitoring Updates: None.

- Related Incidents/Bugs: `2026-03-28-full-stack-managed-runtime-payloads-are-too-large-for-install-and-upgrade.md`

- Version/Build: Relaunch source line targeting restarted preview `v0.1.0`.

- Config/Flags: None.

- Customer Comms: None.

- Code References: `src/odylith/install/fs.py`,
  `src/odylith/install/release_assets.py`,
  `src/odylith/install/runtime.py`,
  release-preflight local smoke coverage

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
