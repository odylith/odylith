# Odylith Context Engine
Last updated: 2026-04-17


Last updated (UTC): 2026-04-17

## Purpose
Odylith Context Engine is the deterministic local grounding runtime for the
governance engine. It compiles repo truth into a reusable read model, exposes
packet-oriented CLI reads for coding agents and surfaces, manages session
claims, and optionally materializes faster local and remote retrieval layers.

## Scope And Non-Goals
### The Context Engine owns
- Projection compilation from tracked markdown, JSON, code, tests, and runtime
  metadata.
- Local daemon and thin-client command execution.
- Session-level grounding packets such as `impact`, `architecture`,
  `governance-slice`, `session-brief`, and `bootstrap-session`.
- Optional local LanceDB + Tantivy materialization and optional Vespa sync.
- Runtime optimization and evaluation snapshots derived from recent packets.
- Structured turn-intake normalization for `turn_context`, lane-fenced
  `target_resolution`, and `presentation_policy` fields carried through packet
  assembly and compaction.
- Compact packet summaries consumed by the visible intervention value engine.
  The Context Engine supplies local source evidence and anchors; it does not
  choose visible Odylith block labels or selector thresholds.

### The Context Engine does not own
- Authoritative repo truth. It compiles truth; it does not replace it.
- Surface rendering policy.
- Delegation routing policy itself. It only provides grounding and packet data
  that router/orchestrator logic can consume.
- Admissibility or next-action control. It provides grounded truth and packets,
  but [Execution Engine](../execution-engine/CURRENT_SPEC.md) decides
  which next move is admissible.
- Historical execution component identifiers. Context packets must carry
  `execution-engine` when the packet addresses the Execution Engine boundary;
  stale execution identifiers fail closed rather than being translated.
- Live intervention rendering policy. The Governance Intervention Engine
  consumes Context Engine packet summaries as one evidence source inside the
  proposition value engine.

## Developer Mental Model
- `src/odylith/runtime/context_engine/odylith_context_engine.py` is the public
  CLI and daemon entrypoint.
- `src/odylith/runtime/context_engine/odylith_context_engine_store.py` is the
  core compiler and packet engine.
- The compiler layer is local-first and disposable. Every runtime artifact
  under `.odylith/runtime/` is derived and safe to rebuild.
- On supported managed-runtime installs, the fast local memory backend ships as
  a managed context-engine pack that is installed by default as part of the
  full-stack Odylith runtime, even though the base runtime and memory overlay
  travel as separate release assets.
- The first-turn intake path is lane-aware: consumer turns may ground from
  visible text and anchors without returning Odylith-owned write targets, while
  maintainer mode can keep the same pipeline writable in the Odylith product
  repo.
- Packet builders and budgeting helpers are explicit modules, not incidental
  string assembly:
  `tooling_context_packet_builder.py`,
  `tooling_context_retrieval.py`,
  `tooling_context_routing.py`,
  `tooling_context_budgeting.py`, and
  `tooling_guidance_catalog.py`.
- Benchmark and runtime guidance memory resolves from the canonical manifest
  `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`, with legacy
  fallback only for backward compatibility and family hints flowing into packet
  finalization plus retrieval.
- Registry treats the memory substrate as a small family of governed sibling
  components rather than one hidden blob:
  [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md),
  [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md),
  [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md),
  [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md), and
  [Odylith Memory Contracts](../odylith-memory-contracts/CURRENT_SPEC.md).
  The Context Engine orchestrates them; it does not erase their boundaries.

## Public Command Surface
Public entrypoint: `odylith context-engine`

## Execution Engine Handshake
- Context Engine owns the evidence cone: canonical component identity,
  workstream and plan grounding, packet kind, route readiness, turn context,
  target resolution, presentation policy, and recommended validation.
- Execution Engine owns the action contract: admissibility outcome, execution
  mode, truthful next move, closure posture, wait/resume semantics, validation
  archetype, host profile, and delegation or parallelism guards.
