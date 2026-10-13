- Bug ID: CB-361

- Status: Open

- Created: 2026-10-13

- Severity: P2

- Reproducibility: High

- Type: Tooling

- Description: Full live proof at f2218311e spent more than 21 minutes in pre-native instruction discovery. Both matched workers were observed traversing retained Greenfield generation repositories under .odylith/runtime. The original attempt was interrupted and remains incomplete and unqualified.

- Impact: Required release proof spends unbounded preparation time traversing runtime history before the native task timeout or reported task timing begins.

- Components Affected: benchmark

- Environment(s): Product maintainer detached source-local; version 0.1.15; full proof profile with retained runtime generations.

- Detected By: Live process observation, one-second native stack sample, and scoped source review.

- Failure Signature: Two workers in os.scandir/os.lstat while workspace_strip_paths executes six root.rglob walks; directory descriptors inside .odylith/runtime/greenfield/generations.

- Trigger Path: odylith benchmark --repo-root . --profile proof

- Ownership: Benchmark isolation instruction inventory.

- Timeline: Captured 2026-10-13 through `odylith bug capture`.

- Blast Radius: Both live lanes, every scenario and selected cache profile on repositories with retained runtime state.

- SLO/SLA Impact: Release proof setup is outside the native timeout and task timing, delaying qualification.

- Data Risk: Traversal was observed; no retained data deletion, copying, or mutation was established. Preserve all publication and recovery data.

- Security/Compliance: No security breach observed. This is a maintainer benchmark scope and availability defect; guidance isolation must remain equally enforced for both lanes.

- Invariant Violated: Instruction discovery must follow replayed source and selected runtime scope, without descending unrelated retained runtime repositories.

- Root Cause: workspace_strip_paths performs six unpruned rglob searches on the live source root before disposable workspace creation and native execution.

- Solution: Use one source traversal with runtime and Git metadata pruned before descent; inspect only replayed runtime bin and explicitly selected runtime directories. Preserve nested instruction removal and exact task anchors.

- Rollback/Forward Fix: Forward fix. Preserve interrupted attempt and diagnostic hold. No quality-floor or corpus changes.

- Verification: Structural tests reject entry into retained generations, cover nested guidance and explicit runtime snapshots, then measure the corrected inventory on the original repository and run unchanged full proof.

- Version/Build: 0.1.15; source f2218311e3594e1d9804062b44d678864172cbab

- Related Incidents/Bugs: CB-027, CB-043, CB-116

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_isolation.py
- src/odylith/runtime/evaluation/odylith_benchmark_live_execution.py

## Implementation and verification

Instruction discovery now walks source once, pruning root Git metadata and
mutable runtime state before descent. It separately inspects the replayed
runtime launcher directory and explicitly selected runtime directories. Nested
guidance removal, exact preserved anchors, and matched-lane ordering remain intact.

The structural regression reproduced two failures on the original owner and
passes after correction. The complete isolation module passed 13 tests; the
existing live-execution and live-diagnostics modules passed 128 tests. Independent
review found no P0, P1, or P2 regression in the two-file change.

The corrected inventory completed in 0.188 seconds on the original repository,
visiting 2,146 source directories and finding 69 instruction paths without
descending retained generations. This measures inventory only. The interrupted
full proof remains incomplete and unqualified; a fresh full proof and release
qualification are still required. Original logs, the process sample, and the
measurement are retained under
`/private/tmp/odylith-v52-canonical-preparation-20261012/` and durable release evidence.
