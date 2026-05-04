# Live Benchmark Snapshot

This note carries the fuller interpretation behind the short benchmark summary
published in the root [README](../../README.md).

## Current Result

Current Live Benchmark report: `44f2a3d83d2c9975` from `2026-04-25T11:19:38Z` with status `provisional_pass`.

The latest live benchmark ran `82` seeded scenarios across matched cache profile(s) `warm` and `cold` under the declared comparison contract `full_product_assistance_vs_raw_agent`.
That produced `164` full matched pairs. The published comparison keeps the conservative same-scenario view at `82` pairs.

This report is the operating-policy proof. The `odylith_on` lane includes
report-visible validator-backed closure and write admission. In this report, `68 / 82`
`odylith_on` rows used focused non-mutating closure; `37 / 41` write-labeled
`odylith_on` rows stopped that way; and `4 / 82` `odylith_on` rows recorded
file changes. That is the intended write-admission signal: Odylith proves
already-satisfied contracts and suppresses unnecessary mutation under the
measured scenario contract.

Current proof posture is local-first on the Odylith Memory Substrate. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.

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
- operating-policy scenarios in tracked corpus: `77`
- write-plus-validator scenarios in tracked corpus: `41`
- correctness-critical scenarios in tracked corpus: `31`
- mechanism-heavy operating-policy ratio: `0.29`

## Reading Notes

- Time to valid outcome and full-session token spend stay published as readouts, not status blockers.
- Current proof posture is local-first on the Odylith Memory Substrate. Remote retrieval is `disabled` in the selected report. Local memory-backed retrieval ready: `True`.
- Operating-posture readouts: auto-grounded `100.0%`, delegated `0.0%`, widening `1.2%`, and workspace-daemon reuse `0.0%`.
- Warm/cold robustness consistency cleared: `True`.
- Focused non-mutating closure rows are write-admission evidence: they measure
  validated closure and mutation suppression under the measured scenario
  contract.
