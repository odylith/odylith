# v0.1.10 Benchmark Archive

This folder preserves the previous README-backed benchmark bundle after the
v0.1.11 report became the current public benchmark claim.

## Archived Reports

- Live proof snapshot: `2d8444952aef28d2`
  - generated: `2026-04-24T00:57:09Z`
  - status: `hold`
  - reason: write-surface precision fell below the raw baseline, and selected
    cache profiles did not all clear the hard quality gate
- Grounding Benchmark snapshot: `dd35a4aab061f49f`
  - generated: `2026-04-24T00:57:12Z`
  - status: `provisional_pass`
- Legacy unprofiled graph snapshot: `926bfeab4e887ade`

## Contents

- [Archived Live Benchmark Snapshot](LIVE_BENCHMARK_SNAPSHOT.md)
- [Archived Grounding Benchmark Snapshot](GROUNDING_BENCHMARK_SNAPSHOT.md)
- [Archived Benchmark Tables](BENCHMARK_TABLES.md)
- [Archived Proof Graphs](proof/)
- [Archived Grounding Graphs](grounding/)
- [Legacy Graphs](legacy-graphs/)

Raw runtime source truth was not versioned for this older archive before the
v0.1.11 documentation change. Starting with v0.1.11, the benchmark folder keeps
a compressed raw-source bundle alongside rendered graphs and summaries.