- The handoff key for this component boundary is strictly `execution-engine`.
  Context Engine registry detail lookup, packet readiness, and benchmark packet
  construction must not resolve stale execution identifiers into the canonical
  component.
  This fail-closed behavior prevents old names from silently producing
  route-ready packets.
- The stable `execution_engine_handshake` packet shape is versioned as `v1`
  and contains `component_id`, `canonical_component_id`, `identity_status`,
  packet kind and state, expanded packet quality, `turn_context`,
  `target_resolution`, `presentation_policy`, recommended validation, and
  route readiness.
- Packet builders call
  `src/odylith/runtime/context_engine/execution_engine_handshake.py` to attach
  that shape and build or reuse one compact Execution Engine snapshot. Packet
  summaries, bootstrap packets, hot-path packets, context dossiers, and
  runtime surfaces should consume that shared snapshot instead of locally
  deriving policy posture.
- Snapshot cost diagnostics are intentionally lightweight and comparative:
  snapshot duration, snapshot token estimate, runtime-contract token estimate,
  handshake token estimate, total payload token estimate, reuse status, and
  handshake version travel with the compact summary for benchmark and
  latency-budget analysis.

### Projection and daemon lifecycle
- `warmup`
  Build or refresh local projections for `default`, `reasoning`, or `full`
  scope.
- `serve`
  Keep projections warm continuously using `watchman`, `watchdog`,
  `git-fsmonitor`, or polling.
- `status`
  Show daemon, watcher, and store posture.
- `stop`
  Stop a running daemon loop.
- `doctor`
  Report watcher readiness and optionally bootstrap the `git fsmonitor`
  fallback.

### Packet and read APIs
- `query`
  Search the local projection store and report when a raw repo scan is still
  recommended. Release selectors such as `current release`, `next release`,
  `release:<id>`, exact version, exact tag, and unique exact release names
  resolve through the same compiled projection truth.
- `surface-read`
  Return pre-shaped payloads for dashboard and surface consumers.
- `context`
  Resolve a single entity or path into a dossier, including first-class
  release entities.
- `impact`
  Build a path-scoped implementation impact packet.
- `architecture`
  Build a topology and diagram-watch audit.
- `governance-slice`
  Build a compact governance and delivery-truth packet.
- `session-brief`
  Build one deterministic session dossier and refresh the session heartbeat.
- `bootstrap-session`
  Build a compact fresh-session bootstrap packet with docs, commands, and test
  recommendations.
  Both session packet forms carry structured turn context, lane-fenced target
  resolution, and presentation policy.

### Snapshot, switch, and remote operations
- `benchmark`
  Run local Odylith ON/OFF or cache-profile comparisons.
- `memory-snapshot`
  Report the current derived memory and retrieval substrate, including explicit
  memory-area posture plus durable judgment-memory posture for what is live,
  partial, cold, or still planned.
- `odylith-switch`
  Inspect or persist the local Odylith ablation switch.
- `odylith-remote-sync`
  Sync the current evidence set to an optional Vespa service.

Operational guidance lives in
[CONTEXT_ENGINE_OPERATIONS.md](../../../../runtime/CONTEXT_ENGINE_OPERATIONS.md).

## Module Ownership
- `odylith_context_engine.py`
  CLI parsing, client mode selection, daemon transport, watcher runtime, and
  status/doctor reporting.
- `odylith_context_engine_store.py`
  Projection compilation, packet assembly, session state, runtime timing,
  optimization snapshots, evaluation snapshots, and fallback behavior.
- `odylith_context_engine_projection_query_runtime.py`
  Query-facing projection composition and export wiring across entity,
  backlog, bug, and registry read models.
- `odylith_context_engine_projection_entity_runtime.py`
  Exact entity resolution, release selector routing, and dossier shaping that
  turns compiled projection truth into packet-safe context payloads.
- `odylith_context_engine_projection_backlog_runtime.py`
  Backlog, plan, and bug projection reads plus workstream detail loading.
