- Bug ID: CB-030

- Status: Closed

- Created: 2026-04-01

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: The benchmark sandbox strip policy removed entire repo
  subtrees such as `odylith/maintainer/` and `odylith/skills/` from disposable
  workspaces, which deleted truth-bearing docs that Odylith had legitimately
  selected for the live evidence cone.

- Impact: The strict benchmark sandbox could tell `odylith_on` to read a
  required benchmark doc like
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md` even though the
  sandbox had already deleted that file. This corrupted both fairness and
  measured accuracy because Odylith was being blamed for missing repo truth the
  harness had made unreachable.

- Components Affected: `src/odylith/runtime/evaluation/odylith_benchmark_isolation.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  sandbox strip policy, benchmark trust boundary, benchmark doc availability in
  disposable worktrees.

- Environment(s): Odylith product repo maintainer mode, detached
  `source-local`, live Codex CLI benchmark runs in disposable worktrees.

- Root Cause: The strip policy used recursive directory-name matching for
  `maintainer`, `skills`, and `agents-guidelines`, instead of limiting removal
  to actual auto-consumed instruction entrypoints like `AGENTS.md`,
  `CLAUDE.md`, `.cursor/`, `.windsurf/`, or `.codex/`. That broadened the
  sandbox from “remove ambient instructions” into “delete repo truth”.

- Solution: Strip only instruction entrypoints and tool config surfaces that
  can auto-contaminate the raw Codex lane. Keep truth-bearing repo docs,
  maintainer guidance markdown, and product `SKILL.md` files readable inside
  the disposable workspace when the agent explicitly opens them.

- Verification: Added regression coverage proving that
  `workspace_strip_paths(...)` still removes root and nested `AGENTS.md`
  instruction files plus root IDE config directories, while preserving
  `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md` and
  `odylith/skills/.../SKILL.md`. Focused benchmark suites pass.

- Prevention: Benchmark isolation must distinguish “auto-consumed instruction
  surface” from “repo truth surface”. A sandbox that deletes truth-bearing
  paths is invalid, even if it is stricter.

- Detected By: Manual inspection of the disposable worktree during a live
  strict rerun on 2026-04-01 showed the benchmark-selected maintainer doc and
  multiple repo truth surfaces missing from the workspace.

- Failure Signature: `git diff --stat` inside the disposable worktree shows
  deleted `odylith/maintainer/`, `odylith/skills/`, or
  `odylith/agents-guidelines/` content even though those paths are normal repo
  documents rather than auto-consumed benchmark instructions.

- Trigger Path: Live benchmark worktree provisioning and strip pass inside
  `_temporary_worktree(...)`.

- Ownership: Benchmark isolation policy and disposable workspace truth
  preservation.

- Timeline: The sandbox hardening wave correctly tightened ambient-state
  isolation, then overreached and deleted truth-bearing maintainer docs. The
  bug was discovered and fixed the same day during the next live rerun.

- Blast Radius: Live required-path recall, live prompt usability, benchmark
  fairness, and any conclusion drawn from `odylith_on` underperformance on
  governance-heavy tasks.

- SLO/SLA Impact: Benchmark credibility degrades immediately because a stricter
  sandbox can become less truthful than raw Codex instead of more fair.

- Data Risk: Low direct data risk, high evaluation-integrity risk.

- Security/Compliance: This is a trust-boundary design bug, not a security
  exploit.

- Invariant Violated: Benchmark isolation may remove auto-injected instruction
  surfaces, but it may not delete repo truth that the task could honestly need
  to inspect.

- Workaround: None acceptable for benchmark publication. Manual worktree
  inspection can detect the bug after the fact only.

- Rollback/Forward Fix: Forward fix only.

- Agent Guardrails: Never equate “more stripped” with “more fair” unless the
  sandbox still preserves all truth-bearing repo surfaces the task could
  legitimately inspect.

- Preflight Checks: Inspect `workspace_strip_paths(...)`, the benchmark
  component spec, and a disposable worktree diff before tightening strip rules.

- Regression Tests Added: `test_workspace_strip_paths_keeps_truth_bearing_repo_docs`.

- Monitoring Updates: Disposable worktree inspection during benchmark triage now
  treats deleted maintainer or skill docs as a benchmark invalidation signal.

- Residual Risk: The sandbox is now materially fairer, but future auto-strip
  expansions still need explicit review against required-path truth surfaces.

- Related Incidents/Bugs:
  `2026-04-01-benchmark-live-runner-inherits-ambient-user-state-and-breaks-raw-codex-isolation.md`

- Version/Build: `v0.1.7` benchmark integrity hardening wave on 2026-04-01.

- Config/Flags: `odylith benchmark --repo-root .`,
  `ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS`,
  `ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS`.

- Customer Comms: Benchmark claims must not use runs launched under a sandbox
  that deleted truth-bearing repo content.

- Code References: `src/odylith/runtime/evaluation/odylith_benchmark_isolation.py`,
  `src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py`,
  `tests/unit/runtime/test_odylith_benchmark_live_execution.py`

- Runbook References: `odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md`

- Fix Commit/PR: Pending.
