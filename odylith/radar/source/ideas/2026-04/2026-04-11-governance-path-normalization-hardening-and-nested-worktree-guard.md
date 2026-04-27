status: implementation

idea_id: B-086

title: Governance Path Normalization Hardening And Nested Worktree Guard

date: 2026-04-11

priority: P1

commercial_value: 4

product_impact: 5

market_value: 3

impacted_parts: agent_governance_intelligence.py, consumer_profile.py

sizing: XS

complexity: Low

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-11-governance-path-normalization-hardening-and-nested-worktree-guard.md

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

## Problem
`odylith start` could fall from a real changed-path slice into
`selection_state: none` because the changed-path pipeline was corrupting
leading-dot directories such as `.claude/`, `.codex/`, and `.github/` through
the broken `lstrip("./")` idiom. Accidental nested worktree copies under paths
like `.claude/worktrees/...` could then fan out into multiple bogus aliases and
make the start bootstrap look noisier and less targetable than the repo really
was.

## Customer
Maintainers using Claude Code and Codex who rely on `odylith start` to infer a
real workstream from the current changed-path set instead of dropping them into
fallback posture because the path normalizer invented bad aliases.

## Opportunity
Make the start/bootstrap pipeline preserve real dotfile paths, ignore nested git
worktrees before normalization, and keep the grounding lane honest about when a
repo is actually ambiguous.

## Proposed Solution
- replace the broken `lstrip("./")` usage in the changed-path normalization
  path with an explicit prefix-strip helper
- add a nested-worktree guard before changed-path normalization runs
- add focused characterization tests for dotfile preservation, bundle-mirror
  aliasing, and nested-worktree exclusion
- extend `CB-102` with the corrected root cause instead of opening a duplicate
  bug

## Scope
- fix the active changed-path normalization callsites in
  `agent_governance_intelligence.py` and `consumer_profile.py`
- add the nested-worktree exclusion guard
- add the focused tests that prove the corrected path behavior
- clean up the accidental worktree copy that polluted the repo state

## Non-Goals
- do not fix every remaining `lstrip("./")` callsite across the product
- do not redesign the start/bootstrap routing model
- do not widen into unrelated governance or bundle-refresh cleanup

## Risks
- fixing only the active start-pipeline callsites could leave adjacent latent
  `lstrip("./")` bugs for a later slice
- an overly broad nested-worktree detector could hide valid repo files if it
  mistakes a normal directory for a worktree marker

## Dependencies
- `CB-102` is the concrete bug record for the fallback-lane failure this slice
  fixes

## Success Metrics
- `odylith start --repo-root .` no longer emits phantom `claude/...`,
  `codex/...`, or `github/...` path variants for real dotfile directories
- nested-worktree copies stop contaminating the changed-path set
- focused governance-intelligence and consumer-profile tests stay green

## Validation
- run focused tests for `agent_governance_intelligence`,
  `consumer_profile`, and `workstream_inference`
- repro `odylith start --repo-root .` and verify a real lane/selection state

## Rollout
- land the path-normalization fix and tests
- remove the accidental nested worktree copy
- extend `CB-102` with the corrected diagnosis

## Why Now
The grounding lane is only trustworthy if fallback posture reflects real
ambiguity. Here it was being triggered by Odylith's own path corruption.

## Product View
Grounding should fail because the repo is actually hard to interpret, not
because Odylith rewrote the filesystem evidence into nonsense.

## Impacted Components
- `odylith`
- `dashboard`

## Interface Changes
- no public CLI change; the fix is in the internal changed-path normalization
  contract used by `odylith start`

## Migration/Compatibility
- no persisted migration; existing repos simply stop producing corrupt
  dot-stripped path aliases

## Test Strategy
- add characterization tests for dotfile preservation, valid bundle alias
  fan-out, and nested-worktree exclusion

## Open Questions
- which of the remaining non-start `lstrip("./")` callsites should be promoted
  into the next latent-bug cleanup slice?
