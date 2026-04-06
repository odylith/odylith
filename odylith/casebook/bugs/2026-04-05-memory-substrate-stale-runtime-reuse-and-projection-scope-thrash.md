- Bug ID: CB-053

- Status: Closed

- Created: 2026-04-05

- Fixed: 2026-04-05

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Odylith's memory substrate could still treat stale derived state as reusable truth. Process-local warm-cache TTL could hide projection fingerprint drift, runtime warm reuse could accept a stale local LanceDB or Tantivy backend, and exact-scope checks across `reasoning` versus `full` could make `query`, `memory-snapshot`, remote sync, and benchmark warmup rebuild over each other even when a safe superset projection was already ready.

- Impact: The same repo truth could produce avoidable projection rebuilds, repeated Lance temp-dataset churn, slower query and snapshot paths, and a real risk that query-time retrieval would trust stale local memory after repo changes. That directly threatened grounding accuracy and benchmark robustness against `odylith_off`.

- Components Affected: `src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py`, `src/odylith/runtime/context_engine/odylith_context_engine_projection_compiler_runtime.py`, `src/odylith/runtime/context_engine/odylith_context_engine.py`, `src/odylith/runtime/memory/odylith_memory_backend.py`, `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, memory freshness contracts, benchmark warm-cache preparation, local LanceDB and Tantivy runtime posture.

- Environment(s): Odylith product repo maintainer mode, detached `source-local`, local macOS runtime, live `query`, `memory-snapshot`, and `odylith-remote-sync --dry-run` validation paths.

- Root Cause: Freshness policy was inconsistent across layers. Some paths used exact projection-scope equality, some trusted process-local cache TTL before rechecking current projection fingerprints, and some treated runtime-state metadata as if it were authoritative even when the compiled snapshot and backend were fresher. That let stale or narrower-scope state survive longer than it should and made compatible `full` projections look unusable to `reasoning` callers.

- Solution: Projection freshness and scope-compatibility rules were hardened and made more structural. Warm-cache reuse now rechecks the current projection fingerprint before honoring TTL, runtime snapshot reuse now requires a projection-current local backend when memory deps are available, compatible-scope reuse now treats `full` as a safe superset for `reasoning` and `default`, compiler warmup can repair stale runtime-state metadata from fresh compiled artifacts instead of rebuilding, hot-path warm checks can now reuse a fresh compatible snapshot/backend even when `runtime_state` lags, backend materialization now reuses a healthy compatible superset instead of insisting on exact-scope matches, sticky proof snapshots can prefer stronger compatible memory evidence, remote sync requires a fresh full-scope local backend, and benchmark warm-cache priming now prepares the full projection superset instead of only the narrower reasoning slice.

- Verification: Focused runtime and benchmark coverage passed after the hardening wave, including projection reuse, backend freshness, compatible-scope backend materialization, sticky proof compatibility, remote sync, daemon/watcher cleanup, and benchmark warm-cache prep. Live proof also confirmed that `query` returned local Tantivy-backed results, `memory-snapshot` reported a ready full-scope LanceDB and Tantivy backend with matching fingerprint, disabled Vespa sync returned fast without warmup drag, process counts stayed flat across live queries, and steady-state reuse no longer emitted repeat Lance rebuild warnings once the full substrate was current.

- Prevention: Derived runtime state is a cache, not a source of truth. Any future reuse fast path must prove current projection compatibility and backend freshness before returning success, and compatible-scope rules must stay centralized so `default`, `reasoning`, and `full` cannot drift apart again.

- Detected By: User escalation during live memory-substrate hardening, followed by direct launcher proof on 2026-04-05.

- Failure Signature: Repeated Lance temp-dataset creation warnings after alternating `query` and `memory-snapshot`, local retrieval staying available only after rebuild, and projection warmup doing extra work even when the full compiled substrate was already ready.

- Trigger Path: `./.odylith/bin/odylith query --repo-root . "odylith memory backend"`, `./.odylith/bin/odylith context-engine --repo-root . memory-snapshot`, `./.odylith/bin/odylith context-engine --repo-root . odylith-remote-sync --dry-run`, and benchmark warm-cache preparation in `odylith benchmark`.

- Ownership: Odylith memory substrate freshness, projection compiler reuse policy, and benchmark warm-cache posture.

- Timeline: The first hardening wave closed stale-manifest and remote-only failure modes, but live proof still exposed `reasoning` versus `full` rebuild thrash and stale reuse semantics. The second wave on 2026-04-05 normalized compatible-scope reuse, repaired stale runtime-state dependence, and extended coverage through live proof plus regression tests. A follow-on structural pass centralized scope-compatibility rules inside the memory backend so backend repair, sticky proof reuse, benchmark priming, and projection warmup all honor the same freshness contract.

- Blast Radius: Query correctness, memory-snapshot trust, remote-sync responsiveness, benchmark warm/cold stability, and developer confidence in Odylith's local memory layer.

- SLO/SLA Impact: No shared outage, but high local-productivity and benchmark-proof risk before the fix.

- Data Risk: Medium product-integrity risk. The bug class could serve stale derived memory after repo changes or wastefully rebuild until a fresh backend happened to win the race.

- Security/Compliance: None directly.

- Invariant Violated: Odylith must never treat stale local memory or stale derived runtime metadata as authoritative when fresher repo-truth-derived state is already required or available.

- Workaround: Before the fix, operators could force a fresh full projection or rerun `memory-snapshot` until the local backend settled, but that was not an acceptable steady state.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not trust warm-cache TTL without recomputing the current projection fingerprint. Do not let exact scope equality block a safe superset reuse path. Do not rebuild the local memory backend solely because a narrower caller requested `reasoning` while a fresh `full` substrate already exists.

- Preflight Checks: Inspect this bug, `tests/unit/runtime/test_context_grounding_hardening.py`, `tests/unit/runtime/test_odylith_memory_backend.py`, `tests/unit/runtime/test_odylith_memory_areas.py`, `tests/unit/runtime/test_odylith_remote_retrieval.py`, and `tests/unit/runtime/test_odylith_benchmark_runner.py` before widening projection or memory reuse logic again.

- Regression Tests Added: `test_warm_runtime_ttl_does_not_hide_projection_fingerprint_drift`, `test_projection_cache_signature_ignores_stale_process_warm_fingerprint`, `test_warm_runtime_rebuilds_when_backend_projection_is_stale`, `test_warm_runtime_reuses_full_snapshot_for_reasoning_queries`, `test_warm_runtime_reuses_reasoning_snapshot_for_default_scope`, `test_warm_runtime_reuses_compatible_snapshot_when_runtime_state_lags`, `test_projection_compiler_runtime_refuses_fast_reuse_when_local_backend_is_stale`, `test_projection_compiler_runtime_reuses_full_projection_when_reasoning_is_requested`, `test_local_backend_ready_for_projection_requires_matching_scope_and_fingerprint`, `test_projection_scope_satisfies_compatible_superset_rules`, `test_materialize_local_backend_reuses_compatible_full_backend_for_default_request`, `test_memory_backend_sticky_snapshot_accepts_full_scope_as_reasoning_superset`, `test_run_odylith_remote_sync_warms_full_projection_when_backend_is_stale`, `test_sync_remote_closes_http_client_after_partial_error`, and the updated benchmark warm-cache proof in `test_prime_benchmark_runtime_cache_warms_once`.

- Monitoring Updates: `memory-snapshot` live proof now serves as an operator check for projection fingerprint, projection scope, backend readiness, and remote-sync disabled posture. Live process-count proof for context-engine and watchman was also used to confirm no new memory-path process leak.

- Residual Risk: Vespa remains optional and inactive in this checkout until a live `ODYLITH_VESPA_URL` and active mode are configured, but disabled or misconfigured remote retrieval no longer drags or overrides the local memory lane.

- Related Incidents/Bugs: `2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md`, `2026-03-24-odylith-autospawn-daemon-ownership-and-lifetime-leak.md`

- Version/Build: `v0.1.7` detached `source-local` hardening wave on 2026-04-05.

- Config/Flags: `./.odylith/bin/odylith query`, `./.odylith/bin/odylith context-engine --repo-root . memory-snapshot`, `./.odylith/bin/odylith context-engine --repo-root . odylith-remote-sync --dry-run`, benchmark warm-cache preparation in `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`.

- Customer Comms: Maintainers and operators can trust that local memory reuse is now freshness-checked and that a ready full projection will satisfy narrower reasoning reads instead of forcing redundant rebuilds.

- Code References: `src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py`, `src/odylith/runtime/context_engine/odylith_context_engine_projection_compiler_runtime.py`, `src/odylith/runtime/context_engine/odylith_context_engine.py`, `src/odylith/runtime/memory/odylith_memory_backend.py`, `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`

- Runbook References: `docs/benchmarks/README.md`

- Fix Commit/PR: Pending local branch.
