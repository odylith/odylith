# Live Benchmark Snapshot

This note carries the fuller interpretation behind the short benchmark summary
published in the root [README](../../README.md).

## Current Result

Current Live Benchmark report: `52aa3f76538cf12f` from `2026-04-05T22:51:40Z`
with status `provisional_pass`.

The latest live benchmark ran `37` seeded scenarios across matched `warm` and
`cold` cache profiles under the same live host CLI model and reasoning
contract for `odylith_on` and `odylith_off`, using an isolated temporary
host home and stripped auto-consumed repo guidance surfaces. That produced
`148` live results, or `74` matched pairs. The published comparison keeps the
conservative scenario-wise worst-of-warm/cold view at `37` scenario pairs.

## Headline Movement

Compared with `odylith_off`, Odylith improved:

- required-path recall by `+0.227`
- required-path precision by `+0.168`
- hallucinated-surface rate by `-0.141`
- validation success by `+0.069`
- critical required-path recall by `+0.330`
- critical validation success by `+0.167`
- expectation success by `+0.393`
- write-surface precision by `+0.124`
- unnecessary widening by `-0.170`
- median live session input tokens by `-52,561`
- median total model tokens by `-53,774`
- median time to valid outcome by `-12.43s`
- median live agent runtime by `-18.42s`
- median validator overhead by `-755 ms`

Mean and p95 time remain slower than the raw host CLI, so tail latency is still
visible even though the full proof gate now clears.

## Publication Read

There are no remaining hard-gate blockers on this report.

- both cache profiles clear the hard quality gate
- tighter-budget behavior is back above the `0.80` floor
- the current proof remains local-memory-first on LanceDB plus Tantivy
- Vespa is still disabled in the current public snapshot

The main families still worth attention on the conservative published view
are:

- `architecture`
- `browser_surface_reliability`
- `component_governance`
- `cross_surface_governance_sync`
- `governed_surface_sync`
- `orchestration_feedback`

These are benchmark steering signals, not publication blockers.

## Reading Notes

Time to valid outcome and full-session token spend stay published as
diagnostics, not status blockers: they measure contention-shared matched-pair
wall clock and multi-turn session accumulation, not solo-user latency.

These live-proof wins should currently be read as local-memory wins first:
Odylith is proving that its local grounding, LanceDB/Tantivy retrieval,
governance scaffold, and execution policy beat the raw lane. Vespa remains an
optional remote augmentation tier, not a hidden assumption behind the current
public snapshot.

Additional agentic diagnostics from the same run:

- auto-grounded `58.3%` of sampled live cases
- delegated on `33.3%`
- showed `0.0%` widening
- reused the workspace daemon on `58.3%`
- cleared warm/cold robustness consistency on the published proof view

Odylith optimizes for coding outcome quality first: correctness and
non-regression, grounding recall and precision, validation and execution fit,
robustness, then time to valid outcome and token efficiency.
