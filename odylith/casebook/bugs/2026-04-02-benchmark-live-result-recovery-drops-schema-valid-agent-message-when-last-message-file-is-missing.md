- Bug ID: CB-045

- Status: Open

- Created: 2026-04-02

- Severity: P0

- Reproducibility: Medium

- Type: Product

- Description: The live proof runner could score a Codex run as
  `missing_schema_output` whenever `--output-last-message` failed to produce
  `result.json`, even if the Codex JSON event stream already contained a
  schema-valid final `agent_message` with the required benchmark result.

- Impact: Proof validation, fit, and expectation success could undercount real
  `odylith_on` wins for a transport reason unrelated to grounding or execution
  quality. This particularly hurts the strict honest baseline because both
  lanes use the same Codex CLI transport, so a flaky last-message file can
  masquerade as product weakness.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  structured-output recovery contract, proof-lane completion accounting.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live `odylith benchmark --repo-root . --profile proof`
  matched-pair runs with Codex CLI `--json`.

- Root Cause: The benchmark runner treated `result.json` as the sole source of
  truth for structured output even though the same Codex invocation also emits
  JSON-line events, including the final `agent_message` text, to stdout.

- Solution: Prefer `result.json` when it exists, but recover a schema-valid
  final result from the last `agent_message` event before failing closed on
  missing schema output.

- Verification: Added regression coverage proving that
  `_structured_output(...)` now restores a valid result from the event stream
  when the last-message file is missing and still fails closed when neither
  transport contains a valid structured result.

- Prevention: Any benchmark transport that duplicates the final result across
  multiple channels must reconcile those channels before declaring product
  failure. Harness I/O loss is not benchmark truth.

- Detected By: Targeted weak-family proof rerun triage after several cases
  passed focused local work yet still landed `missing_schema_output`.

- Failure Signature: `live_execution.structured_output.validation_summary`
  reports `missing_schema_output` while the Codex stdout event stream contains
  a schema-valid final `agent_message`.

- Trigger Path: `odylith benchmark --repo-root . --profile proof` through
  `_run_live_codex_cli(...)` and `_structured_output(...)`.

- Ownership: Benchmark live execution contract and proof completion recovery.

- Timeline: The clean-room fairness wave removed larger contamination bugs,
  exposing that some remaining proof losses were pure structured-output
  transport drops rather than real task failures.

- Blast Radius: Proof validation success, execution fit, expectation success,
  and maintainers' confidence in live benchmark losses.

- SLO/SLA Impact: Maintainers can chase selector or memory changes when the
  immediate problem is a dropped final schema artifact.

- Data Risk: Low direct data risk, high benchmark-integrity risk.

- Security/Compliance: None directly; this is a harness transport-recovery
  defect.

- Invariant Violated: A live proof run must fail only on genuine task or
  validator failure, not because one of two equivalent structured-output
  transport paths was unavailable.

- Workaround: Manual inspection of the Codex JSON event stream. Not acceptable
  for benchmark publication.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not “fix” this by weakening `odylith_off` or by
  relaxing the final JSON contract. Recover the result from the existing same
  Codex execution instead.

- Preflight Checks: Inspect `result.json`, the JSON event stream, and final
  schema parsing together before changing proof completion accounting again.

- Regression Tests Added:
  `test_structured_output_recovers_from_agent_message_event_when_last_message_file_is_missing`,
  `test_structured_output_reports_missing_schema_when_no_file_or_agent_message_exists`

- Monitoring Updates: Treat `missing_schema_output` as benchmark-invalid until
  both the last-message file and event-stream fallback paths have been checked.

- Residual Risk: Medium until a fresh weak-family proof rerun confirms that
  event-stream recovery flips real proof cases instead of only test fixtures.

- Related Incidents/Bugs:
  `2026-04-02-benchmark-live-prompt-surfaced-routing-metadata-instead-of-concrete-focus.md`,
  `2026-04-02-benchmark-validator-truth-restore-rehydrates-ambient-repo-state-outside-scoped-snapshot.md`

- Version/Build: `v0.1.7` benchmark proof transport-recovery hardening wave on
  2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL=gpt-5.4`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT=medium`

- Customer Comms: Do not count a missing `result.json` as evidence that
  Odylith lost when the same Codex run already emitted the valid structured
  answer in the event stream.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
