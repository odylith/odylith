Status: In progress

Created: 2026-03-29

Updated: 2026-04-07

Backlog: B-025

Goal: Restore trustworthy live Compass and shell behavior by hardening runtime
freshness, removing stale brief reuse, and widening headless browser proof
across the UX/UI, including cross-surface filter and search semantics.

Assumptions:
- Compass staleness is a runtime reuse and projection invalidation problem, not
  source-truth loss.
- The existing Playwright harness is the right place to prove the UX/UI
  contracts that matter here.
- Fixing the freshness contract centrally is safer than piling on more local
  Compass special cases.
- Commit-time Odylith self-healing is a backstop, not an acceptable primary
  freshness experience for consumer shell use.

Constraints:
- Do not regress current benchmark quality or benchmark gate status.
- Keep Compass reactive to current Atlas, Registry, Casebook, Radar, and audit
  changes.
- Do not widen browser proof in a way that ignores real console, request, or
  page failures.
- Do not solve this by adding a default always-hot background daemon that
  mutates tracked `odylith/` outputs during normal editing.
- Keep one Odylith product codebase across consumer, proof, and maintainer-dev
  lanes; policy may vary by posture, but shipped behavior must converge through
  the same source and generated assets.

Reversibility: Reverting this slice restores the previous runtime reuse and
brief recovery behavior, along with the same stale-state risk.

Boundary Conditions:
- Scope includes Compass runtime freshness, projection invalidation,
  standup-brief cache recovery, shell browser proof, rerendered assets, and a
  balanced live-shell freshness posture that can refresh runtime-backed views
  earlier than commit without contaminating benchmark or release-proof lanes,
  plus consistent exact-id, normalized-token, and filter-reset behavior across
  Radar, Registry, Atlas, Casebook, and Compass.
- Scope excludes UI redesign and benchmark publication policy changes.

