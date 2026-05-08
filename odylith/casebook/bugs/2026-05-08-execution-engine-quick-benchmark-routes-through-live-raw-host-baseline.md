- Bug ID: CB-188

- Status: Open

- Created: 2026-05-08

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Execution Engine quick benchmark routes through live raw-host baseline

- Impact: Operators running engine-integrity or quick Execution Engine proof can wait on a live raw-host CLI baseline instead of getting a cheap local packet/handshake result.

- Components Affected: benchmark

- Environment(s): Odylith product repo source-local maintainer lane on 2026-05-08, branch 2026/freedom/v0.1.15.

- Detected By: Manual engine-integrity hardening pass for Context Engine, Execution Engine, benchmark, and low-latency UX.

- Failure Signature: odylith benchmark --profile quick --family execution_engine --limit 1 --mode odylith_off produced no output for more than 30 seconds and required killing the benchmark process; the full quick pair also appeared stuck before the raw baseline was killed.

- Trigger Path: odylith benchmark --repo-root . --profile quick --family execution_engine --limit 1 --no-write-report

- Ownership: Benchmark Harness quick-profile family routing and Execution Engine benchmark family contract.

- Timeline: Captured 2026-05-08 through `odylith bug capture`.

- Blast Radius: Maintainer engine-integrity proof, release hardening, low-latency diagnostics, and any operator who narrows the quick benchmark to execution_engine.

- SLO/SLA Impact: Quick benchmark latency violated the developer-lane expectation; the command could block an integrity pass even when local packet proof was sufficient.

- Data Risk: No data loss; runtime temp worktrees and benchmark processes can be left behind if operators interrupt the stuck lane.

- Security/Compliance: No credential exposure observed; the risk is operational proof reliability and avoiding unnecessary host-model execution in a local integrity check.

- Invariant Violated: Quick engine-family diagnostics must stay local, low-latency, and dependency-light unless the operator explicitly asks for publication-grade live proof.

- Solution: Added execution_engine to the local-only quick benchmark family set so quick family checks use the packet/handshake diagnostic lane instead of live raw-host execution.

- Rollback/Forward Fix: Forward fix only; proof-profile live comparison remains available for publication-grade evidence.

- Verification: Run the focused benchmark routing test and run odylith benchmark --profile quick --family execution_engine --no-write-report; hard quality gate should clear without invoking the live raw-host baseline.

- Prevention: Keep engine-integrity smoke proof on validate engine-integrity and local-only quick benchmark families; use proof profile for live host baseline publication only.

- Regression Tests Added: tests/unit/runtime/test_odylith_benchmark_execution_engine.py::test_execution_engine_quick_family_uses_local_packet_lane

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_runner.py
- tests/unit/runtime/test_odylith_benchmark_execution_engine.py
