Status: Done

Created: 2026-04-07

Updated: 2026-04-07

Backlog: B-058

Goal: Make the memory substrate explicit in Registry by promoting the real
compiler, retrieval, remote, and contract boundaries into first-class
components with comprehensive living specs and a rendered surface that reflects
that topology honestly.

Assumptions:
- The current memory package already contains the right architectural seams; the
  immediate gap is governed visibility, not runtime redesign.
- `odylith-memory-backend` should remain a first-class component, but its path
  ownership should narrow to the backend contract it actually owns.
- Registry is allowed to track multiple adjacent runtime components under the
  same `memory_retrieval` layer when those components have distinct runtime
  contracts and failure posture.

Constraints:
- Do not invent components for trivial helpers or for contracts that have no
  stable runtime or governance meaning.
- Keep the new component boundaries grounded in actual module ownership, runtime
  artifacts, and validation paths.
- Do not widen benchmark required paths or mutate runtime behavior just to make
  the docs read better.

Reversibility: The registry and spec changes are additive source-truth updates.
If a component split proves too fine-grained, Odylith can merge the inventory
later without changing runtime state.

Boundary Conditions:
- Scope includes component inventory, new memory component specs, surrounding
  parent-spec updates, Registry rendering, and validation.
- Scope excludes memory-runtime feature changes, benchmark policy changes, and
  any new remote provider beyond the existing Vespa contract.

Related Bugs:
- [2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-04-registry-live-forensics-miss-source-owned-bundle-mirror-component-activity.md)
- [2026-04-05-memory-substrate-stale-runtime-reuse-and-projection-scope-thrash.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-05-memory-substrate-stale-runtime-reuse-and-projection-scope-thrash.md)

## Success Criteria
- [x] `component_registry.v1.json` tracks explicit memory-substrate components
      for projection bundle, projection snapshot, remote retrieval, and memory
      contracts.
- [x] `odylith-memory-backend` path ownership narrows to its real backend
      contract.
- [x] Each new component has a comprehensive `CURRENT_SPEC.md` with purpose,
      scope, runtime contract, failure posture, validation, and feature
      history.
- [x] The surrounding `registry`, `odylith`, `odylith-context-engine`, and
      `odylith-memory-backend` specs reflect the new hierarchy.
- [x] The rendered Registry surface exposes the new components cleanly.

## Non-Goals
- [x] Rewriting the memory runtime architecture.
- [x] Promoting every memory helper or test fixture into the component
      registry.
- [x] Enabling remote retrieval in benchmark or default runtime posture.

## Impacted Areas
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/registry/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-memory-backend/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-projection-bundle/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-projection-snapshot/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-remote-retrieval/CURRENT_SPEC.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-memory-contracts/CURRENT_SPEC.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)
- [x] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [x] [test_hygiene.py](/Users/freedom/code/odylith/tests/unit/runtime/test_hygiene.py)

## Traceability
### Registry Truth
- [x] Add the new first-class memory components to the manifest.
- [x] Update parent components so subcomponent topology stays explicit.

### Living Specs
- [x] Write comprehensive new dossiers for the newly promoted memory
      components.
- [x] Update existing parent specs so ownership and sibling boundaries do not
      contradict the new manifest.

### Rendered Surface
- [x] Regenerate `odylith/registry/registry.html` and related detail shards.
- [x] Confirm the new components are reachable in Registry detail.

## Risks & Mitigations

- [x] Risk: memory-backend path ownership keeps swallowing adjacent modules.
  - [x] Mitigation: narrow `path_prefixes` to concrete owned files before
        adding sibling components.
- [x] Risk: new specs become stale narrative instead of living contracts.
  - [x] Mitigation: ground each dossier in runtime files, owning modules, test
        paths, and explicit failure posture.
- [x] Risk: Registry surface grows but still feels incoherent.
  - [x] Mitigation: update the surrounding umbrella specs and subcomponent
        links in the same slice.

## Validation/Test Plan
- [x] `PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_hygiene.py`
- [x] `PYTHONPATH=src .venv/bin/python -m odylith.runtime.surfaces.render_registry_dashboard --repo-root . --output odylith/registry/registry.html`
- [x] focused headless Registry browser check on the rendered component detail
      flow
- [x] `git diff --check`

## Rollout/Communication
- [x] Land the source-truth component split first.
- [x] Refresh the rendered Registry surface after the source truth is coherent.
- [x] Call out the new governed memory-component topology in closeout so the
      operator-facing reason for the split is explicit.

## Current Outcome
- [x] `B-058` is opened as the governing workstream for memory-substrate
      Registry coverage.
- [x] Inventory, specs, and rendered Registry updates are complete.
- [x] Registry now surfaces five governed memory-substrate components instead
      of collapsing that topology into one backend silhouette.
- [x] Headless Registry proof now exercises direct shell deep links for the new
      memory components so rendered detail and user navigation stay honest.
