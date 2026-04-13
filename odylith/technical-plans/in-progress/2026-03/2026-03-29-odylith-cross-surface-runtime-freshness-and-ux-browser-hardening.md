Status: In progress

Created: 2026-03-29

Updated: 2026-04-12

Backlog: B-025

Goal: Restore trustworthy live Compass and shell behavior by hardening runtime
freshness, removing stale brief reuse, and widening headless browser proof
across the UX/UI, including cross-surface filter and search semantics.

Current architecture rule:
- local code selects, compresses, diffs, validates, and caches
- the provider only writes the final prose bundle
- deterministic guards decide which evidence may speak and which drift modes
  fail closed
- the provider prose stays free-flowing, human, and non-template inside that
  bounded evidence cone

Assumptions:
- Compass staleness is a runtime reuse and projection invalidation problem, not
  source-truth loss.
- Brief quality and brief cost are both mostly input-contract problems, not a
  reason to reintroduce synthetic fallback narration.
- Good live narration comes from better evidence shaping and drift rejection,
  not from hard-coded sentence structure.
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
- [2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-compass-standup-brief-fails-to-use-local-provider-and-stays-deterministic.md)
- [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md)
- [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
- [2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-06-radar-topology-deep-links-fall-through-to-stale-filtered-selection-and-browser-proof-misses-disclosure-gated-routes.md)
- [2026-04-09-compass-release-target-layout-regresses-to-unauthorized-multi-column-board.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-release-target-layout-regresses-to-unauthorized-multi-column-board.md)
- [2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-shared-surface-contract-drift-reopens-workstream-button-and-release-layout-regressions.md)
- [2026-04-09-cross-surface-workstream-buttons-can-reopen-local-scope-instead-of-radar.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-cross-surface-workstream-buttons-can-reopen-local-scope-instead-of-radar.md)
- [2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md)
- [2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-runtime-reuse-can-ignore-live-release-and-program-source-changes.md)
- [2026-04-09-compass-current-workstream-ranking-can-hide-active-release-and-wave-lanes.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-current-workstream-ranking-can-hide-active-release-and-wave-lanes.md)
- [2026-04-09-compass-current-workstreams-can-duplicate-governed-lanes-already-visible-in-programs-or-release-targets.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-current-workstreams-can-duplicate-governed-lanes-already-visible-in-programs-or-release-targets.md)
- [2026-04-09-compass-browser-source-truth-fallback-can-accept-unusable-snapshots-and-preserve-stale-scope-state.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-browser-source-truth-fallback-can-accept-unusable-snapshots-and-preserve-stale-scope-state.md)
- [2026-04-12-compass-programs-can-regrow-a-redundant-nested-inner-card.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-12-compass-programs-can-regrow-a-redundant-nested-inner-card.md)
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
- [x] Compass `Release Targets` can regress back to a side-by-side release
      board when stale shared shell CSS overrides still impose an auto-fit
      multi-column layout after the operator already restored the prior stacked
      format.
- [x] Shared shell-surface contracts can still split into duplicated source
      template CSS, generated shared CSS, live checked-in assets, and bundled
      mirrors, which lets later rebuilds silently reopen workstream-button and
      release-layout regressions that were already fixed once.
- [x] Interactive `B-###` controls can still disagree on destination across
      product surfaces, with Compass release-member, execution-wave, and
      timeline chips reopening Compass-local scope instead of the canonical
      Radar workstream route.
- [x] Radar topology relation chips and disclosure-gated traceability links
      could route to the wrong record when selected detail and visible filters
      drifted, and the browser lane did not open that UI before release proof.
- [x] Compass standup narration can still sound templated even when the facts
      are current, because both the provider contract and the then-active
      fallback narrator reused the same stock lead-ins.
- [ ] Compass live narration can still drift into portfolio/status prose when
      it broadens past one active lane or compensates for thin evidence with
      abstract maintainer language.
- [x] The governed Compass brief contract was still scattered across prompt
      folklore, cache-salvage behavior, and skills, which kept teaching the
      old fallback worldview back into the product even after the runtime
      architecture changed.
- [x] Raw-packet prompt payloads were still wasting model time on local
      selection work that Compass should perform deterministically first.
- [x] Bundle replies could still lose good sibling entries because validation
      treated the whole response as one fate instead of salvaging valid
      subsets.
- [x] Hot unchanged refresh was still paying too much Python startup and
      projection re-entry cost even when the daemon already knew the current
      fingerprint and payload.
- [ ] Casebook detail view repeats the same signals across summary, guidance,
      and inspect sections, which makes the human-facing bug readout noisy.
- [ ] Casebook detail can also repeat the same evidence path in both "Direct
      proof links" and "Evidence and references", which makes the agent band
      feel busy instead of sharp.
- [x] Shell-safe Compass dashboard refresh can keep Timeline Audit pinned to an
      old runtime snapshot instead of rebuilding current audit truth.
- [x] Explicit `odylith dashboard refresh --surfaces compass` can still defer
      live scoped narration and surface a synthetic fail-closed banner even
      when the operator asked for a real refresh.
- [x] Explicit `odylith dashboard refresh --surfaces compass` can become
      materially slower after moving onto the full live refresh path because it
      fans into scoped narration work that does not belong on a synchronous
      shell refresh.
- [x] Timeline Audit still stays pinned to the prior runtime snapshot when an
      explicit live refresh does not finish, because the refresh writes one
      coupled runtime payload after the standup brief stage completes.
- [x] Compass still carried a second minute-scale `full` refresh idea that the
      product could not make truthful, cheap, and fast at the same time.
- [x] Compass scope selection and scoped Timeline Audit could still treat
      governance-only local churn or broad fanout transactions as if they were
      verified local window movement, which let quiet scopes such as `B-040`
      appear in the dropdown and leak unrelated global audit cards.
- [x] Timeline Audit could headline a checkpoint on one workstream while the
      visible workstream chip row still hid that anchor scope behind broader
      linked ids, which made the most important fix harder to click.
- [ ] Compass is still below release bar after the maintained-global narration
      follow-on. The bounded hot exact-reuse lane now measures `0.3s`
      internal (`0.73s` wall), the rebuilt cold shell-safe lane measures
      `1.7s` internal (`2.18s` wall), and the ready-brief source mix is now
      `35 cache / 0 synthetic fallback`, so the remaining release blocker is cold
      wall-clock and startup overhead rather than deterministic dominance.

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
- [x] Shell-safe Compass refresh no longer spends provider credits on the
      blocking path. Exact same-packet cache may replay a narrated brief, but
      fresh narration warms in the maintained sidecar after the bounded local
      refresh finishes.
- [x] Compass scope dropdowns and scoped timelines advertise only workstreams
      with verified scoped activity for the selected rolling window; broad
      governance churn and wide fanout transactions stay global-only evidence.
- [x] Timeline Audit transaction cards keep the anchor workstream visible and
      first in the chip row whenever the headline or checkpoint text names the
      primary fix.
- [x] Explicit `odylith dashboard refresh --surfaces compass` now delegates to
      the same bounded Compass refresh engine instead of advertising a second
      deeper contract.
- [x] Fresh rerenders publish new bundle and frame URLs so browsers cannot keep
      serving old shell or Compass assets after a live refresh.
- [x] Missing global and verified scoped briefs now warm through one
      packet-level narrated bundle with one repair pass max instead of
      separate scoped provider fanout and retry bookkeeping.
- [x] Scoped exact-cache replay and scoped unavailable states no longer borrow
      one generic wording path when the wider window should read differently.
- [x] Browser proof can observe Compass brief source, scope, window, and
      fingerprint directly instead of inferring stale selection changes from
      narrative text alone.
- [x] Compass no longer advertises or routes a second `full` refresh mode. One
      bounded refresh contract now owns freshness, failure truth, and brief
      reuse across global and scoped views.
- [x] Compass command cleanup removes the stale `--refresh-profile` noun from
      the operator surface entirely. "Full Compass refresh" in prose now maps
      to `odylith compass refresh --repo-root . --wait`, not a second CLI
      flag or hidden contract.
- [x] Dashboard-triggered Compass refresh now waits for the bounded terminal
      result instead of returning a queued follow-up that the just-activated
      pinned launcher may not be able to run; wrapper recovery stays on
      `odylith dashboard refresh --repo-root . --surfaces compass`.
- [ ] Compass hot unchanged refresh reaches `<=50ms` of internal runtime work,
      complete cold shell-safe refresh reaches `<=1s`, and the change-detect
      lane stays watcher-first instead of paying for an aggressive timer loop.
- [x] Compass briefs no longer reuse stock lead-ins across provider output,
      exact cache replay, and validation, and those canned openings now fail
      before they reach the live payload.
- [x] Compass voice is now treated as a product invariant instead of polish:
      queue-label restatement, generic priority wrappers, canned current/next
      scaffolding, and warmed-cache replay of stock prose are all contract
      failures even when the underlying facts are current.
- [x] Compass voice is now explicitly named and enforced as plainspoken
      grounded maintainer narration: open, natural, clear, lightly soulful,
      ordinary-language brief writing with validator coverage against stagey
      metaphors, dashboard-polished abstractions, and rhythmic summary prose.
- [ ] Live narration keeps the prose free-flowing and human while the hard
      gates stay on evidence eligibility, one-lane scope, immediate next move,
      concrete risk seams, and banned abstraction patterns instead of sentence
      templates.
- [x] The governed Compass brief contract now has one durable home in the
      Registry-owned `briefs-voice-contract` component, and guidance plus
      skills no longer teach deterministic fallback or stock coverage
      narration back into the product.
- [ ] Thin evidence packets make the brief shorter instead of pushing it into
      broader portfolio synthesis.
- [x] Compass brief cache identity now keys off the deterministic narration
      substrate fingerprint instead of raw packet identity, so non-winner
      churn does not force avoidable cold misses.
- [x] Compass brief generation now uses local narration substrates and
      delta-oriented bundle payloads instead of prompting directly from full
      fact packets.
- [x] Provider-worthiness gating now skips narration attempts for trivial or
      non-winner deltas and records that decision explicitly.
- [x] Brief spend telemetry now records bundle fingerprint, substrate
      fingerprints, latency, input/output size, salvage count, repair count,
      skip reason, and provider failure detail.
- [x] Daemon-backed hot refresh can now reuse the last matching Compass
      runtime payload directly instead of rebuilding on every unchanged
      request.
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
- [x] Compass `Current Workstreams` now behaves as the residual focus table in
      the default unscoped view: workstreams already represented in `Programs`
      or `Release Targets` are filtered out instead of being duplicated in a
      third board, while explicit scoped selection still shows the chosen
      workstream directly.
- [x] Compass `Release Targets` now starts collapsed in the default unscoped
      view; current/next/single-release state no longer auto-expands on load,
      while explicit scoped workstream selection may still open the matching
      release section.
- [x] Interactive `B-###` workstream buttons stay on one compact shared
      contract across Radar, Compass, release views, and execution-wave member
      stacks instead of drifting whenever generic identifier styling changes.
- [x] Interactive `B-###` workstream buttons across Compass, Registry, Atlas,
      Casebook, and Radar all deep-link to the same Radar workstream route;
      local surface scoping stays a separate row-selection or disclosure
      behavior instead of changing the destination of those controls.
- [x] Compass `Release Targets` stays on the operator-approved stacked format,
      and release-target layout changes now require explicit operator
      authorization instead of renderer or shared-CSS improvisation.
- [x] Compass keeps program cards and release cards visually distinct with
      subtle surface tinting, so execution structure and ship targeting stay
      separable at a glance without forking the shared layout contract.
- [x] Compass labels the outer program container `Programs`, parallel to
      `Release Targets`, so the two grouped sections are legible before the
      inner cards open.
- [x] Compass `Programs` now treats its disclosure shell as an explicit flat
      section contract, so the grouped outer box cannot silently regrow a
      redundant nested inner card when shared section chrome shifts.
- [x] Compass outer `Programs` and `Release Targets` containers now keep
      subtle but distinct surface tints so the two governance families are
      visually separable without changing the shared layout contract.
- [x] Compass program focus panels no longer repeat the outer `N-wave
      program` chip; the inner focus band keeps only additional context that
      is not already present in the section summary.
- [x] Shared shell-surface contracts now keep one canonical source path:
      interactive `B-###` controls flow through the shared workstream-button
      primitive, Compass execution-wave CSS composes from the shared generator
      plus thin overrides only, surface renders refresh live checked-in assets
      and source-owned bundle mirrors in the same pass, live and bundle
      Compass shell assets must exactly match the source loader output, and
      browser proof audits the computed button contract plus the stacked
      release board.
- [x] Governance KPI/stat cards across Compass, Radar, Registry, and Casebook
      now consume one shared contract for grid, card surface, and label/value
      typography; local stat-card CSS forks in source templates are forbidden,
      browser proof audits computed KPI-card styling plus labeled
      current-release values, and Radar release-only tiles no longer carry
      local alignment or value-spacing overrides on top of that shared
      contract.
- [x] Generic deep-link buttons such as `Registry`, `Spec`, proof refs, and
      `D-###` diagram links now consume one shared contract across Compass,
      Radar, Registry, Casebook, and Atlas; local button CSS forks are
      forbidden, and browser proof audits the computed font, padding, and
      radius across representative deep-link buttons in those surfaces.
- [x] Registry component detail no longer renders a default proof-state or
      live-status card; proof-state internals such as `Proof Control`,
      `Live Blocker`, `Fingerprint`, `Frontier`, `Evidence tier`,
      `Truthful claim`, and commit-hash deployment rows stay out of the
      default detail view entirely.
- [x] Casebook detail headers keep the selected bug id in the summary-facts
      band and must not also render a standalone `CB-###` kicker above the
      title.
- [x] Compass `Release Targets` member cards keep the workstream title on a
      dedicated second row under the ID/status chip row; short titles must not
      collapse back into the first row.
- [x] Compass operator release UI now stays current-release-only: the hero KPI
      lane does not render a separate `Next Release` box, while `Release
      Targets` still shows the governed planned release set and the current
      release group carries an explicit `Current Release` indicator.
- [x] Release-truth drift uses Compass's subtle in-surface status banner only;
      shell-level runtime status must not duplicate that drift as a second top
      warning slab.
- [x] Radar topology no longer renders a separate selected-workstream focus
      strip above the relations disclosure; the detail header already carries
      the identity, so the relations board opens directly into relation
      content.
- [x] The shell cheatsheet now teaches release planning and program/wave
      planning as separate operator workflows with explicit examples instead
      of blurring ship targeting and umbrella execution into one planning
      concept.
- [ ] Benchmark proof remains green after the fix.

## Non-Goals
- [ ] Visual redesign.
- [ ] Screenshot approval testing.
- [ ] Hosted runtime freshness infrastructure.

## Impacted Areas
- [x] [odylith-compass-refresh-and-maintained-narration-topology.mmd](/Users/freedom/code/odylith/odylith/atlas/source/odylith-compass-refresh-and-maintained-narration-topology.mmd)
- [x] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [compass_dashboard_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_runtime.py)
- [x] [compass_runtime_payload_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py)
- [x] [compass_standup_brief_narrator.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_standup_brief_narrator.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [ ] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [ ] [agents.py](/Users/freedom/code/odylith/src/odylith/install/agents.py)
- [ ] [odylith_context_engine_store.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_store.py)
- [x] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [build_traceability_graph.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/build_traceability_graph.py)
- [x] [render_backlog_ui_html_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py)
- [x] [dashboard_ui_primitives.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/dashboard_ui_primitives.py)
- [x] [execution_wave_ui_runtime_primitives.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/execution_wave_ui_runtime_primitives.py)
- [x] [compass_dashboard_frontend_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/compass_dashboard_frontend_contract.py)
- [x] [dashboard_shell_links.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/dashboard_shell_links.py)
- [x] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [x] [render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [x] [render_tooling_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_tooling_dashboard.py)
- [x] [tooling_dashboard_cheatsheet_presenter.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/tooling_dashboard_cheatsheet_presenter.py)
- [x] [source_bundle_mirror.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/source_bundle_mirror.py)
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
- [x] [test_compass_refresh_contract.py](/Users/freedom/code/odylith/tests/unit/runtime/test_compass_refresh_contract.py)
- [ ] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)
- [ ] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [ ] [test_agents.py](/Users/freedom/code/odylith/tests/unit/install/test_agents.py)
- [x] [render_casebook_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_casebook_dashboard.py)
- [ ] [test_render_casebook_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_casebook_dashboard.py)
- [x] [test_dashboard_shell_links.py](/Users/freedom/code/odylith/tests/unit/runtime/test_dashboard_shell_links.py)
- [x] [test_source_bundle_mirror.py](/Users/freedom/code/odylith/tests/unit/runtime/test_source_bundle_mirror.py)
- [ ] [test_render_registry_dashboard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_registry_dashboard.py)
- [x] [test_render_backlog_ui.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_backlog_ui.py)
- [x] [test_execution_wave_ui_runtime_primitives.py](/Users/freedom/code/odylith/tests/unit/runtime/test_execution_wave_ui_runtime_primitives.py)
- [x] [test_render_mermaid_catalog.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_mermaid_catalog.py)
- [x] [test_dashboard_ui_primitives.py](/Users/freedom/code/odylith/tests/unit/runtime/test_dashboard_ui_primitives.py)
- [x] [test_surface_shell_contracts.py](/Users/freedom/code/odylith/tests/unit/runtime/test_surface_shell_contracts.py)
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)
- [x] [test_surface_browser_deep.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_deep.py)
- [x] [test_surface_browser_ux_audit.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_ux_audit.py)
- [x] [test_surface_browser_layout_audit.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_layout_audit.py)
- [ ] [test_surface_browser_filter_audit.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_filter_audit.py)

## Risks & Mitigations

- [ ] Risk: stricter invalidation slows Compass too much.
  - [x] Mitigation: reuse the current runtime by exact input fingerprint and
        rewrite today's daily history files from that reused payload instead of
        forcing a rebuild on simple date rollover.
- [x] Risk: a minute-scale `full` refresh path keeps draining time, credits,
      and operator trust while pretending to be a real product contract.
  - [x] Mitigation: retire the second refresh mode entirely and collapse
        Compass onto one bounded refresh engine.
- [ ] Risk: global brief freshness fix reduces resilience when provider is
    unavailable.
  - [ ] Mitigation: keep exact-cache reuse from the current fact packet and
    fail closed to explicit `unavailable` otherwise.
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
- [x] `python -m pytest tests/unit/runtime/test_dashboard_surface_bundle.py tests/unit/runtime/test_tooling_dashboard_runtime_builder.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_contract.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_compass_dashboard.py`
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
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root . --output odylith/index.html`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_compass_dashboard.py tests/integration/runtime/test_surface_browser_smoke.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/test_cli.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_refresh_contract.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_sync_cli_compat.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k compass` (executed locally; skipped because Playwright/Chromium is unavailable in this workstation environment)
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py -k "compass or shell"`
- [x] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_casebook_dashboard.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_layout_audit.py`
- [x] `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_surface_browser_deep.py -k casebook_detail_stacks_cleanly_in_compact_viewport`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_surface_shell_contracts.py`
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
      sync`, no background tracked-truth mutation, and no shell-safe scoped
      provider warming; the global shell-safe brief may still reuse exact
      cache or request the live provider opportunistically.
- [x] Browser proof covers the stale-snapshot Compass path so old runtime
      payloads stay visibly stale instead of looking empty.
- [x] `odylith dashboard refresh --surfaces compass` now rebuilds stale Compass
      runtime snapshots in shell-safe mode instead of replaying the old
      `current.v1.json`, and shell-safe now keeps scoped provider warming
      deferred while letting global `24h`/`48h` narration use the provider
      opportunistically when it is available.
- [x] Shell bundle assets and child-surface frame hrefs now carry cache-busting
      version tokens, and the shell preserves those tokens when query state is
      merged so a rerender cannot stay hidden behind browser cache.
- [x] Compass shell assets and runtime script refs now carry version tokens,
      and deterministic scoped `48h` narration widens its wording instead of
      reusing the exact `24h` brief.
- [x] April 8 cost-bleed guardrails and the April 9 follow-on cuts collapsed
      Compass back onto one bounded refresh contract: cold refresh no longer
      fans out across every active scoped brief, global narration reuses
      warmed truth first, and there is no second `full` path left to burn
      minutes or credits behind the operator's back.
- [x] April 8 refresh-state truth now records concrete render-failure detail,
      and `--wait` repairs dead worker state into explicit terminal failure
      instead of hanging on a stale `running` record.
- [x] April 9 shell-safe refresh/runtime hardening turns the default path back
      into an operator-safe budgeted refresh: shell-safe now keeps live
      provider cost on the two global windows only, status derives dead-worker
      failure truth without mutating state, progress splits the heavy runtime
      build into named phases with plain detail, then reused deterministic
      timeline/window material upstream, moved simple live brief narration to
      `gpt-5.3-codex-spark` with low reasoning, bumped the brief cache to
      `v21`, invalidated warmed runtime-snapshot prose that no longer passes
      the current voice validator, and brought source-local proof down to
      `0.78s` warm wall-clock with about `1.63s` on a tmpdir cold shell-safe
      render.
- [x] April 9 live-voice recovery cleaned the remaining upstream phrasing leak:
      whole-window coverage facts now use plain wording, plan-fed next-action
      facts no longer relay raw checklist fragments, and a source-local
      shell-safe refresh returned both global windows provider-backed again at
      `27.29s` wall-clock. The remaining measured long pole is
      `window facts prepared` at `10.8s`, so the next latency cut belongs in
      incremental fact-packet reuse rather than more model trimming.
- [x] April 9 shell-safe reuse architecture now cuts the remaining latency
      spike by persisting `standup_runtime` window fingerprints into
      `current.v1.json`, reusing prior validated live brief sections when the
      narrative-relevant window signature still matches, and rebuilding only
      the scopes that actually changed. Source-local proof after this cut:
      first shell-safe CLI refresh dropped to `1.38s` wall-clock with
      `window facts prepared` at `0.107s` and `standup briefs built` at
      `0.014s`; the immediate hot rerun now takes the runtime-reuse fast path
      in `0.47s` wall-clock with `elapsed_seconds: 0.1`.
- [x] April 9 scoped-activity follow-on re-closes the local-scope contract:
      Compass now publishes `verified_scoped_workstreams` per rolling window,
      excludes governance-only local-change rows plus broad fanout
      transactions from scoped verification, keeps quiet scopes such as
      `B-040` out of the normal selector, and renders an empty scoped timeline
      instead of inheriting unrelated global audit cards when a preserved deep
      link points at an inactive local window. Headless browser proof now
      covers that exact regression directly.
- [x] April 9 scope-signal follow-on split the broader promotion problem into
      child workstream `B-071`: Delivery Intelligence now owns one shared
      ladder for scope visibility, default promotion, and provider-neutral
      compute budgets so Compass, Radar, Registry, Atlas, and shell consumers
      stop re-deriving urgency independently.
- [x] April 9 current-workstreams follow-on removed the old backend `12`-row
      truncation from Compass. The current-workstreams board now ranks the
      full eligible set and relies on the visible scope/window focus filters
      to narrow what operators see instead of discarding rows before those
      filters have a chance to act.
- [x] Compass summary rendering now publishes brief source, scope, window, and
      fingerprint metadata into the DOM, and Playwright proves those values
      switch correctly across global versus scoped selection and `24h` versus
      `48h` toggles.
- [x] Compass standup brief contract is now `v23`: fresh provider narration
      and exact-cache replay share one governed voice bar, the dedicated `Why
      this matters` section is gone, consequence must be woven into the
      remaining four sections, and validation now rejects fact-detached
      portable summary prose, repetitive polished claim-then-consequence
      cadence, repeated window leads, canned `next/why/timing` wrappers,
      rhetorical benchmark challenges, second-wave house phrasing, stock
      workstream roll calls, and the old `Executive/Product` versus
      `Operator/Technical` bullet split before a stored brief can replay into
      Compass again.
- [x] April 10 final brief-contract cutover retired the deterministic narrator
      and the broader maintained-global salvage lane: warmed runtime reuse now
      rolls to the new brief epoch, stale whole-window coverage lines are no
      longer rewritten into synthetic current prose, and provider miss without
      an exact current-packet cache hit lands on explicit `unavailable`.
- [x] April 10 packet-bundle follow-on collapsed global and verified-scoped
      background warming into one narrated bundle transaction, removed the
      separate scoped maintenance fanout path, and kept provider diagnostics on
      one packet-shaped retry loop instead of one scope at a time.
- [x] Compass governance, skills, and session-memory guidance now all carry
      the same non-negotiable voice rule: no stock framing, no house style,
      and no provider-, cache-, or synthetic-backed replay of canned prose in
      Compass-facing summaries.
- [x] The April 8 Compass brief hardening follow-on is now tagged to release
      `v0.1.11`: scoped `24h`/`48h` fail closed instead of borrowing global
      text, the old `Executive/Product` versus `Operator/Technical` split is
      gone across narration and rendering, and both brief paths reject the
      internal stock wrappers that kept replaying into Compass after refresh.
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
- [x] April 9 follow-on removes the stale Compass base-CSS release-board
      override, keeps `Release Targets` on the prior stacked format, records
      the regression in Casebook, and codifies that future release-target
      layout changes require explicit operator authorization.
- [x] April 9 follow-on collapses the remaining Compass and Registry
      top-line KPI/stat-card CSS forks into the shared Dashboard KPI contract
      and adds browser proof that Compass, Radar, Registry, and Casebook keep
      the same computed card, label, and value styling.
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
- [x] April 9 Compass refresh retirement follow-on removed the remaining
      minute-scale `full` contract from the product. Legacy callers normalize
      onto the bounded refresh engine, and browser or runtime proof no longer
      needs a second deep-refresh truth lane.
- [x] April 9 performance follow-on tightened the runtime lane contract too:
      Compass now has only two acceptable refresh budgets, hot exact-reuse
      under `50ms` of internal runtime work and cold complete shell-safe
      refresh under `1s` of internal runtime work. Any third minute-scale or
      deep-refresh lane is now governed as a regression, not a product option.
- [x] April 10 lane-switch wrapper follow-on removed a dead post-switch handoff:
      `odylith upgrade` and `odylith dashboard refresh --surfaces compass` now
      wait Compass through to a terminal bounded result, and failure recovery
      stays on the stable dashboard wrapper command instead of assuming the
      newly activated pinned launcher already exposes `odylith compass refresh`.
- [x] April 9 Atlas follow-on made that refresh contract visible in one
      architecture map too: diagram `D-032` now shows the canonical refresh
      command surface, bounded sync path, reinstall/no-cache cold-start
      behavior, scope-signal gated scoped spend, maintained narrated-cache
      sidecar, and the failure edges that must stay fail-closed.
- [x] April 9 live-cache carry-forward follow-on keeps that same bounded lane
      off fresh provider spend after the one-time seed: source-local proof now
      shows global `24h` and `48h` on `cache exact` during shell-safe refresh,
      `standup briefs built` stays sub-`0.1s`, and the remaining wall-clock
      miss is upstream input/startup cost rather than Compass narration cost.
- [x] April 10 architecture follow-on makes the freshness trigger explicit
      too: Compass should wake on real watcher-backed projection change, not
      because a tight heartbeat fired. The intended order is daemon push wait
      first, direct local watcher second, and coarse polling only as a last
      fallback on machines with no usable watcher backend.
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
- [x] April 9 follow-on re-closes that shell-warning contract for failed
      Compass refresh too: if Compass already carries the failed-refresh
      warning inside the frame, the shell must not add a second wrapper banner
      above it, and browser proof now watches that exact regression directly.
- [x] April 7 Compass closeout follow-on reconciles the remaining open Compass
      claims with code-level proof: global changed-packet cache recovery stays
      disabled, self-host/install posture remains part of the standup-brief
      fingerprint and provider contract, narrator regression proof now covers
      self-host posture drift explicitly, and umbrella bug `CB-019` closes.
- [x] April 7 final Compass browser cleanup bounds live history augmentation to
      retained history days only, so stale live snapshots still disclose their
      age inside Compass without spraying 404 history fetches into the shell
      browser lane; the resumed stale-warning browser proof now passes cleanly.
- [x] April 8 shell-safe global-brief follow-on was a temporary recovery step
      while the bounded lane was still untangling stale-cache and voice issues.
      That stopgap is now superseded by the stricter contract above: no
      foreground provider spend on `shell-safe`, exact-cache replay only, and
      maintained background warming for fresh narration.
- [x] Compass closeout is complete on this plan. Remaining unchecked items
      belong to broader cross-surface or benchmark follow-on work, not to
      unresolved Compass freshness, narrator, or shell-disclosure claims.
- recorded on 2026-04-12 for the founder-feedback live-narration retune:
  the governed brief contract now says prose should stay simple, crisp, clear,
  insightful, human, live, and free-flowing; deterministic rules stop at
  evidence eligibility, one active lane, one immediate next move, concrete
  risk seams, thin-packet shortening, and rejection of abstract
  manager-speak such as `forcing function`, `execution coherence`, or
  `room to tighten`