Related Bugs:
- [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)
- [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md)
- [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
- [2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md)
- no related Casebook-specific bug record exists yet for detail-view field repetition or header-collapse regressions; keep the failure mode visible in this plan and handoff until it is formalized

## Context/Problem Statement
- [x] Compass can reuse stale runtime snapshots for rolling 24h/48h windows.
- [ ] Warmed bug projection state can stay stale after parser-contract changes.
- [x] Standup-brief recovery can reuse stale global AI cache across changed
      fact packets.
- [x] Install and upgrade-oriented narration can keep stale self-host or
      launcher assumptions after live runtime posture changes.
- [ ] Operators still need the full governance sync to express a narrow
      dashboard refresh, and Atlas Mermaid worker failures can look hung
      instead of naming the blocking diagram ids.
- [ ] Commit-time refresh and autofix are too late to be the first user-visible
      freshness signal in consumer shells.
- [ ] Radar still renders info-level traceability autofix conflicts as default
      workstream warnings while Compass silently filters them out, so the same
      shared governance diagnostics read as product warnings on one surface and
      maintainer noise on another.
- [ ] Current browser proof still misses some UX/UI freshness regressions.
- [ ] Governance-surface filter/search behavior still drifts across surfaces:
      Atlas already normalizes ids and punctuation-heavy tokens well, while
      Radar, Registry, and Casebook still leave some exact-id and normalized
      token queries behaving like plain substring search.
- [ ] The release browser lane still does not brutalize filter edge cases
      across every governance surface, so exact-id search, compact id tokens,
      filter resets, and invalid deep-link combinations can regress quietly.
- [x] Radar topology relation chips and disclosure-gated traceability links
      could route to the wrong record when selected detail and visible filters
      drifted, and the browser lane did not open that UI before release proof.
- [x] Compass standup narration can still sound templated even when the facts
      are current, because both the provider contract and the deterministic
      fallback reuse the same stock lead-ins.
- [ ] Casebook detail view repeats the same signals across summary, guidance,
      and inspect sections, which makes the human-facing bug readout noisy.
- [ ] Casebook detail can also repeat the same evidence path in both "Direct
      proof links" and "Evidence and references", which makes the agent band
      feel busy instead of sharp.
- [x] Shell-safe Compass dashboard refresh can keep Timeline Audit pinned to an
      old runtime snapshot instead of rebuilding current audit truth.
- [x] Explicit `odylith dashboard refresh --surfaces compass` can still defer
      live scoped narration and surface a deterministic fallback banner even
      when the operator asked for a real refresh.
- [x] Explicit `odylith dashboard refresh --surfaces compass` can become
      materially slower after moving onto the full live refresh path because it
      fans into scoped narration work that does not belong on a synchronous
      shell refresh.
- [x] Timeline Audit still stays pinned to the prior runtime snapshot when an
      explicit live refresh does not finish, because the refresh writes one
      coupled runtime payload after the standup brief stage completes.
- [x] Explicit Compass `full` refresh still lacks one fail-closed contract
      across the valid five-minute runtime reuse clamp, standup-brief
      fallback, and shell/browser proof, so a passing rerender can still leave
      deterministic or stale Compass state visible.

## Success Criteria
- [x] Compass runtime reuse is bounded by both input change and age.
- [x] Current bug/risk/timeline truth is reflected in Compass after rerender,
      cross-tab hops, and reload.
- [x] Changed global fact packets do not reuse stale last-known-good brief
      content.
- [x] Live self-host/install posture changes invalidate stale Compass
      narration before it leaks into operator guidance.
- [x] A render-only dashboard refresh path exists for shell surfaces without
      unrelated Registry or forensic churn.
- [x] While the shell is actively open, runtime-backed views can stay fresh
      earlier than commit through bounded shell-safe refresh or explicit stale
      posture signaling instead of silent tracked-file mutation.
- [x] Mixed-worktree or drift posture is visible in the shell when live refresh
      is no longer safe.
- [x] Atlas Mermaid worker failures name the blocking diagram ids and degrade
      to one-shot rendering clearly instead of appearing hung.
- [x] Playwright proves broader UX/UI freshness paths across shell surfaces.
- [x] Explicit shell-safe Compass dashboard refresh rebuilds the runtime
      snapshot in bounded mode instead of reusing stale `current.v1.json`.
- [x] Explicit `odylith dashboard refresh --surfaces compass` uses the full
      provider-backed global and scoped refresh path without leaving selected
      workstreams pinned to deterministic local briefs after a completed
      rerender.
- [x] Fresh rerenders publish new bundle and frame URLs so browsers cannot keep
      serving old shell or Compass assets after a live refresh.
- [x] Scoped deterministic 24h and 48h briefs no longer collapse into the same
      wording when the wider window should read as a broader live standup.
- [x] Browser proof can observe Compass brief source, scope, window, and
      fingerprint directly instead of inferring stale selection changes from
      narrative text alone.
- [x] A passing explicit Compass `full` refresh never lands on deterministic
      local brief state or warmed stale payload reuse across global 24h/48h and
      current-workstream scoped views.
- [x] Provider and deterministic Compass briefs no longer reuse stock
      lead-ins across sections, windows, and workstreams, and validation now
      rejects those canned openings before they reach the live payload.
- [x] Explicit Radar relation and traceability deep links resolve to the exact
      requested target even when stale list filters would otherwise hide it.
- [x] Release-gating browser proof opens disclosure-gated shell UI and audits
      governed cross-surface routes across Radar, Registry, Atlas, Compass,
      and Casebook.
- [ ] Casebook bug detail separates a crisp human readout from deeper Odylith
      agent learnings without repeating the same field content in both bands.
- [ ] Casebook detail dedupes overlapping proof and evidence links so the same
      path does not appear twice just because it was captured through two
      adjacent fields.
- [x] Default operator-facing surfaces only show operator-facing
      warning/error traceability diagnostics; maintainer autofix notes remain
      available in the graph/report without leaking into primary warning cards.
- [ ] Governance-surface filters consistently honor exact ids, normalized
      tokens, reset behavior, and deep-link self-healing across Radar,
      Registry, Atlas, Casebook, and Compass.
- [ ] Benchmark proof remains green after the fix.

## Non-Goals
- [ ] Visual redesign.
- [ ] Screenshot approval testing.
- [ ] Hosted runtime freshness infrastructure.

## Impacted Areas
- [x] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [compass_runtime_payload_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py)
- [x] [compass_standup_brief_narrator.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_standup_brief_narrator.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [ ] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [ ] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [ ] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [build_traceability_graph.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/build_traceability_graph.py)
- [x] [render_backlog_ui_html_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py)
- [ ] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [ ] [render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [ ] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [x] [dashboard_surface_bundle.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/dashboard_surface_bundle.py)
- [x] [tooling_dashboard_runtime_builder.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_runtime_builder.py)
- [ ] [tooling_dashboard_shell_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py)
- [ ] [surface_projection_fingerprint.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/surface_projection_fingerprint.py)
- [x] [test_compass_dashboard_runtime.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_dashboard_runtime.py)
- [x] [test_render_compass_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_compass_dashboard.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)
- [x] [test_compass_standup_brief_narrator.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_standup_brief_narrator.py)
- [x] [test_dashboard_surface_bundle.py](/Users/freedom/code/odylith/tests/unit/runtime/test_dashboard_surface_bundle.py)
- [x] [test_tooling_dashboard_runtime_builder.py](/Users/freedom/code/odylith/tests/unit/runtime/test_tooling_dashboard_runtime_builder.py)
- [x] [test_render_tooling_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_tooling_dashboard.py)
- [x] [test_compass_standup_brief_deterministic.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_standup_brief_deterministic.py)
- [ ] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)
- [ ] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [ ] [render_casebook_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_casebook_dashboard.py)
- [ ] [test_render_casebook_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_casebook_dashboard.py)
- [ ] [test_render_registry_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_registry_dashboard.py)
- [ ] [test_render_backlog_ui.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_backlog_ui.py)
- [ ] [test_render_mermaid_catalog.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_mermaid_catalog.py)
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)
- [x] [test_surface_browser_deep.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_deep.py)
- [x] [test_surface_browser_ux_audit.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_ux_audit.py)
- [ ] [test_surface_browser_filter_audit.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_filter_audit.py)

## Risks & Mitigations

- [ ] Risk: stricter invalidation slows Compass too much.
  - [ ] Mitigation: bound runtime reuse by a small age budget instead of
    disabling reuse entirely.
- [ ] Risk: provider-backed scoped full refresh becomes too slow to trust as a
    shell action.
  - [x] Mitigation: fan scoped provider warming through a small worker pool
    instead of a fully serial per-workstream render.
- [x] Risk: explicit `full` refresh still reports success via deterministic or
      stale fallback semantics that are acceptable only in `shell-safe`, or it
      reuses a recent payload that is not actually deep-refresh-clean.
  - [x] Mitigation: give explicit full refresh one fail-closed contract across
        runtime reuse, exact-cache reuse, deterministic fallback, and browser
        proof.
- [ ] Risk: global brief freshness fix reduces resilience when provider is
    unavailable.
  - [ ] Mitigation: keep exact-cache reuse and deterministic fallback from the
    current fact packet.
- [ ] Risk: browser tests become brittle.
  - [ ] Mitigation: assert stateful user-visible contracts, not layout trivia.
- [ ] Risk: hiding info-level diagnostics masks real maintainer conflicts.
  - [ ] Mitigation: keep those rows in the shared traceability graph/report and
    filter only the default operator-facing warning surfaces.
- [ ] Risk: overly fuzzy search hides exact-id intent or leaves surprising
      cross-surface mismatches.
  - [ ] Mitigation: prefer exact canonical-id and alias matches first, then
        fall back to normalized token search with browser proof for compact id
        forms and reset behavior.
- [ ] Risk: opportunistic live refresh changes benchmark or release-proof
    behavior.
  - [ ] Mitigation: freeze benchmark and release-proof lanes to explicit clean
    snapshots with no hidden refresh path.
- [ ] Risk: live freshness mutates tracked governance outputs during mixed
    work.
  - [ ] Mitigation: prefer runtime-backed refresh and explicit stale-state
    signaling; reserve tracked-truth mutation for explicit sync and commit-time
    repair.

## Validation/Test Plan
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/install/test_agents.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_dashboard_runtime.py`
- [x] `python -m pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py`
- [x] `python -m pytest tests/unit/runtime/test_dashboard_surface_bundle.py tests/unit/runtime/test_tooling_dashboard_runtime_builder.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_standup_brief_deterministic.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_compass_dashboard.py`
- [x] `python -m py_compile src/odylith/runtime/surfaces/render_compass_dashboard.py src/odylith/runtime/surfaces/compass_dashboard_runtime.py src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_build_traceability_graph.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_compass_dashboard_runtime.py`
- [x] `python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py`
- [x] `python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_ux_audit.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_filter_audit.py`
- [ ] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --refresh-profile full`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root . --output odylith/index.html`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_compass_dashboard.py tests/integration/runtime/test_surface_browser_smoke.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_refresh_contract.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_sync_cli_compat.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k compass` (executed locally; skipped because Playwright/Chromium is unavailable in this workstation environment)
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py -k "compass or shell"`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_casebook_dashboard.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_layout_audit.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k casebook_detail_stacks_cleanly_in_compact_viewport`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_casebook_dashboard --repo-root . --output odylith/casebook/casebook.html`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_casebook_dashboard --repo-root . --output src/odylith/bundle/assets/odylith/casebook/casebook.html`
- [x] `python -m py_compile src/odylith/runtime/surfaces/render_casebook_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/integration/runtime/test_surface_browser_layout_audit.py`
- [x] `python -m py_compile src/odylith/runtime/surfaces/render_mermaid_catalog.py src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_render_backlog_ui.py tests/integration/runtime/test_surface_browser_layout_audit.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_render_backlog_ui.py`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_mermaid_catalog --repo-root . --output odylith/atlas/atlas.html`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_mermaid_catalog --repo-root . --output src/odylith/bundle/assets/odylith/atlas/atlas.html`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_backlog_ui --repo-root . --output odylith/radar/radar.html --standalone-pages odylith/radar/standalone-pages.v1.js`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_backlog_ui --repo-root . --output src/odylith/bundle/assets/odylith/radar/radar.html --standalone-pages src/odylith/bundle/assets/odylith/radar/standalone-pages.v1.js`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k 'radar_search_selection_and_cross_surface_detail_links or radar_topology_relation_chips_route_to_their_own_workstream_ids or atlas_navigation_filters_and_context_links or atlas_d025_memory_substrate_route_exposes_governed_registry_links'`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k atlas`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py -k atlas`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k 'casebook or radar'`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py -k 'casebook or radar'`
- [ ] `odylith benchmark --repo-root .`
- [x] `git diff --check`

## Rollout/Communication
- [ ] Note the Casebook regression explicitly so future Compass or shell
  freshness work sees the exact failure mode.
- [x] Note the Casebook regression explicitly so future Compass or shell
      freshness work sees the exact failure mode.
- [x] Rerender shipped shell and Compass assets before browser validation so
  the proof runs against the same artifacts users open.
- [x] Add a dedicated cross-surface filter/search audit lane so release proof
      fails if exact-id queries, normalized token search, or filter reset
      behavior drifts again.

## Current Outcome
- [x] Bound to `B-025`; implementation in progress.
- [x] Product direction clarified on 2026-04-01: commit-time autofix remains a
      backstop, while the desired steady-state posture is runtime-fresh earlier
      than commit, explicit about mixed-worktree drift, and benchmark-safe by
      construction.
- [x] Compass rolling windows and audit timelines now anchor to the loaded
      runtime snapshot timestamp and show an explicit stale-runtime warning
      instead of rendering empty recent-day buckets from browser wall-clock
      drift.
- [x] Dashboard live refresh now exposes three modes: `balanced` for consumer
      and detached maintainer-dev lanes, `proof_frozen` for pinned proof and
      benchmark lanes, and explicit `full_dev` override for faster maintainer
      iteration.
- [x] Balanced mode auto-reloads only read-only runtime-backed tabs
      (`radar`, `registry`, `compass`, `casebook`) after an idle debounce and
      keeps Atlas explicit with a next-command hint.
- [x] Live refresh now carries explicit guardrails: no background `odylith
      sync`, no background tracked-truth mutation, and no provider-backed
      Compass brief refresh.
- [x] Browser proof covers the stale-snapshot Compass path so old runtime
      payloads stay visibly stale instead of looking empty.
- [x] `odylith dashboard refresh --surfaces compass` now rebuilds stale Compass
      runtime snapshots in shell-safe mode instead of replaying the old
      `current.v1.json`, and the bounded path still keeps provider-backed
      global brief generation deferred.
- [x] Shell bundle assets and child-surface frame hrefs now carry cache-busting
      version tokens, and the shell preserves those tokens when query state is
      merged so a rerender cannot stay hidden behind browser cache.
- [x] Compass shell assets and runtime script refs now carry version tokens,
      global `48h` is back on the live provider path during full refresh, and
      deterministic scoped `48h` narration widens its wording instead of
      reusing the exact `24h` brief.
- [x] Full Compass refresh now warms scoped workstream briefs through the live
      provider path as well, but does it in parallel so the completed rerender
      stops leaving selected scopes on deterministic local narration.
- [x] Compass summary rendering now publishes brief source, scope, window, and
      fingerprint metadata into the DOM, and Playwright proves those values
      switch correctly across global versus scoped selection and `24h` versus
      `48h` toggles.
- [x] Compass standup brief contract is now `v13`: provider narration is told
      to avoid house phrases, deterministic fallback rewrites the same facts in
      plainer spoken language, and validation rejects overused stock openings
      so cached or regenerated briefs cannot slide back into the robotic voice.
- [x] April 7 follow-on keeps `B-025` active for the Casebook detail polish:
      repeated proof/evidence links stay deduped, summary metadata now renders
      as stacked fact cards instead of one non-wrapping strip, and the
      browser/unit proof now attacks the live bug header under long-title
      multi-source records.
- [x] April 7 QA follow-on expands browser proof from correctness-only into
      compact-width and repetition-aware UX proof so the live shell catches
      noisy detail bands before release, including desktop and compact
      geometry audits for Casebook detail headers.
- [x] April 7 Atlas/Radar detail-header follow-on makes Atlas mirror the
      Casebook fact-card treatment, promotes Radar workstream ids into the KPI
      grid as the first box, and extends the browser layout audit so desktop
      and compact views fail on header overlap, inline-collapsed facts, or id
      cards drifting out of first position.
- [x] Atlas header now also drops the old right-side control lane so the fact
      cards use the full detail width instead of leaving empty space beside the
      first card rows; the layout audit now proves the controls stack below the
      facts instead of reserving a desktop-side gutter.
- [x] Dashboard detail-header ordering is now explicit shared governance: the
      primary fact/KPI grid must be the first block under the headline across
      Casebook, Atlas, and Radar, while supporting prose, chips, links, and
      controls render below that grid; the Dashboard spec now carries that
      contract and the layout/browser proof enforces it.
- [x] April 7 diagnostics follow-on keeps maintainer autofix conflict notes in
      shared traceability artifacts but removes them from default Radar warning
      cards so default surfaces agree on operator-facing warning semantics.
- [x] Radar explicit relation navigation now reveals the requested target
      before selection, and the browser lane audits disclosure-gated deep
      links plus cross-surface action chips across Radar, Registry, Atlas,
      Compass, and Casebook.
- [x] April 7 filter/search follow-on aligns exact-id and normalized-token
      behavior across Radar, Registry, Atlas, and Casebook, and the new
      browser audit now attacks compact ids, punctuation-free queries, reset
      behavior, and cross-surface filter state directly.
- [x] April 7 Compass retained-history follow-on narrows the audit-day picker
      to real retained history dates, closing a browser-visible 404 path that
      appeared when the old synthetic 30-day bounds offered non-existent
      historical snapshots.
- [x] April 8 full-refresh follow-on closed the fail-closed contract: explicit
      Compass `full` keeps the valid five-minute reuse clamp, only reuses
      recent payloads that are already deep-refresh-clean, refuses to pass
      with deterministic local narration or stale fallback truth, and now has
      targeted contract/runtime/render/narrator proof plus a headless browser
      regression for the deterministic-brief banner path.
- [x] April 8 browser-resume follow-on fixed the tooling-shell bootstrap path:
      shell-computed Compass stale/failure posture now survives first load and
      later runtime probes, and the resumed headless browser lane proves both
      stale-shell-newer and failed-full-refresh disclosure on the Compass tab.
- [x] April 8 deeper QA follow-on rerendered checked-in shell and Casebook
      surfaces before the broader Compass/browser sweep, eliminating stale
      generated-artifact false positives and closing the resumed `compass or
      shell` browser lane cleanly.
- [x] April 7 shell-warning dedupe follow-on removes the redundant
      shell-level "snapshot older than shell" banner, keeps Compass stale
      disclosure in the Compass frame itself, drops the `Show status` recovery
      dock button, and centralizes that one-warning shell contract in the
      Dashboard spec.
- [x] April 7 Compass closeout follow-on reconciles the remaining open Compass
      claims with code-level proof: global changed-packet cache recovery stays
      disabled, self-host/install posture remains part of the standup-brief
      fingerprint and provider contract, narrator regression proof now covers
      self-host posture drift explicitly, and umbrella bug `CB-019` closes.
- [x] April 7 final Compass browser cleanup bounds live history augmentation to
      retained history days only, so stale live snapshots still disclose their
      age inside Compass without spraying 404 history fetches into the shell
      browser lane; the resumed stale-warning browser proof now passes cleanly.
- [x] Compass closeout is complete on this plan. Remaining unchecked items
      belong to broader cross-surface or benchmark follow-on work, not to
      unresolved Compass freshness, narrator, or shell-disclosure claims.
