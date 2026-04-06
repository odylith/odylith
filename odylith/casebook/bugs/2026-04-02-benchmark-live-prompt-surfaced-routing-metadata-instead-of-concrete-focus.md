- Bug ID: CB-039

- Status: Closed

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark prompt for `odylith_on` exposed compact
  routing metadata such as `selection_state`, `selected_counts`, and raw route
  hints, and in architecture cases could fall back to dumping compact
  `architecture_audit` JSON instead of rendering a concrete first-pass read
  list for Codex.

- Impact: Odylith could retrieve the right slice internally and still lose the
  proof run honestly because the live Codex lane saw weak or machine-oriented
  focus cues. That encouraged unnecessary repo widening, hurt required-path
  precision, inflated hallucinated-surface rate, and made the benchmark story
  look worse than the underlying retrieval posture.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`, proof prompt
  contract, architecture benchmark handoff, benchmark README and SVG wording.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live `odylith benchmark --repo-root . --profile proof`
  matched-pair runs.

- Root Cause: The live prompt formatter optimized for compact packet fidelity
  rather than model-facing actionability. It rendered internal route state that
  explains Odylith's own runtime but does not help Codex stay narrow, and it
  did not translate architecture packet fields such as `required_reads` into a
  concrete read list.

- Solution: Render the live `odylith_on` focus as concrete starting files,
  supporting docs or contracts, architecture required reads, and explicit
  narrowing guidance. Remove raw route-state codes from the prompt and replace
  them with user-facing bounded-slice instructions that tell Codex to widen
  only when the listed surfaces prove insufficient or contradictory.

- Verification: Added prompt regression coverage for concrete focus rendering,
  architecture required-read projection, and stricter widening instructions.
  Benchmark runner, live-execution, graph, and hygiene suites pass after the
  prompt contract and public timing language update.

- Prevention: Any Odylith packet field shown to the live model must be audited
  for model-facing usefulness, not just internal traceability. Compact runtime
  metadata belongs in diagnostics unless it materially improves the model's
  first-pass evidence discipline.

- Detected By: Manual proof-run triage after `odylith_on` underperformed on
  precision-heavy families despite better internal packet grounding than the
  live Codex traces suggested.

- Failure Signature: Live prompt traces show route or selection codes instead
  of a concrete read list, architecture cases dump compact audit JSON, and
  `odylith_on` widens into unrelated repo surfaces even when the scenario's
  truthful slice is narrow.

- Trigger Path: `odylith benchmark --repo-root . --profile proof` through
  `_prepare_live_scenario_request(...)` and `odylith_focus_lines(...)`.

- Ownership: Benchmark live prompt contract and proof-lane grounding handoff.

- Timeline: The strict raw-Codex honest-baseline redesign exposed that Odylith
  was no longer losing only to missing docs or attribution noise. The next
  failure layer was the Codex-facing prompt itself, which still spoke in
  compact runtime metadata instead of bounded concrete surfaces.

- Blast Radius: Proof-lane recall and precision interpretation, architecture
  benchmark credibility, family-level fit stories, and README benchmark trust.

- SLO/SLA Impact: Benchmark tuning could chase memory or retrieval changes when
  the immediate problem was the last-mile handoff to the live model.

- Data Risk: Low direct data risk, high evaluation-integrity risk.

- Security/Compliance: None directly; this is a prompt-contract and benchmark
  truth defect.

- Invariant Violated: Odylith's live proof prompt must present the model with a
  concrete first-pass evidence cone. Internal route metadata must not displace
  the actual read list the model should follow.

- Workaround: Manual prompt inspection and ad hoc reviewer interpretation. Not
  acceptable as a benchmark contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not interpret proof-lane widening as a retrieval or
  memory failure until the live prompt is confirmed to render concrete
  Odylith-selected surfaces rather than only compact runtime metadata.

- Preflight Checks: Inspect `odylith_focus_lines(...)`, architecture prompt
  payload rendering, and benchmark README or graph wording together before
  changing live proof prompt semantics again.

- Regression Tests Added:
  `test_odylith_focus_lines_prioritize_selected_files_and_docs`,
  `test_odylith_focus_lines_render_architecture_required_reads`,
  `test_agent_prompt_marks_selected_docs_as_approved_read_only_grounding`

- Monitoring Updates: The public benchmark story now labels proof timing as
  time to valid outcome, which matches the task-completion measurement basis
  used by the live prompt and report contract.

- Residual Risk: Cleaner prompt focus should reduce false widening, but Odylith
  can still lose honestly on proof if retrieval choice, edit strategy, or
  validator handling remain worse than `odylith_off`.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-prompt-drops-selected-docs-before-codex-handoff.md`,
  `2026-04-01-benchmark-observed-path-attribution-counts-transitive-links-from-doc-content.md`,
  `2026-04-02-benchmark-live-proof-overstates-paired-session-metrics-and-reuses-packet-era-guardrails.md`

- Version/Build: `v0.1.7` benchmark prompt-contract hardening wave on
  2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT`

- Customer Comms: Public benchmark tables and graphs should say `time to valid
  outcome` and should describe the live prompt as a bounded grounded read list,
  not as abstract route metadata.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_prompt.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_graphs.py`

- Runbook References: `docs/benchmarks/README.md`,
  `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
