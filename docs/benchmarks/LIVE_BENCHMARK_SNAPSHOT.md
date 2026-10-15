# Live Benchmark Snapshot

This note carries the fuller interpretation behind the short benchmark summary
published in the root [README](../../README.md).

## Current Result

Current Live Benchmark report: `ea0fbd0916ee9690` from `2026-10-15T15:08:18Z` with status `provisional_pass`.

The latest live benchmark ran `82` seeded scenarios across matched cache profile(s) `warm` and `cold` under the declared comparison contract `full_product_assistance_vs_raw_agent`.
That produced `164` full matched pairs. The published comparison keeps the conservative same-scenario view at `82` pairs.

Current proof posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

## Headline Movement

Compared with `odylith_off`, Odylith moved:

- required-path recall by `0.227`
- required-path precision by `0.502`
- hallucinated-surface rate by `-0.502`
- validation success by `0.013`
- critical required-path recall by `0.205`
- critical validation success by `0.000`
- expectation success by `0.652`
- write-surface precision by `0.286`
- unnecessary widening by `0.000`
- median live-session input tokens by `-245,206`
- median total model tokens by `-246,380`
- median time to valid outcome by `-48s`

## Publication Read

There are no hard-gate blockers on this report.

- fairness contract passed: `True`
- corpus seriousness floor passed: `True`
- full tracked-corpus coverage rate: `1.000`
- operating-policy scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `41`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy operating-policy ratio: `0.29`

Current attention families on the published view:
- `destructive_scope_control`

## Reading Notes

- Time to valid outcome and full-session token spend stay published as diagnostics, not status blockers.
- Current proof posture is local-first on `lance_local_columnar` plus `tantivy_sparse_recall`. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Operating-posture diagnostics: auto-grounded `75.0%`, delegated `25.0%`, widening `16.7%`, and workspace-daemon reuse `75.0%`.
- Warm/cold robustness consistency cleared: `True`.
