- Bug ID: CB-117

- Status: Open

- Created: 2026-04-15

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Benchmark proof shards treat shell hangup as terminal interrupt

- Impact: Maintainer proof shards can fail after a pause/resume or PTY close even though benchmark work was healthy, forcing reruns and blocking release proof.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer source-local proof lane on branch 2026/freedom/v0.1.11 with four proof shards launched from Codex Desktop PTY sessions.

- Detected By: Deep resume inspection of shard reports 4955da0f4ab6d7eb, e240ca9060667721, and 5bd0bb4fdbbb68d5 after the paused benchmark proof run.

- Failure Signature: Three current-head proof shard reports persisted as failed with hard gate failure BenchmarkRunInterrupted: received SIGHUP, even though the active-run ledger had previously shown healthy shard progress.

- Trigger Path: Launch proof shards through the benchmark runner, pause or end the host PTY session, then inspect .odylith/runtime/odylith-benchmarks/<report-id>.json.

- Ownership: benchmark runner signal lifecycle and long-running proof execution contract

- Timeline: Captured 2026-04-15 through `odylith bug capture`.

- Blast Radius: Sharded proof, release benchmark publication, maintainer proof recovery, and current-head benchmark closeout.

- SLO/SLA Impact: Release proof latency and reliability degrade because healthy shards can be invalidated by host-shell lifecycle instead of benchmark quality.

- Data Risk: Low product-data risk, high benchmark-truth and release-proof reliability risk.

- Security/Compliance: None directly.

- Invariant Violated: A benchmark proof shard must fail closed on explicit termination, but host shell hangup during pause/resume must not be treated as a benchmark-quality failure.

- Root Cause: The benchmark interrupt guard installed the same raising handler for SIGHUP as for SIGTERM and SIGINT.

- Solution: Ignore SIGHUP in the benchmark runner while preserving SIGTERM and SIGINT as explicit fail-closed stop signals; keep child live processes in their own process groups.

- Verification: Add unit coverage that the benchmark interrupt guard ignores SIGHUP, still raises on SIGTERM, and restores prior handlers, then rerun the benchmark runner and live execution suites.

- Prevention: Long-running benchmark proof must be resilient to host shell hangup; use explicit SIGTERM or SIGINT for operator stop semantics.

- Agent Guardrails: Do not launch or judge long-running proof from an interactive PTY unless the runner is SIGHUP-safe or detached.

- Regression Tests Added: Benchmark runner interrupt-guard tests for SIGHUP ignore and SIGTERM fail-closed semantics.

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_runner.py
