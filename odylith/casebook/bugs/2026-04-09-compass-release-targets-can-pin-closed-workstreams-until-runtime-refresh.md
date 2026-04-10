- Bug ID: CB-081

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: After release source truth removes a finished workstream from
  active targeting, Compass can keep rendering that workstream in `Release
  Targets` with stale `implementation` status and `0% progress` until
  `odylith/compass/runtime/current.v1.json` is explicitly refreshed. The same
  bug class also let execution-wave progress chips coerce missing
  `progress_ratio` into synthetic `0%` across Compass and Radar backlog
  summaries. On 2026-04-09, source truth already showed `release-0-1-11`
  targeting `B-068` and listing `B-067` as completed, but the visible Compass
  runtime snapshot still targeted `B-067` and omitted it from the completed
  section.

- Impact: The operator sees the exact opposite of the release-membership truth
  we intended to preserve in `B-066`: a closed workstream remains visually
  active while the true active member disappears. That is both a release-truth
  bug and a stale-runtime trust bug.

- Components Affected: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/`,
  `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  Compass release-target rendering, Compass execution-wave chips, Radar
  execution-wave summaries, shell runtime-status disclosure.

- Environment(s): Maintainer and consumer surface lanes where release source
  truth changed but the current Compass runtime snapshot has not yet been
  rewritten.

- Root Cause: Compass release rendering trusted the last generated runtime
  snapshot wholesale. That snapshot can lag the live traceability release read
  model after closeout, so stale `current_workstreams`, release membership, and
  plan progress values remain visible until a full Compass refresh rewrites the
  runtime payload. Separately, progress-rendering paths in Compass and Radar
  used `Number(...)` coercion on possibly-missing `plan.progress_ratio`, which
  silently turned unknown into `0`. Shell and sync proof could acknowledge
  generic staleness, but they did not specifically detect or reconcile this
  source-truth drift.

- Solution: Add a shared Compass runtime/source-truth drift detector, reconcile
  release-target and current-workstream views against the live traceability
  graph when the runtime snapshot is behind, surface the mismatch through
  Compass, shell runtime-status, and sync guidance instead of silently trusting
  the stale snapshot, and treat missing `progress_ratio` as unknown rather than
  coercing it to `0` in release-target and execution-wave views.

- Verification: `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_tooling_dashboard_surface_status.py tests/unit/runtime/test_context_engine_release_resolution.py` passed (`13 passed`). `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_backlog_ui.py` passed (`26 passed`). `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_surface_shell_contracts.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_backlog_ui.py` passed (`90 passed`). `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py::test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale tests/integration/runtime/test_surface_browser_layout_audit.py::test_compass_release_targets_keep_single_column_board_layout_in_browser tests/integration/runtime/test_surface_browser_layout_audit.py::test_compass_release_targets_keep_single_column_board_layout_in_compact_browser tests/integration/runtime/test_surface_browser_smoke.py -k release_targets` passed (`3 passed`). `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --runtime-mode standalone --proceed-with-overlap` passed. `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone` passed.

- Prevention: High-churn Compass runtime payloads must not silently outrank
  fresher governed release source truth for active-versus-completed membership,
  and unknown plan progress must not be coerced into `0%` in any shared
  release or execution-wave readout.

- Detected By: Manual Compass review against current release source truth on
  2026-04-09.

- Failure Signature: `odylith/radar/traceability-graph.v1.json` shows
  `release-0-1-11` with `active_workstreams = ["B-068"]` and
  `completed_workstreams = ["B-061", "B-062", "B-063", "B-067"]`, while
  `odylith/compass/runtime/current.v1.json` still shows
  `active_workstreams = ["B-067"]` and renders `B-067` as `implementation`
  with `0% progress`. Parallel execution-wave views can render `0%` when
  `plan.progress_ratio` is absent rather than truly zero.

- Trigger Path: 1. Close or remove a finished workstream from the current
  release. 2. Refresh or validate only source truth and generated governance
  artifacts. 3. Open Compass without rewriting the current runtime snapshot.

- Ownership: Compass runtime truth contract, Dashboard shell stale-runtime
  posture, sync guidance for visible Compass runtime drift.

- Timeline: This surfaced immediately after `B-067` closeout; release source
  truth was correct, but the visible Compass runtime snapshot still reflected
  the pre-closeout state.

- Blast Radius: Any release closeout or release-target audit that relies on
  Compass or shell-embedded Compass without first forcing a fresh Compass
  runtime rewrite.

- SLO/SLA Impact: No outage, but direct operator-trust damage on a key release
  control surface.

- Data Risk: Low source-of-truth corruption risk; high read-model trust risk.

- Security/Compliance: None directly.

- Invariant Violated: Compass must not render a finished removed workstream as
  an active release target when fresher release source truth already says
  otherwise.

- Workaround: Run `odylith compass refresh --repo-root .` and reload the
  Compass frame. That is not sufficient as the default product contract because
  the stale state is currently silent.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When release source truth and Compass runtime disagree,
  fail closed to source truth or explicitly disclose the drift; do not let the
  stale runtime snapshot narrate active release membership as if it were
  current.

- Preflight Checks: Reopen `B-066`, inspect `odylith/radar/traceability-graph.v1.json`,
  `odylith/compass/runtime/current.v1.json`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js`,
  `src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py`, and the
  current Compass/Dashboard component specs.

- Regression Tests Added: `tests/unit/runtime/test_release_truth_runtime.py`, `tests/unit/runtime/test_compass_dashboard_shell.py`, `tests/unit/runtime/test_render_backlog_ui.py`, `tests/unit/runtime/test_tooling_dashboard_surface_status.py`, `tests/unit/runtime/test_context_engine_release_resolution.py`, `tests/integration/runtime/test_surface_browser_deep.py`, `tests/integration/runtime/test_surface_browser_layout_audit.py`, `tests/integration/runtime/test_surface_browser_smoke.py`.

- Monitoring Updates: Watch for any case where live traceability release
  membership differs from the visible Compass runtime snapshot, especially when
  the stale snapshot still lists a finished removed workstream as active, and
  any case where missing progress reappears as `0%` in release or
  execution-wave views.

- Residual Risk: No active blocker remains in this slice. Future regressions
  would most likely come from live-vs-bundle surface drift or a new progress
  renderer bypassing the shared unknown-progress contract.

- Related Incidents/Bugs:
  [2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md](2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md)
  [2026-04-08-explicit-compass-full-refresh-can-pass-with-deterministic-or-stale-runtime-state.md](2026-04-08-explicit-compass-full-refresh-can-pass-with-deterministic-or-stale-runtime-state.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Visible in normal Compass runtime loads when source-truth
  closeout happened without a fresh Compass runtime rewrite.

- Customer Comms: Tell operators that Compass will no longer silently reuse a
  stale active release-membership view when current source truth has already
  moved the workstream into completed release history.

- Code References: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js`,
  `src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/maintainer/AGENTS.md`

- Fix Commit/PR: Pending.
