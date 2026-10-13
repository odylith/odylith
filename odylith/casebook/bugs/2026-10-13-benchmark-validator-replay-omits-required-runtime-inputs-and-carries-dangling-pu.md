- Bug ID: CB-362

- Status: Open

- Prerequisite Proof (2026-10-13): Existing clean-checkout graph and sync commands pass; the unchanged publication suite has eight passes, complete browser module has 37 passes, and eight replay/tree-identity controls pass. A real dependency-owner control selects the same 693 paths for both lanes and copies exact retained HOLD hash 1fc2fcab7ca4b9ef1ee14f2cea6aedc4ae5ca9633c743682047d106d6d665e40. Initial mode 0444 caused the existing second-copy provision to fail in both lanes; only the proof-local seed mode changed to 0644, preserving bytes and the retained original. No source, corpus, scores, floors, budgets or validators changed. Fresh full proof remains required. Evidence: durable readback-verified archive 3be-cb362-validator-prerequisites.tar.gz, SHA-256 d47a1a6650433c021f9508123e56803adda5140da477860d5c4ee4a8710debbe.

- Created: 2026-10-13

- Severity: P1

- Reproducibility: High

- Type: Tooling

- Description: Benchmark validator replay omits required runtime inputs and carries dangling publication entry

- Impact: Full release proof reports a write-precision HOLD when disposable validators fail on missing report and generation inputs; all seven failed On observations wrote no files.

- Components Affected: benchmark

- Environment(s): Detached source-local v0.1.15 checkpoint 3be2011c7; full warm/cold 82-case report 737ff669ce61f58b.

- Detected By: Completed full benchmark outer-validator logs and bounded independent replay-owner diagnosis.

- Failure Signature: Graph validator FileNotFoundError for latest.v1.json; sync check Greenfield immutable generation is missing or unsafe; both lanes also show 35 browser failures with truncated exception output.

- Trigger Path: Full proof from the working source tree containing an active published dashboard entry.

- Ownership: Benchmark snapshot dependency admission and maintainer proof-source preparation.

- Timeline: Captured 2026-10-13 through `odylith bug capture`.

- Blast Radius: Four benchmark scenarios, seven failed On observations, both cache profiles and matched raw baseline.

- SLO/SLA Impact: Release proof held after a complete 328-observation run; no consumer latency inference.

- Data Risk: No observed source or consumer data loss. Retain old HOLD and protected live publication.

- Security/Compliance: Do not replay unrelated retained generations or ambient host state.

- Invariant Violated: Unchanged validators must receive their required inputs in both matched lanes from one bounded source snapshot.

- Root Cause: Existing path discovery includes report arguments only when present; working index contains an active generation reference outside replay scope. Exact browser exception remains unproven.

- Solution: Reuse the authorized clean committed proof checkout and seed the exact report path with a frozen byte copy of retained HOLD report. Existing shared snapshot and ignored-file overlay owners should carry the input equally.

- Verification: First prove exact replay input hashes and run unchanged graph, sync and complete browser validators; only then run fresh complete proof. Old report remains HOLD.

- Agent Guardrails: No score, floor, case, validator or budget weakening. No forced edits. Preserve CB-125 runtime exclusions from stable source identity; no ambient restore or publication rollback.

- Related Incidents/Bugs: CB-043; CB-049; CB-124; CB-125; CB-361; B-142

- Code References: - src/odylith/runtime/evaluation/odylith_benchmark_snapshot_paths.py
- src/odylith/runtime/evaluation/odylith_benchmark_isolation.py
