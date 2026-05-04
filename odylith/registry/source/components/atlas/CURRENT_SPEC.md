# Atlas

## Odylith Discipline Contract
- Atlas owns the topology view of the Odylith Discipline learning loop. D-039 shows
  intent, local pressure observations, adaptive stance, hard laws, ranked
  affordances, admissible action, proof, compact learning, benchmark evidence,
  updated priors, and the cross-system loop through Context, Execution,
  Memory, Intervention, Tribunal, Surfaces, and Benchmarks.
Last updated: 2026-05-03


Last updated (UTC): 2026-04-09

## Purpose
Atlas is Odylith's architecture and diagram-governance surface. It manages the
diagram catalog, diagram freshness, watched-change re-rendering, and the
architecture evidence that Context Engine consumes for topology-sensitive
grounding.

## Scope And Non-Goals
### Atlas owns
- The canonical diagram catalog.
- Diagram metadata linking workstreams, components, docs, code, and change
  watch paths.
- Mermaid render/update tooling.
- Shared workstream pill links in Atlas must use Dashboard's compact
  workstream-button contract rather than Atlas-local chip sizing.
- Diagram freshness and review-age enforcement.
- The read-only Atlas catalog surface.
- Architecture-domain source data consumed by Context Engine architecture mode.

### Atlas does not own
- The component inventory itself. That belongs to Registry.
- Workstream priority and plan state. That belongs to Radar.
- Shell navigation. That belongs to Dashboard.

## Developer Mental Model
- Atlas is not just a gallery of images.
- The catalog is a governed architecture contract tying diagrams to real
  workstreams, components, plans, docs, code, and watched implementation
  paths.
- Context Engine architecture mode uses Atlas evidence for topology-sensitive
  packets, so catalog quality directly affects grounding quality.

## Runtime Contract
### Source truth
- `odylith/atlas/source/catalog/diagrams.v1.json`
  Canonical diagram catalog metadata.
- `odylith/atlas/source/*.mmd`
  Mermaid source diagrams.
- `odylith/atlas/source/*.svg`
  Rendered SVG artifacts.
- `odylith/atlas/source/*.png`
  Rendered PNG artifacts.
- `odylith/atlas/source/architecture-domains.v1.json`
  Architecture-domain rules and topology guidance source.

### Generated artifacts
- `odylith/atlas/atlas.html`
- `odylith/atlas/mermaid-payload.v1.js`
- `odylith/atlas/mermaid-app.v1.js`

### Owning modules
- `src/odylith/runtime/surfaces/render_mermaid_catalog.py`
  Atlas renderer.
- `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`
  Watched-change re-renderer and freshness updater.
- `src/odylith/runtime/surfaces/install_mermaid_autosync_hook.py`
  Git pre-commit autosync hook installer.
- `src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py`
  Catalog and source scaffolding helper.
- `src/odylith/runtime/surfaces/assets/mermaid_render_config.json`
  Shared Mermaid render theme for diagram-internal typography, pastel semantic
  colors, spacing, and edge shape.
- `src/odylith/runtime/context_engine/odylith_architecture_mode.py`
  Compiled architecture bundle and architecture dossier builder.

## Catalog Model
Each diagram catalog entry is the join point between architecture proof and
implementation activity. Important fields include:
- diagram id and slug
- title, kind, owner, and summary
- source/render artifact paths
- `last_reviewed_utc`
- `reviewed_watch_fingerprints`
- `render_source_fingerprint`
- `change_watch_paths`
- related workstreams, plans, docs, and code
- linked components

The catalog is the authoritative metadata layer; the image files alone are not
enough to recover engineering intent.

## Render And Refresh Pipeline
### Atlas render
`render_mermaid_catalog.py`:
- validates catalog input
- reads traceability and component context
- resolves diagram source/render assets
- computes freshness and stale status
- produces the Atlas HTML surface and externalized JS bundle
- presents diagrams on a plain white viewer stage with padded first-fit sizing
  so large SVG labels are not clipped or hidden on first paint
- renders Mermaid assets through a shared Atlas theme config so unclassified
  diagrams still get polished typography, softer colors, and readable edges

### Auto-update
`auto_update_mermaid_diagrams.py`:
1. collects changed paths from git or explicit input
2. matches them to diagram `change_watch_paths`
3. classifies the selected diagrams into render-needed versus review-only work
   using render-semantic Mermaid fingerprints plus tracked-output truth
4. re-renders only the diagrams that genuinely need fresh SVG and PNG assets
5. refreshes `last_reviewed_utc`, `reviewed_watch_fingerprints`, and
   `render_source_fingerprint` in
   `odylith/atlas/source/catalog/diagrams.v1.json` without touching `.mmd`,
   `.svg`, or `.png` files when the run is review-only
6. re-renders `odylith/atlas/atlas.html`

It also supports `--all-stale` to refresh diagrams selected by the global
freshness contract rather than by path changes alone.

