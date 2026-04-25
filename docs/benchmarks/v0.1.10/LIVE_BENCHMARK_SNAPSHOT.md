# Live Benchmark Snapshot

This note carries the fuller interpretation behind the short benchmark summary
published in the root [README](../../README.md).

## Current Result

Current Live Benchmark report: `2d8444952aef28d2` from `2026-04-24T00:57:09Z` with status `hold`.

The latest live benchmark ran `82` seeded scenarios across matched cache profile(s) `warm` and `cold` under the declared comparison contract `full_product_assistance_vs_raw_agent`.
That produced `164` full matched pairs. The published comparison keeps the conservative same-scenario view at `82` pairs.

Current proof posture is local-first on the Odylith Memory Substrate. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

## Headline Movement

Compared with `odylith_off`, Odylith moved:

- required-path recall by `0.252`
- required-path precision by `0.260`
- hallucinated-surface rate by `-0.260`
- validation success by `0.068`
- critical required-path recall by `0.237`
- critical validation success by `0.032`
- expectation success by `0.692`
- write-surface precision by `-0.403`
- unnecessary widening by `-0.014`
- median live-session input tokens by `-101,010`
- median total model tokens by `-103,238`
- median time to valid outcome by `-1m 12s`

## Publication Read

The current report is on `hold` because these hard-gate blockers remain:
- write-surface precision fell below the raw baseline
- selected cache profiles do not all clear the hard quality gate

- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- full tracked-corpus coverage rate: `1.000`
- implementation scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `42`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy implementation ratio: `0.29`

Current attention families on the published view:
- `architecture`
- `live_proof_discipline`
- `release_publication`
- `runtime_state_integrity`

## Reading Notes

- Time to valid outcome and full-session token spend stay published as readouts, not status blockers.
- Current proof posture is local-first on the Odylith Memory Substrate. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Operating-posture readouts: auto-grounded `100.0%`, delegated `0.0%`, widening `0.0%`, and workspace-daemon reuse `0.0%`.
- Warm/cold robustness consistency cleared: `False`.
