- Bug ID: CB-017

- Status: Closed

- Created: 2026-03-29

- Fixed: 2026-03-29

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Atlas could show different diagram totals depending on which tab
  the operator came from. The shell reused stale Atlas `diagram` state across
  tab switches, reused unrelated Radar/Compass `workstream` state when opening
  Atlas from the top tab bar, and Atlas itself tolerated mismatched
  `workstream + diagram` query pairs. That produced inconsistent counts,
  mismatched filter UI, and confusing single-diagram or partial-catalog views
  even though the Atlas catalog itself was healthy.

- Impact: Operators could see different Atlas totals and filtered results for
  the same catalog just by approaching Atlas from a different previous tab.
  That weakens trust in Atlas as a system-of-record surface and makes shell
  query-state routing feel nondeterministic.

- Components Affected: `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  Atlas shell query-state contract, Atlas filter normalization behavior,
  headless browser surface proof lane.

- Environment(s): local Odylith shell in the product repo and consumer-style
  rendered surfaces entered through the shared shell.

- Root Cause: The tooling shell treated top-tab switches as "reuse the current
  global URL state" instead of "restore the destination tab's own state". That
  let Atlas-specific `diagram` params leak into Radar/Compass URLs and let
  unrelated `workstream` params leak back into Atlas. Inside Atlas, the list
  filter also had a special case that kept the selected diagram visible even
  when it no longer matched the active `workstream` filter, so bad routes
  produced mixed or collapsed counts instead of normalizing.

- Solution: The shell now keeps tab-local navigation memory and sanitizes URL
  state per tab before syncing frames or writing history, so Atlas opens from
  its own remembered state instead of inheriting Radar/Compass scope. Atlas now
  normalizes mismatched selected-diagram/workstream routes back to `All
  Workstreams` before filtering, and new Playwright coverage locks the route
  contract end to end.

- Verification: `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_render_mermaid_catalog.py
  tests/unit/runtime/test_render_tooling_dashboard.py` passed with `10 passed`;
  `PYTHONPATH=src python -m pytest -q
  tests/integration/runtime/test_surface_browser_smoke.py -k
  'atlas_bad_cross_surface_route_self_heals_to_full_catalog or atlas_tab_switch_restores_atlas_state_instead_of_leaking_radar_scope'`
  passed with `2 passed`; the widened browser/runtime lane and full sync also
  passed after the fix.

- Prevention: Shell query state must be tab-local, not a shared bag of params.
  Top-tab switching should restore the destination surface's own state, and
  child surfaces must fail closed on mismatched route params instead of showing
  partially filtered truth.

- Detected By: user report with screenshots showing Atlas totals changing
  between routes, followed by source audit and headless-browser reproduction.

- Failure Signature: Atlas showed `1` or other partial totals with the
  `All Workstreams` dropdown visible, or preserved an old diagram while the
  shell URL/workstream belonged to a different surface context.

- Trigger Path: select a diagram in Atlas, move to another surface with a
  different workstream, then return to Atlas through the top tab; or open Atlas
  with a mismatched `workstream + diagram` shell URL.

- Ownership: shell tab-state routing, Atlas query normalization, and browser
  proof of cross-surface navigation contracts.

- Timeline: reported and reproduced on 2026-03-29; shell-state isolation,
  Atlas route normalization, and browser hardening landed the same day.

- Blast Radius: Atlas operators in the Odylith product repo and consumer-style
  shells using the same shared query-state/tab-routing contract.

- SLO/SLA Impact: no outage, but meaningful product-trust regression in the
  core local shell.

- Data Risk: low. The bug was presentation and routing state drift, not source
  truth corruption.

- Security/Compliance: no direct security issue, but the defect weakens trust
  in the shell as an accurate local read model.

- Invariant Violated: the same Atlas catalog should render the same total count
  regardless of the previous surface route unless the operator explicitly asked
  for an Atlas-specific filter.

- Workaround: reload Atlas directly with `?tab=atlas` or clear the leaked
  `workstream`/`diagram` query params manually.

- Rollback/Forward Fix: Forward fix. Reverting the shell-state isolation or
  Atlas route normalization reintroduces nondeterministic Atlas counts.

- Agent Guardrails: Do not carry surface-specific query params across unrelated
  shell tabs. Do not preserve a selected Atlas diagram by violating the active
  filter contract.

- Preflight Checks: inspect this bug, [control.js](../../../src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js),
  [render_mermaid_catalog.py](../../../src/odylith/runtime/surfaces/render_mermaid_catalog.py),
  and [test_surface_browser_smoke.py](../../../tests/integration/runtime/test_surface_browser_smoke.py)
  before changing shell query routing or Atlas filtering again.

- Regression Tests Added: `test_atlas_bad_cross_surface_route_self_heals_to_full_catalog`
  and `test_atlas_tab_switch_restores_atlas_state_instead_of_leaking_radar_scope`.

- Monitoring Updates: the headless browser route lane now proves Atlas
  cross-tab and bad-query normalization behavior directly.

- Related Incidents/Bugs: no related bug found

- Version/Build: workspace state on 2026-03-29 before Atlas shell-state
  isolation and route-normalization hardening.

- Config/Flags: shell `tab`, Atlas `workstream`, Atlas `diagram`, top-tab route
  switching.

- Customer Comms: tell operators Atlas was not losing diagrams; it was
  reusing stale shell state. The fix makes the count and filter state stable
  across routes again.

- Code References: `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  `tests/unit/runtime/test_render_mermaid_catalog.py`,
  `tests/unit/runtime/test_render_tooling_dashboard.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`

- Runbook References: `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`,
  `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`

- Fix Commit/PR: `B-023` closed on 2026-03-29 after shell tab-state isolation,
  Atlas query normalization, and browser proof landed together.
