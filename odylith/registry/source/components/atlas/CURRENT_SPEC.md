# Atlas
Last updated: 2026-04-09


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
`scaffold_mermaid_diagram.py` creates a new catalog entry and, optionally, a
starter `.mmd` source file. It enforces that backlog, plan, and doc links are
present because Atlas diagrams are supposed to be governed artifacts, not
orphan visual assets.

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