- `odylith_context_engine_projection_registry_runtime.py`
  Component index, registry snapshot, and registry-detail projection reads.
- `odylith_context_engine_packet_summary_runtime.py`
  Packet-summary extraction and compact bootstrap-packet readback, including
  turn-context, target-resolution, and presentation-policy carry-through.
- `odylith_context_engine_packet_session_runtime.py`
  Session-brief and bootstrap packet assembly, including first-turn intake and
  lane-aware target resolution.
- `odylith_context_engine_packet_architecture_runtime.py`
  Architecture-audit packet assembly.
- `odylith_context_engine_packet_adaptive_runtime.py`
  Adaptive packet escalation and daemon-reuse packet flows.
- `odylith_context_engine_hot_path_packet_core_runtime.py`
  Compact packet-quality, routing, and execution-profile shaping for hot-path
  packets.
- `odylith_context_engine_hot_path_packet_bootstrap_runtime.py`
  Governance and proof-aware hot-path bootstrap packet compaction.
- `odylith_context_engine_hot_path_packet_finalize_runtime.py`
  Final compact packet shaping, prompt trimming, and workstream context
  compaction.
- `tooling_context_packet_builder.py`
  Shared packet finalization and packet metrics.
- `tooling_context_retrieval.py`
  Evidence retrieval and miss-recovery shaping.
- `tooling_context_routing.py`
  Ambiguity handling and routing readiness heuristics.
- `tooling_context_budgeting.py`
  Packet trimming and budget policy.
- `tooling_guidance_catalog.py`
  Compiled guidance-catalog caching.
- `src/odylith/runtime/memory/odylith_projection_bundle.py`
  Compiler-owned JSONL bundle contract, governed by
  [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md).
- `src/odylith/runtime/memory/odylith_projection_snapshot.py`
  Compiler-owned JSON snapshot contract, governed by
  [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md).
- `src/odylith/runtime/memory/odylith_memory_backend.py`
  Local retrieval substrate owned by
  [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md).
- `src/odylith/runtime/memory/odylith_remote_retrieval.py`
  Optional Vespa-backed shared retrieval augmentation, governed by
  [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md).
- `src/odylith/runtime/memory/tooling_memory_contracts.py`
  Shared packet and evidence-pack compaction contract, governed by
  [Odylith Memory Contracts](../odylith-memory-contracts/CURRENT_SPEC.md).

## Guidance Catalog Contract

- The canonical tracked manifest path is
  `odylith/agents-guidelines/indexable-guidance-chunks.v1.json`.
- Each guidance chunk must declare source path, task families, and path or
  component affinity so benchmark slices can retrieve guidance without broad
  generic spillover.
- The compiled catalog must retain manifest path, source-doc count, and
  task-family coverage so benchmark preflight can fail closed when guidance is
  missing instead of silently running zero-guidance proof.

## Benchmark Boundedness Contract

- Benchmark-facing impact, governance-slice, session-brief, and
  bootstrap-session packets must pass family hints through finalization so
  retrieval and packet compaction can stay family-aware.
- Session-brief and bootstrap-session packets must preserve structured
  `turn_context`, lane-fenced `target_resolution`, and `presentation_policy`
  so the router and chatter layers consume the same truth as the context
  engine.
- On already-grounded proof slices, `required_paths` are authoritative and
  family-aware ceilings must suppress support-doc spillover and miss recovery
  before prompt rendering.
- Families such as `component_governance`, `compass_brief_freshness`,
  `consumer_profile_compatibility`, `daemon_security`, `cross_file_feature`,
  `exact_anchor_recall`, `explicit_workstream`,
  `orchestration_feedback`, and `orchestration_intelligence` must fail closed
  on unrelated support-doc expansion unless a required path or focused
  validator points there directly.
- Candidate ordering for docs, tests, and commands must stay deterministic so
  warm and cold cache posture change latency, not first-pass truth selection.

