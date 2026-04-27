- Bug ID: CB-119

- Status: Open

- Created: 2026-04-16

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Benchmark live proof conflates support paths, write targets, and read-only sandbox policy

- Impact: The 0.1.11 proof lane goes to hold for harness-induced quality failures, so benchmark publication cannot distinguish real Odylith regressions from stale scenario contracts or sandbox artifacts.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer source-local benchmark proof on branch 2026/freedom/v0.1.11 at commit 089758a654ba3d5c12a53104cce0d51490420108.

- Detected By: Detached eight-shard benchmark proof recovery run and manual shard report inspection.

- Failure Signature: Hard gates reported grounding precision, observed-surface drift, unnecessary write-surface widening, write-surface precision, and execution-fit regressions while shard rows showed legitimate support-cone paths counted as hallucinations, changed_paths reused as expected write targets, read-only analysis sandboxes blocking runtime temp usage, and Atlas check-only validators failing on stale chatter module paths.

- Trigger Path: PYTHONPATH=src .venv/bin/python -c 'from odylith.runtime.evaluation import odylith_benchmark_runner as runner; runner.run_benchmarks(repo_root=Path("."), benchmark_profile="proof", shard_count=8, shard_index=N)'

- Ownership: Benchmark harness, benchmark corpus contract, live execution sandbox policy, and benchmark-facing Atlas validation truth.

- Timeline: 2026-04-16: current detached proof produced hold shards 562df3c8face810e, 412d141d0a92690a, 092da5afcd303119, and 3189741f37f1889b; remaining shards were stopped after the run was already non-publishable.

- Blast Radius: Benchmark proof/profile publication, B-092/B-093 release gates, live odylith_on vs odylith_off quality interpretation, Atlas-backed validation scenarios, and current-head benchmark docs/graphs.

- SLO/SLA Impact: Blocks 0.1.11 benchmark proof closeout and can waste hours of live proof time on non-publishable runs.

- Data Risk: Low direct data risk; benchmark reports and generated docs can carry misleading quality conclusions if stale proof is published.

- Security/Compliance: Low direct security risk, but false benchmark publication weakens release governance and auditability.

- Invariant Violated: The live benchmark must measure current-source product quality, not stale scenario write targets, undeclared support-path scoring artifacts, or artificial sandbox constraints; Atlas validation paths must resolve before proof scenarios can claim validator-backed status.

- Root Cause: The harness only has required_paths and changed_paths, so legitimate supporting evidence is scored as hallucination and changed_paths doubles as expected write surface. The live runner also uses read-only sandbox for no-write scenarios even when Odylith analysis commands need temporary runtime state. Separately, Atlas catalog truth still references removed odylith_chatter runtime modules.

- Solution: Add first-class supporting_paths and expected_write_paths semantics, score precision against required plus supporting paths while keeping recall strict on required paths, default live sandboxes to workspace-write while scoring unexpected writes, and repair stale Atlas chatter paths.

- Rollback/Forward Fix: Forward fix only; do not weaken benchmark hard gates or publish stale reports.

- Verification: Verify with focused benchmark runner/live execution tests, corpus tests, Atlas check-only render, and a fresh current-head proof rerun.

- Prevention: Corpus scenarios must distinguish required, supporting, and expected-write surfaces; live sandboxes must not be stricter than real agent workspace semantics; Atlas path existence must remain part of benchmark validators.

- Agent Guardrails: Do not call benchmark hold publishable until shard reports and current-tree proof agree; capture concrete bug evidence before adjusting corpus expectations.

- Preflight Checks: Inspect shard hard_gate_failure_labels, per-scenario observed_paths, candidate_write_paths, validator_status_basis, and Atlas path-existence errors before editing benchmark expectations.

- Monitoring Updates: Benchmark publication should continue surfacing hard_gate_failure_labels, weak_families, current_tree_identity_match, and fairness_findings.

- Version/Build: 0.1.11 benchmark closeout

- Config/Flags: benchmark_profile=proof, shard_count=8, full_product_assistance_vs_raw_agent

- Customer Comms: No external customer communication until a current-head proof is regenerated and publication artifacts match it.

- Related Incidents/Bugs: Related to CB-113, CB-116, CB-117, CB-118 and prior benchmark precision bugs from 2026-04-01/2026-04-02.

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_runner.py
- src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py
- odylith/runtime/source/optimization-evaluation-corpus.v1.json
- odylith/atlas/source/catalog/diagrams.v1.json
