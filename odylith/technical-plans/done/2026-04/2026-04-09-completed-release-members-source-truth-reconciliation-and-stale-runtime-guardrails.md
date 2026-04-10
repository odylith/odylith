Status: Done

Created: 2026-04-09

Updated: 2026-04-09

Backlog: B-066

Goal: Keep Compass release-target, current-workstream, and execution-wave
progress readouts truthful when release source truth changes before the
high-churn Compass runtime snapshot is rewritten, and keep unknown progress
unknown across the shared release/execution-wave views.

Assumptions:
- `odylith/radar/traceability-graph.v1.json` is the freshest governed release
  read model available to Compass at page-load time.
- A stale Compass runtime snapshot must never silently reclassify completed
  release members as active targeting.
- Non-mutating validation remains non-mutating; the product must disclose or
  reconcile stale Compass runtime truth without requiring check-only sync to
  rewrite runtime files.

Constraints:
- Do not reintroduce compatibility shims that preserve the wrong active-member
  rendering path.
- Keep active release targeting distinct from completed release history.
- Prefer one shared stale-runtime/source-truth contract over ad hoc surface
  heuristics.

Reversibility: The source-truth reconciliation layer and stale-runtime warning
logic are additive and can be removed without changing release source schema or
assignment history.

Boundary Conditions:
- Scope includes Compass runtime truth reconciliation, shell runtime-status
  disclosure, sync guidance, focused browser proof, and the related governance
  updates.
- Scope excludes broader release archive redesign and unrelated Compass brief
  rendering.

Related Bugs:
- [CB-081](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md)

## Learnings
- [x] A stale Compass runtime snapshot can reopen the exact active-versus-
      completed release-membership confusion that `B-066` originally fixed.
- [x] Clean source-truth validation is not enough when the visible Compass
      runtime stays behind that truth.

## Must-Ship
- [x] Add a shared stale-runtime/source-truth detector for Compass runtime
      payloads against the live traceability release read model.
- [x] Reconcile Compass `Release Targets` and `Current Workstreams` against
      live release source truth when the runtime snapshot drifts.
- [x] Surface the mismatch in the shell runtime-status path and sync guidance
      so stale Compass payloads cannot look current.
- [x] Add focused unit and browser regressions for stale active/completed
      release-member drift.
- [x] Update Casebook, Compass/Dashboard specs, and Atlas coverage for the new
      stale-runtime truth contract.

## Should-Ship
- [x] Reuse one shared explanatory warning line across Compass and shell where
      the same stale-runtime drift is being disclosed.
- [x] Patch placeholder workstream rows from source truth enough that release
      titles and finished-state labels stay intelligible even when the runtime
      snapshot is stale.
- [x] Remove null-to-zero progress coercion from Compass execution-wave and
      Radar backlog execution-wave readouts so missing plan progress does not
      render as synthetic `0%`.

## Defer
- [x] Broader runtime/source-truth reconciliation outside Compass and its shell
      posture.
- [x] Full client-side reconstruction of all workstream analytics from source
      truth alone.

## Success Criteria
- [x] If release source truth moves `B-067` from active to completed and adds
      `B-068` as the sole active release member, Compass no longer shows
      `B-067` in `Targeted Workstreams`.
- [x] A stale Compass runtime snapshot is either reconciled from live
      traceability truth or explicitly disclosed before the operator trusts it.
- [x] Shell-facing status and sync notes admit the drift instead of implying
      the visible Compass view is current.

## Non-Goals
- [x] Making check-only sync mutate Compass runtime files.
- [x] Rebuilding the whole Compass timeline from traceability truth.

## Open Questions
- [x] Whether other high-churn child surfaces need the same live source-truth
      reconciliation contract after this Compass proof lands.

## Impacted Areas
- [x] [2026-04-08-completed-release-members-stay-visible-until-explicit-ga.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-completed-release-members-stay-visible-until-explicit-ga.md)
- [x] [2026-04-09-completed-release-members-source-truth-reconciliation-and-stale-runtime-guardrails.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-09-completed-release-members-source-truth-reconciliation-and-stale-runtime-guardrails.md)
- [x] [2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-release-targets-can-pin-closed-workstreams-until-runtime-refresh.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/compass/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/radar/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/dashboard/CURRENT_SPEC.md)
- [x] [odylith-release-planning-and-workstream-targeting.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-release-planning-and-workstream-targeting.mmd)
- [x] [release_truth_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/release_truth_runtime.py)
- [x] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [compass_dashboard_frontend_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py)
- [x] [tooling_dashboard_surface_status.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [compass-runtime-truth.v1.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/compass_dashboard/compass-runtime-truth.v1.js)
- [x] [compass-releases.v1.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js)
- [x] [compass-waves.v1.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/compass_dashboard/compass-waves.v1.js)
- [x] [compass-workstreams.v1.js](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js)
- [x] [render_backlog_ui_html_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py)
- [x] [test_release_truth_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_release_truth_runtime.py)
- [x] [test_compass_dashboard_shell.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_dashboard_shell.py)
- [x] [test_render_compass_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_compass_dashboard.py)
- [x] [test_render_backlog_ui.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_backlog_ui.py)
- [x] [test_tooling_dashboard_surface_status.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_dashboard_surface_status.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)
- [x] [test_surface_browser_deep.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_deep.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_tooling_dashboard_surface_status.py tests/unit/runtime/test_context_engine_release_resolution.py`
      (`13 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_backlog_ui.py`
      (`26 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_surface_shell_contracts.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_backlog_ui.py`
      (`90 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py::test_compass_reconciles_release_targets_from_live_traceability_when_runtime_snapshot_is_stale tests/integration/runtime/test_surface_browser_layout_audit.py::test_compass_release_targets_keep_single_column_board_layout_in_browser tests/integration/runtime/test_surface_browser_layout_audit.py::test_compass_release_targets_keep_single_column_board_layout_in_compact_browser tests/integration/runtime/test_surface_browser_smoke.py -k release_targets`
      (`3 passed`)
- [x] `git diff --check`
      (passed)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --runtime-mode standalone --proceed-with-overlap`
      (passed)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
      (passed)

## Current Outcome
- [x] Compass does not silently trust stale runtime release-membership truth over
      fresher traceability source truth.
- [x] Release-target and current-workstream cards no longer pin closed
      workstreams at `0% progress` after closeout.
- [x] Shared execution-wave progress chips leave unknown progress blank instead
      of inventing `0%` in Compass and Radar.
- [x] Bundled surface mirrors under `src/odylith/bundle/assets/odylith/`
      match the live checked-in Compass, Radar, Atlas, Registry, Casebook, and
      shell outputs after the fix.