## Persistent State And Runtime Files
### Daemon and watcher files
- `.odylith/runtime/odylith-context-engine.pid`
- `.odylith/runtime/odylith-context-engine.stop`
- `.odylith/runtime/odylith-context-engine.sock`
  Socket metadata may describe a Unix socket, TCP loopback transport, or
  in-process fallback.
- `.odylith/runtime/odylith-context-engine-daemon-usage.v1.json`
- `.odylith/runtime/odylith-proof-surfaces.v1.json`

### Compiler outputs
- `.odylith/runtime/odylith-compiler/projection-manifest.v1.json`
- `.odylith/runtime/odylith-compiler/documents.v1.jsonl`
- `.odylith/runtime/odylith-compiler/edges.v1.jsonl`
- `.odylith/runtime/odylith-compiler/projection-snapshot.v1.json`

### Local memory backend
- `.odylith/runtime/odylith-memory/`
- `.odylith/runtime/odylith-memory/odylith-memory-backend.v1.json`
- `.odylith/runtime/odylith-memory/odylith-judgment-memory.v1.json`
- `.odylith/runtime/odylith-memory/lance/`
- `.odylith/runtime/odylith-memory/tantivy/`

### Optional remote sync
- `.odylith/runtime/odylith-vespa-sync.v1.json`
- `.odylith/runtime/odylith-vespa-sync-manifest.v1.json`

### Session and optimization state
- `.odylith/runtime/sessions/`
  Active or recent session claim records.
- `.odylith/runtime/bootstraps/`
  Recent bootstrap packets.
- `.odylith/runtime/odylith-benchmarks/`
  Benchmark history and latest reports.

## Turn Intake And Lane Fencing
- The context engine's first-turn intake path should preserve structured
  `turn_context` and quoted visible text separately from semantic intent so
  consumer-lane packets can resolve diagnostic anchors without exposing
  Odylith-owned writable targets.
- Maintainer-authorized turns in the Odylith product repo may reuse the same
  intake and resolution pipeline while keeping Odylith-owned targets writable
  when lane policy permits mutations.

## Core Read Models
### [Odylith Projection Bundle](../odylith-projection-bundle/CURRENT_SPEC.md)
`odylith_projection_bundle.py` writes a bundle manifest plus two JSONL streams:
- `documents.v1.jsonl`
  Entity and evidence documents suitable for lexical or vector retrieval.
- `edges.v1.jsonl`
  Typed graph relationships between entities and artifacts.

The manifest records version, compile time, scope, input fingerprint,
projection fingerprint, and the relative paths to the document and edge files.

### [Odylith Projection Snapshot](../odylith-projection-snapshot/CURRENT_SPEC.md)
`odylith_projection_snapshot.py` writes one JSON snapshot containing:
- version and compile metadata
- projection fingerprint and input fingerprint
- projection scope
- updated projection names
- the fully materialized projection tables
- projection-state metadata

This is the deterministic fallback read model when optional local memory
dependencies are absent or when the managed context-engine pack is missing or
unhealthy.

### [Odylith Memory Backend](../odylith-memory-backend/CURRENT_SPEC.md)
`odylith_memory_backend.py` is optional in the code path and activates only
when `lancedb`, `pyarrow`, and `tantivy` are available. In the supported
managed-runtime lane, those dependencies are shipped through the managed
context-engine pack and installed by default so first install and normal pinned
upgrade still realize the full local-memory experience. The shared local memory
root now stores:
- a Lance table of document records
- a Lance table of edge records
- a Tantivy sparse index
- a local backend manifest describing provider, storage, sparse recall mode,
  counts, and dependency availability
- a `judgment_memory.v1` snapshot that retains compact decisions,
  workspace/actor continuity, contradictions, freshness, failures, outcomes,
  onboarding, and provenance

The backend is derived from the compiler bundle plus compact runtime evidence,
not from direct repo scans.

