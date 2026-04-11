# Compass
Last updated: 2026-04-10


Last updated (UTC): 2026-04-10

## Purpose
Compass is Odylith's execution, decision, and runtime-posture surface. It turns
the local timeline stream plus linked governance artifacts into an operator view
of what changed, what is active, what risks or cases dominate, and what the
standup-level summary should be.

## Scope And Non-Goals
### Compass owns
- The local host/Odylith timeline stream.
- Runtime snapshot generation and history retention.
- Timeline grouping and transaction shaping.
- The standup brief pipeline, including provider narration, exact-cache replay,
  and explicit unavailable state under the governed Briefs Voice Contract.
- Current release readouts, grouped current-release member views, and
  per-workstream release chips derived from governed traceability truth, with
  the current active release kept visible until an explicit `shipped` or
  `closed` lifecycle transition and completed release members shown separately
  from active targeting. `next` release truth remains governed source data,
  but Compass does not render it as a top-level operator box by default.
- The Compass HTML shell and bundle.

### Compass does not own
- The authoritative backlog, component inventory, or bug markdown. It projects
  them from Radar, Registry, and Casebook inputs.
- Shell-level routing. Dashboard owns that.

## Developer Mental Model
- Compass is both a live stream and a derived runtime snapshot surface.
- `odylith/compass/runtime/agent-stream.v1.jsonl` is the canonical
  append-oriented local event truth for the surface.
- `odylith/compass/runtime/codex-stream.v1.jsonl` remains a legacy-compatible
  input while checked-in and bundled surfaces migrate.
- Everything else in `odylith/compass/runtime/` is derived from that stream and
  linked governance sources.
- The standup brief must stay truthful when the live narrator is unavailable.
  Compass uses provider narration first, exact same-packet replay second, and
  an explicit unavailable state otherwise.
- The current active release stays visible in `Release Targets` until
  maintainers explicitly mark it `shipped` or `closed`; zero targeted
  workstreams is an empty state, not implicit release closure.
- Compass operator UI shows only the current release in the hero KPI lane.
  `Release Targets` still lists the governed planned release set, with the
  current release called out explicitly inside that section instead of via a
  second top-level KPI box.
- Finished work completed in that active release remains visible in a separate
  completed-members section until explicit ship or closeout; it does not
  become active targeting again.
- The visible Compass runtime snapshot is not allowed to outrank fresher
  release truth. If `odylith/compass/runtime/current.v1.json` drifts from the
  live traceability release read model, Compass must reconcile `Release
  Targets` and `Current Workstreams` from traceability at page load and warn
  the operator that the runtime snapshot is behind.
- `Current Workstreams` is a ranked focus view, not a pre-capped shortlist.
  Compass may rank and narrow that board by the visible window, scope, and
  focus rules, but the backend is not allowed to truncate it to an arbitrary
  fixed row count before those visible filters run.
- In the default unscoped Compass view, `Current Workstreams` is the residual
  focus board after subtracting workstreams already represented in `Programs`
  or `Release Targets`. If a workstream is already visible through one of
  those governance groupings, Compass must not duplicate it in the current
  table; explicit scoped selection is the exception and may still show the
  chosen workstream directly.
- In the default unscoped Compass view, `Release Targets` sections start
  collapsed. Do not auto-expand the current release, the next release, or a
  single visible release on initial render. Explicit scoped workstream
  selection may open the matching release section.
- That release-truth drift warning belongs in Compass's own subtle in-surface
  status banner, not as a duplicated shell-level warning slab above the page.
- Source-truth reconciliation must not invent fake plan progress. If a
  workstream row is patched in from traceability without plan progress,
  Compass leaves progress blank rather than displaying stale or synthetic
  `0% progress`.
- The same no-fake-progress rule applies to execution-wave chips. Missing
  `plan.progress_ratio` is unknown, not `0`, so Compass execution-wave
  summaries must leave the progress chip absent until real plan progress
  exists.
- Visible workstream progress is derived from execution-relevant checklist
  sections only. `Learnings`, `Defer`, `Non-Goals`, `Impacted Areas`,
  `Traceability`, risk/mitigation checklists, and `Open Questions` must not
  dilute the percent shown in Compass.
