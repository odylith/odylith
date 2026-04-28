- Bug ID: CB-126

- Status: Closed

- Created: 2026-04-25

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: The first publication-identity fix placed new tree identity logic in the already pressure-sensitive benchmark runner, pushing the runtime hotfile inventory gate back into failure during live proof shards.

- Impact: Real odylith_on proof rows failed in the README closeout and mirror-integrity shards, so the run correctly stopped for a product regression instead of treating the failures as infrastructure noise.

- Components Affected: benchmark

- Environment(s): Odylith product repo maintainer mode on branch 2026/freedom/v0.1.11, clean-head proof rerun on commit 2586dc71.

- Detected By: 12-shard proof rerun with capped four-way waves and focused hotfile validation after the first publication-identity fix.

- Failure Signature: Shard 1 benchmark-docs-and-readme-closeout and shard 12 benchmark-corpus-expansion-mirror-integrity reported odylith_on expectation failures from test_runtime_hotfile_inventory_stays_explicit_and_non_expanding.

- Trigger Path: odylith benchmark --repo-root . --profile proof --shard-count 12 --shard-index 1 and 12 after commit 2586dc71.

- Ownership: Benchmark runner source-size and anti-slop enforcement contract.

- Timeline: Captured on 2026-04-25 after the regression was fixed and affected proof shards 1, 5, 8, and 12 were rerun cleanly.

- Blast Radius: Proof publication, README benchmark closeout, benchmark corpus mirror integrity, and the runtime hotfile guardrail for the benchmark component.

- SLO/SLA Impact: Release proof was held until the benchmark runner dropped back under the hotfile limit and affected shards were rerun.

- Data Risk: Low product data risk, moderate benchmark-maintainability and proof-integrity risk.

- Security/Compliance: No direct security or compliance impact.

- Invariant Violated: Fixes for benchmark publication must not grow the oversized benchmark runner or bypass the source-file size discipline that protects proof-critical hot paths.

- Root Cause: Tree identity filtering was implemented directly in odylith_benchmark_runner.py instead of a focused helper module, so a valid publication fix still violated the anti-slop hotfile contract.

- Solution: Move tree identity filtering and current-tree report matching into src/odylith/runtime/evaluation/odylith_benchmark_tree_identity.py and have the runner, shard merge, publication, and compare paths call that focused owner directly.

- Rollback/Forward Fix: Forward fix only; reverting would reopen CB-125 publication identity failures.

- Verification: Focused hotfile and tree-identity tests passed with 9 passed; affected shard retries on head 1cfca107 passed with zero odylith_on failures; final merged proof report 44f2a3d83d2c9975 has 164 odylith_on rows and zero row failures. The 0.1.12 cleanup pass then moved the remaining tree-identity contract out of the runner, reduced odylith_benchmark_runner.py from 8561 to 8429 LOC, and passed 355 focused benchmark, shard-merge, publication, compare, prompt-payload, corpus, and hygiene tests.

- Prevention: When fixing benchmark publication logic, keep helper ownership outside the runner unless the change is truly runner control flow, and run the hotfile inventory test before rerunning proof.

- Agent Guardrails: Do not call a benchmark fix complete if it clears publication but regrows a red-zone runner or fails the hotfile proof gate.

- Preflight Checks: Run tests/unit/runtime/test_hygiene.py::test_runtime_hotfile_inventory_stays_explicit_and_non_expanding with the tree-identity and publication tests before launching proof shards.

- Regression Tests Added: tests/unit/runtime/test_odylith_benchmark_tree_identity.py plus the existing runtime hotfile inventory test covered the extraction boundary; benchmark publication, compare, shard merge, and runner tests now import the tree-identity owner instead of monkeypatching runner-local identity helpers.

- Monitoring Updates: Final proof notes preserve the shard 1 and shard 12 hotfile failures as real product regressions, distinct from infra-only shard retries.

- Version/Build: v0.1.11 benchmark publication hardening on commits 2586dc71 and 1cfca107.

- Config/Flags: proof shards capped to four parallel workers; affected shards rerun single-threaded after fix.

- Customer Comms: No public benchmark report should cite commit 2586dc71 as final proof because that head still had real hotfile row failures.

- Related Incidents/Bugs: CB-125

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_runner.py
- src/odylith/runtime/evaluation/odylith_benchmark_tree_identity.py
- tests/unit/runtime/test_hygiene.py
- tests/unit/runtime/test_odylith_benchmark_tree_identity.py

- Runbook References: - odylith/agents-guidelines/ANTI_SLOP_AND_DECOMPOSITION.md

- Fix Commit/PR: 1cfca107 on branch 2026/freedom/v0.1.11; 0.1.12 owner-completion cleanup on branch 2026/freedom/v0.1.12.
