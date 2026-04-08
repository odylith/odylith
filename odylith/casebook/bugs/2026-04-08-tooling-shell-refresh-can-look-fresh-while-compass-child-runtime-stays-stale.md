- Bug ID: CB-067

- Status: Closed

- Created: 2026-04-08

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: After a shell-only refresh succeeds, the top-level tooling shell
  can still present an obviously stale Compass standup brief as if it were the
  current shell state. In downstream proof on 2026-04-07, Compass first
  refreshed successfully in bounded `shell-safe` mode, then explicit
  `--compass-refresh-profile full` failed twice under the dashboard wrapper
  timeout, and then `odylith dashboard refresh --repo-root . --surfaces
  tooling_shell` passed. The wrapper assets at `odylith/index.html` refreshed,
  but the shell still pointed at the older Compass child runtime snapshot in
  `odylith/compass/runtime/current.v1.json`, so the operator kept seeing the
  stale `DETERMINISTIC LOCAL BRIEF` card from `Generated Apr 07, 2026, 17:06`
  with no shell-level admission that Compass data had not been refreshed by the
  successful shell render.

- Impact: A successful shell refresh can look like a successful Compass refresh
  even when the visible Compass brief still comes from an older child-runtime
  snapshot. That is an operator-trust bug, not just a cosmetic mismatch:
  wrapper freshness and child-surface freshness diverge, but the shell does not
  tell the truth about the divergence.

- Components Affected: `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, tooling shell
  refresh contract, Compass child-runtime freshness projection, shell runtime
  status messaging.

- Environment(s): Consumer shell lane and maintainer proof lanes when the
  shell is refreshed without simultaneously rerendering Compass, especially
  after a failed explicit Compass full refresh.

- Root Cause: Odylith fixed the Compass-side failure marker and the bogus full
  refresh hint, but the top-level shell still treated its own wrapper render as
  the only freshness signal it needed. `render_tooling_dashboard.py` refreshed
  `odylith/index.html` and shell bundle assets without reading the current
  Compass child-runtime posture, and the shell runtime-status card in
  `control.js` still had no logic to expose a stale or failed child-surface
  state. That left a truthful Compass runtime warning trapped inside the child
  payload while the shell-level success path stayed visually silent.

- Solution: When the shell renderer refreshes, read the current Compass runtime
  snapshot and project a shell-facing child-surface freshness status into the
  shell payload. If the shell wrapper is newer than the current Compass runtime
  by a meaningful gap, or if the latest explicit Compass full refresh failed,
  the product must say so instead of implying the visible brief is current.
  Ordinary stale-snapshot age now stays disclosed once inside the Compass
  frame itself, while shell runtime-status cards are reserved for failed
  deeper-refresh or cross-surface posture the child frame cannot already
  explain. The shell refresh plan should also say that shell-only refresh
  updates the wrapper, not Compass child-runtime truth.

- Verification: Fixed on 2026-04-08. `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_render_tooling_dashboard.py
  tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_render_compass_dashboard.py`
  passed with `76 passed`, and the resumed browser proof on the same date
  passed with `PYTHONPATH=src python3 -m pytest -q
  tests/integration/runtime/test_surface_browser_smoke.py -k "compass or shell"
  tests/integration/runtime/test_surface_browser_deep.py -k "compass or shell"
  tests/integration/runtime/test_surface_browser_ux_audit.py -k "compass"
  tests/integration/runtime/test_surface_browser_filter_audit.py -k "compass"`
  (`15 passed, 34 deselected`). That resumed browser lane also proved the
  shell-bootstrap follow-on fix in `control.js`: precomputed Compass stale or
  failed-full-refresh status now stays visible on first load and after runtime
  probes instead of being cleared by an empty probe payload. The final
  closeout proof then passed with `PYTHONPATH=src python -m pytest -q
  tests/integration/runtime/test_surface_browser_deep.py -k
  'shell_compass_tab_dedupes_stale_runtime_status_to_compass_notice or
  shell_compass_tab_surfaces_failed_full_refresh_warning'` (`2 passed,
  21 deselected`) and `PYTHONPATH=src python -m pytest -q
  tests/integration/runtime/test_surface_browser_deep.py -k compass`
  (`10 passed, 13 deselected`), confirming one stale warning and no retained-
  history 404 leakage in the shell lane.

- Prevention: Shell refresh must not claim freshness for Compass-derived
  sections unless the Compass child-runtime snapshot was actually refreshed, or
  the shell explicitly says it was not.

- Detected By: Downstream maintainer packet on 2026-04-08 based on
  `/Users/freedom/code/dentoai-orion` shell and Compass artifact timestamps.

- Failure Signature: `odylith dashboard refresh --repo-root . --surfaces
  tooling_shell` passes, `odylith/index.html` has a newer write time than
  `odylith/compass/runtime/current.v1.json`, and the shell still shows the old
  Compass deterministic brief without a shell-level stale-runtime warning.

- Trigger Path: 1. Refresh Compass in default `shell-safe` mode. 2. Attempt and
  fail explicit Compass `full` refresh. 3. Refresh only `tooling_shell`. 4.
  Open or stay on the Compass tab in the shell.

- Ownership: Dashboard shell refresh contract, Compass child-runtime truth
  projection, shell runtime-status messaging.

- Timeline: This surfaced immediately after the prior Compass refresh hardening
  slice closed. The Compass child runtime now marks failed full refreshes
  truthfully, and the final closeout on 2026-04-08 also removed the redundant
  wrapper-level stale banner so ordinary stale age is disclosed once, inside
  Compass, instead of twice across shell and child frame.

- Blast Radius: Any lane where operators use the shell as the parent entrypoint
  and assume a successful shell refresh means the visible Compass brief is also
  current.

- SLO/SLA Impact: No hard outage, but direct operator-trust damage in a core
  shell workflow.

- Data Risk: Low source-of-truth risk; medium operator-decision risk because
  the shell can visually imply freshness for an older Compass snapshot.

- Security/Compliance: None directly.

- Invariant Violated: The shell must not present child-surface content as
  current just because the wrapper refreshed successfully.

- Workaround: Run a real Compass rerender command and then reload the shell, or
  inspect Compass runtime artifacts directly. Neither is acceptable as the
  default operator contract.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not treat shell-wrapper success as child-surface success
  unless the shell can prove the child runtime is fresh enough for that claim.

- Preflight Checks: Inspect CB-050, the active B-060 plan, `render_tooling_dashboard.py`,
  the shell runtime-status logic in `templates/tooling_dashboard/control.js`,
  and the current Compass runtime contract in
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`.

