# Odylith Projection Bundle
Last updated: 2026-04-07


Last updated (UTC): 2026-04-07

## Purpose
Odylith Projection Bundle is the compiler-owned JSONL read model that writes
the projection manifest plus document and edge streams shared across the memory
substrate.

## Scope And Non-Goals
### Odylith Projection Bundle owns
- `.odylith/runtime/odylith-compiler/projection-manifest.v1.json`
- `.odylith/runtime/odylith-compiler/documents.v1.jsonl`
- `.odylith/runtime/odylith-compiler/edges.v1.jsonl`
- deterministic write and load helpers for those three artifacts
- the stable handoff from projection compilation to downstream memory
  consumers

### Odylith Projection Bundle does not own
- the full JSON projection snapshot fallback
- LanceDB or Tantivy materialization
- remote retrieval or remote sync
- packet compaction, redaction, or execution-profile shaping

## Developer Mental Model
- `src/odylith/runtime/memory/odylith_projection_bundle.py` is the one
  contract owner for the bundle manifest and the two JSONL streams.
- This bundle is the first compiled memory read model, not the final one.
  It exists so later consumers can share one deterministic substrate instead of
  recompiling repo truth independently.
- The bundle is derived and disposable. If the files are deleted or corrupted,
  the next valid projection compile can recreate them.
- Document and edge streams are intentionally simple, portable artifacts. They
  are readable without a local database and stable enough to feed the snapshot,
  local backend, and diagnostics.

## Runtime Contract
### Inputs
- compiled projection documents from
  `src/odylith/runtime/context_engine/odylith_context_engine_store.py`
- compiled projection edges from the same compiler path
- `projection_fingerprint`
- `projection_scope`
- `input_fingerprint`
- `source`

### Generated artifacts
- `.odylith/runtime/odylith-compiler/projection-manifest.v1.json`
- `.odylith/runtime/odylith-compiler/documents.v1.jsonl`
- `.odylith/runtime/odylith-compiler/edges.v1.jsonl`

### Manifest contract
`projection-manifest.v1.json` must expose:
- `version`
- `compiled_utc`
- `ready`
- `source`
- `projection_fingerprint`
- `projection_scope`
- `input_fingerprint`
- `document_count`
- `edge_count`
- `documents_path`
- `edges_path`

### Document stream contract
`documents.v1.jsonl` is the compiler-to-memory document stream. Rows are
mapping-shaped JSON records and typically carry:
- `doc_key`
- `kind`
- `entity_id`
- `title`
- `path`
- `content`

Downstream consumers may enrich those rows later, but the compiler-owned bundle
remains the stable deterministic source stream.

### Edge stream contract
`edges.v1.jsonl` is the typed relationship stream linking the compiled
documents. It is the graph sidecar consumed by retrieval and diagnostics, not
an invitation to re-query the repo ad hoc.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
  compiles and writes the bundle.
- [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md)
  materializes a full JSON fallback read model from the same compile wave.
- [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md)
  consumes the bundle when fast local retrieval is available.
- [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md)
  syncs document payloads derived from the same compiled truth.

## Failure And Recovery Posture
- Missing bundle files are rebuildable and should trigger recompilation, not
  silent invention.
- Invalid JSONL rows should degrade to a weaker reload or rebuild path instead
  of polluting downstream memory with half-parsed artifacts.
- The bundle must stay fingerprint-aware. If the projection fingerprint or
  scope changes, downstream consumers should treat the old bundle as stale.
- The write path is intentionally idempotent through the shared
  `odylith_context_cache` helpers so repeated refreshes do not churn files
  without content change.

## Validation Playbook
- `odylith context-engine --repo-root . warmup`
- `odylith context-engine --repo-root . status`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_context_grounding_hardening.py tests/unit/runtime/test_odylith_memory_backend.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-07: Promoted the compiler-owned bundle manifest plus document and edge streams into a first-class Registry component so the first compiled memory read model has explicit governed ownership. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
