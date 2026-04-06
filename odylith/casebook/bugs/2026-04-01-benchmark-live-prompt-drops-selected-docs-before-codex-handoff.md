- Bug ID: CB-029

- Status: Closed

- Created: 2026-04-01

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark runner built Odylith packets with the correct
  supporting docs and contracts, then dropped those selected docs from the
  Codex-facing prompt payload before launching the live `odylith_on` run.

- Impact: Odylith could honestly select the right benchmark governance truth
  and still lose required-path recall against `odylith_off` because the live
  Codex lane never saw the selected docs. This made the benchmark punish
  Odylith for an internal handoff bug rather than for the underlying retrieval
  or memory system.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  benchmark prompt-token accounting, live prompt contract, benchmark accuracy
  interpretation.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live `odylith_on` benchmark runs using the Codex CLI runner.

- Root Cause: `_build_packet_payload(...)` returned top-level `docs`, but the
  live handoff only forwarded `_PROMPT_PAYLOAD_KEYS =
  {"context_packet", "narrowing_guidance"}`. The live prompt formatter then
  looked for `prompt_payload["docs"]`, found nothing, and omitted the selected
  contracts from the first-pass evidence cone shown to Codex.

- Solution: Treat selected docs as first-class prompt payload, not operator
  diagnostics. The live prompt contract now preserves `docs` and
  `relevant_docs`, and the prompt formatter deduplicates doc candidates across
  top-level docs, relevant docs, and retrieval-plan selected docs before
  emitting the Odylith focus section.

- Verification: Added regression coverage that proves the benchmark runner
  passes the selected benchmark docs through `run_live_scenario(...)`, that the
  prompt-token accounting now includes those docs, and that the live prompt
  formatter renders doc focus from both `docs` and fallback `relevant_docs` or
  `selected_docs`. Focused benchmark runner and live-execution suites pass.

- Prevention: Any evidence surface that Odylith expects the live model to use
  must be preserved in the Codex-facing prompt payload or explicitly excluded
  from both prompt accounting and accuracy claims. Silent packet-to-prompt
  amputation is benchmark corruption.

- Detected By: Manual architectural audit during the 2026-04-01 strict
  raw-Codex benchmark hardening wave after a live run showed Odylith selecting
  the right governance docs internally but still missing them in observed live
  paths.

- Failure Signature: A benchmark payload includes `docs` at packet-build time,
  but live prompt traces, prompt-token accounting, and Codex-observed paths
  behave as if no selected docs were ever provided.

- Trigger Path: `odylith benchmark --repo-root . --mode odylith_on --mode odylith_off`
  through `_run_scenario_mode(...)` and `run_live_scenario(...)`.

- Ownership: Benchmark prompt contract and live Codex handoff integrity.

- Timeline: The same benchmark hardening wave that exposed the fake raw
  baseline and contamination issues also surfaced that Odylith-selected docs
  were not actually being shown to the live model. The contract was corrected
  the same day.

- Blast Radius: Required-path recall, required-path precision, prompt-token
  deltas, benchmark family narratives, and any conclusion drawn from live
  `odylith_on` underperformance on governance-heavy tasks.

- SLO/SLA Impact: Benchmark credibility and tuning decisions degrade because
  maintainers can chase retrieval or memory changes when the actual defect is a
  prompt boundary drop.

- Data Risk: Low direct data risk, high evaluation-integrity risk.

- Security/Compliance: Not a security defect; this is a benchmark truth and
  product measurement defect.

- Invariant Violated: If Odylith selects a doc or contract as part of the live
  evidence cone, that surface must remain visible in the live Codex prompt and
  must count toward prompt-payload accounting.

- Workaround: None acceptable for publication. Manual packet inspection can
  diagnose the issue but cannot salvage a run already launched with the bad
  prompt contract.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not narrate live benchmark misses as retrieval or memory
  failures until the prompt payload is proven to contain the selected evidence
  surfaces.

- Preflight Checks: Inspect the benchmark component spec, `_PROMPT_PAYLOAD_KEYS`,
  `_odylith_focus_lines(...)`, and the prompt handoff regression tests before
  changing live benchmark prompt logic.

- Regression Tests Added: `test_benchmark_runner_gate_hot_path_keeps_reviewer_guide_visible_in_live_prompt_payload`,
  `test_run_scenario_mode_passes_selected_docs_to_live_prompt_payload`,
  `test_odylith_focus_lines_fall_back_to_relevant_docs_and_selected_docs`.

- Monitoring Updates: Prompt artifact token accounting now reflects selected
  docs as Codex-facing input rather than operator-only diagnostics.

- Residual Risk: The corrected prompt contract removes one major false loss
  mode, but Odylith can still lose honestly if retrieval, reasoning, or edit
  strategy remain worse than `odylith_off` on a given task.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`

- Version/Build: `v0.1.7` benchmark integrity hardening wave on 2026-04-01.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_REASONING_MODEL`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT`.

- Customer Comms: Benchmark narratives must distinguish genuine retrieval or
  reasoning misses from harness prompt-boundary defects.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
