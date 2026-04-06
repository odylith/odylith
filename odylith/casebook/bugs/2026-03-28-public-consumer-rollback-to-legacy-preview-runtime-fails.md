- Bug ID: CB-014

- Status: Open

- Created: 2026-03-28

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: Hosted consumer rehearsal for the abandoned Odylith `v0.1.1`
  prelaunch drill failed on the rollback step when the previous installed
  version was the legacy wrapped preview runtime from `v0.1.0`.

- Impact: The abandoned rehearsal line did not prove the full
  upgrade-plus-rollback contract from `v0.1.0` to `v0.1.1`, even though first
  install and managed-runtime upgrade succeeded.

- Components Affected: `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, maintainer rehearsal lane,
  `bin/consumer-rehearsal`, launcher/runtime trust boundary.

- Environment(s): hosted prelaunch consumer install rehearsal on macOS (Apple
  Silicon), upgrade from hosted `v0.1.0` assets to hosted `v0.1.1` assets,
  rollback to the previous preview runtime.

- Root Cause: The launcher trust check resolved the rollback target
  `.odylith/runtime/versions/<version>/bin/python` symlink before deciding
  whether it stayed inside `.odylith/runtime/versions/`. Legacy preview
  runtimes created from a venv therefore resolved to the underlying machine
  interpreter path outside the runtime tree and were rejected, even though the
  repo-local runtime path itself was correct and isolated under `.odylith/`.

- Solution: Trust the repo-local runtime executable path under
  `.odylith/runtime/versions/<version>/bin/` as the launcher fallback reference
  when that path itself is inside the trusted runtime tree, even if the legacy
  venv symlink resolves to the underlying interpreter outside the tree. Keep
  direct host-Python fallback disallowed for consumer repos and preserve the
  managed-runtime contract for current previews.

- Verification: Source fix and focused regression tests are landed locally in
  `tests/unit/install/test_runtime.py` and
  `tests/integration/install/test_manager.py`. The bug remains open until the
  restarted preview line proves consumer rehearsal from hosted assets.

- Prevention: Preserve repo-local launcher references for legacy wrapped
  runtimes, keep direct host-Python fallback blocked for consumer repos, and
  keep consumer rehearsal proving both current-preview and legacy-preview
  upgrade/rollback boundaries.

- Detected By: Hosted prelaunch consumer rehearsal against the abandoned
  `v0.1.1` drill assets.

- Failure Signature: `launcher fallback python must stay inside
  \`.odylith/runtime/versions/\` unless host-python fallback is explicitly
  allowed`

- Trigger Path: `make consumer-rehearsal VERSION=0.1.1 PREVIOUS_VERSION=0.1.0`

- Ownership: Release/install runtime activation and rollback contract.

- Timeline: The abandoned `v0.1.1` prelaunch drill cut successfully with
  managed-runtime bundles and restored the product repo to pinned dog-food
  posture, but hosted consumer rehearsal then failed on rollback to the legacy
  `v0.1.0` wrapped runtime.

- Blast Radius: Any consumer repo attempting a preview rollback from
  `v0.1.1` to the legacy `v0.1.0` preview runtime.

- SLO/SLA Impact: Preview upgrade credibility and backward-compat proof remain
  incomplete until the forward fix is shipped on the restarted preview line and
  rehearsed.

- Data Risk: None.

- Security/Compliance: The existing guardrail is directionally correct, but the
  pre-fix implementation was too strict and rejected a repo-local legacy
  runtime path that remained isolated under `.odylith/`. The forward fix must
  preserve the ban on arbitrary host-Python fallback for consumer repos.

- Invariant Violated: Consumer rollback should accept a repo-local legacy
  preview runtime path under `.odylith/runtime/versions/` without relaxing the
  host-Python boundary for normal consumer operation.

- Workaround: None for the abandoned `v0.1.1` drill beyond avoiding rollback
  to `v0.1.0` after upgrade.

- Rollback/Forward Fix: Forward fix in the restarted preview release.

- Agent Guardrails: Do not let this compatibility fix reintroduce general
  host-Python fallback for consumer repos. Keep launcher/runtime trust anchored
  to repo-local paths under `.odylith/runtime/versions/`.

- Preflight Checks: Inspect this bug, the active B-005 plan, and the Release
  plus Odylith component specs before touching rollback/launcher trust logic.

- Regression Tests Added: `tests/unit/install/test_runtime.py`,
  `tests/integration/install/test_manager.py`.

- Monitoring Updates: Consumer rehearsal should cover both the current preview
  path and the legacy `v0.1.0` compatibility boundary until the restarted
  preview line is fully stabilized.

- Related Incidents/Bugs:
  `2026-03-28-public-consumer-install-depends-on-machine-python.md`

- Version/Build: Abandoned prelaunch `v0.1.1` drill assets.

- Config/Flags:
  `make consumer-rehearsal VERSION=0.1.1 PREVIOUS_VERSION=0.1.0`

- Customer Comms: No canonical public release should claim full rollback proof
  until the restarted preview line includes this forward fix and restores full
  hosted consumer rehearsal evidence.

- Code References: `src/odylith/install/runtime.py`,
  `src/odylith/install/manager.py`, `bin/consumer-rehearsal`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
