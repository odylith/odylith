Status: Done

Created: 2026-03-29

Updated: 2026-03-29

Backlog: B-011

Goal: Make Odylith’s durable memory coherent and operator-trustworthy by
retaining open risk, cross-surface contradictions, and onboarding slice
continuity without regressing the benchmark priorities.

Assumptions:
- Repo truth remains authoritative over every retained memory item.
- Durable memory should stay judgment-dense and compact, not verbose.
- The benchmark ordering stays explicit: recall/accuracy/speed first, prompt
  tokens second, total token budgets third.

Constraints:
- Do not retain raw chat transcripts.
- Do not invent onboarding activity when the governed slice is only inferred.
- Do not regress the benchmark gate or inflate hot-path packets.

Reversibility: Reverting this slice restores the earlier weaker Casebook bug
ingestion, weaker contradiction/negative/onboarding memory posture, and the
less coherent top-level memory readout without touching tracked repo truth.

Boundary Conditions:
- Scope includes bug projection parsing, durable contradiction/negative/
  onboarding memory, memory snapshot coherence, spec updates, and proof
  reruns.
- Scope excludes hosted-memory rollout, raw conversation memory, and unrelated
  release/install work already on this branch.

Related Bugs:
- no related bug found

## Context/Problem Statement
- [x] Durable judgment memory exists, but key signals were still missing or
  inconsistent.
- [x] Multiline Casebook index rows were preventing open bug pressure from
  reaching negative memory.
- [x] Contradiction memory should retain the strongest cross-surface conflicts,
  not just packet-local observations.
- [x] Onboarding continuity should survive after the welcome state hides.
- [x] Operators should not need to infer the memory headline from nested JSON.

## Success Criteria
- [x] Open Casebook rows, including multiline index rows, feed the bug
  projection and negative memory.
- [x] Contradiction memory retains proof-vs-open-risk and
  bugs-without-active-plan conflicts when they exist.
- [x] Onboarding memory retains or infers the governed starter slice after the
  welcome state hides.
- [x] `memory_snapshot.v1` exposes a coherent top-level headline.
- [x] `judgment_memory.v1` and `memory_areas.v1` expose explicit `status`
  values.
- [x] Benchmark proof remains at least `provisional_pass` without regressing
  the ordered priority stack.

## Non-Goals
- [x] Raw transcript retention.
- [x] Hosted-memory authority changes.
- [x] Broad shell redesign beyond the memory/onboarding continuity slice.

## Impacted Areas
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [shell_onboarding.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/shell_onboarding.py)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [test_odylith_memory_areas.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_memory_areas.py)
- [x] [test_shell_onboarding.py](/Users/freedom/code/odylith/tests/unit/runtime/test_shell_onboarding.py)

## Traceability
### Runtime Contracts
- [x] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [shell_onboarding.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/shell_onboarding.py)

### Registry Truth
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/src/odylith/bundle/assets/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)

### Governance Truth
- [x] [2026-03-29-odylith-memory-coherence-contradiction-retention-and-onboarding-continuity.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-03/2026-03-29-odylith-memory-coherence-contradiction-retention-and-onboarding-continuity.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)

### Tests And Proof
- [x] [test_odylith_memory_areas.py](/Users/freedom/code/odylith/tests/unit/runtime/test_odylith_memory_areas.py)
- [x] [test_shell_onboarding.py](/Users/freedom/code/odylith/tests/unit/runtime/test_shell_onboarding.py)
- [x] [latest.v1.json](/Users/freedom/code/odylith/.odylith/runtime/odylith-benchmarks/latest.v1.json)

## Risks & Mitigations

- [x] Risk: contradiction memory becomes noisy.
  - [x] Mitigation: retain only named, high-signal conflicts with explicit provenance.
- [x] Risk: onboarding continuity overstates certainty.
  - [x] Mitigation: label inferred starter slices as `inferred` instead of `established`.
- [x] Risk: stronger memory posture leaks extra token cost into hot-path packets.
  - [x] Mitigation: keep the new memory posture in runtime artifacts and shell/CLI readouts, then rerun the benchmark gate.

## Validation/Test Plan
- [x] `pytest -q tests/unit/runtime/test_odylith_memory_areas.py tests/unit/runtime/test_shell_onboarding.py`
- [x] `pytest -q tests/unit/runtime/test_odylith_runtime_surface_summary.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_subagent_surface_validation.py`
- [x] `pytest -q tests/unit/test_cli.py`
- [x] `odylith benchmark --repo-root .`
- [x] `odylith sync --repo-root . --force --impact-mode full`

## Rollout/Communication
- [x] Ship the memory contract tightening as additive runtime truth.
- [x] Refresh surfaces so the shell and other readouts see the stronger memory posture.
- [x] Keep benchmark priorities explicit in the closeout record.

## Dependencies/Preconditions
- [x] Durable judgment memory from `B-010` is already present.
- [x] Shell onboarding already computes a chosen slice when the welcome state is visible.
- [x] The benchmark harness remains runnable locally.

## Edge Cases
- [x] Hidden welcome state still yields an inferred starter slice.
- [x] Multiline Markdown table rows in Casebook indexes still parse into open bugs.
- [x] Missing sessions or bootstraps leave onboarding memory partial instead of fabricated.

## Open Questions/Decisions
- [x] Decision: treat proof-vs-open-risk and bugs-without-active-plan as durable contradictions because they are exactly the cross-surface delta Odylith should remember.
- [x] Decision: expose a compact snapshot-level headline so operators can read memory posture in one glance.

## Current Outcome
- Open Casebook risk now reaches durable negative memory even when the bug index
  wraps table rows across multiple lines.
- Contradiction memory now retains named conflicts for benchmark proof versus
  unresolved critical risk and for unresolved critical bugs without any active
  implementation plan.
- Onboarding memory now preserves an inferred starter slice even after the
  welcome card hides, so the second session still has governed continuity.
- `memory_snapshot.v1` now mirrors a top-level headline and exposes coherent
  `status` fields for both `memory_areas.v1` and `judgment_memory.v1`.
- Live memory posture after this slice is materially stronger: top-level
  memory areas are `strong=5`, `partial=1`, `cold=2`, while judgment memory is
  `strong=7`, `partial=1`.
