- Bug ID: CB-095

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass `Current Workstreams` could still duplicate active
  governed lanes even when those same ids were already represented in
  `Programs` or `Release Targets`. The frontend stopped applying the residual
  filter in the default unscoped view, which let the same lane appear in
  multiple governance boards at once.

- Impact: Compass could look noisy and procedurally sloppy by restating the
  same workstream in three places. Operators lost the intended separation
  between execution structure, release targeting, and the residual focus board.

- Components Affected: `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `odylith/compass/compass-workstreams.v1.js`,
  `src/odylith/bundle/assets/odylith/compass/compass-workstreams.v1.js`,
  Compass `Current Workstreams`, release-target coexistence, and execution-wave
  coexistence in the visible UI.

- Environment(s): Odylith product-repo maintainer mode, normal Compass shell
  render, and any browser view where a workstream appeared in `Programs` or
  `Release Targets` and also survived into the default unscoped `Current
  Workstreams` board.

- Root Cause: The default unscoped residual-focus-board rule drifted out of the
  Compass browser layer and its tests. Once that filter was removed, the UI no
  longer subtracted workstreams already represented in `Programs` or `Release
  Targets`.

- Solution: Restore the browser-layer subtraction rule for the default
  unscoped view, keep scoped workstream selection exempt, and record the
  no-duplication policy explicitly in the Compass spec, plan, and regression
  suite.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_governance_source_runtime.py`
    passed (`24 passed`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_surface_browser_deep.py -k 'compass or shell'`
    passed (`26 passed, 15 deselected`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py -k compass`
    passed (`6 passed, 11 deselected`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_layout_audit.py -k compass`
    passed (`14 passed, 12 deselected`)

- Prevention: Keep the default unscoped `Current Workstreams` board explicitly
  governed as a residual view after `Programs` and `Release Targets`, and keep
  that rule encoded in both the spec and browser tests.

- Detected By: User review of Compass asking for duplicate workstreams to be
  filtered back out of `Current Workstreams`.

- Failure Signature: The same workstream id appears in `Programs` or `Release
  Targets` and again in the default unscoped `Current Workstreams` board.

- Trigger Path: 1. Put an active lane into the current release and/or active
  execution wave. 2. Open Compass in the default unscoped view after the
  residual filter has been removed or bypassed. 3. Observe the same id in
  multiple governance boards.

- Ownership: Compass browser-layer workstream rendering and residual-board
  filter policy.

- Timeline: This surfaced during the Compass hardening pass on 2026-04-09 when
  the residual filter was relaxed and the operator reaffirmed the original
  no-duplication product rule.

- Blast Radius: Any default unscoped Compass view with active release or wave
  membership.

- SLO/SLA Impact: No outage, but a direct execution-dashboard trust regression.

- Data Risk: Low source-corruption risk; high operator-readout integrity risk.

- Security/Compliance: None directly.

- Invariant Violated: In the default unscoped view, `Current Workstreams` must
  not duplicate lanes already represented in `Programs` or `Release Targets`.

- Workaround: Manually ignore the duplicate rows and infer that the residual
  board is wrong. That is not acceptable product behavior.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: In the default unscoped view, filter out any workstream
  already represented in `Programs` or `Release Targets`; only scoped selection
  may intentionally show the chosen lane directly.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`
  and the served/generated Compass workstream assets for the residual
  subtraction rule between `Programs`, `Release Targets`, and `Current
  Workstreams`.

- Regression Tests Added: `tests/integration/runtime/test_compass_browser_regression_matrix.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_render_compass_dashboard.py`.

- Monitoring Updates: Watch for any default unscoped Compass page where ids
  already represented above reappear in the rendered `Current Workstreams`
  table.

- Residual Risk: Ranking policy can still change which non-represented rows are
  visible first, but duplication with `Programs` and `Release Targets` is now
  fail-closed again.

- Related Incidents/Bugs:
  [2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md](2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md)
  [2026-04-09-compass-current-workstream-ranking-can-hide-active-release-and-wave-lanes.md](2026-04-09-compass-current-workstream-ranking-can-hide-active-release-and-wave-lanes.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Compass shell and browser render path.

- Customer Comms: Tell operators that `Current Workstreams` is once again the
  residual board in the default unscoped view, so lanes already shown in
  `Programs` or `Release Targets` are filtered out instead of duplicated.

- Code References: `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `odylith/compass/compass-workstreams.v1.js`,
  `src/odylith/bundle/assets/odylith/compass/compass-workstreams.v1.js`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
