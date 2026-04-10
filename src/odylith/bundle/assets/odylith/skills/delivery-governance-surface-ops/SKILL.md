# Delivery Governance Surface Ops

Use this skill for substantive grounded repo work when Odylith should keep backlog, plans, components, Atlas, Casebook, Compass, and closeout truth synchronized automatically.

## Lane Boundary
- Consumer lane:
  - use `./.odylith/bin/odylith` for Odylith commands
  - validate repo code with the consumer repo's own toolchain
- Product-repo maintainer mode:
  - pinned dogfood posture proves the shipped runtime
  - detached `source-local` posture is the explicit live-source dev lane
- Interpreter choice does not control which repo files the agent may edit.

## Default Flow
- ground the slice through Odylith packets first
- keep commentary focused on the slice, the repo truth, and the validation plan; avoid narrating startup, routing, or degraded-attempt internals unless the user needs a command or a blocker explanation
- keep Odylith ambient by default during work; weave grounded governance facts into ordinary updates and only emit explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` lines when they materially change the next move
- when closeout would benefit from naming Odylith, use at most one short `Odylith Assist:` line; prefer `**Odylith Assist:**` when Markdown formatting is available. Lead with the user win, link updated governance ids inline when they were actually changed, frame the edge against `odylith_off` or the broader unguided path when the evidence supports it, and back it with concrete observed counts, measured deltas, or validation outcomes while keeping it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Silence is better than filler.
- search existing workstream, plan, bug, component, diagram, and session or Compass context before writing
- extend, consolidate, or reopen existing truth before creating new governed records
- create a missing workstream and bound plan before non-trivial implementation when the slice is genuinely new
- in the Odylith product repo, name Radar workstreams after the slice itself and do not prefix the title with `Odylith`
- add child workstreams or execution waves when the slice is truly umbrella-shaped
- use the release-planning contract when the operator talks about `current release`, `next release`, `release x.y.z`, or adding/removing/moving `B-###` work between releases
- suggest or deepen Registry components and living specs when new or clarified system boundaries appear
- update or create Atlas coverage when a materially changed flow, seam, or contract lacks truthful diagrams
- run Casebook preflight and capture named failures or repeat-debug loops in the same turn
- keep Compass updates intent-first and carry forward constraints plus validation obligations
- treat Compass voice as governed truth: plainspoken grounded maintainer narration in ordinary words, with no stock framing, house phrases, queue-label restatement, repeated window leads, generic priority wrappers, rhetorical benchmark challenges, stagey metaphor, or canned current/next/why/timing scaffolding in Compass-facing summaries or updates
- keep Compass cheap too: the one bounded Compass refresh should stay deterministic and provider-light, timeline audit inputs should be reused instead of recomputed through model calls, and if a user asks for a "full" Compass refresh the correct command is still `odylith compass refresh --repo-root . --wait`; do not add a Compass-specific `full` flag or second mode
- use Delivery Intelligence's shared Scope Signal Ladder when deciding what
  deserves default visibility, promotion, or expensive compute:
  - `R0 suppressed_noise`
  - `R1 background_trace`
  - `R2 verified_local`
  - `R3 active_scope`
  - `R4 actionable_priority`
  - `R5 blocking_frontier`
- do not rebuild urgency heuristics locally in Compass, Radar, Registry,
  Atlas, shell, or guidance once `scope_signal` exists
- treat `scope_signal.budget_class` as provider-neutral policy:
  - `none`
  - `cache_only`
  - `fast_simple`
  - `escalated_reasoning`
- low-signal scopes stay hidden by default; explicit deep links may remain but
  they must render quiet instead of borrowing global activity
- keep closeout surfaces explicit
- prefer proof bundles over prose summaries
- fail closed when the evidence is incomplete
- use strict refresh and strict check intentionally, not interchangeably

## Canonical Commands

```bash
./.odylith/bin/odylith context-engine --repo-root . governance-slice --working-tree
./.odylith/bin/odylith sync --repo-root .
./.odylith/bin/odylith dashboard refresh --repo-root .
./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces shell,radar,compass
./.odylith/bin/odylith dashboard refresh --repo-root . --surfaces atlas --atlas-sync
./.odylith/bin/odylith sync --repo-root . --force --impact-mode full --check-clean
./.odylith/bin/odylith sync --repo-root . --check-only --check-clean --runtime-mode standalone
./.odylith/bin/odylith validate plan-traceability --repo-root .
./.odylith/bin/odylith validate plan-risk-mitigation --repo-root .
./.odylith/bin/odylith release list --repo-root .
./.odylith/bin/odylith release show current --repo-root .
./.odylith/bin/odylith release update current --repo-root . --status shipped
./.odylith/bin/odylith release add B-123 current --repo-root .
./.odylith/bin/odylith release move B-123 next --repo-root .
./.odylith/bin/odylith atlas auto-update --repo-root . --from-git-working-tree --fail-on-stale
./.odylith/bin/odylith atlas render --repo-root . --fail-on-stale
./.odylith/bin/odylith compass log --repo-root . --kind implementation --summary "<intent-first update>"
./.odylith/bin/odylith compass watch-transactions --repo-root . --interval-seconds 15
```

