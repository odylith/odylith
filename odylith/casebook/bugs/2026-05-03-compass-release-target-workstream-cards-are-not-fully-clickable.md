- Bug ID: CB-158

- Status: FixedPendingRelease

- Created: 2026-05-03

- Fixed: Pending

- Severity: P2

- Reproducibility: Consistent

- Type: UX

- Description: Compass Release Targets rendered targeted workstreams as card-shaped rows, but the card body and title were static; only the small B-### chip carried the Radar route. Operators reading the release target panel reasonably expected the whole targeted workstream card to open the canonical Radar workstream context.

- Impact: Operators could not click the visible targeted workstream card or title to inspect the workstream, making release target navigation feel broken and undermining the greenfield governance review flow.

- Components Affected: compass

- Environment(s): Odylith v0.1.13 dev-maintainer and generated consumer Compass release target surfaces

- Detected By: Operator screenshot of the Compass Targeted Workstreams panel on 2026-05-02

- Failure Signature: Targeted workstream cards in Compass Release Targets render as static article rows with no card-level href; clicking the card body or title does not navigate.

- Trigger Path: Open odylith/index.html?tab=compass, expand Release Targets, and click a targeted workstream card body or title.

- Ownership: Compass shell frontend release-target renderer and cross-surface workstream navigation contract

- Timeline: Captured 2026-05-03 through `odylith bug capture`.

- Blast Radius: Compass Release Targets, generated consumer greenfield release plans, and browser proof for cross-surface workstream navigation

- SLO/SLA Impact: No service outage, but primary operator navigation from release planning to Radar detail is degraded.

- Data Risk: None; source truth is intact but rendered navigation is incomplete.

- Security/Compliance: None.

- Invariant Violated: Any rendered workstream card that represents a B-### entity must provide an obvious canonical Radar navigation target for the whole visible workstream object.

- Root Cause: The Compass release-target renderer used a static article for each member row and only rendered the small member chip as an anchor. The shared execution-wave card styling made the row look interactive, but the card itself had no navigation contract.

- Solution: Render each release-target member card as a card-level anchor to radarWorkstreamHref, keep the member chip non-nested inside that anchor, add focus styling, and extend browser proof to click the release-target card into Radar.

- Verification: PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_compass_dashboard.py::test_render_compass_dashboard_emits_release_summary_and_workstream_release_ui; PYTHONPATH=src ODYLITH_BROWSER_FAILURE_SCREENSHOTS=.odylith/browser-failures .venv/bin/python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py::test_compass_deeplinks_into_radar_and_registry_contexts tests/integration/runtime/test_surface_browser_smoke.py::test_compass_current_workstreams_excludes_rows_already_represented_in_programs_or_release_targets

- Prevention: Keep card-level navigation in the Compass Release Targets browser proof; cross-surface workstream cards must be tested as whole cards, not only as tiny ID chips.

- Agent Guardrails: Do not treat a visible card layout as complete when only a nested micro-chip is interactive. For workstream entity cards, the card-level affordance must navigate to Radar unless a separate in-surface expand/collapse control is explicit.

- Preflight Checks: Open Compass Release Targets, expand the release section, click a targeted workstream card, and verify the shell URL lands on tab=radar&workstream=B-###.

- Regression Tests Added: tests/unit/runtime/test_compass_dashboard_shell.py; tests/unit/runtime/test_render_compass_dashboard.py; tests/integration/runtime/test_surface_browser_smoke.py::test_compass_deeplinks_into_radar_and_registry_contexts

- Version/Build: v0.1.13 branch

- Config/Flags: Default Compass shell assets; no special flags

- Related Incidents/Bugs: CB-083

- Fixed In: 0.1.13

- Code References: - src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js
- src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py
- tests/integration/runtime/test_surface_browser_smoke.py
