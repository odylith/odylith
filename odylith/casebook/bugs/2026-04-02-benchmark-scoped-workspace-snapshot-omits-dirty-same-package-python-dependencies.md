- Bug ID: CB-044

- Status: Open

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The shared live-workspace snapshot for `odylith_on` and
  `odylith_off` could copy only the explicitly selected dirty Python file while
  omitting dirty sibling modules from the same package that were still needed
  for imports. That produced disposable workspaces that could not execute the
  real local package shape the benchmark was supposed to compare.

- Impact: Proof validation and fit can fail with import errors that have
  nothing to do with Odylith quality. Both compared lanes may be forced through
  a partial package that a real developer workspace would never present,
  distorting the clean-room story and hiding the real next product weakness.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  shared live-workspace snapshot contract, proof-lane validator imports,
  disposable package integrity, validator-backed proof accounting.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live proof reruns on a dirty source tree where multiple
  sibling modules inside one Python package changed together.

- Root Cause: The benchmark snapshot allowlist optimized for exact touched
  files. That kept the clean-room narrow, but it was not import-closed. When a
  selected dirty file inside `src/odylith/runtime/evaluation/` imported a dirty
  sibling module from the same package, the disposable worktree could still be
  missing that sibling and fail inside validation for a harness reason rather
  than a product reason.

- Solution: Expand the shared snapshot allowlist to include dirty same-package
  Python siblings whenever a dirty Python file from that package is already in
  scope. Keep the expansion shared across both compared lanes and bounded to
  the same package rather than widening arbitrarily.

- Verification: Added focused regression coverage in
  `tests/unit/runtime/test_odylith_benchmark_runner.py` proving that live
  workspace snapshot selection keeps dirty same-package Python siblings
  together. A live rerun is still pending to confirm the fix against the weak
  proof slice.

- Prevention: Clean-room fairness is not just about making the snapshot small.
  It also has to represent a runnable local package. Partial-package imports
  are harness corruption, not honest baseline pressure.

- Detected By: Targeted weak-family proof rerun `b77ee8df90889a2a`, where
  `release-benchmark-publication-proof` hit
  `ImportError: cannot import name 'odylith_benchmark_prompt_payloads' from
  'odylith.runtime.evaluation'` inside the disposable workspace even though the
  sibling module was dirty in the real repo.

- Failure Signature: Disposable proof worktrees fail with import errors for
  dirty sibling modules that exist in the main repo but were omitted from the
  scoped snapshot.

- Trigger Path: Shared live-workspace snapshot planning in the proof runner
  before disposable worktree provisioning.

- Ownership: Benchmark shared-snapshot contract and live proof validator
  integrity.

- Timeline: The strict snapshot wave correctly removed broad dirty-tree
  overlay, then exposed that the narrowed snapshot could still become too
  narrow for dirty same-package Python imports on proof validators.

- Blast Radius: Proof validation success, execution fit, weak-family tuning,
  and confidence that `odylith_off` is being compared on the same runnable task
  shape as `odylith_on`.

- SLO/SLA Impact: Maintainers can chase false product regressions instead of
  fixing the remaining real grounding or execution misses.

- Data Risk: Low direct data risk, high benchmark-integrity risk.

- Security/Compliance: This is a local packaging and trust-boundary bug, not a
  remote exploit.

- Invariant Violated: A clean-room live benchmark may narrow repo truth, but it
  may not fabricate a partial local Python package that breaks imports for one
  or both compared lanes.

- Workaround: Manual snapshot expansion or ad hoc reruns from a cleaner tree,
  but neither is acceptable as a publication process.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not “fix” this by weakening `odylith_off` or by
  widening only the Odylith lane. The shared snapshot has to stay the same for
  both compared lanes.

- Preflight Checks: Inspect live snapshot planning, dirty-file selection, and
  same-package import behavior before tightening snapshot scope further.

- Regression Tests Added:
  `test_live_workspace_snapshot_paths_include_dirty_same_package_python_dependencies`

- Monitoring Updates: Treat disposable-worktree import errors on dirty sibling
  modules as benchmark invalidation until the snapshot planner shows the same
  runnable package shape to both lanes.

- Residual Risk: Medium until a new weak-family rerun proves that same-package
  expansion is sufficient. If future failures reveal cross-package dirty import
  gaps, the next expansion must stay shared and bounded rather than turning
  back into a whole-tree overlay.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`,
  `2026-04-02-benchmark-validator-truth-restore-rehydrates-ambient-repo-state-outside-scoped-snapshot.md`

- Version/Build: `v0.1.7` benchmark clean-room hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL=gpt-5.4`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT=medium`

- Customer Comms: Do not accept proof failures caused by partial disposable
  packages as evidence that Odylith itself is worse than raw Codex.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_runner.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
