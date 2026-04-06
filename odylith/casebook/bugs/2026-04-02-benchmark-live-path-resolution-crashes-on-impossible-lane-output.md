- Bug ID: CB-035

- Status: Closed

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark runner trusted lane-emitted workspace path
  tokens too much. When a Codex lane surfaced an impossible file name in a
  `changed_files` payload or file-change event, the harness attempted to
  `stat()` that path inside the disposable workspace and crashed the entire
  proof run with `OSError: [Errno 63] File name too long`.

- Impact: A single malformed lane output could fail the full benchmark corpus
  even though the honest outcome should have been a degraded lane result with
  missing-path attribution. That undermined proof-run stability and made the
  benchmark harness look less trustworthy than the product it was trying to
  measure.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  live observed-path attribution, candidate-write detection, benchmark proof
  stability.

- Environment(s): Odylith product repo maintainer mode, live Codex CLI proof
  runs, disposable benchmark workspaces on macOS.

- Root Cause: `_resolve_workspace_file`, `_relative_workspace_path`, and
  `_existing_file_paths` assumed lane-reported path tokens were safe to
  resolve and inspect. They did not suppress filesystem errors such as
  `ENAMETOOLONG` when the lane emitted nonsense or adversarial path strings.

- Solution: Fail closed on impossible workspace paths. Path resolution and
  file checks now suppress filesystem resolution errors and simply drop invalid
  tokens from observed-path and write-surface attribution instead of failing
  the report.

- Verification: Added regression coverage proving the runner ignores
  impossible long path components in both direct path resolution and
  mixed valid-plus-invalid observed-path events.

- Prevention: Treat lane-emitted path data as untrusted input. Benchmark
  attribution logic must only elevate paths that can be safely resolved inside
  the disposable workspace.

- Detected By: Full `gpt-5.4 / medium` proof rerun on 2026-04-02 after the
  stricter live Codex harness refresh.

- Failure Signature: `OSError: [Errno 63] File name too long` under
  `.odylith/runtime/odylith-benchmarks/in-progress.v1.json`, with the current
  scenario stuck on a live lane.

- Trigger Path: `odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark live execution harness and path-attribution safety.

- Timeline: The first full proof rerun under the refreshed live harness
  crashed on `broad-shared-guarding` after a live lane emitted an impossible
  path token. The resolver was hardened to fail closed, and the proof rerun
  was restarted.

- Blast Radius: Entire proof-corpus stability, benchmark publication
  confidence, and maintainer trust in long-running honest benchmark reruns.

- SLO/SLA Impact: Full proof reruns could abort after several minutes of live
  execution, wasting benchmark time and invalidating publication attempts.

- Data Risk: Low direct data risk, high proof-stability risk.

- Security/Compliance: None directly, but the fix aligns with a strict
  sandboxing posture by treating lane output as untrusted.

- Invariant Violated: Invalid lane output must degrade that lane's measured
  quality, not crash the benchmark harness.

- Workaround: Rerun the proof after restarting the benchmark process; no safe
  operator workaround existed before the fix.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Never treat lane-reported workspace paths as authoritative
  until the harness confirms they resolve safely inside the disposable
  workspace.

- Preflight Checks: Exercise live benchmark path attribution with malformed
  path tokens before widening the proof corpus or changing live structured
  output contracts.

- Regression Tests Added:
  `test_resolve_workspace_file_ignores_enametoolong_path_component`,
  `test_observed_paths_from_events_ignores_invalid_changed_file_tokens`

- Monitoring Updates: Benchmark reruns now surface lane-quality misses instead
  of infrastructure crashes when path tokens are impossible to resolve.

- Residual Risk: Extremely large but syntactically valid path sets can still
  bloat attribution work, but they no longer crash the benchmark harness.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-observed-path-attribution-counts-transitive-links-from-doc-content.md`

- Version/Build: `v0.1.7` live benchmark harness hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`

- Customer Comms: Benchmark docs should describe the harness as fail-closed on
  invalid lane-emitted paths rather than implying every emitted token is
  authoritative.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
