# Grounding Benchmark Snapshot

This note carries the fuller interpretation behind the short Grounding Benchmark summary
published in the root [README](../../README.md).

## Current Result

Current Grounding Benchmark report: `9dcae95d5bb62c75` from `2026-04-25T11:20:25Z` with status `provisional_pass`.

The latest Grounding Benchmark ran `82` seeded scenarios on cache profile(s) `warm` comparing `odylith_on` versus `odylith_off` on packet and prompt construction only.
Across the `82` Grounding Benchmark pairs, wall clock was `22.540 ms` median, `46.680 ms` at `p95`, and `1.86s` total.

Current Grounding Benchmark posture is local-first on the Odylith Memory Substrate. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

## Headline Movement

Compared with the `odylith_off` prompt bundle, Odylith moved:

- required-path recall by `0.326`
- required-path precision by `0.049`
- hallucinated-surface rate by `0.000`
- validation-success proxy by `0.689`
- critical required-path recall by `0.278`
- critical validation-success proxy by `0.613`
- expectation-success proxy by `0.951`
- median prompt-bundle input tokens by `+834`
- median total prompt-bundle payload tokens by `+1,076`
- median packet time by `+23 ms`

## Publication Read

There are no hard-gate blockers on this report.

- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- full tracked-corpus coverage rate: `1.000`
- operating-policy scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `41`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy operating-policy ratio: `0.29`

## Reading Notes

- `odylith_off` is the raw prompt-bundle control for this mechanism-evidence
  view.
- Prompt-visible path credit and Turn Gate evidence must remain explicit in the report contract.
- Current Grounding Benchmark posture is local-first on the Odylith Memory Substrate. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Grounding Benchmark gains only matter if they preserve or improve the live proof lane.
