- Bug ID: CB-080

- Status: Closed

- Created: 2026-04-09

- Fixed: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Shared shell-surface contracts for interactive `B-###`
  workstream controls and Compass release layout kept reopening after local
  fixes. The product had multiple partially overlapping sources of truth for
  the same UI contract, so a later rebuild could silently reintroduce larger
  workstream buttons or the rejected multi-column `Release Targets` board.

- Impact: Operators had to keep re-correcting the same Compass and cross-surface
  UI regressions. The product kept drifting on compact `B-###` button sizing
  and release-target layout even after explicit operator direction and prior
  fixes.

- Components Affected:
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py`,
  `src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-base.v1.css`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-execution-waves.v1.css`,
  Compass live and bundled shell mirrors,
  Radar and Atlas workstream-link styling,
  cross-surface browser proof.

- Environment(s): Odylith product repo shell surfaces, especially Compass
  `Current Workstreams`, Compass `Release Targets`, Radar traceability/release
  chips, and Atlas workstream pill links in both live checked-in outputs and
  packaged bundle mirrors.

- Root Cause: The same visual contract existed in too many places. Compass kept
  a static fork of the shared execution-wave stylesheet instead of generating
  from the canonical shared primitive, generic Compass chip selectors still
  targeted `B-###` controls directly, and the repo lacked exact
  source-versus-live-versus-bundle equality tests for Compass shell assets plus
  computed-style browser proof across surfaces. That split truth let stale or
  duplicated rules survive and then reappear on the next render.

- Solution: Centralize interactive workstream-button styling through one shared
  `surface_workstream_button_chip_css(...)` helper, exclude workstream controls
  from generic Compass chip selectors, make Compass execution-wave CSS load the
  canonical shared generator plus only thin Compass-specific overrides, add
  exact live/bundle mirror equality tests for Compass shell assets plus the
  mirrored product surface artifacts that ship from live checked-in outputs,
  and add headless browser audits for computed workstream-button styles plus
  the single-column Compass release board in both standard and compact shell
  layouts.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_dashboard_ui_primitives.py
  tests/unit/runtime/test_execution_wave_ui_runtime_primitives.py
  tests/unit/runtime/test_render_backlog_ui.py
  tests/unit/runtime/test_render_mermaid_catalog.py
  tests/unit/runtime/test_compass_dashboard_shell.py
  tests/unit/runtime/test_surface_shell_contracts.py` passed; `PYTHONPATH=src
  python3 -m pytest -q tests/integration/runtime/test_surface_browser_layout_audit.py
  -k 'workstream_buttons or release_targets'` passed; `git diff --check`
  passed after the fix.

- Prevention: Shared surface contracts must have one canonical source. Do not
  duplicate generated shared CSS into local static surface templates, do not
  let generic chip selectors style interactive `B-###` controls, and do not
  accept shell-surface changes without exact source/live/bundle mirror proof
  for the relevant artifacts plus browser-level computed-style/layout proof
  for the operator-facing contract.

- Detected By: Repeated operator screenshots and direct corrections on
  2026-04-08 and 2026-04-09 after the same Compass release-layout and
  workstream-button regressions kept resurfacing.

- Failure Signature: Compass `Release Targets` reverts to a side-by-side
  release board or `B-###` controls in Compass, Radar, and Atlas render with
  larger text/padding than the shared compact contract.

- Trigger Path: Any later surface rebuild that consumes stale duplicated Compass
  CSS or lets generic chip rules style workstream controls again.

- Ownership: Dashboard shared UI primitives, Compass shell frontend contract,
  and cross-surface browser-proof ownership for operator-facing shell
  contracts.

- Timeline: Initial local fixes landed for individual regressions, but the
  product kept reopening them because the root contract was still duplicated.
  On 2026-04-09 the root cause was captured and the shared contract was
  re-architected to remove the duplicate paths.

- Blast Radius: Compass shell assets, Radar workstream chips, Atlas workstream
  pills, packaged bundle mirrors, and future shell-surface maintenance that
  touches shared chip/layout styling.

- SLO/SLA Impact: No outage, but repeated product-trust regressions in the
  operator surfaces.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: Operator-owned shell-surface contracts must not drift
  across rebuilds. One canonical workstream-button contract and one canonical
  execution-wave CSS source must govern the live and bundled product surfaces.

- Workaround: Manual CSS rollback and repeated surface rebuilds. There was no
  trustworthy durable fix until the contract paths were centralized.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Before changing shell-surface button or release-board
  styling, inspect this bug, the active B-025 plan, and the Compass/Dashboard
  specs. Do not introduce local size overrides, duplicate shared execution-wave
  CSS, or accept a surface slice without mirror equality and browser proof for
  the affected contract.

- Preflight Checks: Confirm interactive `B-###` controls consume the shared
  workstream-button helper, confirm Compass execution-wave CSS is composed from
  the shared generator plus thin overrides only, confirm live and bundle
  Compass shell assets exactly match the source loader output, and rerun the
  browser audit for computed button styles and stacked release layout.

- Regression Tests Added:
  `tests/unit/runtime/test_dashboard_ui_primitives.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`,
  `tests/unit/runtime/test_render_mermaid_catalog.py`,
  `tests/unit/runtime/test_render_backlog_ui.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  [2026-04-09-compass-release-target-layout-regresses-to-unauthorized-multi-column-board.md](2026-04-09-compass-release-target-layout-regresses-to-unauthorized-multi-column-board.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Shared shell surfaces in normal maintainer browsing; no special
  runtime flags required.

- Customer Comms: None. This is repo-local product memory and operator
  contract hardening.

- Code References:
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py`,
  `src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/runtime/surfaces/render_mermaid_catalog.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`

- Runbook References:
  `odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
