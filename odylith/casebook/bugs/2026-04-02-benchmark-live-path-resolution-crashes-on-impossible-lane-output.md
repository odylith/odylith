- Bug ID: CB-035

- Type: Product








- Status: FixedPendingRelease

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High


- Description: The live benchmark runner trusted lane-emitted workspace path
  tokens too much. When a Codex lane surfaced an impossible file name in a
  `changed_files` payload or file-change event, the harness attempted to
  `stat()` that path inside the disposable workspace and crashed the entire
  proof run with `OSError: [Errno 63] File name too long`.

- Impact: A single malformed lane output could fail the full benchmark corpus
  even though the honest outcome should have been a degraded lane result with
  missing-path attribution. That undermined proof-run stability and made the
  benchmark harness look less trustworthy than the product it was trying to
  measure.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  live observed-path attribution, candidate-write detection, benchmark proof
  stability.

- Environment(s): Odylith product repo maintainer mode, live Codex CLI proof
  runs, disposable benchmark workspaces on macOS.

- Root Cause: `_resolve_workspace_file`, `_relative_workspace_path`, and
  `_existing_file_paths` assumed lane-reported path tokens were safe to
  resolve and inspect. They did not suppress filesystem errors such as
  `ENAMETOOLONG` when the lane emitted nonsense or adversarial path strings.

- Solution: Fail closed on impossible workspace paths. Path resolution and
  file checks now suppress filesystem resolution errors and simply drop invalid
  tokens from observed-path and write-surface attribution instead of failing
  the report.

- Verification: Added regression coverage proving the runner ignores
  impossible long path components in both direct path resolution and
  mixed valid-plus-invalid observed-path events.

- Prevention: Treat lane-emitted path data as untrusted input. Benchmark
  attribution logic must only elevate paths that can be safely resolved inside
  the disposable workspace.

- Detected By: Full `gpt-5.4 / medium` proof rerun on 2026-04-02 after the
  stricter live Codex harness refresh.

- Failure Signature: `OSError: [Errno 63] File name too long` under
  `.odylith/runtime/odylith-benchmarks/in-progress.v1.json`, with the current
  scenario stuck on a live lane.

- Trigger Path: `odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark live execution harness and path-attribution safety.

- Timeline: The first full proof rerun under the refreshed live harness
  crashed on `broad-shared-guarding` after a live lane emitted an impossible
  path token. The resolver was hardened to fail closed, and the proof rerun
  was restarted.

- Blast Radius: Entire proof-corpus stability, benchmark publication
  confidence, and maintainer trust in long-running honest benchmark reruns.

- SLO/SLA Impact: Full proof reruns could abort after several minutes of live
  execution, wasting benchmark time and invalidating publication attempts.

- Data Risk: Low direct data risk, high proof-stability risk.

- Security/Compliance: None directly, but the fix aligns with a strict
  sandboxing posture by treating lane output as untrusted.

- Invariant Violated: Invalid lane output must degrade that lane's measured
  quality, not crash the benchmark harness.

- Workaround: Rerun the proof after restarting the benchmark process; no safe
  operator workaround existed before the fix.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Never treat lane-reported workspace paths as authoritative
  until the harness confirms they resolve safely inside the disposable
  workspace.

- Preflight Checks: Exercise live benchmark path attribution with malformed
  path tokens before widening the proof corpus or changing live structured
  output contracts.

- Regression Tests Added:
  `test_resolve_workspace_file_ignores_enametoolong_path_component`,
  `test_observed_paths_from_events_ignores_invalid_changed_file_tokens`

- Monitoring Updates: Benchmark reruns now surface lane-quality misses instead
  of infrastructure crashes when path tokens are impossible to resolve.

- Residual Risk: Extremely large but syntactically valid path sets can still
  bloat attribution work, but they no longer crash the benchmark harness.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-observed-path-attribution-counts-transitive-links-from-doc-content.md`

2026-07-02 recurrence: the same path-token trust boundary escaped into the
Casebook dashboard path-link helper. A generated Casebook row contained a
prose-sized token that was treated as a filesystem path, and source-local
`odylith casebook refresh --repo-root .` crashed with
`OSError: [Errno 63] File name too long` before publishing refreshed surfaces.
The forward fix wraps path resolution and existence checks in
`src/odylith/runtime/surfaces/surface_path_helpers.py`, returns an empty href
for unsafe tokens, and proves the behavior with
`tests/unit/runtime/test_surface_path_helpers.py::test_path_link_does_not_stat_prose_sized_tokens`.
The durable guardrail is broader than the original benchmark lane: every
human-visible governance surface must treat extracted path-like text as
untrusted until it resolves safely, and invalid path tokens must degrade the
single link rather than aborting the whole governed refresh.

