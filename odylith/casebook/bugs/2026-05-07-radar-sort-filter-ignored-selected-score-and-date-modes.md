- Bug ID: CB-178

- Status: FixedPendingRelease

- Created: 2026-05-07

- Severity: P2

- Reproducibility: High

- Type: UX

- Description: Radar sort filter ignored selected score and date modes

- Impact: Operators changing the Radar sort control could still see scope-signal rank dominate the row order, making Score and Date filters feel broken and hiding the intended prioritization mode.

- Components Affected: radar

- Environment(s): Odylith product repo v0.1.15 source-local maintainer posture; generated Radar backlog UI.

- Detected By: Operator feedback on 2026-05-07 that the Radar sorting filter was broken, then browser regression fixture.

- Failure Signature: sortRows applied scopeSignalRank before the selected sort mode, so rows with high scope-signal rank stayed ahead even when the operator selected Score or Date.

- Trigger Path: Open odylith/index.html?tab=radar, search/filter to a small result set, switch Sort from Date/Rank to Score.

- Ownership: Radar backlog UI sortRows contract and browser sort regression tests.

- Timeline: Captured 2026-05-07 through `odylith bug capture`.

- Blast Radius: Radar prioritization review, release/workstream planning, and any operator using score/date sort to compare backlog rows.

- SLO/SLA Impact: No outage; adds review latency and can cause wrong workstream ordering decisions.

- Data Risk: No application data risk; generated planning order can be misleading.

- Security/Compliance: Policy and accessibility posture: operator-selected controls must change visible ordering truthfully for keyboard and screen-reader users; no credential or privacy exposure.

- Invariant Violated: A selected Radar sort mode must own the ordering for non-finished rows instead of being silently overridden by scope-signal rank.

- Root Cause: The scope-signal rank comparator ran unconditionally before the selected Score and Date comparators.

- Solution: Gate scope-signal rank behind state.sort === 'rank' and let Score and Date modes apply their own comparators.

- Verification: PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_backlog_ui.py::test_render_backlog_ui_sorts_default_sections_by_scope_signal_rank tests/integration/runtime/test_surface_browser_deep.py::test_radar_sort_filter_switches_between_date_score_and_rank_without_hiding_scope

- Prevention: Keep unit source assertions plus browser fixture that switches Date, Score, and Rank against rows with conflicting rank/date/score values.

- Regression Tests Added: tests/unit/runtime/test_render_backlog_ui.py and tests/integration/runtime/test_surface_browser_deep.py.

- Code References: - src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py
- tests/unit/runtime/test_render_backlog_ui.py
- tests/integration/runtime/test_surface_browser_deep.py
