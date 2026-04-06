- Bug ID: CB-031

- Status: Closed

- Created: 2026-04-01

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark runner counted repo paths mentioned inside
  raw file-content output as observed surfaces, so reading one selected doc
  could falsely inflate `observed_paths` with every linked README, SVG, skill,
  or auxiliary doc named inside that file.

- Impact: `odylith_on` could win the real retrieval battle and still lose on
  required-path precision and hallucinated-surface rate because its selected
  benchmark docs are link-dense. The harness treated transitive references from
  `sed` or `cat` output as if the model had explicitly inspected those linked
  files.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  live observed-path attribution, required-path precision, hallucinated-surface
  rate, benchmark family deltas.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live Codex CLI benchmark runs.

- Root Cause: `_observed_paths_from_events(...)` extracted repo paths from both
  command strings and all `aggregated_output` text. That was too permissive.
  Listing or search command output can represent directly observed paths, but
  content-printing commands like `sed -n`, `cat`, or `head` often emit file
  contents that mention many other repo paths the agent never opened.

- Solution: Restrict output-based path attribution to path-listing and
  path-search commands such as `rg`, `grep`, `find`, `fd`, `ls`, and relevant
  `git` name-listing commands. Keep extracting paths from command strings,
  file-change events, and structured changed-files output, but stop treating
  transitive references in raw file contents as inspected repo surfaces.

- Verification: Added regression coverage proving that reading
  `docs/benchmarks/REVIEWER_GUIDE.md` via `sed` only counts the guide itself,
  while `rg` listing output still counts matched result paths. Focused live
  benchmark and runner suites pass.

- Prevention: Path attribution must distinguish between “the agent saw this
  path as a search/list result” and “this path happened to appear in the text
  of another file.” Benchmark precision metrics are not trustworthy if those
  cases are conflated.

- Detected By: Honest rerun analysis on 2026-04-01 after `odylith_on` improved
  recall and completion but still lost precision due to extra observed paths
  that matched transitive links embedded inside selected benchmark docs.

- Failure Signature: `observed_paths` contain README files, SVG assets, skill
  docs, or other linked surfaces that appear in a read doc’s content even
  though there is no corresponding listing/search command or explicit open of
  those linked files.

- Trigger Path: `_observed_paths_from_events(...)` during live benchmark result
  assembly.

- Ownership: Live benchmark path-attribution correctness.

- Timeline: The doc handoff and sandbox fixes exposed that Odylith’s remaining
  precision loss was largely attribution noise from transitive links. The
  attribution rule was tightened the same day.

- Blast Radius: Required-path precision, hallucinated-surface rate, benchmark
  hard-quality gating, and any tuning decisions based on those metrics.

- SLO/SLA Impact: Benchmark credibility degrades because maintainers can chase
  retrieval or memory changes when the real issue is path-attribution noise.

- Data Risk: Low direct data risk, high evaluation-integrity risk.

- Security/Compliance: Not a security issue.

- Invariant Violated: Content references printed from a file read are not
  equivalent to explicit inspection of the referenced files and must not be
  counted as observed repo surfaces.

- Workaround: None acceptable for benchmark publication. Manual trace review
  can identify the issue but cannot repair already-computed precision metrics.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not call Odylith’s link-dense governance docs
  “hallucination spread” unless the trace shows explicit listing, search, or
  open behavior for the linked files.

- Preflight Checks: Inspect live observed-path attribution logic before using
  command output as benchmark evidence.

- Regression Tests Added: `test_observed_paths_from_events_ignores_transitive_paths_in_file_content_output`,
  `test_observed_paths_from_events_keeps_paths_from_listing_output`.

- Monitoring Updates: Benchmark triage should treat sudden precision drops from
  doc-heavy tasks as a prompt to inspect the underlying command trace, not only
  the aggregate metric.

- Residual Risk: The attribution rule is fairer now, but future Codex CLI
  event types may require explicit inclusion if they represent direct file
  inspection.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-prompt-drops-selected-docs-before-codex-handoff.md`

- Version/Build: `v0.1.7` benchmark integrity hardening wave on 2026-04-01.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS`,
  `ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS`.

- Customer Comms: Do not frame transitive doc-link mentions as evidence that
  Odylith widened irresponsibly.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `docs/benchmarks/REVIEWER_GUIDE.md`

- Fix Commit/PR: Pending.
