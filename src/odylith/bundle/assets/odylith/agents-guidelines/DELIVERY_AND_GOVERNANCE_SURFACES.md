# Delivery And Governance Surfaces

- Odylith should carry closeout obligations, validation bundles, and affected-surface truth together.
- Surface updates should be driven from grounded packet output, not freehand heuristics.
- The right goal is truthful closeout with less operator effort, not more narration.
- If a surface lacks enough evidence, keep the fail-closed posture and ask the operator to widen.

## Source Contracts
- Use the local source contracts under `odylith/` as the operational authority for their surfaces:
  - `odylith/radar/source/AGENTS.md`
  - `odylith/technical-plans/AGENTS.md`
  - `odylith/casebook/bugs/AGENTS.md`
  - `odylith/registry/source/AGENTS.md`

## Consumer Boundary
- In consumer repos, an Odylith product issue uses these surfaces for diagnosis, not self-directed mutation.
- Gather evidence from Radar, Atlas, Registry, Casebook, Compass, and plans as usual, but stop at handoff-ready feedback instead of editing Odylith truth locally.

## Governance Autopilot
- Treat this as the default for substantive grounded repo work when the slice is repo-owned work.
- Do not wait for explicit bookkeeping instructions before checking Radar, technical plans, Registry, Atlas, Casebook, Compass, and session context.
- Start by searching for the existing workstream, active plan, related bugs, related components, related diagrams, and recent Compass or session context for the slice.
- Extend, consolidate, or reopen existing truth before creating parallel records; in consumer Odylith-fix requests, use that evidence to hand off instead of mutating Odylith truth.
- If no matching workstream exists and the slice is repo-owned work, create one and bind a plan before continuing non-trivial implementation; otherwise capture the missing workstream, plan, or bug as handoff-ready feedback.
- If the slice is genuinely multi-lane or umbrella-shaped, add child workstreams or execution waves instead of hiding separate streams inside one backlog note.
- If execution reveals an important untracked system or a materially changed boundary, suggest or create the missing Registry component and deepen the living spec in the same change; in consumer Odylith-fix requests, stop at a component-ready handoff packet.
- If Atlas coverage is missing or stale for a materially changed flow, contract, or operator seam, update the existing diagram or create a new one in the same slice; in consumer Odylith-fix requests, stop at a handoff-ready Atlas evidence packet.
- Always run Casebook preflight: search existing bugs first, record `no related bug found` when true, and capture a new bug immediately for a named failure mode or repeated-debug loop.
- Keep Compass and session context current with intent, constraints, validation obligations, artifact links, and major decisions so the next turn inherits real repo memory instead of starting cold.
- Fail closed when evidence is too weak to update a governed surface truthfully.

## Severe Bug Capture
- Casebook preflight is not optional when the slice exposes a named failure mode, repeat-debug loop, or correctness-sensitive breakage.
- When a P0/P1 failure, repeat-debug loop, or broken invariant is diagnosed clearly enough to name the failure mode, capture it in Casebook immediately instead of waiting for the end of the thread.
- In consumer Odylith-fix requests, produce a Casebook-ready handoff payload instead of editing `odylith/casebook/bugs/` locally.
- Add or update the bug markdown entry under `odylith/casebook/bugs/`, update `odylith/casebook/bugs/INDEX.md`, and refresh governed surfaces once the operator-visible signature is stable enough to prevent rediscovery.
- Minimum severe-bug payload: failure signature, trigger path, invariant violated, workaround, code references, regression coverage, and the next guardrails or preflight checks for future agents.
- Repeated loop debugging counts as severe even before broad blast radius is proven if the same hidden invariant is causing agents to fix, rerun, and rediscover nearby failures without durable repo memory.

## Workstream, Plan, And Phase Truth
- Treat `Workstream` as the primary entity name and `idea` as the earliest stage.
- Before adding new work, review `odylith/radar/source/INDEX.md` plus nearby idea specs for duplicates or adjacent scope.
- If related scope already exists, update or consolidate the existing workstream instead of creating a parallel duplicate.
- Backlog upkeep is part of normal implementation even when the user asked for code, docs, or debugging rather than explicitly asking for backlog edits.
- Queued backlog items are not self-starting implementation grants. Unless the user explicitly asks to work a queued item, Odylith and agents must not start implementing it automatically just because it appears in Radar, Compass, the shell, or another queue surface.
- When the user asks to add, create, reprioritize, or promote backlog work, run the full workflow in the same turn.
- Canonical backlog lifecycle states are:
  - `queued`
  - `planning|implementation`
  - `parked`
  - `finished`
  - `superseded`
