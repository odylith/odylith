status: implementation

idea_id: B-106

title: Visible Intervention Proposition Engine

date: 2026-04-17

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: governance-intervention-engine, conversation_surface, visibility_broker, host surfaces

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: This is the runtime core that makes multi-signal visible intervention useful instead of noisy.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-14-conversation-observation-engine-governed-proposal-flow-and-human-intervention-voice-contract.md

execution_model: standard

workstream_type: child

workstream_parent: B-096

workstream_children:

workstream_depends_on: B-105

workstream_blocks:

related_diagram_ids: D-038

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
The runtime must select visible Odylith blocks from distinct supported propositions, not from block labels or a hand-tuned pseudo-ML ranker.

## Customer
Operators using Codex and Claude who need high-value Odylith observations without duplicate, stale, unsupported, or hidden-only claims.

## Opportunity
Build the proposition ledger, hard gates, deterministic utility features, conflict graph, subset selector, and compact decision log as the v0.1.11 core.

## Proposed Solution
Ship the proposition-first value engine under
`src/odylith/runtime/intervention_engine/`: evidence/proposition/value
contracts, deterministic utility scoring, evidence and freshness hard gates,
semantic duplicate collapse, proposal dependency checks, adaptive live budget,
bounded subset enumeration, and compact selected/suppressed decision logging.
The old block-first signal-ranker direction is removed from the shipped
runtime posture.

## Scope
- Convert ambient, Observation, and Proposal candidates into
  `SignalProposition` options before label selection.
- Select from proposition utility and conflict constraints, not from a single
  hand-tuned block threshold.
- Keep hot-path inputs local and compact: packet summaries, execution
  snapshots, memory/session summaries, Tribunal/delivery summaries, and
  governed anchors.
- Carry material Guidance Behavior summary failures as one evidence-qualified
  contract proposition without letting passing summaries create visible noise.

## Non-Goals
- Do not ship runtime adaptive learning, provider-backed embeddings, or
  ML-calibrated threshold claims in v0.1.11.
- Do not add broad repo search or context-store expansion to live selection.

## Risks
- A fast selector can still hurt the brand if it accepts unsupported facts,
  duplicates propositions across labels, or lets producer-supplied confidence
  inflate weak evidence. Those are hard gates, not post-render cleanup.

## Dependencies
- B-105 governance binding.
- Context Engine, Execution Engine, memory, Tribunal, and delivery-ledger
  summaries as compact evidence providers.

## Success Metrics
The value-engine package owns proposition contracts, hard gates, adaptive budget, duplicate collapse, proposal dependency checks, and p95 selector latency at or below 15 ms in focused tests, with contracts/scoring, selection, and corpus/reporting split into focused modules instead of one oversized runtime file.

## Validation
- Value-engine unit and benchmark tests prove duplicate visible proposition
  rate `0.0`, visibility-failure recall `1.0` for explicit invisibility
  cases, suppressed weak/unsupported/stale/hidden/generated evidence, and
  p95 selector latency at or below the v0.1.11 target.
- Intervention alignment evidence tests prove Guidance Behavior summaries only
  become visible facts when material.

## Rollout
- Land behind the v0.1.11 forward contract and keep calibration artifact
  loading disabled unless the governed corpus becomes publishable.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Odylith should surface the smallest high-value set of true, timely, distinct propositions that materially improve the user's next move.

## Impacted Components
- `governance-intervention-engine`
- `odylith-context-engine`
- `execution-engine`
- `odylith-memory-contracts`
- `tribunal`

## Interface Changes
- New value-engine contracts:
  `SignalEvidence`, `SignalProposition`, `InterventionValueFeatures`,
  `VisibleInterventionOption`, and `VisibleSignalSelectionDecision`.
- Decision log now carries selected/suppressed proposition ids, duplicate
  groups, utility, suppression reasons, proof posture, and latency summary.

## Migration/Compatibility
- v0.1.10 signal-ranker artifacts migrate to the v0.1.11 value-engine corpus
  and migration ledger; no compatibility shim preserves the misleading API.

## Test Strategy
- Test adversarial no-evidence high scores, weak-evidence confidence ceilings,
  duplicate keys that disagree with semantic signatures, same-label distinct
  ambient stacking, exact Proposal restatements, and candidate floods.

## Open Questions
- Later releases can add calibrated weights after enough adjudicated
  non-synthetic data exists; v0.1.11 runtime stays deterministic.
