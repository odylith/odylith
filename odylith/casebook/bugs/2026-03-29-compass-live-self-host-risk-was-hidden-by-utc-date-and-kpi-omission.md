- Bug ID: CB-018

- Status: Closed

- Created: 2026-03-29

- Fixed: 2026-03-29

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Compass live 24h and 48h views could hide the current self-host
  release-posture risk even when the runtime snapshot counted it as a critical
  risk. The KPI math omitted self-host risks entirely, the self-host risk row
  was stamped with the UTC date instead of the local audit day, and zero-valued
  KPIs rendered as blank strings instead of `0`. Together those defects made
  Compass look calmer than the real product posture and undermined trust in the
  standup brief and timeline audit.

- Impact: Maintainers could open Compass and see empty or misleading critical
  risk state right before a release even though the runtime correctly knew the
  product repo was diverged from its pinned runtime. That weakens operator
  trust, makes release triage slower, and creates a real risk of shipping with
  an incorrect read of current posture.

- Components Affected: `src/odylith/runtime/surfaces/compass_dashboard_shell.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`, Compass live KPI
  render path, self-host posture risk rows, browser smoke coverage.

- Environment(s): Odylith product repo live Compass renders and any consumer or
  maintainer shell navigation that relies on Compass 24h or 48h windows.

- Root Cause: Compass counted self-host posture risk in the runtime snapshot but
  the shell computed the visible `Critical Risks` KPI from bugs, traceability,
  and stale diagrams only. Separately, the self-host risk row used the UTC
  date from `generated_utc`, which crossed into the next day in Pacific time
  and got filtered out of the live local audit window. Finally, the generic
  Compass HTML escaping helper collapsed falsy values, so numeric zeroes
  rendered as empty strings.

- Solution: Compass now counts self-host posture rows in the live `Critical
  Risks` KPI, stamps those rows with the local Compass audit day instead of the
  UTC date, preserves numeric zero values in KPI rendering, and covers the path
  with unit and headless-browser regression tests.

- Verification: `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_compass_dashboard_shell.py` passed with `16 passed`;
  `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard
  --repo-root . --output odylith/compass/compass.html --runtime-mode standalone`
  passed; `PYTHONPATH=src python -m pytest -q
  tests/integration/runtime/test_surface_browser_smoke.py -k
  'compass_window_switches_keep_brief_visible or shell_cross_tab_hops_keep_compass_global_runtime_fresh'`
  passed with `2 passed`.

- Prevention: Treat live runtime KPI math, visible risk rows, and local audit
  day handling as one contract. Compass browser coverage must assert that the
  live windows show a numeric critical-risk KPI and a non-empty risk panel when
  the runtime snapshot says critical risk exists.

- Detected By: user report and release-preflight validation on 2026-03-29.

- Failure Signature: Compass 24h/48h showed blank or empty critical-risk state
  even though the runtime snapshot contained a self-host posture risk and the
  current standup brief stayed current.

- Trigger Path: render Compass after source version promotion while the product
  repo active runtime still diverges from the pinned runtime.

- Ownership: Compass live runtime read model and self-host posture surfacing.

- Timeline: user flagged Compass trust regression during release prep; browser
  smoke then failed on missing numeric `Critical Risks`; root cause traced to
  KPI omission plus UTC/local-day mismatch; source, generated assets, and tests
  were repaired the same afternoon.

- Blast Radius: release triage, maintainer trust in Compass, and any operator
  using the live 24h/48h windows to assess current product posture.

- SLO/SLA Impact: no shared outage; operator visibility and release confidence
  degraded.

- Data Risk: low. The runtime snapshot was correct; the defect was in visible
  Compass interpretation and filtering.

- Security/Compliance: indirect risk. Hidden self-host posture makes it easier
  to miss release-blocking divergence.

- Invariant Violated: Compass live views must not hide current critical risks
  that the runtime snapshot already counts as present.

- Workaround: inspect `odylith/compass/runtime/current.v1.json` directly or run
  a fresh Compass render before relying on the visible KPI state.

- Rollback/Forward Fix: Forward fix. Reverting would restore hidden self-host
  posture and blank zero-value KPI rendering.

- Agent Guardrails: Do not compute visible Compass KPIs from a narrower set of
  risk classes than the runtime snapshot uses. Do not derive live audit-day
  filtering from UTC dates when the surface contract is local-day based.

- Preflight Checks: inspect this bug, [CURRENT_SPEC.md](../../registry/source/components/compass/CURRENT_SPEC.md),
  [test_compass_dashboard_runtime.py](../../../tests/unit/runtime/test_compass_dashboard_runtime.py),
  [test_compass_dashboard_shell.py](../../../tests/unit/runtime/test_compass_dashboard_shell.py),
  and [test_surface_browser_smoke.py](../../../tests/integration/runtime/test_surface_browser_smoke.py)
  before changing Compass live KPI or risk filtering logic again.

- Regression Tests Added: Compass shell regression for zero-value rendering and
  self-host risk counting; Compass runtime regression for local-date self-host
  risk rows; headless browser proof for live 24h/48h KPI freshness.

- Monitoring Updates: release-preflight now implicitly exercises this path
  through browser smoke and Compass runtime regeneration.

- Related Incidents/Bugs: [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)

- Version/Build: workspace state on 2026-03-29 before `v0.1.3` GA release.

- Config/Flags: live Compass 24h and 48h windows, local audit-day filtering,
  self-host posture snapshot.

- Customer Comms: maintainer-facing. Tell maintainers Compass was counting the
  risk internally but hiding it in the UI, and that the visible release-posture
  signal is now aligned with runtime truth again.

- Code References: `src/odylith/runtime/surfaces/compass_dashboard_shell.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`,
  `tests/unit/runtime/test_compass_dashboard_shell.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`

- Fix Commit/PR: release-prep hardening on 2026-03-29 alongside the `v0.1.3`
  source-truth promotion and Compass browser regression repair.
