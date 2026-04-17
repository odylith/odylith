---
status: implementation
idea_id: B-025
title: Cross-Surface Runtime Freshness and UX Browser Hardening
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_parts: Compass runtime freshness, projection invalidation, standup-brief recovery, shell UX proof, cross-surface browser hardening, balanced live-shell freshness posture, default-surface diagnostics curation, cross-surface filter and search semantics
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: If Compass can go stale while the underlying Odylith truth is current, the shell stops feeling like a trustworthy operating layer. This slice fixes the freshness contract and widens browser proof across the UX/UI, not just Compass.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/in-progress/2026-03/2026-03-29-odylith-cross-surface-runtime-freshness-and-ux-browser-hardening.md
execution_model: standard
workstream_type: standalone
workstream_parent:
workstream_children: B-071,B-080,B-081,B-091
workstream_depends_on: B-017, B-018, B-023
workstream_blocks:
related_diagram_ids: D-032
workstream_reopens:
workstream_reopened_by:
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Problem
Compass can still present stale brief, risk, and timeline state even when the
current Odylith source truth is fresh. More broadly, commit-time self-healing
is too late to be the primary freshness posture for consumer shell use: an
operator can spend a long active session looking at stale Odylith views before
the pre-commit hook ever gets a chance to repair anything. The current browser
suite also proves many surface routes, but it does not yet lock the broader
UX/UI freshness contracts tightly enough. Radar and Compass also still disagree
about which traceability diagnostics count as default operator-facing warnings,
so info-level maintainer autofix conflicts can leak into Radar detail cards as
scary product warnings. Search and filter behavior also still drifts across
surfaces: Atlas already supports punctuation-insensitive diagram search, while
Radar, Registry, and Casebook still leave more exact-id and normalized-token
cases to luck or raw substring matching, and the browser lane does not yet
brutalize those edge cases across every governance surface.

## Customer
- Primary: Odylith operators using Compass as the live blended control surface.
- Secondary: maintainers relying on headless browser proof to catch shell UX/UI
  regressions before release.

## Opportunity
If Compass and the broader shell invalidate stale runtime state correctly and
the browser suite proves cross-tab, reload, and rolling-window behavior, then
the Odylith UX feels reactive, trustworthy, and much harder to regress.

## Proposed Solution
Harden runtime freshness across Compass and related shell flows: version the
projection contract, cap Compass runtime reuse by age for rolling windows,
remove stale cross-packet global brief recovery, curate traceability
diagnostics once so default surfaces only show operator-facing warning/error
rows, and expand Playwright proof to assert fresh KPIs, brief posture,
timelines, and cross-surface state restore.
Rebuild the brief lane around one strict rule: local code selects, compresses,
diffs, validates, and caches; the LLM only writes the final prose bundle.
That means:
- deterministic narration substrates instead of raw-packet prompting
- exact cache identity on the narration substrate fingerprint
- delta bundle narration from changed winner facts and prior accepted brief
- provider-worthiness gating so trivial/non-winner churn never burns credits
- keep brief wallet and latency evidence in explicit provider diagnostics, not
  dashboard shell status UI
- daemon-backed hot refresh reuse so unchanged Compass does not repay process
  and import costs
Keep the prose human and free-flowing. The governed contract should be strict
about evidence eligibility and banned drift patterns, not about sentence
templates. In practice that means:
- `Completed in this window` stays on concrete completed movement in the
  selected slice
- `Current execution` usually stays on one active lane and one concrete action
- `Next planned` stays on the immediate next move from that lane
- `Risks to watch` names explicit blockers, freshness seams, or proof gaps
- thin packets shorten the brief instead of widening into portfolio synthesis
The voice contract should reject abstract maintainer/status language such as
`forcing function`, `execution coherence`, or `room to tighten` even when the
underlying facts are current.
That same slice also has to retire the old minute-scale deeper Compass rerender
idea entirely. Compass should keep one bounded refresh contract, reuse a recent
payload only when it already satisfies current bounded truth, and never ask
operators to choose between a cheap mode and a second expensive truth lane.
Extend that same model into a balanced live-shell posture:
- keep live shell views fresh earlier than commit through runtime-backed data
  and bounded shell-safe refresh while the shell is actively open
