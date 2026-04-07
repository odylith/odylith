# Radar
Last updated: 2026-04-07


Last updated (UTC): 2026-04-07

## Purpose
Radar is Odylith's authoritative workstream backlog and execution-governance
surface. It turns backlog markdown, plan linkage, traceability metadata, and
execution evidence into the ranked workstream view used by operators and other
Odylith surfaces.

## Scope And Non-Goals
### Radar owns
- The canonical Odylith workstream backlog under `odylith/radar/source/`.
- Workstream ranking and status presentation.
- Backlog-to-plan linkage and validation.
- Workstream traceability graph generation.
- Auto-backfill and auto-promotion helpers for workstream state.
- Read-only rendered backlog UI and standalone detail/document shards.

### Radar does not own
- The actual implementation plans under `odylith/technical-plans/`.
- Component inventory ownership. That belongs to Registry.
- Diagram rendering. That belongs to Atlas.

## Developer Mental Model
- Radar is not just one HTML renderer. It is the combination of:
  - strict markdown contracts for workstream ideas
  - validators and repair helpers
  - traceability graph generation
  - the rendered backlog surface
- Markdown in `odylith/radar/source/` remains authoritative. Generated UI
  bundles and traceability JSON are derived.

## Runtime Contract
### Source truth
- `odylith/radar/source/INDEX.md`
  Canonical ranked backlog index.
- `odylith/radar/source/ideas/YYYY-MM/*.md`
  Idea/workstream specs.

### Generated artifacts
- `odylith/radar/radar.html`
- `odylith/radar/backlog-payload.v1.js`
- `odylith/radar/backlog-app.v1.js`
- `odylith/radar/standalone-pages.v1.js`
- `odylith/radar/backlog-detail-shard-*.v1.js`
- `odylith/radar/backlog-document-shard-*.v1.js`
- `odylith/radar/traceability-graph.v1.json`
- `odylith/radar/traceability-autofix-report.v1.json`

### Owning modules
- `src/odylith/runtime/surfaces/render_backlog_ui.py`
  Main Radar renderer.
- `src/odylith/runtime/governance/validate_backlog_contract.py`
  Fail-closed backlog contract validator.
- `src/odylith/runtime/governance/build_traceability_graph.py`
  Unified workstream traceability graph builder used by Radar and Atlas.
- `src/odylith/runtime/governance/backfill_workstream_traceability.py`
  Missing-topology autofill helper.
- `src/odylith/runtime/governance/auto_promote_workstream_phase.py`
  Conservative planning-to-implementation promotion helper.
- `src/odylith/runtime/governance/reconcile_plan_workstream_binding.py`
  Backlog/plan linkage maintenance.
- `src/odylith/runtime/governance/normalize_plan_risk_mitigation.py`
  Plan risk-mitigation normalization.
- `src/odylith/runtime/governance/plan_progress.py`
  Plan checklist/progress extraction.
- `src/odylith/runtime/governance/traceability_ui_lookup.py`
  Shared traceability link helpers.
- `src/odylith/runtime/governance/workstream_inference.py`
  Shared workstream mapping logic.

## Markdown And Contract Model
### Backlog index
`validate_backlog_contract.py` treats the backlog index as a strict table
contract with stable headers including:
- rank
- idea id
- title
- priority
- ordering score
- commercial/product/market value
- sizing and complexity
- impacted lanes
- status
- link

### Idea spec
Idea files are also validated fail-closed. Required metadata includes:
- `date`
- `priority`
- `commercial_value`
- `product_impact`
- `market_value`
- `impacted_lanes`
- `impacted_parts`
- `sizing`
- `complexity`
- `ordering_score`
- `ordering_rationale`

Required sections include workstream problem framing, solution, scope,
validation, rollout, components, interface changes, migration/compatibility,
test strategy, and open questions.

The practical effect is that Radar doubles as both the visual backlog surface
and the contract gate for workstream authoring quality.

## Render Pipeline
`render_backlog_ui.py` reads canonical Radar markdown plus linked plan and
traceability data and produces:
- summary rows for active, execution, parked, and finished workstreams
- standalone detail/document pages and route map
- traceability-driven component/diagram/doc links
- execution-wave summaries
- Compass-aware live context such as current active window and recent activity

