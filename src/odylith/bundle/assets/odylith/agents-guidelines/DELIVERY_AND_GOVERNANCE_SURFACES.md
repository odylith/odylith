# Delivery And Governance Surfaces

- Odylith should carry closeout obligations, validation bundles, and affected-surface truth together.
- Surface updates should be driven from grounded packet output, not freehand heuristics.
- The right goal is truthful closeout with less operator effort, not more narration.
- If a surface lacks enough evidence, keep the fail-closed posture and ask the operator to widen.

## Source Contracts
- Use the local source contracts under `odylith/` as the operational authority for their surfaces:
  - `odylith/radar/source/AGENTS.md`
  - `odylith/radar/source/releases/AGENTS.md`
  - `odylith/technical-plans/AGENTS.md`
  - `odylith/casebook/bugs/AGENTS.md`
  - `odylith/registry/source/AGENTS.md`

## Consumer Boundary
- In consumer repos, an Odylith product issue uses these surfaces for diagnosis, not self-directed mutation.
- Gather evidence from Radar, Atlas, Registry, Casebook, Compass, and plans as usual, but stop at maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.

## Governance Autopilot
- Treat this as the default for substantive grounded repo work when the slice is repo-owned or maintainer-authorized Odylith work.
- Do not wait for explicit bookkeeping instructions before checking Radar, technical plans, Registry, Atlas, Casebook, Compass, and session context.
- Start by searching for the existing workstream, active plan, related bugs, related components, related diagrams, and recent Compass or session context for the slice.
- Extend, consolidate, or reopen existing truth before creating parallel records; in consumer Odylith-fix requests, use that evidence to hand off instead of mutating Odylith truth.
- If no matching workstream exists and the slice is repo-owned or maintainer-authorized Odylith work, create one and bind a plan before continuing non-trivial implementation; otherwise capture the missing workstream, plan, or bug as maintainer-ready feedback.
- If the slice is genuinely multi-lane or umbrella-shaped, add child workstreams or execution waves instead of hiding separate streams inside one backlog note.
- If execution reveals an important untracked system or a materially changed boundary, suggest or create the missing Registry component and deepen the living spec in the same change; in consumer Odylith-fix requests, stop at a component-ready maintainer payload instead of editing Registry.
- If Atlas coverage is missing or stale for a materially changed flow, contract, or operator seam, update the existing diagram or create a new one in the same slice; in consumer Odylith-fix requests, stop at a maintainer-ready Atlas evidence packet instead of editing Atlas truth.
- Always run Casebook preflight: search existing bugs first, record `no related bug found` when true, and capture a new bug immediately for a named failure mode or repeated-debug loop.
- Keep Compass and session context current with intent, constraints, validation obligations, artifact links, and major decisions so the next turn inherits real repo memory instead of starting cold.
- Fail closed when evidence is too weak to update a governed surface truthfully.
- Scope visibility, promotion, and expensive compute budgets now share one
  ladder contract. Do not rebuild urgency heuristics locally once Delivery
  Intelligence has published `scope_signal`.
- The canonical ladder is:
  - `R0 suppressed_noise`
  - `R1 background_trace`
  - `R2 verified_local`
  - `R3 active_scope`
  - `R4 actionable_priority`
  - `R5 blocking_frontier`
- Default operational views should hide low-signal scopes by default rather
  than inventing a fake "activity" story from governance-only churn, generated
  churn, or broad fanout evidence.
- Preserve explicit deep links for low-signal scopes, but keep them quiet:
  unavailable brief or empty local timeline is honest; borrowed global
  activity is not.
- `scope_signal.budget_class` is the shared compute gate:
  - `none`
  - `cache_only`
  - `fast_simple`
  - `escalated_reasoning`
- Keep that budget contract provider-neutral. Map it onto Codex, Claude, or
  future hosts in adapter code, not in product guidance.