- make freshness change-driven: real local watcher events first, projection
  fingerprint change second, bounded refresh third
- auto-reload only read-only runtime-backed tabs in the default balanced lane:
  Radar, Registry, Compass, and Casebook
- keep Atlas explicit by default and print the exact follow-up command when
  Atlas truth is stale but excluded
- avoid ambient background mutation of tracked `odylith/` governance outputs in
  mixed worktrees
- keep provider spend off the blocking refresh path entirely; exact cache may
  replay live narration, but fresh narration warms only in the maintained
  sidecar and only once per new packet fingerprint
- keep internal diagnostics out of dashboard product DOM:
  no shell status drawer, cockpit, recorder tape, chart hydrator, or snapshot
  status slab may render above child surfaces
- make stale or mixed-worktree posture explicit in the shell instead of hiding
  it until commit time
- keep benchmark and release-proof lanes frozen so no hidden live-refresh path
  contaminates the evaluation contract
- harden every governance-surface search and filter contract so exact ids,
  normalized tokens, reset behavior, and invalid/deep-linked filter state all
  behave predictably under headless browser proof

## Scope
- fix Compass runtime reuse so 24h/48h windows rebuild on age as well as input
  change
- replace timer-led freshness with watcher-led invalidation plus cheap
  projection-fingerprint checks, and treat coarse polling as a last resort
- version the bug projection contract into store and hot-path fingerprints
- remove stale last-known-good global brief reuse across changed fact packets
- extend the shell freshness model so runtime-backed live views can refresh
  earlier than commit without forcing tracked-governance churn
- surface mixed-worktree or drift posture clearly when shell-safe refresh is no
  longer safe
- stop default Radar warning cards from surfacing info-level maintainer
  traceability autofix conflicts that belong in diagnostics artifacts instead
- add broader browser proof for shell UX/UI across Compass, Atlas, Radar,
  Registry, and Casebook
- delete shell status/cockpit code from the product shell and prove legacy
  diagnostic payload keys cannot reappear in rendered dashboard tabs
- align search semantics across Radar, Registry, Atlas, and Casebook so exact
  ids and punctuation-insensitive human queries do not behave differently
  depending on which governance surface the operator happened to open first
- rerender shipped shell and Compass assets

## Non-Goals
- redesigning Compass or the shell
- introducing screenshot approval testing
- changing benchmark publication policy

## Risks
- over-tight freshness invalidation could make Compass slower than necessary
- aggressive brief fallback changes could reduce availability if provider reuse
  is still needed in scoped paths
- browser assertions could become brittle if they depend on incidental layout
- broad filter-search matching could become too fuzzy and hide real exact-match
  intent

## Dependencies
- `B-017`, `B-018`, and `B-023` established the browser-proof lane and shell
  tab-state isolation this slice extends

## Success Metrics
- Compass global 24h and 48h windows stop reusing stale last-known-good briefs
  across changed fact packets
- Compass critical-risk KPIs and timeline panels reflect current source truth
  after tab hops and reloads
- default operator-facing shell surfaces agree on which traceability warnings
  deserve primary warning treatment
- browser proof covers broader shell UX/UI freshness paths, not just Compass
- browser proof fails if shell status strings, selectors, recorder UI, chart
  DOM, or ECharts hydration reappear across Radar, Registry, Casebook, Atlas, or
  Compass
- browser proof catches bounded Compass refresh regressions so a passing
  rerender never lands on synthetic or stale local brief state across global
  24h/48h and scoped current-workstream views
- missing global and verified scoped briefs warm through one packet-level
  narrated bundle instead of separate scoped provider fanout
- Compass only advertises scoped windows when the selected workstream has
  verified scoped activity in that exact rolling window; governance-only churn
  and broad fanout timeline rows stay global-only evidence
- exact-id and normalized-token filter/search behavior is proven across Radar,
  Registry, Atlas, Casebook, and Compass filter state
- the shell makes the difference between live runtime freshness and tracked
  governance drift explicit instead of leaving commit-time repair as the first
  user-visible signal
