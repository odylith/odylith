# Casebook
Last updated: 2026-04-09


Last updated (UTC): 2026-04-07

## Purpose
Casebook is Odylith's bug and operational-learning surface. It preserves product
failure history in markdown, rebuilds a canonical bug index, and renders a
queryable bug knowledge base linked back to workstreams, components, diagrams,
and source evidence.

## Scope And Non-Goals
### Casebook owns
- The canonical bug markdown tree.
- Bug-index regeneration from source markdown.
- The read-only rendered Casebook dashboard.
- Bug-centric linkage to workstreams, components, and diagrams.

### Casebook does not own
- The live timeline stream. Compass owns that.
- Component definitions. Registry owns those.
- Workstream prioritization. Radar owns that.

## Developer Mental Model
- Bug markdown under `odylith/casebook/bugs/` is authoritative.
- `INDEX.md` is derived from those markdown files, not hand-maintained.
- The rendered Casebook surface is a searchable read model over the markdown
  archive, not a second source of truth.

## Runtime Contract
### Source truth
- `odylith/casebook/bugs/*.md`
- `odylith/casebook/bugs/archive/**`
- `odylith/casebook/bugs/INDEX.md`
  Derived, but canonical as the index artifact for the source tree.

### Generated artifacts
- `odylith/casebook/casebook.html`
- `odylith/casebook/casebook-payload.v1.js`
- `odylith/casebook/casebook-app.v1.js`
- `odylith/casebook/casebook-detail-shard-*.v1.js`

### Owning modules
- `src/odylith/runtime/governance/sync_casebook_bug_index.py`
  Rebuilds `INDEX.md` from markdown bug files.
- `src/odylith/runtime/surfaces/render_casebook_dashboard.py`
  Renders the Casebook dashboard from the bug snapshot.

## Bug Markdown Model
Casebook bug files are semi-structured markdown documents with metadata fields
such as:
- bug id
- status
- severity
- created/fixed dates
- reproducibility and type
- components affected
- ownership
- timeline
- blast radius
- workaround and recovery details
- regression tests and monitoring updates
- code and runbook references

The renderer and index sync both assume those metadata fields remain the
authoritative representation of bug knowledge.

`Bug ID` is the primary Casebook identity. The source markdown owns it, the
index projects it, and shell/render/runtime links should prefer it over file
paths while still accepting legacy file-path aliases during migration.
Normal Casebook index sync and dashboard refresh flows should backfill missing
`Bug ID` fields automatically so upgraded repos migrate cleanly without a
one-off operator step.

## Bug Index Sync
`sync_casebook_bug_index.py`:
- scans the bug tree recursively
- ignores `AGENTS.md` and `INDEX.md`
- parses bug metadata from markdown
- resolves a stable bug id for each bug, preferring markdown `Bug ID` and
  falling back to a deterministic alias for legacy records
- canonicalizes status labels
- rebuilds open and closed bug tables
- writes a deterministic `odylith/casebook/bugs/INDEX.md`

This ensures the index remains a projection of the bug archive instead of a
separate editable ledger that could drift.

## Render Pipeline
`render_casebook_dashboard.py` consumes the bug snapshot from Context Engine and
builds:
- searchable summary rows
- detail rows sharded into JS detail bundles
- severity and status facets
- bug-id-first routes and selection state, with legacy path tokens accepted as
  migration aliases
- source links back to markdown bug files
- workstream, component, and diagram links into Radar, Registry, and Atlas
- shared deep-link buttons for component, spec, proof, and diagram actions;
  those chips must reuse Dashboard's centralized deep-link button contract
  instead of Casebook-local button styling

The renderer is intentionally read-only with respect to bug truth.

### Detail-view readout contract
Casebook detail should keep two distinct read bands:
- a crisp human-facing readout that highlights the bug signal, impact, and
  current response without repeating the same field content across adjacent
  sections
- a deeper Odylith agent-learning band for guardrails, preflight checks, proof
  links, related context, and other implementation-adjacent detail

The renderer should not echo the same field content in both bands unless the
copy is materially transformed for a different audience.
- It should also dedupe overlapping proof and evidence links across those
  bands so the same path is not rendered twice under adjacent headings.
- The selected bug id should appear in the detail-header summary-facts band,
  and the renderer must not also emit a separate `CB-###` kicker above the
  title.

## Intent Behind Casebook
Casebook exists so a developer can answer:
- what failed before
- how severe it was
- which components and workstreams were involved
- what workaround, fix, and prevention knowledge already exists

It is the product learning archive, not just a list of open bugs.

## What To Change Together
- New bug metadata field:
  update bug parsing, index sync, and renderer detail shaping together.
- New status semantics:
  update canonical status mapping, open/closed grouping, and UI filters.
- New cross-link type:
  update bug snapshot shaping and renderer link generation together.
- New archive layout:
  keep index sync and renderer file discovery aligned.

## Failure And Recovery Posture
- Missing or malformed bug markdown should be surfaced through the index or
  render pipeline rather than silently dropped where possible.
- Index sync should remain deterministic and idempotent.
- The renderer should never become the primary edit path for bugs; it is a
  read model over markdown truth.

## Validation Playbook
### Casebook
- `odylith governance sync-casebook-bug-index --repo-root .`
- `odylith sync --repo-root . --check-only`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_casebook_dashboard --repo-root . --output odylith/casebook/casebook.html`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-20 · Decision:** Successor created: B-266 reopens B-265 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/casebook/CURRENT_SPEC.md +1 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Added an Odylith-owned Casebook root so the product can keep its own bug and learning history without treating any consumer bug archive as the product source of truth. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-04-07: Tightened the Casebook detail contract so the human brief and Odylith agent-learning band stay distinct, and overlapping proof/evidence links are deduped instead of repeated. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
