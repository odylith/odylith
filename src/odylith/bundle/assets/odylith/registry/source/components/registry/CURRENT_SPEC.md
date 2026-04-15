# Registry
Last updated: 2026-04-15


Last updated (UTC): 2026-04-15

## Purpose
Registry is Odylith's authoritative component-inventory and component-centric
forensics surface. It defines which components are first-class, how evidence is
mapped to them, how living specs stay synchronized with timeline-derived
requirements, and how operators inspect change history by component rather than
only by workstream.

## Scope And Non-Goals
### Registry owns
- The canonical component manifest.
- Component-to-workstream, component-to-diagram, and component-to-spec linkage.
- Component-centric event mapping and forensic coverage.
- Requirements-trace synchronization into living component specs.
- The Registry dashboard and component detail shards.
- Registry contract validation.

### Registry does not own
- Backlog priority and planning semantics. Radar owns those.
- Raw event capture. Compass owns the event stream.
- Diagram rendering. Atlas owns that.

## Developer Mental Model
- Registry is both data contract and rendered surface.
- The manifest is curated truth.
- Candidate extraction from ideas, catalog, or stream is advisory only and does
  not auto-promote a component into the first-class inventory.
- Registry treats component specs as living contracts, not static documentation.

## Runtime Contract
### Source truth
- `odylith/registry/source/component_registry.v1.json`
  Canonical component manifest.
- `odylith/registry/source/components/<component-id>/CURRENT_SPEC.md`
  Canonical current-spec dossiers for tracked components.
- `odylith/registry/source/components/<component-id>/FORENSICS.v1.json`
  Derived forensic snapshots for tracked components.

### Derived and rendered artifacts
- `odylith/registry/registry.html`
- `odylith/registry/registry-payload.v1.js`
- `odylith/registry/registry-app.v1.js`
- `odylith/registry/registry-detail-shard-*.v1.js`

### Owning modules
- `src/odylith/runtime/governance/component_registry_intelligence.py`
  Inventory normalization, event mapping, forensic coverage, and report model.
- `src/odylith/runtime/surfaces/render_registry_dashboard.py`
  Registry renderer.
- `src/odylith/runtime/governance/sync_component_spec_requirements.py`
  Requirements-trace sync into living specs.
- `src/odylith/runtime/governance/validate_component_registry_contract.py`
  Manifest and event-mapping validator.

## Core Data Structures
`component_registry_intelligence.py` defines the core model:
- `ComponentEntry`
  Normalized first-class component inventory entry.
- `ComponentSpecSnapshot`
  Parsed spec title, last-updated date, feature history, markdown body, skill
  trigger structure, and validation commands.
- `MappedEvent`
  Compass or synthetic workspace event with derived component linkage.
- `ComponentForensicCoverage`
  Whether a component currently has usable explicit or synthetic evidence.
- `ComponentRegistryReport`
  End-to-end inventory plus mapped-event report.

These types are the real Registry contract. The UI is a consumer of them.

## Component Mapping Model
Registry intentionally uses deterministic mapping precedence:
- explicit component references or direct artifact ownership
- workstream linkage
- summary/token inference as the weakest fallback

It also separates:
- first-class curated components
- candidate extraction from catalog, ideas, or stream
- synthetic workspace activity used only for forensics

Synthetic workspace activity is explicitly forensic-only. It must not pollute
requirements-trace sync or replace explicit Compass narrative capture.

## Living Spec Synchronization
`sync_component_spec_requirements.py` keeps each component spec aligned with
mapped timeline evidence by maintaining the generated
`## Requirements Trace` block.

Design intent:
- component specs stay human-authored around the generated block
- requirement evidence stays visible in the same document developers treat as
  the current contract
- sync is deterministic and idempotent

This is why every component in the manifest must point at a meaningful `spec_ref`.

## Registry Surface Pipeline
`render_registry_dashboard.py` builds the surface by combining:
- component manifest data
- component traceability index
- parsed spec snapshots
- mapped timelines
- forensic coverage
- delivery-intelligence runtime posture

`sync_component_spec_requirements.py` also writes the component-local
`FORENSICS.v1.json` sidecars so Registry source keeps a per-component evidence
snapshot next to the current spec.

The result is a component-centric dashboard where each detail panel can show:
- what the component is
- why it is tracked
- its current spec
- linked workstreams and diagrams
- relevant docs, runbooks, and code
- event timeline and forensic coverage posture

When Delivery Intelligence publishes `scope_signal`, Registry may use it to
order default operational views so high-signal components surface first without
silencing raw component truth.

## Validation Model
`validate_component_registry_contract.py` is fail-closed for:
- manifest integrity
- meaningful event mapping coverage

It supports advisory or `enforce-critical` policy reporting and can evaluate
deep-skill policy expectations for configured high-risk components. Some
diagnostics remain warn-only by design, such as candidate components pending
review.