2026-07-02 follow-up recurrence: the source-local helper guard proved the
renderer boundary safe, but Casebook refresh still exposed the upstream
projection-snapshot missed mechanism while refreshing B-142 governance. The
context-engine Casebook snapshot builder extracted path references from raw bug
prose, and `_extract_path_refs` admitted multiline or whitespace-bearing
sentence fragments as repo paths because the token contained a real path
elsewhere in the text. The pinned dashboard then attempted to stat the
prose-sized token and failed with the same `OSError: [Errno 63] File name too
long`. The forward fix adds a generic repo-path token guard in the projection
search owner: path candidates with whitespace, newlines, impossible overall
length, or filesystem-impossible segment length are ignored before link
classification. Regression coverage proves that a real `src/odylith/...` path
inside prose is still extracted while the surrounding multiline sentence is
not. Source-local Casebook refresh then passed with 213 cases and 119 open
cases.

2026-07-02 pinned-dogfood recurrence during the high-volume greenfield
checkpoint: `./.odylith/bin/odylith sync --repo-root . --force` was still
running the pinned 0.1.15 runtime and failed while rendering Casebook because a
prose paragraph was treated as a path and `pathlib.exists()` raised
`OSError: [Errno 63] File name too long`. The same refresh immediately passed
through the current source runtime with
`odylith sync --repo-root . --force`,
including Casebook render, 46 fresh Atlas diagrams, Registry render, Compass
refresh, and top-level shell render. This confirms the fix is present in
current source but not yet shipped in the active pinned dogfood runtime. Future
agents should use source-local refresh for this unreleased checkpoint, then
prove the packaged runtime after building the next dist; they should not
reopen the greenfield post-confirm root cause for this governance refresh
failure.

2026-07-03 repeat during the high-volume shard-08 checkpoint: the pinned
repo-local launcher again failed `casebook refresh` with
`OSError: [Errno 63] File name too long` while linking a prose-sized Casebook
token. This repeated the known unreleased pinned-runtime gap, not the
greenfield post-confirm defect. Keep using source-local governance refresh for
the active branch until the next local release dist packages the path-token
guard, then prove the packaged runtime with Casebook refresh as part of the
installable volume pass.

2026-07-03 repeat during Greenfield campaign-harness governance update: pinned
`./.odylith/bin/odylith casebook refresh --repo-root .` failed while rendering
CB-202 because the pinned context-engine snapshot still exposed a prose-sized
Casebook path token beginning `into the canonical title...`. Source validation
passed first (`213` records checked), and the same Casebook surface refreshed
cleanly through the current source runtime with
`odylith casebook refresh --repo-root .`
(`213` total cases, `120` open). This is the same known shipped-runtime gap:
do not repeat the fix, do not mutate CB-202 to hide parser behavior, and prove
the packaged runtime after the next local dist is built.

2026-07-04 repeat during rendered-projection governance update: pinned
`./.odylith/bin/odylith casebook refresh --repo-root .` failed on the same
prose-sized Casebook path token while source-local refresh passed with `213`
total cases and `120` open. This remains a pinned-runtime packaging gap, not a
new Casebook source-data defect and not a greenfield post-confirm regression.

2026-07-04 repeat during semantic-ownership governance update: pinned Casebook
refresh again failed with File name too long while linking prose-sized CB-202
tokens. This repeated the known unreleased pinned-runtime gap. Do not massage
CB-202 source prose to satisfy the pinned renderer; use the source-local runtime
for governance refresh on this branch and prove the packaged path-token guard in
the next local dist.

2026-07-05 repeat during Greenfield source-title boundary governance update:
pinned `./.odylith/bin/odylith casebook refresh --repo-root .` again failed on
the same prose-sized CB-202 path token after Casebook source validation passed.
The source-local refresh immediately passed with `213` total cases and `120`
open cases in `1.5s`, confirming this is still the known pinned-runtime
packaging gap rather than a new Casebook source defect or a Greenfield
post-confirm regression. Do not repeat source fixes that are already present in
`src/odylith/runtime/surfaces/surface_path_helpers.py`; package and prove the
guard in the next local release dist.

- Version/Build: `v0.1.7` live benchmark harness hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`

- Customer Comms: Benchmark docs should describe the harness as fail-closed on
  invalid lane-emitted paths rather than implying every emitted token is
  authoritative.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `src/odylith/runtime/context_engine/odylith_context_engine_projection_search_runtime.py`,
  `src/odylith/runtime/surfaces/surface_path_helpers.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_context_grounding_hardening.py`,
  `tests/unit/runtime/test_surface_path_helpers.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`

- Fix Commit/PR: Pending.
