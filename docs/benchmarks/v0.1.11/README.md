# v0.1.11 Benchmark Artifacts

This folder is the versioned GitHub bundle for the v0.1.11 benchmark proof.
It keeps the rendered README artifacts and the compressed raw source truth
together so the public benchmark can be audited without relying on mutable
`.odylith/runtime` state.

## Reports

- Live proof: `44f2a3d83d2c9975`
  - generated: `2026-04-25T11:19:38Z`
  - status: `provisional_pass`
  - comparison: `odylith_on` versus `odylith_off`
  - cache profiles: `warm`, `cold`
- Grounding Benchmark: `9dcae95d5bb62c75`
  - generated: `2026-04-25T11:20:25Z`
  - status: `provisional_pass`
  - comparison: internal packet and prompt Grounding Benchmark lane

## Rendered Artifacts

- [Live Benchmark Snapshot](LIVE_BENCHMARK_SNAPSHOT.md)
- [Grounding Benchmark Snapshot](GROUNDING_BENCHMARK_SNAPSHOT.md)
- [Benchmark Tables](BENCHMARK_TABLES.md)
- [Proof Graphs](proof/)
- [Grounding Graphs](grounding/)

## Raw Source Truth

The compressed raw source bundle is:

- [odylith-v0.1.11-benchmark-raw-source-20260425.tar.gz](raw-source/odylith-v0.1.11-benchmark-raw-source-20260425.tar.gz)

It contains `85` files, including:

- canonical live and grounding report JSON
- proof shard logs from the 12-shard run, affected-shard reruns, fill run, and
  final shard retry
- Grounding Benchmark run log
- shard history report JSON referenced by those logs
- benchmark corpus and benchmark component source truth
- generated benchmark docs and graph artifacts used by the README

Checksums and the exact file list are stored under [provenance](provenance/).