### Local cache invalidation
Registry component-index and component-report caches are performance artifacts,
not governance truth. Their fingerprints must include:
- manifest, catalog, stream, workspace-activity, and component spec signatures;
- the Radar ideas tree fingerprint;
- the active Radar idea parser/cache contract version from
  `validate_backlog_contract.IDEA_SPEC_CACHE_VERSION`.

When Radar idea parsing starts depending on new parsed fields, Registry must
invalidate dependent caches in the same change. Stale cached `idea-parse`
diagnostics must never survive a valid source reparse and block
`odylith validate component-registry --repo-root .`.

## Intent Behind Registry
Registry exists so a developer can answer:
- what a component actually is
- why Odylith tracks it as first-class
- where its living spec is
- what evidence links recent changes to it
- whether it has sufficient forensic coverage

This is the surface that makes component boundaries explicit enough for routing,
governance, and diagnosis to stay coherent.

## What To Change Together
- New manifest field:
  update inventory normalization, renderer consumption, and validation rules.
- New event-mapping heuristic:
  update mapping confidence logic, forensic coverage, and any requirements-trace
  sync assumptions.
- New default-promotion rule:
  update Registry renderer, Delivery Intelligence `scope_signal` contract, and
  any operator-readout or browser proof that assumes component ordering.
- New spec snapshot field:
  update snapshot parsing and Registry detail rendering together.
- New deep-skill policy:
  update registry intelligence and the contract validator together.

## Failure And Recovery Posture
- Registry should fail closed on broken inventory truth.
- Candidate extraction must never silently promote first-class components.
- Synthetic workspace evidence should remain explicitly weaker than explicit
  Compass narrative evidence.
- Registry component detail must not render a default proof-state or
  live-status card. Proof-state internals such as `Proof Control`,
  `Live Blocker`, `Fingerprint`, `Frontier`, `Evidence tier`,
  `Truthful claim`, or commit-hash-heavy deployment rows are diagnostic
  engine data, not default Registry detail UI.
- Low-signal governance churn or generated noise must not outrank stronger
  component evidence in Registry's default ordering once `scope_signal` is
  available.
- Requirements-trace sync must preserve surrounding manual spec content even
  when the generated block changes.

## Validation Playbook
### Registry
- `odylith validate component-registry --repo-root .`
- `odylith governance sync-component-spec-requirements --repo-root . --check-only`
- `odylith sync --repo-root . --check-only`

## Scope Signal Ladder Contract
Registry keeps the full curated component inventory visible. The shared Scope
Signal Ladder only affects default promotion and ordering:
- `R0-R1` scope signals do not earn top-of-surface promotion by themselves
- `R2` signals can keep a component locally relevant without outranking stronger
  execution or blocker evidence
- `R3+` signals may float components earlier in default operational ordering
- `R4-R5` signals should dominate ordinary component activity when warning or
  blocker posture is present

Registry detail truth, requirements trace, and component inclusion stay
exhaustive regardless of rung.

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-17 · Implementation:** Added quick-tooltip metadata to Registry component spec inline links and code spans for hover parity in the Current Spec pane.
  - Evidence: odylith/registry/source/components/registry/CURRENT_SPEC.md, src/odylith/runtime/surfaces/render_registry_dashboard.py
- **2026-03-04 · Implementation:** Shipped Registry dashboard rendering plus governance and traceability sync updates, and refreshed generated Radar, Atlas, and Compass shells.
  - Evidence: src/odylith/runtime/governance/sync_workstream_artifacts.py, src/odylith/runtime/surfaces/render_backlog_ui.py +2 more
- **2026-03-04 · Decision:** Standardized governance visibility around Registry as the canonical component audit surface across Radar, Atlas, and Compass.
  - Evidence: src/odylith/runtime/governance/sync_workstream_artifacts.py, src/odylith/runtime/surfaces/render_backlog_ui.py +2 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Moved the authoritative Odylith product component inventory into the public repo so product components stop depending on consumer-local registry truth. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-07: Promoted the hidden memory-substrate seams into first-class Registry components so projection bundle, projection snapshot, remote retrieval, and memory contracts have explicit governed ownership and rendered detail instead of one coarse backend silhouette. (Plan: [B-058](odylith/radar/radar.html?view=plan&workstream=B-058))
- 2026-04-09: Bound Registry default operational ordering to Delivery Intelligence's shared Scope Signal Ladder so low-signal churn can stay visible in forensics without outranking real execution or blocker evidence. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071); Bug: `CB-090`)
- 2026-04-15: Hardened Registry cache fingerprints so Radar idea parser contract changes invalidate component-index and component-report diagnostics instead of letting stale `idea-parse` failures block valid governance validation. (Plan: [B-096](odylith/radar/radar.html?view=plan&workstream=B-096))