### Scaffold
`scaffold_mermaid_diagram.py` creates a new catalog entry and starter `.mmd`
source file. Atlas supports an Atlas-first flow: a new diagram may start as a
visible `draft` with empty Radar, plan, and doc link lists when the operator
asks for topology before the rest of the governance stack exists. These entries
carry `link_state: atlas_first_draft` and must still have components plus
non-empty `change_watch_paths`; later Registry/Radar/plan work should tighten
the same catalog entry instead of forcing a new diagram.

Starter flowcharts use Atlas's visual grammar inside the Mermaid source:
subgraph lanes where they clarify placement, subtle `classDef`/`style` colors
for semantic grouping, and wrapped node labels (`<br/>`) where copy would
otherwise become too wide to read. The Atlas viewer canvas stays plain white;
it must not simulate lanes, ruled grids, or color bands behind diagrams.

Atlas color is a deterministic readability aid, not source truth. Authored
Mermaid remains topology truth, but rendered fill, stroke, and text color are
Atlas-owned so legacy diagrams and newly scaffolded diagrams share one visual
contract. Container/subgraph colors use semantic lane labels first, then a
restrained wash-tone rotation only when the lane has no clear role. The
container tone must stay visibly lighter than the matching node tone, so lanes
read as quiet grouping and never compete with the boxes inside them. Inner
node colors respect authored semantic classes such as `input`, `intelligence`,
`decision`, `apply`, and `memory` before falling back to normalized label text
through broad semantic buckets: inputs/sources/operators/signals,
engines/runtimes/planners/Radar/Registry/Atlas/Casebook/proposals,
decisions/gates/validation/blockers/readiness, writes/apply/render/refresh/
release/migrate/deploy/register, memory/Compass/state/history/proof/
observation, and neutral fallback. Color must never assert status, ownership,
freshness, correctness, or evidence quality; those remain governed by catalog
metadata, labels, traceability, and source records.
The decision/gate node bucket uses the Soft Coral accent (`#ffece7` fill,
`#df8f7d` stroke, `#5c2418` text) so it stays visually distinct without
reading as warning/status truth. Containers never reuse full-strength node
accents over large areas; the matching container rotation uses a much lighter
wash (`#fff9f8` fill, `#f6d8d0` stroke) so grouped lanes stay quiet.

Strict callers can pass `--require-links` to preserve the older fail-closed
behavior when at least one Radar backlog path, technical-plan path, and doc path
must be present before the catalog write.

## Freshness And Review Semantics
Atlas tracks freshness explicitly:
- `last_reviewed_utc`
  Review anchor recorded in catalog metadata.
- `reviewed_watch_fingerprints`
  Stored content fingerprints for watched implementation paths at the time of
  the last honest review.
- `render_source_fingerprint`
  Stored render-semantic Mermaid source fingerprint used to skip SVG and PNG
  regeneration when review comments changed but the rendered topology did not.
  The fingerprint includes the Atlas Mermaid render theme, so renderer-level
  visual polish invalidates stale SVG/PNG outputs intentionally.
- `max-review-age-days`
  Staleness threshold used by renderer and auto-update tooling.
- `fail-on-stale`
  Optional mode that turns stale diagrams into a failing validation condition.

This keeps diagrams from drifting silently away from the product topology they
claim to document, while avoiding false stale debt from mtime-only churn.

## Architecture Mode Integration
`odylith_architecture_mode.py` compiles an architecture bundle under the
Context Engine compiler root and uses Atlas domain rules to build topology
dossiers. That means Atlas is part of the grounding stack, not just a UI
surface:
- architecture domain rules define required reads and operator consequences
- compiled bundles let architecture packets stay deterministic and local
- diagram watch gaps are surfaced back into Context Engine packets

## Intent Behind Atlas
Atlas exists so a developer can answer:
- what topology proof exists for this subsystem
- which diagrams are relevant to the changed paths
- whether the architectural documentation is current enough to trust
- which workstreams and components a diagram actually governs

It is meant to be architecture evidence with operational linkage, not a static
diagram dump.

## What To Change Together
- New catalog field:
  update renderer, scaffold tooling, and any freshness or architecture-mode
  consumers.
- New default-promotion rule:
  update Atlas renderer, shared Delivery Intelligence `scope_signal` contract,
  and any browser proof that asserts which workstream pills deserve default
  visibility.
- New freshness rule:
  update renderer, auto-update flow, and any validation or pre-commit hook
  messaging.
- New architecture domain:
  update `architecture-domains.v1.json` and the compiled architecture-mode
  logic together.
- New deep-link behavior:
  update Atlas renderer and shell link helpers together.

## Failure And Recovery Posture
- Missing or malformed catalog data should fail rendering clearly.
- Auto-update is deterministic and path-driven; it should not rewrite unrelated
  diagrams.
