---
status: implementation
idea_id: B-064
title: Radar Workstream Title Prefix Normalization
date: 2026-04-08
priority: P2
commercial_value: 2
product_impact: 3
market_value: 2
impacted_parts: Radar workstream source truth, backlog authoring, backlog validation, product-governance guidance, and Compass or Radar readouts that project workstream titles
sizing: M
complexity: Medium
ordering_score: 90
ordering_rationale: The Odylith product backlog is already product-scoped, so repeating the product name at the front of almost every Radar title burns horizontal space, makes cards wrap early, and adds no discriminating value to operators. Normalizing the titles now is a small but pervasive clarity win, and the authoring path should stop reintroducing the same redundancy.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-08-radar-workstream-title-prefix-normalization.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on:
workstream_blocks:
related_diagram_ids:
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Radar titles in the Odylith product repo have drifted into a redundant naming
habit: many workstreams begin with `Odylith` even though the whole backlog is
already the Odylith product backlog.

That prefix adds no disambiguation in Radar or Compass, but it does consume
precious horizontal space and makes long titles wrap earlier than they need to.

## Customer
- Primary: operators and maintainers scanning Radar and Compass for one clear
  slice name without wasted prefix noise.
- Secondary: maintainers creating new workstreams who need the title contract
  to be obvious and mechanically enforced.

## Opportunity
If the product repo removes the redundant `Odylith` prefix from workstream
titles and treats the shorter title as canonical, Radar and Compass become
denser and easier to scan without losing any real context.

## Proposed Solution
Normalize existing workstream titles in Radar source, enforce the shorter title
contract in the Odylith product repo validator and authoring path, and update
governance guidance so future workstreams do not reintroduce the prefix.

## Scope
- Remove the leading `Odylith` prefix from existing Radar workstream titles in
  the Odylith product repo.
- Normalize new titles in the backlog authoring path for the product repo.
- Fail closed in product-repo backlog validation when a prefixed title is
  reintroduced.
- Update Radar governance guidance to describe the shorter title contract.

## Non-Goals
- Renaming historical file slugs or technical-plan filenames that already
  carry `odylith-` in the path.
- Rewriting normal sentence prose that mentions Odylith as the product name.
- Enforcing this naming rule in consumer repos that own their own backlog truth.

## Risks
- Existing plan filenames and some historical references will still carry
  `odylith-` slugs, which could look uneven next to shorter titles.
- Over-broad normalization could strip legitimate product-name phrasing if the
  rule is not scoped carefully to the product repo and the title prefix only.

## Dependencies
- No related bug found.
- Existing Radar and Compass renderers must continue reading title metadata as
  authored source truth.

## Success Metrics
- Radar and Compass render shorter workstream titles without the redundant
  product-name prefix.
- `odylith backlog create` in the product repo no longer writes prefixed titles.
- Product-repo backlog validation rejects new workstream titles that begin with
  `Odylith`.

## Validation
- Run targeted backlog authoring and validation tests for the new title
  contract.
- Run a focused Radar render and sync proof after the title sweep.

## Rollout
- Normalize the existing product backlog title source truth in one pass.
- Ship the authoring and validation contract in the same change so the cleanup
  sticks.

## Why Now
This is currently surfacing directly in the UI as wasted width and noisy
scanning, so the naming fix should land while Radar and Compass title UX are
already under active refinement.

## Product View
Radar should name the work, not restate the product boundary on every row.
Shorter titles read better, wrap later, and make the backlog feel more
intentional.

## Impacted Components
- `radar`
- `compass`

## Interface Changes
- Product-repo Radar title authoring now strips a leading `Odylith` prefix for
  newly created workstreams.
- Product-repo backlog validation now rejects prefixed Radar titles.

## Migration/Compatibility
- Existing title cleanup is a source-truth migration inside the Odylith product
  repo only.
- Consumer repos keep their own title contracts and are not auto-rewritten by
  this rule.

## Test Strategy
- Add direct tests for product-repo title normalization during backlog authoring.
- Add validation coverage for product-repo prefixed-title rejection.
- Re-render Radar and Compass after the source-title sweep.

## Open Questions
- Whether future work should also normalize historical technical-plan display
  titles, not just Radar workstream titles.