- narration spend is bounded by substrate gating and packet-level bundle
  generation instead of raw-packet scope fanout
- hot refresh can return from daemon-held in-memory state when the projection
  fingerprint did not move
- live narration stays simple, crisp, clear, insightful, human, and live
  without turning deterministic; the hard rules stay on evidence scope and
  drift rejection, not sentence templates
- thin evidence produces a shorter, more grounded brief instead of a broader
  portfolio-style summary
- benchmark proof stays green

## Guardrail
- CB-120 makes this explicit: internal diagnostics may remain explicit debug
  artifacts, but they must never render as dashboard shell chrome, drawers, status
  slabs, recorder tapes, cockpit panels, charts, or product guidance.

## Validation
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_surface_projection_fingerprint.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_filter_audit.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --output odylith/compass/compass.html`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root . --output odylith/index.html`
- `odylith benchmark --repo-root .`
- `git diff --check`

## Outcome
- implemented on 2026-04-02 for the shell/Compass contract:
  Compass windows now anchor to the loaded snapshot timestamp and the shell now
  distinguishes `balanced`, `proof_frozen`, and explicit `full_dev`
  live-refresh posture without background sync or provider-backed refresh
- implemented on 2026-04-05 for the browser-refresh contract:
  shell bundle assets, child-surface frame hrefs, and Compass runtime/script
  refs now publish cache-busting version tokens; global `48h` is back on the
  provider-backed live-brief path when warmed truth is available; and
  deterministic scoped `48h` briefs now
  widen their wording instead of collapsing into the exact `24h` narration
- implemented on 2026-04-05 for the scoped-brief/browser-proof follow-up:
  the Compass DOM now exposes brief source, scope, window, and fingerprint
  metadata, and Playwright asserts those values switch correctly across global
  versus scoped selection and `24h` versus `48h` toggles; the older deeper
  rerender experiment that warmed selected scoped briefs was later retired in
  favor of one bounded refresh contract
- implemented on 2026-04-08 for the standup-voice follow-up: Compass brief
  contract `v15` now treats no-stock-framing as a standing product invariant
  across provider output, warmed cache reuse, and the then-active fallback
  path;
  repeated window leads, canned `next/why/timing` wrappers, rhetorical
  benchmark challenges, and second-wave house phrasing are rejected before
  global or scoped briefs can quietly fall back into robotic prose after
  rerender
- implemented on 2026-04-08 for the `v0.1.11` Compass release target:
  scoped `24h` and `48h` briefs now fail closed instead of borrowing the
  global brief, the old `Executive/Product` versus `Operator/Technical` split
  is gone across provider output, cache replay, DOM rendering, and copied
  brief text, and the brief contract rejects the internal stock templates that
  kept making Compass sound canned after refresh
- implemented on 2026-04-08 for the plainspoken-voice hardening follow-up:
  Compass brief contract `v19` now names the target style as plainspoken
  grounded maintainer narration, invalidates warmed cache written under the
  older contract, rejects stagey phrases like `pressure point`, `muddy`,
  `window coverage spans`, `with the clearest movement around`, and `The next move is`,
  and carries the same voice rule through the Compass spec, delivery guidance,
  session memory, and bundled skills
- implemented on 2026-04-07 for cross-surface diagnostics curation:
  traceability warning items now carry audience/visibility policy, default
  Radar warning cards and Compass traceability risks agree on the same
  operator-facing warning boundary, and browser proof now guards against raw
  maintainer autofix conflicts leaking into the default workstream detail view
- implemented on 2026-04-07 for cross-surface filter and search hardening:
  Radar, Registry, and Casebook now honor exact canonical ids and normalized
  punctuation-insensitive search terms more consistently, Atlas filter proof is
  now part of the same aggressive browser lane, and the dedicated headless
  audit makes cross-surface filter drift a release-visible failure instead of a
  lucky manual catch
- implemented on 2026-04-07 for Compass retained-history filter reliability:
  the audit-day picker now clamps against real retained history dates instead
  of a synthetic 30-day range, so historical filter changes stop inviting
  browser-visible 404s for snapshots that were never retained
