- Bug ID: CB-037

- Status: Closed

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The diagnostic benchmark lane was supposed to stay packet and
  prompt only, but a post-run singleton latency probe reran `odylith_on`
  versus `odylith_off` through a live-Codex-capable mode path. That reopened
  the live lane inside a diagnostic run and could leave behind benchmark temp
  worktrees or Codex subprocesses.

- Impact: Diagnostic reports could silently stop being trustworthy. They could
  pick up live execution cost, contaminate the process table, leak temp
  worktrees, and misstate what the diagnostic benchmark was actually
  measuring.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  diagnostic latency probes, benchmark runtime hygiene contract, benchmark
  publication semantics.

- Environment(s): Odylith product repo maintainer mode, `odylith benchmark
  --repo-root . --profile diagnostic`, source-local benchmark debugging.

- Root Cause: The singleton latency probe helper did not propagate
  `benchmark_profile`, so it defaulted back to the proof-mode live path.
  Separately, `_run_scenario_mode` treated public modes as live-capable even
  when the active profile was diagnostic, so the runner could trip the
  fail-closed live guard after the main diagnostic loop had already completed.

- Solution: Propagate `benchmark_profile` through singleton latency probes,
  keep diagnostic `odylith_on` and `odylith_off` on the local packet or
  architecture path, add an explicit diagnostic runtime hygiene check, and fail
  closed if any benchmark-owned Codex subprocess or benchmark temp worktree is
  present after the run.

- Verification: Unit coverage now proves singleton latency probes preserve the
  diagnostic profile and that diagnostic runtime hygiene fails closed on
  contamination. A full CLI diagnostic run completed with `0`
  benchmark-owned Codex subprocesses and `0` benchmark temp worktrees at
  close.

- Prevention: Diagnostic and proof are separate benchmark products and must not
  share hidden execution fallbacks. Any code path that can invoke live Codex
  must carry the active benchmark profile explicitly.

- Detected By: Manual process-table and worktree inspection during the
  diagnostic benchmark cleanup and fairness review.

- Failure Signature: A diagnostic run reached `completed_results == total` and
  then spawned a live `codex exec` subprocess during post-run metrics or left
  behind an `odylith-benchmark-live-*` worktree.

- Trigger Path: `odylith benchmark --repo-root . --profile diagnostic`

- Ownership: Benchmark runner integrity, diagnostic benchmark hygiene, and
  benchmark publication trust.

- Timeline: The benchmark contract split exposed that the diagnostic lane was
  still clean during the main corpus loop but could reenter live execution
  during singleton latency probes. The runner was then hardened so diagnostic
  remains packet and prompt only from start to finish.

- Blast Radius: Diagnostic reports, packet/prompt latency claims, local temp
  state hygiene, and maintainer trust in internal benchmark tuning.

- SLO/SLA Impact: Diagnostic runs risked being too slow, too noisy, and too
  misleading for inner-loop tuning.

- Data Risk: Low direct data risk, high benchmark-integrity risk.

- Security/Compliance: No direct security exploit, but the bug violated the
  strict contamination boundary expected of the diagnostic lane.

- Invariant Violated: Diagnostic runs must never spawn live Codex work,
  must never leak benchmark temp worktrees, and must fail closed on any
  contamination.

- Workaround: Manual process cleanup and worktree pruning after each run, which
  is not acceptable as the benchmark contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: When editing benchmark execution flow, do not assume that
  public mode names imply live execution. The benchmark profile decides whether
  the live path is even legal.

- Preflight Checks: Inspect benchmark profile routing, singleton latency probe
  helpers, and benchmark hygiene tests before changing diagnostic execution
  semantics.

- Regression Tests Added:
  `test_singleton_family_latency_probes_preserve_diagnostic_profile`,
  `test_enforce_diagnostic_runtime_hygiene_fails_closed_on_contamination`,
  `test_run_scenario_mode_uses_local_packet_path_on_diagnostic_profile`

- Monitoring Updates: Diagnostic reports now expose `startup_hygiene` and
  `final_hygiene`; clean runs show zero benchmark-owned Codex subprocesses and
  zero temp worktrees.

- Residual Risk: Diagnostic runs still depend on local memory and prompt-build
  components, so packet/prompt latency remains sensitive to those local code
  paths, but not to live Codex execution.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-default-cli-collapsed-developer-signal-and-publication-proof.md`,
  `2026-04-02-benchmark-live-public-pair-ran-serially-despite-isolated-workspaces.md`

- Version/Build: `v0.1.7` benchmark hygiene hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile diagnostic`

- Customer Comms: Maintainer docs and README should say that diagnostic is a
  packet/prompt benchmark, not a live-product benchmark, and that any
  diagnostic contamination is a hard failure.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `docs/benchmarks/README.md`,
  `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