## Severe Bug Capture
- Casebook preflight is not optional when the slice exposes a named failure mode, repeat-debug loop, or correctness-sensitive breakage.
- When a P0/P1 failure, repeat-debug loop, or broken invariant is diagnosed clearly enough to name the failure mode, capture it in Casebook immediately instead of waiting for the end of the thread.
- In consumer Odylith-fix requests, produce a Casebook-ready payload for the maintainer instead of editing `odylith/casebook/bugs/` locally.
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
  - in the Odylith product repo, title the slice directly and do not prefix the Radar workstream title with `Odylith`
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

## Release Planning Truth
- Release planning is a separate additive contract. It does not replace generic workstream topology, umbrella execution waves, or the canonical maintainer publication lane.
- Use release planning when the operator is answering "what release should this workstream ship in?"
  Example: `B-067 -> 0.1.11` through `odylith release add B-067 0.1.11`.
- Use program or wave planning when the operator is answering "how should this umbrella effort execute?"
  Example: umbrella `B-021 -> W1, W2, W3` through the umbrella execution-wave contract in Radar source.
- One workstream may participate in both contracts at once because release picks the ship lane while waves pick the execution order.
- The canonical source files are:
  - `odylith/radar/source/releases/releases.v1.json`
  - `odylith/radar/source/releases/release-assignment-events.v1.jsonl`
- `release_id` is the immutable source key. `version`, `tag`, and `name` are optional metadata. `current` and `next` are explicit aliases owned by source truth, not inferred from semver or dates.
- One workstream may have at most one active target release at a time. Carry-forward belongs in append-only `move` history or explicit child workstreams, not simultaneous active multi-release membership.
- Use the release authoring CLI instead of inventing prose-only release ownership:
  - `odylith release list`
  - `odylith release show current`
  - `odylith release add B-123 current`
  - `odylith release move B-123 next`
  - `odylith release remove B-123`
  - `odylith release update release:<id> --name "..." --alias current`
- Selector resolution is exact and fail-closed:
  - exact `release_id`
  - explicit alias
  - exact `version`
  - exact `tag`
  - unique exact `name`
- Do not leave `finished`, `parked`, or `superseded` workstreams in active releases.
- Do not mutate a `shipped` or `closed` release except by moving alias ownership off it before lifecycle closure.
- Release `name` is explicit operator-owned source truth. Matching authored
  release notes may exist for the same `version`, but they must never rename
  or override the release-planning record without explicit maintainer
  authorization.
- In practice, release names only change through an explicit
  `odylith release create ... --name` or `odylith release update ... --name`
  operation.
- If `name` is blank, governed release surfaces may fall back to `version`,
  then `tag`, then `release_id`, but never to a release-note title.
- Compass `Release Targets` layout is operator-owned. Keep `Targeted
  Workstreams` and `Completed Workstreams` in the established stacked format,
  and do not reintroduce side-by-side or auto-fit multi-column release boards
  without explicit operator authorization.
- Release-target member progress is operator-facing contract too. Source those
  badges from shared workstream-progress semantics rather than raw
  `plan.progress_ratio`:
  - active implementation with tracked execution work shows the tracked
    percent
  - active implementation with zero checked execution tasks shows
    checklist-only or unknown state, never fake `0% progress`
  - planning or queued work may still show truthful `0% progress`
- Inside those release-member cards, keep the workstream title on its own
  second row under the ID/status chips. Short titles must not collapse back
  into the first row.
- Governance KPI/stat cards are operator-facing shared shell contract too.
  Compass hero KPIs, Radar summary stats, Registry summary KPIs, and Casebook
  summary KPIs must consume the shared grid/card/label-value helpers instead
  of carrying local stat-card CSS forks in source templates or renderers.
- Treat top-line release cards as part of that same shared KPI contract:
  keep the label visible, prefer explicit release truth for the value, and do
  not let local surface styling or stale summary templates improvise a
  different layout.

## Shared Workstream Button Contract
- Interactive `B-###` workstream buttons are a distinct compact shell-surface
  contract, not a side effect of broader identifier-link styling.
- The canonical source is `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`.
- Radar, Compass, execution-wave member stacks, and sibling non-Atlas surfaces
  must consume the shared workstream-button tokens/helpers instead of
  hardcoding local font-size, font-weight, or padding overrides.