- If a workstream is already in `implementation` but its execution checklist
  still shows `0/N`, Compass must present that as checklist-only state such as
  `Checklist 0/N`, not as `0% progress`.
- Compass release-target layout is operator-owned: `Targeted Workstreams` and
  `Completed Workstreams` stay on the established stacked format unless the
  operator explicitly authorizes a layout change. Shared shell CSS must not
  silently reintroduce side-by-side or auto-fit multi-column release boards.
- The outer program container should be explicitly titled `Programs`, parallel
  to the `Release Targets` outer container, so the two governance groupings
  read as separate sections before the inner cards begin.
- Those two outer governance containers should also stay subtly tinted by
  family instead of reading as identical plain-white blocks: `Programs`
  keeps the cool execution-governance tint and `Release Targets` keeps a
  distinct release-family tint.
- Program cards and release cards should remain visually distinct in Compass.
  Keep programs on the cool execution-governance tint and give `Release
  Targets` its own subtle release-family surface tint so execution structure
  and ship targeting are separable at a glance without changing the shared
  layout or typography contract.
- Compass program sections must not repeat the program-count chip inside the
  inner focus panel. If the outer section summary already carries `N-wave
  program`, the inner program board should not restate the same chip.
- Within those release-member cards, the ID/status chip row stays first and
  the workstream title stays on a dedicated second row. Do not inline short
  titles back into the first row.
- Interactive `B-###` workstream buttons in `Current Workstreams`,
  `Release Targets`, and execution-wave member stacks must use Dashboard's
  shared compact workstream-button contract rather than Compass-local size or
  padding overrides.
- Compass hero KPI cards must use Dashboard's shared governance KPI/stat-card
  contract as well. Do not keep local stat-tile grid, surface, or label/value
  typography forks in Compass source templates when the shared helper output is
  available.
- Those Compass `B-###` controls must also use Dashboard's canonical Radar
  workstream route. Scope selection for Compass stays in row expansion and URL
  `scope` state; the shared workstream buttons themselves do not navigate to a
  Compass-local scoped view.
- Compass shell CSS and JS assets are source-owned through
  `src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py`.
  Shared execution-wave CSS must compose from the canonical shared generator
  plus only thin Compass-specific overrides, and the live plus bundled shell
  assets must exactly match the frontend-contract loader output.

## Runtime Contract
### Runtime inputs
- `odylith/compass/runtime/agent-stream.v1.jsonl`
- `odylith/compass/runtime/codex-stream.v1.jsonl` as a legacy-compatible input
- `odylith/radar/source/INDEX.md`
- `odylith/technical-plans/INDEX.md`
- `odylith/casebook/bugs/INDEX.md`
- `odylith/radar/traceability-graph.v1.json`
- `odylith/atlas/source/catalog/diagrams.v1.json`

`odylith/radar/traceability-graph.v1.json` is the live release-membership read
model for Compass page-load reconciliation. If the current runtime snapshot
lags that file, Compass must repair the visible release groups and current
workstream list from traceability before the operator trusts the page.

### Generated artifacts
- `odylith/compass/compass.html`
- `odylith/compass/compass-payload.v1.js`
- `odylith/compass/compass-app.v1.js`
- `odylith/compass/runtime/current.v1.json`
- `odylith/compass/runtime/current.v1.js`
- `odylith/compass/runtime/refresh-state.v1.json`
- `odylith/compass/runtime/history/index.v1.json`
- `odylith/compass/runtime/history/restore-pins.v1.json`
- `odylith/compass/runtime/history/YYYY-MM-DD.v1.json`
- `odylith/compass/runtime/history/archive/YYYY-MM-DD.v1.json.gz`
- `odylith/compass/runtime/history/embedded.v1.js`

### Owning modules
- `src/odylith/runtime/surfaces/compass_refresh_runtime.py`
  Shared Compass refresh engine, request-state lifecycle, wait/status contract,
  runtime-mode resolution, and failure recording.
- `src/odylith/runtime/surfaces/render_compass_dashboard.py`
  Render facade, argument parsing, runtime refresh, and shell bundle output.
- `src/odylith/runtime/surfaces/compass_dashboard_base.py`
  Low-churn path, markdown, git, and parsing helpers.
- `src/odylith/runtime/surfaces/compass_dashboard_runtime.py`
  High-churn runtime payload, digest, and history builders.
