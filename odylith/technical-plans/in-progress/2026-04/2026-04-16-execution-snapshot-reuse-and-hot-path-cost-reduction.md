Status: In progress
Created: 2026-04-16
Updated: 2026-04-16
Backlog: B-103

# Execution Snapshot Reuse and Hot Path Cost Reduction

## Goal
Measure and reduce Context Engine to Execution Engine hot-path cost by reusing built snapshots, emitting cost fields once, and keeping no-op/content-addressed behavior intact.

## Assumptions
- The benchmark runner and Context Engine store are red-zone sized and should receive only narrow plumbing.
- Snapshot reuse is the first low-risk latency and token-burn reduction.
- Measurement fields must be compact enough for benchmark summaries and packet surfaces.
- Missing or noncanonical component identity should fail closed before expensive expansion.

## Constraints
- Do not add execution aggregation logic to the benchmark runner.
- Do not rebuild execution snapshots for summaries when a compact snapshot already exists.
- Do not churn generated surfaces on no-op sync paths.
- Do not make token estimates exact-model claims; they are lightweight comparative estimates.

## Reversibility
Cost fields are additive and can be ignored by consumers. Removing snapshot reuse should require proof that repeated builds do not regress latency or token budget.

## Related Bugs
No related Casebook bug found.

## Must-Ship
- [x] Measure context packet build time via benchmark packet results.
- [x] Measure Execution Engine snapshot duration.
- [x] Estimate prompt-bundle, runtime-contract, handshake, snapshot, and total payload tokens.
- [x] Add benchmark family medians for context packet build time, snapshot time, prompt bundle tokens, runtime contract tokens, and total payload tokens.
- [x] Add lower-is-better comparison deltas for the execution-engine cost fields.
- [x] Reuse existing compact execution snapshots across packet summaries.

## Should-Ship
- [x] Keep benchmark cost aggregation in `odylith_benchmark_execution_engine.py`.
- [x] Limit benchmark runner changes to fixture-key allowance and packet duration plumbing.
- [x] Preserve source/bundle corpus alignment after adding cost-backed scenarios.

## Deferred
- Exact tokenizer-backed token accounting.
- Broader runtime surface cache invalidation refactors beyond this handshake path.

## Success Criteria
- Execution benchmark summaries contain latency and token medians for the Context Engine to Execution Engine path.
- Snapshot reuse status is visible in compact summaries.
- Focused benchmark tests prove the cost fields.

## Impacted Areas
- `src/odylith/runtime/context_engine/execution_engine_handshake.py`
- `src/odylith/runtime/evaluation/odylith_benchmark_execution_engine.py`
- `src/odylith/runtime/evaluation/odylith_benchmark_runner.py`
- `tests/unit/runtime/test_odylith_benchmark_execution_engine.py`

## Validation Plan
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_execution_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_corpus.py`
- `git diff --check`
