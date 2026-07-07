# Atlas

## Odylith Discipline Contract
- Atlas owns the topology view of the Odylith Discipline learning loop. D-039 shows
  intent, local pressure observations, adaptive stance, hard laws, ranked
  affordances, admissible action, proof, compact learning, benchmark evidence,
  updated priors, and the cross-system loop through Context, Execution,
  Memory, Intervention, Tribunal, Surfaces, and Benchmarks.
Last updated: 2026-07-07


Last updated (UTC): 2026-07-07

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
- Governance-learning topology updates for changed flows, post-confirm paths,
  repair loops, governance-write paths, host lanes, projection boundaries, and
  failed mechanisms whose architecture shape must not be rediscovered.
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
- Atlas search must index diagram ids in canonical, compact, padded numeric,
  and unpadded numeric forms. A query such as `003` must find `D-003` and make
  that exact diagram-id hit the active detail even when related workstream
  text also matches the query.

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
- `src/odylith/runtime/surfaces/atlas_detail_layout.py`
  Atlas detail-pane contract for diagram explanation, read guidance, component
  cards, and linked engineering context layout.
- `src/odylith/runtime/surfaces/atlas_box_explanations.py`
  Generic box-explanation text for Atlas diagram elements. It must not encode
  simulation-domain triggers; explanations should depend on platform-generic
  roles, ownership, evidence, provider, and topology cues.
- `src/odylith/runtime/surfaces/atlas_box_terms.py`
  Selects the tracked domain object phrase used by generated box explanations
  without letting generic control verbs become the subject of visible copy.
- `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`
  Watched-change re-renderer and freshness updater.
- `src/odylith/runtime/surfaces/install_mermaid_autosync_hook.py`
  Git pre-commit autosync hook installer.
- `src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py`
  Catalog and source scaffolding helper.
- `src/odylith/runtime/surfaces/assets/mermaid_render_config.json`
  Shared Mermaid render theme for diagram-internal typography, semantic state
  colors, neutral containers, white canvas, and subdued connector shape.
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
- optional diagram-specific `read_guide` copy shown in the Atlas detail pane
- diagram-box explanations shown separately from owning Registry components:
  Atlas derives every flowchart container and inner node from Mermaid source,
  then overlays any catalog-authored `diagram_boxes` copy by label
- catalog-authored `diagram_boxes` descriptions must be clear complete
  sentences; terse placeholders are invalid because the generated detail pane
  is an operator reading surface, not an internal shorthand dump

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
- explains the selected diagram with a summary, a "how to read this view"
  guide that prefers diagram-specific catalog copy, a row-based box guide that
  covers containers and inner boxes, and owning components as a separate
  ownership list
  compact owning-component rows, and a bottom linked-context list so engineering
  links support the diagram without turning into horizontal category cards
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
`scaffold_mermaid_diagram.py` creates a new catalog entry, starter `.mmd`
source file, and default reader guidance. Atlas supports an Atlas-first flow:
a new diagram may start as a
visible `draft` with empty Radar, plan, and doc link lists when the operator
asks for topology before the rest of the governance stack exists. These entries
carry `link_state: atlas_first_draft` and must still have components plus
non-empty `change_watch_paths`; later Registry/Radar/plan work should tighten
the same catalog entry instead of forcing a new diagram.

Starter flowcharts use Atlas's visual grammar inside the Mermaid source:
subgraph lanes where they clarify placement, the shared semantic `classDef`
system for node state, restrained neutral `style` rules for containers, and
wrapped node labels (`<br/>`) where copy would otherwise become too wide to
read. The Atlas viewer canvas stays plain white; it must not simulate lanes,
ruled grids, or color bands behind diagrams.

