status: queued

idea_id: B-136

title: v0.1.15+ Enterprise Outcome Connectors and Hosted Augmentation

date: 2026-04-29

priority: P1

commercial_value: 5

product_impact: 4

market_value: 5

impacted_parts: Enterprise connectors, GitHub/Jira/Linear/Slack/Teams/Drive ingestion, optional hosted sync, remote retrieval, Context Graph, Memory Contracts, collaboration annotations, Compass, Dashboard, policy packs, and install/runtime configuration

sizing: XL

complexity: VeryHigh

ordering_score: 68

ordering_rationale: Enterprise collaboration value eventually needs connectors and optional hosted augmentation, but this should follow local-first context graph and policy boundaries so external systems cannot invert authority.

confidence: medium

founder_override: no

promoted_to_plan: 

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
Enterprise work context often lives outside the repo in GitHub, Jira, Linear, Slack, Teams, Drive, Docs, ticketing systems, and hosted observability platforms. If Odylith ignores those systems, agents miss business intent and decisions. If Odylith imports them naively, raw conversations, stale tickets, secrets, and conflicting external status can pollute repo truth. Odylith needs a connector and hosted-augmentation strategy that captures distilled outcomes while preserving local authority.

## Customer
Primary customers are enterprise teams whose engineering work spans repos, tickets, chat, docs, and approval systems. Secondary customers are Odylith maintainers who need future hosted retrieval or collaboration to remain optional and fail-safe.

## Opportunity
Connectors can make Odylith's context graph enterprise-aware without turning Odylith into a generic SaaS memory database. Hosted augmentation can add live comments, presence, shared retrieval, or cross-repo search while syncing back only distilled governed outcomes.

## Proposed Solution
Create the workstream for v0.1.15+ Enterprise Outcome Connectors and Hosted Augmentation and refine the exact implementation plan during execution.

## Scope
- Define and land the bounded work for v0.1.15+ Enterprise Outcome Connectors and Hosted Augmentation.
- Keep the first implementation wave narrow and test-backed.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- The title may need refinement once the implementation owner confirms the exact boundary.

## Dependencies
- No explicit dependency recorded yet; confirm related workstreams before implementation starts.

## Success Metrics
Connector prototypes can ingest distilled summaries from at least one issue tracker and one chat/doc source into non-authoritative context graph evidence. Raw external threads do not enter tracked truth by default. Hosted augmentation can be disabled without breaking local workflows. Compass distinguishes repo truth, runtime evidence, external observation, and hosted augmentation. Policy packs can restrict connector classes and retention.

## Validation
- Run focused validation for the touched paths once implementation begins.

## Rollout
- Queue now, then bind a technical plan when the implementation wave starts.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Build connector ingestion around outcome summaries, not raw data mirroring. Each connector should classify source type, actor, freshness, authority, policy class, linked repo artifact, and durable-summary eligibility. Hosted sync remains optional, non-authoritative, and removable. Local rendering, grounding, governance, and validation must continue when hosted services are absent or stale.

## Impacted Components
- `odylith`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- No migration impact recorded yet.

## Test Strategy
- Add targeted regression coverage when implementation begins.

## Open Questions
- Which existing workstreams or component specs should this attach to first?
