---
status: finished
idea_id: B-067
title: Context Engine Module Decomposition and Boundary Hardening
date: 2026-04-08
priority: P0
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: Context Engine projection-surface resolution, session-packet builders, hot-path packet compaction, store call boundaries, benchmark packet expectations, and Context Engine component contracts
sizing: L
complexity: High
ordering_score: 98
ordering_rationale: The Context Engine is now functionally strong enough that its remaining failure mode is structural: several central runtime modules are still far beyond the repo size policy, couple unrelated concerns together, and make every new change riskier than it should be. This should be tackled now as a bounded refactor wave before more benchmark, proof-state, release, and collaboration work compounds the same central files.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-08-odylith-context-engine-module-decomposition-and-boundary-hardening.md
execution_model: standard
workstream_type: child
workstream_parent: B-033
workstream_children:
workstream_depends_on: B-014,B-033,B-062,B-063
workstream_blocks:
related_diagram_ids: D-002
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
The Context Engine still carries several red-zone runtime modules that mix too
many responsibilities into one file. The product now depends on those modules
for release selectors, proof-state packets, benchmark packet shaping, and
grounded context reads, so continued growth inside the same files raises both
regression risk and review cost.

## Customer
- Primary: Odylith maintainers changing Context Engine grounding, packet, and
  benchmark behavior.
- Secondary: benchmark and surface consumers who need the Context Engine to
  stay behaviorally stable while its internals evolve.

## Opportunity
If the Context Engine splits its oversized runtime modules along real
responsibility boundaries now, future changes can land in narrower owned files
with stronger tests and lower cross-surface regression risk.

## Proposed Solution
Perform a hard refactor of the oversized Context Engine helper modules by
splitting projection-surface resolution, session-packet building, and hot-path
packet compaction into smaller owned modules, then rewiring all imports
directly to the new boundaries instead of leaving compatibility facades behind.

## Scope
- split the projection-surface runtime into smaller modules with direct query
  runtime imports
- split the session-packet runtime into smaller packet-builder and packet-
  summary modules with direct store and learning-runtime imports
- split the hot-path packet compaction runtime into smaller focused modules and
  wire `odylith_context_engine_hot_path_runtime.py` directly to them
- update component docs and regression coverage to match the new module
  boundaries

## Non-Goals
- redesigning Context Engine packet contracts
- changing public CLI semantics
- broad collaboration-memory work beyond the module-boundary refactor itself

## Risks
- direct import rewiring could surface hidden coupling that the current giant
  files masked
- an incomplete split could simply recreate the same monolith under a new
  filename
- broad packet regressions are possible if the refactor lands without a real
  end-to-end test sweep

## Dependencies
- no related bug found
- `B-033` already carries the targeted refactor discipline umbrella
- `B-062` and `B-063` recently expanded the exact Context Engine modules that
  now need structural cleanup

## Success Metrics
- the targeted oversized Context Engine modules are replaced by smaller owned
  modules with direct imports and no compatibility shims
- Context Engine behavior remains green across packet, benchmark, and surface
  regression suites
- the Context Engine component spec names the new module boundaries clearly

## Validation
- focused unit coverage for the refactored projection, session-packet, and
  hot-path modules
- broader Context Engine, benchmark, and surface regression bundles
- `git diff --check`

## Rollout
Bind the refactor as a dedicated child of the refactor-discipline umbrella,
land the hard module split with direct rewiring, and prove it with a broader
regression run before carrying more feature work into the same area.

## Why Now
The repo already knows these files are oversized. Waiting until the next
feature lands would only make the decomposition harder and less trustworthy.

## Product View
The Context Engine should feel like a maintained runtime, not a pile of
successful accidents in a few central files. Smaller owned modules are part of
the product contract when the engine is this central.

## Impacted Components
- `odylith-context-engine`
- `benchmark`

## Interface Changes
- none intended at the public CLI level
- internal Context Engine module boundaries become explicit and directly owned

## Migration/Compatibility
- behavior-preserving refactor only
- internal imports should move directly to the new modules; compatibility
  facades and alias wrappers are out of scope by design

## Test Strategy
- characterize current packet and query behavior first through targeted tests
- add direct coverage for the new module seams
- rerun broad Context Engine, benchmark, and surface regressions after the
  split

## Open Questions
- whether a later wave should decompose `odylith_context_engine_store.py`
  itself after the helper-module split proves stable