- Interactive `B-###` workstream buttons also share one destination contract:
  they open the canonical Radar workstream route, not a local Compass scope or
  another surface-local approximation. Local scope selection belongs in row
  expansion, filter state, or other clearly separate controls.
- Generic chip or label selectors must explicitly exclude interactive
  `B-###` controls; broader chip styling must never resize or repad workstream
  buttons by accident.
- When a surface owns source-generated shell assets, keep one canonical
  generator or loader path and make live checked-in artifacts plus shipped
  bundle mirrors match that output exactly.
- Do not keep static forks of generated shared CSS in local surface templates.
  Compose shared generated CSS plus thin surface-specific overrides only.
- If the workstream-button contract changes, update the shared primitive,
  affected renderers/templates, focused tests, and governed docs/specs
  together in the same slice.
- Headless browser proof must click representative `B-###` controls in
  Compass current-workstream rows, Compass release and execution-wave stacks,
  Atlas workstream pills, and Registry workstream chips, then verify the shell
  lands on `tab=radar&workstream=B-###`.
- The same rule applies to shared shell CSS release-layout overrides: do not
  let Dashboard or Compass base styles silently change the established Compass
  release-target layout. If release layout must change, treat it as an
  operator-approved contract change and update the renderer, shared CSS, tests,
  specs, and Casebook memory together.
- The same discipline applies to top-line KPI/stat cards: do not hardcode
  local `.stats`, `.stat`, `.kpi-card`, `.kpi-label`, or `.kpi-value`
  contracts when the shared Dashboard KPI helpers already express the same
  surface. Update the shared primitive path, affected renderers/loaders,
  browser proof, and governed docs/specs together.
- Operator-owned shell-surface contracts such as compact `B-###` buttons and
  stacked Compass `Release Targets` require headless browser proof in both the
  normal and compact shell layouts, not just string or snapshot assertions.
- Browser proof for shared KPI/stat-card contracts must verify the computed
  padding, radius, label typography, value typography, and release-card
  labeling across Compass, Radar, Registry, and Casebook.

## Refresh, Sync, And Clean Proof
- `odylith sync --repo-root . --force --odylith-mode refresh --registry-policy-mode enforce-critical --enforce-deep-skills` is the strict canonical refresh path.
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
- Meaningful agent timeline events must map to at least one component via explicit tags or deterministic inference.
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
- Compass voice is a product invariant: plainspoken grounded maintainer narration, live spoken maintainer register, human, plain, specific, open, clear, and lightly soulful, not branded dashboard prose or generic portfolio narration.
- The standup contract should stay compressed and causal: verified movement, current proof, forcing function, impact, and the most relevant watch item should dominate over generic portfolio narration.
- Repeated house phrases, workstream-title restatement, repeated window leads, priority or attention wrappers, sloganized self-host status, rhetorical benchmark challenges, and canned next/why/timing scaffolding are invalid even if the underlying facts are true.
- Templating is also a shape failure, not just a phrase failure: Compass should not read like four evenly polished summary cards. Let vividness, asymmetry, and human emphasis survive when the evidence calls for them.
- Stagey metaphor is a failure too. Reject `pressure point`, `center of gravity`, `muddy`, `slippery`, `top lane`, `window coverage spans`, or similar dashboard-wise phrasing even when the facts are current.
- Rhythmic prose is not safer than stock phrases. If bullets settle into repeated claim-then-explanation cadence or sound like a dashboard performing insight, the brief has already drifted.
- Every bullet must stay visibly tethered to the cited fact language. If the cited facts disappear and the sentence still works as a polished status card, it is too generic for Compass.
- Do not reintroduce `Executive/Product` or `Operator/Technical` brief bullets. Compass briefs are unlabeled narrative bullets now, and that rule applies in provider output, deterministic fallback, warmed cache reuse, browser rendering, copied brief text, and legacy compatibility shims.
- Provider output, warmed cache reuse, and deterministic fallback all share the same voice bar. If one path cannot stay natural, it should fall back to plainer fact language, not a different template.
- Deterministic fallback is the live-narration quality floor, not the place to
  hide canned prose. If a Compass test blesses stock fallback wording, rewrite
  or remove the test rather than preserving the stale phrasing.
