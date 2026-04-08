- Bug ID: CB-069

- Status: Open

- Created: 2026-04-08

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The pinned-dogfood `proof` benchmark lane can wedge mid-corpus
  during release proof. `./.odylith/bin/odylith benchmark --repo-root .
  --profile proof` started a real full warm-plus-cold run, completed part of
  the corpus, then left the top-level benchmark runner alive without
  finalizing a report or failing closed. The release lane therefore had no
  fresh release-safe `latest.v1.json`, even though the process continued to
  hold the lane open as if proof were still progressing.

- Impact: Canonical release proof cannot rely on a full pinned-dogfood
  benchmark rerun when the runner can stall indefinitely mid-corpus. That
  forces maintainers into a version-scoped benchmark override for the release
  or into waiting on a wedged process while the release lane is blocked.

- Components Affected:
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  benchmark progress finalization, benchmark cleanup/interruption handling,
  pinned-dogfood release proof, maintainer benchmark override contract.

- Environment(s): Odylith product repo maintainer mode, pinned dogfood,
  branch `2026/freedom/v0.1.10`, macOS Apple Silicon, local release prep for
  `v0.1.10`.

- Root Cause: Not isolated yet. The live proof runner progressed far enough to
  persist `in-progress.v1.json`, spawn child Codex work, and complete multiple
  scenario results, but the outer benchmark process remained alive after
  forward progress effectively stopped. The failure surface likely sits in the
  live scenario batch orchestration, child cleanup, or finalization path where
  the outer runner can outlive useful work without failing closed.

- Solution: Track a one-release benchmark override for `v0.1.10` in governed
  truth, stop the wedged proof run cleanly, and move benchmark runner tuning
  plus proof restoration back into the next release as an explicit blocker.
  The forward fix should make the proof runner either finish and persist a
  release-safe report or fail with a bounded interrupted/failed status plus
  exact cleanup, never hang indefinitely in a nominally running state.

- Verification: Reproduced on 2026-04-08 with benchmark report
  `0047192366d8bf1c`. The persisted progress file showed `status: running`,
  `phase: executing_scenarios`, `scenario_count: 37`, `completed_scenarios: 4`,
  `completed_results: 8`, `current_cache_profile: warm`, and
  `current_scenario_id: context-engine-daemon-security-hardening`, with
  `updated_utc: 2026-04-08T08:56:57Z`. At the same time the outer process
  `/Users/freedom/code/odylith/.odylith/runtime/current/bin/python -I -m odylith.cli benchmark --repo-root . --profile proof`
  remained alive for more than nine minutes while no completed
  `.odylith/runtime/odylith-benchmarks/latest.v1.json` existed.

- Prevention: Release-proof benchmark execution must be bounded and auditable.
  If the live pair stalls, the runner should mark the run interrupted/failed,
  clean up owned children/temp worktrees, and leave exact remediation instead
  of appearing to run forever.

- Detected By: Maintainer release prep while returning from detached
  `source-local` to pinned dogfood for canonical `v0.1.10` proof.

- Failure Signature: `in-progress.v1.json` stays on `running` and
  `executing_scenarios` for the same scenario, the outer benchmark runner
  process remains alive, and no new `latest.v1.json` is written.

- Trigger Path: `./.odylith/bin/odylith benchmark --repo-root . --profile proof`

- Ownership: Benchmark runner lifecycle, live proof orchestration,
  release-proof benchmark contract.

- Timeline: Observed on 2026-04-08 during `v0.1.10` release prep after the
  product repo was returned to pinned dogfood posture. The release owner chose
  a tracked one-release benchmark override for `v0.1.10` rather than hold the
  release on benchmark runner tuning in the same cut.

- Blast Radius: Benchmark proof trust, release preflight readiness, benchmark
  publication cadence, and maintainer confidence in the pinned-dogfood proof
  lane.

- SLO/SLA Impact: No customer outage, but direct release-blocker behavior in a
  P0 maintainer lane.

- Data Risk: Low product-data risk, high release-proof risk because the lane
  can appear active without producing a usable audited report.

- Security/Compliance: None directly.

- Invariant Violated: The release-safe benchmark lane must either complete and
  persist a release-safe proof report or fail clearly within bounded time. It
  must not hang mid-corpus while still looking active.

- Workaround: For `v0.1.10` only, use the tracked maintainer override in
  `odylith/runtime/source/release-maintainer-overrides.v1.json`, stop the
  in-flight proof run, and continue release prep without claiming benchmark
  re-proof. This is an explicit exception, not a new normal.

- Rollback/Forward Fix: Forward fix.

- Agent Guardrails: Do not treat a version-scoped benchmark override as
  equivalent to a completed proof rerun, and do not leave a live wedged
  benchmark process running once the override decision is made.

- Preflight Checks: Inspect
  [odylith_benchmark_runner.py](../../../src/odylith/runtime/evaluation/odylith_benchmark_runner.py),
  [odylith_benchmark_live_execution.py](../../../src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py),
  `.odylith/runtime/odylith-benchmarks/in-progress.v1.json`, and active
  benchmark-owned processes before changing proof-run lifecycle behavior.

- Regression Tests Added: None in this release slice. `v0.1.10` records the
  override and moves the runner fix to the next release instead of claiming the
  benchmark wedge is solved.

- Monitoring Updates: Track any `proof` run that keeps a live benchmark-owned
  process after progress stops, and fail the next release if pinned-dogfood
  proof still depends on a maintainer override.

- Residual Risk: High until the next release restores a reliable full
  pinned-dogfood proof run and records a fresh release-safe benchmark report.

- Related Incidents/Bugs:
  [2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md](2026-04-02-benchmark-warm-cold-proof-instability-flips-narrow-slice-winners.md)
  [2026-04-03-benchmark-repair-style-live-cases-penalize-validator-backed-no-op-completion.md](2026-04-03-benchmark-repair-style-live-cases-penalize-validator-backed-no-op-completion.md)

- Version/Build: pinned dogfood `0.1.9` proving the `v0.1.10` release lane on
  2026-04-08.

- Config/Flags: `./.odylith/bin/odylith benchmark --repo-root . --profile proof`

- Customer Comms: Tell maintainers the `v0.1.10` release is using a tracked
  benchmark override because the full pinned-dogfood proof runner wedged
  mid-corpus; do not describe this release as benchmark re-proved.

- Code References:
  `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `odylith/runtime/source/release-maintainer-overrides.v1.json`

- Runbook References:
  `odylith/MAINTAINER_RELEASE_RUNBOOK.md`,
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`,
  `odylith/registry/source/components/benchmark/CURRENT_SPEC.md`,
  `odylith/registry/source/components/release/CURRENT_SPEC.md`

- Fix Commit/PR: Pending next-release benchmark runner reliability slice.
