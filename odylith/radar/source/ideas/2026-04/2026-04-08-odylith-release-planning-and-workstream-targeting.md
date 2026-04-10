---
status: finished
idea_id: B-063
title: Release Planning and Workstream Targeting
date: 2026-04-08
priority: P0
commercial_value: 5
product_impact: 5
market_value: 4
impacted_parts: Radar release-source contracts, release authoring CLI, backlog validation, traceability graph generation, Radar and Compass release read models, context-engine release resolution, maintainer release planning guidance, and release note naming alignment
sizing: L
complexity: High
ordering_score: 100
ordering_rationale: Odylith already has a mature publication lane and a mature backlog lane, but it still lacks one explicit release-planning contract that lets maintainers declare what belongs to the current or next release without smuggling that intent into prose, umbrella waves, or release-memory folklore.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-08-odylith-release-planning-and-workstream-targeting.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-026,B-030,B-033
workstream_blocks:
related_diagram_ids: D-027
workstream_reopens:
workstream_reopened_by: B-065
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Odylith can publish releases, author release notes, and track backlog
workstreams, but it has no first-class release-planning object that backlog
work can target directly. Maintainers still have to imply release membership
through plan prose, release-note titles, or local memory instead of saying
simple things like "add B-063 to current release" or "move B-060 to next
release" and having the product enforce one truthful answer everywhere.

## Customer
- Primary: Odylith maintainers and advanced operators planning what is in or
  out of a release before the publication lane runs.
- Secondary: Radar, Compass, Context Engine, and future agent workflows that
  need one canonical release target for a workstream instead of inferring it
  from prose or semver folklore.

## Opportunity
Add a repo-generic release-planning layer with a simple authoring surface and
strict contracts so release intent becomes durable product truth instead of
maintainer memory.

## Proposed Solution
- add a Radar source subtree for release definitions plus append-only
  workstream assignment history
- make `release_id` the immutable source key, with optional `version`, `tag`,
  and `name` fields plus explicit aliases such as `current` and `next`
- keep one active target release per workstream and record carry or move
  history explicitly instead of allowing ambiguous simultaneous ownership
- expose release authoring through `odylith release create|update|list|show|add|remove|move`
- project release catalog and release membership through Radar, Compass,
  Context Engine, and traceability outputs without collapsing the contract into
  execution waves or publication-only release notes

## Scope
- release source contract, loader, selector resolution, and validation
- release authoring CLI and append-only assignment event log
- traceability graph and surface payload extensions for release planning
- Radar and Compass read-only release UX
- Context Engine entity/query grounding for release selectors and aliases
- governance guidance, skills, and maintainer release alignment

## Non-Goals
- replacing umbrella execution-wave programs
- replacing Odylith's canonical maintainer publication lane
- allowing one workstream to actively belong to multiple releases at the same
  time in v1
- auto-generating release notes or release versions from backlog membership

## Risks
- ambiguous selector rules could make natural-language release operations feel
  unsafe if exact matching and explicit errors are not strict
- weak lifecycle checks could let parked, superseded, or finished workstreams
  linger in active releases and rot release truth
- routing release planning through already oversized validator and renderer
  files would create maintainability debt in the exact modules that already
  need decomposition pressure
- release planning could silently rename a release from adjacent publication
  artifacts if release naming stops being explicit operator-owned truth

## Dependencies
- `B-026` established release-version and published-release anchoring
- `B-030` established release-note driven upgrade storytelling
- `B-033` remains the historical release-hardening umbrella for maintainer
  release rigor

## Success Metrics
- maintainers can create, update, add, remove, and move release assignments
  through one canonical CLI surface
- the same workstream resolves to one active target release across source
  truth, traceability outputs, Radar, Compass, and grounded packets
- `current` and `next` are explicit aliases, not inferred from semver or date
  ordering
- release selector ambiguity fails closed with actionable exact-match choices
- shipped or closed releases reject mutable planning operations

## Validation
- focused release-contract and release-authoring unit coverage
- backlog contract, traceability build, Radar payload, Compass payload, and
  Context Engine resolution coverage for release planning
- `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
- `git diff --check`

## Rollout
Land the source contract and authoring path first, then wire read models and
surfaces, then update guidance so maintainers and agents start using the new
release-planning workflow instead of prose-only release targeting.

## Why Now
Release planning is already happening in practice, but the product still makes
it feel informal. That mismatch is now expensive because Odylith has enough
release rigor everywhere else that this missing layer stands out.

## Product View
Release should be a first-class planning object, not just a publication event.
If backlog work is truly part of a release, Odylith should be able to say so
directly and enforce that truth across surfaces.

## Impacted Components
- `release`
- `radar`
- `compass`
- `odylith-context-engine`
- `odylith`

## Interface Changes
- new CLI surface: `odylith release ...`
- new Radar source truth under `odylith/radar/source/releases/`
- new derived release fields in traceability and surface payloads

## Migration/Compatibility
- release planning is additive and should leave existing workstream topology,
  execution-wave programs, and publication-lane artifacts valid
- release-note publication truth and release-planning truth may coexist for the
  same version, but release notes must never auto-rename the release-planning
  record

## Test Strategy
- unit-test parser, selector, validator, and authoring behavior directly
- add projection and surface tests for release catalog plus workstream chips
- keep sync proof fail-closed on broken release truth

## Open Questions
- whether release planning should eventually grow an explicit "stretch"
  secondary target after the one-active-target v1 proves stable
