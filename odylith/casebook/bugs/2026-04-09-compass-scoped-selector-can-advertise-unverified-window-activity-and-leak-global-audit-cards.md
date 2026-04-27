- Bug ID: CB-088

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass scoped window selection was still too permissive. In the
  live `24h` and `48h` windows, a workstream could appear in the scope
  dropdown even when Compass had no verified scoped activity for that exact
  window. On 2026-04-09 this surfaced on `B-040`: the scoped brief correctly
  said there was no verified local activity, but the selector still advertised
  `B-040`, and selecting it could make Timeline Audit show broad global plan
  or governance transactions that merely mentioned `B-040` among many other
  workstreams.

- Impact: A quiet workstream could look locally active when it was not. That
  breaks operator trust in both the scope selector and Timeline Audit because
  the UI can imply “this workstream moved in this window” while the underlying
  verified-scope truth says the opposite.

- Components Affected: `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`, Compass component
  spec, and `B-025` governance memory.

- Environment(s): Odylith product-repo maintainer mode, bundled Compass
  surface, and any rendered Compass runtime payload using scoped `24h` or
  `48h` windows.

- Root Cause: Compass was using broad “scope mentioned anywhere in the window”
  heuristics instead of a tighter verified-scoped-activity contract. Two noisy
  row classes were enough to advertise a scoped window incorrectly: governance-
  only local-change rows under Radar/Plan/Casebook/Atlas/Registry source paths,
  and wide fanout transactions that touched many workstreams at once. The UI
  then reused those same broad rows for scoped timeline filtering, so a quiet
  selected workstream could inherit unrelated global audit cards.

- Solution: Compute `verified_scoped_workstreams` per rolling window inside the
  runtime payload, and make both the dropdown and scoped timeline derive from
  that authoritative set. Verified scoped activity now excludes governance-only
  local-change rows and broad fanout transactions, while still allowing recent
  completed workstreams and genuinely scoped audit movement. Deep-linked scopes
  may still be preserved for continuity, but if the selected workstream is not
  verified for the active window, Compass must render the quiet/unavailable
  brief state and an empty scoped timeline instead of borrowing global audit
  rows.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_compass_dashboard_shell.py
  tests/unit/runtime/test_render_backlog_ui.py
  tests/unit/runtime/test_render_tooling_dashboard.py` passed (`105 passed`).
  `PYTHONPATH=src python3 -m pytest -q
  tests/integration/runtime/test_surface_browser_smoke.py
  tests/integration/runtime/test_surface_browser_deep.py
  tests/integration/runtime/test_surface_browser_ux_audit.py
  tests/integration/runtime/test_surface_browser_filter_audit.py
  tests/integration/runtime/test_surface_browser_layout_audit.py
  tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
  passed (`87 passed, 1 skipped`). `env PYTHONPATH=src /usr/bin/time -p
  python3 -m odylith.cli compass refresh --repo-root . --wait` passed with a
  bounded refresh (`real 1.14`), and the refreshed
  `odylith/compass/runtime/current.v1.json` now excludes `B-040` from both
  `verified_scoped_workstreams["24h"]` and `verified_scoped_workstreams["48h"]`
  while keeping the scoped `B-040` brief unavailable with
  `diagnostics.reason = scoped_window_inactive`.

- Prevention: Scoped Compass is fail-closed, and that rule now covers the
  selector and timeline as well as the brief. A workstream scope is only
  advertised for a rolling window when Compass has verified scoped activity for
  that exact window. Global governance churn and broad fanout audit rows stay
  global-only evidence unless a narrower verified scoped row also exists.

- Detected By: User report with screenshots showing `B-040` in the `48h`
  scope selector and unrelated `B-064` timeline cards still visible after
  selecting it.

- Failure Signature: A workstream with no verified scoped `24h` or `48h`
  activity still appears in the scope dropdown, the scoped standup brief says
  there is no local verified movement, and Timeline Audit shows unrelated
  global transactions anyway.

- Trigger Path: 1. Create a window containing only governance-only local
  changes or broad fanout transactions that mention a workstream. 2. Open
  Compass on that rolling window. 3. Select or deep-link to the workstream.

- Ownership: Compass runtime payload truth, scoped selection semantics, and
  headless browser proof for Compass timeline/scope behavior.

- Timeline: The operator-visible failure surfaced during `v0.1.11` Compass
  hardening. Earlier fixes already made scoped briefs fail closed, but the
  selector and timeline were still reading looser scope signals than the brief
  layer itself.

- Blast Radius: Any workstream that appears only inside broad governance churn
  or many-workstream transactions can be misadvertised as locally active in
  Compass.

- SLO/SLA Impact: No outage, but a direct operator-trust regression in one of
  Compass’s core navigation and audit surfaces.

- Data Risk: Low source-truth corruption risk; high local-readout integrity
  risk.

- Security/Compliance: None directly.

- Invariant Violated: Compass must not advertise or render a scoped rolling
  window unless that exact workstream has verified scoped activity for that
  window.

- Workaround: Treat the scoped brief’s unavailable state as more trustworthy
  than the selector and timeline. That is not an acceptable product default.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not treat every workstream mention as scoped evidence.
  Governance-only local changes and broad fanout audit rows are global context
  unless the runtime builder has also found verified scoped movement for that
  workstream and window.

- Preflight Checks: Inspect `verified_scoped_workstreams` in
  `odylith/compass/runtime/current.v1.json`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js`,
  and `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`.

- Regression Tests Added: `tests/unit/runtime/test_compass_dashboard_runtime.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`.

- Monitoring Updates: Watch for any scope present in the selector but missing
  from the payload’s `verified_scoped_workstreams` for the active window, and
  watch for any scoped timeline rendering global fanout cards when the scoped
  brief is unavailable.

- Residual Risk: Deep links can still preserve a selected scope for continuity
  even when the window is quiet, but that state now renders as quiet/unavailable
  with an empty timeline instead of false scoped activity.

- Related Incidents/Bugs:
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Default Compass rolling-window behavior; no special flag
  required.

- Customer Comms: Tell operators that Compass now advertises local scope only
  when it has verified scoped activity for that exact window. Quiet workstreams
  may still be deep-linked, but they will show a quiet brief and empty
  Timeline Audit instead of inherited global audit cards.

- Code References: `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
