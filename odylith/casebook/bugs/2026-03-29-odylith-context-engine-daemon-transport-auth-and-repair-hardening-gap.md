- Bug ID: CB-021

- Status: Closed

- Created: 2026-03-29

- Fixed: 2026-03-29

- Severity: P1

- Reproducibility: Intermittent

- Type: Tooling

- Description: Odylith Context Engine daemon safety was hardened only in the
  CLI-side client path. The store-side daemon client still trusted stale pid
  and socket state, accepted TCP transport hints without loopback validation,
  and omitted daemon auth-token forwarding. The repair reset path also deleted
  runtime files without first stopping a live daemon. Together those gaps left
  a real recurrence path for local process leaks, unaudited daemon reuse, and
  weaker-than-intended local transport trust.

- Impact: Odylith could reconnect to dead or mismatched local daemon artifacts,
  fail to stop a live daemon before cleanup, or accept a tampered local TCP
  transport hint. That weakens local operator trust, risks leaving background
  processes behind during repair, and leaves the local daemon boundary less
  secure than the product contract claims.

- Components Affected: `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/install/repair.py`, Odylith Context Engine local daemon
  transport contract, repair reset-local-state flow, daemon hardening tests.

- Environment(s): local dev, maintainer runtime loops, and consumer-installed
  repos using the local Context Engine daemon.

- Root Cause: The previous autospawn leak fix hardened the explicit CLI daemon
  client and server contract, but Odylith still carried a second daemon client
  implementation in `odylith_context_engine_store.py`. That duplicate path
  drifted: it only trusted the pid file, did not reuse daemon metadata for
  auth-token forwarding or owner fallback, and did not reject non-loopback TCP
  transport hints. Separately, `reset_local_state()` removed runtime artifacts
  without first terminating a live daemon, which could orphan a background
  process during repair.

- Solution: The store-side daemon client now follows the same transport and
  auth contract as the CLI-side client: live-owner validation, metadata-backed
  owner fallback, auth-token forwarding, and loopback-only TCP acceptance.
  Odylith also now stops a live Context Engine daemon before `--reset-local-state`
  cleanup, hardens Watchman shutdown with kill fallback and stream close, and
  covers the boundary with focused daemon-harden­ing regression tests plus a
  broader runtime/browser proof suite.

- Verification: `python -m py_compile` on the touched runtime/install/test
  files passed; `PYTHONPATH=src python -m pytest -q
  tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py
  tests/unit/install/test_repair.py` passed with `11 passed`; `PYTHONPATH=src
  python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py
  tests/unit/install/test_repair.py` passed with `371 passed`; live process
  audit after the fixes showed no active `odylith-context-engine` daemon
  residue on this machine.

- Prevention: Treat daemon transport, owner liveness, and repair cleanup as one
  shared security-sensitive contract. Do not maintain duplicate daemon clients
  with different trust rules. Local recovery flows must terminate live helpers
  before deleting their runtime files, and daemon transport tests must cover
  auth, loopback-only TCP, owner mismatch, and stubborn-process shutdown.

- Detected By: user report from Activity Monitor plus manual process-table and
  daemon-lifecycle audit on 2026-03-29.

- Failure Signature: many visible Python processes in macOS Activity Monitor,
  combined with code audit showing split daemon-client logic, unauthenticated
  store-side daemon requests, and repair cleanup that could delete runtime
  files while a daemon was still alive.

- Trigger Path: repeated local Odylith use, `--client-mode auto` daemon reuse,
  repair/reset-local-state while a daemon is still running, or any local actor
  capable of tampering with the daemon transport artifact under `.odylith/runtime/`.

- Ownership: Odylith Context Engine daemon lifecycle, local transport trust
  boundary, and install repair cleanup.

- Timeline: escalated on 2026-03-29 after Activity Monitor showed an
  unexpectedly large Python process set; live process audit showed no current
  Odylith daemon fleet, but repo scan confirmed remaining daemon lifecycle and
  transport hardening gaps the same morning; code, tests, and source-truth
  closeout landed later that day.

- Blast Radius: Odylith maintainers and consumers using the local Context
  Engine daemon in one repo on one machine; highest risk is local workstation
  residue, recovery confusion, and weakened trust of the daemon boundary.

- SLO/SLA Impact: no shared outage; local reliability and trust degradation.

- Data Risk: low. The issue is process lifecycle and local control-plane trust,
  not persisted product truth corruption.

- Security/Compliance: local security posture regression. Non-loopback TCP
  acceptance and missing auth-token forwarding made the local daemon boundary
  easier to subvert than intended, even though the threat model stays
  workstation-local.

- Invariant Violated: Odylith must not trust stale daemon artifacts, must not
  silently leave background daemons behind during repair, and must keep
  non-in-process daemon traffic authenticated and loopback-only.

- Workaround: use `odylith context-engine --repo-root . stop` before repair;
  use `odylith context-engine --repo-root . status` to inspect daemon state;
  if local residue is suspected, kill only the specific Odylith daemon and then
  rerun `odylith doctor --repo-root . --repair --reset-local-state`.

- Rollback/Forward Fix: Forward fix. Reverting the hardening would reopen the
  split trust model and the repair-orphaning gap.

- Agent Guardrails: Do not add a second daemon client or transport reader
  without keeping it bit-for-bit aligned with the primary trust contract. Do
  not accept TCP transport metadata for non-loopback hosts. Do not delete live
  runtime artifacts before terminating the owning daemon.

- Preflight Checks: inspect this bug, [CURRENT_SPEC.md](../../registry/source/components/odylith-context-engine/CURRENT_SPEC.md), [ODYLITH_CONTEXT_ENGINE.md](../../agents-guidelines/ODYLITH_CONTEXT_ENGINE.md), [test_odylith_context_engine_daemon_hardening.py](../../../tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py), and [test_repair.py](../../../tests/unit/install/test_repair.py) before changing daemon lifecycle or repair cleanup again.

- Regression Tests Added: `test_read_daemon_transport_rejects_non_loopback_tcp_host`,
  `test_store_runtime_daemon_transport_rejects_non_loopback_tcp_host`,
  `test_store_daemon_request_includes_auth_token_for_socket_transport`,
  `test_reset_local_state_stops_live_context_engine_daemon_before_cleanup`,
  plus the widened runtime/browser proof run.

- Monitoring Updates: `odylith context-engine --repo-root . status` remains the
  operator source for daemon liveness and stale artifacts; the daemon timing
  ledger now records authenticated store-side reuse as well.

- Related Incidents/Bugs: [2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md](2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md)

- Version/Build: workspace state on 2026-03-29 before daemon transport and
  repair hardening closeout.

- Config/Flags: `--client-mode auto`, local daemon transport reuse,
  `odylith doctor --repo-root . --repair --reset-local-state`.

- Customer Comms: maintainer-facing. Tell maintainers that a large Python
  process list is not automatically an Odylith leak, but Odylith should still
  fail closed on live-daemon residue and local transport trust issues.

- Code References: `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`,
  `src/odylith/install/repair.py`,
  `tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py`,
  `tests/unit/install/test_repair.py`

- Runbook References: `odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`

- Fix Commit/PR: `B-014` workstream closed on 2026-03-29 after daemon client
  parity, loopback-only transport validation, repair cleanup hardening, and
  regression proof landed together.
