- Bug ID: CB-089

- Status: Open

- Created: 2026-04-09

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: The shared host contract is now host-neutral across runtime,
  guidance, Registry, Atlas, and Compass, but the benchmark subsystem still
  emits Codex-branded canonical fields in live execution and published report
  payloads. Live rows still use values like `raw_codex_cli`, and report token
  accounting still centers `codex_prompt_*` fields even when those names are
  supposed to be legacy compatibility aliases rather than the canonical proof
  schema.

- Impact: The benchmark layer keeps reintroducing Codex-first canon into the
  one subsystem that is supposed to prove host-scoped behavior honestly, which
  makes future Claude proof work and benchmark publication harder than it
  should be.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`,
  benchmark docs under `docs/benchmarks/`, benchmark component truth, and
  benchmark regression tests.

- Environment(s): Odylith product repo maintainer benchmark proof lane,
  benchmark graph publication, benchmark docs, and benchmark regression tests.

- Root Cause: `B-069` cleaned up the shared runtime and governance canon first,
  but the benchmark report schema and live runner payloads still encode the
  original Codex-first benchmark names as if they were the canonical host-
  neutral proof contract.

- Solution: Add host-neutral canonical benchmark fields such as
  `benchmark_host_family`, `agent_prompt_estimated_tokens`, `runner`, and
  host-neutral `packet_source` values, keep the current Codex-branded fields as
  compatibility aliases for one release, and update graphs, docs, and tests to
  prefer the canonical fields first.

- Verification: Repo scan on 2026-04-09 found `raw_codex_cli`,
  `codex_prompt_estimated_tokens`, `codex_prompt_input_tokens`, and
  `codex_output_tokens` still emitted or asserted as canonical benchmark
  fields in the live-runner and graph/test paths.

- Prevention: When a host-neutral contract lands outside the benchmark layer,
  the proof schema must migrate in the same release or be split explicitly as
  a follow-up. Do not leave benchmark canon as the last Codex-branded
  holdout.

- Detected By: `B-069` closeout while separating completed non-benchmark
  cross-host contract work from the remaining benchmark-only schema tail.

- Failure Signature: Benchmark rows or proof graphs use Codex-branded field
  names as canonical output instead of as compatibility aliases.

- Trigger Path: Any benchmark live-execution, graph, or doc change that reads
  `raw_codex_cli` or `codex_prompt_*` as the primary host-neutral proof
  schema.

- Ownership: Benchmark report schema, benchmark live execution, benchmark
  graph publication, and benchmark docs.

- Timeline: `B-069` closed the non-benchmark host-neutral contract on
  2026-04-09 and split this benchmark-only remainder into `B-070`.

- Blast Radius: Benchmark publication, maintainer proof reviews, and future
  multi-host proof work.

- SLO/SLA Impact: No outage, but continued benchmark-schema drift against the
  now-host-neutral product contract.

- Data Risk: Low.

- Security/Compliance: Low direct security risk; this is proof-schema and
  publication honesty debt.

- Invariant Violated: The benchmark proof schema should describe the proof host
  generically and reserve Codex naming for explicit host-scoped publication or
  compatibility aliases only.

- Workaround: Maintainers can interpret the current Codex-branded benchmark
  fields as compatibility aliases manually, but that workaround should not stay
  in the canonical report schema.

- Rollback/Forward Fix: Forward fix behind compatibility aliases.

- Agent Guardrails: When editing benchmark runner, live execution, or graphs,
  distinguish between canonical host-neutral report fields and legacy alias
  fields. Do not add new Codex-branded canonical benchmark fields.

- Preflight Checks: Inspect the benchmark runner, live-execution payloads,
  graph readers, and benchmark docs before editing any benchmark schema field.

- Regression Tests Added: Pending under `B-070`; expected additions include
  canonical benchmark field assertions for runner/live-execution rows, graph
  readers, and compatibility alias behavior.

- Monitoring Updates: Watch benchmark reports and generated docs for renewed
  `raw_codex_cli` or `codex_prompt_*` canon outside compatibility-only lanes.

- Residual Risk: Public proof should remain Codex-host-scoped until Claude has
  its own measured lane; the open work here is schema neutrality, not invented
  cross-host proof.

- Related Incidents/Bugs:
  [2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md](2026-04-09-host-contract-drift-leaks-codex-only-policy-into-claude-and-shared-runtime-surfaces.md)

- Version/Build: Odylith product repo working tree on 2026-04-09.

- Customer Comms: The shared product contract is already host-neutral; this
  remaining fix is about making the benchmark proof schema match that truth.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_graphs.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`,
  `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Pending `B-070`.
