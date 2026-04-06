- Bug ID: CB-034

- Status: Closed

- Created: 2026-04-02

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The benchmark runner prepared and executed the public live
  `odylith_on` and `odylith_off` lanes fully serially even after the harness
  had moved both lanes into isolated disposable worktrees and temporary Codex
  homes. That preserved correctness, but it wasted wall-clock without adding
  benchmark quality.

- Impact: Full proof runs took materially longer than necessary, which reduced
  maintainers' ability to run honest live benchmarks frequently and increased
  pressure toward ad hoc narrowed runs.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark live execution scheduling, benchmark runtime efficiency contract.

- Environment(s): Odylith product repo maintainer mode, honest live Codex CLI
  benchmark runs, `odylith_on` versus `odylith_off` matched-pair execution.

- Root Cause: The original runner loop serialized everything by mode and
  scenario. Once the raw lane moved into a strict isolated worktree and temp
  Codex home, the runner still treated the live pair as if it had to share the
  same mutable process state.

- Solution: Keep Odylith packet construction serial, then execute the isolated
  same-scenario public live pair in a bounded thread pool. This parallelizes
  only the expensive live Codex subprocess phase, keeps the live pair under the
  same ambient machine moment, and preserves strict sandbox isolation.

- Verification: Unit coverage now proves the live public pair is executed once
  as a matched batch and that both results carry matched-pair metadata.

- Prevention: Only parallelize phases that are already fully isolated. Keep
  packet shaping, cache-profile preparation, and other global-state-sensitive
  work serial unless they are explicitly decontaminated first.

- Detected By: Benchmark runtime investigation after the benchmark contract was
  split into explicit quick versus proof profiles.

- Failure Signature: Public live lanes dominate wall-clock and still run in
  mode order even though they already use disposable worktrees and temporary
  Codex homes.

- Trigger Path: `odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark runner scheduling and harness runtime quality.

- Timeline: The honest live benchmark redesign isolated the public lanes
  correctly, then exposed that the remaining runtime cost came from a fully
  serial scheduler. The runner was updated to batch only the isolated public
  live pair.

- Blast Radius: Full proof runtime, developer feedback cadence, and benchmark
  operator trust.

- SLO/SLA Impact: Honest live proof took longer than needed, making it harder
  to run often enough during iteration.

- Data Risk: Low direct data risk, moderate process-efficiency risk.

- Security/Compliance: None directly; the fix preserves the strict sandbox and
  temp-home isolation model.

- Invariant Violated: Benchmark runtime optimization must never compromise
  isolation or fairness, but it also should not serialize already-isolated
  phases without need.

- Workaround: None acceptable beyond manual patience.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not parallelize Odylith packet-building or any phase
  that still relies on global process state. The only approved benchmark
  batching here is the isolated live public pair after request preparation.

- Preflight Checks: Inspect benchmark runner tests and the live isolation
  contract before changing benchmark concurrency.

- Regression Tests Added:
  `test_run_live_scenario_batch_executes_public_pair_once_with_matched_pair_metadata`

- Monitoring Updates: Live results now expose `matched_pair_batch`,
  `matched_pair_batch_size`, and `matched_pair_modes` in `live_execution`
  metadata.

- Residual Risk: Running the live public pair concurrently can increase
  absolute latency due to same-machine contention, but the contention is shared
  across the compared lanes and is preferable to serial idle time for this
  comparative benchmark.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-default-cli-collapsed-developer-signal-and-publication-proof.md`

- Version/Build: `v0.1.7` benchmark scheduler hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`

- Customer Comms: Maintainer docs should state that only the isolated live
  public pair is batched, and that the stricter packet-building phases remain
  serial for integrity.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
