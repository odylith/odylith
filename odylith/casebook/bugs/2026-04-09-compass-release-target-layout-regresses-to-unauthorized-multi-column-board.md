- Bug ID: CB-078

- Status: Closed

- Created: 2026-04-09

- Fixed: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass `Release Targets` regressed back to a side-by-side
  multi-column board. `Targeted Workstreams` and `Completed Workstreams`
  rendered as adjacent panels with compressed cards even after the operator had
  already explicitly directed the prior stacked format to stay in place.

- Impact: The core release-target readout in Compass stopped honoring explicit
  operator preference, became harder to scan, and forced repeat correction on a
  workflow that is supposed to stay stable once the layout contract is set.

- Components Affected:
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-base.v1.css`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  bundled Compass shell mirrors,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`,
  Compass release-target layout contract.

- Environment(s): Compass release-target view in the Odylith product repo
  maintainer shell, including the checked-in `odylith/compass/` assets and the
  packaged bundle mirror under `src/odylith/bundle/assets/odylith/compass/`.

- Root Cause: The visible renderer had already been corrected back to the
  stacked release format, but a stale release-specific override remained in the
  shared Compass base CSS:
  `.card.release-groups-card .execution-wave-board { grid-template-columns:
  repeat(auto-fit, minmax(240px, 1fr)); }`. Later shell rebuilds kept pulling
  that override back into the live Compass assets, so the unauthorized
  multi-column release layout resurfaced even though the operator had already
  rejected it.

- Solution: Remove the release-specific auto-fit board override from the shared
  Compass base CSS, keep `Release Targets` on the prior stacked format, add
  source and bundle guardrails so the override cannot come back silently, and
  codify the operator-authorization rule in the active B-025 plan plus the
  Compass/Dashboard governance docs.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_compass_dashboard_shell.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_surface_shell_contracts.py` passed after the fix;
  `rg "release-groups-card \\.execution-wave-board"` now returns no matches in
  the live or bundled Compass base CSS; `git diff --check` passed.

- Prevention: Compass release-target layout is operator-owned. Do not
  reintroduce side-by-side or auto-fit multi-column release boards without
  explicit operator authorization, and do not let shared shell CSS override the
  established stacked release-target format behind the renderer's back.

- Detected By: Operator screenshot and direct correction on 2026-04-09 after
  the release-target view reverted to the rejected board layout.

- Failure Signature: Compass `Release Targets` shows `Targeted Workstreams` and
  `Completed Workstreams` as adjacent board columns with shrunken cards instead
  of the prior stacked format.

- Trigger Path: Rebuild or reload Compass after a shell render that still
  includes the stale `.card.release-groups-card .execution-wave-board`
  override.

- Ownership: Compass release-target surface contract and Dashboard shared shell
  CSS primitives.

- Timeline: The operator first rejected the side-by-side release board on
  2026-04-08 and requested the previous stacked format. One release-layout
  override was removed, but the shared base CSS override remained. On
  2026-04-09 that stale shared override reasserted the rejected layout when the
  shell assets were rebuilt.

- Blast Radius: Compass release-target rendering in the live checked-in shell,
  the packaged bundle mirrors, and future release-target UX work that reuses
  the shared base CSS.

- SLO/SLA Impact: No outage, but a repeat operator-trust regression in a core
  product surface.

- Data Risk: None.

- Security/Compliance: None.

- Invariant Violated: Once the operator sets Compass release-target layout, the
  product must not silently drift back to an alternate release board format.
  Shared shell CSS is not allowed to reintroduce release-target layout changes
  without explicit operator authorization.

- Workaround: Manual CSS rollback and shell rebuild. There was no in-product
  toggle to restore the prior layout.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Before changing Compass release-target layout, inspect this
  Casebook record, the active B-025 UX hardening plan, and the Compass and
  Dashboard component specs. Do not improvise a new release-board layout or
  add release-specific board overrides unless the operator explicitly asks for
  that change.

- Preflight Checks: Search source and bundled Compass base CSS for
  `release-groups-card .execution-wave-board`, confirm `Release Targets`
  renders `Targeted Workstreams` and `Completed Workstreams` in the established
  stacked format, and keep tests proving both the source asset and bundle
  mirror free of release-specific board overrides.

- Regression Tests Added: `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`

- Monitoring Updates: None.

- Related Incidents/Bugs:
  [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Config/Flags: Compass release-target view for the current active release with
  both targeted and completed workstreams visible.

- Customer Comms: None. This is product-repo maintainer UX and governance
  memory.

- Code References:
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-base.v1.css`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-releases.v1.js`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/unit/runtime/test_surface_shell_contracts.py`

- Runbook References:
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
