- Bug ID: CB-339

- Status: Open

- Created: 2026-08-18

- Severity: P2

- Reproducibility: Always

- Type: Test

- Description: The shared browser fixture serves the repository root but does not provision the dynamic odylith-version-state.v1.js required by the shell. The primary checkout happens to contain that ignored runtime file; a detached source-local worktree does not. Long-running Radar browser tests therefore emit repeated 404s and fail despite correct rendered content.

- Impact: Operational release risk: canonical detached-worktree validation depends on unrelated mutable state from another checkout and fails late in the browser shard.

- Components Affected: dashboard

- Environment(s): Odylith product-repo detached source-local worktree browser matrix

- Detected By: canonical shard 2 continuation after Atlas freshness settlement

- Failure Signature: test_radar_execution_wave_summary_avoids_dead_side_lane_in_browser sees two 404s for /.odylith/runtime/odylith-version-state.v1.js and fails clean-page assertion.

- Trigger Path: make dev-validate -> shared browser_context static server -> tooling shell live version-state load

- Ownership: Shared browser integration fixture and tooling dashboard version-state owner

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: All browser tests whose runtime lasts long enough for the shell version-state request or retry.

- SLO/SLA Impact: Full detached source-local validation cannot complete reproducibly without manual hidden-state provisioning.

- Data Risk: No application data loss; test hermeticity and release-proof attribution are compromised.

- Security/Compliance: Security and compliance posture remain fail-closed; the fix must generate only the normal local runtime view and must not suppress arbitrary 404s.

- Invariant Violated: Browser integration tests must provision every required local runtime input through the product owner and must not depend on ignored state from a maintainer checkout.

- Root Cause: surface_browser_test_support serves REPO_ROOT directly but does not call tooling_dashboard_version_state.persist_version_state when the ignored runtime view is absent.

- Solution: Provision the exact version-state JSON/JS through persist_version_state before starting the shared static server when the file is absent; retain strict clean-page handling for real 404s.

- Rollback/Forward Fix: Forward-fix test fixture setup; do not copy mutable bytes from the primary checkout or suppress the missing request.

- Verification: Run the exact Radar browser node in a worktree without the version-state files, the full browser layout audit, then canonical shards.

- Prevention: Keep browser fixtures hermetic by creating dynamic local inputs through their owning runtime builders.

- Agent Guardrails: Do not whitelist the 404, copy another checkout state, or weaken clean-page assertions.

- Preflight Checks: Confirm the root checkout has the ignored file while the detached worktree does not; prove the runtime owner can generate it locally.

- Regression Tests Added: The exact long-running Radar browser node becomes the regression proof in a detached worktree.

- Related Incidents/Bugs: CB-338

- Code References: - tests/integration/runtime/surface_browser_test_support.py
- src/odylith/runtime/surfaces/tooling_dashboard_version_state.py
- tests/integration/runtime/test_surface_browser_layout_audit.py
