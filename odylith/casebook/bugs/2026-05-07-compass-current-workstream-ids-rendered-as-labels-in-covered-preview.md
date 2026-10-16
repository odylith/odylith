- Bug ID: CB-177

- Status: FixedPendingRelease

- Created: 2026-05-07

- Severity: P2

- Reproducibility: High

- Type: OperatorUX

- Description: Compass current workstream ids rendered as labels in covered preview

- Impact: Operators could not jump from the Current Workstreams B-id controls in the program-covered preview to the canonical Radar workstream route; the screenshot showed B-001/B-002/B-003 as passive labels instead of deeplink buttons.

- Components Affected: compass

- Environment(s): Odylith product repo v0.1.15 source-local maintainer posture; generated Compass current workstreams surface after greenfield apply.

- Detected By: Operator screenshot and explicit feedback on 2026-05-07.

- Failure Signature: Current Workstreams rendered B-### inside inert chip markup for rowsAreProgramCovered instead of an anchor with tab=radar&view=plan&workstream=B-###.

- Trigger Path: Open odylith/index.html?tab=compass after greenfield apply where active rows are represented by programs or release targets.

- Ownership: Compass Current Workstreams renderer and shared workstream-button route contract.

- Timeline: Captured 2026-05-07 through `odylith bug capture`.

- Blast Radius: Compass current-workstream navigation, greenfield first-run closeout, and operator trust in B-id controls.

- SLO/SLA Impact: No service outage; slows handoff from generated Compass summary to Radar implementation workstream.

- Data Risk: No application data risk; generated governance navigation can mislead operators.

- Security/Compliance: Accessibility and policy posture: B-### controls must be keyboard-focusable links with truthful destinations so screen-reader and keyboard operators can reach Radar without guessing or editing URLs; no credential exposure.

- Invariant Violated: Interactive B-### workstream controls must be buttons/anchors that deep-link to Radar, not passive labels.

- Root Cause: The rowsAreProgramCovered branch used label-style chip markup while ordinary current rows used the shared ws-id button contract.

- Solution: Render covered-preview ids as a.ws-id-btn anchors pointing at radarWorkstreamHref(id, { view: "plan" }) and keep data-covered-ws-id for local row behavior.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py::test_workstream_and_registry_links_stay_cross_surface_and_without_footer_actions tests/integration/runtime/test_surface_browser_smoke.py::test_compass_current_workstreams_excludes_rows_already_represented_in_programs_or_release_targets

- Prevention: Keep unit and browser proof that Current Workstreams B ids are anchor controls with tab=radar, view=plan, and workstream=B-### links.

- Regression Tests Added: tests/unit/runtime/test_compass_dashboard_shell.py and tests/integration/runtime/test_surface_browser_smoke.py cover the anchor contract.

- Related Incidents/Bugs: CB-083

- Code References: - src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js
- tests/unit/runtime/test_compass_dashboard_shell.py
- tests/integration/runtime/test_surface_browser_smoke.py