Atlas color is a deterministic readability aid, not source truth. Authored
Mermaid remains topology truth, but rendered fill, stroke, connector, and text
color are Atlas-owned so legacy diagrams and newly scaffolded diagrams share
one visual contract. Containers default to neutral structure (`#FBFDFF` fill,
`#D8E5F4` border, `#334155` label) and may use only a semantic border when
the whole region has a clear role. Nodes carry semantic color: primary blue for
intent, API entry, diagram metadata, and final reporting; execution teal for
runtime activity, successful lookup, cache, persistence, notification, and
record creation; governance violet for policy, grants, ownership, access,
provenance, authorization, and artifact reasoning; constraint amber for
ambiguity, missing information, fallback, retry, partial evidence, conflict,
or conditional outcomes; invalid red only for hard failure, denial, security
violation, destructive failure, or unrecoverable rejection. Unclassified nodes
fall back to neutral instead of rotating through arbitrary colors or inheriting
container tone.

The canonical Mermaid node classes are:

```mermaid
classDef neutral fill:#FBFDFF,stroke:#D8E5F4,color:#17233A;
classDef primary fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;
classDef execution fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;
classDef governance fill:#F5F3FF,stroke:#DDD6FE,color:#17233A;
classDef constraint fill:#FFF8E6,stroke:#F6D98B,color:#17233A;
classDef invalid fill:#FFF1F0,stroke:#F7B4AE,color:#17233A;
```

Connectors default to subdued blue-gray (`#B9C7D8`, 1.25px, 65% opacity).
Primary-path, evidence/validation, dependency/retry/assumption, and invalid
connectors have distinct stroke rules, but dashed edges must remain
semantically meaningful and cross-links must not dominate the map. Edge labels
stay `#334155` on white or near-white backgrounds. Color must never assert
status, ownership, freshness, correctness, or evidence quality beyond the
semantic state it encodes; those remain governed by catalog metadata, labels,
traceability, and source records.

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
- **2026-06-30 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 5 tracked artifact references retained.
  - Scope: B-142
  - Evidence: 5 tracked artifact references retained
- **2026-06-30 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 5 tracked artifact references retained.
  - Scope: B-142
  - Evidence: 5 tracked artifact references retained
- **2026-06-28 · Implementation:** Implementation evidence linked this component to governed work with workstream scope preserved; 5 tracked artifact references retained.
  - Scope: B-142
  - Evidence: 5 tracked artifact references retained
- **2026-03-16 · Implementation:** Implementation evidence linked this component to governed work with 3 tracked artifact references retained.
  - Evidence: 3 tracked artifact references retained
- **2026-03-16 · Decision:** Decision evidence linked this component to governed work with 3 tracked artifact references retained.
  - Evidence: 3 tracked artifact references retained
<!-- registry-requirements:end -->

