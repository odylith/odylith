# Compass
Last updated: 2026-04-09


Last updated (UTC): 2026-04-09

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
- The standup brief pipeline, including deterministic fallback narration.
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
- The standup brief is not allowed to disappear just because the AI provider is
  unavailable; deterministic local narration is the baseline.
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
  AI/deterministic standup brief pipeline and cache.
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
  Observe prompt transactions and refresh Compass as activity occurs.

`odylith dashboard refresh --repo-root . --surfaces compass` remains supported
as a compatibility wrapper over the same refresh engine. It is not a separate
Compass orchestration path.

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
remain active.

### 5. Render shell
The shell renderer externalizes the payload and control script into the checked
in surface bundle.

### 6. Reconcile stale runtime truth
At page load, Compass compares the visible runtime snapshot against the live
traceability release read model. If the active release id, targeted members,
completed members, or current-workstream rows drift, Compass patches the view
from traceability, marks the runtime truth guard, and tells the operator to run
`odylith compass refresh --repo-root .` for a full snapshot rewrite.

## Scope Signal Ladder Contract
Compass does not own scope escalation anymore. It consumes Delivery
Intelligence's shared `scope_signal` contract and applies these rules:
- scope dropdowns and scoped timelines require `R2+` in the exact active
  window
- deep-linked `R0-R1` scopes remain preserved but render a quiet scoped brief
  plus empty timeline instead of borrowing global activity
- promoted current-workstream lists and whole-window brief focus prefer `R3+`
  scopes
- fresh scoped provider narration is reserved for `R4-R5` scopes only
- `R0-R3` scoped paths stay cache or deterministic even when fresh provider is
  available

Compass must not reintroduce local urgency heuristics for governance-only
churn, generated-only churn, or broad fanout rows once the shared ladder is
present.

## Standup Brief Contract
`compass_standup_brief_narrator.py` owns the standup brief policy:
- AI-authored narration is allowed when Odylith can resolve a runnable shared
  reasoning provider. By default Compass prefers the active local coding agent
  CLI when one is available and only falls back to explicit endpoint config
  when that is the configured path.
- Compass voice is a product invariant. Briefs must read as plainspoken
  grounded maintainer narration: like a strong maintainer speaking off notes,
  open, natural, clear, specific, lightly soulful, and spoken, not branded
  dashboard prose or portfolio boilerplate.
- Stock framing is a correctness failure, not copy polish. Repeated house
  phrases, workstream-title restatement, generic priority or attention
  wrappers, sloganized self-host status, and canned current/next-step wrappers
  are invalid even when the underlying facts are true.
- Templating is broader than stock phrases. Compass briefs must not read like
  four balanced summary cards or interchangeable management bullets; they
  should feel observed, uneven where the evidence is uneven, and specific to
  the repo state in front of the operator.
- Stagey metaphor and dashboard-polish are invalid too. Phrases like
  `pressure point`, `center of gravity`, `muddy`, `slippery`, `top lane`, or
  `window coverage spans` are not vividness; they are drift back into
  performance language.
- Rhythmic prose is a shape failure. Even factually correct bullets are wrong
  if they fall into repeated claim-then-explanation cadence or sound like a
  dashboard trying to sound wise.
- Compass no longer renders a separate `Why this matters` brief section. User
  need, consequence, and leverage belong inside the relevant completed,
  current, next, or risk bullet instead of being split into an extra explainer
  block.
- Every brief bullet must stay visibly tethered to the cited fact language.
  If the cited facts disappear and the bullet still sounds plausible, Compass
  has drifted into portable summary prose and the brief is invalid.
- Compass no longer splits brief bullets into `Executive/Product` and
  `Operator/Technical` lanes. That labeled separation is part of the old
  templated surface contract and must not reappear in provider output,
  deterministic fallback, warmed cache reuse, legacy compatibility rendering,
  or copied brief text.
- The same no-stock-framing contract applies to provider output, warmed cache
  reuse, and deterministic fallback. If one path cannot stay natural, it must
  fall back to plainer fact language rather than a different template.
- Deterministic fallback is not a license for stock prose. It is the live
  narration quality floor on the bounded path, and any fallback that reads
  canned, rhythmic, or dashboard-polished is a correctness failure.
- Invalid, empty, deferred, or unavailable AI output may degrade to a
  deterministic local brief only when Compass cannot recover a validated
  maintained narrated brief for the same window or scope. Deterministic is
  emergency coverage, not the normal global steady state.
- The local cache lives at `.odylith/compass/standup-brief-cache.v22.json`.
- Warmed provider/cache briefs must still satisfy the current standup-brief
  validation contract before Compass is allowed to reuse them; cache must never
  replay stale house phrasing back into Compass.
