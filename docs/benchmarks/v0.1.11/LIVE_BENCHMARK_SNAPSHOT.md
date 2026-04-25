# Live Benchmark Snapshot

This note carries the fuller interpretation behind the short benchmark summary
published in the root [README](../../README.md).

## Current Result

Current Live Benchmark report: `44f2a3d83d2c9975` from `2026-04-25T11:19:38Z` with status `provisional_pass`.

The latest live benchmark ran `82` seeded scenarios across matched cache profile(s) `warm` and `cold` under the declared comparison contract `full_product_assistance_vs_raw_agent`.
That produced `164` full matched pairs. The published comparison keeps the conservative same-scenario view at `82` pairs.

Current proof posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

## Headline Movement

Compared with `odylith_off`, Odylith moved:

- required-path recall by `0.258`
- required-path precision by `0.421`
- hallucinated-surface rate by `-0.397`
- validation success by `0.081`
- critical required-path recall by `0.206`
- critical validation success by `0.097`
- expectation success by `0.688`
- write-surface precision by `0.011`
- unnecessary widening by `-0.011`
- median live-session input tokens by `-206,626`
- median total model tokens by `-209,404`
- median time to valid outcome by `-1m 28s`

## Publication Read

There are no hard-gate blockers on this report.

- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- full tracked-corpus coverage rate: `1.000`
- implementation scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `41`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy implementation ratio: `0.29`

## Reading Notes

- Time to valid outcome and full-session token spend stay published as diagnostics, not status blockers.
- Current proof posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Operating-posture diagnostics: auto-grounded `100.0%`, delegated `0.0%`, widening `1.2%`, and workspace-daemon reuse `0.0%`.
- Warm/cold robustness consistency cleared: `True`.