- `src/odylith/runtime/surfaces/compass_dashboard_shell.py`
  Compass shell HTML/CSS composition.
- `src/odylith/runtime/surfaces/compass_standup_brief_narrator.py`
  AI-authored standup brief pipeline, exact-cache replay, and voice
  validation.
- `src/odylith/runtime/surfaces/update_compass.py`
  Statement capture and surface refresh helper.
- `src/odylith/runtime/surfaces/restore_compass_history.py`
  Explicit restore command for archived Compass history dates.
- `src/odylith/runtime/surfaces/watch_prompt_transactions.py`
  Prompt-transaction watcher integration.

## Command Surface
Compass is exposed through the top-level CLI:
- `odylith compass refresh`
  Canonical Compass runtime refresh command with one bounded refresh contract
  plus explicit `--wait`/`--status`.
- `odylith compass log`
  Append one timeline event.
- `odylith compass update`
  Capture update statements into timeline and standup inputs.
- `odylith compass restore-history`
  Rehydrate archived daily history snapshots back into the active Compass calendar.
- `odylith compass watch-transactions`
  Observe prompt transactions and refresh Compass as activity occurs. This is a
  change-driven path, not a timer-driven refresh loop: it waits on the
  context-engine daemon's projection-fingerprint change signal when available,
  falls back to a local watcher when the daemon is absent, and uses coarse
  polling only as a last resort on machines with no real watcher backend. The
  blocking path stays `shell-safe` so Compass freshness does not spend
  foreground narration credits.

`odylith dashboard refresh --repo-root . --surfaces compass` remains supported
as a compatibility wrapper over the same refresh engine. It is not a separate
Compass orchestration path. The wrapper must finish Compass to a terminal
result before returning control, and any recovery hint from that wrapper must
stay on `odylith dashboard refresh --repo-root . --surfaces compass` rather
than assuming the newly activated launcher already exposes the direct
`odylith compass refresh` subcommand surface.

## Runtime Pipeline
### 1. Collect evidence
Compass loads backlog, plan, bug, diagram, and stream inputs and resolves
component/workstream linkage.

### 2. Select source events
`compass_dashboard_runtime.py` ranks recent events by event kind, workstream
signal, and source-vs-generated artifact mix so implementation and decision
events dominate the visible narrative.

### 3. Build runtime payload
The runtime builder shapes:
- current workstream state
- current release summary
- grouped release-member release-target view, including empty-state visibility
  for the current active release until explicit ship/close and a separate
  completed-members section proven from release history
- recent activity and grouped transactions
- bug and plan summaries
- per-workstream release label and release history summary
- freshness posture
- product-repo self-host posture
- Tribunal or operator readout slices
- standup brief inputs

### 4. Write snapshots and history
`refresh_runtime_artifacts(...)` writes current snapshot files, keeps a 15-day
active daily history lane by default, compresses older daily snapshots into
`history/archive/`, and honors explicit restore pins for older dates that must
remain active. Exact runtime reuse is keyed to the current input fingerprint,
not to a small recency window; when the current payload still matches, Compass
must reuse it and cheaply rewrite today's daily history files instead of
forcing a full runtime rebuild just because the date rolled over.

### 5. Render shell
The shell renderer externalizes the payload and control script into the checked
in surface bundle.

### 6. Reconcile stale runtime truth
At page load, Compass compares the visible runtime snapshot against the live
traceability release read model. If the active release id, targeted members,
completed members, or current-workstream rows drift, Compass patches the view
from traceability, marks the runtime truth guard, and tells the operator to run
`odylith compass refresh --repo-root .` for a fresh bounded snapshot rewrite.

## Scope Signal Ladder Contract
Compass does not own scope escalation anymore. It consumes Delivery
Intelligence's shared `scope_signal` contract and applies these rules:
- scope dropdowns and scoped timelines require `R2+` in the exact active
  window
- deep-linked `R0-R1` scopes remain preserved but render a quiet scoped brief
  plus empty timeline instead of borrowing global activity
- promoted current-workstream lists and whole-window brief focus prefer `R3+`
  scopes
- the shared ladder decides which scopes are verified and visible; it no
  longer owns a second scoped-provider spend gate