## Feature History
- 2026-07-07: Cleaned generic Atlas evidence-node explanation copy. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-220`)
  `atlas_box_explanations.py` now describes evidence/log/record nodes as
  keeping review evidence instead of producing `record records` or
  `evidence record records` constructions in generated diagram payloads. The
  change keeps the renderer domain-neutral and pins the shared explanation
  contract with the existing action-oriented node-copy test.

- 2026-06-30: Tightened Atlas box-explanation custody against platform-domain leakage. `atlas_box_explanations.py` must describe generic topology, provider, ownership, and evidence cues without carrying simulation-domain triggers into platform runtime; fixture and Casebook evidence may retain concrete repro vocabulary, but Atlas runtime explanations and current component contracts stay scenario-neutral. Tracked-object phrase extraction now lives in `atlas_box_terms.py`, keeping the touched explanation owner under the source-size pressure line and pinning generic verb fallback so terms like `stays` do not become the visible domain object. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-209`)
- 2026-06-28: Tightened Atlas workstream visibility custody after D-045 was rendered but not visible from B-142 navigation. The renderer now preserves backlog-derived `idea_id` ownership during diagram relationship attachment, and Atlas proof must check route/filter indexes such as `diagram_related_workstreams`, not only catalog rows, payload presence, or SVG/PNG assets. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-208`)
- 2026-06-28: Added source-local static generated-flowchart visibility proof to the Atlas architecture contract. D-040 now shows static generated-flowchart fallback inside Atlas auto-update, and new diagrams D-045/D-046 were rendered with SVG/PNG assets after the browser renderer degraded. Atlas payload verification confirmed D-040, D-043, D-045, and D-046 as fresh with rendered assets present, so new architecture diagrams must prove rendered visibility, not just catalog/source creation. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-208`)
- 2026-05-09: Promoted diagram-box explanation from a per-diagram convention to a general Atlas contract: Mermaid source now derives every flowchart container and inner node, catalog-authored box copy must be clear complete sentences, and v0.1.15 upgrade migration regenerates older Atlas browser surfaces without rewriting repo-owned diagram source truth. (Plan: [B-141](odylith/radar/radar.html?view=plan&workstream=B-141); Assessment: [B-140](odylith/radar/radar.html?view=plan&workstream=B-140))
- 2026-05-09: Reworked Atlas detail panes so diagrams explain what they show, how to read them, each cataloged diagram box, and their owning components before presenting linked engineering context as a bottom category list. (Plan: [B-141](odylith/radar/radar.html?view=plan&workstream=B-141))
- 2026-03-26: Added the first Odylith-owned diagram catalog so product topology can be traced and reviewed inside the public repo rather than through a consumer-specific Atlas tree. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-02: Hardened Atlas Mermaid preflight so valid diagrams no longer false-fail strict refresh on the DOMPurify hook-drift path; Atlas now falls back to browser-backed scratch validation while keeping the fail-fast syntax gate for real source errors. (Plan: [B-022](odylith/radar/radar.html?view=plan&workstream=B-022); Bug: `CB-042`)
- 2026-04-07: Refreshed the broad runtime maps to show the governed memory family, Tribunal-backed delivery flow, and conversation intelligence path, and added the dedicated memory-substrate diagram `D-025` so Registry can deep-link into projection bundle, snapshot, backend, remote retrieval, and memory-contract topology directly. (Plan: [B-059](odylith/radar/radar.html?view=plan&workstream=B-059))
- 2026-04-09: Moved Atlas workstream pill links onto the shared compact workstream-button contract and added bundle plus browser proof so Atlas pills cannot drift from the product-wide `B-###` control contract. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-080`)
- 2026-04-09: Bound Atlas default active-workstream promotion to Delivery Intelligence's shared Scope Signal Ladder so low-signal governance churn and broad fanout activity stop masquerading as architecture-relevant active work by default. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071); Bug: `CB-090`)
- 2026-04-09: Added diagram `D-032` so Compass refresh now has a first-class Atlas topology covering the one bounded command lane, cold-start narrated-cache warming, scoped budget gating, and the edge cases that must fail closed instead of reviving a hidden deeper refresh path. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Replaced Atlas watched-path freshness mtimes with stored content fingerprints, taught auto-update to distinguish review-only versus render-needed work before printing its plan, and repaired the persistent Mermaid worker bootstrap so real render jobs work again on the optimized path. Review-only Atlas refresh now updates freshness truth without regenerating unchanged SVG and PNG assets. (Plan: [B-080](odylith/radar/radar.html?view=plan&workstream=B-080); Bugs: `CB-097`, `CB-098`, `CB-099`, `CB-100`)
- 2026-05-03: Added the v0.1.14 deterministic Atlas visual grammar: pure-white viewer stage, harmonious container and semantic node palettes, Soft Coral decision/gate node coloring instead of amber or warning-coded yellow, lighter wash tones for grouped lanes, semantic-label-first container coloring, managed render-color precedence over legacy Mermaid color tokens, render-style fingerprints, and migration-backed rerendering for stale SVG/PNG assets from 0.1.10/0.1.11/0.1.12/0.1.13 installs. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-162`)
- 2026-05-04: Tightened the Atlas palette rule so container/subgraph fills use a near-white wash layer while inner node boxes keep the stronger semantic tone. The migration detector treats old full-strength container fills and container-inherited node fills as stale, forcing existing consumer diagrams to rerender during upgrade. (Plan: [B-142](odylith/radar/radar.html?view=plan&workstream=B-142); Bug: `CB-162`)
- 2026-05-07: Added short-token diagram-id search so `D-003`, `D003`, `003`, and `3` all resolve through Atlas search, with exact diagram-id token hits preferred for the active detail. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-179`)
