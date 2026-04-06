- Bug ID: CB-028

- Status: Closed

- Created: 2026-04-01

- Severity: P0

- Reproducibility: Always

- Type: Product

- Description: The benchmark acceptance gate could return a provisional pass
  even when both live compared lanes failed, timed out, or never reached a
  validator-backed successful outcome.

- Impact: A broken or untrusted live benchmark run could still look green in
  the headline status, which directly undermines the benchmark's role as an
  anti-gaming product proof.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark hard-quality gate, live benchmark status publication.

- Environment(s): Odylith product repo live benchmark runs after the move from
  packet-only baseline proxies to matched live Codex CLI execution.

- Root Cause: The publication gate compared lane deltas and guardrails but did
  not require the candidate lane to achieve a positive live success signal of
  its own. Equal failure could therefore sneak through as non-regression.

- Solution: Add fail-closed positive-success gates to the benchmark status
  contract. `odylith_on` now has to achieve a real expectation success,
  validation success, critical required-path recall, and critical validation
  success before the benchmark can pass.

- Verification: The earlier medium run that had previously surfaced as a false
  `provisional_pass` now reports `hold`, and focused regressions covering the
  new gate contract pass in `tests/unit/runtime/test_odylith_benchmark_runner.py`.

- Prevention: Relative deltas are not enough. Any benchmark gate that can pass
  without one lane proving an actual positive outcome is structurally unsafe.

- Detected By: 2026-04-01 honest raw-baseline redesign after a matched live run
  timed out on both lanes yet still looked green.

- Failure Signature: A report shows both lanes failed, timed out, or blocked,
  but benchmark status still lands on `provisional_pass`.

- Trigger Path: `odylith benchmark --repo-root .` using the live Codex CLI
  benchmark modes before the gate hardening patch landed.

- Ownership: Benchmark hard-quality gate and publication integrity.

- Timeline: The bug surfaced immediately after the live raw-baseline runner was
  introduced. The fail-closed gate patch and regression coverage landed the
  same day.

- Blast Radius: README or release-proof benchmark status, maintainer trust in
  benchmark gates, and product decisions made from benchmark snapshots.

- SLO/SLA Impact: Benchmark status loses credibility and can silently permit a
  regression or harness failure to ship.

- Data Risk: None.

- Security/Compliance: Integrity failure only.

- Invariant Violated: A benchmark comparison must never pass without the
  candidate lane proving a real positive live outcome.

- Workaround: Manual report inspection was possible but not an acceptable
  release-safe control.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not accept non-negative deltas as success when the
  candidate lane did not actually finish the task.

- Preflight Checks: Inspect this bug, the benchmark component spec,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, and
  `tests/unit/runtime/test_odylith_benchmark_runner.py` before changing the
  benchmark gate again.

- Regression Tests Added: `test_benchmark_status_requires_positive_candidate_success`

- Monitoring Updates: None beyond the hardened benchmark status contract.

- Residual Risk: The gate now fails closed, but live sandbox contamination and
  timeout-policy quality still need separate benchmark hardening.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`

- Version/Build: `v0.1.7` benchmark integrity hardening wave completed on
  2026-04-01.

- Config/Flags: `odylith benchmark --repo-root .`

- Customer Comms: None beyond treating the earlier false green as invalid.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