- once a scope is verified for the active window, any missing scoped brief for
  that same packet travels in the shared background bundle alongside the
  window's global brief instead of queuing its own provider workflow

Compass must not reintroduce local urgency heuristics for governance-only
churn, generated-only churn, or broad fanout rows once the shared ladder is
present.

## Standup Brief Contract
The canonical brief contract now lives in
[Briefs Voice Contract](../briefs-voice-contract/CURRENT_SPEC.md).

Compass consumes that contract through the prompt, voice validator, cache
epoch, renderer, copied brief text, and fail-closed runtime states:
- Compass brief source states are only `provider`, exact `cache`, or explicit
  `unavailable`.
- Deterministic or templated fallback narration is retired. If Compass cannot
  validate a provider-authored brief and no exact same-packet narrated brief
  exists, the standup panel must say so explicitly.
- Cache is an acceleration layer, not a second narrator. Contract changes must
  rotate the brief epoch and invalidate stale warmed prose.
- Whole-window coverage facts are evidence, not a required workstream roll
  call. Compass must not inject stock coverage bullets just to satisfy
  bookkeeping.
- The brief should read like a thoughtful maintainer talking to a teammate:
  friendly, calm, direct, simple, factual, precise, and human.
- Quiet celebration is allowed when something real landed. Calm reassurance is
  allowed when the work is still shaky. Both still have to stay factual.
- Stock framing, stagey metaphor, portable summary prose, and workstream
  roll-call bullets are correctness failures, not copy polish.
- If the cited facts disappear and a bullet still sounds plausible, Compass has
  drifted into generic narration and the brief is invalid.
- The full standup-brief stage is reserved for ready `provider` or exact
  `cache` briefs. Warming, failed, budget-limited, or unavailable states must
  collapse into a compact truthful status instead of taking the same visual
  weight as a finished narrated brief.
- `Copy Brief` belongs to the live brief contract. Compass should expose it
  only when a real narrated brief is on screen.
- Global and scoped narration are one bundle contract, not two independent
  provider products. For one new runtime packet, Compass warms one narrated
  bundle containing any missing global windows plus any missing verified scoped
  briefs for those windows.
- Scoped briefs are first-class views into that same narrated bundle. Compass
  must not maintain a separate scoped provider queue, a second scoped repair
  ladder, or scope-by-scope narration fanout after refresh.
- Scoped Compass must stay explicit, not silent. When a workstream scope is
  selected, Compass should render that workstream's exact scoped brief when it
  exists. If the scoped brief is still warming but a governed global live brief
  is already available, Compass may temporarily show that global brief only
  with an explicit scoped-warming notice. If neither scoped nor governed global
  live narration is available, Compass must render an explicit scoped
  unavailable state.
- Scoped selection is also fail-closed. The runtime payload publishes
  `verified_scoped_workstreams` per rolling window, and both the scope
  dropdown and the scoped Timeline Audit must derive from that verified set.
  Governance-only local changes and broad fanout transactions stay global
  evidence by default; they must not advertise a scoped window on their own.
- Deep-linked or persisted scope state may be preserved for continuity, but if
  the selected workstream is not verified for the active window, Compass must
  render the quiet/unavailable scoped brief state and an empty scoped timeline
  instead of showing unrelated global audit rows.

## Benchmark-Facing Slice Contract

- When benchmark or focused regression work targets
  `compass_brief_freshness`, the bounded slice is the Compass runtime builder,
  the standup brief narrator, focused Compass tests, this component spec, and
  `odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`.
- Those proof slices must not widen into install, repair, or context-engine
  guidance unless a required path or focused validator points there directly.
- Warm and cold benchmark packets should choose the same truthful Compass slice
  so cache posture changes timing, not the first-pass support surface.

## Timeline Semantics
Compass distinguishes:
- durable implementation and decision events
- operator statements
- bug and plan updates
- self-host posture transition and failed preflight statements
- local changes
- transaction boundaries and grouped activity

Generated-only narrative noise is intentionally deprioritized so dashboard
churn does not drown out meaningful implementation evidence.

## Snapshot-Age Contract
- Compass rolling windows, per-day timelines, and audit-hour detail are anchored
  to the loaded runtime snapshot timestamp, not the browser wall clock.
