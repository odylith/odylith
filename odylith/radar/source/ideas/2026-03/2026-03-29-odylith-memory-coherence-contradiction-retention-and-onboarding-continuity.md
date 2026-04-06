---
status: finished
idea_id: B-011
title: Odylith Memory Coherence, Contradiction Retention, and Onboarding Continuity
date: 2026-03-29
priority: P1
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: both
impacted_parts: memory snapshot contract, Casebook bug ingestion, contradiction and negative memory, onboarding continuity, shell starter-slice retention, and benchmark proof
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: B-010 made durable judgment memory real, but the live memory contract still leaked credibility. Open bugs were missing from negative memory because multiline Casebook rows were parsed weakly, contradiction memory did not retain the proof-vs-risk or bug-vs-plan conflicts Odylith could already infer, onboarding forgot the chosen slice once the welcome card hid, and operators still had to infer the snapshot headline from nested memory-area sections. Tightening those edges is necessary if Odylith’s memory should feel sharper and more trustworthy than Codex alone.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-memory-coherence-contradiction-retention-and-onboarding-continuity.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-008,B-009,B-010
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
Odylith’s durable memory existed, but some of the most important signals were
still either missing or internally inconsistent. Open Casebook risk was not
feeding negative memory reliably, contradiction memory was weaker than the
cross-surface truth Odylith could already see, onboarding continuity vanished
after the first welcome card disappeared, and the top-level memory snapshot
still made operators infer the real posture from nested sections.

## Customer
- Primary: Odylith operators and maintainers who expect memory readouts to be
  truthful, concise, and stable across sessions.
- Secondary: benchmark evaluators comparing Odylith against Codex-alone and
  looking for real retained judgment instead of one-off runtime narration.

## Opportunity
By making durable memory coherent instead of merely present, Odylith can show
that it remembers the governed slice, the unresolved risk, and the important
cross-surface conflicts without bloating the hot path or inventing stale
certainty.

## Proposed Solution
Fix multiline Casebook index ingestion, feed open bug pressure into negative
memory, retain contradiction memory for proof-vs-risk and bug-vs-plan drift,
preserve the chosen onboarding slice even after the welcome state hides, and
make the top-level memory snapshot advertise one clear status and headline.

## Scope
- parse multiline Casebook index rows into the bug projection reliably
- retain unresolved bug pressure as durable negative memory
- retain cross-surface contradiction memory for open-risk vs active-plan and
  proof vs unresolved-risk conflicts
- preserve starter-slice continuity from the shell welcome state even after it
  hides
- align top-level memory snapshot posture with the derived memory-area and
  judgment-memory sections
- rerun benchmark proof and confirm the ordered priorities still hold:
  recall/accuracy/speed first, prompt tokens second, total token budget third

## Non-Goals
- adding raw transcript retention
- inventing onboarding activity when no governed slice can be inferred
- changing hosted-memory posture or optional remote retrieval behavior

## Risks
- stronger contradiction memory could become noisy if it records every mismatch
  instead of the highest-value conflicts
- open bug pressure could overwhelm negative memory if low-signal bugs are not
  filtered down
- onboarding continuity could become misleading if the inferred slice is not
  clearly labeled as inferred rather than explicitly created

## Dependencies
- `B-008` established the memory-area operator contract
- `B-009` set the benchmark proof bar that this slice must preserve
- `B-010` established durable judgment memory and the memory-backend boundary

## Success Metrics
- open Casebook rows, including multiline index rows, feed the bug projection
  and durable negative memory
- contradiction memory retains at least the proof-vs-open-risk and
  bugs-without-active-plan conflicts when they exist
- onboarding memory retains or infers the current governed starter slice even
  when the shell welcome state is hidden
- `memory_snapshot.v1` exposes a coherent top-level headline and active status
  that agree with the nested memory-area posture
- the benchmark remains at least `provisional_pass` and keeps Odylith ahead of
  the Codex/full-scan baseline on recall/accuracy/speed first, prompt tokens
  second, and total token budgets third

## Validation
- `pytest -q tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_shell_onboarding.py`
- `pytest -q tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_subagent_surface_validation.py`
- `pytest -q tests/unit/test_cli.py`
- `odylith benchmark --repo-root .`
- `odylith sync --repo-root . --force --impact-mode full`

## Rollout
Ship as an additive memory-contract tightening. Rebuild the local runtime
artifact, refresh the shell surfaces, and keep repo truth authoritative over
every retained memory item.

## Why Now
Odylith’s memory story is already materially stronger than it was a few days
ago, which makes the remaining inconsistencies stand out more sharply. This is
the cleanup that makes the claim feel real.

## Product View
If Odylith is going to claim durable memory, it cannot quietly forget the
starter slice, miss open critical bugs, or make operators infer the real
posture from nested JSON.

## Impacted Components
- `odylith-context-engine`
- `odylith-memory-backend`
- `dashboard`
- `odylith`

## Interface Changes
- `memory_snapshot.v1` now mirrors one top-level headline from the live
  memory-area posture
- `judgment_memory.v1` and `memory_areas.v1` now expose explicit runtime
  `status` values
- onboarding memory retains an inferred starter slice even after the shell
  welcome state hides

## Migration/Compatibility
- additive only; existing consumers keep reading the nested memory sections
- stale local memory artifacts can be rebuilt from repo truth and runtime
  evidence
- no hosted service migration is required

## Test Strategy
- unit-test multiline bug-index parsing and retained negative/contradiction/
  onboarding memory
- rerun shell-onboarding tests so the inferred starter slice survives hidden
  welcome state
- rerun benchmark proof and broad runtime/unit coverage

## Open Questions
- should contradiction memory eventually gain its own shell affordance instead
  of staying a compact read model
- how much onboarding continuity should survive once broader B-002 workspace
  collaboration memory lands
