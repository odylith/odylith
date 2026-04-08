- Bug ID: CB-047

- Status: Closed

- Created: 2026-04-02

- Fixed: 2026-04-02

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: `odylith dashboard refresh --repo-root . --surfaces compass`
  rendered Compass in `shell-safe` mode, but that mode could simply reuse the
  existing `odylith/compass/runtime/current.v1.json` snapshot instead of
  rebuilding it. Timeline Audit then stayed pinned to the last snapshot time
  such as `Apr 02, 2026, 14:00`, even after new local work landed and the
  operator asked for a refresh.

- Impact: Compass is supposed to be the trustworthy live audit surface across
  consumer, detached maintainer-dev, and other shell-backed lanes. When an
  explicit dashboard refresh keeps serving the old snapshot, operators can miss
  current Timeline Audit events and lose trust in the shell’s “refresh”
  contract.

- Components Affected: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  Compass shell-safe refresh contract,
  `tests/unit/runtime/test_render_compass_dashboard.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`.

- Environment(s): Consumer and maintainer-dev shell lanes that rely on
  `odylith dashboard refresh` or other Compass shell-safe refresh paths.

- Root Cause: `refresh_runtime_artifacts(..., refresh_profile="shell-safe")`
  treated shell-safe as “reuse a bounded stale snapshot” and returned the
  existing `current.v1.json` for up to 24 hours. That bypassed the actual
  runtime payload rebuild path, so newer local changes and codex-event inputs
  never reached Timeline Audit, and the provider-deferral logic that already
  existed for bounded rebuilds never ran.

- Solution: Redefine `shell-safe` as a bounded rebuild mode rather than stale
  snapshot reuse. `render_compass_dashboard.refresh_runtime_artifacts` now
  rebuilds Compass when the snapshot is older than the normal fast-reuse budget,
  passes the `refresh_profile` through to the runtime payload builder, and the
  global standup brief path defers live provider narration in shell-safe mode so
  the refresh stays deterministic and bounded. The shell-safe path also works
  without a preexisting snapshot.

- Verification: `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/runtime/test_compass_dashboard_runtime.py` passed with `21 passed`;
  `python -m py_compile src/odylith/runtime/surfaces/render_compass_dashboard.py
  src/odylith/runtime/surfaces/compass_dashboard_runtime.py
  src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py` passed.

- Prevention: Any refresh profile exposed to operators as a real refresh must
  rebuild runtime-backed truth once the fast exact-cache window expires. “Safe”
  can mean provider-deferred and deterministic; it must not mean “keep serving
  the old snapshot.”

- Detected By: User report with screenshots on 2026-04-02 showing Compass
  still pinned to `14:00` and explicitly calling out that Timeline Audit had no
  new events since then.

- Failure Signature: Compass banner reads `Compass snapshot Apr 02, 2026, 14:00
  is 8.8h old; timeline stays pinned there. Refresh: odylith dashboard refresh
  --repo-root .` while the Timeline Audit card shows no post-14:00 events.

- Trigger Path: Run `odylith dashboard refresh --repo-root . --surfaces compass`
  after new local work or codex-event updates, then open Compass live view and
  expect Timeline Audit to advance.

- Ownership: Compass runtime freshness contract and shell-facing dashboard
  refresh path.

- Timeline: The user reported a visibly stale 14:00 Timeline Audit late on
  2026-04-02. Runtime inspection showed the shell-facing refresh command still
  targeting `shell-safe`, while the renderer treated that profile as stale
  snapshot reuse instead of a bounded rebuild. The fix moved shell-safe onto the
  bounded rebuild path and added unit coverage for both stale-snapshot and
  no-existing-snapshot cases.

- Blast Radius: All lanes that rely on Compass dashboard refresh, especially the
  shell surfaces where operators expect explicit refresh to update Timeline
  Audit without a full sync.

- SLO/SLA Impact: No outage, but a direct freshness and operator-trust
  regression in a core shell surface.

- Data Risk: Low source-truth risk; medium operator-decision risk because the
  timeline read model can omit current execution evidence.

- Security/Compliance: None directly; the issue is runtime read-model
  freshness and operator trust.

- Invariant Violated: Explicit Compass dashboard refresh must not preserve an
  old `current.v1.json` snapshot once the runtime reuse window has expired.

- Workaround: Run `odylith compass update --repo-root .` or a full Compass
  render instead of relying on shell-safe dashboard refresh.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: When a refresh mode exists to keep shell refresh bounded,
  defer provider-backed narration rather than reusing a stale runtime payload.
  Verify the runtime payload builder actually executes for stale snapshots.

- Preflight Checks: Inspect `render_compass_dashboard.py` refresh-profile
  branches, confirm `current.v1.json` `generated_utc` advances after refresh,
  and verify shell-safe still suppresses provider-backed global brief work.

- Regression Tests Added:
  `test_refresh_runtime_artifacts_shell_safe_rebuilds_stale_snapshot_in_bounded_mode`,
  `test_refresh_runtime_artifacts_shell_safe_builds_without_existing_snapshot`,
  `test_global_brief_provider_allowed_disables_provider_for_shell_safe`,
  `test_global_brief_provider_allowed_uses_default_policy_for_full_refresh`

- Monitoring Updates: Unit coverage now locks the shell-safe contract to
  bounded rebuild plus provider deferral instead of stale runtime reuse.

- Residual Risk: This closes the stale shell-safe reuse path, but other Compass
  freshness gaps could still surface if upstream event capture misses new local
  work entirely.

- Related Incidents/Bugs:
  [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)

- Version/Build: Odylith product repo working tree on 2026-04-02.

- Config/Flags: Compass `24h` and `48h` windows, live runtime `date=live`,
  shell-safe dashboard refresh, bounded provider deferral.

- Customer Comms: Tell operators that `odylith dashboard refresh` now rebuilds
  Compass in bounded deterministic mode, so Timeline Audit advances again
  without requiring the heavier `odylith compass update` fallback.

- Code References: `src/odylith/runtime/surfaces/render_compass_dashboard.py`,
  `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`,
  `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`,
  `tests/unit/runtime/test_render_compass_dashboard.py`,
  `tests/unit/runtime/test_compass_dashboard_runtime.py`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: `2026/freedom/v0.1.10` Compass closeout series.
