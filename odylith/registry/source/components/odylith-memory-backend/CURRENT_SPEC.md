# Odylith Memory Backend

## Odylith Discipline Contract
- Memory Backend stores and replays compact discipline practice events without
  widening into transcript archives. Session memory may nudge a current turn;
  durable priors require validation, benchmark evidence, or Tribunal doctrine.
- Retention classes include `hot_recent`, `durable_practice`,
  `casebook_failure`, `benchmark_pressure`, `tribunal_doctrine_candidate`, and
  `noise_suppressed`, with decay and suppression preserved.
Last updated: 2026-04-13


Last updated (UTC): 2026-04-13

## Purpose
Odylith Memory Backend is the local-first derived memory substrate that stores
fast retrieval state and compact durable judgment memory for the Odylith
Context Engine.

## Scope And Non-Goals
### Odylith Memory Backend owns
- the local LanceDB + Tantivy retrieval materialization
- backend manifests and readiness evidence under `.odylith/runtime/odylith-memory/`
- the durable `judgment_memory.v1` snapshot stored beside the retrieval files
- the local-first memory trust boundary: derived, rebuildable, and never
  authoritative over tracked repo truth

### Odylith Memory Backend does not own
- tracked backlog, plan, bug, component, or diagram truth
- the compiler-owned projection bundle or projection snapshot contracts
- the optional remote retrieval sync lane
- shared packet and evidence-pack compaction helpers
- packet assembly, routing, or orchestration policy
- hosted or remote memory as the primary authority

## Developer Mental Model
- `src/odylith/runtime/memory/odylith_memory_backend.py` owns the retrieval
  backend contract and its runtime files.
- [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md)
  and [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md)
  are sibling compiler components that feed or backstop the backend; they are
  not owned by the backend itself.
- [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md) is a
  sibling opt-in augmentation layer, not part of the local backend's primary
  authority.
- [Odylith Memory Contracts](../odylith-memory-contracts/CURRENT_SPEC.md)
  shapes packet-safe memory outputs and provenance, but it does not own
  retrieval state.
- `src/odylith/runtime/context_engine/odylith_context_engine_store.py` may
  compile judgment memory, but the resulting artifact lives inside the same
  local memory root because it is part of one local-first memory substrate.
- Everything under `.odylith/runtime/odylith-memory/` is derived and safe to
  rebuild from repo truth plus recent runtime evidence.
- Durable judgment memory must stay compact. It is for remembered decisions,
  contradictions, failures, outcomes, onboarding state, and provenance, not
  raw thread retention.

## Runtime Contract
### Runtime inputs
- `.odylith/runtime/odylith-compiler/projection-manifest.v1.json`
- `.odylith/runtime/odylith-compiler/documents.v1.jsonl`
- `.odylith/runtime/odylith-compiler/edges.v1.jsonl`
- `.odylith/runtime/odylith-context-engine-daemon-usage.v1.json`
- `.odylith/runtime/sessions/`
- `.odylith/runtime/bootstraps/`
- `.odylith/runtime/odylith-benchmarks/latest.v1.json`
- tracked repo truth under `odylith/radar/`, `odylith/technical-plans/`,
  `odylith/casebook/bugs/`, `odylith/atlas/source/`, and
  `odylith/registry/source/`

### Generated artifacts
- `.odylith/runtime/odylith-memory/odylith-memory-backend.v1.json`
- `.odylith/runtime/odylith-memory/odylith-judgment-memory.v1.json`
- `.odylith/runtime/odylith-memory/lance/`
- `.odylith/runtime/odylith-memory/tantivy/`

### Owning modules
- `src/odylith/runtime/memory/odylith_memory_backend.py`
  Retrieval backend materialization, manifest generation, and runtime status.
- `src/odylith/runtime/context_engine/odylith_context_engine_store.py`
  Durable judgment-memory compilation and persistence into the memory root.

## Persistent State And Runtime Files
- `.odylith/runtime/odylith-memory/`
- `.odylith/runtime/odylith-memory/odylith-memory-backend.v1.json`
- `.odylith/runtime/odylith-memory/odylith-judgment-memory.v1.json`
- `.odylith/runtime/odylith-memory/lance/`
- `.odylith/runtime/odylith-memory/tantivy/`

## Local Memory Posture
- Repo truth remains authoritative.
- Retrieval state and judgment memory are derived from that truth plus runtime
  evidence.
- The backend may remember starter-slice continuity, proof outcomes, and
  recent contradictions, but it must not silently override tracked product
  records.
- Multiline Casebook bug-index rows must still normalize into open bug
  pressure so negative memory does not silently lose unresolved risk.
