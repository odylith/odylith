Status: Done

Created: 2026-03-26

Updated: 2026-03-27

Goal: Make the public Odylith repo the authoritative home for Odylith product governance, surface-owned truth, and product registry truth, then repoint downstream repos to the Odylith surface/runtime paths and CLI surface.

Assumptions:
- Odylith product code remains under `src/odylith/`.
- Downstream repos keep their own local workstream, plan, bug, and diagram truth.
- Public Odylith product docs must stay generic and free of host-repo branding.

Constraints:
- Do not copy downstream-repo backlog, plan, bug, or diagram content into the public Odylith repo.
- Do not reintroduce downstream-repo-specific branding or path assumptions into public Odylith docs or manifests.
- Keep the user-facing contract on `odylith ...`.

Reversibility: Public governance files are additive. Downstream reference cutovers are path-level and reversible as long as the old repo-local product docs remain in the same branch during migration.

Boundary Conditions:
- Scope includes the public component registry, public product component specs, public local governance roots, and downstream reference cutovers to `odylith/...` product docs.
- Scope excludes moving host-repo truth into Odylith or changing downstream repo domain/runtime ownership.

## Context/Problem Statement
- [x] The public Odylith repo now owns its own component registry, product governance roots, and surface/runtime specs under `odylith/`.
- [x] Source/runtime truth is still duplicated by stale generated outputs, tests, and duplicate root `docs/` copies that point back at deleted shared-doc governance paths.
- [x] A downstream repo still carries Odylith product docs or registry truth as local repo truth instead of using `odylith/...` product paths.

## Success Criteria
- [x] The public repo has its own `odylith/registry/source/component_registry.v1.json`.
- [x] The public repo keeps the canonical current spec for every Odylith component under `odylith/registry/source/components/<component-id>/CURRENT_SPEC.md`.
- [x] The public repo has its own `odylith/radar/source/`, `odylith/technical-plans/`, `odylith/casebook/bugs/`, `odylith/atlas/source/`, and `odylith/compass/runtime/`.
- [x] Downstream product-component references resolve to `odylith/...` surface and runtime docs.

## Non-Goals
- [x] Copying downstream-repo workstreams, plans, bugs, or diagrams into the public repo.
- [x] Rewriting host-repo-owned domain docs or runtime code here.

## Impacted Areas
- [x] [component_registry.v1.json](/Users/freedom/code/odylith/odylith/registry/source/component_registry.v1.json)
- [x] [SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [odylith/radar/source/INDEX.md](/Users/freedom/code/odylith/odylith/radar/source/INDEX.md)
- [x] [odylith/technical-plans/INDEX.md](/Users/freedom/code/odylith/odylith/technical-plans/INDEX.md)

## Traceability
### Runbooks
- [x] [INSTALL_AND_UPGRADE_RUNBOOK.md](/Users/freedom/code/odylith/odylith/INSTALL_AND_UPGRADE_RUNBOOK.md)

### Developer Docs
- [x] [SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [docs/specs/odylith-repo-integration-contract.md](/Users/freedom/code/odylith/docs/specs/odylith-repo-integration-contract.md)
- [x] [PRODUCT_COMPONENTS.md](/Users/freedom/code/odylith/odylith/PRODUCT_COMPONENTS.md)

### Code References
- [x] [src/odylith/cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [src/odylith/runtime/governance/component_registry_intelligence.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/component_registry_intelligence.py)
- [x] [src/odylith/runtime/governance/sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)

## Risks & Mitigations

- [x] Risk: the public governance files exist but are not used by the product runtime.
  - [x] Mitigation: keep the component registry and public specs aligned with runtime paths and use them in focused validation.
- [x] Risk: downstream repos keep referencing stale repo-local product docs.
  - [x] Mitigation: repoint downstream product-component references to `odylith/...` files in the same migration.

## Validation/Test Plan
- [x] `PYTHONPATH=src python -m pytest -q tests/unit tests/integration`
- [x] `PYTHONPATH=src python -m odylith.runtime.governance.validate_component_registry_contract --repo-root . --policy-mode advisory`

## Rollout/Communication
- [x] Land public self-governance first.
- [x] Repoint downstream repos to product docs second.

## Dependencies/Preconditions
- [x] Keep workstream `B-001` active in `odylith/radar/source/INDEX.md`.

## Edge Cases
- [x] Public repo docs drift from bundle docs.
- [x] Downstream repos keep stale local product spec links during migration.

## Open Questions/Decisions
- [x] Decision: public Odylith owns product component specs and registry truth in this repo.
- [x] Decision: downstream repos keep their own governance truth and consume Odylith product docs from `odylith/...`.

## Follow-on
- [x] First public release rehearsal and first real consumer adoption are tracked separately so this repo-complete product-boundary slice can close without recording consumer-specific cleanup inside Odylith.

## Current Outcome
- [x] Public Odylith now owns `odylith/registry/source/component_registry.v1.json`
  plus Registry-owned component dossiers for Odylith, Dashboard, Radar, Atlas,
  Compass, Registry, Casebook, Odylith Context Engine, Subagent Router,
  Subagent Orchestrator, Tribunal, and Remediator under
  `odylith/registry/source/components/`.
- [x] Public Odylith now has working self-governed Radar, Atlas, Compass,
  Registry, Casebook, and shell surfaces under `odylith/`, backed by the local
  product registry and governance roots.
- [x] Public Odylith Atlas now owns the full Odylith product diagram family for
  delivery governance, Tribunal, router/orchestrator topology, and installable
  product/runtime boundaries, with public Registry diagram coverage widened to
  match and downstream Atlas trees pruned back to repo-owned diagrams only.
- [x] Installed Odylith bundles now expose Registry explicitly in the product
  tree, and downstream integration keeps stable installed-product component
  identities so Registry-linked historical evidence stays mapped without
  reauthorizing repo-local product docs.
- [x] Consumer installs now treat `odylith/` as customer-owned bootstrap and
  local truth, keep staged product runtimes under `.odylith/runtime/versions/`,
  pin the intended product version in
  `odylith/runtime/source/product-version.v1.json`, and stop copying the public
  Odylith repo's `odylith/` tree into downstream repositories. Normal upgrades
  now fail closed instead of repairing customer truth, except for the explicitly
  Odylith-managed `odylith/agents-guidelines/` subtree.
- [x] Deep verification closed the remaining product-boundary leaks by keeping
  surface HTML brand links pinned to installed `odylith/surfaces/brand/`
  paths, restoring those brand assets only during first bootstrap or explicit
  repair, pruning live-governance residue from the shipped bundle tree, and
  sanitizing public Casebook history of internal consumer-specific path and
  branding references.
- [x] The written install contract now matches the implementation: first install
  and explicit `doctor --repair` may restore starter metadata and
  `odylith/surfaces/brand/`, while normal upgrades remain limited to
  `.odylith/` plus the managed `odylith/agents-guidelines/` subtree.
- [x] Queued follow-on workstream `B-002` to define Odylith's multi-developer
  collaboration architecture around canonical `project > repo > workspace`
  identity, stable actor attribution, hybrid local-first collaboration state,
  resolved-summary comment durability, and optional hosted augmentation.
- [x] Operational release rehearsal, verified pinned dogfood activation, and
  first consumer install/upgrade/rollback adoption were split into follow-on
  workstream `B-005` so this plan closes on the public product-boundary work
  completed inside the Odylith repo itself.
- [x] Related bug review for that follow-on slice: no related bug found in
  `odylith/casebook/bugs/INDEX.md`.
