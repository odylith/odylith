---
status: finished
idea_id: B-019
title: Benchmark Frontier Compaction and README Refresh
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: benchmark hot path, runtime contract payload, benchmark component boundary, Codex benchmark proof, README benchmark snapshot, and benchmark graph outputs
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Odylith already has a green benchmark lane, but the current frontier still leaves measurable payload and latency headroom that should be captured before the next release snapshot lands in the README. This slice should tighten the real hot path, rerun the Codex corpus, and refresh the published graphs from stronger proof without giving back recall or validation.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-benchmark-frontier-compaction-and-readme-refresh.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-009, B-015
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
---

## Problem
Odylith's benchmark proof is strong, but the current frontier still leaves
measurable room to improve the hot path before the next published snapshot. The
runtime contract and routed packet shapes are still paying some residual prompt,
payload, and latency cost that can likely be reduced further without weakening
required-path recall or validation success. The README graphs should only be
updated from the final strongest proof, not from an older green report.

## Customer
- Primary: Odylith consumers who rely on Codex and expect Odylith-on to stay
  clearly faster, denser, and better grounded than the repo-scan baseline.
- Secondary: Odylith maintainers who need the README benchmark section and graph
  assets to reflect the strongest validated release-ready proof.

## Opportunity
If Odylith compacts the remaining hot-path overhead and refreshes the published
benchmark snapshot from the improved report, then the product can show a wider
Codex-on advantage on speed and token economy while keeping recall and
validation gains intact. That makes the README claim stronger and keeps the
release lane honest.

## Proposed Solution
Inspect the latest scenario-level benchmark report, remove the highest-value
remaining packet and routing overhead in the hot path, rerun the Codex
benchmark corpus, and regenerate the README snapshot plus maintained benchmark
graph assets from the improved final report.

## Scope
- inspect the latest benchmark report at the scenario and family level
- identify the remaining hot-path packet or routing overhead with the highest
  median impact
- compact the relevant runtime-contract or orchestration path without regressing
  grounded behavior
- rerun the Codex benchmark corpus and confirm stronger proof
- regenerate the benchmark graph assets and refresh the README snapshot from the
  improved report

## Non-Goals
- redesigning the benchmark corpus
- changing the published graph order or release-benchmark presentation contract
- weakening correctness, recall, or validation in exchange for synthetic speed

## Risks
- over-compacting the hot path and losing useful routed signal
- improving one family while regressing another family or cache profile
- updating README proof from a report that does not actually beat the current
  benchmark frontier

## Dependencies
- `B-009` established the benchmark proof lane and acceptance contract
- `B-015` improved grounded delegation posture and the current benchmark
  frontier baseline

## Success Metrics
- median prompt tokens improve beyond the current latest report
- median total payload improves beyond the current latest report
- latency stays better than baseline and improves where possible
- required-path recall and validation success do not regress
- README benchmark numbers and graph assets match the strongest validated report

## Validation
- `odylith benchmark --repo-root .`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_evaluation_ledger.py tests/unit/runtime/test_odylith_benchmark_graphs.py`
- `git diff --check`

## Rollout
Land the hot-path compaction first, rerun the Codex corpus, then regenerate the
README numbers and canonical benchmark SVGs from the strongest validated report
only.

## Why Now
Odylith already has a green benchmark story, but release proof should track the
best frontier available, not a merely acceptable earlier win.

## Product View
If Odylith claims better speed, density, and grounding than the repo-scan
baseline, the public README should always be backed by the strongest current
proof the product can produce.

## Impacted Components
- `benchmark`
- `odylith-context-engine`
- `subagent-orchestrator`
- `odylith`

## Interface Changes
- benchmark now has a first-class Registry component boundary and Atlas proof lane
- README benchmark snapshot now points at the newer Codex benchmark frontier
- benchmark SVG assets now reflect the stronger report
- no operator-facing CLI or shell contract change

## Migration/Compatibility
- no migration required
- benchmark corpus and graph order stay unchanged
- published proof updates remain backward compatible with the current README
  structure

## Test Strategy
- add hot-path regression coverage for the tightened compact packet contract
- rerun the Codex benchmark harness on the full corpus
- regenerate graphs only after the stronger report is validated

## Open Questions
- should the next benchmark slice target family-level latency outliers instead
  of median packet compaction now that the payload frontier is substantially
  lower

## Outcome
- latest benchmark report improved from `091cdd60b1795fc8` to `5ed96082084ffaa6`
- median latency improved from `-15.015 ms` to `-16.893 ms`
- median prompt and total payload improved from `-631.5` to `-715.5`
- required-path recall stayed at `+0.964` and validation success stayed at `+0.714`
- README benchmark snapshot and the canonical SVG graph set were regenerated from
  the stronger final report
