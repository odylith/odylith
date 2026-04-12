---
status: finished
idea_id: B-082
title: Shared Turn Intake With Hard Consumer Fencing and Dev-Maintainer Odylith Targeting
date: 2026-04-10
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: first-turn intake flags, Context Engine session packets, lane-fenced target resolution, task-first presentation policy, consumer write boundaries, and maintainer-authorized Odylith targetability
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith needs one structured turn-intake path that can ground from copied UI text and visible surfaces without collapsing consumer turns into Odylith write targets. The same intake pipeline must still allow maintainer-authorized Odylith targeting in the product repo, so the lane boundary has to be explicit and enforced rather than inferred from prose.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-12-structured-turn-intake-hard-consumer-fencing-and-maintainer-targetability.md
execution_model: standard
workstream_type: child
workstream_parent: B-072
workstream_children:
workstream_depends_on: B-073
workstream_blocks: B-074
related_diagram_ids: D-030,D-031
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
Odylith can already ground from repo truth, but the first-turn path still
needs one explicit contract for structured user intent, quoted visible text,
and lane-aware target selection. Without that boundary, consumer turns can
bleed into Odylith-owned writes or over-narrow into irrelevant control-plane
language, while maintainer-mode work on the Odylith product repo still needs
to remain fully writable.

## Customer
- Primary: consumers using Odylith through coding agents who need hard
  protection against accidental Odylith mutations.
- Secondary: Odylith maintainers who need the same intake pipeline to keep the
  product repo writable in maintainer-authorized mode.

## Opportunity
Make one structured turn-intake contract that separates diagnostic anchors
from writable targets, preserves task-first commentary, and keeps consumer
fencing and maintainer targeting truthful across the same packet path.

## Proposed Solution
- add structured turn-context fields for intent, visible text, active tab,
  turn ids, and explicit supersession
- classify quoted surface literals as anchors and not semantic intent
- resolve target candidates with lane-aware fencing so consumer turns cannot
  emit Odylith-owned writable paths
- let product-repo maintainer mode keep Odylith-owned targets writable when
  the lane policy authorizes mutations
- drive task-first minimal narration from structured presentation policy

## Scope
- turn intake and target-resolution contract shape
- consumer-lane write fencing
- product-repo maintainer targetability
- presentation-policy carry-through for packets and commentary

## Non-Goals
- adding a second public transport before the current entrypoints are fixed
- weakening the consumer write fence just to keep a surface target writable

## Risks
- if lane policy is inferred loosely, consumer diagnostics can still leak into
  write-target selection
- if maintainer mode is treated like consumer mode, the Odylith product repo
  loses the ability to fix itself materially

## Dependencies
- `B-073`

## Success Metrics
- consumer turns ground reliably but never return Odylith-owned writable
  targets
- maintainer-mode turns in the Odylith product repo can still target Odylith
  paths when allowed by lane policy
- the same visible-text prompt resolves through one shared intake pipeline in
  both lanes

## Validation
- governance source review for the new lane-fenced turn-intake contract
- release-binding checks against the active v0.1.11 wave

## Rollout
Bind the turn-intake contract into the current release wave after the base
execution-contract slice exists.

## Why Now
This boundary is the difference between useful consumer grounding and
accidental self-mutation pressure.

## Product View
Consumer lane should be diagnosis-first and write-fenced; maintainer mode
should stay capable of materially fixing the product.

## Impacted Components
- `odylith-context-engine`
- `execution-governance`
- `odylith-chatter`

## Interface Changes
- additive `turn_context`, `target_resolution`, and `presentation_policy`
  contract fields

## Migration/Compatibility
- additive; the existing entrypoints remain the same while the packet contract
  becomes more explicit

## Test Strategy
- source-truth validation for workstream, release, and spec alignment

## Open Questions
- whether the visible-text resolver should eventually absorb screenshot OCR as
  a separate field after the first release wave proves stable