- Runtime-snapshot cache reuse follows the same rule. A stricter voice contract
  must invalidate older warmed snapshot prose instead of letting prior provider
  wording outrank the current brief contract.
- The same voice contract applies to whole-window coverage facts and plan-fed
  next-action facts before provider generation. Compass must not feed raw
  checklist fragments, trailing punctuation stubs, or canned window wrappers
  into the narrator and then hope the model cleans them up downstream.
- Scoped Compass is fail-closed. When a workstream scope is selected, Compass
  must render that workstream's scoped brief or an explicit scoped-unavailable
  state; it must never silently substitute the global brief.
- Scoped selection is also fail-closed. The runtime payload publishes
  `verified_scoped_workstreams` per rolling window, and both the scope
  dropdown and the scoped Timeline Audit must derive from that verified set.
  Governance-only local changes and broad fanout transactions stay global
  evidence by default; they must not advertise a scoped window on their own.
- Deep-linked or persisted scope state may be preserved for continuity, but if
  the selected workstream is not verified for the active window, Compass must
  render the quiet/unavailable scoped brief state and an empty scoped timeline
  instead of showing unrelated global audit rows.

The intent is that Compass always produces an understandable standup artifact,
even when the shared reasoning provider is down.

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
- Provider-backed standup narration stays opportunistic and manual-refresh
  bounded. Local timeline, workstream, risk, and KPI readouts must remain
  understandable without spending provider credits.
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
- The bounded Compass refresh may reuse exact brief cache, including
  already-warmed provider-backed global `24h` and `48h` narration, but it
  must not spend a fresh provider call on a cold miss. Shell-safe global
  refresh must prefer maintained narrated cache first, including validated
  carry-forward of older global narrated sections when the current facts still
  support them. Cold bounded refresh rebuilds should fall back to
  deterministic narration only after that maintained global reuse path fails.
  Scoped views must stay cheap by serving exact cache or deterministic
  narration when live scoped provider output is deferred, unavailable, or
  invalid, but same-scope narrated reuse must not be blocked just because the
  packet also carries freshness facts for the current window.
- Cache reuse has to be resilient enough to keep narrated state dominant
  without buying new provider work. When one current-execution bullet drifts
  out of the current validation contract but the rest of the narrated cache
  still fits the live fact packet, Compass may salvage that section from the
  live deterministic floor and keep the rest of the narrated cache intact
  rather than dropping the whole brief back to deterministic.
- Cheapness is part of the product contract, not an implementation detail.
  Compass has only two acceptable runtime lanes now: hot unchanged refresh
  under `50ms` of internal runtime work and complete cold shell-safe refresh
  under `1s` of internal runtime work. There is no separate deep or
  minute-scale truth lane beyond those two budgets. Any regression away from
  that target is a product bug.
- Release readiness is stricter than "globals look better." Compass is not
  ready to ship while either bounded runtime lane misses those budgets or
  while deterministic still dominates the ready-brief source mix. Once the
  ready-brief population returns to narrated cache, the remaining release
  blocker narrows to the runtime budgets themselves. In either case, release
  notes, plans, and Casebook must say Compass is still below bar instead of
  treating the bounded contract as done.
- Compass reaches that budget by reusing the last validated brief layer
  when the narrative-relevant window signature still matches. Compass should
  not repay provider or deterministic scoped-brief work just because a new
  payload was requested; the live refresh contract is current-payload reuse
  first, salient brief reuse second, and rebuild only for the scopes or
  windows whose narrative inputs actually changed. A ready warmed brief is not
  reusable if it fails the current voice validator. Cached narrated reuse may
  remap packet-local fact ids through stored evidence lookup and rewrite old
  whole-window coverage summary bullets into plainer current wording before
  validation, but it must still fail closed if the narrated sections no longer
  fit the current packet.
- Refresh-state progress must break the heavy runtime build into concrete
  operator-facing phases instead of burying minutes under one generic stage.
  At minimum the request state must surface projection input load, activity
  collection, execution projection, window-fact preparation, standup-brief
  build, payload write, snapshot write, and shell-bundle completion, each with
  a short plain detail string.
- Minute-scale `full strict live refresh` is retired. Compass does not expose,
  document, or promise a second deep-refresh mode anymore because the product
  could not make that contract truthful, cheap, and fast at once. Any old
  caller or persisted state that still says `full` must normalize onto the one
  bounded refresh contract instead of reviving a second path.
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
  bounded Compass refresh, not a second Compass contract.
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
  update narrator validation, deterministic fallback, and shell rendering at
  the same time.