- Canonical plan storage lanes are:
  - `odylith/technical-plans/in-progress/`
  - `odylith/technical-plans/parked/YYYY-MM/`
  - `odylith/technical-plans/done/**`
- Treat workstream lineage as first-class typed metadata:
  - `workstream_reopens` <-> `workstream_reopened_by`
  - `workstream_split_from` <-> `workstream_split_into`
  - `workstream_merged_into` <-> `workstream_merged_from`
- Active-plan binding is fail-closed for touched work:
  - active plan rows cannot remain unbound
  - queued bindings must advance when meaningful implementation evidence exists
  - finished bindings must create a truthful successor instead of mutating closed lineage
- Canonical phase promotion is one-way and evidence-gated:
  - allow only `planning -> implementation` auto-promotion
  - require semantic implementation evidence plus non-generated source-file touch
  - never auto-demote to planning during quiet periods
- Global/generated coordination artifacts are not strict workstream implementation evidence by themselves.
- For new workstream intake:
  - create or update the idea spec under `odylith/radar/source/ideas/YYYY-MM/` using the template contract
  - compute ordering with the Radar ordering model
  - reorder `odylith/radar/source/INDEX.md` with truthful rationale
  - bind new implementation plans to existing workstreams first, or backfill the workstream before continuing implementation
  - keep the bound `B-###` visible in the active plan and implementation handoff
- If the slice outgrows one truthful workstream, split it explicitly with child workstreams, lineage metadata, or umbrella execution waves instead of overloading one record.
- When execution pauses before completion, use the parked lifecycle honestly: move the plan to `odylith/technical-plans/parked/YYYY-MM/`, clear active-plan binding, and keep the workstream visible as parked instead of pretending it is done.
- Incomplete work must never move to done-plan storage just to reduce active counts.
- When lifecycle semantics change, evolve the whole set together:
  - source contracts under `odylith/radar/source/` and `odylith/technical-plans/`
  - source indexes and section membership
  - validators and renderers
  - targeted tests
  - guidance docs

## Refresh, Sync, And Clean Proof
- `odylith dashboard refresh --repo-root .` is the low-friction shell-facing refresh path.
- `odylith sync --repo-root . --force --impact-mode full --registry-policy-mode enforce-critical --enforce-deep-skills` is the strict canonical refresh path.
- `odylith sync --repo-root .` is the normal selective fast path for in-session upkeep.
- Use `--check-commit-ready` for staged commit validation and `--check-clean` for strict clean-snapshot proof; do not conflate those contracts.
- Do not rely on the optional autosync hook against a mixed staged/unstaged worktree.
- Consumer-shell freshness warnings are advisory only: they may point at fresher runtime state or mixed local truth, but they must not become implicit permission for background tracked-file mutation.
- If strict sync is blocked only by Mermaid freshness, repair that with `odylith atlas auto-update ...`, rerender Atlas, then rerun the strict sync gate.
- Compass runtime snapshots under `odylith/compass/runtime/*` remain local high-churn artifacts and should stay uncommitted.

## Registry, Atlas, And Component Specs
- `odylith/registry/source/component_registry.v1.json` is the component inventory source of truth.
- First-class components must keep `category`, `qualification`, `what_it_is`, `why_tracked`, and `spec_ref` truthful in the same change.
- `spec_ref` must point at the living canonical spec, and every living spec must keep:
  - `## Requirements Trace` block markers
  - `## Feature History` bullets in `- YYYY-MM-DD: ...` format
- When a slice touches the component registry, component living specs, Atlas catalog, or workstream `related_diagram_ids`, reconcile Registry-to-Atlas coverage in the same change.
- Do not leave a first-class component linked to only some materially relevant Atlas diagrams.
- When execution reveals an important untracked system, control, infrastructure, or data surface, actively suggest a Registry component in the same turn; prefer a reviewed `candidate` entry over silent omission when curated promotion is premature.
- Component living specs under `odylith/registry/source/components/<component-id>/CURRENT_SPEC.md` are governance contracts, not optional documentation.
- When a conversation changes or clarifies component behavior, requirements, controls, or rationale, update the living component spec in the same slice.
- When a component already exists but its living spec is too shallow for the now-grounded behavior, deepen it with technically specific boundaries, responsibilities, interfaces, controls, validation obligations, and feature-history context instead of leaving it as a thin placeholder.
- Every `## Feature History` bullet in `odylith/registry/source/components/*/CURRENT_SPEC.md` must include the canonical rendered Radar plan link, not a raw technical-plan path.
- The canonical provenance format is:
  - `- YYYY-MM-DD: summary (Plan: [B-###](../../../odylith/radar/radar.html?view=plan&workstream=B-###))`
