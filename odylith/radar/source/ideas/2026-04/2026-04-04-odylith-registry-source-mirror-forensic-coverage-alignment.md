---
status: implementation
idea_id: B-045
title: Registry Source-Mirror Forensic Coverage Alignment
date: 2026-04-04
priority: P1
commercial_value: 3
product_impact: 4
market_value: 3
impacted_parts: Registry forensic coverage, source-owned bundle mirrors, component workspace-activity mapping, and benchmark-safe evidence capture
sizing: S
complexity: Medium
ordering_score: 100
ordering_rationale: Registry already has live forensic capture, but source-owned mirrored paths can leave actively changing components looking artificially quiet; that weakens operator trust in the evidence surface and makes component activity harder to read honestly.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-04/2026-04-04-odylith-registry-source-mirror-forensic-coverage-alignment.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on:
workstream_blocks:
related_diagram_ids: D-006,D-008,D-011
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
Registry forensic coverage is supposed to show whether a tracked component has
live evidence, but source-owned mirrored bundle paths can still fall outside
the component's canonical `path_prefixes`. When that happens, real product
activity can leave the component marked `baseline_forensic_only` even though
the change is materially about that component.

## Customer
- Primary: Odylith maintainers using Registry to understand which components
  are actively changing.
- Secondary: future Odylith operators who rely on Registry forensic coverage to
  explain why a component is quiet, active, or lagging.

## Opportunity
If Registry treats source-owned mirror paths as component-owned evidence
without widening into generic generated-file churn, the forensic surface stays
truthful and operators can trust component activity without manually
reconstructing source-to-bundle relationships.

## Proposed Solution
- add mirror-aware workspace-activity normalization for component forensic
  mapping
- keep canonical source paths authoritative while allowing product-owned bundle
  mirrors to map back to the same component
- add focused regressions for component forensic coverage, sidecar sync, and
  Registry rendering
- validate with targeted unit tests and a benchmark-safe check path

## Scope
- Registry forensic workspace-activity mapping
- source-owned mirrored bundle path recognition for component evidence
- focused tests and regenerated forensic truth for the affected components

## Non-Goals
- changing benchmark snapshot selection semantics
- turning generic generated assets into forensic evidence
- replacing explicit Compass events with synthetic workspace activity

## Risks
- mirror expansion could create false-positive evidence for unrelated
  components
- a fix aimed at Registry could accidentally widen benchmark or proof-run
  dirty-worktree handling

## Dependencies
- none

## Success Metrics
- source-owned mirror edits for a component can promote that component from
  baseline-only to live forensic coverage
- unrelated generated or mirrored churn still does not create spurious
  evidence
- benchmark-facing tests remain green on the focused validation path

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_sync_component_spec_requirements.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_prompt_payloads.py`
- `git diff --check`

## Rollout
Land the mapper and test changes first, then refresh governed Registry
artifacts so the product repo shows the corrected forensic coverage.

## Why Now
The mismatch is small but operator-visible. Leaving it in place teaches people
not to trust Registry exactly where Odylith is trying to make evidence
mechanical.

## Product View
If Odylith says a component is quiet while its own governed mirror is changing,
the surface is lying by omission. The fix should make the truth more faithful,
not more permissive.

## Impacted Components
- `registry`
- `tribunal`
- `remediator`
- `dashboard`

## Interface Changes
- Registry forensic coverage treats recognized source-owned mirrored paths as
  live component evidence
- components with only source-mirror activity no longer stay artificially
  baseline-only

## Migration/Compatibility
- no consumer migration required
- explicit Compass logging remains the preferred high-signal evidence path
- synthetic workspace activity remains support evidence only

## Test Strategy
- characterize the current baseline-only failure mode
- prove the owning component becomes live when only the mirrored path changes
- prove unrelated generated paths still stay excluded
- keep benchmark-facing regression coverage in the validation set

## Open Questions
- whether source-mirror mapping should become explicit manifest metadata later
  instead of staying rule-based for the current Odylith bundle layout

## Outcome
- Bound to `B-045`; implementation in progress.
