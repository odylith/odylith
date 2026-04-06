- Bug ID: CB-043

- Status: Open

- Created: 2026-04-02

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The live benchmark clean-room still restored stripped
  validator-truth files from the ambient repo root instead of from the scoped
  benchmark workspace snapshot. That let unrelated dirty repo state leak back
  into disposable worktrees immediately before validator execution.

- Impact: Proof quality and fairness can be corrupted even when the live Codex
  subprocess itself is isolated correctly. A validator can fail on unrelated
  dirty files, making `odylith_on` or `odylith_off` look worse for reasons
  that are outside the same-task comparison contract.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_isolation.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  validator-truth restore contract, disposable worktree integrity, proof-lane
  validator-backed success.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live `odylith benchmark --repo-root . --profile proof`
  runs on a dirty working tree with unrelated changes.

- Root Cause: The shared snapshot allowlist was only applied while the
  disposable workspace was first provisioned. After the harness stripped
  auto-consumed guidance surfaces for the live Codex phase, validator restore
  still copied the stripped files back from the ambient repo root instead of
  from a stash captured inside the scoped workspace snapshot.

- Solution: Capture stripped validator-truth files from the scoped benchmark
  workspace before removal, store them in a dedicated temporary truth root, and
  restore only from that scoped stash before validators run. Never restore
  benchmark truth directly from the ambient repo root.

- Verification: Added focused regression coverage for scoped validator-truth
  capture and restore in
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`. The broader
  proof rerun is still pending to verify that the fairness fix holds on the
  weak-family slice and the full corpus.

- Prevention: Any clean-room restore path must stay snapshot-rooted. A later
  restore from the ambient repo root is benchmark contamination, even if the
  initial worktree overlay was correctly scoped.

- Detected By: Targeted weak-family proof rerun `b77ee8df90889a2a`, where
  validator failures on `closeout-surface-path-normalization` and
  `benchmark-component-governance-truth` still surfaced unrelated dirty
  worktree overlap after the earlier isolation hardening wave.

- Failure Signature: Validator output in a disposable workspace references
  unrelated dirty repo files outside the scoped benchmark snapshot, or strict
  sync fails on ambient surfaces that the scenario never selected.

- Trigger Path: `_temporary_worktree(...)` strip phase followed by validator
  restore in the live proof lane.

- Ownership: Benchmark isolation trust boundary and validator restore contract.

- Timeline: The ambient-state hardening wave fixed Codex home, env, and temp
  isolation first. The next weak-family rerun then exposed that restore-time
  validator truth could still rehydrate ambient repo state, which is this
  narrower contamination bug.

- Blast Radius: Proof-lane validation success, execution fit, README benchmark
  trust, and any maintainer conclusion drawn from live weak-family failures.

- SLO/SLA Impact: Benchmark publication can stay on `hold` for the wrong
  reason, and maintainers can waste tuning effort on harness artifacts instead
  of product weaknesses.

- Data Risk: Low direct data risk, high benchmark-integrity risk.

- Security/Compliance: This is a local trust-boundary bug, not a remote
  security exploit.

- Invariant Violated: If a live proof lane says both compared lanes saw only
  the shared scoped snapshot, validator restore may not reintroduce unrelated
  ambient repo state later in the run.

- Workaround: Manual disposable-worktree inspection after a failed run can
  reveal the leak, but that is diagnosis only and not acceptable publication
  proof.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Do not explain away validator-backed proof misses until
  the restore path is known to be snapshot-rooted.

- Preflight Checks: Inspect `capture_workspace_validator_truth(...)`,
  `restore_workspace_validator_truth(...)`, the benchmark component spec, and
  the live proof worktree contract before changing validator restore again.

- Regression Tests Added:
  `test_capture_workspace_validator_truth_copies_scoped_workspace_files_only`,
  `test_restore_workspace_validator_truth_restores_stripped_files_only`

- Monitoring Updates: Treat any validator-time reference to unrelated ambient
  dirty repo files as benchmark invalidation, not just as a normal failed
  validator.

- Residual Risk: Medium until the next targeted weak-family rerun and the next
  full proof rerun confirm that validator-backed outcomes no longer drift on
  ambient dirty-state restore. The partial-package snapshot bug is tracked
  separately in `CB-044`.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`,
  `2026-04-01-benchmark-sandbox-strip-policy-deletes-truth-bearing-maintainer-docs.md`

- Version/Build: `v0.1.7` benchmark clean-room hardening wave on 2026-04-02.

- Config/Flags: `odylith benchmark --repo-root . --profile proof`,
  `ODYLITH_REASONING_MODEL=gpt-5.4`,
  `ODYLITH_REASONING_CODEX_REASONING_EFFORT=medium`

- Customer Comms: Do not narrate proof misses as product weakness if the
  disposable validator phase can still see ambient repo state outside the
  shared snapshot.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_isolation.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