- implemented on 2026-04-08 for explicit-refresh hardening:
  Compass briefly carried a stricter deep-refresh contract to prove that stale
  or synthetic fail-closed brief state could be rejected end to end; that contract
  was then retired on 2026-04-09 when the product collapsed back to one
  bounded refresh path instead of preserving a second minute-scale mode
- implemented on 2026-04-10 for the packet-bundle brief follow-up:
  Compass now warms missing global and verified scoped narration through one
  packet-level provider bundle with one repair pass max, which removes the
  separate scoped maintenance fanout and keeps provider failures on one retry
  loop instead of one scope at a time
- implemented on 2026-04-10 for the local-substrate brief follow-up:
  Compass now fingerprints exact brief reuse on the deterministic narration
  substrate instead of raw packets, computes provider-worthiness locally from
  winner deltas, keeps brief spend diagnostics bounded, and reuses
  daemon-held runtime payloads on hot unchanged refreshes
- implemented on 2026-04-08 for shell freshness projection bootstrap:
  the tooling shell now preserves its precomputed Compass stale/failure status
  on first load and across runtime probes, so browser-visible shell truth no
  longer disappears just because the runtime-probe payload omits shell-only
  status records
- implemented on 2026-04-09 for shell-versus-child warning dedupe:
  when Compass already carries a failed-refresh warning inside the frame, the
  shell now stays quiet instead of rendering the same warning again above the
  iframe
- implemented on 2026-04-08 for deeper Compass/browser hardening proof:
  the resumed shell-and-Compass browser sweep now runs against rerendered
  checked-in shell and Casebook surfaces after source/governance changes, so
  stale generated artifacts stop masquerading as Compass freshness regressions
- implemented on 2026-04-16 for Casebook source-truth cleanup:
  `Reproducibility` is now a compact classifier across all checked-in Casebook
  bug records, and shared Casebook source validation plus skills/guidance reject
  prose values before capture, index refresh, dashboard refresh, or direct
  renderer execution can publish repro steps or proof shard notes
- implemented on 2026-04-08 for the shell-safe global-brief regression:
  the product temporarily restored global live-provider calls on the blocking
  path to recover narration quality while the deeper architecture was still in
  flux; that stopgap is now retired by the push-first refresh contract instead
  of being treated as the permanent default
- implemented on 2026-04-08 for Compass credit-burn containment:
  the retired deeper rerender lane proved that exact current-packet cache
  reuse and bounded multi-scope provider packs could cut cost before the
  product removed that second lane entirely
- implemented on 2026-04-08 for deeper Compass refresh hardening:
  the retired deeper rerender lane also proved out scoped-pack splitting,
  24h-to-48h narration reuse, global synthesis from scoped truth, and stale
  worker repair before the product removed that minute-scale path and kept the
  cheaper pieces inside the bounded refresh contract
- implemented on 2026-04-09 for shell-safe refresh/runtime hardening:
  status derives dead-worker failure truth without mutating state, live phase
  reporting finally exposes where runtime time is going, and the remaining
  runtime miss is now isolated from narration economics instead of being hidden
  behind synchronous provider work
- implemented on 2026-04-09 for live-voice recovery after the cache epoch cut:
  global coverage facts and plan-fed next actions were rewritten into plain
  source language, warmed narrated globals recovered without replaying the old
  stock phrases, and source-local proof showed both `24h` and `48h` global
  briefs back under the current voice contract
- implemented on 2026-04-09 for the scope-signal follow-up:
  low-signal scope visibility, promotion, and compute budgets split into child
  workstream `B-071` so Compass's verified-scope gating can become one shared
  cross-surface ladder contract instead of another Compass-only heuristic
  provider-backed again at `27.29s` wall-clock; the measured long pole is now
  upstream window-fact preparation (`10.8s`), not model fan-out
- implemented on 2026-04-09 for Atlas governance clarity:
  added diagram `D-032` so Compass refresh now has one explicit architecture
  map covering the canonical command surface, bounded sync lane, global and
  scoped brief decisions, cold-start maintenance warming, and the failure
  edges that must stay fail-closed instead of silently reviving a second
  deeper refresh mode
