status: implementation

idea_id: B-133

title: v0.1.15+ Durable Decisions Annotations and Memory Hygiene

date: 2026-04-29

priority: P0

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: Memory Backend, Memory Contracts, Context Engine, Compass intervention stream, Casebook, Radar, technical plans, annotation capture, raw thread suppression, durable judgment memory, and collaboration summaries

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Shared memory becomes a liability unless Odylith distinguishes durable decisions and resolved annotations from raw conversation exhaust before enterprise collaboration inputs arrive.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/in-progress/2026-10/2026-10-04-current-authority-and-useful-history-in-memory.md

execution_model: standard

workstream_type: standalone

workstream_parent: 

workstream_children: 

workstream_depends_on: 

workstream_blocks: 

related_diagram_ids: D-025

workstream_reopens: 

workstream_reopened_by: 

workstream_split_from: 

workstream_split_into: 

workstream_merged_into: 

workstream_merged_from: 

supersedes: 

superseded_by: 

## Problem
Enterprise multi-agent workflows generate large amounts of conversational, review, trace, and tool-output data. If Odylith stores raw threads as durable memory, memory can become noisy, stale, secret-bearing, or prompt-injection contaminated. If it stores too little, handoffs lose decisions and policy rationale. Odylith needs a governed annotation and decision-memory contract that preserves distilled outcomes while suppressing raw exhaust.

## Customer
Primary customers are maintainers and agents that need decisions, approvals, reversals, contradictions, and review outcomes to survive across sessions. Secondary customers are enterprise teams that need defensible memory retention, redaction, and audit posture.

## Opportunity
Odylith can turn collaboration memory into a governed advantage by retaining only resolved summaries, durable decisions, contradiction records, proof outcomes, and provenance. That lets humans and agents operate from shared memory without turning every chat or trace into authoritative context.

## Proposed Solution
The operator authorizes first-wave current-authority and useful-history policy
while Greenfield converges. Add explicit record role/validity metadata and
weighted relevance/evidence/freshness after authority admission. Use one shared
Context Engine owner for judgment synthesis, retrieval and hint admission;
Memory Contracts carries compact provenance and reasons. Rebuilding a cache
must not reconfirm old evidence or let a stale hint manufacture confidence.

## Scope
- H1: source-backed history-use metadata, authority precedence, weighted
  usefulness/decay, evidence-time preservation and current-source hint admission.
- Snapshot, retrieval, compact packet and later-decision round-trip proof.
- Fixed-case recall/precision, stale-authority, continuity, packet and latency
  comparisons; independent current/history boundary review.
- Wider collaboration annotations remain subsequent work under this record.
- Preserve historically honest Atlas review evidence during the H1 topology
  update: CB-357 bounds selected authoring refresh to its validated diagrams.

## Non-Goals
- No enterprise collaboration or general annotation platform in H1.
- No new consumer model phase, remote activation or transcript archive.

## Risks
- Age is not truth: decay must not suppress active safety constraints or turn
  unknown legacy records into accepted or superseded facts.
- Metadata-only changes cannot establish better retrieval or judgment; prove
  actual live-caller selection, useful recall and bounded cost.

## Dependencies
- Reuse existing source-fingerprint/generation contracts and workstream lineage.
- Preserve B-010/B-011 memory boundaries and CB-053's freshness discipline.
- B-142 consumes this shared memory boundary while retaining all Greenfield laws.

## Success Metrics
Context Engine grounding prefers resolved decisions and durable annotations over raw threads. Memory validation rejects placeholder summaries, transcript-shaped durable refs, secret-bearing annotations, and unproven policy changes. Compass can show pending versus resolved annotations. Casebook and Radar can link decisions to bugs, plans, and workstreams. Benchmarks prove lower stale-memory and decision-loss rates.

## Validation
- Prove current valid authority over recent historical claims, useful historical
  failure recall, unknown legacy status, source drift, current contradictions,
  rebuild without reconfirmation and valid current continuity.
- Verify producer -> snapshot -> retrieval -> compact packet -> later decision,
  preserving shared-only ambiguity and session-intent non-replay.

## Rollout
- Bind the authorized H1 plan and implement on the existing release branch.
- Assess installed compatibility and preserve original evidence before release.

## Why Now
The operator explicitly requests historically useful knowledge without stale
context overriding current evidence, and measurable Retrieval and Judgment/
session memory improvements while Greenfield reaches production quality.

## Product View
Add a durable annotation and decision-memory contract. Raw comments, chat threads, and full traces remain transient or hosted-only. Tracked truth receives resolved annotation summaries with actor, artifact, timestamp, status, decision class, affected component, and evidence links. Memory Contracts compact those summaries into packets; Memory Backend retains freshness, contradiction, outcome, and provenance signals; Context Engine excludes transcript-shaped source refs from durable grounding.

## Impacted Components
- `odylith`
- `odylith-context-engine`
- `odylith-memory-backend`
- `odylith-memory-contracts`
- `atlas`

## Interface Changes
- Explicit derived record role/validity, usefulness/decay reasons and source
  provenance must survive retrieval and compaction. Final fields are owned by
  the shared implementation and must not imply inferred semantic authority.

## Migration/Compatibility
- Legacy missing metadata remains unknown; derived caches must preserve the
  current source/fingerprint contract. Assess actual installed changes before
  release; no consumer source truth is rewritten to manufacture new authority.

## Test Strategy
- Use current source versus historical/rejected/refuted/superseded controls and
  valid later recall with fixed expected meaning. Existing memory, shared-scope,
  session, provenance and compact-contract guards remain required.

## Open Questions
- No operator decision is needed for the authorized H1 policy wave. Wider
  enterprise annotation/collaboration interfaces remain outside this first wave.
