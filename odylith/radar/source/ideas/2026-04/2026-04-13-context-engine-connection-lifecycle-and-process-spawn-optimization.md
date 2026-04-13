status: queued

idea_id: B-094

title: Context Engine Connection Lifecycle and Process-Spawn Optimization

date: 2026-04-13

priority: P2

commercial_value: 3

product_impact: 4

market_value: 3

impacted_parts: odylith-memory-backend,odylith-context-engine

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Every CLI invocation spawns a new Python process and opens fresh LanceDB and Tantivy connections that are closed immediately after the query. The actual query time is sub-millisecond for 2711 documents but Python startup plus import plus connection churn dominates wall-clock latency. The daemon infrastructure exists but is unused and holds no warm connections even when running. Fixing this requires careful design around multi-repo isolation and multi-session safety before implementation.

confidence: medium

founder_override: no

promoted_to_plan: 

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: 

workstream_blocks: 

related_diagram_ids: D-037

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

execution_model: standard

## Problem

Every `odylith start`, `odylith context`, and `odylith query` CLI call spawns a
new Python process, imports the full module chain, opens fresh LanceDB and
Tantivy connections, runs a sub-millisecond query against 2,711 documents, then
tears everything down and exits. The dominant wall-clock cost is Python startup
(~200ms) plus module import plus connection open/close overhead — not the query
itself.

Current architecture in `odylith_memory_backend.py`:
- `_lance_connection()` context manager: opens `lancedb.connect()`, yields, closes.
  No caching, no pooling, no reuse.
- `_open_tantivy_index()`: opens `tantivy.Index.open()` from disk every call. No
  caching.
- `exact_lookup`, `sparse_search`, `hybrid_rerank_search`: each opens and closes
  its own connections. A single `search_entities_payload` call with hybrid search
  pays 2 LanceDB connect/close cycles plus 1 Tantivy open.
- `materialize_local_backend`: rebuilds Lance tables and Tantivy index, returns
  no cached handles.

The daemon infrastructure (`odylith context-engine serve`) exists but is unused:
- Supports Unix socket, TCP, and in-process transports.
- Dispatches commands to `store.*` functions that open/close their own connections.
- Keeps no warm LanceDB or Tantivy connections even when running.
- Has idle timeout and stop-file lifecycle but no auto-start or supervisor.
- Is not started by the SessionStart hook or any other automated path.

The codebase does have process-global caching for lighter structures:
- `_PROCESS_PROJECTION_CONNECTION_CACHE` caches the in-memory
  `_ProjectionConnection` (not a real database connection) with
  `(mtime_ns, size)` invalidation.
- `_PROCESS_WARM_CACHE` caches warm-check timestamps with 300-second TTL.
- Neither pattern applies to LanceDB or Tantivy handles.

## Customer

All Odylith operator sessions — Claude Code, Codex, and CLI users. Every
grounded query pays this overhead: SessionStart hooks, context resolution,
entity lookup, workstream matching, and benchmark preflight.

## Opportunity

Reduce per-query latency from ~200ms (process spawn + connection churn) to
sub-10ms (cached connection hit) for all queries after the first in a given
process lifetime, without sacrificing the correctness guarantees of the current
open-close pattern.

## Proposed Solution

Three layers, each independently valuable:

1. **Connection caching in `odylith_memory_backend.py`**: process-global dict
   holding open LanceDB connection and Tantivy index handle, keyed by repo root,
   invalidated by backend manifest `input_fingerprint`. Same pattern as the
   existing `_PROCESS_PROJECTION_CONNECTION_CACHE`. Within a single process,
   queries after the first reuse warm connections.

2. **Daemon auto-start and warm connection holding**: have the SessionStart hook
   (or `odylith start`) ensure the daemon is alive. The daemon becomes the
   long-lived process that holds the connection cache across all sessions and all
   CLI calls for a given repo.

3. **Daemon-as-default query path**: when the daemon is running, `odylith context`
   and `odylith query` talk to it over the Unix socket instead of spawning a new
   Python process. This eliminates the ~200ms process-spawn cost entirely.

## Scope

- Connection caching with manifest-fingerprint invalidation in memory backend
- `clear_connection_cache()` called by `materialize_local_backend` after rebuild
- Daemon auto-start from SessionStart hook with idle-timeout lifecycle
- Multi-repo safety: one daemon per repo root, discovered via PID file
- Multi-session safety: concurrent sessions share the daemon; materialization
  invalidates cached connections via fingerprint check, not via cross-process signal

