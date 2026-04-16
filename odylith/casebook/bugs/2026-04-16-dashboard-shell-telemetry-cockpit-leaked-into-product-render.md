- Bug ID: CB-120

- Status: Open

- Created: 2026-04-16

- Severity: P1

- Reproducibility: High

- Type: regression

- Description: The shared tooling dashboard shell rendered internal telemetry cockpit/status chrome above child surfaces, including the Telemetry Snapshot hero, recorder tape, backend footprint, and chart DOM. The screenshot captured the leak across the Executive Compass surface, and the same shell path affected Radar, Registry, Casebook, Atlas, and Compass when opened through odylith/index.html.

- Impact: Operators saw internal telemetry/status cockpit UI as product chrome, which cluttered every dashboard surface and undermined trust in the governed surfaces.

- Components Affected: dashboard

- Environment(s): Odylith product repo dashboard shell render, observed 2026-04-15 in a local browser against odylith/index.html.

- Detected By: User screenshot /Users/freedom/Desktop/Screenshot 2026-04-15 at 6.25.41 PM.png showing Telemetry Snapshot across Executive Compass.

- Failure Signature: Telemetry Snapshot, Telemetry runtime status, system-status-shell, telemetry-stat-grid, odylith-recorder-shell, odylith-chart-canvas, and ECharts hydration surfaced in the product dashboard shell.

- Trigger Path: Render the tooling dashboard and open odylith/index.html?tab=compass, or any other dashboard tab, in Chromium.

- Ownership: Dashboard shared shell presenter, tooling dashboard templates, and dashboard governance contracts.

- Timeline: Captured 2026-04-16 through `odylith bug capture`.

- Blast Radius: All dashboard tabs loaded through the shared shell: Radar, Registry, Casebook, Atlas, and Compass.

- SLO/SLA Impact: Visual/product correctness regression; non-browser checks could pass while the user-facing dashboard stayed polluted by internal runtime telemetry.

- Data Risk: No secret exposure observed, but internal runtime telemetry and derived operational metrics leaked into operator-facing product UI.

- Security/Compliance: Low direct security risk; product separation violation because internal diagnostic telemetry crossed into shipped dashboard surfaces.

- Invariant Violated: Dashboard product surfaces must never render internal telemetry cockpit, status drawer, recorder tape, chart hydration, derived telemetry chrome, or the internal delivery/evaluation/optimization/memory snapshots that fed those views.

- Root Cause: The shared shell status presenter still built and rendered an odylith_drawer telemetry payload, the top-level shell still accepted internal delivery snapshots, and the template assets still shipped CSS and JavaScript for telemetry charts and recorder UI.

- Solution: Delete the shell telemetry presenter path, remove the status presenter module, stop loading internal delivery/evaluation/optimization/memory snapshots into the product shell payload, strip telemetry CSS/JS/template hooks, remove ECharts, and add headless Chromium proof that hostile telemetry payload keys do not render across tabs.

- Verification: pytest tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_shell_never_renders_internal_telemetry_status_across_tabs -q

- Prevention: Governance records, the dashboard spec, agent guidelines, and surface-operation skills now forbid internal telemetry UI and its internal snapshot feed from entering product dashboard surfaces.

- Agent Guardrails: Do not add shell telemetry/status/cockpit/recorder/chart UI to dashboard surfaces, and do not load internal delivery/evaluation/optimization/memory snapshots into the top-level shell payload. If diagnostic telemetry is needed, keep it in runtime artifacts or explicit debug outputs and prove product DOM and payload absence in Playwright.

- Preflight Checks: Search rendered shell assets, payloads, and templates for Telemetry Snapshot, system-status-shell, telemetry-stat, odylith-recorder, odylith-chart, ECharts, memory_snapshot, optimization_snapshot, and evaluation_snapshot before closing dashboard UI work.

- Regression Tests Added: Added headless Chromium integration coverage that injects legacy telemetry/status payload keys and asserts no telemetry strings, selectors, recorder, charts, ECharts script, status cards, or internal snapshot payload keys render across Radar, Registry, Casebook, Atlas, and Compass.

- Code References: - src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py
- src/odylith/runtime/surfaces/templates/tooling_dashboard/page.html.j2
- src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js
- src/odylith/runtime/surfaces/templates/tooling_dashboard/style.css
- tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py
