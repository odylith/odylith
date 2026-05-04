- Bug ID: CB-165

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-04

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: Compass execution-wave dependency labels overflow group panels

- Impact: Operators reviewing Compass program wave tracking can see long dependency wave labels bleed outside the Depends On panel, making the wave card look broken and harder to scan.

- Components Affected: dashboard

- Environment(s): Compass execution-wave tracking in the generated dashboard, desktop and compact browser views.

- Detected By: Operator screenshot from 2026-05-04 showing a long Wave 1 dependency label escaping the Depends On card.

- Failure Signature: A Depends On chip such as Wave 1: Solo task tracking renders as one nowrap label and bleeds beyond the panel boundary.

- Trigger Path: Open odylith/index.html?tab=compass for a workstream with execution-wave dependencies whose labels are longer than the panel width, then expand the wave detail card.

- Ownership: Shared execution-wave UI primitive and Compass generated dashboard assets.

- Timeline: Captured 2026-05-04 through `odylith bug capture`.

- Blast Radius: All Compass program wave tracking cards with long dependency wave labels, including consumer greenfield programs and product dogfood programs.

- SLO/SLA Impact: No runtime outage; visible governance UX regression in Compass wave tracking.

- Data Risk: No data loss; risk is misleading or untrustworthy governance presentation.

- Security/Compliance: No security impact.

- Invariant Violated: Compass wave tracking labels must stay within their group panels and remain readable across desktop and compact layouts.

- Root Cause: Shared execution-wave labels forced white-space nowrap for every chip, so long dependency wave labels could not wrap inside narrow group panels.

- Solution: Let execution-wave labels inside group bodies wrap within their panel while preserving compact nowrap chips in section/meta rails.

- Rollback/Forward Fix: Forward fix in v0.1.14; no source-truth migration needed because the bug is in generated surface CSS and static assets.

- Verification: Browser layout regression opens Compass wave cards and verifies long dependency labels stay inside Depends On panels on desktop and compact views; shared CSS contract asserts wrapping rules.

- Prevention: Keep the browser overflow test and shared CSS contract so long dependency labels cannot regress to nowrap panel bleed.

- Agent Guardrails: Before changing execution-wave chip CSS, prove long labels in Compass group panels against desktop and compact browser layouts.

- Preflight Checks: Search existing Casebook for Compass wave label overflow; keep related shared surface contract bugs in mind.

- Regression Tests Added: tests/integration/runtime/test_surface_browser_layout_audit.py::test_compass_wave_dependency_labels_stay_inside_group_panels_in_browser and compact counterpart; tests/unit/runtime/test_execution_wave_ui_runtime_primitives.py

- Monitoring Updates: Watch Compass screenshots for long wave labels in Depends On, Primary, Carried, and In Band panels.

- Version/Build: v0.1.14 development branch

- Config/Flags: No feature flag; generated CSS default.

- Customer Comms: No public incident required; release note can mention Compass wave label overflow fix.

- Related Incidents/Bugs: CB-094, CB-098, CB-101

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.14

- Public Response: pending

- Code References: - src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py
- tests/integration/runtime/test_surface_browser_layout_audit.py
