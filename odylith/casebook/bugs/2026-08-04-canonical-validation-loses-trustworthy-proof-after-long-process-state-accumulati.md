- Bug ID: CB-308

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: High

- Type: Test

- Description: The canonical maintainer validation runs all 6,218 pytest nodes in one Python interpreter. A durable run reached 40 percent, emitted three failures that passed immediately in fresh-process replay, then terminated with SIGBUS during garbage collection while compiling a Greenfield regex. The gate therefore cannot distinguish product regressions from order contamination or preserve complete release evidence after an interpreter crash.

- Impact: Maintainers cannot obtain a trustworthy complete release verdict; repeated multi-hour runs can lose accumulated proof and delay Greenfield quality convergence.

- Components Affected: odylith

- Environment(s): macOS arm64; Python 3.13.12; source-local maintainer posture; ODYLITH_NO_BROWSER=1 make dev-validate

- Detected By: Durable validation log and exit-status capture followed by exact frozen-node fresh-process replay

- Failure Signature: At approximately node 2,520 and 40 percent, three tests emitted F markers; the process then exited with Bus error 10 in greenfield_sequence_steps.py while garbage collecting and compiling a regex; make returned Error 138. The exact three tests, the containing 46-test window, and the crash-site module all passed in fresh processes.

- Trigger Path: ODYLITH_NO_BROWSER=1 make dev-validate

- Ownership: Canonical maintainer pytest execution boundary in bin/validate

- Timeline: A clean pushed checkpoint was validated in one durable foreground process. The run reached 40 percent, showed three failures, and terminated with SIGBUS. Frozen-node mapping identified the failing window. Fresh-process replays passed 4 of 4 body-composition tests, the exact 3 marked failures, and all 46 nodes in the affected window.

- Blast Radius: Every maintainer and release lane relying on the full canonical validation gate

- SLO/SLA Impact: Blocks deterministic release proof and consumes hours per inconclusive retry

- Data Risk: No governed data loss or write corruption observed; the risk is lost validation evidence and repeated execution cost.

- Security/Compliance: Security posture: no security exposure or compliance breach was observed; release policy still requires an auditable fail-closed validation result, which a crashed monolithic process cannot provide.

- Invariant Violated: One test process must not allow accumulated global or runtime state, or one interpreter crash, to invalidate all prior proof or create order-dependent verdicts.

- Workaround: Run the suite in bounded fresh-process batches and aggregate every batch result.

- Root Cause: bin/validate invokes the entire pytest corpus in one interpreter and has no process-isolation or result-aggregation boundary. Long-lived process state and a native interpreter crash can contaminate later tests and erase the canonical verdict.

- Solution: Collect deterministic pytest node IDs, execute bounded shards in fresh Python subprocesses, continue through all shards, and return one aggregate nonzero result if any shard fails or crashes.

- Rollback/Forward Fix: Forward fix the validation harness; do not weaken, skip, or quarantine product tests.

- Verification: Six shard-runner contract tests passed. A real two-process smoke run passed three selected nodes, including the prior Greenfield crash-site test. The Registry and Atlas governance regression batch passed 61 tests in 263.14 seconds. Final closure still requires a complete `make dev-validate` run with durable log and status.

- Prevention: Keep full-suite execution process-isolated and make shard boundaries and failures explicit in canonical output.

- Agent Guardrails: Do not classify long-process-only failures as product defects until exact-node fresh-process replay is compared. Do not accept fresh replay alone as release proof; repair and rerun the canonical gate.

- Preflight Checks: Confirm working tree scope, preserve ODYLITH_NO_BROWSER, verify deterministic collection count, and retain exact failing node IDs.

- Regression Tests Added: `tests/unit/test_pytest_shards.py` covers collection parsing, stable contiguous sharding, invalid-size rejection, continuation after a signaled shard, collection failure reporting, and canonical `bin/validate` wiring.

- Monitoring Updates: Canonical output will report shard index, node count, exit code, and aggregate failed shards.

- Version/Build: 0.1.15 development checkpoint e92e4a5ea

- Config/Flags: ODYLITH_NO_BROWSER=1

- Customer Comms: Internal maintainer validation defect; no consumer-facing data failure observed.

- Related Incidents/Bugs: CB-209 documented a prior installed-matrix SIGBUS and required stronger subprocess isolation and incremental proof persistence.

- Code References: - bin/validate
- scripts/run_pytest_shards.py
- tests/unit/test_pytest_shards.py
- tests/unit/runtime/test_greenfield_confirmed_body_comp.py
