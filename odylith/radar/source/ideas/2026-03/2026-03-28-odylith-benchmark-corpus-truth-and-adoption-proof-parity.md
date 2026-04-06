status: finished

idea_id: B-009

title: Odylith Benchmark Corpus Truth and Adoption Proof Parity

date: 2026-03-28

priority: P1

commercial_value: 4

product_impact: 5

market_value: 4

impacted_lanes: both

impacted_parts: benchmark corpus source truth, orchestration proof validation, benchmark component boundary, benchmark acceptance gate, and public benchmark snapshot

sizing: M

complexity: Medium

ordering_score: 100

ordering_rationale: Odylith already beats the raw full-scan baseline on the important signals, but the public benchmark gate is still held back by stale corpus truth and a validation contract that does not recognize Odylith-owned guidance paths cleanly.

confidence: high

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-28-odylith-benchmark-corpus-truth-and-adoption-proof-parity.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-001,B-008

workstream_blocks:

related_diagram_ids: D-024

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith's local benchmark already shows better recall, validation success, and
prompt-token cost than the raw full-scan lane. But the gate still reports
`hold` because the benchmark corpus references missing workstreams and the
adoption-proof validator rejects real Odylith-owned docs and skills paths as if
they were undeclared write surfaces.

## Customer
- Primary: Odylith maintainers who rely on the benchmark gate to prove the
  product is actually stronger than Codex-alone or raw repo scan behavior.
- Secondary: downstream users evaluating whether Odylith's claimed grounding
  advantage is real, measurable, and current.

## Opportunity
By making the corpus reflect real repo truth and teaching the validator about
Odylith-owned guidance paths, Odylith can beat its own benchmark honestly
instead of carrying stale false negatives.

## Proposed Solution
Repair stale benchmark workstream anchors, recognize Odylith-owned docs and
skills paths as declared write surfaces during orchestration validation, rerun
the benchmark, and refresh the public benchmark snapshot from the new report.

## Scope
- fix stale benchmark corpus workstream references
- improve declared-write-surface recognition for Odylith-owned guidance paths
- keep the orchestration contract strict while removing false rejections
- rerun the benchmark harness and refresh the README snapshot from the new report

## Non-Goals
- weakening orchestration validation for truly under-scoped prompts
- changing benchmark families or lowering the parity gate
- changing non-benchmark product routing behavior beyond the needed contract fix

## Risks
- benchmark numbers can look artificially improved if the corpus is softened
  instead of corrected
- write-surface recognition can become too permissive if Odylith-owned paths are
  treated as blanket coverage for unrelated write surfaces

## Dependencies
- `B-001` established Odylith-owned governance and guidance paths in the public
  product repo
- `B-008` clarified current memory posture but did not address benchmark gate
  truth

## Success Metrics
- the benchmark corpus no longer references missing workstream ids
- adoption proof accepts Odylith-owned guidance paths when they satisfy the
  declared docs/skills surface
- a fresh benchmark run clears the current `hold` state to `provisional_pass`
- README benchmark numbers match the latest machine-readable report

## Validation
- `pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py`
- `pytest -q tests/unit/runtime/test_subagent_surface_validation.py`
- `odylith benchmark --repo-root .`

## Rollout
Ship the benchmark and validation fixes together, then treat the refreshed
`provisional_pass` report as the new public snapshot.

## Why Now
Odylith's product UX and memory posture improved, so the benchmark contract now
needs to catch up. Shipping stronger first-run experience while leaving stale
benchmark truth in place would undercut the product story.

## Product View
If Odylith is actually better, the benchmark should prove it cleanly and fail
only on real weaknesses, not on stale ids or misunderstood product paths.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `subagent-orchestrator`
- `subagent-router`
- `odylith`

## Interface Changes
- benchmark corpus workstream anchors align with real Radar truth
- orchestration validation recognizes Odylith-owned docs and skills surfaces
- benchmark now has a first-class Registry component boundary and Atlas proof lane
- README benchmark snapshot reflects the latest measured report

## Migration/Compatibility
- additive behavioral fix; no consumer repo migration required
- benchmark reports regenerate from source truth on the next run

## Test Strategy
- unit-test declared-write-surface recognition for Odylith-owned guidance paths
- unit-test benchmark proof-request and acceptance behavior against the fixed contract
- rerun the benchmark harness locally and inspect the resulting gate

## Open Questions
- should the benchmark snapshot in README eventually be generated directly from
  the latest report instead of updated manually
