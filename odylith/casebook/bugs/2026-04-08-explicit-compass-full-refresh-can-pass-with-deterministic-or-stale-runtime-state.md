- Bug ID: CB-068

- Status: Closed

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Explicit Compass full refresh still has no single fail-closed
  contract from render start through shell and browser consumption. An operator
  can ask for a deep Compass refresh and still end up with a surface that looks
  recently refreshed while it is backed by the wrong reused runtime payload,
  deterministic local narration, or stale child-runtime state instead of a
  fully rebuilt current Compass read model. The existing five-minute reuse
  clamp is not the bug; reusing a payload that does not already satisfy the
  requested full-refresh truth contract is.

- Impact: Compass is the product's live executive read surface. If
  `odylith dashboard refresh --repo-root . --surfaces compass
  --compass-refresh-profile full` can complete or appear current without
  recomputing current packets, briefs, window summaries, and audit timelines,
  the operator loses trust in Compass, the shell, and the refresh command
  itself.

- Components Affected: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/governance/dashboard_refresh_contract.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  Compass full-refresh contract, shell/browser freshness proof.

- Environment(s): product-repo maintainer mode and consumer repos using
  explicit Compass refresh.

- Root Cause: Compass full refresh still spreads its truth contract across too
  many layers. The renderer's five-minute reuse clamp is valid, but it does not
  yet distinguish between a recent payload that already satisfies the requested
  full-refresh contract and a recent payload that is still shell-safe,
  deterministic, or otherwise not deep-refresh-clean. The standup narrator can
  still succeed via deterministic or stale-recovery paths that were designed
  for bounded `shell-safe` refresh, and browser proof does not yet explicitly
  assert that a successful full rerender never lands on the deterministic brief
  banner or stale child-runtime state across 24h, 48h, and scoped
  current-workstream views.

- Solution: Introduce one explicit full-refresh contract and enforce it
  end-to-end. Keep the five-minute runtime reuse clamp, but only let explicit
  Compass `full` reuse a recent payload when that payload already satisfies the
  requested deep-refresh truth bar. Full refresh must otherwise rebuild current
  packets, must prefer live provider-backed brief generation for global and
  scoped packets, may reuse only exact current-packet AI brief cache as a
  bounded recovery path, and must fail the render instead of writing
  deterministic or stale fallback state on a passing run. Browser proof must
  assert that successful full-refresh artifacts do not land on the
  deterministic local brief banner and that 24h, 48h, scoped brief, and
  timeline/audit state all resolve from the refreshed payload.

- Verification: Fixed on 2026-04-08. `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_compass_refresh_contract.py
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_compass_standup_brief_narrator.py
  tests/unit/runtime/test_sync_cli_compat.py` passed with `104 passed`;
  `python3 -m py_compile
  src/odylith/runtime/surfaces/compass_refresh_contract.py
  src/odylith/runtime/surfaces/render_compass_dashboard.py
  src/odylith/runtime/surfaces/compass_dashboard_runtime.py
  src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py
  src/odylith/runtime/surfaces/compass_standup_brief_narrator.py
  src/odylith/runtime/governance/dashboard_refresh_contract.py
  tests/unit/runtime/test_compass_refresh_contract.py
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_compass_standup_brief_narrator.py
  tests/integration/runtime/test_surface_browser_deep.py` passed; `git diff
  --check` passed; and the targeted browser regression command
  `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k "explicit_full_compass_refresh_artifacts_do_not_show_deterministic_brief or compass_scope_window_and_detail_behavior_in_compact_viewport"`
  executed locally and completed with `2 skipped, 19 deselected` because
  Playwright/Chromium is unavailable on this workstation.

- Prevention: Explicit operator refresh needs one contract for payload reuse,
  brief fallback, timeout budget, and shell/browser freshness proof. Bounded
  `shell-safe` behavior is allowed to defer, but `full` must not silently
  degrade into the same semantics.

