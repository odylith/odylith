Status: In progress

Created: 2026-03-29

Updated: 2026-04-05

Backlog: B-025

Goal: Restore trustworthy live Compass and shell behavior by hardening runtime
freshness, removing stale brief reuse, and widening headless browser proof
across the UX/UI.

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
  earlier than commit without contaminating benchmark or release-proof lanes.
- Scope excludes UI redesign and benchmark publication policy changes.

Related Bugs:
- [2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-29-compass-runtime-freshness-regressed-brief-risk-and-timeline-trust.md)
- [2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-02-compass-dashboard-refresh-shell-safe-keeps-timeline-audit-pinned-to-stale-snapshot.md)
- [2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-03-compass-explicit-refresh-fans-into-slow-live-scoped-narration-and-leaves-old-deterministic-brief-visible-on-interrupt.md)
- no related Casebook-specific bug record exists yet for detail-view field repetition; keep the failure mode visible in this plan and handoff until it is formalized

## Context/Problem Statement
- [ ] Compass can reuse stale runtime snapshots for rolling 24h/48h windows.
- [ ] Warmed bug projection state can stay stale after parser-contract changes.
- [ ] Standup-brief recovery can reuse stale global AI cache across changed
      fact packets.
- [ ] Install and upgrade-oriented narration can keep stale self-host or
      launcher assumptions after live runtime posture changes.
- [ ] Operators still need the full governance sync to express a narrow
      dashboard refresh, and Atlas Mermaid worker failures can look hung
      instead of naming the blocking diagram ids.
- [ ] Commit-time refresh and autofix are too late to be the first user-visible
      freshness signal in consumer shells.
- [ ] Current browser proof still misses some UX/UI freshness regressions.
- [x] Compass standup narration can still sound templated even when the facts
      are current, because both the provider contract and the deterministic
      fallback reuse the same stock lead-ins.
- [ ] Casebook detail view repeats the same signals across summary, guidance,
      and inspect sections, which makes the human-facing bug readout noisy.
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

## Success Criteria
- [x] Compass runtime reuse is bounded by both input change and age.
- [x] Current bug/risk/timeline truth is reflected in Compass after rerender,
      cross-tab hops, and reload.
- [ ] Changed global fact packets do not reuse stale last-known-good brief
      content.
- [ ] Live self-host/install posture changes invalidate stale Compass
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
- [x] Provider and deterministic Compass briefs no longer reuse stock
      lead-ins across sections, windows, and workstreams, and validation now
      rejects those canned openings before they reach the live payload.
- [ ] Casebook bug detail separates a crisp human readout from deeper Odylith
      agent learnings without repeating the same field content in both bands.
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
- [ ] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
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
- [x] [test_surface_browser_smoke.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_smoke.py)
- [x] [test_surface_browser_deep.py](/Users/freedom/code/odylith/tests/integration/runtime/test_surface_browser_deep.py)

## Risks & Mitigations

- [ ] Risk: stricter invalidation slows Compass too much.
  - [ ] Mitigation: bound runtime reuse by a small age budget instead of
    disabling reuse entirely.
- [ ] Risk: provider-backed scoped full refresh becomes too slow to trust as a
    shell action.
  - [x] Mitigation: fan scoped provider warming through a small worker pool
    instead of a fully serial per-workstream render.
- [ ] Risk: global brief freshness fix reduces resilience when provider is
    unavailable.
  - [ ] Mitigation: keep exact-cache reuse and deterministic fallback from the
    current fact packet.
- [ ] Risk: browser tests become brittle.
  - [ ] Mitigation: assert stateful user-visible contracts, not layout trivia.
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
- [x] `python -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime tests/integration/runtime/test_surface_browser_smoke.py`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_compass_dashboard --repo-root . --refresh-profile full`
- [x] `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root . --output odylith/index.html`
- [ ] `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_compass_dashboard.py tests/integration/runtime/test_surface_browser_smoke.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/test_cli.py`
- [ ] `odylith benchmark --repo-root .`
- [ ] `git diff --check`

## Rollout/Communication
- [ ] Note the Casebook regression explicitly so future Compass or shell
  freshness work sees the exact failure mode.
- [x] Note the Casebook regression explicitly so future Compass or shell
      freshness work sees the exact failure mode.
- [x] Rerender shipped shell and Compass assets before browser validation so
  the proof runs against the same artifacts users open.

## Current Outcome
- [ ] Bound to `B-025`; implementation in progress.
- [ ] Product direction clarified on 2026-04-01: commit-time autofix remains a
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