- New freshness or activity heuristic:
  update runtime scoring, history output, and any dependent tests together.

## Failure And Recovery Posture
- Missing required governance inputs should fail Compass render rather than
  producing a misleading runtime snapshot.
- AI brief failures should degrade to deterministic narration, not to a missing
  brief.
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
- 2026-04-09: Bound Compass scope visibility, promoted focus, and scoped fresh-provider eligibility to Delivery Intelligence's shared Scope Signal Ladder so quiet low-signal scopes stay deep-linkable but no longer masquerade as active window work. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071); Bug: `CB-090`)
- 2026-03-26: Added Odylith-owned Compass runtime roots so the public repo can keep a first-class audit trail for product changes and validation events. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-03-27: Changed Compass history to a 15-day active window with compressed archived daily snapshots and an explicit restore-history command for older dates. (Plan: [B-003](odylith/radar/radar.html?view=plan&workstream=B-003))
- 2026-03-27: Added self-host posture payload, product-runtime risk surfacing, and posture-transition evidence for the public Odylith repo. (Plan: [B-004](odylith/radar/radar.html?view=plan&workstream=B-004))
- 2026-04-02: Anchored rolling windows and audit timelines to the loaded runtime snapshot time and added explicit stale-runtime warnings so old snapshots no longer masquerade as empty recent days. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-07: Aligned Compass traceability risk rows with Radar's shared operator-facing warning policy so maintainer autofix diagnostics stay in the artifacts instead of primary risk cards. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-05: Documented the bounded `compass_brief_freshness` benchmark slice so proof stays on Compass runtime, narrator, focused tests, and product-surface guidance instead of widening into unrelated install or repair surfaces. (Plan: [B-038](odylith/radar/radar.html?view=plan&workstream=B-038))
- 2026-04-08: Clarified that shell-host refresh truth must distinguish wrapper freshness from Compass child-runtime freshness so stale or failed deeper-refresh snapshots stay explicit on the Compass tab. (Plan: [B-060](odylith/radar/radar.html?view=plan&workstream=B-060))
- 2026-04-09: Retired the old minute-scale Compass `full` refresh contract entirely. Compass now exposes one bounded refresh path, and any legacy `full` request normalizes onto that path instead of reviving a second expensive truth mode. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-086`)
- 2026-04-08: Finalized stale-runtime disclosure to a single in-frame Compass warning for ordinary stale snapshots and bounded live-history backfill to retained or restored days so stale windows no longer spray 404 history fetches into the shell browser lane. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Re-closed the one-warning contract for failed Compass refresh so the shell stays silent when the Compass frame already carries the same failed-refresh disclosure. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Collapsed Compass shell asset truth back to one canonical frontend-contract path, removed the duplicated execution-wave CSS fork, and required exact live/bundle mirror plus browser proof for compact workstream buttons and stacked `Release Targets`. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-080`)
- 2026-04-09: Removed Compass-local KPI/stat-card forks from the shell base CSS so hero KPIs and current-release tiles now load through Dashboard's shared card contract and browser proof can audit the same computed styling as Radar, Registry, and Casebook. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-085`)
- 2026-04-08: Added current and next release summaries, grouped release-member views, and per-workstream release chips and history summaries so Compass shows target ship lanes without pretending release planning is the publication lane itself. (Plan: [B-063](odylith/radar/radar.html?view=plan&workstream=B-063))
- 2026-04-08: Kept the current active release visible in Compass until an explicit `shipped` or `closed` transition, with a `No targeted workstreams.` empty state when the lane stays active but temporarily has no targeted members. (Plan: [B-065](odylith/radar/radar.html?view=plan&workstream=B-065))
- 2026-04-08: Added a separate completed-members section for finished work closed in the active current release, so release closeout stays visible without reclassifying that work as active targeting. (Plan: [B-066](odylith/radar/radar.html?view=plan&workstream=B-066))
- 2026-04-08: Bound Compass workstream buttons to the shared compact `B-###` button contract so release/member cards and current-workstream links stop drifting when broader identifier styling changes. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-08: Elevated no-stock-framing Compass voice to a standing product invariant and required cache revalidation before warmed briefs can replay, so human standup tone survives refresh, reuse, and future narrator changes. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Locked `Release Targets` back to the operator-approved stacked format and prohibited shared shell CSS from reintroducing side-by-side or auto-fit release boards without explicit operator authorization. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Hardened workstream progress truth so Compass counts only execution-relevant checklist sections, shows checklist-only state for active implementation lanes with zero checked execution tasks, and stops narrating those rows as fake `0% progress`. (Plan: [B-068](odylith/radar/radar.html?view=plan&workstream=B-068); Bug: `CB-087`)