- Detected By: maintainer escalation after repeated Compass refresh feedback
  packets and downstream repros that still showed deterministic local briefs or
  stale Compass state after operator-requested refresh attempts.

- Failure Signature: Explicit Compass full refresh leaves `deterministic local
  brief`, provider-deferred notices, or older child-runtime timestamps visible
  after the operator asked for a fresh full render, or the command reuses a
  recent payload that still reflects shell-safe or stale Compass state instead
  of a deep-refresh-clean read model.

- Trigger Path: run `odylith dashboard refresh --repo-root . --surfaces
  compass --compass-refresh-profile full`, then inspect global 24h/48h,
  current workstream scope selection, and timeline audit state in Compass or
  the top-level shell.

- Ownership: Compass refresh contract, standup narrator fallback policy,
  shell/browser proof lane.

- Timeline: escalated on 2026-04-08 after multiple partial fixes still left the
  product without a single trustworthy explicit full-refresh contract.

- Blast Radius: Compass refresh UX, shell trust posture, and release confidence
  around live runtime freshness.

- SLO/SLA Impact: no outage, but direct operator-trust regression in a core
  refresh path.

- Data Risk: low source-truth risk; high presentation risk because stale or
  deterministic Compass state can be mistaken for freshly recomputed truth.

- Security/Compliance: none directly.

- Invariant Violated: A successful explicit Compass full refresh must represent
  freshly rebuilt current Compass truth end to end; it must not quietly pass
  with deterministic or stale runtime state.

- Workaround: rerun Compass refresh, inspect timestamps manually, or distrust
  the standup brief until deeper validation is done. None is acceptable as the
  normal operator path.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not solve this by only increasing the timeout. Tighten
  the refresh contract across runtime reuse, narrator fallback, and browser
  proof together.

- Preflight Checks: inspect
  [render_compass_dashboard.py](../../../src/odylith/runtime/surfaces/render_compass_dashboard.py),
  [compass_runtime_payload_runtime.py](../../../src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py),
  [compass_standup_brief_narrator.py](../../../src/odylith/runtime/surfaces/compass_standup_brief_narrator.py),
  and [test_surface_browser_deep.py](../../../tests/integration/runtime/test_surface_browser_deep.py)
  before changing Compass full-refresh behavior again.

- Regression Tests Added:
  `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_compass_refresh_contract.py
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_compass_standup_brief_narrator.py
  tests/unit/runtime/test_sync_cli_compat.py`
  and the targeted browser regression in
  `tests/integration/runtime/test_surface_browser_deep.py::test_explicit_full_compass_refresh_artifacts_do_not_show_deterministic_brief`

- Monitoring Updates: Watch explicit Compass `full` refresh proof for any case
  where a recent payload is reused even though its brief source/notice state
  does not already satisfy the deep-refresh contract, and keep the browser
  regression focused on eliminating the deterministic brief banner from a
  successful full-refresh artifact.

- Related Incidents/Bugs:
  [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)

- Version/Build: product-repo workspace on 2026-04-08 before the unified
  full-refresh contract hardening pass.

- Config/Flags: `odylith dashboard refresh --repo-root . --surfaces compass
  --compass-refresh-profile full`, Compass 24h/48h windows, current-workstream
  scoped briefs, runtime payload reuse, standup-brief cache and fallback.

- Customer Comms: Tell operators the product is tightening explicit full
  Compass refresh so it either lands fresh runtime truth or fails clearly; it
  will no longer quietly pass with deterministic or stale Compass state.

- Code References: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/governance/dashboard_refresh_contract.py`,
  `tests/unit/runtime/test_render_compass_dashboard.py`,
  `tests/unit/runtime/test_compass_standup_brief_narrator.py`,
  `tests/integration/runtime/test_surface_browser_deep.py`

- Runbook References:
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: `2026/freedom/v0.1.10` Compass closeout series.

- Historical Note: On 2026-04-09, Compass retired the old minute-scale
  `full` lane entirely under `CB-086` instead of preserving it as a standing
  product mode.
