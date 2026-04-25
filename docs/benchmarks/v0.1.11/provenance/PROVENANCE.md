# v0.1.11 Benchmark Provenance

This provenance note describes the compressed raw source bundle stored at:

`docs/benchmarks/v0.1.11/raw-source/odylith-v0.1.11-benchmark-raw-source-20260425.tar.gz`

## Identity

- archive created from repo: `/Users/freedom/code/odylith`
- archive recorded on branch: `2026/freedom/v0.1.11`
- archive recorded while local HEAD was: `d07422f7522cae1467ed8338226d15c23c023b5d`
- live proof report tree: `1cfca107048e9dbe3b81ddd933ca1138f0c4e6f0`
- live proof report id: `44f2a3d83d2c9975`
- diagnostic report id: `9dcae95d5bb62c75`
- archive sha256:
  `67aafebbb0fe286c5027f86cc187c38fec8e7b49ff98246d0e7242b99cf76ebe`

## Scope

The archive is intentionally versioned under `docs/benchmarks/v0.1.11/` and
does not move mutable runtime state into `.odylith/runtime`. It captures the
raw benchmark source truth needed to audit the v0.1.11 README claim:

- report JSON for the selected proof and diagnostic reports
- proof and diagnostic logs
- shard report JSON referenced by the logs
- benchmark corpus and benchmark component source truth
- generated benchmark docs, tables, summaries, and graphs

The exact archived paths are listed in
[raw-source-file-list.txt](raw-source-file-list.txt). Checksums for the archive
and rendered version-folder artifacts are listed in [SHA256SUMS](SHA256SUMS).
