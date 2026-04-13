# Internal Diagnostic Benchmark Snapshot

This note carries the fuller interpretation behind the short Grounding
Benchmark summary published in the root [README](../../README.md).

## Current Result

Current Internal Diagnostic Benchmark report: `74cbe36427f2c375` from
`2026-04-05T02:47:27Z` with status `hold`.

The latest grounding benchmark ran `37` seeded scenarios on the `warm` cache
profile comparing `odylith_on` versus `odylith_off` on packet and prompt
construction only. Across the `37` grounding pairs, wall clock was `7.048 ms`
median, `9.881 ms` at `p95`, and `254.219 ms` total.

In the current public diagnostic runs, the retrieval and memory layer is the
local LanceDB plus Tantivy substrate. Vespa is not part of the default
published snapshot unless explicitly configured and reported.

## Headline Movement

Compared with the `odylith_off` prompt bundle, Odylith improved:

- required-path recall by `+0.320`
- required-path precision by `+0.084`
- validation-success proxy rate by `+0.690`
- critical required-path recall by `+0.284`
- critical validation-success proxy rate by `+0.667`
- expectation-success proxy rate by `+1.000`

It also added:

- `+7.045 ms` median packet and prompt time
- `+47.0` median prompt-bundle input tokens
- `+57.0` median total prompt-bundle payload tokens

The current diagnostic `hold` is not a recall collapse. It is still driven by
a small observed-surface drift regression (`+0.024`
hallucinated-surface-rate delta) and a selected-cache-profile coverage miss.

## Reading Notes

In this diagnostic lane, `odylith_off` is still the raw prompt-bundle
control, but the frontier no longer forces the whole baseline onto the `0.00`
recall rail. The scorer gives the control credit for repo paths explicitly
named in the prompt bundle, so the red points show prompt-visible grounding
only while Odylith still gets the full packet-construction advantage.

The operating-posture graph remains a separate `12`-sample adoption-proof
slice, so its operation mix and auto-grounding rates are sampled runtime
posture, not inferred placeholders.

Grounding is the pre-run diagnostic view. The Live Benchmark is the
product-claim lane, so grounding only matters if it preserves or improves the
live result.
