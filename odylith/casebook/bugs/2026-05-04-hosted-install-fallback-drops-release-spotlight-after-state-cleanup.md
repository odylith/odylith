- Bug ID: CB-169

- Status: FixedPendingRelease

- Created: 2026-05-04

- Severity: P1

- Reproducibility: High

- Type: OperatorUX

- Description: Hosted install fallback drops release spotlight after state cleanup

- Impact: Operators can upgrade through hosted install, see migrations and dashboard refresh run, but get no release popup explaining the newly activated release.

- Components Affected: dashboard

- Environment(s): Consumer lane hosted install on an existing Odylith folder whose install state is incomplete or stale enough to fall back from upgrade to compact install.

- Detected By: Maintainer feedback after upgrading: the new release did not show the release pop even though install/migration activity occurred.

- Failure Signature: After curl install activates a new release through the fallback install path, odylith/index.html has no release spotlight for the new version.

- Trigger Path: curl -fsSL https://odylith.ai/install.sh | bash on an existing Odylith install where install.sh removes stale .odylith/install.json or runtime/current before invoking odylith install --version <release>.

- Ownership: Consumer upgrade release-spotlight state and hosted installer fallback cleanup.

- Timeline: 2026-05-04: Maintainer observed the release pop missing after an install/upgrade path that still ran migrations; investigation found hosted install cleanup deleted prior install state before compact install could write release spotlight state.

- Blast Radius: Existing consumer installs with incomplete state, stale uninstall residue, or migration-triggered fallback install paths.

- SLO/SLA Impact: Release comprehension and upgrade trust degrade because the shell cannot explain what changed after the upgrade-like install.

- Data Risk: No repository data loss; governed UX state loses the prior-version edge needed for release memory.

- Security/Compliance: No direct security impact.

- Invariant Violated: Any upgrade-like install that activates a new Odylith release and refreshes the dashboard must preserve the previous active version long enough to render the release spotlight; first installs remain quiet.

- Root Cause: The fallback install branch in hosted install.sh deleted .odylith/install.json and runtime/current before running odylith install, and the install CLI treated the path as first install, so activation_history stayed single-version and build_release_spotlight rejected the payload.

- Solution: Carry ODYLITH_INSTALL_PREVIOUS_ACTIVE_VERSION from hosted install cleanup into the install CLI, repair activation_history for upgrade-like fallback installs, write release-upgrade-spotlight before dashboard refresh, and align the server-side spotlight lifetime with the 30-minute browser contract.

- Rollback/Forward Fix: Forward fix only; do not delete release spotlight gating or show popups for first installs.

- Verification: Focused tests prove hosted fallback install preserves prior version, writes release-upgrade-spotlight, repairs activation_history, refreshes dashboard, and still routes complete installs through upgrade.

- Prevention: Keep previous-version preservation in install.sh decision tests and CLI fallback tests; do not allow cleanup of install state to erase upgrade UX state.

- Agent Guardrails: When install triggers migrations or activates a new release, check both version state and release spotlight state before claiming dashboard refresh is complete.

- Preflight Checks: Inspect .odylith/runtime/release-upgrade-spotlight.v1.json, .odylith/install.json activation_history, and tooling-payload release_spotlight after hosted install fallback rehearsals.

- Regression Tests Added: tests/unit/test_cli.py::test_install_fallback_preserves_upgrade_spotlight_after_hosted_state_cleanup; tests/unit/install/test_release_bootstrap.py hosted install decision assertions; tests/unit/runtime/test_shell_onboarding.py spotlight lifetime assertion.

- Monitoring Updates: Release migration gate and generated change manifest should treat install-managed asset changes plus browser-surface spotlight proof as release-blocking.

- Version/Build: v0.1.14 post-release fixes

- Config/Flags: ODYLITH_INSTALL_PREVIOUS_ACTIVE_VERSION, ODYLITH_INSTALL_COMPACT, ODYLITH_BOOTSTRAP_RUNTIME_PRESTAGED

- Customer Comms: Tell operators the next patch preserves the release popup even when install has to clean stale state and fall back to compact install.

- Related Incidents/Bugs: Related to CB-051 upgrade spotlight live refresh and CB-168 dashboard version drift recovery.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.14

- Public Response: pending

- Code References: - src/odylith/cli.py
- scripts/release/publish_release_assets.py
- src/odylith/runtime/surfaces/shell_onboarding.py
- tests/unit/test_cli.py
- tests/unit/install/test_release_bootstrap.py
- tests/unit/runtime/test_shell_onboarding.py
