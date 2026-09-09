- Bug ID: CB-119

- Frozen Checkpoint Verification (2026-09-09): The isolated packet contracts, live semantic controls and mirrored support declarations pass the final frozen runtime gate: 5,002 passed, no failures. Install has 1,168 passes and browser has 340 passes with one fixture skip. All 3,191 selected proof inputs remain unchanged. The old ambient exact assertions are removed without changing their controlled codec expectations; broader live benchmark and release claims remain separate.

- Independent Current-slice Review (2026-09-09): Bounded review accepts the six isolated contracts, five live semantic cases and three source-grounded support additions, with no actionable finding and 16 targeted passes in 8.68 seconds. The reviewer guide allowance is the existing finalizer-owned delivery companion, not a blanket support exemption. Canonical sync mirrors the corpus and all 30 corpus/publication controls then pass in 18.11 seconds. Required recall, write authority and undeclared-path rejection remain unchanged. Full runtime/install/browser proof is still outstanding.

- Controlled Packet Proof (2026-09-09): Six exact packet contracts now use explicit uncompressed inputs, preserving B-002, c4d6g3, fallback/narrowing semantics and the two-edge/one-traceability-edge output. Five separate live-repository cases retain exact-code ownership, shared-runbook narrowing, bounded source-backed support and current graph-count preservation. The old module loses 183 lines and the new owner has 321 lines. The six original cases fail before correction; 19 focused controls pass in 14.66 seconds afterward, including the untouched runtime-warmup regression. Independent review, canonical corpus mirroring and the full frozen gate remain outstanding; no assertion is changed to the latest repository winner or ambient count.

- Current Support And Fixture Audit (2026-09-09): Nine context/benchmark controls reproduce after valid active-plan traceability updates. CB-336 separately owns the genuine shared-support ownership defect. Two corpus support declarations are stale: Compass queued/failed refresh directly depends on its component spec and PRODUCT_SURFACES_AND_RUNTIME.md, while benchmark publication directly depends on FAMILIES_AND_EVALS.md. Declare those reviewed supporting paths without changing required recall, write scope or undeclared-path rejection. Other exact compaction/fallback tests inherit old maintainer-repo candidates and graph counts; preserve their assertions with controlled ambiguous, empty and codec input, alongside current-repo semantic checks. Exact Compass and benchmark code references now legitimately resolve owners and must not be suppressed to recreate old ambiguity. CB-072 supplies the prior ambient-input isolation lesson. These are ordinary context benchmark contracts, not the protected Greenfield final holdout or its frozen evaluation splits.

- Type: Product








- Status: Open

- Created: 2026-04-16

- Severity: P1

- Reproducibility: High


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
