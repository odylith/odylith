status: implementation

idea_id: B-109

title: v0.1.11 Visible Intervention Release Proof

date: 2026-04-17

priority: P0

commercial_value: 4

product_impact: 5

market_value: 4

impacted_parts: release proof, validation, Compass, Atlas, Registry, Casebook, Radar

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Release proof is required because the feature is a brand-visible trust surface.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on: B-107,B-108

workstream_blocks:

related_diagram_ids: D-038,D-002

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
The visible intervention value engine must ship with proof that runtime behavior, migration, governance truth, host parity, and generated surfaces agree before v0.1.11 closes.

## Customer
Odylith maintainers and downstream users who need the released intervention UX to be trustworthy on first use.

## Opportunity
Tie focused tests, migration checks, Atlas renders, Registry validation, Casebook/Radar validation, and Compass status into one release-proof wave.

## Proposed Solution
Close v0.1.11 only after the runtime, migration, host visibility, guidance
behavior integration, benchmark/corpus proof, Registry specs, Atlas diagrams,
Radar records, Casebook records, Compass log, generated dashboards, and bundle
mirrors all agree. Release proof must name skipped coverage explicitly instead
of letting green source tests imply chat-visible product success. Guidance
Behavior release proof includes both runtime-layer alignment and
guidance-surface alignment across Codex, Claude, installed skills, command
shims, and consumer/pinned-dogfood/source-local lane instructions.

## Scope
- Focused runtime and host-visible regression for value selection,
  transcript replay, visibility status, and Assist closeout ownership.
- Guidance behavior validator and runtime-layer contract proof.
- Guidance behavior host/lane guidance-surface contract proof.
- Governance refresh across Radar, Registry, Atlas, Casebook, Compass, shell,
  and source bundle mirrors.
- Final hygiene: py_compile, selective sync, rendered Atlas checks, and
  `git diff --check`.

## Non-Goals
- Do not claim live deployed chat proof from source-local tests alone.
- Do not close B-096 until new or reloaded host sessions prove visibility or
  direct fallback Markdown is rendered in the active chat.

## Risks
- Governance can look current because generated surfaces refreshed while source
  workstreams, specs, or Casebook records still omit the new contract.

## Dependencies
- B-105 through B-108.
- Release assignment for `release-0-1-11`.
- CB-122 and CB-123.

## Success Metrics
Focused runtime, host-visible, install migration, corpus, benchmark report, Registry, Casebook, Radar, Atlas, py_compile, sync, guidance-surface contract, and git diff checks pass with any skipped coverage explicitly named.

## Validation
- Run focused intervention runtime, host-visible, transcript replay,
  benchmark/corpus, guidance behavior, guidance-surface, Casebook, Registry,
  Radar, Atlas, Compass, py_compile, sync, browser, and diff hygiene checks.

## Rollout
- Keep this wave active until release proof differentiates source-local code
  proof, generated dashboard proof, and fresh host chat visibility proof.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should leave v0.1.11 with visible intervention value as proven mechanism evidence, not a half-integrated runtime experiment.

## Impacted Components
- `governance-intervention-engine`
- `odylith-context-engine`
- `execution-engine`
- `odylith-memory-contracts`
- `tribunal`
- `benchmark`
- `compass`
- `radar`
- `registry`
- `atlas`
- `casebook`

## Interface Changes
- Release proof consumes the v0.1.11 value-engine, visibility, guidance
  behavior, and migration contracts as one acceptance bundle.

## Migration/Compatibility
- v0.1.10 to v0.1.11 migration must cut hard to the value-engine and
  guidance-behavior corpus contracts; stale ranker or missing corpus mirrors
  block release proof.

## Test Strategy
- Include both source-local runtime tests and headless/generated-surface checks
  so governance and UI proof cannot drift.

## Open Questions
- Remaining open item is fresh/reloaded Codex and Claude session proof before
  the release can claim live chat-visible activation.
