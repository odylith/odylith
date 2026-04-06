- Bug ID: CB-049

- Status: Open

- Created: 2026-04-03

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Several live benchmark scenarios now explicitly say "repair if
  needed, otherwise preserve current truth and stop," but the benchmark corpus
  and live scorer still treated those slices as mandatory-write tasks. As a
  result, a validator-backed no-op could still score as failed expectation or
  failed write-surface precision even when the grounded tree already satisfied
  the contract.

- Impact: `odylith_on` is biased toward speculative edits on developer-core
  recovery and publication slices such as
  `consumer-install-upgrade-runtime-contract`,
  `install-time-agent-activation-contract`,
  `managed-runtime-repair-and-rollback-contract`,
  `release-benchmark-publication-proof`, and
  `benchmark-raw-baseline-publication-contract`. This inflates latency and
  token cost, degrades fit, and can keep live proof status on `hold` even when
  the repo already passes the real validators.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`, live
  repair/publication scenario contract in
  `odylith/runtime/source/optimization-evaluation-corpus.v1.json`, bundled
  corpus mirror, validator-backed no-op scoring discipline.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live proof shards for install, activation, repair, and
  publication families.

- Root Cause: The prompt wording was hardened first, but the benchmark source
  contract still only exposed `needs_write`, and the live scorer still
  required a non-empty candidate write set for success. That left the prompt,
  corpus metadata, and scorer semantics out of sync on slices whose honest
  outcome can be "already correct."

- Solution: Add an explicit `allow_noop_completion` contract to the affected
  scenarios, carry that metadata through scenario loading, teach the live
  prompt to state that validator-backed no-op is fully acceptable, and update
  live expectation plus write-surface accounting so successful no-op
  completion is not scored as a write failure.

- Verification: Focused unit coverage for benchmark runner, prompt payloads,
  and live execution is green after the change. Targeted proof reruns for the
  affected live families are the remaining verification step.

- Prevention: Whenever a benchmark prompt allows "already correct, stop," the
  corpus metadata and live scorer must expose the same contract explicitly. Do
  not rely on prompt prose alone for evaluation semantics.

- Detected By: Install-family weak-slice recovery on 2026-04-03 while tracing
  why benchmark live proof still spent heavy time and tokens after the
  activation and snapshot fixes landed.

- Failure Signature: The live result can show passing validators or an
  otherwise grounded completion, yet still report `expectation_ok = false` or
  `write_surface_precision = 0.0` solely because no file was changed on a
  slice whose prompt explicitly allowed stopping with no file changes.

- Trigger Path: `odylith benchmark --repo-root . --profile proof --case-id consumer-install-upgrade-runtime-contract`
  and sibling repair/publication slices through the live Codex CLI runner.

- Ownership: Benchmark corpus contract, live prompt discipline, live
  expectation scoring.

- Timeline: Prompt wording for validator-backed no-op was added earlier during
  activation-family recovery. On 2026-04-03, deeper install-runtime analysis
  exposed that the corpus and live scorer still silently penalized the same
  outcome.

- Blast Radius: Developer-facing benchmark credibility, install and activation
  weak-family recovery, release publication proof honesty, and the release push
  to move benchmark status from `hold` back to `pass`.

- SLO/SLA Impact: Live benchmark quality regresses immediately on
  recovery-style tasks because the scorer rewards unnecessary writes over
  correctly stopping on current truth.

- Data Risk: Low direct data risk; high benchmark quality risk.

- Security/Compliance: No direct security impact.

- Invariant Violated: A validator-backed no-op that satisfies the stated task
  contract must not be scored as a write failure.

- Workaround: Manual shard inspection can recognize the false penalty, but
  that is not an acceptable publication path.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: On live repair/publication slices, do not invent code or
  docs changes simply because the task is write-capable; first prove whether
  the grounded tree already satisfies the contract.

- Preflight Checks: Inspect this bug, `CB-048`, the active B-021 plan, the
  affected corpus entries, and the live execution prompt plus scorer tests
  before changing this path.

- Regression Tests Added: Yes. Benchmark runner metadata loading, live prompt
  wording, and live no-op write accounting now have focused unit coverage.

- Monitoring Updates: Track the affected live families for
  `expectation_success`, `write_surface_precision`, latency, prompt tokens, and
  whether successful no-op completions still appear as failed write behavior.

- Residual Risk: The packet-only diagnostic benchmark still reports write-slice
  shape rather than validator-backed no-op outcome, so live proof remains the
  authoritative check for these slices until a broader contract alignment wave
  lands.

- Related Incidents/Bugs:
  `2026-04-03-benchmark-live-agent-activation-prefers-speculative-install-guidance-rewrites-over-validator-backed-no-op.md`,
  `2026-04-02-benchmark-support-doc-selector-overweights-generic-guidance-on-proof-slices.md`,
  `2026-04-02-benchmark-scoped-workspace-snapshot-omits-dirty-same-package-python-dependencies.md`

- Version/Build: `v0.1.7` benchmark weak-family recovery wave in progress on
  2026-04-03.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS`,
  `ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS`.

- Customer Comms: Do not claim the install/publication weak slices are fully
  recovered until the focused proof shards reflect the new no-op contract with
  validator-backed improvement.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `odylith/runtime/source/optimization-evaluation-corpus.v1.json`,
  `src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
