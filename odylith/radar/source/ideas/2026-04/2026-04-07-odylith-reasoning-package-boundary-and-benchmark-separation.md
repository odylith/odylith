---
status: implementation
idea_id: B-061
title: Odylith Reasoning Package Boundary and Benchmark Separation
date: 2026-04-07
priority: P1
commercial_value: 4
product_impact: 5
market_value: 3
impacted_lanes: both
impacted_parts: Tribunal and Remediator packaging, shared reasoning provider adapters, benchmark live execution and isolation, Atlas catalog freshness, delivery intelligence imports, Registry traceability, sync hardening, browser-surface reproof, and strict package-boundary cleanup
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Benchmark proof and Tribunal diagnosis are now tightly coupled in code even though they are different product concerns. A clean package boundary is the lowest-risk way to keep benchmark harness work from accreting more reasoning internals while preserving the current runtime contract.
confidence: medium
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-07-odylith-reasoning-package-boundary-and-benchmark-separation.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-022,B-046
workstream_blocks:
related_diagram_ids: D-007,D-024
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
Tribunal, Remediator, and shared reasoning-provider code currently live under
the same `src/odylith/runtime/evaluation/` package as the benchmark harness.
That package shape makes benchmark changes feel closer to diagnosis internals
than they should be, and it leaves the product with a muddier runtime boundary
than the component model describes.

## Customer
- Primary: Odylith maintainers changing benchmark proof or diagnosis behavior
  who need a cleaner package contract and lower regression risk.
- Secondary: reviewers trying to understand whether a change affects Tribunal,
  benchmark proof, or both.

## Opportunity
Move reasoning into its own runtime package, keep benchmark code under the eval
surface, and remove the mixed-package layout completely so the filesystem and
import graph tell the same story.

## Proposed Solution
- move Tribunal, Remediator, and shared reasoning-provider implementation into
  a dedicated `src/odylith/runtime/reasoning/` package
- update runtime imports so benchmark, Compass, and delivery intelligence read
  from the new package directly
- remove the legacy `src/odylith/runtime/evaluation/{odylith_reasoning,
  tribunal_engine,remediator}.py` module files entirely
- update Registry source and traceability references so the package boundary is
  explicit and auditable
- add regression coverage for the new package paths and the absence of the old
  eval-path modules

## Scope
- reasoning-package creation and module moves
- benchmark/runtime callers updated to the new package
- Registry source and forensic path alignment
- focused regression and edge-case tests for the package boundary and
  benchmark-isolation path handling

## Non-Goals
- redesigning Tribunal logic or benchmark scoring behavior
- broad benchmark-corpus changes
- changing the persisted reasoning artifact or public CLI contract

## Risks
- stale path references in Registry or tests could make the package split look
  incomplete
- benchmark isolation could miss the new reasoning paths and leak self
  references into disposable workspaces
- stale internal or governed references could keep pointing at the deleted eval
  paths after the move
- the separately tracked benchmark live-result transport flake in `CB-045`
  can still produce an intermittent `missing_schema_output` hold even when the
  package boundary itself is healthy, so quick shard proof may require a rerun
  until that benchmark bug is fully closed

## Dependencies
- `B-022` remains the benchmark-proof umbrella
- `B-046` remains the queued Tribunal-specific benchmark-proof follow-on

## Success Metrics
- reasoning modules live under `src/odylith/runtime/reasoning/`
- benchmark modules no longer import Tribunal from the evaluation package
- the legacy reasoning module files no longer exist under
  `src/odylith/runtime/evaluation/`
- Registry source and forensic references point at the new source-of-truth
  paths
- strict `odylith sync --check-only` passes without mutating Atlas or delivery
  intelligence after the move
- browser-backed shell and surface audits stay green after the governed path
  refresh

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_reasoning.py tests/unit/runtime/test_tribunal_engine.py tests/unit/runtime/test_remediator.py tests/unit/runtime/test_odylith_benchmark_live_execution.py tests/unit/runtime/test_odylith_benchmark_runner.py`
- focused Registry/spec contract tests covering the moved source paths
- broader runtime regression sweep across delivery intelligence and Compass
- `odylith sync --repo-root . --check-only --runtime-mode standalone`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- `make dev-validate`
- a quick source-local architecture shard rerun to confirm the benchmark family
  still clears after the package-boundary hardening
- `git diff --check`

## Rollout
Land the package move and strict path cleanup together, prove the new package
layout in tests, then refresh the governed source references so the rendered
surfaces inherit a truthful boundary.

## Why Now
The product is leaning harder on Tribunal and on benchmark proof at the same
time. Keeping them physically co-located in one package makes future changes
harder to reason about than they need to be.

## Product View
Benchmark proof should be able to consume reasoning without pretending they
are the same subsystem. The package layout should make that boundary obvious.

## Impacted Components
- `benchmark`
- `tribunal`
- `remediator`
- `odylith`

## Interface Changes
- new Python package path: `odylith.runtime.reasoning.*`
- the reasoning modules now resolve only from `odylith.runtime.reasoning.*`

## Migration/Compatibility
- no consumer migration required
- internal callers move to the new package
- callers must import Tribunal, Remediator, and shared reasoning helpers from
  `odylith.runtime.reasoning`
- do not leave compatibility shims behind under `odylith.runtime.evaluation`

## Test Strategy
- prove the new package paths directly
- prove the old eval-path modules are gone and the new package paths resolve
  cleanly
- exercise benchmark isolation and live-execution helpers against the new path
  set so self-reference stripping remains correct

## Open Questions
- none inside B-061; the only residual note is the separately tracked benchmark
  live-result transport flake in `CB-045`
