---
status: finished
idea_id: B-058
title: Memory Substrate Registry Componentization and Spec Deepening
date: 2026-04-07
priority: P1
commercial_value: 3
product_impact: 5
market_value: 3
impacted_parts: Registry component inventory, memory-substrate boundaries, context-engine traceability, Registry detail rendering, and memory contract documentation
sizing: M
complexity: Medium
ordering_score: 100
ordering_rationale: Odylith already relies on a real multi-part memory substrate, but Registry mostly collapses it into one backend component. That makes the governance surface too coarse exactly where retrieval, projection reuse, remote augmentation, and packet-safety contracts need explicit ownership.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-07-odylith-memory-substrate-registry-componentization-and-spec-deepening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children:
workstream_depends_on: B-001,B-010,B-045
workstream_blocks:
related_diagram_ids: D-002,D-020,D-025
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
Registry does not model the memory substrate with enough fidelity. The public
surface mostly exposes the broad `odylith-memory-backend` boundary while the
actual runtime has distinct compiler bundle, snapshot, remote retrieval, and
contract-sanitization modules with different ownership and failure posture.

## Customer
- Primary: Odylith maintainers using Registry to understand what the memory
  runtime actually is and where a change belongs.
- Secondary: future operators and evaluators who need explicit governed
  boundaries for projection reuse, fallback read models, and remote retrieval.

## Opportunity
If Registry tracks the real memory-substrate seams, Odylith can explain memory
behavior as governed product architecture instead of leaving critical contracts
buried inside one oversized component or one broad Context Engine dossier.

## Proposed Solution
- promote the hidden memory-substrate modules into first-class Registry
  components
- narrow `odylith-memory-backend` path ownership so it no longer swallows the
  whole memory package
- add comprehensive living specs for projection bundle, projection snapshot,
  remote retrieval, and memory contracts
- refresh the surrounding Context Engine, Memory Backend, Registry, and Odylith
  umbrella dossiers so the hierarchy is coherent
- regenerate the Registry surface and add a repo-level guard that fails when
  the memory component inventory collapses again

## Scope
- `odylith/registry/source/component_registry.v1.json`
- new component dossiers under `odylith/registry/source/components/`
- memory-related parent specs that must reference the new component boundaries
- Registry source indexes and rendered Registry surface
- focused contract and render validation

## Non-Goals
- changing the runtime behavior of the memory substrate itself
- redesigning the context-engine module split
- turning every helper function into a first-class component

## Risks
- over-componentization could make Registry noisier instead of clearer
- path ownership could become ambiguous if broad prefixes remain in place
- elaborate specs could drift into architecture fiction if they are not tied to
  the actual runtime contracts and tests

## Dependencies
- `B-001`
- `B-010`
- `B-045`

## Success Metrics
- Registry explicitly tracks the memory substrate beyond one coarse backend
  component
- each new component spec describes a real runtime boundary with concrete files,
  failure posture, and validation
- Registry detail rendering and contract validation stay green

## Validation
- `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_hygiene.py`
- `PYTHONPATH=src .venv/bin/python -m odylith.runtime.surfaces.render_registry_dashboard --repo-root . --output odylith/registry/registry.html`
- focused headless Registry surface audit after render

## Rollout
Land source-truth componentization first, then refresh the rendered Registry
surface and prove the new components are navigable.

## Why Now
The product is leaning harder on memory, retrieval, and Tribunal-backed
diagnosis. If Registry cannot show the real memory architecture, one of
Odylith's most important subsystems stays visually under-governed.

## Product View
Odylith should not have a soulful explanation for memory while Registry shows a
blunt silhouette. The governance surface should reveal the real seams where the
product stores, compiles, sanitizes, and optionally augments memory.

## Impacted Components
- `registry`
- `odylith`
- `odylith-context-engine`
- `odylith-memory-backend`
- `odylith-projection-bundle`
- `odylith-projection-snapshot`
- `odylith-remote-retrieval`
- `odylith-memory-contracts`

## Interface Changes
- Registry gains first-class memory-substrate components and deeper dossiers
- Context Engine and Memory Backend specs link to explicit sibling components
  instead of treating the whole memory package as one undifferentiated detail

## Migration/Compatibility
- additive Registry/source-truth refinement only
- no runtime migration required

## Test Strategy
- validate the component manifest and spec contracts
- rerender Registry and confirm the new components surface in generated detail
  shards
- run a headless Registry check on the rendered surface

## Open Questions
- whether projection bundle and projection snapshot should eventually collapse
  into one higher-level compiler read-model component once their contracts stop
  evolving independently

## Outcome
- Landed on 2026-04-07.
- Registry now tracks the real memory-substrate seams as first-class components:
  projection bundle, projection snapshot, local memory backend, remote
  retrieval, and packet/memory contracts.
- `odylith-memory-backend` no longer claims the whole memory package; its
  governed boundary now matches the actual local backend plus durable
  judgment-memory contract it owns.
- New comprehensive component dossiers now cover compiler bundle, fallback
  snapshot, optional remote retrieval, and packet-safe memory contracts, while
  the Odylith, Registry, and Context Engine umbrella specs were updated to make
  that topology explicit.
- Focused validation proved the source truth, rendered Registry payload, and
  headless Registry deep-link flow all agree on the new components.
- Atlas now has a dedicated memory-substrate map `D-025`, so the Registry
  memory family points at one governed topology artifact instead of forcing
  maintainers to reconstruct the substrate from broad runtime diagrams alone.