The renderer is read-only with respect to backlog truth. It projects what the
markdown and linked governance state already say.

## Traceability Model
Radar's traceability layer is first-class, not optional garnish.

### Graph generation
`build_traceability_graph.py` composes one graph from:
- Radar idea metadata
- linked plans
- Atlas diagram catalog
- runbook/developer-doc/code references parsed from traceability sections

### Autofill
`backfill_workstream_traceability.py` is non-destructive by default:
- it fills missing or empty topology fields
- it does not overwrite explicit metadata unless forced
- it emits a JSON autofix report instead of silently mutating everything

### Default-surface diagnostics policy
- `traceability-autofix-report.v1.json` is a maintainer-facing diagnostics
  artifact, not a primary product surface.
- `warning_items` in `traceability-graph.v1.json` may retain maintainer notes
  for truth preservation, but default Radar warning cards must only project
  operator-facing `warning` and `error` rows.
- Info-level autofix conflicts and similar maintainer diagnostics should remain
  inspectable through the graph/report without leaking into the default
  workstream `Warnings` section.

### Why this exists
Radar is the workstream source of truth, but workstreams must still be tied to
plans, components, diagrams, and implementation evidence. The traceability
graph is the machine-readable join layer that lets Atlas, Compass, Registry,
and Context Engine reason over those relationships.

## Execution State Automation
`auto_promote_workstream_phase.py` is intentionally conservative:
- promotion is one-way: `planning -> implementation`
- no auto-demotion
- trigger requires live semantic implementation evidence from Compass stream
- trigger also requires at least one non-generated source-file touch

This prevents generated dashboard churn from being mistaken for implementation
progress.

## Intent Behind Radar
Radar exists so a developer or operator can answer:
- what Odylith believes the active work is
- which workstreams are only queued versus actually executing
- which plans and artifacts are bound to each workstream
- whether traceability is complete enough for safe implementation

It is the planning/governance surface, not a substitute for the plan documents
themselves.

## What To Change Together
- New workstream metadata or section:
  update the validator, renderer, and any autofill/traceability logic that
  depends on the field.
- New backlog status semantics:
  update index validation, renderer section grouping, and any automation such
  as auto-promotion.
- New traceability edge type:
  update graph generation, UI lookup helpers, and any cross-surface consumers.
- New standalone page behavior:
  update the renderer, standalone page map, and any shell deep-link assumptions.

## Failure And Recovery Posture
- Validation is fail-closed for malformed backlog truth.
- Autofill is intentionally non-destructive unless forced.
- Auto-promotion ignores generated-only churn.
- If traceability cannot be inferred confidently, Radar should surface the gap
  or emit it in the autofix report rather than inventing a clean topology.
- Default user-facing warnings should stay curated; maintainer-only diagnostics
  belong in explicit diagnostics artifacts, not primary warning cards.

## Validation Playbook
### Radar
- `odylith validate backlog-contract --repo-root .`
- `odylith validate plan-risk-mitigation --repo-root .`
- `odylith validate plan-traceability --repo-root .`
- `odylith validate plan-workstream-binding --repo-root .`
- `odylith sync --repo-root . --check-only`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-23 · Decision:** Successor created: B-280 reopens B-279 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md +1 more
- **2026-03-23 · Decision:** Successor created: B-279 reopens B-278 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/dashboard/CURRENT_SPEC.md +3 more
- **2026-03-23 · Decision:** Successor created: B-276 reopens B-275 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/subagent-orchestrator/CURRENT_SPEC.md +2 more
- **2026-03-20 · Decision:** Successor created: B-266 reopens B-265 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/casebook/CURRENT_SPEC.md +1 more
- **2026-03-20 · Decision:** Successor created: B-258 reopens B-256 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/dashboard/CURRENT_SPEC.md +1 more
- **2026-03-20 · Decision:** Successor created: B-255 reopens B-253 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/compass/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Created the first Odylith-owned Radar source tree so the public repo can maintain its own ranked product backlog instead of borrowing a consumer backlog as authority. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-07: Curated default workstream warnings to stay operator-facing while keeping info-level autofix conflicts in shared diagnostics artifacts for maintainers. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
