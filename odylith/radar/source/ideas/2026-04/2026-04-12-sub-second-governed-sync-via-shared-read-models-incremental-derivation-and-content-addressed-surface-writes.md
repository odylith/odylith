status: implementation

idea_id: B-091

title: Sub-Second Governed Sync via Shared Read Models, Incremental Derivation, and Content-Addressed Surface Writes

date: 2026-04-12

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: odylith sync execution engine, delivery intelligence refresh, registry report reuse, Compass backlog-row reuse, dashboard surface writes, heartbeat pacing, and path-normalization hot paths

sizing: L

complexity: VeryHigh

ordering_score: 87

ordering_rationale: Full governed sync is paying for repeated read-model reconstruction, path canonicalization, and cross-surface recomputation even when the repo state is already known. This slice should replace that shared-nothing execution posture with one session-hoisted derivation model that preserves the same governance outcomes while making warm syncs genuinely cheap.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-12-governed-sync-shared-read-models-incremental-derivation-and-content-addressed-writes.md

execution_model: standard

workstream_type: child

workstream_parent: B-025

workstream_children: 

workstream_depends_on: B-080,B-086

workstream_blocks: 

related_diagram_ids: D-005,D-009,D-036

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

## Problem
`odylith sync` is still paying for a shared-nothing execution posture even when
the runtime fast path already has one Python process and one known repo root.
Validators and renderers keep re-discovering the same consumer profile, repo
root, path canonicalization, idea-spec corpus, Registry report, and delivery
inputs instead of reusing one read model for the duration of the run.

That wasted work now dominates the honest sync cost. Profiling shows the core
governed outputs are not intrinsically a thirty-second job; the majority of the
latency is repeated `Path.resolve()` chains, repo-root inference walks,
duplicate idea parsing, repeated component-Registry report construction, and
unchanged surface writes that still dirty the tree.

As long as sync keeps behaving like twenty adjacent tools that all boot from
zero, Odylith cannot make warm incremental sync genuinely cheap without either
weakening truthfulness or relying on hand-wavy benchmark claims.

## Customer
- Primary: Odylith maintainers iterating on governed product code who need
  warm sync to stay in the same feedback loop as code/test/edit.
- Secondary: operators and reviewers who need no-op or narrowly-scoped sync to
  stop rewriting unchanged generated surfaces and polluting git status.
- Tertiary: future daemon and evaluation work that needs one clean derivation
  model instead of ad hoc per-step caches.

## Opportunity
If sync owns one shared read model per run, then the product can preserve the
same Radar, Registry, Atlas, Compass, Casebook, and shell outcomes while
turning repeated discovery into reusable state. That changes the optimization
story from "micro-cache one more helper" to "compute each governed fact once,
then derive from it."

The same architecture also unlocks clean no-op behavior. When a render or sync
step produces the same bytes for the same content fingerprints, Odylith should
not rewrite the file, should not trigger downstream invalidation, and should
not present fake churn as meaningful work.

## Proposed Solution
- introduce one sync-scoped shared session that hoists repo root, consumer
  profile, truth-root resolution, canonical path tokens, parsed idea specs, and
  Registry report reuse
- make shared projection/compiler/backend reuse prove one exact provenance
  tuple, including derivation generation and generator code version, before any
  warm substrate is treated as reusable
- add a derivation-generation contract to the sync session so derivation-input
  mutations immediately invalidate stale warm substrates without treating every
  generated output write as a source-truth change
- route the current sync hot path through session-aware helpers before jumping
  to a daemon or full dependency-graph rewrite
- add content-addressed no-op writes on the first governed generated outputs so
  unchanged bytes stay quiet
- make sync-planned render steps authoritative for rebuild intent so generated
  surfaces do not spend wall clock rescanning their watch trees when sync
  already decided to execute the render
- settle Atlas review/catalog truth, Registry spec reconciliation, and
  delivery-intelligence refresh before the runtime-backed Compass, Radar,
  Registry, and shell renders so one final warm serves the full render phase
- treat Compass live governance context as part of that shared derivation
  substrate so release, workstream, and execution-wave truth is built once per
  settled sync generation and traceability signature rather than once per
  payload render
- treat Compass backlog projection rows as part of that same shared derivation
  substrate so later Compass payload builds reuse one settled row payload per
  generation and runtime mode instead of reopening backlog table shaping
- narrow projection and runtime cache invalidation to derivation inputs that can
  actually change the next read model, instead of clearing warm/runtime state on
  every generated HTML or JS write
- make sync-side invalidation and follow-up reruns depend on watched-output
  changes, so byte-identical traceability or delivery writes do not blow away
  compatible warm state or pay a second rerender lane
- make repo-scoped runtime invalidation clear projected-input fingerprint caches
  as well as warm verdicts, because generated derivation inputs like the
  traceability graph and delivery-intelligence artifact do not move the
  workspace-activity token by themselves
- memoize projection path-tree fingerprints per repo-state so compatible scope
  checks stop rescanning the same watched directories during one sync phase
- delay in-process sync heartbeat emission until a step actually runs long
  enough to deserve operator progress output, so fast steps do not pay a
  standing polling tax just to say they are still alive
- keep the current sync step graph externally compatible while replacing
  repeated read-model reconstruction under the hood
