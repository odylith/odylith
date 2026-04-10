- Bug ID: CB-101

- Status: Closed

- Created: 2026-04-10

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: After switching the Odylith product repo from detached
  `source-local` back to pinned dogfood, the upgrade/dashboard wrapper could
  leave Compass in a queued follow-on state and tell the operator to run
  `odylith compass refresh --repo-root . --wait`, even though the newly
  activated pinned launcher did not expose `compass refresh` at all.

- Impact: The lane switch itself could finish, but the repo was left looking
  half-switched because Compass still needed a follow-on command that the just
  activated launcher rejected. That breaks operator trust at exactly the
  moment when pinned dogfood proof is supposed to feel clean and stable.

- Components Affected: `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/governance/dashboard_refresh_contract.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`, Compass component spec, and
  active Compass hardening governance under `B-025`.

- Environment(s): Odylith product-repo maintainer mode when switching from
  detached `source-local` back to pinned dogfood, plus any dashboard wrapper
  run that refreshes Compass through `odylith dashboard refresh --surfaces compass`.

- Root Cause: The dashboard wrapper treated Compass like an asynchronous side
  job and returned as soon as the request was queued. That was safe only when
  the same command surface remained available afterward. During a lane switch,
  the wrapper activated a different launcher first, then returned a follow-up
  command from the new Compass engine (`odylith compass refresh --wait`) that
  the pinned launcher did not actually support yet.

- Solution: Make the dashboard/upgrade wrapper finish Compass to a bounded
  terminal result before returning control. For failure recovery, route the
  operator back through `odylith dashboard refresh --repo-root . --surfaces compass`,
  which remains the stable compatibility wrapper across launcher generations,
  instead of assuming the direct Compass subcommand is available after the
  switch.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_compass_refresh_runtime.py
  tests/unit/runtime/test_render_compass_dashboard.py
  tests/unit/test_cli.py` passed (`154 passed`). A live source-local lane proof
  via `PYTHONPATH=src python3 -m odylith.cli upgrade --repo-root . --source-repo .`
  now completes the post-upgrade dashboard refresh with `compass refresh passed`
  and `- compass: passed` instead of leaving Compass queued behind a follow-up
  command.

- Prevention: Dashboard wrappers must not hand off to a command surface that
  may have changed underneath them. If a wrapper can trigger a runtime or lane
  transition first, it must either finish Compass inline or keep recovery on a
  wrapper command guaranteed to exist after the switch.

- Detected By: User report after lane switching plus live repro where
  `./.odylith/bin/odylith compass refresh --repo-root . --wait` failed with
  `invalid choice: 'refresh'` immediately after a pinned dogfood activation.

- Failure Signature: `odylith upgrade --repo-root .` reports a queued Compass
  follow-on and points at `odylith compass refresh --repo-root . --wait`, but
  the newly activated launcher rejects `compass refresh` as an unknown
  subcommand.

- Trigger Path: 1. Start in detached `source-local` maintainer posture.
  2. Switch back to pinned dogfood through `odylith upgrade --repo-root .`.
  3. Let the upgrade path refresh dashboard surfaces. 4. Follow the printed
  Compass wait command on the newly activated launcher.

- Ownership: Compass dashboard wrapper contract, lane-switch upgrade ergonomics,
  and post-switch recovery command safety.

- Timeline: The shared Compass refresh engine cleaned up the direct source-local
  command surface first, but the older pinned launcher did not yet expose the
  same nested `compass refresh` subcommand. The wrapper still assumed it did,
  which only surfaced once a lane switch changed the active launcher between
  queueing Compass and telling the operator how to wait for it.

- Blast Radius: Every product-repo maintainer lane switch and any wrapper path
  that queues Compass then tells the operator to use a direct Compass command
  the activated launcher may not support.

- SLO/SLA Impact: No outage, but a direct workflow break in a high-trust
  maintainer operation.

- Data Risk: Low source-truth corruption risk; medium operator workflow risk
  because the pinned proof lane can look incomplete even when the switch
  itself succeeded.

- Security/Compliance: None directly.

- Invariant Violated: A lane-switch wrapper must not leave the operator with a
  required next command that the just activated launcher cannot run.

- Workaround: Re-run `odylith dashboard refresh --repo-root . --surfaces compass`
  from a command surface that still exists after the switch. The product
  should not require the operator to reason this out.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: When a wrapper activates a different runtime or launcher,
  do not emit recovery or wait commands that assume the pre-switch command
  surface still exists afterward.

- Preflight Checks: Inspect
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/governance/dashboard_refresh_contract.py`, and the
  Compass wrapper path inside `odylith upgrade` before changing lane-switch
  refresh behavior.

- Regression Tests Added: `tests/unit/runtime/test_sync_cli_compat.py`.

- Monitoring Updates: Watch for any dashboard-refresh or upgrade output that
  reports `compass: queued` immediately after a runtime switch or prints a
  Compass follow-up command rejected by the activated launcher.

- Residual Risk: Direct `odylith compass refresh` still belongs to the current
  bounded Compass contract, but older pinned launchers may lag that subcommand
  until the next release ships. The wrapper now shields that mismatch instead
  of exposing it to operators during lane changes.

- Related Incidents/Bugs:
  [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
  [2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md](2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md)

- Version/Build: Odylith product repo working tree on 2026-04-10.

- Config/Flags: Product-repo maintainer lane switch from detached `source-local`
  to pinned dogfood; default dashboard wrapper surfaces.

- Customer Comms: Tell maintainers that lane-switch dashboard refresh now
  finishes Compass before returning and that any retry stays on the stable
  dashboard wrapper command instead of a launcher-specific Compass subcommand.

- Code References: `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `src/odylith/runtime/governance/dashboard_refresh_contract.py`

- Runbook References: `odylith/registry/source/components/compass/CURRENT_SPEC.md`,
  `odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md`

- Fix Commit/PR: Pending.
