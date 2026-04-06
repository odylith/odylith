- Bug ID: CB-036

- Status: Closed

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark proof reported matched-pair conservative
  wall-clock and full-session Codex token spend using packet-era labels such as
  `Median latency` and `Median agent prompt tokens`, then reused packet-era
  `+15 ms`, `+64`, and `+96` guardrails as if the live proof were measuring
  solo-user latency and initial prompt size.

- Impact: Maintainers and reviewers could read the public benchmark snapshot as
  if Odylith or raw Codex CLI normally took multiple minutes for a single user
  interaction when the harness was actually publishing conservative
  same-scenario warm/cold matched-pair task-cycle diagnostics. The live proof
  also risked holding status for the wrong reason by applying thresholds that
  belonged to the diagnostic packet or prompt lane.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`, benchmark
  publication contract, README benchmark framing, benchmark reviewer guidance.

- Environment(s): Odylith product repo maintainer mode, `quick` and `proof`
  live Codex CLI benchmark lanes, release benchmark publication.

- Root Cause: The benchmark contract moved from packet-centric proof to a real
  live Codex matched pair, but the measurement vocabulary and lower-tier
  guardrails were not re-based. The runner still treated live proof like a
  prompt-bundle benchmark even though it now measured paired wall-clock plus
  validator time and full-session token accumulation.

- Solution: Keep the hard quality gate unchanged, but split live proof and
  diagnostic efficiency semantics. Live proof now labels paired task-cycle
  time, live agent runtime, validator overhead, and full-session token spend
  honestly, while prompt-bundle efficiency remains a diagnostic-lane concern.
  The runner also records an explicit initial prompt estimate for future
  diagnostic use.

- Verification: Focused benchmark runner, live-execution, graph, and hygiene
  tests pass after the measurement labels, acceptance semantics, and SVG
  headings are updated.

- Prevention: Any benchmark contract shift from packet diagnostics to live
  execution must re-audit the measurement basis, labels, and guardrails in the
  runner, docs, graphs, and README in the same change.

- Detected By: Maintainer review after a full `gpt-5.4` `medium` proof run
  reported multi-minute benchmark timing that did not match normal solo usage.

- Failure Signature: Published latency looks dramatically higher than expected,
  prompt-token deltas look implausibly large, and the public table implies
  those numbers are directly comparable to solo-user latency and first-prompt
  size.

- Trigger Path: `odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark measurement semantics, acceptance contract, and public
  benchmark framing.

- Timeline: The raw-Codex honest-baseline redesign made the benchmark live and
  same-agent honest, then exposed that the old packet-era latency and token
  vocabulary no longer matched the measurement basis.

- Blast Radius: Benchmark credibility, README trust, maintainer release proof,
  and the fairness story for `odylith_on` versus `odylith_off`.

- SLO/SLA Impact: Benchmark proof looked materially less believable than it
  was, reducing confidence in the product's benchmark claim.

- Data Risk: Low direct data risk, high interpretability risk.

- Security/Compliance: None directly.

- Invariant Violated: Benchmark labels and status blockers must match the
  actual measurement basis. A live matched-pair proof must not silently inherit
  packet-era efficiency thresholds or wording.

- Workaround: Manual explanation of the report structure. Not acceptable as a
  long-term publication contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not hide live-proof efficiency costs. Keep them visible,
  but separate paired task-cycle and full-session metrics from diagnostic
  prompt-bundle metrics.

- Preflight Checks: Inspect live-execution measurement fields, published mode
  table labels, acceptance notes, and graph headings together before changing
  benchmark wording.

- Regression Tests Added:
  `test_live_acceptance_keeps_latency_and_token_deltas_diagnostic_for_live_proof`
  and live-execution coverage for initial prompt estimates.

- Monitoring Updates: Live reports now expose an initial prompt estimate and
  explicit matched-pair latency basis metadata alongside the published
  task-cycle and session-token metrics.

- Residual Risk: Full live proof still takes hours on the full corpus because
  it is genuinely measuring many real Codex tasks; that runtime should be
  optimized separately from publication wording.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-live-public-pair-ran-serially-despite-isolated-workspaces.md`
  and
  `2026-04-01-benchmark-relative-efficiency-guardrails-punish-success-against-failed-baseline.md`

- Version/Build: `v0.1.7` benchmark measurement-contract hardening wave on
  2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`

- Customer Comms: README, maintainer guidance, and reviewer docs should state
  that live proof publishes conservative matched-pair task-cycle and
  full-session metrics, not solo-user latency or initial prompt size.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
