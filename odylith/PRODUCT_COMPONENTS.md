# Odylith Product Components

Odylith's governance engine is the product control plane. It turns repo-local
truth into grounded packets, bounded delegation decisions, diagnosed delivery
cases, and approval-gated remediation guidance. Tracked truth lives under
`odylith/`. Rebuildable runtime state lives under `.odylith/`.

## Governance Engine At A Glance

1. `odylith` CLI materializes, validates, repairs, and drives the product.
2. The Context Engine compiles repo truth into local projection, memory, and
   packet layers.
3. The Subagent Router decides whether one bounded task stays local or becomes
   one delegated leaf.
4. The Subagent Orchestrator decides whether a prompt stays local or expands
   into a serial or parallel plan.
5. Tribunal turns delivery scopes into ranked diagnosed cases.
6. Remediator compiles one bounded correction packet per case.
7. Shell, Compass, Registry, Atlas, Radar, and Casebook render the resulting
   posture and evidence.

## Shared Invariants

- Markdown, JSON contracts, and tracked generated artifacts remain the product
  source of truth.
- `.odylith/` state is local-only, host-specific, and rebuildable.
- Public operator guidance uses `odylith ...` commands, not module entrypoints.
- Deterministic local reasoning is the baseline. Provider enrichment and
  delegated execution are explicit overlays.
- Grounding should fail open to narrower packets or direct reads. Corrective
  action should fail closed to manual review when scope is not trustworthy.

## Governance Engine Spec Index

- [Odylith](registry/source/components/odylith/CURRENT_SPEC.md)
  Product boundary, public CLI, install/runtime split, and lifecycle.
- [Odylith Context Engine](registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
  Projection compiler, daemon or client runtime, session packets, and local
  memory.
- [Subagent Router](registry/source/components/subagent-router/CURRENT_SPEC.md)
  Bounded leaf routing, profile selection, and refusal gates.
- [Subagent Orchestrator](registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
  Prompt decomposition, merge barriers, and orchestration planning.
- [Tribunal](registry/source/components/tribunal/CURRENT_SPEC.md)
  Case selection, dossier construction, adjudication, and queue shaping.
- [Remediator](registry/source/components/remediator/CURRENT_SPEC.md)
  Correction packet compilation, execution-mode selection, stale guards,
  validation, and rollback.

## Read These Specs By Task

- Grounding, retrieval, session packets, or runtime caches:
  [Odylith Context Engine](registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- Delegated leaf profiling, gating, or escalation:
  [Subagent Router](registry/source/components/subagent-router/CURRENT_SPEC.md)
- Prompt fanout, merge barriers, or orchestration closeout:
  [Subagent Orchestrator](registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
- Diagnosis, ranking, or provider enrichment:
  [Tribunal](registry/source/components/tribunal/CURRENT_SPEC.md)
- Fix packets, deterministic execution, or approval-gated action:
  [Remediator](registry/source/components/remediator/CURRENT_SPEC.md)
- Install, product on/off posture, uninstall, or top-level CLI:
  [Odylith](registry/source/components/odylith/CURRENT_SPEC.md)

## Governance Surface Spec Index

- [Dashboard](registry/source/components/dashboard/CURRENT_SPEC.md)
- [Radar](registry/source/components/radar/CURRENT_SPEC.md)
- [Atlas](registry/source/components/atlas/CURRENT_SPEC.md)
- [Compass](registry/source/components/compass/CURRENT_SPEC.md)
- [Registry](registry/source/components/registry/CURRENT_SPEC.md)
- [Casebook](registry/source/components/casebook/CURRENT_SPEC.md)

## Source Tree Map

- Product code: `src/odylith/`
- Tracked product truth and generated checked-in surfaces: `odylith/`
- Mutable install/runtime state: `.odylith/`
- Product registry authority:
  `odylith/registry/source/component_registry.v1.json`
- Product component dossiers:
  `odylith/registry/source/components/`
- Product-owned backlog and plans:
  `odylith/radar/source/` and `odylith/technical-plans/`
- Product-owned bug history:
  `odylith/casebook/bugs/`

## Developer Working Rules

- Edit source code or source artifacts first, then regenerate checked-in
  outputs.
- Keep public docs and managed guidance aligned between `odylith/` and
  `src/odylith/bundle/assets/odylith/`.
- Do not mirror Odylith product-governance truth into bundled consumer starter
  surfaces.
- Treat `odylith/` as product truth, not scratch space. Local-only,
  host-specific, or rebuildable state belongs under `.odylith/`.
