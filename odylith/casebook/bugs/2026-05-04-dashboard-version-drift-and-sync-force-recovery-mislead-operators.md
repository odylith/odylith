- Bug ID: CB-168

- Status: FixedPendingRelease

- Fixed: Pending

- Fixed In: 0.1.14

- Created: 2026-05-04

- Severity: P0

- Reproducibility: High

- Type: Tooling

- Description: After upgrade, odylith version can report the new active release while the generated dashboard shell still renders the prior version. The hosted install path can make this ambiguous because a complete existing install routes through upgrade, while incomplete or legacy installs can run repo-state migrations inside install without an obvious dashboard-refresh settlement. A failed odylith sync --force path can also block on dirty overlap after beginning tracked sync preflight work, then recommend the broad --proceed-with-overlap path instead of the narrow dashboard refresh that resolves visible shell drift.

- Impact: Operators cannot trust the human-facing dashboard as install-state evidence after upgrade, and recovery guidance nudges them toward a broader write path than needed.

- Components Affected: dashboard

- Environment(s): Consumer lane upgrade from v0.1.13 to v0.1.14 with generated dashboard surfaces and a dirty governed worktree.

- Detected By: Operator feedback from a consumer upgrade where odylith version reported 0.1.14 while the dashboard shell still showed v0.1.13.

- Failure Signature: odylith version reports 0.1.14; odylith/index.html toolbar still renders v0.1.13; hosted install output says an existing install or migration ran but does not make the upgrade/refresh handoff obvious; odylith sync --force blocks on dirty-overlap entries and recommends odylith sync --proceed-with-overlap instead of dashboard refresh.

- Trigger Path: Run odylith upgrade or hosted install against an existing, incomplete, or legacy-migrating consumer install, open odylith/index.html, then run odylith version and odylith sync --force during recovery.

- Ownership: Tooling dashboard renderer, install/upgrade dashboard refresh handoff, and governed sync dirty-overlap guard.

- Timeline: Captured 2026-05-04 from consumer-lane upgrade feedback after v0.1.14 dashboard version mismatch and sync force recovery confusion.

- Blast Radius: All upgraded consumer repos with stale generated dashboard assets or broad dirty-overlap worktrees.

- SLO/SLA Impact: No service outage, but upgrade recovery confidence and governance-memory trust are degraded.

- Data Risk: Generated dashboard truth can misreport authoritative runtime version; sync guard ordering can create partial tracked churn before refusing to proceed.

- Security/Compliance: No credential exposure; governance trust posture is weakened because stale generated UI looks authoritative.

- Invariant Violated: The dashboard must not silently drift from odylith version, and guarded write commands must block before tracked mutation or explicitly report partial writes.

- Workaround: Run odylith dashboard refresh --repo-root . --force to refresh the shell without broad governance sync overlap acknowledgement.

- Root Cause: Upgrade refresh could reuse generated surface fingerprints instead of forcing the shell render, the shell had no runtime version sidecar to detect drift, install output did not clearly distinguish upgrade routing from migration-only install repair, install-time repo-state migrations did not always force a dashboard refresh when first-run surfaces already existed, and sync normalized Radar source before dirty-overlap blocking.

- Solution: Persist a runtime version-state sidecar sourced from odylith version, have the dashboard warn when rendered shell version differs, force dashboard refresh after upgrade, force dashboard refresh after install-time repo-state migration activity, make complete-install routing explicitly say it is running the upgrade lifecycle and refreshing dashboard surfaces, and move sync dirty-overlap blocking before tracked Radar normalization with narrow dashboard refresh guidance.

- Rollback/Forward Fix: Forward fix in v0.1.14 post-release fixes; do not relax dirty-overlap safety and do not restore broad recovery guidance for shell-only drift.

- Verification: Focused unit proof covers start compact output, upgrade dashboard refresh force, sync dirty-overlap pre-mutation block, tooling payload version sidecar, and dashboard stale-version control logic.

- Prevention: Keep upgrade refresh force coverage, stale-version sidecar tests, and dirty-overlap pre-mutation tests in the release gate.

- Agent Guardrails: When diagnosing dashboard drift, compare odylith version against generated shell payload before recommending broad sync recovery.

- Preflight Checks: Search existing Casebook bugs for dashboard stale, version drift, and sync dirty-overlap before capture.

- Regression Tests Added: tests/unit/test_cli.py, tests/unit/install/test_release_bootstrap.py, tests/unit/runtime/test_sync_cli_compat.py, tests/unit/runtime/test_render_tooling_dashboard.py, tests/unit/runtime/test_tooling_dashboard_runtime_builder.py

- Monitoring Updates: Dashboard runtime status now surfaces stale shell version with source, shell generated timestamp, and the narrow force refresh command.

- Version/Build: v0.1.14 post-release fixes branch

- Config/Flags: odylith dashboard refresh --repo-root . --force

- Customer Comms: Release notes should call out safer post-upgrade dashboard refresh and stale-version detection.

- Related Incidents/Bugs: Related: CB-167

- GitHub Status: needs_info

- Public Response: pending

- Code References: - src/odylith/runtime/surfaces/tooling_dashboard_version_state.py
- src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js
- src/odylith/runtime/governance/sync_workstream_artifacts.py
- src/odylith/cli.py
- scripts/release/publish_release_assets.py