### [Odylith Remote Retrieval](../odylith-remote-retrieval/CURRENT_SPEC.md)
`odylith_remote_retrieval.py` is optional and configured via environment:
- `ODYLITH_VESPA_URL`
- `ODYLITH_VESPA_SCHEMA`
- `ODYLITH_VESPA_NAMESPACE`
- `ODYLITH_VESPA_MODE`
- `ODYLITH_VESPA_RANK_PROFILE`
- `ODYLITH_VESPA_TIMEOUT_SECONDS`
- `ODYLITH_VESPA_TOKEN`
- `ODYLITH_VESPA_CLIENT_CERT`
- `ODYLITH_VESPA_CLIENT_KEY`
- `ODYLITH_VESPA_PRUNE_MISSING`

Modes are effectively disabled unless a base URL is present and the mode is
`augment` or `remote_only`.

## Daemon And Watcher Architecture
### Client modes
- `auto`
  Use the daemon-backed client when available, otherwise fall back locally.
- `local`
  Bypass the daemon.
- `daemon`
  Force daemon-backed execution.

### Transport fallback
The daemon server attempts transport in this order:
1. Unix domain socket
2. Loopback TCP socket
3. In-process registry fallback

This keeps the daemon usable even when Unix sockets are unavailable.

Non-in-process daemon reuse is a private local transport only:
- Unix socket and TCP transport artifacts are local runtime state, not public
  control endpoints.
- TCP transport hints are accepted only for loopback hosts and a live daemon
  owner pid.
- Socket and TCP requests carry a per-daemon auth token from
  `.odylith/runtime/odylith-context-engine-daemon.json`.
- Stale pid, socket, or metadata artifacts must fail closed instead of being
  trusted as healthy daemon proof.

### Watcher backends
Auto mode prefers the strongest available watcher backend:
1. `watchman`
2. `watchdog`
3. `git-fsmonitor`
4. `poll`

`doctor --bootstrap-watcher` can bootstrap `git fsmonitor` when it is the best
available local-assisted fallback.
`watchdog` is the default in-runtime filesystem watcher fallback after
`watchman` on managed installs that bundle it. Linux managed feature packs do
not require `watchdog`; when it is absent, Odylith still falls back to
`git-fsmonitor` and then polling without changing the full-stack install
contract.
Surface watchers such as Compass should consume change notifications before
they invent their own timers: the daemon now exposes a blocking
`wait-projection-change` request keyed to the current projection fingerprint,
and long-running local watch commands may reuse the same watcher stack directly
when the daemon is absent. Tight heartbeat polling is not the intended product
contract; coarse polling exists only as the last fallback on machines with no
real watcher backend.

## Packet Families And Control Flow
### Governance slice
`build_governance_slice(...)` composes:
- guidance-catalog summary
- impact packet
- optional architecture audit when topology-sensitive work is detected
- governance obligations, validation commands, and surface references

If no viable seeds exist, it fails open with `full_scan_recommended: true`
instead of pretending to have a grounded answer.

### Impact packet
`build_impact_report(...)` is the primary path-scoped implementation packet.
It resolves path scope, warms reasoning projections, selects candidate
workstreams, components, diagrams, docs, recommended commands, and recommended
tests, then finalizes the result through the shared packet builder.

Typical degraded states are:
- no grounded paths
- working-tree scope degraded
- runtime unavailable

In those cases the packet includes fallback scan guidance.

### Architecture audit
`build_architecture_audit(...)` is the topology-sensitive companion packet.
It resolves changed paths against architecture bundles, domain coverage,
diagram watch gaps, contract touchpoints, authority graph edges, and benchmark
alignment. It is separate from the impact packet because not every coding slice
needs full topology analysis.

### Session brief
`build_session_brief(...)` combines:
- path-scope resolution
- impact packet reuse or regeneration
- workstream selection
- session-state registration or refresh
- conflict detection against other active sessions
- compact workstream context

The session state records claimed paths, generated surfaces, working-tree
scope, branch/head identity, intent, claim mode, and lease duration.

