- Bug ID: CB-158

- Status: FixedPendingRelease

- Created: 2026-05-03

- Fixed: Pending

- Severity: P2

- Reproducibility: Consistent

- Type: UX

- Description: Compass Release Targets briefly made targeted workstream card text/empty space navigate to Radar after an earlier affordance request. That overcorrected the UX: blank card regions looked like passive layout space but still navigated away. Only explicit workstream controls such as the B-### chip should open Radar.

- Impact: Operators could accidentally leave Compass by clicking empty card space or title text in the release target panel, making release review feel twitchy and imprecise.

- Components Affected: compass

- Environment(s): Odylith v0.1.13 dev-maintainer and generated consumer Compass release target surfaces

- Detected By: Operator screenshot and follow-up correction of the Compass Targeted Workstreams panel on 2026-05-04.

- Failure Signature: Targeted workstream cards in Compass Release Targets expose non-control regions, including title/blank row space, as Radar navigation hit targets.

- Trigger Path: Open odylith/index.html?tab=compass, expand Release Targets, and click blank space or non-button title text inside a targeted workstream card.

- Ownership: Compass shell frontend release-target renderer and cross-surface workstream navigation contract

- Timeline: Captured 2026-05-03 through `odylith bug capture`; corrected 2026-05-04 after operator clarified that the prior whole-card-navigation request was too broad.

- Blast Radius: Compass Release Targets, generated consumer greenfield release plans, and browser proof for cross-surface workstream navigation

- SLO/SLA Impact: No service outage, but primary operator review of release targets is degraded by accidental navigation.

- Data Risk: None; source truth is intact but rendered navigation semantics are too broad.

- Security/Compliance: None.

- Invariant Violated: Passive card regions must not navigate. Cross-surface navigation belongs to explicit buttons/chips/links with visible affordance.

- Root Cause: The Compass release-target renderer promoted the member title to an anchor and carried stale card-link CSS, making text/row space behave like a navigation control instead of reserving navigation for explicit chips.

- Solution: Render release-target member titles as inert text, keep the B-### member chip as the explicit Radar link, remove stale card-link CSS, and extend browser proof so blank card space stays on Compass while the chip still opens Radar.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_compass_dashboard_shell.py::test_workstream_and_registry_links_stay_cross_surface_and_without_footer_actions tests/unit/runtime/test_render_compass_dashboard.py::test_render_compass_dashboard_emits_release_summary_and_workstream_release_ui tests/unit/runtime/test_execution_wave_ui_runtime_primitives.py; PYTHONPATH=src pytest -q tests/integration/runtime/test_surface_browser_smoke.py::test_compass_deeplinks_into_radar_and_registry_contexts

- Prevention: Keep Compass Release Targets browser proof that blank card space does not navigate and explicit workstream chips still navigate to Radar.

- Agent Guardrails: Do not broaden passive card hit targets without an explicit user-facing control. Navigation should be visible, intentional, and tied to button/chip/link affordances.

- Preflight Checks: Open Compass Release Targets, expand the release section, click blank card space and verify the shell URL stays on Compass; then click the B-### chip and verify the shell URL lands on tab=radar&workstream=B-###.

- Regression Tests Added: tests/unit/runtime/test_compass_dashboard_shell.py; tests/unit/runtime/test_render_compass_dashboard.py; tests/integration/runtime/test_surface_browser_smoke.py::test_compass_deeplinks_into_radar_and_registry_contexts

- Version/Build: v0.1.13 branch

- Config/Flags: Default Compass shell assets; no special flags

- Related Incidents/Bugs: CB-083

- Fixed In: 0.1.13

- Code References: - src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js
- src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py
- tests/integration/runtime/test_surface_browser_smoke.py
