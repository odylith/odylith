Status: Done

Created: 2026-04-07

Updated: 2026-04-07

Backlog: B-059

Goal: Refresh Atlas so the broad runtime maps and the diagram catalog reflect
the real governed memory substrate plus the current runtime/conversation flow,
then add one dedicated memory-substrate map with clean cross-surface links.

Assumptions:
- Atlas already has the right broad runtime map family; the immediate gap is
  stale topology and missing dedicated memory coverage.
- The memory substrate deserves its own diagram because it now has first-class
  Registry components with distinct runtime contracts.
- Broad diagrams should stay readable, so the dedicated memory map will carry
  the denser detail.

Constraints:
- Do not mutate runtime behavior just to make diagrams prettier.
- Keep the new diagram linked to real code, docs, workstreams, and component
  ids so it is governed topology, not decorative architecture art.
- Rerender only the surfaces that actually need the updated diagram truth.

Reversibility: Atlas source and catalog changes are tracked truth. If the new
diagram proves redundant later, it can be merged back into a broader runtime map
without changing runtime state.

Boundary Conditions:
- Scope includes Atlas source, catalog metadata, Atlas component docs, relevant
  Registry diagram references, and focused surface proof.
- Scope excludes new memory-runtime functionality or Atlas renderer feature work.

## Success Criteria
- [x] `D-002`, `D-018`, and `D-020` reflect the governed memory family and the
      current runtime/conversation flow.
- [x] Atlas has a dedicated memory-substrate diagram `D-025`.
- [x] Relevant Registry components link to `D-025`.
- [x] Atlas and any affected generated surfaces rerender cleanly.
- [x] Focused browser proof covers the new memory diagram route and links.

## Impacted Areas
- [x] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [odylith-context-and-agent-execution-stack.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-context-and-agent-execution-stack.mmd)
- [x] [odylith-installable-product-layered-topology.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-installable-product-layered-topology.mmd)
- [x] [odylith-product-runtime-boundary-map.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-product-runtime-boundary-map.mmd)
- [x] [odylith-memory-substrate-compile-retrieval-and-packet-topology.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-memory-substrate-compile-retrieval-and-packet-topology.mmd)
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/atlas/CURRENT_SPEC.md)
- [x] [atlas.html](/Users/freedom/code/odylith/odylith/atlas/atlas.html)
- [x] [registry.html](/Users/freedom/code/odylith/odylith/registry/registry.html)
- [x] [radar.html](/Users/freedom/code/odylith/odylith/radar/radar.html)
- [x] [test_hygiene.py](/Users/freedom/code/odylith/tests/unit/runtime/test_hygiene.py)
- [x] [test_surface_browser_deep.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_deep.py)
- [x] [test_surface_browser_ux_audit.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_ux_audit.py)

## Traceability
### Atlas Source
- [x] Refresh the broad runtime maps.
- [x] Add the dedicated memory-substrate diagram.
- [x] Update catalog metadata and diagram linkage.

### Cross-Surface Truth
- [x] Extend Registry diagram references for the memory components.
- [x] Keep Atlas component docs aligned with the new coverage.

### Proof
- [x] Rerender Atlas and affected generated surfaces.
- [x] Add focused browser proof for the new diagram route.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_hygiene.py tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py`
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py -k 'atlas or registry'`
- [x] `git diff --check`

## Current Outcome
- [x] `B-059` is opened as the governed Atlas refresh slice for the memory
      substrate and updated runtime topology.
- [x] Source, catalog, Registry linkage, and browser proof are complete.
- [x] Atlas now exposes `D-025` as a dedicated memory-substrate map with live
      Registry links for the governed memory family.
- [x] Radar now routes `B-058` into `D-025`, so the memory componentization
      slice points at its dedicated topology artifact instead of only broad
      runtime maps.
