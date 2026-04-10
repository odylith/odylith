- Bug ID: CB-079

- Status: Closed

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: When Compass already carries its own in-frame runtime warning,
  the tooling shell can still render a second Compass failure banner above the
  iframe. On 2026-04-09, a failed full Compass refresh left the orange
  in-frame warning inside the Compass hero and also showed the shell-level
  white `Showing prior Compass snapshot` status strip above the surface. The
  operator therefore read the same failed-refresh truth twice in two different
  wrappers.

- Impact: Duplicate failure disclosure makes Compass feel noisy and regressive
  right when the surface is supposed to be calm and trustworthy. Operators lose
  the simple one-place-to-look contract and have to guess which warning is
  canonical.

- Components Affected: `src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py`,
  tooling shell runtime-status contract, Compass failed-refresh disclosure
  policy, `tests/unit/runtime/test_render_tooling_dashboard.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`.

- Environment(s): Tooling shell Compass tab when the embedded Compass runtime
  payload already includes a failed-refresh warning in `current.v1.json`.

- Root Cause: The shell-side Compass status projection only checked whether the
  child payload was stale enough to need parent disclosure. It did not check
  whether Compass itself was already surfacing the same failed-refresh truth
  inside the frame. That reopened a bug class the earlier shell-warning dedupe
  work had already said should stay closed.

- Solution: Treat the Compass in-frame warning as the canonical disclosure
  surface whenever `current.v1.json` already carries `payload.warning`. The
  shell must project a parent status only when the wrapper needs to explain a
  child-runtime problem that Compass cannot already explain on its own.

- Verification: Fixed on 2026-04-09. `PYTHONPATH=src pytest -q
  tests/unit/runtime/test_render_tooling_dashboard.py
  tests/integration/runtime/test_surface_browser_deep.py -k
  shell_compass_tab_surfaces_failed_full_refresh_warning` passed after the
  shell dedupe change, and the broader focused Compass/runtime suite passed
  with `122 passed`.

- Prevention: Compass and the shell must keep a one-warning contract for the
  same failed-refresh truth. If the child frame already explains the failure,
  the parent wrapper stays quiet.

- Detected By: Maintainer visual QA on 2026-04-09 after repeated Compass
  refresh hardening.

- Failure Signature: The shell shows a top `Showing prior Compass snapshot`
  runtime-status strip while the Compass hero also shows the failed-refresh
  warning inside the frame.

- Ownership: Dashboard shell runtime-status projection, Compass refresh
  disclosure contract.

- Invariant Violated: A single Compass failure should be disclosed once, in the
  most local truthful surface, not repeated across parent and child wrappers.

- Related Incidents/Bugs:
  [2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md](2026-04-08-tooling-shell-refresh-can-look-fresh-while-compass-child-runtime-stays-stale.md)

- Fix Commit/PR: `2026/freedom/v0.1.11` Compass hardening branch.