## Rules

- Treat this skill as Odylith's governance-autopilot loop, not as optional closeout polish.
- Release planning is additive:
  - execution waves stay the umbrella execution contract
  - release planning stays the repo-local target-ship contract
  - the canonical maintainer publication lane stays separate again
- Keep the operator wording simple:
  - release planning answers "what release should this workstream ship in?"
  - program or wave planning answers "how should this umbrella effort execute?"
  - a workstream may appear in both because ship target and execution order are different facts
- Use concrete examples when teaching or updating shell guidance:
  - `B-067 -> 0.1.11` is release planning
  - `B-021 -> W1, W2, W3` is program/wave planning
- Release selectors are exact and fail-closed. Prefer `release:<id>` when a natural-language name or version could be ambiguous.
- `current` and `next` are explicit aliases owned by source truth, not inferred from semver or dates.
- The current active release stays visible in Compass and other governed read
  surfaces until an explicit `shipped` or `closed` release update. Zero
  targeted workstreams is an empty state, not implicit GA.
- Finished work removed during closeout can still appear as completed release
  history in Compass; do not confuse that readout with active release
  targeting.
- One workstream may have at most one active release target. Use `move`, not a second `add`, when work carries forward.
- `finished`, `parked`, and `superseded` workstreams must not stay in active releases, and `shipped` or `closed` releases must not keep mutable active planning state.
- Release `name` is explicit operator-owned source truth. Matching authored
  release notes may exist for the same `version`, but they must never rename
  or override the release-planning record without explicit maintainer
  authorization.
- If `name` is blank, governed release surfaces may fall back to `version`,
  then `tag`, then `release_id`; they must never inherit a release-note title
  as the release name.
- Interactive `B-###` workstream buttons are a separate compact contract from
  generic identifier links and labels. Use the shared workstream-button
  primitive in `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`
  across Compass, Radar, release views, and execution-wave stacks; do not
  locally resize or repad those controls in renderer/template CSS.
- Interactive `B-###` workstream buttons also share one navigation contract:
  they open Radar. Do not point those buttons at Compass-local scope routes or
  other surface-local views; keep local scoping as separate row/disclosure
  behavior instead.
- Generic chip or label selectors must explicitly exclude interactive `B-###`
  controls so broader styling cannot silently re-inflate workstream buttons.
- Compass `Release Targets` layout is also operator-owned. Keep
  `Targeted Workstreams` and `Completed Workstreams` on the established stacked
  format, and do not reintroduce side-by-side or auto-fit multi-column release
  boards through renderer or shared-CSS changes unless the operator explicitly
  authorizes that layout change.
- Treat top-line governance KPI/stat cards as a shared shell contract too.
  Compass hero KPIs, Radar summary stats, Registry summary KPIs, and
  Casebook summary KPIs should consume the shared Dashboard KPI helpers for
  grid, card surface, and label/value typography instead of carrying local
  stat-card CSS in templates or renderers.
- If a surface owns source-generated shell assets, keep one canonical loader
  or generator path, refresh live and bundled mirrors together, and do not
  keep a static fork of generated shared CSS when shared plus thin overrides
  will do.
- When a slice touches operator-owned shell layout or workstream-button
  contracts, rerun headless browser proof in both standard and compact shell
  layouts instead of relying on static selector checks alone.
- When a slice touches governance KPI/stat cards, rerun headless browser proof
  for computed card padding/radius, label/value typography, and current-release
  labeling across Compass, Radar, Registry, and Casebook.
- That browser proof must click representative `B-###` controls in Compass
  current-workstream rows, Compass release/execution-wave stacks, Atlas, and
  Registry and verify the shell lands on the Radar workstream route.
- `dashboard refresh --repo-root .` is the low-friction render-only refresh path when you need the shell current without running the full governance pipeline. It refreshes `tooling_shell`, `radar`, and `compass` by default, prints the included and excluded surfaces, and points at `--surfaces atlas --atlas-sync` when Atlas is stale but excluded.
- `sync --force --impact-mode full --check-clean` is the authoritative write-mode refresh gate.
- `sync --check-only --check-clean --runtime-mode standalone` is the authoritative non-mutating clean proof lane.
- Refresh and shell upkeep must stay local and deterministic when the Tribunal reasoning artifact is absent; do not wait on opportunistic provider enrichment just to refresh governed surfaces.
- If explicit Tribunal provider enrichment times out during a run, keep the remaining cases deterministic instead of retrying the same unhealthy provider path across the whole queue.
- If strict sync is blocked only by Mermaid freshness, repair Atlas first, rerender, then rerun the strict gate.