- If the loaded runtime snapshot is materially stale, Compass must surface that
  explicitly as a warning with the snapshot age and timestamp; it must not
  silently render recent day buckets as if they were live empty days.
- Provider-backed standup narration is a background enrichment path, not a
  blocking refresh dependency. Local timeline, workstream, risk, and KPI
  readouts must remain understandable without foreground provider spend.
- Timeline audits are deterministic and precomputed. They must stay cheap
  enough to feed Compass without model calls on the normal path, and Compass
  should consume that upstream material instead of rediscovering the same
  timeline meaning scope by scope.
- The expensive live narration path is no longer the main long pole on the
  default shell-safe refresh. The remaining runtime wall clock now sits mostly
  in upstream window-fact preparation, so future latency cuts should target
  fact-packet reuse and incremental projection before widening model work.
- `odylith compass refresh --repo-root .` is the canonical operator refresh
  path. Compass now exposes one bounded refresh contract: it writes
  `refresh-state.v1.json`, returns queued truth promptly when not waiting, and
  exposes request status instead of pretending minute-scale deep rerenders are
  a healthy interactive product behavior.
- The bounded Compass refresh may reuse only exact same-packet narration on the
  foreground path. `shell-safe` refresh never blocks on a fresh provider call:
  it reuses exact global or scoped brief cache when available, otherwise
  returns the truthful current brief state immediately, enqueues one packet
  bundle containing any missing global and verified scoped briefs, and lets the
  UI pick up the warmed results later. Non-exact cache carry-forward is not
  allowed.
- Cheapness is part of the product contract, not an implementation detail.
  Compass has only two acceptable runtime lanes now: hot unchanged refresh
  under `50ms` of internal runtime work and complete cold shell-safe refresh
  under `1s` of internal runtime work. There is no separate deep or
  minute-scale truth lane beyond those two budgets. Any regression away from
  that target is a product bug.
- The freshness trigger is separate from the runtime budget. Compass should not
  wake up because a one-second heartbeat fired; it should refresh because the
  watched projection fingerprint actually changed. Push-style watcher wakeups
  are the preferred contract, direct local file watching is the secondary
  fallback, and coarse polling is a last resort rather than the normal product
  posture.
- Release readiness is stricter than "globals look better." Compass is not
  ready to ship while either bounded runtime lane misses those budgets or
  while exact-cache replay still dominates because live provider warming has
  not caught up to the current packet mix. Once the ready-brief population is
  back to fresh provider plus exact cache only, the remaining release
  blocker narrows to the runtime budgets themselves. In either case, release
  notes, plans, and Casebook must say Compass is still below bar instead of
  treating the bounded contract as done.
- Compass reaches that budget by reusing the last validated brief layer
  when the exact fact-packet fingerprint still matches. Compass should not
  repay provider work just because a new payload was requested; the live
  refresh contract is current-payload reuse first and rebuild only for the
  scopes or windows whose narrative inputs actually changed. A ready warmed
  brief is not reusable if it fails the current voice validator.
- Refresh-state progress must break the heavy runtime build into concrete
  operator-facing phases instead of burying minutes under one generic stage.
  At minimum the request state must surface projection input load, activity
  collection, execution projection, window-fact preparation, standup-brief
  build, payload write, snapshot write, and shell-bundle completion, each with
  a short plain detail string.
- Timeline Audit must keep its primary fix visible. If a transaction headline,
  checkpoint summary, or primary narrative infers an anchor workstream, the
  visible chip row must include that workstream and order it first before
  broader linked scope pills are trimmed for space.
- Minute-scale `full strict live refresh` is retired. Compass does not expose,
  document, or promise a second deep-refresh mode anymore because the product
  could not make that contract truthful, cheap, and fast at once. The public
  Compass command surface is just `odylith compass refresh` now. If an agent
  or operator asks for a "full" Compass refresh in prose, route that intent to
  `odylith compass refresh --repo-root . --wait` instead of inventing a second
  noun, flag, or stricter acceptance bar.
- When live provider narration is needed for Compass briefs or similar simple
  refresh-time brief enrichment, the default model class is the cheap-fast
  coding path: `gpt-5.3-codex-spark` with low reasoning effort, unless a
  narrower slice proves that a more expensive model is required.
