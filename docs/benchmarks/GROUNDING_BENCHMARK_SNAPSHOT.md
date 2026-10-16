# Internal Diagnostic Benchmark Snapshot

This note carries the fuller interpretation behind the short diagnostic summary
published in the root [README](../../README.md).

## Current Result

Current Internal Diagnostic Benchmark report: `b75f850362a680d2` from `2026-10-15T19:31:51Z` with status `hold`.

The latest internal diagnostic benchmark ran `82` seeded scenarios on cache profile(s) `cold` comparing `odylith_on` versus `odylith_off` on packet and prompt construction only.
Across the `82` diagnostic pairs, wall clock was `58.529 ms` median, `211.377 ms` at `p95`, and `6.67s` total.

Current diagnostic posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

## Headline Movement

Compared with the `odylith_off` prompt bundle, Odylith moved:

- required-path recall by `0.316`
- required-path precision by `0.047`
- hallucinated-surface rate by `0.002`
- validation-success proxy by `0.648`
- critical required-path recall by `0.256`
- critical validation-success proxy by `0.548`
- expectation-success proxy by `0.823`
- median prompt-bundle input tokens by `+871`
- median total prompt-bundle payload tokens by `+1,124`
- median packet time by `+59 ms`

## Publication Read

The current report is on `hold` because these hard-gate blockers remain:
- observed-surface drift is worse than the raw baseline
- selected cache profiles do not all clear the hard quality gate

Secondary guardrail blockers:
- median latency exceeds the +15 ms guardrail
- median prompt cost exceeds the +64-token guardrail
- median total payload exceeds the +96-token guardrail

- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- full tracked-corpus coverage rate: `1.000`
- operating-policy scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `41`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy operating-policy ratio: `0.29`

Current diagnostic weak families:
- `architecture`

## Reading Notes

- `odylith_off` is the raw prompt-bundle control for this mechanism-evidence view.
- Prompt-visible path credit and Turn Gate evidence must remain explicit in the report contract.
- Current diagnostic posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Diagnostic gains only matter if they preserve or improve the live proof lane.
