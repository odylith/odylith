- Bug ID: CB-091

- Status: Open

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass now has one bounded refresh contract and the visible
  global `24h` and `48h` briefs stay on maintained narrated cache, and the
  latest live payload now keeps every ready brief on narrated cache too. The
  product is still not release-ready because the bounded cold lane remains
  above the founder runtime bar. On the latest measured source-local runs, hot
  exact reuse landed at `0.1s` internal / `0.61s` wall, cold shell-safe
  landed at `0.8s` internal / `1.14s` wall, and the live payload carried
  `39` ready narrated-cache briefs with `0` deterministic ready briefs.

- Impact: Compass now avoids the older stale-global lie, but it still spends
  too much time in the bounded cold path. Live narration quality is back on
  the ready brief set, but the runtime still misses the founder wall-clock
  bar and therefore remains below release readiness.

- Components Affected: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_runtime_reuse.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  Compass component spec, `B-025`, `B-071`, and the `v0.1.11` release note.

- Environment(s): Odylith product-repo maintainer mode, bounded
  `odylith compass refresh --repo-root . --wait`, and the checked-in Compass
  runtime payload.

- Root Cause: The architecture improved in two uneven halves. Maintained
  narrated reuse now protects the global windows, and an exact-reuse hot lane
  exists again after the refresh contract stopped persisting a pre-build input
  fingerprint that self-invalidated on the next run. The remaining scoped
  deterministic dominance turned out to come from two bounded-reuse gaps:
  same-scope cache reuse was still blocked by scoped freshness facts, and one
  recoverable stale current-execution bullet could invalidate an otherwise
  healthy narrated cache candidate. Those are now fixed. The remaining cold
  shell-safe miss is mostly startup, input loading, and runtime-payload
  rebuild cost.

- Solution: Keep deterministic as emergency coverage only, keep ready briefs on
  maintained narrated cache, and continue pushing the product toward two real
  release lanes only: hot exact reuse under `50ms` of internal runtime work
  and complete cold shell-safe refresh under `1s` wall clock. The next cuts
  belong in launcher or import slimming and cheaper incremental projection or
  payload reuse, not in reintroducing fresh provider spend on the default
  path.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_compass_standup_brief_maintenance.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_runtime.py`
    (`143 passed`)
  - `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k 'shell_safe_compass_refresh_artifacts_reuse_warmed_globals_but_do_not_cold_call_provider or compass_scope_window_and_detail_behavior_in_compact_viewport or compass_scoped_brief_missing_fails_closed_instead_of_showing_global or compass_quiet_catalog_scope_reports_quiet_window_instead_of_missing_brief'`
    (`4 passed`)
  - `env PYTHONPATH=src /usr/bin/time -p python3 -m odylith.cli compass refresh --repo-root . --wait`
    produced `elapsed_seconds: 0.8`, `real 1.14`
  - immediate rerun of the same command produced `elapsed_seconds: 0.1`,
    `real 0.61`
  - `odylith/compass/runtime/current.v1.json` now shows global `24h` and `48h`
    as `source=cache`, and the ready-brief source mix now sits at
    `39 cache / 0 deterministic`

- Prevention: Release readiness must stay explicit in governed truth whenever
  Compass misses either of its bounded runtime targets or lets deterministic
  fallback re-emerge as the main ready-brief path. The product must not
  silently treat “globals look better now” as equivalent to full Compass
  release readiness.

- Detected By: Founder review of the live Compass payload and bounded-refresh
  timings after the maintained-global narration fix.

- Failure Signature: Global briefs look healthy, but the overall ready-brief
  source mix has recovered to narrated cache while bounded cold refresh still
  measures above the published wall-clock budget.

- Trigger Path: 1. Run `odylith compass refresh --repo-root . --wait`
  twice without changing source inputs. 2. Inspect `refresh-state.v1.json`
  for internal timings and `current.v1.json` for brief-source mix. 3. Compare
  those numbers against the founder release bar.

- Ownership: Compass refresh architecture, maintained narration strategy,
  bounded runtime contract, and release-readiness truth.

- Invariant Violated: Compass is not release-ready while bounded refresh still
  misses the published hot/cold budgets or while deterministic fallback
  retakes the primary ready-brief path.

- Workaround: Trust the current narrated-cache brief set and accept the cold
  wall-clock miss. That is not acceptable release posture.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not declare Compass release-ready just because global
  `24h` and `48h` are back on narrated cache. The governing numbers are the
  bounded refresh timings first, and the full ready-brief source mix second.

- Related Incidents/Bugs:
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
  [2026-04-09-compass-minute-scale-full-refresh-lane-remained-in-product-after-bounded-contract.md](2026-04-09-compass-minute-scale-full-refresh-lane-remained-in-product-after-bounded-contract.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.