- Regression Tests Added:
  `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_render_tooling_dashboard.py
  tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_render_compass_dashboard.py`
  plus the browser regressions in
  `tests/integration/runtime/test_surface_browser_deep.py::test_shell_compass_tab_dedupes_stale_runtime_status_to_compass_notice`
  and
  `tests/integration/runtime/test_surface_browser_deep.py::test_shell_compass_tab_surfaces_failed_full_refresh_warning`
  plus the resumed shell/Compass browser sweep
  `PYTHONPATH=src python3 -m pytest -q
  tests/integration/runtime/test_surface_browser_smoke.py
  tests/integration/runtime/test_surface_browser_deep.py
  tests/integration/runtime/test_surface_browser_ux_audit.py
  tests/integration/runtime/test_surface_browser_filter_audit.py -k "compass or shell"`
  (`24 passed, 25 deselected`)

- Monitoring Updates: Watch shell refresh proof for cases where
  `odylith/index.html` advances while `odylith/compass/runtime/current.v1.json`
  does not, ensure failure-only shell status remains available when Compass
  cannot explain the problem itself, keep the Compass in-frame stale notice as
  the only ordinary stale-age warning, and keep browser proof watching the
  first-load/runtime-probe handoff so shell-computed child-runtime status
  cannot be cleared by a later probe that lacks shell-facing posture fields.

- Residual Risk: Even after the shell truth fix, shell-only refresh still does
  not rerender Compass. That is acceptable only if the shell keeps admitting
  the difference instead of pretending otherwise.

- Related Incidents/Bugs:
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)

- Version/Build: Odylith product repo working tree on 2026-04-08.

- Config/Flags: `odylith dashboard refresh --repo-root . --surfaces tooling_shell`
  after earlier Compass `shell-safe` and failed `full` refresh attempts.

- Customer Comms: Tell operators that shell-only refresh updates the wrapper
  frame, not Compass child-runtime truth, and the shell will now say when the
  visible Compass brief still comes from an older snapshot.

- Code References: `src/odylith/runtime/surfaces/render_tooling_dashboard.py`,
  `src/odylith/runtime/surfaces/templates/tooling_dashboard/control.js`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `tests/unit/runtime/test_render_tooling_dashboard.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`

- Runbook References: `odylith/registry/source/components/dashboard/CURRENT_SPEC.md`,
  `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/maintainer/AGENTS.md`

- Fix Commit/PR: `2026/freedom/v0.1.10` Compass closeout series.
