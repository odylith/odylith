- Bug ID: CB-019

- Status: Closed

- Created: 2026-03-29

- Severity: P1

- Reproducibility: Intermittent but user-visible

- Type: Product

- Description: Compass could render stale global standup briefs, undercount
  critical risks, and show empty-looking audit timelines even though current
  Odylith source truth contained fresher bug, event, and transaction evidence.
  The same shell session could also surface different Compass freshness
  posture depending on route history and runtime reuse.

- Impact: Compass is supposed to be the live executive read model over Odylith
  work, so stale brief, risk, and timeline output undermines operator trust in
  the entire shell.

- Components Affected: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/runtime/context_engine/surface_projection_fingerprint.py`,
  Compass runtime freshness contract, shell UX/browser proof lane.

- Environment(s): local Odylith shell in the product repo; shared shell flows
  after cross-tab navigation and reload.

- Root Cause: Compass reused runtime snapshots too aggressively for rolling
  24h/48h windows, the warmed projection fingerprint did not invalidate when
  bug-projection parser semantics changed, and standup-brief recovery could
  reuse a stale last-known-good global AI brief across changed fact packets
  instead of narrating the current packet deterministically.

- Solution: tighten Compass runtime freshness with an age budget, version the
  bug projection contract into the projection fingerprint, remove stale
  cross-packet global brief reuse, and expand headless browser proof across
  shell surfaces so stale counts, stale briefs, and empty timeline regressions
  are caught end to end.

- Verification: Closed after reconciling the full B-025 Compass hardening
  stack. `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_compass_standup_brief_narrator.py
  tests/unit/runtime/test_compass_dashboard_runtime.py
  tests/unit/runtime/test_render_tooling_dashboard.py` passed with `84 passed`;
  `PYTHONPATH=src python -m pytest -q
  tests/integration/runtime/test_surface_browser_deep.py -k
  'shell_compass_tab_dedupes_stale_runtime_status_to_compass_notice or
  shell_compass_tab_surfaces_failed_full_refresh_warning'` passed with
  `2 passed, 21 deselected`; `python -m py_compile
  src/odylith/runtime/surfaces/compass_standup_brief_narrator.py
  src/odylith/runtime/surfaces/tooling_dashboard_surface_status.py
  tests/unit/runtime/test_compass_standup_brief_narrator.py
  tests/integration/runtime/test_surface_browser_deep.py` passed; and
  `git diff --check` passed.

- Prevention: Compass and other rolling-window shell surfaces must treat time
  passage as a first-class invalidation input, and browser proof should assert
  fresh KPI, brief, and timeline behavior after cross-tab and reload flows.

- Detected By: user report with screenshots showing missing fresh brief/timeline
  context and inconsistent Compass behavior.

- Failure Signature: Compass shows `AI narrative · last known good cache` or a
  deterministic fallback even when fresh local evidence exists, critical-risk
  KPIs collapse toward zero, and timeline panels show empty-state rows despite
  a populated runtime history.

- Trigger Path: revisit Compass after cross-tab navigation, reload, or elapsed
  time without a full runtime rebuild; especially on global 24h/48h views.

- Ownership: Compass runtime freshness, projection invalidation, standup-brief
  recovery policy, and UX/browser hardening.

- Timeline: reported on 2026-03-29; the runtime reuse, cache, narrator,
  refresh-contract, and browser-proof fixes landed across the B-025 hardening
  follow-ons and this umbrella bug was closed after final proof reconciliation.

- Blast Radius: Compass directly, plus the broader shell trust model because
  Compass is the only surface that blends live bugs, plans, delivery, and
  audit trails.

- SLO/SLA Impact: no outage, but meaningful product-trust regression in a core
  decision surface.

- Data Risk: low for source truth, medium for operator decisions because stale
  presentation can hide real bug and timeline pressure.

- Security/Compliance: no direct security issue, but stale operational read
  models reduce confidence in a safety-critical local governance surface.

- Invariant Violated: a rolling Compass window should reflect current Odylith
  truth and should not silently reuse stale brief or risk state once the fact
  packet or freshness budget changes.

- Workaround: rerender Compass or force a broader sync, but that is not an
  acceptable steady-state operator workflow.

- Rollback/Forward Fix: Forward fix. Reverting the freshness hardening would
  reintroduce stale runtime reuse and stale brief recovery.

- Agent Guardrails: do not widen browser proof only around Compass. Cover the
  broader shell UX/UI flows that can feed stale or leaked state back into
  Compass.

- Preflight Checks: inspect [render_compass_dashboard.py](../../../src/odylith/runtime/surfaces/render_compass_dashboard.py),
  [compass_standup_brief_narrator.py](../../../src/odylith/runtime/surfaces/compass_standup_brief_narrator.py),
  [surface_projection_fingerprint.py](../../../src/odylith/runtime/context_engine/surface_projection_fingerprint.py),
  and [test_surface_browser_smoke.py](../../../tests/integration/runtime/test_surface_browser_smoke.py)
  before changing Compass freshness or shell browser proof again.

- Regression Tests Added:
  `tests/unit/runtime/test_compass_standup_brief_narrator.py`
  now proves global changed packets do not reuse stale cache and that
  self-host/install posture drift changes the standup fingerprint and forces
  current narration instead of cached reuse; shell/Compass browser proof in
  `tests/integration/runtime/test_surface_browser_deep.py` also covers stale
  versus failed-refresh disclosure on the Compass tab without leaking
  out-of-retention Compass history fetch 404s into the shell page.

- Monitoring Updates: Keep watching Compass brief source/notice state and
  self-host posture facts for any case where global changed-packet renders
  regress back to cache reuse, wrapper-only stale disclosure, or retained
  history-range violations from stale live snapshots.

- Related Incidents/Bugs: [2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md](2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md)

- Version/Build: workspace state on 2026-03-29 before Compass runtime
  freshness hardening and widened UX/browser proof.

- Config/Flags: Compass `window`, Compass `scope`, shell `tab`,
  `runtime_contract.input_fingerprint`, standup-brief cache reuse.

- Customer Comms: tell operators Compass source truth was intact, but the local
  runtime reuse and brief recovery policy could show stale blended state. The
  fix makes current bug, brief, and timeline context reactive again.

- Code References: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/runtime/context_engine/surface_projection_fingerprint.py`,
  `tests/unit/runtime/test_render_compass_dashboard.py`,
  `tests/unit/runtime/test_compass_standup_brief_narrator.py`,
  `tests/integration/runtime/test_surface_browser_smoke.py`

- Runbook References: `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`,
  `odylith/agents-guidelines/VALIDATION_AND_TESTING.md`

- Fix Commit/PR: `2026/freedom/v0.1.10` Compass closeout series.
