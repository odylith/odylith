- Bug ID: CB-109

- Status: Closed

- Created: 2026-04-14

- Fixed: 2026-04-14

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass live and historical `24h` and `48h` Timeline Audit
  views could collapse to the selected `audit_day` instead of showing the full
  rolling window. On 2026-04-14 this made Compass look underfilled because the
  `2026-04-14` audit-day slice showed only a few current-day transactions,
  while the same rolling window still contained most of its populated audit
  rows on `2026-04-13`.

- Impact: Operators could open Compass, trust the standup brief and KPI readout
  as rolling-window views, and still see a Timeline Audit that silently
  narrowed itself to one day. That makes Compass look sparse or stale even when
  the runtime payload still holds valid in-window execution evidence.

- Components Affected:
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `odylith/compass/compass-workstreams.v1.js`,
  `src/odylith/bundle/assets/odylith/compass/compass-workstreams.v1.js`,
  `tests/integration/runtime/test_surface_browser_deep.py`,
  `tests/integration/runtime/test_surface_browser_filter_audit.py`,
  Compass component spec, and `B-025` governance memory.

- Environment(s): Odylith product-repo maintainer mode, bundled Compass
  surface, and any Compass render where `window=24h` or `window=48h` spans
  more than one populated local audit day.

- Root Cause: `renderTimeline(...)` still treated `audit_day` as a hard
  selected-day filter even after the rest of Compass had moved to rolling-window
  semantics. The renderer computed all day tokens inside the active window,
  then replaced them with `[selectedAuditDay]` whenever `audit_day` was
  present. That made the audit-day picker act like a single-day slicer instead
  of a rolling-window anchor.

- Solution: Keep rolling-window truth in the Timeline Audit renderer. Compass
  now renders every populated day token inside the active window bounds,
  ordered newest-first, while still using `audit_day` to anchor the chosen
  window and the current-day visible-hour horizon. The live shipped surface and
  bundled mirror were updated together, and browser proof now covers both sides
  of the contract: prior-day in-window sections stay visible, and the current
  day still clips future empty hours.

- Verification: `pytest -q tests/integration/runtime/test_surface_browser_deep.py -k 'compass_scoped_live_view_prefers_latest_non_empty_audit_day or compass_live_timeline_keeps_prior_window_day_while_hiding_future_hours'`
  passed (`2 passed, 38 deselected`). `pytest -q
  tests/integration/runtime/test_surface_browser_filter_audit.py -k
  'compass_filter_audit_preserves_valid_audit_day_across_window_changes'`
  passed (`1 passed, 4 deselected`).

- Prevention: In Compass, `audit_day` anchors a rolling window; it is not
  allowed to collapse a `24h` or `48h` Timeline Audit to one day when other
  populated day buckets still fall inside the active bounds. Browser proof must
  keep asserting both parts together.

- Detected By: User report with screenshot on 2026-04-14 asking why Timeline
  Audit was not filling.

- Failure Signature: Compass `24h` or `48h` live view shows only the selected
  audit day in Timeline Audit, mostly empty current-day hours, and no prior-day
  section even though the same rolling window still contains populated
  transactions or events.

- Trigger Path: 1. Open Compass with `window=24h` or `window=48h`. 2. Let the
  selected `audit_day` point at the current local day. 3. Ensure the current
  day has only a few early-hour transactions while the prior day still carries
  most of the rolling-window activity. 4. Observe Timeline Audit render only
  the current day.

- Ownership: Compass Timeline Audit window semantics, live and bundled Compass
  timeline assets, and browser proof for rolling-window day visibility.

- Timeline: The user reported the underfilled Timeline Audit on 2026-04-14.
  Investigation showed the runtime payload already contained the prior-day
  evidence, so the regression was in render-time day filtering rather than data
  freshness. The fix restored true rolling-window day rendering the same turn.

- Blast Radius: Any Compass render where `audit_day` is set and the chosen
  `24h` or `48h` window spans more than one populated local day.

- SLO/SLA Impact: No outage, but a direct operator-trust regression in a core
  audit surface.

- Data Risk: Low source-truth corruption risk; medium readout integrity risk
  because valid in-window execution evidence became invisible.

- Security/Compliance: None directly.

- Invariant Violated: Compass rolling Timeline Audit must show all populated
  day sections inside the active `24h` or `48h` window. `audit_day` may anchor
  the window, but it must not collapse rolling-window evidence to one day.

- Workaround: Change the audit day manually to the prior day or inspect the raw
  runtime payload. That is not acceptable product behavior.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not let an audit-day picker silently redefine Timeline
  Audit from rolling-window evidence to single-day slicing. If the UI still
  presents `24h` or `48h`, the renderer must keep every populated in-window day
  visible unless the operator explicitly chose a single-day mode.

- Preflight Checks: Inspect
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js`,
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  and the shipped `odylith/compass/compass-workstreams.v1.js` mirror before
  changing Timeline Audit window semantics again.

- Regression Tests Added: `tests/integration/runtime/test_surface_browser_deep.py`,
  `tests/integration/runtime/test_surface_browser_filter_audit.py`.

- Monitoring Updates: Watch for live `24h` or `48h` Timeline Audit renders that
  show only the current day while the runtime payload still contains populated
  prior-day rows inside the active window bounds.

- Residual Risk: Explicit historical date views still depend on retained
  history coverage for older days, so missing retained snapshots can still
  leave a bounded rolling window partially empty for truthful reasons.

- Related Incidents/Bugs:
  [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md)
  [2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md](2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md)
  [2026-04-09-compass-timeline-audit-cards-can-hide-their-own-anchor-workstream-in-visible-chip-row.md](2026-04-09-compass-timeline-audit-cards-can-hide-their-own-anchor-workstream-in-visible-chip-row.md)

- Version/Build: Odylith product repo working tree on 2026-04-14.

- Config/Flags: Default Compass rolling-window behavior with `window=24h` or
  `window=48h` and a selected `audit_day`; no special flag required.

- Customer Comms: Tell operators that Compass Timeline Audit now shows every
  populated day in the active rolling window again, so `24h` and `48h` read
  like real windows instead of looking sparse when the current day is only
  partially populated.

- Code References:
  `src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js`,
  `odylith/compass/compass-workstreams.v1.js`,
  `src/odylith/bundle/assets/odylith/compass/compass-workstreams.v1.js`,
  `tests/integration/runtime/test_surface_browser_deep.py`,
  `tests/integration/runtime/test_surface_browser_filter_audit.py`

- Runbook References:
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