### Session bootstrap
`build_session_bootstrap(...)` builds on `session_brief` and adds:
- relevant document shortlist
- recommended command shortlist
- recommended test shortlist
- recent runtime timing and state when available

This is the packet used to give a coding agent a compact fresh-session handoff.

## Optimization And Evaluation Snapshots
### Optimization snapshot
`load_runtime_optimization_snapshot(...)` summarizes recent packet behavior:
- estimated bytes and tokens
- utility score
- density and evidence-diversity metrics
- route-ready and native-spawn-ready rates
- narrowing and miss-recovery rates
- deep-reasoning readiness
- orchestration adoption and timing posture

This is runtime feedback for tuning, not authoritative truth.

### Evaluation snapshot
`load_runtime_evaluation_snapshot(...)` compares recent bootstrap packets
against the benchmark corpus in
`odylith/runtime/source/optimization-evaluation-corpus.v1.json`.
It reports coverage rate, satisfaction rate, drift, unmatched cases, family
distribution, and recommendations when the corpus is seeded but recent packet
evidence is missing or drifting.

## What Developers Need To Change Together
- New projection table:
  update compilation in `odylith_context_engine_store.py`, include it in the
  snapshot or bundle if it is part of the public runtime contract, and then
  update any packets that consume it.
- Release projection changes must evolve together:
  - compiler/runtime tables and projection fingerprints
  - exact-resolution aliases for `context` and `query`
  - memory-backend release documents
  - dependent surface or packet payloads that use active release labels
- New packet family:
  add the packet builder logic, define its budget and trim behavior, and make
  the degraded or full-scan fallback explicit.
- New retrieval capability:
  extend the compiler bundle first, then the optional local or remote backend.
- New session behavior:
  update session registration, conflict detection, and bootstrap/brief payloads
  together so packet consumers do not drift.

## Failure And Recovery Posture
- Projection invalidation is fingerprint-driven and safe to rebuild.
- Missing optional memory dependencies should fall back to the compiler
  snapshot instead of breaking reads.
- Missing remote retrieval config should disable augmentation cleanly.
- Missing grounded paths or ambiguous selection should return fallback scan
  guidance instead of a false-positive route recommendation.
- Watcher failures should degrade to a weaker watcher or polling.
- If a consumer still needs fresh local truth after watchers degrade all the
  way to polling, the expensive work must remain outside the detection loop:
  detect cheaply, rebuild locally only on fingerprint change, and keep provider
  narration off the blocking path.
- Repair and reset-local-state flows must stop a live daemon before deleting
  runtime files so recovery does not orphan background processes.
- If Odylith is disabled through `odylith-switch`, snapshot APIs should return
  disabled posture instead of stale enabled assumptions.

## Debugging Checklist
- `odylith context-engine --repo-root . status`
  Check daemon, watcher backend, and restart recommendations.
- `odylith context-engine --repo-root . doctor`
  Check watcher support and bootstrap recommendation.
- `odylith context-engine --repo-root . warmup --scope full --force`
  Rebuild projections.
- `odylith context-engine --repo-root . memory-snapshot`
  Inspect compiler, local backend, remote sync posture, durable judgment
  memory, and the named memory-area gaps Odylith still does not retain.
- `odylith context-engine --repo-root . bootstrap-session --working-tree --working-tree-scope session --session-id <id>`
  Inspect the actual packet a coding agent would consume.

## Validation Playbook
### Runtime
- `odylith context-engine --repo-root . warmup --scope full --force`
- `odylith context-engine --repo-root . status`
- `odylith context-engine --repo-root . doctor`
- `pytest -q tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py`
- `python -m pytest -q tests/unit/runtime/test_tooling_guidance_catalog.py tests/unit/runtime/test_tooling_context_retrieval_guidance.py`
- `odylith context-engine --repo-root . benchmark --limit 5`
- `odylith sync --repo-root . --check-only`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-04-16 · Implementation:** Context Engine and Execution Engine alignment hardened stale snapshot handling across packet summaries, router assessment, remediator execution, and benchmark proof with fail-closed canonical execution-engine identity checks; runtime, integration, registry, backlog, atlas, sync, and diff hygiene validation passed.
  - Scope: B-099
  - Evidence: src/odylith/runtime/context_engine/execution_engine_handshake.py, src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py +3 more
