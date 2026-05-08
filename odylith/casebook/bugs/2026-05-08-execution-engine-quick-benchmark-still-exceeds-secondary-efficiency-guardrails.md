- Bug ID: CB-189

- Status: Open

- Created: 2026-05-08

- Severity: P2

- Reproducibility: Consistent

- Type: Tooling

- Description: After the execution_engine quick benchmark was rerouted away from the live raw-host baseline, the run now completes locally and clears the hard quality gate, but report c816bd2493538b2e still returns status=hold because secondary latency and token guardrails fail.

- Impact: Operators cannot honestly claim the execution-engine activation path is fully low-latency or token-optimal; the benchmark must stay published as a quality pass with an efficiency hold.

- Components Affected: benchmark

- Environment(s): Product repo source-local on 2026/freedom/v0.1.15, PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family execution_engine --no-write-report --json

- Detected By: Benchmark rerun during engine-integrity hardening

- Failure Signature: report_id=c816bd2493538b2e status=hold hard_quality_gate_cleared=true secondary_guardrails_cleared=false latency_delta_ms=40.072 prompt_token_delta=911 total_payload_token_delta=1363

- Trigger Path: odylith benchmark --repo-root . --profile quick --family execution_engine --no-write-report --json

- Ownership: Benchmark and Execution Engine packet-efficiency contract

- Timeline: 2026-05-08: route bug fixed so execution_engine quick no longer hangs on live raw-host baseline; same-day rerun c816bd2493538b2e exposed remaining +40 ms median latency and +911/+1363 token overhead.

- Blast Radius: Execution-engine quick benchmark, public low-latency claims, and future activation-performance proof

- SLO/SLA Impact: No runtime outage, but blocks a clean low-latency proof for the execution-engine quick lane.

- Data Risk: No customer data risk; benchmark payloads are local repo-governance artifacts.

- Security/Compliance: No direct security exposure; the risk is claim accuracy and proof-governance integrity.

- Invariant Violated: Engine activation claims must not hide secondary latency or token-efficiency guardrail failures behind a hard-quality pass.

- Workaround: Treat the current result as hard-quality green with efficiency hold; do not publish it as a clean low-latency pass.

- Root Cause: The immediate live-host routing bug is fixed, but the source-local packet still carries more selected docs, commands, and runtime contract payload than the raw baseline.

- Solution: Compact the execution_engine quick packet for local-only scenarios, reduce unnecessary selected-command/doc payload, and re-run the quick benchmark until secondary guardrails clear without weakening acceptance logic.

- Rollback/Forward Fix: Forward-fix only; do not relax benchmark guardrails to manufacture a pass.

- Verification: PYTHONPATH=src python -m odylith.cli benchmark --repo-root . --profile quick --family execution_engine --no-write-report --json must return status=provisional_pass with hard_quality_gate_cleared=true and secondary_guardrails_cleared=true.

- Prevention: Keep CB-188's local-only routing test and add packet-size regression coverage for execution_engine quick scenarios before closing this bug.

- Agent Guardrails: Agents must report the hard-quality pass and the efficiency hold separately; no final answer should call execution_engine fully low-latency while this bug is open.

- Preflight Checks: Run engine-integrity validation, execution_engine quick benchmark, and inspect published_summary secondary_guardrail_failures before release claims.

- Regression Tests Added: Not yet; this bug records the remaining post-route efficiency debt after the current hardening pass.

- Monitoring Updates: Benchmark published_summary already exposes latency_delta_ms, prompt_token_delta, total_payload_token_delta, and secondary_guardrail_failures.

- Version/Build: 0.1.15 source-local hardening branch

- Config/Flags: PYTHONPATH=src; --profile quick; --family execution_engine; --no-write-report

- Related Incidents/Bugs: CB-188

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_runner.py
- tests/unit/runtime/test_odylith_benchmark_execution_engine.py
