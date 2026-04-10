- Bug ID: CB-096

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass browser-side runtime-truth reconciliation could accept a
  malformed or incomplete source-truth snapshot and stop there, or fall back to
  traceability without clearing stale scoped-workstream metadata. In those
  cases the page could keep old scope options, stale current-workstream state,
  or a misleading release/workstream mixture even though fresher fallback truth
  was available.

- Impact: Compass could stay delusional after the browser had already detected
  that the runtime snapshot was behind. Operators would get a partly patched
  page instead of one coherent view of the freshest governed truth.

- Components Affected: `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-runtime-truth.v1.js`,
  `odylith/compass/compass-runtime-truth.v1.js`,
  `src/odylith/bundle/assets/odylith/compass/compass-runtime-truth.v1.js`,
  source-truth reconciliation, traceability fallback, and scoped-workstream
  runtime metadata in Compass.

- Environment(s): Browser-rendered Compass with a stale runtime snapshot and
  either a missing, malformed, or partial `compass-source-truth.v1.json`, or a
  traceability fallback path that needed to replace stale scoped metadata.

- Root Cause: The reconciliation layer treated any fetched source payload as
  admissible enough to patch from, even when it lacked the fields needed to
  rebuild current-workstream and scope state. It also preserved stale scoped
  maps when falling back from source-truth to traceability.

- Solution: Normalize source-truth payloads into an explicit contract, reject
  unusable snapshots, continue through the traceability fallback, and clear
  scoped-workstream state when the fallback source cannot authoritatively
  supply it.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_governance_source_runtime.py`
    passed (`24 passed`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_compass_browser_regression_matrix.py tests/integration/runtime/test_surface_browser_deep.py -k 'compass or shell'`
    passed (`26 passed, 15 deselected`)

- Prevention: Compass browser reconciliation must refuse partial truth instead
  of half-applying it, and fallback paths must clear any stale scoped metadata
  they can no longer justify.

- Detected By: Browser regression hardening after the user reported Compass
  drift across release targets, current workstreams, and scoped views.

- Failure Signature: A newer source-truth or traceability fallback exists, but
  the browser view keeps stale scope options, stale scoped current-workstream
  selections, or a mixed old/new release posture after reconciliation.

- Trigger Path: 1. Keep a stale runtime snapshot. 2. Serve a partial or missing
  source-truth snapshot. 3. Let the browser reconciliation patch only the easy
  top-level release fields without rebuilding scoped-workstream truth.

- Ownership: Compass browser-side runtime-truth reconciliation and scoped state
  reset policy.

- Timeline: This emerged while building a harsher Compass browser regression
  matrix around the `B-072` and `B-025` drift failures.

- Blast Radius: Any browser-rendered Compass page that depends on source-truth
  or traceability fallback instead of a perfectly fresh runtime snapshot.

- SLO/SLA Impact: No outage, but a high-risk correctness regression on the main
  execution dashboard.

- Data Risk: Low source-corruption risk; high read-model trust risk.

- Security/Compliance: None directly.

- Invariant Violated: When Compass reconciles a stale runtime snapshot, it must
  produce one coherent freshest-truth view rather than a mixed stale/fresh
  scope posture.

- Workaround: Force a broader refresh and hope the source-truth snapshot is
  fully present. That is not an acceptable browser contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: If a source-truth snapshot does not contain the fields
  needed to rebuild current-workstream or scoped state, treat it as unusable and
  keep falling back.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-runtime-truth.v1.js`
  for source-payload normalization, admissibility checks, and explicit clearing
  of scoped-workstream maps on traceability fallback.

- Regression Tests Added: `tests/integration/runtime/test_compass_browser_regression_matrix.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`.

- Monitoring Updates: Watch for any Compass browser page where a stale runtime
  snapshot receives a reconciliation banner but still advertises stale scope
  options or stale current-workstream ids.

- Residual Risk: Future source overlays can still regress if they bypass the
  shared normalization path.

- Related Incidents/Bugs:
  [2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md](2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md)
  [2026-04-09-compass-current-workstream-ranking-can-hide-active-release-and-wave-lanes.md](2026-04-09-compass-current-workstream-ranking-can-hide-active-release-and-wave-lanes.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Compass browser reconciliation path; no special flag
  required.

- Customer Comms: Tell operators that Compass now refuses partial source-truth
  snapshots and clears stale scoped state instead of silently mixing old and
  new truth in the browser.

- Code References: `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-runtime-truth.v1.js`,
  `odylith/compass/compass-runtime-truth.v1.js`,
  `src/odylith/bundle/assets/odylith/compass/compass-runtime-truth.v1.js`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
