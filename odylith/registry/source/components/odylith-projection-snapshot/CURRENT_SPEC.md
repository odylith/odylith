# Odylith Projection Snapshot
Last updated: 2026-04-07


Last updated (UTC): 2026-04-07

## Purpose
Odylith Projection Snapshot is the compiler-owned JSON fallback read model that
stores fully materialized projection tables and projection-state metadata for
deterministic local reads.

## Scope And Non-Goals
### Odylith Projection Snapshot owns
- `.odylith/runtime/odylith-compiler/projection-snapshot.v1.json`
- the write and load helpers for that snapshot
- the deterministic full-table fallback contract when fast local retrieval is
  unavailable, stale, or intentionally bypassed

### Odylith Projection Snapshot does not own
- the document and edge JSONL bundle streams
- LanceDB and Tantivy runtime materialization
- remote retrieval state or sync
- packet sanitization and compact evidence-pack shaping

## Developer Mental Model
- `src/odylith/runtime/memory/odylith_projection_snapshot.py` owns one thing:
  a full JSON snapshot of the compiled projection state.
- This snapshot is the blunt but honest fallback path. It trades storage
  compactness for deterministic availability.
- The snapshot is derived and disposable. If it disappears or its fingerprint
  no longer matches the requested scope, the Context Engine can rebuild it.
- Snapshot truth is compiler truth. It must not become a quiet cache for stale
  runtime guesses.

## Runtime Contract
### Inputs
- `projection_fingerprint`
- `projection_scope`
- `input_fingerprint`
- `tables`
- `projection_state`
- `updated_projections`
- `source`

### Generated artifact
- `.odylith/runtime/odylith-compiler/projection-snapshot.v1.json`

### Snapshot contract
`projection-snapshot.v1.json` must expose:
- `version`
- `compiled_utc`
- `ready`
- `source`
- `projection_fingerprint`
- `projection_scope`
- `input_fingerprint`
- `updated_projections`
- `tables`
- `projection_state`

The snapshot is the fully materialized read model. It should be sufficient for
deterministic local readers without needing a secondary relational or vector
store.

## Composition
- [Odylith Context Engine](../odylith-context-engine/CURRENT_SPEC.md)
  compiles and consumes the snapshot in fallback or warm-reuse lanes.
- [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md)
  carries the lighter shared stream form for sibling consumers.
- [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md)
  is stronger when ready, but the snapshot is the honest backstop when local
  backend dependencies or readiness are missing.

## Failure And Recovery Posture
- A missing snapshot must degrade to recompilation or a narrower fallback path,
  not to invented memory state.
- A stale snapshot must be rejected when projection scope or fingerprint no
  longer matches the requested runtime need.
- Snapshot reuse must stay scoped. Reusing an incompatible scope is a trust bug,
  not an optimization win.
- The write path stays idempotent through `odylith_context_cache`, so repeated
  refreshes only rewrite the file when the actual payload changes.

## Validation Playbook
- `odylith context-engine --repo-root . warmup --scope reasoning`
- `odylith context-engine --repo-root . query "projection snapshot"`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_context_grounding_hardening.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-04-07: Promoted the compiler-owned fallback snapshot into a first-class Registry component so deterministic memory fallback can be governed independently from the bundle stream and the local backend. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
