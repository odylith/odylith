status: finished

idea_id: B-010

title: Durable Judgment Memory and Memory Backend Productization

date: 2026-03-28

priority: P1

commercial_value: 5

product_impact: 5

market_value: 4

impacted_parts: judgment memory snapshot contract, workspace and actor memory posture, contradiction and outcome persistence, runtime diagnostics, CLI runtime readouts, benchmark proof, and the memory backend component boundary

sizing: L

complexity: High

ordering_score: 100

ordering_rationale: Odylith already exposes real retrieval and packet posture, but it still lacks durable judgment memory that can remember decisions, contradictions, outcomes, onboarding choices, and workspace identity without falling back to raw chat retention. That gap weakens the product's claim against Codex-alone behavior and makes the memory backend feel like an implementation detail instead of a governed subsystem.

confidence: medium

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-28-odylith-durable-judgment-memory-and-memory-backend-productization.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-002,B-008,B-009

workstream_blocks:

related_diagram_ids: D-002,D-020

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith can already compile repo truth, retrieval state, and optimization
signals, but it still forgets too much judgment. Resolved decisions, hidden
contradictions, failed attempts, onboarding picks, actor/workspace boundaries,
and proven outcomes are either recomputed ad hoc or lost between sessions.
That leaves Odylith sounding smarter than Codex-alone without remembering the
specific governed shape that makes it stronger.

## Customer
- Primary: Odylith operators and maintainers who expect the product to remember
  what mattered, what drifted, and what worked without replaying raw thread
  history.
- Secondary: downstream evaluators comparing Odylith against Codex-alone and
  judging whether the extra runtime really improves recall, accuracy, speed,
  and token efficiency.

## Opportunity
By promoting the memory backend into a first-class governed component and
adding a durable `judgment_memory.v1` contract, Odylith can remember the
high-signal decisions and conflicts that raw repo scans miss while still
keeping repo truth authoritative and prompt budgets dense.

## Proposed Solution
Persist a compact judgment-memory snapshot under `.odylith/runtime/odylith-memory/`,
derive it from repo truth plus runtime evidence, expose decision/workspace/
contradiction/freshness/negative/outcome/onboarding/provenance memory in the
Context Engine and shell, and give the local memory backend its own Registry
component boundary.

## Scope
- add a durable `judgment_memory.v1` runtime contract
- persist compact judgment memory under `.odylith/runtime/odylith-memory/`
- implement first-class decision, workspace/actor, contradiction, freshness,
  negative, outcome, onboarding, and provenance memory areas
- expose judgment-memory summaries in CLI/runtime shell readouts
- promote the local memory backend into a first-class Registry component
- rerun the benchmark and confirm the new memory work preserves or improves the
  Codex-baseline proof

## Non-Goals
- retaining raw chat transcripts as primary memory
- making hosted memory authoritative over repo truth
- broadening prompt payloads with verbose diagnostics that does not improve
  coding outcomes
- changing the optional remote retrieval provider contract

## Risks
- durable memory can become noisy if it stores every observation instead of the
  highest-signal judgment
- workspace and actor memory can become misleading if identity is inferred from
  unstable or missing local metadata
- new memory sections can regress token budgets if they leak into the hot path
  instead of staying shell/runtime facing

## Dependencies
- `B-002` already defines the collaboration and scope-isolation target for
  project, repo, workspace, and actor memory
- `B-008` introduced the memory-area posture contract but left judgment memory
  explicitly unimplemented
- `B-009` established the current benchmark proof and token-efficiency bar that
  this slice must preserve or improve

## Success Metrics
- `memory_snapshot.v1` includes a first-class `judgment_memory` section with
  durable entries for decision, workspace/actor, contradiction, freshness,
  negative, outcome, onboarding, and provenance memory
- Odylith persists judgment memory under `.odylith/runtime/odylith-memory/`
  without promoting raw chat to source truth
- the local memory backend is a first-class Registry component with synced
  source and bundle specs
- a fresh benchmark run remains at least `provisional_pass`
- benchmark deltas keep Odylith ahead of the Codex/full-scan baseline on the
  ordered priorities: recall/accuracy/speed first, prompt-token density second,
  total token-budget discipline third

## Validation
- `pytest -q tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_render_tooling_dashboard.py`
- `pytest -q tests/unit/test_cli.py`
- `odylith benchmark --repo-root .`

## Rollout
Ship the new memory contract as an additive local-runtime feature, keep repo
truth authoritative, and treat the refreshed benchmark report as proof that
the denser memory model did not regress the product against baseline.

## Why Now
Odylith's first-run UX and benchmark story are both stronger now, which makes
the lack of durable judgment memory stand out more sharply. The product needs
to remember governed insight, not just retrieve source material.

## Product View
If Odylith is really better than Codex alone, it has to remember the governed
shape of the repo, the conflicts across surfaces, and the outcomes that proved
or disproved its decisions.

## Impacted Components
- `odylith-context-engine`
- `odylith-memory-backend`
- `dashboard`
- `odylith`

## Interface Changes
- `memory_snapshot.v1` gains a `judgment_memory` section
- `.odylith/runtime/odylith-memory/odylith-judgment-memory.v1.json` becomes a
  durable local runtime artifact
- runtime and diagnostic readouts expose judgment-memory posture without
  reintroducing dashboard shell status UI
- the local memory backend becomes a first-class Registry component

## Migration/Compatibility
- additive only; existing memory snapshot consumers keep working
- no hosted service migration required
- old repos can rebuild the new runtime artifact from existing repo truth and
  recent runtime evidence

## Test Strategy
- unit-test the judgment-memory builder and persistence contract
- unit-test runtime summary and shell rendering for the new memory sections
- rerun the local benchmark harness and inspect the refreshed report

## Open Questions
- should contradiction memory eventually graduate into its own surface or stay
  a Context Engine read model
- how much actor identity should remain local-only before optional hosted
  collaboration augmentation is introduced
