# v0.1.11 Benchmark Provenance

This provenance note describes the compressed raw source bundle stored at:

`docs/benchmarks/v0.1.11/raw-source/odylith-v0.1.11-benchmark-raw-source-20260425.tar.gz`

## Identity

- archive created from repo: `/Users/freedom/code/odylith`
- archive recorded on branch: `2026/freedom/v0.1.11`
- archive recorded while local HEAD was: `884ceceefc3d8322805696e5dd2b75e0179660fc`
- live proof report tree: `1cfca107048e9dbe3b81ddd933ca1138f0c4e6f0`
- live proof report id: `44f2a3d83d2c9975`
- grounding report id: `9dcae95d5bb62c75`
- archive sha256:
  `b6508487866213efd85b2da88235fa19c6c3e73caa23de467154b83a64fbf705`

## Scope

The archive is intentionally versioned under `docs/benchmarks/v0.1.11/` and
does not move mutable runtime state into `.odylith/runtime`. It captures the
raw benchmark source truth needed to audit the v0.1.11 README claim:

- report JSON for the selected proof and grounding reports
- proof and Grounding Benchmark logs
- shard report JSON referenced by the logs
- benchmark corpus and benchmark component source truth
- generated benchmark docs, tables, summaries, and graphs

The exact archived paths are listed in
[raw-source-file-list.txt](raw-source-file-list.txt). Checksums for the archive
and rendered version-folder artifacts are listed in [SHA256SUMS](SHA256SUMS).
