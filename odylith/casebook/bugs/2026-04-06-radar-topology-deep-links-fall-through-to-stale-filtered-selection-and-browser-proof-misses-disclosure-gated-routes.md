- Bug ID: CB-062

- Status: Closed

- Created: 2026-04-06

- Fixed: 2026-04-06

- Severity: P0

- Reproducibility: Consistent

- Type: Product

- Description: Radar detail views could show the right topology but still
  route the operator to the wrong record. The concrete report came from
  `B-048`: clicking relation chips inside `Topology -> Relations` could land
  on `B-025` or another unrelated workstream because the selection path fell
  back to the first visible filtered row instead of honoring the explicit
  clicked id. The broken path lived behind a disclosure panel, so the browser
  suite never opened it and never proved the route contract before release.

- Impact: This is a direct trust break in a system-of-record surface.
  Topology chips exist so operators can traverse governed relationships
  exactly. Landing on a random workstream makes Radar look nondeterministic,
  weakens surrounding Atlas and Registry traceability, and lets release proof
  claim the shell is healthy while a primary operator path is still wrong.

- Components Affected: `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  bundled Radar `backlog-app.v1.js` mirrors, Radar explicit-selection routing,
  and the Playwright browser proof lane in
  `tests/integration/runtime/test_surface_browser_deep.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`, and
  `tests/integration/runtime/test_surface_browser_ux_audit.py`.

- Environment(s): Odylith product-repo shell, pinned dogfood maintainer proof
  lane, and consumer-style rendered surfaces reached through the shared shell.

- Root Cause: Explicit Radar navigation and filtered-list navigation were not
  the same contract. Relation clicks supplied an exact workstream id, but the
  detail-selection path still depended on the currently visible filtered list.
  If the target id was hidden by stale filters, selection could collapse to
  the first visible row. Browser proof missed the defect because it only
  covered already-open and obvious route affordances; it did not open
  disclosure-gated topology panels or aggressively round-trip governed shell
  links across surfaces.

- Solution: Explicit workstream navigation now reveals the requested idea
  before selection so a clicked relation id cannot be replaced by whichever
  row is currently visible. The same fix was mirrored into the bundled Radar
  assets. Browser proof widened in two layers: targeted Radar regressions for
  the exact `B-048` topology case, and a new aggressive UX audit that opens
  disclosure-gated topology UI and round-trips deep links across Radar,
  Registry, Atlas, Compass, and Casebook.

- Verification: `.venv/bin/pytest -q tests/integration/runtime/test_surface_browser_ux_audit.py`
  passed with `5 passed`. `.venv/bin/pytest -q
  tests/integration/runtime/test_surface_browser_deep.py
  tests/integration/runtime/test_surface_browser_smoke.py
  tests/integration/runtime/test_surface_browser_ux_audit.py` passed with
  `34 passed`. `git diff --check` also passed cleanly.

- Prevention: Disclosure-gated operator flows are still first-class product
  behavior. Release-gating browser proof must open them, click every governed
  shell route they expose, and assert the exact record that loads instead of
  only asserting that some page changed.

- Detected By: User report and screenshot on 2026-04-06 showing `B-048`
  relation clicks landing on unrelated Radar records.

- Failure Signature: Open Radar detail for `B-048`, expand `Topology ->
  Relations`, click a child or dependency chip, and land on a different
  workstream that happened to be first in the current filtered slice.

- Trigger Path: Enter Radar with a selected workstream plus stale list/filter
  state, open the topology disclosure, and use relation or traceability chips
  without first clearing the filter slice.

- Ownership: Radar detail routing, shell deep-link correctness, and
  release-gating browser proof of cross-surface navigation.

- Timeline: Reported on 2026-04-06 from the `B-048` detail view. The same
  night, explicit-selection routing was hardened, targeted Radar regressions
  were added, and a broader cross-surface browser audit was made part of the
  release-ready lane.

- Blast Radius: Every Radar detail view with topology relations or
  traceability links, plus any release candidate that relied on the old
  browser lane as proof of shell routing health.

- SLO/SLA Impact: No outage, but severe operator-trust regression on a primary
  navigation path.

- Data Risk: Low source-truth risk; high navigation-trust risk because the
  shell could display one governed record and open another.

- Security/Compliance: No direct security issue.

- Invariant Violated: Clicking an Odylith id or governed shell link must open
  that exact target, even when the source surface currently has stale or
  incompatible filter state.

- Workaround: Reload Radar with a clean `?tab=radar&workstream=<id>` route or
  clear filters manually before clicking relations. This is not acceptable as
  the product contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not let filtered-list convenience paths override an
  explicit record id. Do not treat collapsed or disclosure-only UI as outside
  the release-gating browser lane.

- Preflight Checks: Inspect this bug, the active `B-025` UX hardening plan,
  `render_backlog_ui_html_runtime.py`, and the browser surface suites before
  changing Radar selection, shell route normalization, or cross-surface chips
  again.

- Regression Tests Added: `test_radar_topology_relation_chips_route_to_their_own_workstream_ids`,
  `test_radar_topology_relation_clicks_self_heal_incompatible_filters`, the
  tightened Radar-to-Atlas smoke path, and
  `tests/integration/runtime/test_surface_browser_ux_audit.py` covering
  `B-048` relation chips plus cross-surface audits for Registry action chips,
  Atlas `D-018` surface/context links, Compass deep links, and Casebook direct
  bug routes.

- Monitoring Updates: The release-gating browser lane now includes the
  aggressive UX audit and will fail if disclosure-gated shell routes stop
  resolving to the exact requested target.

- Residual Risk: The audit now covers the highest-value governed routes, but
  future topology affordances can still regress if they bypass the shared
  explicit-selection path or if a new surface ships links without joining the
  browser lane.

- Related Incidents/Bugs:
  [2026-03-29-atlas-tab-reuses-cross-surface-shell-state-and-shows-inconsistent-diagram-counts.md](2026-03-29-atlas-tab-reuses-cross-surface-shell-state-and-shows-inconsistent-diagram-counts.md)

- Version/Build: Odylith product repo working tree on 2026-04-06 after the
  Radar explicit-selection fix and browser-lane expansion.

- Config/Flags: shell `tab`, Radar `workstream`, disclosure-gated topology
  panels, cross-surface deep links.

- Customer Comms: Tell operators the bug was in Radar route selection, not in
  the underlying backlog topology. Clicking a relation id now opens the exact
  target again, and the release browser lane now proves that behavior before
  ship.

- Code References: `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`,
  `src/odylith/bundle/assets/odylith/radar/backlog-app.v1.js`,
  `odylith/radar/backlog-app.v1.js`,
  `tests/integration/runtime/test_surface_browser_deep.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`,
  `tests/integration/runtime/test_surface_browser_ux_audit.py`

- Runbook References: `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`,
  `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`,
  `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`

- Fix Commit/PR: Pending.