- Starter-slice continuity may be inferred from the shell welcome state after
  the welcome card hides, but inferred continuity must stay labeled as
  inferred.
- Missing dependencies must fail over to weaker local retrieval, not to
  invented state.

## Durable Judgment Memory Contract
`judgment_memory.v1` must expose compact areas for:
- decision memory
- workspace and actor memory
- contradiction memory
- freshness memory
- negative memory
- outcome memory
- onboarding memory
- provenance memory

Each area must carry:
- `state`
- `summary`
- `freshness`
- `items`
- `provenance`

The contract is intentionally compact so shell and CLI readouts can surface it
without polluting the coding hot path.

`judgment_memory.v1` and `memory_areas.v1` must each expose:
- `status`
- `headline`
- compact counts and gaps that agree with the retained area posture

## Benchmark Proof Posture

- The current published benchmark posture is local-memory-first: LanceDB plus
  Tantivy are the active retrieval substrate and Vespa remains intentionally
  disabled unless a run explicitly reports otherwise.
- Benchmark warm preflight requires the local memory backend to be ready and
  benchmark guidance coverage to be non-empty before proof runs.
- `ODYLITH_HYBRID_RERANK` remains a weak-family experiment lane only. It stays
  off by default until it improves precision, hallucination control, and
  warm/cold consistency without harming recall or validation.

## Connection Lifecycle

The current connection model is stateless open-close: every `exact_lookup`,
`sparse_search`, and `hybrid_rerank_search` call opens a fresh
`lancedb.connect()` and `tantivy.Index.open()`, runs the query, and tears down.
No connection pooling, no caching, no singleton. This is correct for
multi-repo and multi-session safety but incurs per-query overhead dominated by
Python process startup (~200ms) rather than the LanceDB/Tantivy open itself
(~5-10ms) or the query (~sub-ms for 2,711 documents).

The daemon infrastructure (`odylith context-engine serve`) exists and supports
Unix socket, TCP, and in-process transports, but it holds no warm connections
even when running — each dispatched command opens and closes its own database
handles independently.

Connection caching with manifest-fingerprint invalidation is planned as
[B-094](odylith/radar/radar.html?view=plan&workstream=B-094) to allow
within-process reuse and daemon-held warm connections without sacrificing the
isolation guarantees of the current model.

## Failure And Recovery Posture
- Missing `lancedb`, `pyarrow`, or `tantivy` must degrade retrieval cleanly to
  the compiler snapshot path.
- Missing benchmark, session, or onboarding artifacts must mark the relevant
  judgment-memory areas as cold or partial instead of inventing certainty.
- Missing or malformed bug-index rows must fail open into weaker parsing rather
  than silently dropping unresolved risk from negative memory.
- Deleting `.odylith/runtime/odylith-memory/` is allowed; the next runtime
  warmup or status read must be able to rebuild it.

## Validation Playbook
- `odylith context-engine --repo-root . status`
- `odylith context-engine --repo-root . memory-snapshot`
- `odylith context-engine --repo-root . benchmark --limit 5`
- `odylith sync --repo-root . --check-only`
- `pytest -q tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_odylith_runtime_surface_summary.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- No synchronized requirement or contract signals yet.
<!-- registry-requirements:end -->

## Feature History
- 2026-03-28: Promoted the local memory backend into a first-class Registry component and added durable judgment memory beside the retrieval substrate. (Plan: [B-010](odylith/radar/radar.html?view=plan&workstream=B-010))
- 2026-03-29: Tightened memory coherence so open bug pressure survives multiline Casebook rows, contradiction memory retains cross-surface risk, onboarding continuity survives a hidden welcome state, and top-level memory readouts expose one coherent headline/status. (Plan: [B-011](odylith/radar/radar.html?view=plan&workstream=B-011))
- 2026-04-05: Documented the current local-memory-first benchmark posture, making LanceDB plus Tantivy the explicit proof substrate and keeping hybrid rerank plus Vespa in the experiment lane until they show no-regression gains. (Plan: [B-021](odylith/radar/radar.html?view=plan&workstream=B-021))
- 2026-04-07: Narrowed the backend's Registry boundary to the actual local backend plus judgment-memory contract and promoted the surrounding projection, remote, and packet-contract seams into sibling first-class components. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
- 2026-04-13: Documented the stateless open-close connection lifecycle, the unused daemon warm-connection gap, and the planned connection-caching optimization with manifest-fingerprint invalidation. (Workstream: [B-094](odylith/radar/radar.html?view=plan&workstream=B-094))
