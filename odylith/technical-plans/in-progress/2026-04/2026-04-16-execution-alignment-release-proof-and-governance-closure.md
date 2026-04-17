Status: In progress
Created: 2026-04-16
Updated: 2026-04-16
Backlog: B-104

# Execution Alignment Release Proof and Governance Closure

## Goal
Close the Context Engine and Execution Engine alignment program with updated docs, specs, diagrams, release targeting, benchmark corpus proof, registry validation, atlas validation, sync validation, and Compass posture logging.

## Assumptions
- The release target is `v0.1.11`.
- The published claim should be full Odylith assistance versus raw host agent, not grounding-only.
- Workstream closure must follow benchmark, registry, atlas, and sync validation.
- Historical generated history may still contain old names, but active contract language must be canonical Execution Engine.

## Constraints
- Use CLI-backed release assignment and wave gate authoring where commands exist.
- Keep docs and diagrams consistent with the canonical `execution-engine` hard cut.
- Do not claim a wave closed before its tests and governed validation pass.

## Reversibility
Release assignment can be moved with `odylith release move` if target release policy changes. Diagram and spec updates are normal source edits and can be reverted with standard review.

## Related Bugs
No related Casebook bug found.

## Must-Ship
- [x] Assign `B-099` through `B-104` to the active `v0.1.11` release.
- [x] Add gate refs for Waves 1-5.
- [x] Update Context Engine and Execution Engine docs/specs for the canonical handshake, shared snapshot, host parity, and cost metrics.
- [x] Refresh Context and Agent Execution Stack and Execution Engine Stack diagram sources.
- [x] Update benchmark docs and corpus language around full Odylith assistance versus raw host agent.
- [x] Run final focused tests, registry validation, backlog validation, Atlas render checks, sync check, and `git diff --check`.
- [x] Log final posture to Compass after validation.

## Should-Ship
- [x] Keep B-099 umbrella and child workstreams coherent in Radar and release targeting.
- [x] Keep bundle mirrors aligned for benchmark corpus changes.

## Deferred
- Historic archived generated-surface text cleanup.
- Renaming old completed B-072 plan filenames.

## Success Criteria
- The active release contains all alignment workstreams.
- Waves 1-5 have plan gates and can be inspected through the wave CLI.
- Docs, Registry, Atlas, and benchmark proof agree on canonical Execution Engine naming and shared snapshot behavior.
- Final validation passes before closeout.

## Impacted Areas
- `odylith/radar/source/releases/`
- `odylith/radar/source/programs/B-099.execution-waves.v1.json`
- `odylith/technical-plans/`
- `odylith/registry/source/components/`
- `odylith/atlas/source/`
- `docs/`
- benchmark docs and corpus

## Validation Plan
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_execution_engine.py tests/unit/runtime/test_odylith_benchmark_execution_engine.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_odylith_benchmark_corpus.py`
- `PYTHONPATH=src python -m odylith.cli validate component-registry --repo-root .`
- `PYTHONPATH=src python -m odylith.cli validate backlog-contract --repo-root .`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py`
- `PYTHONPATH=src python -m odylith.cli sync --repo-root . --check-only`
- `git diff --check`
