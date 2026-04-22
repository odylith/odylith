# Internal Diagnostic Benchmark Snapshot

This note carries the fuller interpretation behind the short diagnostic summary
published in the root [README](../../README.md).

## Current Result

Current Internal Diagnostic Benchmark report: `4dfde9ab25d7149c` from `2026-04-22T19:10:57Z` with status `hold`.

The latest internal diagnostic benchmark ran `82` seeded scenarios on cache profile(s) `warm` comparing `odylith_on` versus `odylith_off` on packet and prompt construction only.
Across the `82` diagnostic pairs, wall clock was `30.381 ms` median, `70.469 ms` at `p95`, and `2.69s` total.

Current diagnostic posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

## Headline Movement

Compared with the `odylith_off` prompt bundle, Odylith moved:

- required-path recall by `0.325`
- required-path precision by `0.030`
- hallucinated-surface rate by `0.019`
- validation-success proxy by `0.657`
- critical required-path recall by `0.278`
- critical validation-success proxy by `0.613`
- expectation-success proxy by `0.951`
- median prompt-bundle input tokens by `+834`
- median total prompt-bundle payload tokens by `+1,076`
- median packet time by `+30 ms`

## Publication Read

The current report is on `hold` because these hard-gate blockers remain:
- observed-surface drift is worse than the raw baseline
- execution-engine benchmark slices resolved the wrong current phase
- execution-engine benchmark slices resolved the wrong last successful phase
- selected cache profiles do not all clear the hard quality gate

- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- full tracked-corpus coverage rate: `1.000`
- implementation scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `42`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy implementation ratio: `0.29`

Current diagnostic weak families:
- `broad_shared_scope`
- `execution_engine`
- `live_proof_discipline`

## Reading Notes

- `odylith_off` is the raw prompt-bundle control, not the product-claim lane.
- Prompt-visible path credit and preflight evidence must remain explicit in the report contract.
- Current diagnostic posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Diagnostic gains only matter if they preserve or improve the live proof lane.
