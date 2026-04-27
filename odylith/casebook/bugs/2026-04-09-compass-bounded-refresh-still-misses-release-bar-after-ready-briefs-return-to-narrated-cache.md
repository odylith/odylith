- Bug ID: CB-091

- Status: Open

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Compass now has one bounded refresh contract and the visible
  global `24h` and `48h` briefs stay on maintained narrated cache, and the old
  stock phrasing is no longer replayed from cached runtime payloads. The
  product is still not release-ready because the rebuilt bounded lane remains
  above the founder runtime bar. On the latest measured source-local runs,
  exact reuse landed at `0.3s` internal / `0.73s` wall, the rebuilt bounded
  refresh landed at `1.7s` internal / `2.18s` wall, and the live payload
  carried `35` ready briefs with `35` narrated cache and `0` deterministic
  scoped fallbacks. A deeper architecture follow-on also made the hidden cost
  problem explicit: Compass had been debating timer cadence and narrator
  availability in the same place. The correct product contract is push-style
  local change detection, local shell-safe rebuild on fingerprint change, and
  background narration warming only after the blocking path is done.

- Impact: Compass now avoids the older stale-global lie and it no longer
  replays the cached stock lines that made live narration feel templated
  again, and the deterministic scoped tail is gone, but it still spends too
  much time on rebuilt refresh. Release readiness is still blocked on runtime
  latency alone, and any attempt to "fix" that by reintroducing foreground
  provider narration or tight freshness heartbeats would just move the cost to
  credits or constant wakeups instead of solving the architecture.

- Components Affected: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_runtime_reuse.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  Compass component spec, `B-025`, `B-071`, and the `v0.1.11` release note.

- Environment(s): Odylith product-repo maintainer mode, bounded
  `odylith compass refresh --repo-root . --wait`, and the checked-in Compass
  runtime payload.

- Root Cause: The architecture improved in three uneven halves. Maintained
  narrated reuse protects the global windows, and exact runtime reuse now
  survives date rollover because it keys off exact input fingerprint instead
  of a small snapshot-age budget. Cached narrated sections are also forced
  back through the current voice validator before reuse, which is what stopped
  old stock lines from replaying forever. The remaining miss is narrower:
  rebuilt shell-safe refresh still spends most of its time in input loading
  and payload construction, even after the ready-brief population returned
  fully to narrated cache. The freshness trigger contract was also not clean
  enough: Compass was still treating timer cadence, rebuild cost, and narrator
  availability as one mixed concern instead of separating change detection,
  local rebuild, and background narration.

- Solution: Keep deterministic as emergency coverage only, keep the visible
  globals on maintained narrated cache, keep provider spend off the blocking
  path entirely, and continue pushing the product toward two real release
  lanes only: hot exact reuse under `50ms` of internal runtime work and
  complete rebuilt shell-safe refresh under `1s` wall clock. The refresh
  trigger should be push-first and fingerprint-driven: watcher event, cheap
  fingerprint check, one shell-safe rebuild, then one deduped background warm
  if narration is missing. The next cuts belong in launcher/import slimming,
  incremental projection or payload reuse, and watcher-backed invalidation,
  not in reintroducing fresh provider spend or aggressive timer loops on the
  default path.

- Verification:
  - `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_compass_standup_brief_maintenance.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_runtime.py`
    (`138 passed` on the focused narrator/runtime/render lane after the cache-voice and exact-reuse fixes, plus `39 passed` on the Compass browser/runtime regression lane)
  - `env PYTHONPATH=src /usr/bin/time -p python3 -m odylith.cli compass refresh --repo-root . --wait`
    produced `elapsed_seconds: 1.7`, `real 2.18` on the latest rebuilt run
  - immediate rerun of the same command produced `elapsed_seconds: 0.4`,
    then `elapsed_seconds: 0.3`, `real 0.73` after the CLI import slimming
  - `odylith/compass/runtime/current.v1.json` now shows global `24h` and `48h`
    as `source=cache`, the cached stock lines no longer appear in the live
    payload, and the ready-brief source mix now sits at `35 cache / 0 deterministic`

- Prevention: Release readiness must stay explicit in governed truth whenever
  Compass misses either of its bounded runtime targets or lets deterministic
  fallback re-emerge as the main ready-brief path. The product must not
  silently treat “globals look better now” as equivalent to full Compass
  release readiness. It also must not confuse cheap change detection with
  cheap refresh: push-style watcher wakeups are the normal answer, coarse
  polling is only a last resort, and foreground provider narration is not part
  of the shell-safe recovery budget.

- Detected By: Founder review of the live Compass payload and bounded-refresh
  timings after the maintained-global narration fix.

- Failure Signature: Global briefs look healthy, but the overall ready-brief
  source mix is healthy and rebuilt bounded refresh still measures above the
  published wall-clock budget.

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
  `24h` and `48h` are back on narrated cache or because the stock phrasing is
  gone from the visible brief. The governing numbers are the rebuilt refresh
  timings first, the exact-reuse lane second, and the full ready-brief source
  mix third.

- Related Incidents/Bugs:
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
  [2026-04-09-compass-minute-scale-full-refresh-lane-remained-in-product-after-bounded-contract.md](2026-04-09-compass-minute-scale-full-refresh-lane-remained-in-product-after-bounded-contract.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.