- Runtime mode for a refresh request resolves once before launch. Timeout or
  mid-run failure must be terminal for that request rather than silently
  retrying the same render through a second wrapper path.
- Any failed refresh, including `shell-safe`, must update the live Compass
  runtime payload warning model and `runtime_contract.last_refresh_attempt` so
  stale or failed deeper-refresh posture is visible inside the current surface.
- `odylith compass refresh --repo-root . --status` stays read-only, but it
  must still derive dead-worker truth instead of parroting a stale `running`
  record when the tracked refresh pid has already exited.
- `--wait` must reconcile dead refresh workers into explicit terminal failure
  state instead of hanging on a stale `running` record, and refresh-state truth
  must carry the concrete failure detail when render fails.
- Compatibility `odylith dashboard refresh --repo-root . --surfaces compass`
  must delegate to the same request engine. It is a wrapper over the same
  bounded Compass refresh, not a second Compass contract, and it must wait for
  a terminal Compass result instead of returning a queued follow-up that can
  outlive the launcher command surface that invoked it.
- When the top-level shell refreshes without rerendering Compass, ordinary
  stale-snapshot disclosure belongs inside Compass itself.
- The shell should reserve runtime-status cards for failed deeper-refresh
  state or other cross-surface posture the Compass frame cannot already
  explain.
- If Compass already carries the failed-refresh or stale-runtime warning
  inside the frame, the shell must not restate the same warning above Compass.
- Any shell-facing Compass freshness status must still derive from the current
  Compass runtime snapshot rather than pretending the shell wrapper refresh
  updated Compass data.
- Live history augmentation for stale rolling windows may fetch only retained
  or explicitly restored history dates. Off-retention days must stay absent
  rather than triggering browser-visible 404 requests.

## Traceability Risk Projection
- Compass consumes shared Radar `warning_items`, but default risk rows are
  reserved for operator-facing `warning` and `error` diagnostics.
- Maintainer-facing info diagnostics, including autofix conflict notes, should
  remain visible in the underlying traceability artifacts without showing up as
  primary Compass risk rows.

## Self-Host Readout Contract
- Compass runtime payload now carries `self_host` with:
  `repo_role`, `posture`, `runtime_source`, `release_eligible`,
  `pinned_version`, and `active_version`.
- When the public product repo is detached, diverged, or incomplete, Compass
  must surface that as an explicit risk row rather than leaving self-host drift
  implicit.
- A pinned but unverified local wrapper runtime must also surface as an
  explicit self-host risk; version alignment alone is not sufficient.
- Install/runtime lifecycle transitions and failed local self-host preflight
  checks are allowed to append concise timeline statements so Compass history
  shows when the product repo drifted in or out of valid dogfood posture.

## Intent Behind Compass
Compass exists so a developer or operator can answer:
- what happened recently
- which workstreams are actually moving
- what state the product thinks it is in right now
- what the standup summary should sound like

It is the runtime narrative surface, not the canonical source of backlog truth
or component definitions.

## What To Change Together
- New event kind:
  update log/update/watch flows, runtime event ranking, and shell rendering.
- New runtime snapshot field:
  update current snapshot JSON, history serialization, and shell payload
  consumption together.
- New release readout or release-history field:
  update the runtime payload, summary cards, workstream detail cards, and
  cross-surface tests together.
- New grouped release-member panel:
  update the Compass shell mount point, grouped release renderer, generated
  bundle list, and shell/runtime tests together.
- Release-target layout change:
  update the grouped release renderer, shared Compass base CSS, bundle mirrors,
  and tests together, and do not change the established stacked format without
  explicit operator authorization.
- Shell asset contract or shared execution-wave CSS change:
  update `compass_dashboard_frontend_contract.py`, the shared execution-wave
  generator, thin Compass overrides, live shell assets, bundle mirrors, and
  browser/unit proof together.
- New standup section or brief contract:
  update narrator validation, cache epoch, the Briefs Voice Contract
  component, and shell rendering at the same time.
- New freshness or activity heuristic:
  update runtime scoring, history output, and any dependent tests together.

## Failure And Recovery Posture
- Missing required governance inputs should fail Compass render rather than
  producing a misleading runtime snapshot.
- AI brief failures should degrade to explicit unavailable state unless an
  exact same-packet validated brief already exists to replay.
