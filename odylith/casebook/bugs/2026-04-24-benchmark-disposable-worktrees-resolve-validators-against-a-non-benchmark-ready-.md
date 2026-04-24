- Bug ID: CB-124

- Status: Open

- Created: 2026-04-24

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Disposable proof worktrees were resolving validator and CLI proof commands against repo-root .venv/bin even when that interpreter surface was not benchmark-ready. In this repo the worktree-local .venv pointed at a bare Homebrew Python without pytest or httpx, so clean proof reruns produced harness failures instead of product truth and forced false live holds.

- Impact: Live proof can fail or hold for harness reasons, forcing fake write-surface regressions and explicit-workstream misses instead of measuring Odylith quality honestly.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer mode, detached source-local, disposable proof worktrees during full and targeted live benchmark reruns.

- Detected By: Full proof rerun recovery on 2026-04-23 after shard merge, plus targeted live reruns for benchmark progress, explicit workstream, and cross-file feature slices.

- Failure Signature: Disposable worktree validators fail with .venv/bin/pytest missing or ModuleNotFoundError: No module named httpx before exercising the bounded slice, and the report then records false hold pressure instead of benchmark-ready proof.

- Trigger Path: odylith benchmark --repo-root . --profile proof through sandbox PATH setup and sandbox validation command rewriting in disposable worktrees.

- Ownership: Benchmark isolation and live validator execution contract.

- Timeline: Captured 2026-04-24 through `odylith bug capture`.

- Blast Radius: README benchmark trust, release-proof decisions, write-surface precision, explicit-workstream expectation coverage, and weak-family diagnosis across the benchmark component.

- SLO/SLA Impact: Release proof can stay on hold for harness reasons and maintainers can waste hours chasing fake regressions.

- Data Risk: Low direct data risk, high benchmark-integrity risk.

- Security/Compliance: No direct security impact; local toolchain and packaging isolation bug inside benchmark execution.

- Invariant Violated: Disposable benchmark workspaces must execute validators and CLI proof on the same benchmark-ready Python toolchain the benchmark runner used, not on an empty or dependency-incomplete repo-local .venv.

- Root Cause: The benchmark sandbox trusted repo_root/.venv/bin unconditionally for PATH prepending and validation command rewriting. In clean disposable worktrees that .venv was only a thin interpreter link and did not carry the benchmark runner's Python package surface.

- Solution: Resolve a benchmark tool bin from a readiness check instead of from path shape alone, prepend that tool bin into sandbox PATH, and rewrite validator or CLI proof commands to that resolved toolchain. Keep repo-local .venv/bin only when it proves benchmark-ready imports such as pytest and httpx.

- Verification: Targeted unit proof now passes for benchmark_tool_bin, sandbox_process_env, and sandbox_validation_command coverage; the broad benchmark unit suite passes 481 tests; the full merged proof rerun completes instead of failing on the toolchain gap.

- Prevention: Treat benchmark toolchain selection as part of the isolation contract. Snapshot or PATH logic is incomplete unless the selected Python surface proves the validator dependency floor before live proof starts.

- Agent Guardrails: Do not narrate benchmark holds as product regressions until disposable-worktree validator failures are checked for missing toolchain readiness. Isolation fixes must prove both PATH selection and command rewrite behavior.

- Preflight Checks: Inspect CB-027, CB-043, CB-044, benchmark live execution, benchmark isolation, and the disposable proof rerun artifacts before changing the harness again.

- Regression Tests Added: tests/unit/runtime/test_odylith_benchmark_isolation.py and tests/unit/runtime/test_odylith_benchmark_live_execution.py now cover benchmark tool-bin readiness fallback and validation-command rewriting to the resolved toolchain.

- Monitoring Updates: Proof rerun diagnostics now have an explicit benchmark_tool_bin readiness owner in the code path that feeds sandbox PATH and validator command rewriting.

- Version/Build: v0.1.11 benchmark hardening on 2026-04-23 after merged proof report 2d8444952aef28d2 and diagnostic report dd35a4aab061f49f.

- Config/Flags: odylith benchmark --repo-root . --profile proof; disposable benchmark worktrees; sandbox validator command rewriting.

- Customer Comms: Public benchmark claims should stay conservative until the remaining live proof hold is resolved on a completed clean rerun.

- Related Incidents/Bugs: CB-027, CB-043, CB-044, CB-048

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_isolation.py
- src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py
- tests/unit/runtime/test_odylith_benchmark_isolation.py
- tests/unit/runtime/test_odylith_benchmark_live_execution.py

- Runbook References: - odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md
