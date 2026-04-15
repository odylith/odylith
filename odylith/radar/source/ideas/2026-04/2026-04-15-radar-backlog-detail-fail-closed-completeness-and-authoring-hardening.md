status: finished

idea_id: B-098

title: Radar backlog detail fail-closed completeness and authoring hardening

date: 2026-04-15

priority: P1

commercial_value: 3

product_impact: 3

market_value: 3

impacted_parts: odylith

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Radar is currently able to show hollow workstream detail for a real populated record, and `odylith backlog create` can still mint core-detail boilerplate that looks governed. Both trust failures need one bounded hardening slice before more backlog authoring lands.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-15-radar-backlog-detail-fail-closed-completeness-and-authoring-hardening.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids:

workstream_reopens:

workstream_reopened_by:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Radar can currently render a hollow detail panel even when the underlying
workstream markdown is fully populated. `B-073` is the concrete symptom: the
idea spec and generated detail shards contain real Problem, Customer,
Opportunity, Product View, and Success Metrics content, but the runtime-backed
detail path does not hand the UI a renderer-compatible payload, so the operator
can see a backlog item that looks under-authored when the source truth is fine.

At the same time, `odylith backlog create` still emits generic core-detail
boilerplate for new workstreams. Several recent records were left with default
Problem/Customer/Opportunity/Product View/Success Metrics copy, which makes
Radar look like it is missing governed detail because the backlog record really
is generic.

## Customer
Odylith maintainers and operators who rely on Radar as an honest view of
workstream intent, especially when they are deciding whether a slice is real,
well-scoped, and safe to execute.

## Opportunity
Make Radar fail closed with real backlog detail instead of hollow fallback copy,
and stop new workstreams from entering the backlog unless their core narrative
sections are grounded.

## Proposed Solution
- normalize the runtime backlog-detail payload so Radar receives the same core
  workstream fields it expects from the static snapshot path
- keep enough summary/detail traceability context available that the UI still
  shows honest detail when one source is thinner than expected
- make `odylith backlog create` require grounded core-detail inputs instead of
  title-only boilerplate creation
- extend backlog validation to reject default-generated core sections and
  retrofill the existing offending records

## Scope
- Radar backlog-detail runtime contract and UI fallback behavior
- backlog authoring and backlog-contract validation for core-detail sections
- shared backlog-create guidance and Radar authoring policy
- retrofill for the backlog records that still match the generic core-detail
  boilerplate

## Non-Goals
- do not redesign the Radar detail layout
- do not widen into a full backlog-schema rewrite
- do not create a generic free-form authoring workflow outside the existing
  CLI-backed backlog lane

## Risks
- if the validator only catches full-template records, partial generic sections
  will keep leaking into live backlog truth
- if `backlog create` requires too little new input, the product will still be
  able to mint hollow-looking workstreams under a different template shape
- if the runtime detail contract stays special-cased, future Radar changes will
  regress because static and runtime payloads will drift again

## Dependencies
- `B-073` is the concrete finished workstream that proves the Radar detail-view
  failure is not only bad source truth
- `B-086`, `B-088`, `B-089`, `B-090`, and `B-097` are the existing backlog
  records that need retrofill where generic core-detail boilerplate survived

## Success Metrics
- `B-073` and other populated workstreams render real detail in Radar without
  requiring a manual source audit
- `odylith backlog create` rejects attempts that omit grounded Problem,
  Customer, Opportunity, Product View, or Success Metrics content
- `odylith validate backlog-contract --repo-root .` fails when a workstream
  still carries generic core-detail boilerplate
- no existing backlog record remains in the product repo with default-generated
  core-detail sections

## Validation
- run focused unit tests for backlog authoring, backlog-contract validation,
  context-engine backlog detail loading, and Radar rendering
- run `./.odylith/bin/odylith validate backlog-contract --repo-root .`
- refresh Radar and verify the generated detail surface picks up the new
  contract

## Rollout
- bind the in-progress technical plan
- land runtime/detail and authoring hardening together so the product both
  reads and writes backlog detail honestly
- retrofill the offending workstreams before the final Radar refresh

## Why Now
The user just hit the trust break directly in Radar, and every additional
backlog item created through the current title-only lane risks adding another
hollow workstream to governed product truth.

## Product View
Radar should never make a real workstream look empty, and the backlog authoring
lane should never make an empty workstream look real.

## Impacted Components
- `odylith`
- `dashboard`

## Interface Changes
- `odylith backlog create` will require grounded core-detail inputs for new
  workstreams.

## Migration/Compatibility
- Existing workstream ids remain stable; the migration is retrofilling source
  markdown and tightening validation for future records.

## Test Strategy
- add regression coverage for runtime backlog-detail normalization
- add contract tests for generic core-detail rejection in backlog validation
- add CLI/backlog-authoring coverage for the new grounded-input requirement

## Open Questions
- should the validator reject only the core-detail template or every untouched
  boilerplate section once a workstream is promoted into active execution?