- **2026-04-16 · Implementation:** Hardened Context Engine to Execution Engine alignment with canonical identity propagation, identity-first guard blocking, benchmark identity gates, and refreshed release-proof surfaces.
  - Scope: B-099
  - Evidence: src/odylith/runtime/context_engine/execution_engine_handshake.py, src/odylith/runtime/execution_engine/runtime_lane_policy.py
- **2026-04-16 · Implementation:** Hard-cut Context Engine and Execution Engine alignment Wave 1 to canonical execution-engine identity; focused execution tests, broader runtime benchmark tests, registry/backlog validators, sync check, Atlas freshness, and diff check pass.
  - Scope: B-099, B-100
  - Evidence: odylith/radar/source/programs/B-099.execution-waves.v1.json, odylith/registry/source/components/execution-engine/CURRENT_SPEC.md +2 more
- **2026-03-23 · Decision:** Successor created: B-280 reopens B-279 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md +1 more
- **2026-03-23 · Decision:** Successor created: B-279 reopens B-278 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/dashboard/CURRENT_SPEC.md +3 more
- **2026-03-18 · Decision:** Successor created: B-220 reopens B-219 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Promoted the public repo runtime, memory, and packetization stack into Odylith's own governed component inventory so the product can ground and inspect itself without consumer-owned specs. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-03-28: Added durable judgment memory, persisted it beside the local memory backend, and promoted the memory backend into a first-class Registry component so governed slice continuity can survive across sessions without polluting hot-path packets. (Plan: [B-010](odylith/radar/radar.html?view=plan&workstream=B-010))
- 2026-04-05: Restored canonical benchmark guidance memory, passed family hints through packet finalization into retrieval, and documented the fail-closed boundedness contract that keeps weak-family proof slices deterministic across warm and cold cache posture. (Plan: [B-038](odylith/radar/radar.html?view=plan&workstream=B-038))
- 2026-04-07: Promoted the hidden memory-substrate seams into governed sibling components so projection bundle, projection snapshot, remote retrieval, and packet contracts become explicit Registry truth instead of broad Context Engine footnotes. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
- 2026-04-08: Added first-class release entities and selector resolution to the projection model so `context`, `query`, and governed read surfaces can resolve release ids, aliases, versions, tags, and unique exact names from one repo-local contract. (Plan: [B-063](odylith/radar/radar.html?view=plan&workstream=B-063))
- 2026-04-09: Clarified the product boundary that Context Engine grounds repo truth and packets, while Execution Engine owns admissibility and next-action control. (Plan: [B-072](odylith/radar/radar.html?view=plan&workstream=B-072))
- 2026-04-10: Added structured turn-intake carry-through so session packets can preserve `turn_context`, lane-fenced target resolution, and presentation policy across consumer and maintainer lanes. (Plan: [B-082](odylith/radar/radar.html?view=plan&workstream=B-082))
- 2026-04-16: Added the Context Engine and Execution Engine alignment program and hard-cut the handoff to canonical `execution-engine` identity so stale execution identifiers fail closed before packet route readiness. (Plan: [B-099](odylith/radar/radar.html?view=plan&workstream=B-099), [B-100](odylith/radar/radar.html?view=plan&workstream=B-100))
- 2026-04-16: Added handshake `v1`, shared compact snapshot reuse, Execution Engine cost diagnostics, and Codex/Claude semantic parity proof for the Context Engine to Execution Engine boundary. (Plan: [B-101](odylith/radar/radar.html?view=plan&workstream=B-101), [B-102](odylith/radar/radar.html?view=plan&workstream=B-102), [B-103](odylith/radar/radar.html?view=plan&workstream=B-103))
