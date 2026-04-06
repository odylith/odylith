- Bug ID: CB-002

- Status: Closed

- Created: 2026-03-24

- Fixed: 2026-03-24

- Severity: P0

- Reproducibility: Always

- Type: Tooling

- Description: Odylith Context Engine rich-context commands in `--client-mode auto` could detach background `serve` daemons with no ownership or idle-lifetime bound. Large test runs and normal local usage could therefore leave hundreds of orphaned Python processes alive after the triggering command exited.

- Impact: Developer machines could accumulate large numbers of idle Python interpreters, consume tens of gigabytes of RSS, and make Activity Monitor/process inspection untrustworthy. The local maintainer loop degraded badly even though the original foreground commands had already finished.

- Components Affected: `src/odylith/runtime/context_engine/odylith_context_engine.py`, Odylith daemon autospawn lifecycle, `tests/unit/runtime/test_odylith_context_engine.py`, Odylith context-engine guidance/specs.

- Environment(s): local dev on macOS, repo-scoped Odylith usage, pytest temp repos under `/private/var/folders/.../pytest-of-...`.

- Root Cause: The runtime treated detached autospawn as a valid steady state. `_spawn_daemon_background()` launched `serve` via `subprocess.Popen(..., start_new_session=True)` and then relied only on pid/socket presence for health. There was no owner heartbeat, no idle expiry, no test/CI fail-closed suppression, and no explicit metadata telling status whether a daemon was operator-started or opportunistically detached from a one-shot command. Tests that exercised many temporary repo roots therefore created real background daemons by design and left them alive after the parent pytest command exited.

- Solution: Detached background autospawn now fails closed by default. `--client-mode auto` may still reuse an already-running healthy daemon, but it no longer detaches a new background `serve` process unless the operator explicitly opts into bounded autospawn. The runtime now blocks detached autospawn in pytest/CI/non-git contexts, records daemon `spawn_reason` plus `idle_timeout_seconds` metadata, self-terminates opt-in autospawned daemons when idle, and clears stale metadata artifacts alongside pid/socket/stop residue. Focused docs, runbooks, AGENTS guidance, and Odylith skills were updated to treat silent daemon residue as a bug again.

- Verification: Focused compile and unit coverage for `src/odylith/runtime/context_engine/odylith_context_engine.py`, governed-surface validation, and live process-tree audit before and after cleanup confirmed leaked Odylith daemons were terminated and no detached Context Engine helper remained alive afterward.

- Prevention: One-shot local tooling commands and tests must never leave silent background processes behind. Background daemon creation is now opt-in instead of ambient, any allowed autospawn must carry explicit owner/lifetime metadata plus idle expiry, and repo guidance/tests now fail closed against future silent helper-process residue.

- Detected By: User report from Activity Monitor plus live process-tree audit on 2026-03-24.

- Failure Signature: Hundreds of `odylith context-engine ... serve --scope reasoning --watcher-backend auto` processes with repo roots under pytest temp directories, all reparented to PID `1`; one real repo daemon also remained alive after its triggering command had exited.

- Trigger Path: Successful local `query`, `context`, `impact`, `architecture`, `session-brief`, or `bootstrap-session` commands in `--client-mode auto`, especially during pytest-heavy Odylith test runs that create many temporary repo roots.

- Ownership: Odylith Context Engine daemon/autospawn lifecycle.

- Timeline: First escalated on 2026-03-24 when Activity Monitor showed over a thousand Python processes; live audit confirmed orphaned Odylith daemons the same evening; leaked processes were terminated immediately; the daemon-lifecycle hardening landed and was validated later the same day.

- Blast Radius: Odylith maintainers and local repo operators using the Context Engine locally; worst case is broad pytest or repeated local rich-context usage across many temp repos.

- SLO/SLA Impact: No shared-environment outage; severe local developer productivity and workstation-stability impact.

- Data Risk: None.

- Security/Compliance: None directly, but silent detached local daemons weaken operator trust and make local process ownership harder to audit.

- Invariant Violated: Opportunistic local acceleration must be disposable. Successful one-shot commands and test runs must not leave detached background processes alive indefinitely.

- Workaround: Kill leaked temp-repo daemons with `pkill -f 'odylith_context_engine.*pytest-of-'`; stop any real repo daemon explicitly with `odylith context-engine --repo-root . stop`.

- Rollback/Forward Fix: Forward fix. Reverting to indefinite detached autospawn would reintroduce silent process accumulation and make the same leak class likely to recur.

- Agent Guardrails: Do not detach a background daemon from a one-shot code path without explicit lifetime semantics. Do not treat a live pid alone as sufficient truth for acceptable daemon ownership. Do not allow tests or CI-style runs to create background helper processes unless the test owns and asserts their cleanup.

- Preflight Checks: Inspect this bug, [CURRENT_SPEC.md](../../registry/source/components/odylith-context-engine/CURRENT_SPEC.md), [ODYLITH_CONTEXT_ENGINE.md](../../agents-guidelines/ODYLITH_CONTEXT_ENGINE.md), and [test_odylith_context_engine.py](../../../tests/unit/runtime/test_odylith_context_engine.py) before touching Odylith daemon lifecycle again.

- Regression Tests Added: `test_odylith_context_engine_status_prunes_runtime_records_and_reports_stale_daemon_artifacts`, `test_odylith_context_engine_status_reports_live_daemon_metadata`, `test_spawn_daemon_background_starts_when_missing_and_cleans_stale_artifacts`, `test_maybe_autospawn_daemon_uses_reasoning_scope`, `test_maybe_autospawn_daemon_is_disabled_by_default`, `test_maybe_autospawn_daemon_blocks_in_pytest_even_when_opted_in`, `test_autospawn_daemon_idle_expired_after_timeout`, `test_run_serve_autospawn_stops_when_idle_timeout_expires`.

- Monitoring Updates: `odylith context-engine --repo-root . status` now exposes daemon origin/lifetime state via `daemon_spawn_reason`, `daemon_idle_timeout_seconds`, `daemon_started_utc`, and stale metadata artifact reporting so operators can distinguish intentional explicit `serve` from bounded opt-in autospawn or residue.

- Related Incidents/Bugs: None recorded in the public Odylith product repo beyond this case.

- Version/Build: Workspace state on 2026-03-24 before daemon-lifecycle hardening.

- Config/Flags: `--client-mode auto`, detached autospawn path in `scripts.odylith_context_engine`.

- Customer Comms: Internal maintainer-facing only. Tell maintainers that background Odylith daemons should now be treated as a bug unless intentionally started through the explicit operator daemon path.

- Code References: `src/odylith/runtime/context_engine/odylith_context_engine.py`, `tests/unit/runtime/test_odylith_context_engine.py`, `odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md`, `odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`, `odylith/skills/odylith-context-engine-operations/SKILL.md`

- Runbook References: `odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`

- Fix Commit/PR: `B-289` workstream closed on 2026-03-24 after daemon lifecycle hardening, regression coverage, guidance updates, and governed-surface sync landed together.