## Non-Goals

- Shared daemon across multiple repos (each repo gets its own)
- Cross-process connection sharing (each process caches independently; the daemon
  is the multiplier, not IPC tricks)
- Changing the LanceDB or Tantivy storage format
- Embedding-based or semantic search (stays in experiment lane per B-021)

## Risks

- **Stale connection after materialization**: if one session rebuilds Lance tables
  while another holds a cached connection, the cached reader may see stale or
  corrupt data. LanceDB uses append-only columnar storage which generally
  tolerates concurrent reads, but this needs explicit validation per version.
- **Daemon lifecycle in multi-session scenarios**: if the last session exits but
  the daemon stays alive past idle timeout, it holds resources unnecessarily.
  If a session kills the daemon while another is mid-query, the mid-query
  session falls back to direct-process mode.
- **Tantivy index segment visibility**: Tantivy readers snapshot segments at
  `Index.open()` time. A cached reader will not see new segments from
  materialization without explicit reopen. The fingerprint invalidation handles
  this, but the timing window during concurrent materialization needs testing.

## Dependencies

- B-072 (Execution Governance) — execution governance now flows through the same
  bootstrap and context dossier paths that would benefit from daemon-backed queries
- Memory backend component spec (`odylith-memory-backend/CURRENT_SPEC.md`)
- Context engine component spec (`odylith-context-engine/CURRENT_SPEC.md`)

## Success Metrics

- P50 latency for `odylith context` with warm daemon drops below 50ms
- Zero stale-connection correctness failures in concurrent session tests
- Daemon auto-starts on SessionStart, auto-stops on idle timeout
- No process leaks: `ps aux | grep odylith` shows only intentional long-lived processes

## Validation

- Unit tests for connection cache lifecycle (open, reuse, invalidate, clear)
- Integration test: concurrent materialization + query returns correct data
- Live test: `time odylith context --repo-root . execution-governance` before and after daemon
- Process leak test: start 5 sessions, close all, verify daemon exits after timeout

## Rollout

Queue now. Implementation should start with layer 1 (connection caching) as a
standalone PR since it improves within-process performance without any daemon
dependency. Layers 2 and 3 follow as separate PRs once the cache invalidation
contract is proven.

## Product View

Every grounded Odylith query pays a ~200ms process-spawn tax that dwarfs the
sub-millisecond retrieval time. As execution governance now flows through more
delivery paths and query count per session increases, the cumulative latency
becomes operator-visible. Connection caching and daemon-backed queries would
make Odylith feel instant on warm sessions while preserving the multi-repo and
multi-session correctness guarantees of the current architecture.

## Why Now

The execution engine Claude optimization (landed in this session) wired
governance into the bootstrap and context dossier delivery paths. Every session
now runs more governance queries than before. The latency tax per query is the
same, but the query count per session has increased, making the optimization
more impactful.

## Impacted Components

- `odylith-memory-backend` — connection caching, cache invalidation
- `odylith-context-engine` — daemon auto-start, query routing to daemon
- `execution-governance` — indirect beneficiary (governance queries go faster)

## Interface Changes

- New `clear_connection_cache(repo_root)` function in `odylith_memory_backend.py`
- Daemon auto-start flag in SessionStart hook or `odylith start`
- No CLI interface changes for operators

## Migration/Compatibility

- Fully backward compatible. Connection caching is additive. Daemon auto-start
  is opt-in or gated behind a flag. All existing CLI commands continue to work
  without the daemon.

## Test Strategy

- `tests/unit/runtime/test_odylith_memory_areas.py` — existing memory backend tests
- New: `tests/unit/runtime/test_memory_backend_connection_cache.py` — cache lifecycle
- New: `tests/integration/runtime/test_daemon_connection_lifecycle.py` — daemon + cache

## Open Questions

- Does LanceDB 0.30.0 guarantee safe concurrent reads during append-only writes,
  or is explicit locking needed during materialization?
- Should the daemon bind to a Unix socket in `.odylith/runtime/` (repo-scoped)
  or in a system temp directory (avoids stale sockets on unclean shutdown)?
- Should connection caching be opt-out via an environment variable for debugging?
