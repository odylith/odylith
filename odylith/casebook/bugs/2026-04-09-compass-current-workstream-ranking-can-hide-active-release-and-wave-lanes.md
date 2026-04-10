- Bug ID: CB-094

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass `Current Workstreams` could hide the very lanes that
  were actively targeted in the current release or active execution wave.
  Status-first row selection let older generic `implementation` rows consume
  the twelve-card cap before active current-release or active-wave rows like
  `B-072`, `B-073`, and `B-079` could surface.

- Impact: Operators could miss the active execution program lane even when the
  release target set and execution-wave truth were correct. Compass looked
  fickle because the release bar, timeline, and current-workstream cards could
  disagree about what was actually in flight.

- Components Affected: `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_current_workstreams_runtime.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  current-workstream ranking, release-target visibility, and execution-wave
  promotion inside Compass.

- Environment(s): Odylith product-repo maintainer mode and any Compass runtime
  with more candidate workstreams than the twelve-card current-workstream cap.

- Root Cause: The current-workstream selector treated plain
  `implementation`/`planning` status as a first-class inclusion rule, then
  truncated to a fixed cap without ranking current release membership or active
  wave membership ahead of older status-only rows. That made queued but truly
  active wave rows especially vulnerable to eviction.

- Solution: Move current-workstream ranking into a dedicated selector that
  explicitly scores active-wave membership, current-release membership, active
  release posture, recent verified activity, recent completion, and promoted
  default scope above status-only rows before applying the visible-row cap.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_refresh_contract.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_compass_transaction_runtime.py tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_surface_projection_fingerprint.py tests/unit/runtime/test_compass_current_workstreams_runtime.py tests/unit/runtime/test_compass_governance_source_runtime.py`
    passed (`92 passed`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py::test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_checklist_label_instead_of_fake_zero_progress tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_tracked_execution_percent_for_partial_progress`
    passed (`3 passed`)
  - `PYTHONPATH=src python3 -m odylith.cli compass refresh --repo-root . --wait`
    passed, and the refreshed `odylith/compass/runtime/current.v1.json`
    includes `B-072`, `B-073`, and `B-079` in `current_workstreams`

- Prevention: Compass must rank live release and active-wave truth ahead of
  older generic status rows whenever a capped visible current-workstream set is
  being chosen.

- Detected By: User review of Compass after active execution-governance lanes
  did not appear in `Current Workstreams`.

- Failure Signature: `release_summary.current_release.active_workstreams`
  includes active lanes, but the visible `current_workstreams` list omits one
  or more of them while showing older generic implementation rows instead.

- Trigger Path: 1. Put more than twelve candidate workstreams into the Compass
  catalog. 2. Mark some lanes as current-release or active-wave work. 3. Let
  older status-only rows remain in the catalog. 4. Open Compass current
  workstreams.

- Ownership: Compass current-workstream promotion and ranking policy.

- Timeline: This showed up at the same time as the `B-072` execution-governance
  program rollout because `B-073` and `B-079` were active under the wave
  program but still `queued` in their idea metadata.

- Blast Radius: Any capped Compass current-workstream view with mixed
  implementation history, queued active-wave members, and current-release
  targeting.

- SLO/SLA Impact: No outage, but a direct prioritization/readout regression on
  the execution surface.

- Data Risk: Low source-corruption risk; medium-high operator-readout
  integrity risk.

- Security/Compliance: None directly.

- Invariant Violated: Compass must not hide a current-release or active-wave
  lane behind older generic implementation rows.

- Workaround: Manually inspect release targets and execution-wave cards to
  reconstruct what should have been in `Current Workstreams`. That is not
  acceptable product behavior.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: If a workstream is current-release or active-wave work, it
  belongs at the front of the visible current-workstream selection unless a
  stronger real-time execution signal outranks it.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_current_workstreams_runtime.py`, and
  the runtime payload selection call site in
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`.

- Regression Tests Added: `tests/unit/runtime/test_compass_current_workstreams_runtime.py`,
  `tests/unit/runtime/test_compass_governance_source_runtime.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`.

- Monitoring Updates: Watch for any runtime payload where
  `release_summary.current_release.active_workstreams` contains ids that are
  absent from `current_workstreams` despite a modest current-workstream cap.

- Residual Risk: Very crowded portfolios can still force a visible cap, but
  active release and active-wave rows now outrank passive status-only rows.

- Related Incidents/Bugs:
  [2026-04-09-low-signal-governance-churn-can-outrank-real-execution-across-governance-surfaces.md](2026-04-09-low-signal-governance-churn-can-outrank-real-execution-across-governance-surfaces.md)
  [2026-04-09-compass-timeline-audit-cards-can-hide-their-own-anchor-workstream-in-visible-chip-row.md](2026-04-09-compass-timeline-audit-cards-can-hide-their-own-anchor-workstream-in-visible-chip-row.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Compass runtime payload selection; no special flag
  required.

- Customer Comms: Tell operators that current release and active-wave lanes now
  stay visible in `Current Workstreams` instead of being pushed out by older
  generic implementation cards.

- Code References: `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_current_workstreams_runtime.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-04/2026-04-09-execution-governance-engines-admissibility-control-and-constraint-aware-action-runtime.md`

- Fix Commit/PR: Pending.
