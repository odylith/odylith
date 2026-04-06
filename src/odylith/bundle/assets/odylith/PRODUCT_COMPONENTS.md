# Odylith Product Components

Odylith's governance engine is the product control plane that turns repo-local
truth into grounded developer packets, bounded delegation decisions, diagnosed
delivery cases, and approval-gated remediation guidance. The engine is local
first: tracked files under `odylith/` stay authoritative, while `.odylith/`
holds rebuildable runtime state.

## Governance Engine At A Glance
1. `odylith` CLI materializes, validates, repairs, and drives the product.
2. The Context Engine compiles repo truth into a local projection, memory, and
   packet layer.
3. The Subagent Router decides whether one bounded task stays local or becomes
   one delegated leaf, and if delegated, with which profile.
4. The Subagent Orchestrator decides whether a prompt stays local, becomes one
   routed leaf, or expands into a serial or parallel plan.
5. Tribunal turns delivery scopes into ranked diagnosed cases.
6. Remediator compiles one bounded correction packet per case.
7. Shell, Compass, Registry, Atlas, Radar, and Casebook render the resulting
   posture and evidence.

## Shared Invariants
- Markdown, JSON contracts, and tracked generated artifacts remain the product
  source of truth.
- `.odylith/` state is local-only, host-specific, and safe to rebuild.
- Public operator guidance uses `odylith ...` commands, not module entrypoints.
- Deterministic local reasoning is the baseline; provider enrichment and
  delegated execution are optional overlays with explicit guardrails.
- Grounding should fail open to narrower packets or direct reads. Corrective
  action should fail closed to manual review when scope is not trustworthy.

## Governance Engine Spec Index
- [Odylith](registry/source/components/odylith/CURRENT_SPEC.md)
  Product boundary, public CLI, install/runtime split, tracked vs mutable
  state, and cross-component lifecycle.
- [Odylith Context Engine](registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
  Projection compiler, daemon/client runtime, session packets, local memory
  backend, remote retrieval sync, and runtime snapshots.
- [Subagent Router](registry/source/components/subagent-router/CURRENT_SPEC.md)
  Bounded leaf routing, model/reasoning profile ladder, hard refusal gates,
  host-tool payload generation, and local adaptive tuning.
- [Subagent Orchestrator](registry/source/components/subagent-orchestrator/CURRENT_SPEC.md)
  Prompt decomposition, merge-barrier planning, conservative parallel safety,
  decision ledgers, and orchestration-local tuning.
- [Tribunal](registry/source/components/tribunal/CURRENT_SPEC.md)
  Scope selection, dossier construction, actor memo generation, adjudication,
  provider validation, cache reuse, and queue shaping.
- [Remediator](registry/source/components/remediator/CURRENT_SPEC.md)
  Correction packet compilation, execution-mode selection, stale guards,
  validation and rollback contract, and deterministic apply semantics.

## Read These Specs By Task
- If you are adding or debugging grounding, retrieval, session packets, or
  runtime caches, start with
  [Odylith Context Engine](registry/source/components/odylith-context-engine/CURRENT_SPEC.md).
- If you are changing how one delegated leaf is profiled, gated, escalated, or
  tuned, start with [Subagent Router](registry/source/components/subagent-router/CURRENT_SPEC.md).
- If you are changing prompt fan-out, merge barriers, or ledger-driven subtask
  closeout, start with
  [Subagent Orchestrator](registry/source/components/subagent-orchestrator/CURRENT_SPEC.md).
- If you are changing diagnosis, ranking, confidence, or provider enrichment,
  start with [Tribunal](registry/source/components/tribunal/CURRENT_SPEC.md).
- If you are changing fix packets, deterministic execution, or approval-gated
  action flow, start with [Remediator](registry/source/components/remediator/CURRENT_SPEC.md).
- If you are changing installation, product on/off posture, uninstall
  semantics, or the top-level CLI, start with [Odylith](registry/source/components/odylith/CURRENT_SPEC.md).

## Governance Surface Spec Index
- [Dashboard](registry/source/components/dashboard/CURRENT_SPEC.md)
- [Radar](registry/source/components/radar/CURRENT_SPEC.md)
- [Atlas](registry/source/components/atlas/CURRENT_SPEC.md)
- [Compass](registry/source/components/compass/CURRENT_SPEC.md)
- [Registry](registry/source/components/registry/CURRENT_SPEC.md)
- [Casebook](registry/source/components/casebook/CURRENT_SPEC.md)

Registry separates these surface dossiers from the governance-engine dossiers
through the `category` field in `component_registry.v1.json`.

## Source Tree Map
- Product code: `src/odylith/`
- Tracked product truth and generated checked-in surfaces: `odylith/`
- Mutable install/runtime state: `.odylith/`
- Product registry authority:
  `odylith/registry/source/component_registry.v1.json`
- Product component dossiers:
  `odylith/registry/source/components/`
  Each dossier owns `CURRENT_SPEC.md` and the derived `FORENSICS.v1.json`.
- Repo-local backlog and plans for the current installed repository:
  `odylith/radar/source/` and `odylith/technical-plans/`
- Repo-local bug history for the current installed repository:
  `odylith/casebook/bugs/`

## Developer Working Rules
- Edit source code or source artifacts first, then regenerate checked-in
  outputs.
- Keep public docs and managed guidance aligned between `odylith/` and
  `src/odylith/bundle/assets/odylith/`.
- Do not mirror Odylith product-governance truth into bundled consumer starter
  surfaces. Bundled `registry/source/`, `atlas/source/`, `casebook/bugs/`,
  `radar/source/`, `technical-plans/`, rendered surface payloads, and
  `runtime/source/tooling_shell.v1.json` must stay consumer-safe bootstrap
  assets rather than copies of the upstream source tree's live records.
- Treat `odylith/` as product truth, not as a scratch cache. Anything that is
  local-only, derived, host-specific, or repairable belongs under `.odylith/`.
