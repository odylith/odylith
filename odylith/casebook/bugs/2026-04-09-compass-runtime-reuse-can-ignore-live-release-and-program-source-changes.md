- Bug ID: CB-093

- Status: Closed

- Created: 2026-04-09

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Compass could keep reusing a seemingly fresh runtime snapshot
  after live release-assignment source or execution-wave program source had
  already changed. In the observed failure, current release truth had moved to
  `B-072` through `B-079`, but `odylith/compass/runtime/current.v1.json` still
  showed the old release membership because the refresh invalidation contract
  did not notice source changes under `odylith/radar/source/releases/` or
  `odylith/radar/source/programs/`.

- Impact: Compass could be confidently wrong about the active release target
  set and the current workstream lane even after the authoritative source had
  already moved. That is a direct operator-trust failure on the execution
  surface.

- Components Affected: `src/odylith/runtime/context_engine/surface_projection_fingerprint.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_governance_source_runtime.py`,
  Compass runtime reuse, live release-target truth, execution-wave source
  overlay, and `B-072`.

- Environment(s): Odylith product-repo maintainer mode, bounded
  `odylith compass refresh --repo-root . --wait`, release-target mutations
  under `odylith/radar/source/releases/`, and umbrella-wave mutations under
  `odylith/radar/source/programs/`.

- Root Cause: The runtime input fingerprint watched the compiled
  traceability graph but not the authoritative release-assignment or
  execution-wave program source trees. At the same time, Compass runtime
  shaping still derived release summary and workstream catalog state from the
  traceability snapshot instead of recomputing from live idea, release, and
  program source during refresh.

- Solution: Extend the surface-projection fingerprint to include
  `odylith/radar/source/releases/` and `odylith/radar/source/programs/`, and
  build Compass governance context from live source truth first, then overlay
  that onto the traceability graph so current release, workstream rows, and
  execution-wave context stay authoritative even when the compiled projection
  lags.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_refresh_contract.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_compass_transaction_runtime.py tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_surface_projection_fingerprint.py tests/unit/runtime/test_compass_current_workstreams_runtime.py tests/unit/runtime/test_compass_governance_source_runtime.py`
    passed (`92 passed`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py::test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_checklist_label_instead_of_fake_zero_progress tests/integration/runtime/test_surface_browser_deep.py::test_compass_release_targets_show_tracked_execution_percent_for_partial_progress`
    passed (`3 passed`)
  - `PYTHONPATH=src python3 -m odylith.cli release show current --repo-root . --json`
    now reports active workstreams `B-072` through `B-079`
  - `PYTHONPATH=src python3 -m odylith.cli compass refresh --repo-root . --wait`
    passed, and the refreshed `odylith/compass/runtime/current.v1.json` now
    reports current release active workstreams `B-072` through `B-079`

- Prevention: Compass runtime reuse must invalidate on every authoritative
  release/program source mutation, and the runtime payload must prefer live
  governed source truth over compiled projections whenever the two can drift.

- Detected By: User review of Compass after `B-072` wave and release changes
  failed to appear under release targets or current workstreams.

- Failure Signature: `odylith/radar/source/releases/release-assignment-events.v1.jsonl`
  and `odylith/radar/source/programs/B-072.execution-waves.v1.json` already
  contain the new truth, but `odylith/compass/runtime/current.v1.json`
  continues to advertise the old release membership set until a refresh path
  happens to rebuild from broader invalidation.

- Trigger Path: 1. Change current release assignments or execution-wave source
  truth. 2. Leave the compiled traceability graph or stale runtime snapshot in
  place. 3. Open Compass on a path that reuses the old runtime payload.

- Ownership: Compass runtime freshness contract, release-target truth, and
  execution-wave source integration.

- Timeline: This surfaced immediately after the `B-072` release and wave slice
  landed. The source records were correct, but Compass still looked at the old
  shape.

- Blast Radius: Any Compass readout that depends on current release membership
  or execution-wave context can drift after source-only release/program changes.

- SLO/SLA Impact: No outage, but a direct correctness failure in the primary
  execution dashboard.

- Data Risk: Low source-corruption risk; high runtime read-model trust risk.

- Security/Compliance: None directly.

- Invariant Violated: Compass must not reuse a runtime snapshot that is blind
  to authoritative release or program source changes.

- Workaround: Force a full enough refresh until the snapshot happens to rebuild.
  That is not an acceptable product contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not trust compiled traceability alone for release or
  execution-wave truth when authoritative source files exist locally and are
  cheap to read.

- Preflight Checks: Inspect
  `src/odylith/runtime/context_engine/surface_projection_fingerprint.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_governance_source_runtime.py`, and the
  live files under `odylith/radar/source/releases/` and
  `odylith/radar/source/programs/`.

- Regression Tests Added: `tests/unit/runtime/test_surface_projection_fingerprint.py`,
  `tests/unit/runtime/test_compass_governance_source_runtime.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`.

- Monitoring Updates: Watch for any case where current release source truth or
  execution-wave source truth changes without a corresponding Compass runtime
  fingerprint change or current runtime payload rewrite.

- Residual Risk: The runtime now rebuilds off the authoritative source, but
  future regressions could reappear if new Compass payload paths bypass the
  shared governance-context overlay.

- Related Incidents/Bugs:
  [2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md](2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md)
  [2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md](2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Visible in normal Compass runtime refresh and render paths; no
  special flag required.

- Customer Comms: Tell operators that Compass now invalidates and rebuilds on
  live release/program source changes instead of silently reusing a stale
  release-target snapshot.

- Code References: `src/odylith/runtime/context_engine/surface_projection_fingerprint.py`,
  `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_governance_source_runtime.py`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-04/2026-04-09-execution-governance-engines-admissibility-control-and-constraint-aware-action-runtime.md`

- Fix Commit/PR: Pending.
