- Bug ID: CB-107

- Status: Open

- Created: 2026-04-12

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: Live observed-path attribution starts from Odylith prompt-payload
  surfaces in `odylith_on` but does not symmetrically credit equivalent
  prompt-visible raw baseline anchors exposed to `odylith_off`, making required-
  path precision and recall structurally easier for the Odylith lane.

- Impact: The live benchmark can award path-discovery credit to `odylith_on`
  for repo anchors that were merely prompt-visible while denying equivalent
  credit to `odylith_off`. That weakens any fairness claim tied to required-path
  scoring, support-doc discovery, or grounded-file recall.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, benchmark
  required-path scoring contract, proof fairness interpretation.

- Environment(s): Odylith product repo maintainer mode, live benchmark proof
  and diagnostic lanes.

- Root Cause: The live runner reused Odylith prompt-payload path extraction for
  `odylith_on` but never mirrored the non-live runner's raw prompt-visible path
  extraction for `odylith_off`. The lane scoring contract therefore drifted from
  the runner's own non-live fairness model.

- Solution: Make the live observed-path scorer symmetric for prompt-visible repo
  anchors by crediting both Odylith prompt payload surfaces and raw baseline
  prompt anchors while preserving the no-hidden-truth rule against transitive
  doc links and internal route metadata.

- Verification: Add live-execution and runner tests for raw prompt-visible path
  attribution, hidden-path rejection, and observed-path source reporting; rerun
  benchmark proof and diagnostic profiles.

- Prevention: Any benchmark path-attribution helper used in one live lane must
  be checked for equivalent visibility credit in the other lane before it is
  treated as a publication-facing fairness primitive.

- Detected By: Maintainer fairness audit comparing live and non-live benchmark
  observed-path logic.

- Failure Signature: `odylith_on` observed paths include prompt-payload files
  such as `README.md` while `odylith_off` observed paths omit equivalent raw
  prompt anchors despite those anchors being visible in the prompt.

- Trigger Path: `odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark path-attribution fairness, required-path scoring, and
  publication trust.

- Timeline: The live benchmark inherited richer Odylith prompt structures, but
  the raw baseline lane never received a matching prompt-visible path extraction
  path.

- Blast Radius: Required-path recall and precision, family deltas, benchmark
  fairness claims, and release-proof credibility.

- SLO/SLA Impact: No runtime-service impact; high measurement-integrity impact.

- Data Risk: Low direct data risk; high scoring and interpretation risk.

- Security/Compliance: None directly.

- Invariant Violated: Prompt-visible repo anchors must be scored symmetrically
  across live lanes. The runner must not grant silent path credit to only one
  side of the published comparison.

- Workaround: Ignore prompt-visible path metrics when reading the live report.
  Not acceptable for release proof.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Keep prompt-visible path credit explicit, symmetric, and
  bounded to files the lane could actually see before command execution.

- Preflight Checks: Compare live and non-live observed-path helpers, raw prompt
  anchor extraction, and transitive-link filtering before changing path-scoring
  semantics.

- Regression Tests Added: Pending.

- Monitoring Updates: Pending observed-path source reporting in benchmark
  results.

- Residual Risk: Symmetric prompt-path credit does not by itself make the
  benchmark serious; corpus realism and contract honesty still need to land in
  the same release.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-observed-path-attribution-counts-transitive-links-from-doc-content.md`
  and
  `2026-04-01-benchmark-live-prompt-drops-selected-docs-before-codex-handoff.md`

- Version/Build: `v0.1.11` benchmark fairness hardening wave on 2026-04-12.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`

- Customer Comms: Benchmark docs should explain observed-path credit sources and
  note that prompt-visible anchors are credited symmetrically across lanes.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
