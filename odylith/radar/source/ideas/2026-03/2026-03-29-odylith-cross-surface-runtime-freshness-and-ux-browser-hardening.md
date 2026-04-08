---
status: implementation
idea_id: B-025
title: Odylith Cross-Surface Runtime Freshness and UX Browser Hardening
date: 2026-03-29
priority: P0
commercial_value: 4
product_impact: 5
market_value: 4
impacted_lanes: both
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
workstream_children:
workstream_depends_on: B-017, B-018, B-023
workstream_blocks:
related_diagram_ids:
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
That same slice now needs one stricter explicit Compass `full` refresh
contract: keep the existing five-minute runtime reuse clamp, but only reuse a
recent payload when it already satisfies the requested deep-refresh truth
contract. A passing deep rerender must not land on deterministic local
narration or stale child-runtime state.
Extend that same model into a balanced live-shell posture:
- keep live shell views fresh earlier than commit through runtime-backed data
  and bounded shell-safe refresh while the shell is actively open
- auto-reload only read-only runtime-backed tabs in the default balanced lane:
  Radar, Registry, Compass, and Casebook
- keep Atlas explicit by default and print the exact follow-up command when
  Atlas truth is stale but excluded
- avoid ambient background mutation of tracked `odylith/` governance outputs in
  mixed worktrees
- avoid provider-backed Compass brief refresh in passive live-refresh paths so
  the steady-state shell does not inflate CODEX/provider spend
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
- keep the existing five-minute runtime reuse clamp, but make explicit Compass
  `full` validate that any reused payload already satisfies the deep-refresh
  contract and fail if the result would still require deterministic or stale
  fallback state
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
- browser proof catches explicit Compass `full` refresh regressions so a
  passing deep rerender never lands on deterministic local brief state across
  global 24h/48h and scoped current-workstream views
- exact-id and normalized-token filter/search behavior is proven across Radar,
  Registry, Atlas, Casebook, and Compass filter state
- the shell makes the difference between live runtime freshness and tracked
  governance drift explicit instead of leaving commit-time repair as the first
  user-visible signal
- benchmark proof stays green

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
  provider-backed full-refresh path; and deterministic scoped `48h` briefs now
  widen their wording instead of collapsing into the exact `24h` narration
- implemented on 2026-04-05 for the scoped-brief/browser-proof follow-up:
  full Compass refresh now warms selected workstream briefs through the live
  provider path as well, but fans that work through a small worker pool so the
  rerender stays bounded; the Compass DOM now exposes brief source, scope,
  window, and fingerprint metadata; and Playwright asserts those values switch
  correctly across global versus scoped selection and `24h` versus `48h`
  toggles
- implemented on 2026-04-05 for the standup-voice follow-up: Compass brief
  contract `v13` now bans repeated house phrases in provider narration,
  deterministic fallback rewrites the same facts in plainer spoken language,
  and validation rejects overused stock openings so global and scoped briefs
  cannot quietly fall back into robotic prose after rerender
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
- implemented on 2026-04-08 for the explicit full-refresh contract:
  Compass `full` now keeps the valid five-minute runtime reuse clamp but only
  reuses recent payloads that already satisfy the deep-refresh truth bar,
  fails closed instead of landing on deterministic or stale fallback brief
  state, and is backed by targeted contract, runtime, render, narrator, and
  browser-regression proof
- implemented on 2026-04-08 for shell freshness projection bootstrap:
  the tooling shell now preserves its precomputed Compass stale/failure status
  on first load and across runtime probes, so browser-visible shell truth no
  longer disappears just because the runtime-probe payload omits shell-only
  status records
- implemented on 2026-04-08 for deeper Compass/browser hardening proof:
  the resumed shell-and-Compass browser sweep now runs against rerendered
  checked-in shell and Casebook surfaces after source/governance changes, so
  stale generated artifacts stop masquerading as Compass freshness regressions

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
- `dashboard`
- `odylith-context-engine`

## Interface Changes
- Compass rolling windows refresh more honestly
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
