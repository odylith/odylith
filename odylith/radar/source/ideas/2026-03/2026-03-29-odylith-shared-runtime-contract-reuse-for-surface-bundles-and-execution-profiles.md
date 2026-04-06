---
status: finished
idea_id: B-013
title: Odylith Shared Runtime Contract Reuse for Surface Bundles and Execution Profiles
date: 2026-03-29
priority: P1
commercial_value: 3
product_impact: 4
market_value: 3
impacted_lanes: both
impacted_parts: shared execution-profile contracts, shared surface bundle bootstrap contracts, Dashboard, Radar, Registry, Casebook, Atlas, Compass, Subagent Router, and Subagent Orchestrator
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: Odylith's runtime and renderer stack had started repeating the same execution-profile parsing and surface bundle bootstrap contracts across multiple modules. That duplication made correctness-sensitive changes slower, raised regression risk, and worked directly against the benchmark and maintainability gains Odylith is supposed to prove. Centralizing those contracts improves reuse without changing the product behavior, and the slice is small enough to verify aggressively with runtime, browser, and benchmark proof.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-03/2026-03-29-odylith-shared-runtime-contract-reuse-for-surface-bundles-and-execution-profiles.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001
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
Odylith had begun carrying the same correctness-sensitive logic in too many
places. Compact execution-profile parsing and encoding existed in the runtime,
router, and orchestrator as parallel helpers. Surface bundle bootstrap wiring
was also repeated across Dashboard, Radar, Registry, Casebook, Atlas, and
Compass renderers. That kind of duplication increases drift risk and makes it
harder to improve the product safely.

## Customer
- Primary: Odylith maintainers changing runtime contracts and surface renderers
  who need safer reuse and lower regression risk.
- Secondary: Odylith operators who benefit when product changes stay faster and
  more correct because shared contracts only need to be fixed once.

## Opportunity
If Odylith centralizes those shared contracts, it gets better reuse,
smaller future diffs, and a lower chance of subtle surface or orchestration
regressions while keeping the benchmark and browser experience stable.

## Proposed Solution
Promote execution-profile parsing, compaction, and token encoding into one
shared tooling-memory contract module. Add one standard surface bundle spec
helper that can generate the common bootstrap and shell-embed wiring for every
surface renderer. Then migrate the existing runtime and renderer callsites to
those shared helpers and prove the result with focused unit tests, browser
smoke tests, and the benchmark harness.

## Scope
- centralize execution-profile mapping and compact encoding helpers
- migrate the Context Engine store, Subagent Router, and Subagent Orchestrator
  to the shared execution-profile helpers
- centralize shared surface bundle bootstrap and shell-embed spec creation
- migrate Dashboard, Radar, Registry, Casebook, Atlas, and Compass renderers
  to the shared surface bundle helper
- add focused tests for the new shared helpers
- prove no user-visible regression with runtime tests, headless browser smoke,
  and benchmark validation

## Non-Goals
- changing user-facing product behavior
- redesigning surface payload schemas
- broad refactors outside the duplicated runtime-contract seams

## Risks
- subtle renderer bootstrap regressions if the shared bundle helper drops a
  surface-specific option
- execution-profile drift if the shared codec normalizes fields differently
  than existing route readers expect

## Dependencies
- `B-001` established Odylith's product-owned runtime, governance, and surface
  boundaries, which makes shared contract cleanup safe to do inside the repo

## Success Metrics
- duplicated execution-profile helper logic is removed from runtime readers
- duplicated surface bundle bootstrap spec logic is removed from renderers
- focused runtime and browser tests stay green
- benchmark proof stays at or above the current green baseline

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_dashboard_surface_bundle.py tests/unit/runtime/test_tooling_memory_contracts.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_subagent_surface_validation.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- `odylith benchmark --repo-root .`

## Rollout
Ship as an internal contract cleanup with no user-facing migration. Keep the
runtime behavior fixed, then verify the product through focused tests, browser
navigation, and benchmark proof before closeout.

## Why Now
Odylith is moving quickly across runtime, surfaces, and orchestration. If the
same contracts are repeated in six or seven places, every future product slice
pays a correctness tax.

## Product View
Odylith should prove disciplined systems engineering in its own repo. Repeating
the same product contract in multiple files is the opposite of that.

## Impacted Components
- `dashboard`
- `radar`
- `registry`
- `casebook`
- `atlas`
- `compass`
- `odylith-context-engine`
- `subagent-router`
- `subagent-orchestrator`

## Interface Changes
- none in the public contract
- internal runtime and renderer callsites now share one execution-profile and
  one surface bundle bootstrap contract

## Migration/Compatibility
- additive internal refactor only
- no content migration required
- rendered surfaces and runtime payloads stay backward compatible

## Test Strategy
- add direct tests for the shared helper boundaries
- rerun focused runtime and renderer suites
- rerun headless browser smoke across the five surfaces
- rerun the benchmark harness to confirm no recall, validation, or token-cost
  regression

## Open Questions
- should the remaining smaller renderer utility seams be pulled into shared
  helpers now that the main bundle contract is centralized
