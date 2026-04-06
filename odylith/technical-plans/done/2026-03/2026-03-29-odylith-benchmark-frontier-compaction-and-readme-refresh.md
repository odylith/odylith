Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-019

Goal: Improve Odylith's Codex benchmark frontier again, then refresh the README
benchmark snapshot and graph assets from the stronger validated report.

Assumptions:
- The current latest benchmark report is green enough to use as the comparison
  baseline for one more compaction pass.
- There is still removable hot-path overhead in runtime-contract or routing
  payloads without weakening grounded behavior.
- The published benchmark visuals and README snapshot should be regenerated only
  after the final stronger report is validated.

Constraints:
- Do not regress required-path recall, validation success, or critical
  validation success.
- Keep the graph order and maintained README benchmark framing intact.
- Do not update the README from a weaker or lateral report.

Reversibility: Reverting this slice restores the previous hot-path contract and
README benchmark snapshot without data migration.

Boundary Conditions:
- Scope includes benchmark analysis, hot-path compaction, corpus rerun, and
  README plus graph refresh.
- Scope excludes benchmark-corpus redesign and non-benchmark product surface
  changes.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] The latest report still leaves measurable prompt, payload, or latency
  headroom on the table.
- [x] The highest-value remaining overhead has been identified at the scenario
  or family level.
- [x] The public README and graph assets still point at the pre-improvement
  benchmark snapshot.

## Success Criteria
- [x] Hot-path runtime-contract or routing overhead is reduced further on the
  benchmark corpus.
- [x] Median prompt-token and total-payload deltas improve beyond the current
  latest report.
- [x] Required-path recall and validation success do not regress.
- [x] README benchmark snapshot and graph assets are regenerated from the final
  improved report.

## Non-Goals
- [x] Benchmark-corpus redesign.
- [x] Changing the benchmark graph order or release presentation contract.
- [x] Trading away benchmark accuracy for cosmetic speed.

## Impacted Areas
- [x] [odylith_benchmark_runner.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_runner.py)
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [test_odylith_benchmark_runner.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_benchmark_runner.py)
- [x] [odylith_benchmark_graphs.py](/Users/freedom/code/odylith/src/odylith/runtime/evaluation/odylith_benchmark_graphs.py)
- [x] [README.md](/Users/freedom/code/odylith/README.md)
- [x] [odylith-benchmark-family-heatmap.svg](/Users/freedom/code/odylith/docs/benchmarks/odylith-benchmark-family-heatmap.svg)
- [x] [odylith-benchmark-operating-posture.svg](/Users/freedom/code/odylith/docs/benchmarks/odylith-benchmark-operating-posture.svg)
- [x] [odylith-benchmark-frontier.svg](/Users/freedom/code/odylith/docs/benchmarks/odylith-benchmark-frontier.svg)

## Risks & Mitigations

- [x] Risk: over-compaction drops routed signal needed for accuracy.
  - [x] Mitigation: rerun focused benchmark tests and keep recall/validation as
    hard gates.
- [x] Risk: README gets refreshed from a report that is not actually stronger.
  - [x] Mitigation: compare the final report against the current latest report
    before regenerating the snapshot and SVG assets.

## Validation/Test Plan
- [x] `odylith benchmark --repo-root .`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_evaluation_ledger.py tests/unit/runtime/test_odylith_benchmark_graphs.py`
- [x] `odylith sync --repo-root . --force --impact-mode full`
- [x] `git diff --check`

## Rollout/Communication
- [x] Keep the published graph order unchanged.
- [x] Refresh README numbers and SVG assets together from the final report.
- [x] Update backlog and plan indexes when the slice closes.

## Current Outcome
- Report `5ed96082084ffaa6` is now the latest benchmark truth and improves over
  `091cdd60b1795fc8` on the same warm-cache Codex corpus.
- Median latency improved from `35.230 ms` versus `52.123 ms`
  (`-16.893 ms` delta), beating the prior `-15.015 ms` frontier.
- Median prompt and total payload improved from `119.0` versus `834.5`
  (`-715.5` delta), beating the prior `-631.5` frontier.
- Required-path recall stayed at `0.964` and validation success stayed at
  `0.714`, so the stronger frontier did not give back correctness.
- README benchmark numbers and the canonical SVG graphs were refreshed from the
  final report.
- Full `odylith sync` and `git diff --check` passed after the backlog and plan
  source truth was reconciled.
