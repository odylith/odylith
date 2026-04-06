Status: Done

Created: 2026-03-28

Updated: 2026-03-29

Backlog: B-009

Goal: Remove stale benchmark false negatives by aligning corpus workstream
truth, recognizing Odylith-owned guidance paths during orchestration
validation, and refreshing the public benchmark snapshot from a fresh run.

Assumptions:
- The benchmark gate should stay strict; the fix is to remove stale or
  incorrect inputs, not to lower the bar.
- Odylith-owned product guidance under `odylith/` should count when a prompt
  explicitly operates on docs or skills surfaces.
- The current README benchmark snapshot is intended to reflect the latest local
  report, not a historic point-in-time sample.

Constraints:
- Keep the orchestration validator fail-closed for truly undeclared write
  surfaces.
- Do not invent new benchmark families or drop hard scenarios just to improve
  the numbers.
- Keep the fix grounded in current repo truth and current benchmark source.

Reversibility: Reverting this slice restores the old benchmark corpus anchors,
the narrower validation behavior, and the previous benchmark snapshot wording.

Boundary Conditions:
- Scope includes the benchmark corpus, benchmark runner/tests, orchestration
  surface recognition, and README benchmark snapshot updates.
- Scope excludes broader routing-policy redesign, benchmark threshold changes,
  and unrelated install/shell UX work already in flight on this branch.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Current benchmark report held on governance packet coverage and widening health even though the important delta against baseline was already positive.
- [x] Benchmark corpus source referenced missing workstreams (`B-242`, `B-275`) for Odylith-owned skill slices.
- [x] Orchestration validation rejected grounded Odylith-owned docs/skills paths because surface recognition only saw the top-level `odylith/` prefix.
- [x] README benchmark snapshot was stale once a fresh benchmark run landed.

## Success Criteria
- [x] Benchmark corpus workstream anchors reference real Radar ids.
- [x] Odylith-owned docs/skills paths satisfy docs/skills implied write-surface checks when appropriate.
- [x] Focused unit tests cover the new validation behavior and benchmark contract.
- [x] Fresh benchmark report clears the previous acceptance hold to `provisional_pass`.
- [x] README benchmark snapshot matches the new report.

## Non-Goals
- [x] Relaxing validation for unrelated write surfaces.
- [x] Lowering acceptance thresholds.
- [x] Changing public messaging outside the benchmark snapshot unless required by the new results.

## Impacted Areas
- [x] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [x] [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [x] [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [README.md](/Users/freedom/code/odylith/README.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [x] [test_subagent_surface_validation.py](/Users/freedom/code/odylith/tests/unit/runtime/test_subagent_surface_validation.py)

## Traceability
### Benchmark Source
- [x] [optimization-evaluation-corpus.v1.json](/Users/freedom/code/odylith/odylith/runtime/source/optimization-evaluation-corpus.v1.json)
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)

### Orchestration Contract
- [x] [subagent_router.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_router.py)
- [x] [subagent_orchestrator.py](/Users/freedom/code/odylith/src/odylith/runtime/orchestration/subagent_orchestrator.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)

### Public Snapshot
- [x] [README.md](/Users/freedom/code/odylith/README.md)

### Tests
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [x] [test_subagent_surface_validation.py](/Users/freedom/code/odylith/tests/unit/runtime/test_subagent_surface_validation.py)

## Risks & Mitigations

- [x] Risk: the validator fix could become too broad.
  - [x] Mitigation: only map Odylith-owned docs and skills paths to their equivalent write surfaces; keep unrelated surfaces strict.
- [x] Risk: refreshed benchmark results could still hold because widening remains genuinely too high.
  - [x] Mitigation: rerun the full harness after the contract and corpus fixes, then trim prompt-only hot-path scaffolding instead of weakening correctness checks.
- [x] Risk: README snapshot could drift again.
  - [x] Mitigation: update it in the same slice immediately after rerunning the benchmark.

## Validation/Test Plan
- [x] `pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py`
- [x] `pytest -q tests/unit/runtime/test_subagent_surface_validation.py`
- [x] `odylith benchmark --repo-root .`

## Rollout/Communication
- [x] Treat the fresh benchmark report as the new product benchmark snapshot.
- [x] Call out whether the gate fully clears or merely improves.

## Dependencies/Preconditions
- [x] Benchmark source corpus and orchestration modules load cleanly in the current branch.
- [x] No existing bug record blocks the benchmark harness from running locally.

## Edge Cases
- [x] Odylith-owned markdown under `odylith/runtime/`, `odylith/surfaces/`, or `odylith/registry/` counts as docs-like surfaces when the prompt explicitly targets docs guidance.
- [x] Pure code paths outside Odylith-owned docs/skills still fail if the prompt implies undeclared docs or test edits.
- [x] Finished but still-valid workstreams referenced by benchmarks remain acceptable when they are real repo truth.

## Open Questions/Decisions
- [x] Decision: treat bundle-asset Odylith docs paths the same as source Odylith docs paths for write-surface recognition.

## Current Outcome
- Benchmark corpus workstream truth now matches live Radar truth instead of dead ids.
- Orchestration validation now accepts Odylith-owned docs and skills paths without relaxing unrelated surface checks.
- Route-ready hot-path packets stop sending redundant narrowing and internal optimization scaffolding to the agent.
- The benchmark gate now clears as `provisional_pass` with better recall, better validation success, lower median agent prompt tokens, and lower median latency than the raw full-scan baseline.
