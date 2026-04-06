- Bug ID: CB-033

- Status: Closed

- Created: 2026-04-02

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The default `odylith benchmark --repo-root .` command expanded
  into the full warm-plus-cold, multi-mode publication matrix. That made the
  normal local benchmark path take hours, pushed maintainers toward ad hoc
  narrowing, and blurred the line between developer signal and release-safe
  benchmark proof.

- Impact: Maintainers could not get fast honest benchmark feedback in the
  normal coding loop, and the command surface made it too easy to confuse a
  local debug run with the canonical publication lane.

- Components Affected: `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, benchmark CLI
  contract, benchmark component spec, release benchmark runbooks.

- Environment(s): Odylith product repo maintainer mode, local Codex benchmark
  execution, release benchmark publication workflow.

- Root Cause: The benchmark command surface had only one effective posture.
  The runner knew how to publish a strict full report, but the public CLI
  treated that same path as the default local operator experience.

- Solution: Split the benchmark surface into explicit `quick` and `proof`
  profiles. Keep `proof` as the strict publication lane, make `quick` the
  default local matched-pair developer lane, and add deterministic family or
  shard selection so strict proof work can be split operationally without
  changing the benchmark contract.

- Verification: Unit coverage now proves quick-profile default narrowing to the
  matched-pair family-smoke lane and deterministic family-filtered shard
  selection for proof runs.

- Prevention: Keep developer-signal ergonomics and release-proof publication as
  separate benchmark contracts. Never make the default local command mean
  “run the entire publication matrix.”

- Detected By: Maintainer investigation after a no-time-cap full
  `gpt-5.4 / medium` run projected multi-hour wall-clock for the default local
  command.

- Failure Signature: `odylith benchmark --repo-root .` projects or incurs
  multi-hour runtime because it expands to the full corpus, multiple modes, and
  both warm and cold cache profiles.

- Trigger Path: `odylith benchmark --repo-root .`

- Ownership: Benchmark component CLI and publication contract.

- Timeline: The honest live same-contract redesign fixed benchmark fairness,
  then exposed a second design flaw: the default local benchmark surface was
  still shaped like the full release publication matrix. The CLI, runner,
  component spec, and maintainer docs were split into explicit quick versus
  proof lanes.

- Blast Radius: Maintainer productivity, benchmark publication hygiene, README
  refresh flow, and any local benchmark workflow that assumed the default CLI
  should be both fast and release-safe.

- SLO/SLA Impact: Benchmark inner-loop feedback was too slow to be useful, and
  maintainers were incentivized to invent custom narrow runs outside the
  documented contract.

- Data Risk: Low direct data risk, moderate benchmark-process risk.

- Security/Compliance: None directly; this is benchmark runtime and process
  integrity.

- Invariant Violated: The default local benchmark command should provide honest
  fast developer signal without pretending to be the same thing as release-safe
  publication proof.

- Workaround: Manual case filtering and ad hoc mode or cache narrowing. Not
  acceptable as the primary operator contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not narrate the quick profile as release proof. Do not
  refresh `latest.v1.json` from anything except a full `proof` profile run that
  satisfies the publication contract.

- Preflight Checks: Inspect the benchmark component spec, release benchmark
  guidance, and benchmark runner tests before changing profile defaults or
  publication eligibility.

- Regression Tests Added: `test_run_benchmarks_quick_profile_defaults_to_representative_matched_pair`,
  `test_run_benchmarks_supports_family_filtered_shards`

- Monitoring Updates: Benchmark reports and progress ledgers now record
  `benchmark_profile`, `selection_strategy`, and shard metadata.

- Residual Risk: Full proof runs are still expensive because they are honest
  live matched-pair Codex executions. That is acceptable as long as the
  operator contract keeps them explicit and shardable.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`,
  `2026-04-01-benchmark-relative-efficiency-guardrails-punish-success-against-failed-baseline.md`

- Version/Build: `v0.1.7` benchmark profile-split and proof-lane hardening
  wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root .`,
  `odylith benchmark --repo-root . --profile proof`,
  `--family`,
  `--shard-count`,
  `--shard-index`

- Customer Comms: Maintainer docs should say explicitly that `quick` is local
  developer signal and `proof` is the release-safe publication lane.

- Code References: `src/odylith/runtime/context_engine/odylith_context_engine.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
