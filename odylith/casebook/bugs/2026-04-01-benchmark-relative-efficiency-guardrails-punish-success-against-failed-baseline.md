- Bug ID: CB-032

- Status: Closed

- Created: 2026-04-01

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The benchmark acceptance contract compared Odylith's relative
  latency and token cost against `odylith_off` even when the raw Codex lane
  produced no successful outcomes on the sampled corpus, so a slower but
  correct Odylith win could stay on `hold` purely because the baseline failed
  faster and cheaper.

- Impact: Benchmark status could mis-rank the product. Odylith could clear the
  hard quality gate on recall, precision, validation, and expectation success,
  yet still fail release status because the failed baseline consumed less time
  or fewer tokens before giving up.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  benchmark acceptance semantics, benchmark component status contract, release
  benchmark publication guidance, reviewer framing.

- Environment(s): Odylith product repo maintainer mode, Codex benchmark
  publication, targeted live same-task `odylith_on` versus `odylith_off`
  reruns, and any report where one compared lane has zero successful outcomes.

- Root Cause: The runner treated the lower-tier relative guardrails as always
  applicable whenever both mode summaries existed. That collapsed two different
  states: "both lanes produced valid outcomes and can be compared on cost" and
  "one lane only failed faster."

- Solution: Make comparative latency and token-efficiency guardrails conditional
  on both lanes producing at least one successful outcome on the sampled
  corpus. Keep faster failure visible in the report as a published diagnostic,
  but do not let it block status. Keep the candidate-only tighter-budget
  health check active.

- Verification: Focused unit coverage now proves both branches: comparable
  successful lanes still trigger the relative guardrails, while reports with no
  successful `odylith_off` outcomes no longer fail status solely on relative
  latency or token deltas.

- Prevention: Treat lower-tier relative cost metrics as meaningful only after
  the compared lanes are both capable of producing successful outcomes on the
  sampled workload. Faster failure is not benchmark superiority.

- Detected By: Honest strict reruns on 2026-04-01 where `odylith_on` cleared
  the hard quality gate on a live benchmark case but remained on `hold`
  because the failed raw baseline exited cheaper.

- Failure Signature: Reports show `hard_quality_gate_cleared = true`,
  `validation_success_delta >= 0`, `expectation_success_delta >= 0`, baseline
  success rates at `0.0`, and yet `status = hold` because latency or token
  deltas breached the lower-tier thresholds.

- Trigger Path: `odylith benchmark --repo-root . --mode odylith_on --mode odylith_off`
  through the benchmark acceptance and publication path.

- Ownership: Benchmark acceptance semantics and release publication contract.

- Timeline: The honest live-baseline redesign fixed the fake-baseline and
  false-pass problems, then exposed a third scoring issue: the benchmark still
  treated failed-baseline cheapness as a status blocker. The acceptance
  contract, public docs, and maintainer guidance were updated together.

- Blast Radius: README benchmark claims, maintainer release proof decisions,
  benchmark dashboard interpretation, and any internal decision that consumes
  benchmark status instead of the raw deltas.

- SLO/SLA Impact: Benchmark release readiness can remain blocked for the wrong
  reason, causing maintainers to optimize lower-tier cost deltas before the
  more important question of whether both lanes can actually complete the work.

- Data Risk: Low direct data risk, high benchmark-interpretation risk.

- Security/Compliance: None directly; this is benchmark correctness and product
  honesty.

- Invariant Violated: Lower-tier relative latency and token guardrails are only
  status blockers after both compared lanes produce successful outcomes.

- Workaround: Manual interpretation of the report. Not acceptable as the
  primary release contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not describe a failed raw baseline as "cheaper" in a
  way that implies benchmark superiority. Keep the hard quality gate first and
  call out when the relative efficiency guardrails were intentionally skipped.

- Preflight Checks: Inspect this bug, the benchmark component spec, the active
  B-022 plan, and the benchmark runner acceptance tests before changing lower-tier
  status semantics.

- Regression Tests Added: `test_acceptance_skips_relative_efficiency_guardrails_when_baseline_has_no_successful_outcomes`

- Monitoring Updates: Acceptance payloads now expose
  `comparative_efficiency_guardrails_applicable` plus
  `comparative_efficiency_guardrail_reason`.

- Residual Risk: Reports can still surface honest efficiency debt when both
  lanes succeed. That is intended and remains a valid blocker.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-gate-can-pass-when-both-live-lanes-fail.md`

- Version/Build: `v0.1.7` benchmark integrity and status-hardening wave on
  2026-04-01.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_REASONING_MODEL`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT`.

- Customer Comms: Public and maintainer docs should say explicitly that faster
  failure stays published as a diagnostic, not as a benchmark blocker.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_guardrails.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