- Low-signal workstream activity must not become an "active" Atlas pill just
  because a watched path churned. Atlas default promotion should only trust the
  shared Delivery Intelligence `scope_signal` contract.
- Auto-update must fail before SVG/PNG generation when Mermaid source is
  syntactically invalid, and the failure must name the blocking diagram,
  source path, and line instead of ending as a long opaque render timeout.
- Review-only refresh must not rewrite Mermaid assets just because a watched
  path churned. Atlas should refresh freshness truth without pretending that
  unchanged diagrams were regenerated.
- Missing SVG or PNG render artifacts make a diagram stale even when the review
  date is current, so a newly scaffolded Atlas-first draft is selected for
  render and becomes visible on the Atlas surface.
- Stale diagrams can be reported or made to fail validation depending on the
  caller posture.
- If Atlas evidence is weak, Context Engine architecture packets should surface
  gaps rather than silently upgrading confidence.

## Validation Playbook
### Atlas
- `odylith atlas render --repo-root . --check-only`
- `odylith atlas auto-update --repo-root . --dry-run`
- `odylith atlas scaffold --help`
- `odylith sync --repo-root . --check-only`

## Scope Signal Ladder Contract
Atlas stays exhaustive about diagram truth, but default operator promotion is
ladder-gated. When Delivery Intelligence publishes `scope_signal`:
- child scopes at `R0-R1` do not earn default active-workstream pills
- corroborating `R2` children may surface only when the parent rollup reaches a
  promoted rung
- `R3+` scopes are eligible for default active-workstream promotion
- `R4-R5` scopes remain dominant when a diagram needs to highlight blocker or
  warning posture over ordinary activity

Atlas must preserve deep links and raw diagram linkage even when a scope is
too low-signal for default promotion.

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-16 · Implementation:** Implemented the Subagent Router runtime, the thin router skill, the component spec and runbook, and the Atlas routing topology diagrams.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
- **2026-03-16 · Decision:** keep Subagent Router accuracy-first, hard-gated, and first-class in Registry and Atlas instead of hiding delegation policy in prompt folklore.
  - Evidence: odylith/atlas/source/catalog/diagrams.v1.json, odylith/registry/source/components/subagent-router/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Added the first Odylith-owned diagram catalog so product topology can be traced and reviewed inside the public repo rather than through a consumer-specific Atlas tree. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-02: Hardened Atlas Mermaid preflight so valid diagrams no longer false-fail strict refresh on the DOMPurify hook-drift path; Atlas now falls back to browser-backed scratch validation while keeping the fail-fast syntax gate for real source errors. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022); Bug: `CB-042`)
- 2026-04-07: Refreshed the broad runtime maps to show the governed memory family, Tribunal-backed delivery flow, and conversation intelligence path, and added the dedicated memory-substrate diagram `D-025` so Registry can deep-link into projection bundle, snapshot, backend, remote retrieval, and memory-contract topology directly. (Plan: [B-059](odylith/radar/radar.html?view=plan&workstream=B-059))
- 2026-04-09: Moved Atlas workstream pill links onto the shared compact workstream-button contract and added bundle plus browser proof so Atlas pills cannot drift from the product-wide `B-###` control contract. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-080`)
- 2026-04-09: Bound Atlas default active-workstream promotion to Delivery Intelligence's shared Scope Signal Ladder so low-signal governance churn and broad fanout activity stop masquerading as architecture-relevant active work by default. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071); Bug: `CB-090`)
- 2026-04-09: Added diagram `D-032` so Compass refresh now has a first-class Atlas topology covering the one bounded command lane, cold-start narrated-cache warming, scoped budget gating, and the edge cases that must fail closed instead of reviving a hidden deeper refresh path. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Replaced Atlas watched-path freshness mtimes with stored content fingerprints, taught auto-update to distinguish review-only versus render-needed work before printing its plan, and repaired the persistent Mermaid worker bootstrap so real render jobs work again on the optimized path. Review-only Atlas refresh now updates freshness truth without regenerating unchanged SVG and PNG assets. (Plan: [B-080](odylith/radar/radar.html?view=plan&workstream=B-080); Bugs: `CB-097`, `CB-098`, `CB-099`, `CB-100`)
- 2026-05-03: Added the v0.1.14 deterministic Atlas visual grammar: pure-white viewer stage, harmonious container and semantic node palettes, Soft Coral decision/gate node coloring instead of amber or warning-coded yellow, lighter wash tones for grouped lanes, semantic-label-first container coloring, managed render-color precedence over legacy Mermaid color tokens, render-style fingerprints, and migration-backed rerendering for stale SVG/PNG assets from 0.1.10/0.1.11/0.1.12/0.1.13 installs. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-162`)
- 2026-05-04: Tightened the Atlas palette rule so container/subgraph fills use a near-white wash layer while inner node boxes keep the stronger semantic tone. The migration detector treats old full-strength container fills and container-inherited node fills as stale, forcing existing consumer diagrams to rerender during upgrade. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-162`)
