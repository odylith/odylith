- Bug ID: CB-085

- Status: Closed

- Created: 2026-04-09

- Fixed: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Top-line governance KPI cards and release summary tiles kept
  drifting across Compass, Radar, Registry, and Casebook because the shared
  shell still allowed local stat-card CSS forks. Compass carried hand-authored
  summary-card CSS instead of composing from the shared KPI primitives, and
  Registry still inlined its own KPI-grid layout. That split truth made label
  alignment, typography, spacing, and release-card presentation regress even
  after prior fixes.

- Impact: Operators saw repeated shell regressions in the first row of the
  product surfaces, including misaligned `Current Release` cards, inconsistent
  top-line summary-tile typography, and local rebuilds that could quietly
  reopen stat-card drift.

- Components Affected:
  `src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/runtime/surfaces/render_registry_dashboard.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-base.v1.css`,
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`,
  live and bundled Compass/Radar/Registry/Casebook shell assets.

- Environment(s): Odylith product repo governance surfaces in normal shell
  browsing, especially Compass hero KPIs, Radar release summary stats,
  Registry summary KPIs, and Casebook summary KPIs.

- Root Cause: The shared KPI primitives existed, but not every surface used
  them. Compass still owned a local copy of the hero stat-card surface,
  typography, and generic card shell, while Registry still held an inline KPI
  grid block. Because those CSS forks lived outside the shared contract path,
  later edits could reopen drift without failing a direct proof lane.

- Solution: Route Compass and Registry through the shared KPI/grid/card helpers
  in `dashboard_ui_primitives.py`, remove local Compass stat-card and generic
  card CSS forks from the source template, add unit proof that the generated
  Compass base CSS contains the exact shared helper output, and add headless
  browser proof for computed KPI-card styles across Compass, Radar, Registry,
  and Casebook plus labeled current-release value checks in Compass and Radar.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_compass_dashboard_shell.py
  tests/unit/runtime/test_surface_shell_contracts.py
  tests/unit/runtime/test_render_backlog_ui.py
  tests/unit/runtime/test_render_registry_dashboard.py
  tests/integration/runtime/test_surface_browser_layout_audit.py -k kpi
  tests/integration/runtime/test_surface_browser_smoke.py -k current_release`
  passed; direct Compass, Radar, Registry, and Casebook renders passed; `git
  diff --check` passed.

- Prevention: Governance KPI/stat-card styling is a shared shell contract.
  Do not hardcode local summary-tile surface, grid, or label/value typography
  in Compass, Radar, Registry, or Casebook when the shared KPI helpers can
  express the same result. Treat local stat-card CSS forks as a regression
  risk that requires Casebook memory, spec updates, and browser proof.

- Detected By: Operator screenshot review on 2026-04-09 after the shell still
  showed stat-card drift in the first KPI row.

- Failure Signature: Compass or Radar `Current Release` tiles drift in label
  alignment, top-line KPI cards across governance surfaces stop matching on
  padding/typography, or a local source template reintroduces hand-authored
  stat-card CSS instead of the shared helper output.

- Trigger Path: Any shell-template edit that reintroduces local `.stats`,
  `.stat`, `.kpi-card`, `.kpi-label`, or `.kpi-value` styling outside the
  shared KPI helper path.

- Ownership: Dashboard shared UI primitives, Compass shell frontend contract,
  Registry renderer contract, and browser-proof coverage for governance KPI
  cards.

- Timeline: Prior fixes handled individual current-release and release-layout
  regressions, but on 2026-04-09 the broader KPI/stat-card contract gap was
  captured and the remaining local CSS forks were collapsed into one shared
  path.

- Blast Radius: Compass hero KPIs, Radar summary stats, Registry KPIs,
  Casebook KPIs, live checked-in surfaces, bundled mirrors, and future shell
  maintenance that touches summary-tile styling.

- SLO/SLA Impact: No outage, but repeated operator-facing presentation drift
  in high-visibility shell cards.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: Governance KPI/stat-card layout and typography must come
  from one shared shell contract, not local surface forks.

- Workaround: Manual card-by-card CSS rollback and repeated surface rebuilds.
  That was not a durable fix.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Before changing top-line KPI or release-summary cards,
  inspect this bug, [CB-080](2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md),
  the active `B-025` plan, and the Dashboard/Compass/Radar specs. Do not add
  local stat-card CSS forks to source templates.

- Preflight Checks: Confirm Compass summary cards, Radar summary stats,
  Registry KPIs, and Casebook KPIs all consume the shared helper output; then
  rerun unit proof for generated asset equality plus browser proof for
  computed KPI-card styles and current-release labeling.

- Regression Tests Added:
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  [2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md](2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Standard maintainer shell browsing; no special flags required.

- Customer Comms: None. This is repo-local product memory and operator
  contract hardening.

- Code References:
  `src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py`,
  `src/odylith/runtime/surfaces/render_registry_dashboard.py`,
  `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-base.v1.css`,
  `tests/unit/runtime/test_surface_shell_contracts.py`,
  `tests/integration/runtime/test_surface_browser_layout_audit.py`

- Runbook References:
  `odylith/agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`,
  `odylith/surfaces/GOVERNANCE_SURFACES.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/registry/source/components/radar/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