- `shell-safe` is bounded by queue-and-status semantics, not by pretending a
  long-running blocking refresh is interactive just because it uses a lighter
  profile.
- Any failed refresh, including `shell-safe`, must leave explicit failure truth
  in both `refresh-state.v1.json` and the live runtime payload.
- Timeout or render failure must not automatically trigger a second render
  attempt through another wrapper mode unless the failure happened before the
  runtime mode resolved.
- History retention should archive older daily snapshots without touching the
  live stream, and restore should remain explicit.
- Compass stream noise should never be treated as authoritative implementation
  evidence unless the event kind and artifact mix justify it.

## Validation Playbook
### Compass
- `odylith compass refresh --repo-root . --status`
- `odylith compass refresh --repo-root . --wait`
- `odylith compass update --repo-root . --help`
- `odylith compass restore-history --repo-root . --help`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_compass_dashboard_base.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_compass_standup_brief_narrator.py`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-20 · Decision:** Successor created: B-255 reopens B-253 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/compass/CURRENT_SPEC.md +1 more
- **2026-03-04 · Implementation:** Shipped Registry dashboard rendering plus governance and traceability sync updates, and refreshed generated Radar, Atlas, and Compass shells.
  - Evidence: src/odylith/runtime/governance/sync_workstream_artifacts.py, src/odylith/runtime/surfaces/render_backlog_ui.py +2 more
- **2026-03-04 · Decision:** Standardized governance visibility around Registry as the canonical component audit surface across Radar, Atlas, and Compass.
  - Evidence: src/odylith/runtime/governance/sync_workstream_artifacts.py, src/odylith/runtime/surfaces/render_backlog_ui.py +2 more
- **2026-03-03 · Implementation:** Implemented lineage fields and relation edges across validation, reciprocal backfill, traceability graph, and Radar/Compass rendering.
  - Evidence: odylith/radar/source/INDEX.md, odylith/technical-plans/INDEX.md +2 more
- **2026-03-03 · Decision:** kickoff B-034 lineage model with successor-first reopen policy and typed relation semantics.
  - Evidence: odylith/radar/source/INDEX.md, odylith/technical-plans/INDEX.md +2 more
- **2026-03-01 · Implementation:** Added Codex decision/implementation stream ingestion into Compass timeline audits and shipped logging skill contract.
  - Evidence: odylith/skills/compass-timeline-stream/SKILL.md, src/odylith/runtime/common/log_compass_timeline_event.py
<!-- registry-requirements:end -->

## Feature History
- 2026-04-10: Centralized Compass brief voice under the Registry-owned `briefs-voice-contract` component, retired deterministic brief fallback, and tightened the brief runtime to fresh provider, exact cache, or explicit unavailable. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Tightened standup-brief presentation so only real narrated briefs keep the full card, non-ready states stay compact and truthful, and the copy action hides unless a real brief is on screen. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Collapsed global and scoped standup warming into one packet-level narrated bundle, removed separate scoped maintenance fanout, and made verified scoped briefs warm through the same provider transaction as their parent global windows. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Reaffirmed that the default unscoped `Current Workstreams` board is residual-only. Lanes already visible in `Programs` or `Release Targets` are filtered out there, while explicit scoped selection may still surface the chosen workstream directly. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-095`)
- 2026-04-09: Removed the backend `12`-row truncation from `Current Workstreams` so Compass now ranks the full eligible set and lets the visible scope/window filters decide what remains on screen instead of hiding rows before the operator's chosen focus rules apply. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Bound Compass scope visibility, promoted focus, and scoped fresh-provider eligibility to Delivery Intelligence's shared Scope Signal Ladder so quiet low-signal scopes stay deep-linkable but no longer masquerade as active window work. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071); Bug: `CB-090`)
- 2026-03-26: Added Odylith-owned Compass runtime roots so the public repo can keep a first-class audit trail for product changes and validation events. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-03-27: Changed Compass history to a 15-day active window with compressed archived daily snapshots and an explicit restore-history command for older dates. (Plan: [B-003](odylith/radar/radar.html?view=plan&workstream=B-003))
- 2026-03-27: Added self-host posture payload, product-runtime risk surfacing, and posture-transition evidence for the public Odylith repo. (Plan: [B-004](odylith/radar/radar.html?view=plan&workstream=B-004))
- 2026-04-02: Anchored rolling windows and audit timelines to the loaded runtime snapshot time and added explicit stale-runtime warnings so old snapshots no longer masquerade as empty recent days. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-07: Aligned Compass traceability risk rows with Radar's shared operator-facing warning policy so maintainer autofix diagnostics stay in the artifacts instead of primary risk cards. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-05: Documented the bounded `compass_brief_freshness` benchmark slice so proof stays on Compass runtime, narrator, focused tests, and product-surface guidance instead of widening into unrelated install or repair surfaces. (Plan: [B-038](odylith/radar/radar.html?view=plan&workstream=B-038))
- 2026-04-08: Clarified that shell-host refresh truth must distinguish wrapper freshness from Compass child-runtime freshness so stale or failed deeper-refresh snapshots stay explicit on the Compass tab. (Plan: [B-060](odylith/radar/radar.html?view=plan&workstream=B-060))
- 2026-04-09: Retired the old minute-scale Compass `full` refresh contract entirely. Compass now exposes one bounded refresh path, and any legacy `full` request normalizes onto that path instead of reviving a second expensive truth mode. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-086`)
- 2026-04-09: Added Atlas diagram `D-032` so the bounded Compass refresh contract is explicit about cold reinstall behavior, global narrated-cache warming, scoped rung-gated fresh spend, and the fail-closed edges around unavailable providers, invalid responses, and stale runtime patching. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-08: Finalized stale-runtime disclosure to a single in-frame Compass warning for ordinary stale snapshots and bounded live-history backfill to retained or restored days so stale windows no longer spray 404 history fetches into the shell browser lane. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Re-closed the one-warning contract for failed Compass refresh so the shell stays silent when the Compass frame already carries the same failed-refresh disclosure. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-10: Fixed the dashboard/lane-switch wrapper so Compass no longer returns control in a queued state with a dead follow-up command after a pinned-runtime activation. The wrapper now waits Compass to a terminal result and routes any retry back through `odylith dashboard refresh --repo-root . --surfaces compass`. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-101`)
- 2026-04-09: Collapsed Compass shell asset truth back to one canonical frontend-contract path, removed the duplicated execution-wave CSS fork, and required exact live/bundle mirror plus browser proof for compact workstream buttons and stacked `Release Targets`. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-080`)
- 2026-04-09: Removed Compass-local KPI/stat-card forks from the shell base CSS so hero KPIs and current-release tiles now load through Dashboard's shared card contract and browser proof can audit the same computed styling as Radar, Registry, and Casebook. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-085`)
- 2026-04-08: Added current and next release summaries, grouped release-member views, and per-workstream release chips and history summaries so Compass shows target ship lanes without pretending release planning is the publication lane itself. (Plan: [B-063](odylith/radar/radar.html?view=plan&workstream=B-063))
- 2026-04-08: Kept the current active release visible in Compass until an explicit `shipped` or `closed` transition, with a `No targeted workstreams.` empty state when the lane stays active but temporarily has no targeted members. (Plan: [B-065](odylith/radar/radar.html?view=plan&workstream=B-065))
- 2026-04-08: Added a separate completed-members section for finished work closed in the active current release, so release closeout stays visible without reclassifying that work as active targeting. (Plan: [B-066](odylith/radar/radar.html?view=plan&workstream=B-066))
- 2026-04-08: Bound Compass workstream buttons to the shared compact `B-###` button contract so release/member cards and current-workstream links stop drifting when broader identifier styling changes. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-08: Elevated no-stock-framing Compass voice to a standing product invariant and required cache revalidation before warmed briefs can replay, so human standup tone survives refresh, reuse, and future narrator changes. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Locked `Release Targets` back to the operator-approved stacked format and prohibited shared shell CSS from reintroducing side-by-side or auto-fit release boards without explicit operator authorization. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Hardened workstream progress truth so Compass counts only execution-relevant checklist sections, shows checklist-only state for active implementation lanes with zero checked execution tasks, and stops narrating those rows as fake `0% progress`. (Plan: [B-068](odylith/radar/radar.html?view=plan&workstream=B-068); Bug: `CB-087`)