- When touching a spec, backfill missing feature-history plan links in the same change instead of leaving mixed provenance quality behind.
- Keep component-spec requirement evidence synchronized through `odylith governance sync-component-spec-requirements ...`; the component spec is the living contract, not transient timeline cards.
- Keep one canonical source of requirement history per component spec; do not duplicate feature-history narratives in ad hoc side panels.
- Meaningful Codex timeline events must map to at least one component via explicit tags or deterministic inference.
- Component-governance audit streams are fail-closed, and deep-skill enforcement stays centralized in validator/sync paths rather than copied into renderer-local policy.
- Skill trigger mappings in component specs use structured tiers:
  - `### Baseline`
  - `### Deep`
- The current enforced deep-skill components are `kafka-topic` and `msk`; expand only with explicit policy or risk rationale.
- Registry forensic coverage is channelized, not guessed from a generic event count. Every tracked component must surface one of:
  - `forensic_coverage_present`
  - `baseline_forensic_only`
  - `tracked_but_evidence_empty`
- Live-gap language must derive mechanically from the absence of Registry's three live evidence channels:
  - explicit Compass events
  - recent tracked path matches
  - mapped workstream-linked evidence

## Compass Standup Contract
- Compass standup is AI-authored only, but deterministic runtime evidence still owns fact selection, ranking, and fail-closed validation.
- The standup contract should stay compressed and causal: verified movement, current proof, forcing function, impact, and the most relevant watch item should dominate over generic portfolio narration.
- `Why this matters` must pair the customer or use-story need with the architecture or operator consequence explicitly.
- `Next planned` should synthesize actionable near-term work, not just file paths, deferred scope, or generic portfolio posture.
- Cache reuse must stay freshness-bound and fail closed; stale or missing provider output should not masquerade as live progress.

## Lifecycle Closeout
- Treat lifecycle reconciliation as part of implementation, not postscript cleanup.
- Before claiming a slice is complete, reconcile each touched plan/workstream pair to exactly one truthful state: finished, still implementation, or parked.
- Finished work must move to done-plan storage, set the bound workstream to finished, update plan and workstream indexes, and refresh impacted governed surfaces.
- Partially implemented active work stays in `odylith/technical-plans/in-progress/` with explicit residual scope.
- Minimum lifecycle validation is the backlog, traceability, risk-mitigation, and strict sync proof path.

## Compass Timeline And Operator Evidence
- Log meaningful implementation decisions and slices through `odylith compass log ...` or `odylith compass update ...` with workstream, component, and artifact linkage whenever known.
- Carry active intent, constraints, validation obligations, and unresolved questions forward in Compass/session updates so future agents inherit the current operating context instead of reconstructing it from scratch.
- Plan links shown to users must target the canonical rendered Radar plan route, not raw `odylith/technical-plans/**/*.md` files.
- Keep Compass transaction headlines intent-first and outcome-first; never degrade to file-count-only labels.
- Treat Registry synthetic workspace activity as forensic-only support for timelines, not as a replacement for explicit Compass decision or implementation logging.
- `odylith compass watch-transactions --repo-root . --interval-seconds <n>` is the supported near-real-time local watcher for transaction cards and Radar execution overlays.

## Backlog Execution Programs
- Umbrella-owned execution waves are a repo-local backlog contract, not ad hoc plan prose.
- Canonical source files are:
  - umbrella opt-in metadata in `odylith/radar/source/ideas/**` via `execution_model`
  - program definitions in `odylith/radar/source/programs/<umbrella-id>.execution-waves.v1.json`
  - additive traceability output in `odylith/radar/traceability-graph.v1.json`
- `execution_model: umbrella_waves` is valid only for umbrella workstreams.
- Validation fails closed for missing companion files, non-umbrella owners, non-reciprocal parent/child topology, duplicate same-wave role assignment, unknown wave references, and gate refs whose `plan_path` no longer matches the bound workstream plan.
- Execution-program metadata is additive only. Generic workstream topology stays canonical for repo-wide relationships, and deployment waves are a separate concept.
- When umbrella-owned execution waves evolve, update the program files, validator/traceability consumers, tests, and docs together in the same slice.

## Odylith Intelligence Plane
- Installed `odylith sync` owns observation, posture recompute, approval state, and clearance lifecycle orchestration.
- Odylith owns signal intake, posture, approval, and clearance; Tribunal owns adjudication and briefs; Remediator owns bounded packets and execution metadata.
- The lifecycle stays ordered: Observe -> Triage -> Adjudicate -> Packetize -> Await Approval -> Apply or Delegate -> Await Clearance.
- Tracked-file mutation proposals remain approval-gated and bounded by validation, rollback, and stale-packet checks.