- record cache-explain/debug manifests plus surface runtime provenance so stale
  or unexpected reuse can be diagnosed after the run instead of guessed from
  wall-clock behavior
- use the first wave to prove the architecture with real profiling deltas, then
  decide whether the next justified wave is a resident daemon, a finer-grained
  DAG invalidator, or both

## Scope
- `src/odylith/runtime/governance/sync_workstream_artifacts.py`
- `src/odylith/runtime/governance/workstream_inference.py`
- `src/odylith/runtime/governance/validate_backlog_contract.py`
- `src/odylith/runtime/governance/component_registry_intelligence.py`
- `src/odylith/runtime/governance/delivery_intelligence_engine.py`
- `src/odylith/runtime/common/consumer_profile.py`
- shared sync-session support under `src/odylith/runtime/common/` or
  `src/odylith/runtime/governance/`
- focused sync/runtime tests proving session reuse and unchanged-write silence

## Non-Goals
- full persistent sync daemon in the first landing
- full reverse-dependency graph across every governed fact and generated surface
- claiming sub-second cold forced full rebuilds from scratch
- using filesystem stat metadata as the only correctness authority

## Risks
- a shared session can produce stale reuse if cache keys ignore generator code,
  flags, or content truth
- helper-level session plumbing can accidentally privilege the runtime fast path
  and leave standalone behavior behind
- content-addressed write elision can hide real output drift if byte comparison
  is applied after lossy render normalization instead of before file write
- the first wave could improve warm sync materially while leaving the remaining
  cold-start cost to a later daemon wave, which must stay explicit

## Dependencies
- `B-025` already owns cross-surface runtime freshness and governed surface
  integrity, which is the umbrella contract for this work
- `B-080` proved Atlas sub-second hot-path cuts through cached path resolution
  and cheaper read paths, giving this slice a concrete pattern to generalize
- `B-086` is already hardening path-normalization and nested-worktree behavior,
  which intersects directly with the sync hot-path cost center

## Success Metrics
- focused profiling shows materially fewer path normalization, repo-root
  inference, and Registry report rebuild calls on the sync hot path
- Compass backlog row loading, projection warms, and heartbeat overhead all
  fall materially in full-sync profiling without weakening the render contract
- projection/compiler/backend reuse fails closed on provenance mismatch, and
  Compass/Radar/Registry payloads explain what they were built from
- unchanged generated outputs stop rewriting bytes on the first landed render
  targets
- warm incremental sync latency drops materially without lowering validation
  strictness or reducing rendered output coverage
- forced/full sync on the maintainer checkout falls into single-digit reported
  elapsed time while strict standalone proof remains under five seconds once the
  write-mode lane settles
- standalone check-only sync remains fail-closed and source-truth equivalent

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_workstream_inference.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_component_registry_intelligence.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_delivery_intelligence_engine.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_derivation_provenance.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_odylith_memory_backend.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_backlog_ui.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_base.py tests/unit/runtime/test_sync_cli_compat.py`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --debug-cache --check-only --runtime-mode standalone`
- profiling before and after the first session-hoisted implementation cut

## Rollout
1. Bind this workstream to an in-progress plan and Atlas coverage before code
   shifts.
2. Land the shared sync-session layer and route the hot governance helpers
   through it.
3. Add content-addressed no-op writes for the first generated surfaces.
4. Re-profile and decide whether the next wave is a persistent daemon, a
   reverse-dependency DAG, or a combined lane.

## Why Now
The current performance diagnosis is already clear enough that more profiling
without architectural movement will just repeat the same call stacks. The next
useful step is to make the derivation model explicit in product truth and then
land the first code cut against that model.

## Product View
Odylith does not need a cleverer excuse for why sync is slow. It needs one
truthful engine that computes governed facts once, derives surfaces from them,
and stays quiet when nothing changed.

## Impacted Components
- `odylith`
- `dashboard`
- `delivery-intelligence`
- `registry`
- `radar`
- `atlas`

## Interface Changes
- additive shared sync-session plumbing behind existing sync and helper entry
  points
- additive content-addressed write guards on selected generated outputs
- no intended public CLI contract change in the first wave

## Migration/Compatibility
- keep standalone and check-only sync valid even if the first optimization wave
  mainly accelerates in-process runtime-backed sync
- keep generated outputs byte-identical for identical source truth
- make cache keys include content truth and generator versioning so reuse stays
  honest across code changes

## Test Strategy
- direct unit coverage for sync-session reuse on the hottest shared helpers
- regression coverage for no-op write elision on generated outputs
- focused sync compatibility tests to prove the external command surface did
  not change
- before/after profiling receipts stored in the plan and closeout narrative
- keep the remaining hotspots explicit so the next wave targets Compass runtime
  payload assembly, Registry snapshot shaping, and projection fingerprint trees
  instead of reopening the old path-normalization storm
- track the steady-state full-sync target against the settled tree, not only the
  first churn-heavy run after source-truth edits, so the operator-facing number
  reflects the real post-change feedback loop

## Open Questions
- whether the second Registry-spec sync should collapse into the same fixpoint
  wave once upstream hashes settle
- whether the first content-addressed write targets should be Registry, shell,
  or delivery-intelligence outputs
- when the architecture crosses from "shared session" to "resident daemon" in a
  way that justifies a first-class new component boundary