- implemented on 2026-04-09 for scoped-window integrity:
  Compass now publishes `verified_scoped_workstreams` for each rolling window,
  keeps quiet scopes such as `B-040` out of the normal selector when they only
  appear in governance-only churn or broad fanout transactions, and renders an
  empty scoped Timeline Audit instead of borrowing unrelated global cards when
  a preserved deep link points at an inactive local window
- implemented on 2026-04-10 for the push-first refresh cut:
  Compass freshness is now governed as change-detect first, local rebuild
  second, narration sidecar third. The intended steady state is daemon
  push-style projection waiting when available, direct local watcher fallback
  when it is not, coarse polling only as a last resort, zero foreground
  provider spend on `shell-safe`, exact-cache replay only for the blocking
  path, and one deduped background warm per new packet fingerprint.
- implemented on 2026-04-09 for current-workstreams clarity:
  removed the backend `12`-row truncation from Compass `Current Workstreams`
  so the board now ranks the full eligible set and lets the visible window and
  scope filters do the narrowing instead of hiding rows ahead of operator focus
- implemented on 2026-04-17 for Compass Programs card shape:
  each visible execution-wave program now renders as a release-like inner card
  inside the outer tinted `Programs` container, the redundant inner focus
  panel remains suppressed, and Dashboard/Compass governance records plus
  browser proof remember that Programs must not flatten back into borderless
  rows
- implemented on 2026-04-10 for lane-switch and wrapper safety:
  `odylith dashboard refresh --surfaces compass` and the upgrade follow-on now
  wait Compass to a terminal bounded result instead of handing control back
  with a queued follow-up that can point at a direct Compass subcommand the
  newly activated pinned launcher does not expose; retry guidance stays on the
  stable dashboard-wrapper command
- implemented on 2026-04-08 for Compass closeout governance:
  Compass-specific freshness, fail-closed refresh, stale-disclosure, and
  retained-history claims are now closed; the remaining open workstream scope
  is broader cross-surface hardening, not unresolved Compass behavior
- recorded on 2026-04-12 for the live-narration contract retune:
  the governed brief posture now explicitly prefers free-flowing human prose,
  with deterministic rules limited to evidence eligibility, one-lane
  execution focus, immediate next move, concrete risk seams, thin-packet
  shortening, and rejection of abstract status prose

## Rollout
Ship as a freshness-and-proof hardening slice. No data migration is required,
but the regenerated runtime and browser proof should accompany the code change.

## Why Now
Odylith cannot claim a live operating layer if Compass can go stale or if the
browser suite misses that regression.

## Product View
This has to stop being whack-a-mole. The shell needs to feel obviously current,
and the proof lane has to catch this class of regression before a user does.

## Impacted Components
- `compass`
- `briefs-voice-contract`
- `dashboard`
- `odylith-context-engine`

## Interface Changes
- Compass rolling windows refresh more honestly
- Compass brief voice, reuse, and unavailable behavior now live under one
  governed contract instead of fallback-era prompt folklore
- Compass warns when the loaded runtime snapshot is stale instead of implying
  recent empty-day truth
- browser proof covers more real UX/UI edge cases across shell surfaces
- Radar, Registry, Atlas, and Casebook search behaves more consistently for
  exact ids and punctuation-insensitive human queries
- dashboard live refresh now publishes surface-specific policy and guardrail
  metadata so the shell can keep read-only tabs current without hidden writes

## Migration/Compatibility
- no source-truth migration required
- existing deep links continue to work
- stale cross-packet global brief reuse is intentionally removed

## Test Strategy
- tighten unit guards around freshness invalidation and cache recovery
- add broader Playwright proof for shell cross-tab and reload freshness
- add a dedicated governance-surface filter/search browser audit
- rerun runtime/browser and benchmark lanes

## Open Questions
- should other shell surfaces get explicit age-budget freshness contracts where
  they render rolling windows or live snapshots
- should the balanced shell posture also expose a first-class report-only Atlas
  preflight lane before explicit `--atlas-sync`