- Compass should not render a separate `Why this matters` section. Customer need, use-story, and operator consequence belong inside the completed/current/next/risk bullets when they sharpen the point.
- `Next planned` should synthesize actionable near-term work, not just file paths, deferred scope, or generic portfolio posture.
- Cache reuse must stay freshness-bound, voice-valid, and fail closed; stale or missing provider output should not masquerade as live progress, and warmed cache must never replay canned prose back into Compass.
- Timeline audit and window-coverage material should stay deterministic and
  precomputed. Compass brief generation should consume that upstream material
  instead of paying repeated model cost to rediscover the same timeline shape.
- For simple Compass brief enrichment, default to the cheap-fast coding model
  lane: `gpt-5.3-codex-spark` with low reasoning effort. A more expensive
  model needs evidence, not habit.
- Hot-path Compass upkeep is budget-owned. Compass now has only two
  acceptable runtime lanes: unchanged refresh under `50ms` of internal runtime
  work and complete cold shell-safe refresh under `1s` of internal runtime
  work on the normal local path. Do not revive a third slower lane.
- Budget cuts must preserve the live voice contract by defaulting to reuse of
  the last validated brief layer when the narrative-relevant window signature
  is unchanged. Do not spend model or deterministic scoped-brief work just
  because a refresh was requested if the brief story is materially the same.
  Compass now has one bounded refresh contract only; do not revive or
  advertise a second `full` or deep-refresh mode. If a user says "full"
  in prose, route that request to `odylith compass refresh --repo-root . --wait`
  instead of inventing a Compass-specific flag. Refresh may reuse a warmed
  live global brief, and shell-safe global `24h`/`48h` should stay on
  maintained narrated cache before deterministic fallback. It must not pay for
  a fresh provider call on a miss, and it must not let packet-local fact-id
  churn or one old coverage-summary sentence knock a validated narrated global
  brief back into deterministic by default.

## Lifecycle Closeout
- Treat lifecycle reconciliation as part of implementation, not postscript cleanup.
- Before claiming a slice is complete, reconcile each touched plan/workstream pair to exactly one truthful state: finished, still implementation, or parked.
- Finished work must move to done-plan storage, set the bound workstream to finished, update plan and workstream indexes, and refresh impacted governed surfaces.
- Partially implemented active work stays in `odylith/technical-plans/in-progress/` with explicit residual scope.
- Minimum lifecycle validation is the backlog, traceability, risk-mitigation, and strict sync proof path.

## Live Proof Claim Discipline
- For live blocker lanes, unqualified `fixed`, `cleared`, or `resolved` language is only valid after hosted proof advances past the prior failing phase.
- Force three checks before live-resolution language: same fingerprint as the last falsification or not, hosted frontier advanced or not, and whether the claim is code-only, preview-only, or live.
- If the same failure fingerprint returns after a claimed fix, reuse and re-pin the same bug and blocker seam instead of narrating a fresh mystery.
- Do not let docs, UX polish, observability, or broader hardening masquerade as blocker clearance while the live frontier is unchanged.

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
- Repo-local release planning is a separate additive layer again: execution waves describe staged umbrella execution, while releases describe target ship lanes for individual workstreams.
- Keep release closeout lifecycle-driven instead of member-count-driven: the
  current active release stays visible in Compass until an explicit `shipped`
  or `closed` lifecycle update, even if its targeted workstream count falls to
  zero.
- During that closeout window, Compass may show finished work completed in the
  current release as historical completed members while keeping active-target
  membership separate.
- When umbrella-owned execution waves evolve, update the program files, validator/traceability consumers, tests, and docs together in the same slice.

## Odylith Intelligence Plane
- Installed `odylith sync` owns observation, posture recompute, approval state, and clearance lifecycle orchestration.
- Odylith owns signal intake, posture, approval, and clearance; Tribunal owns adjudication and briefs; Remediator owns bounded packets and execution metadata.
- The lifecycle stays ordered: Observe -> Triage -> Adjudicate -> Packetize -> Await Approval -> Apply or Delegate -> Await Clearance.
- Tracked-file mutation proposals remain approval-gated and bounded by validation, rollback, and stale-packet checks.
