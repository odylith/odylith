Status: In progress

Created: 2026-04-09

Updated: 2026-04-09

Backlog: B-071

Goal: Replace surface-local scope visibility and priority heuristics with one
shared Scope Signal Ladder contract that governs default visibility,
promotion, and expensive compute budgets across Compass, Radar, Registry,
Atlas, Dashboard, and downstream reasoning or narration jobs.

Assumptions:
- The raw source surfaces should stay exhaustive; focus gating belongs in
  default operational views, not in the source-of-truth layer itself.
- Compass's live narration quality must remain plainspoken, human, and
  free-flowing. Cost cuts have to happen in gating and reuse, not by lowering
  the voice bar.
- The bounded Compass path now has only two acceptable runtime lanes: hot
  exact reuse under `50ms` of internal runtime work and cold complete
  shell-safe refresh under `1s` of internal runtime work. The ladder work must
  not reopen a third slower lane.
- Deterministic, auditable ranking is the right v1 contract; opaque model-led
  ranking would make governance harder to trust and harder to debug.

Constraints:
- Keep low-signal scopes hidden by default, but preserve explicit deep links as
  quiet state instead of returning false activity.
- Do not let the ladder add noticeable overhead to the hot Compass path.
- Use provider-neutral budget classes so the same product contract works
  across Codex, Claude, and future hosts.
- Avoid re-deriving urgency locally once the shared ladder is present.

Reversibility: The ladder is additive contract and ordering logic. If a rung or
budget rule is too strict, the rollback is to adjust deterministic rules or
consumer thresholds without rewriting source truth.

Boundary Conditions:
- Scope includes Delivery Intelligence snapshots, Compass rolling-window scope
  gating, Radar default focus ordering, Registry ordering, Atlas active
  workstream promotion, shell budget classes, and governed guidance.
- Scope excludes visual redesign and any attempt to remove exhaustive work from
  Radar or raw traceability outputs.

Related Bugs:
- [CB-088](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-scoped-selector-can-advertise-unverified-window-activity-and-leak-global-audit-cards.md)
  proved that Compass could still advertise a scope with no verified local
  movement when local heuristics were too loose.
- [CB-092](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-compass-timeline-audit-cards-can-hide-their-own-anchor-workstream-in-visible-chip-row.md)
  proved that even after the right scope was inferred, Compass could still let
  broader linked scopes hide that anchor fix from the visible chip row.
- [CB-090](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-09-low-signal-governance-churn-can-outrank-real-execution-across-governance-surfaces.md)
  is the umbrella architecture bug for cross-surface low-signal promotion and
  budget drift.

## Learnings
- [x] Compass quiet-scope failures were not just Compass bugs; they exposed a
      broader product problem that each surface still had its own answer to
      "what counts as locally important."
- [x] Governance-only local churn, generated-only churn, and broad fanout rows
      are the three big low-signal classes that repeatedly masquerade as real
      work unless they are capped centrally.
- [x] Proof-state blockers need explicit precedence over ordinary activity
      signals; otherwise the operator can get a busy-looking surface that still
      buries the actual blocker frontier.
- [x] Budget gating and focus gating are the same contract wearing different
      clothes. If the ladder says a scope is background trace, the runtime
      should not spend fresh provider or heavier reasoning budget on it either.
- [x] Cheap fallback is not allowed to sound cheap. If the ladder forces
      Compass onto deterministic coverage, that prose still has to clear the
      same plainspoken live-narration bar instead of slipping back into canned
      stock wrappers.

## Must-Ship
- [x] Add one shared Scope Signal Ladder contract under Delivery Intelligence
      with deterministic rung rules, reasons, caps, feature vectors, promotion
      bit, and provider-neutral budget class.
- [x] Extend delivery snapshots additively with `scope_signal` and make
      Delivery Intelligence the single owner of scope escalation.
- [x] Make Compass scope dropdowns and scoped timelines require `R2+` for the
      exact window while preserving explicit low-signal deep links as quiet
      state.
- [x] Make Compass promoted workstreams and default brief focus draw from `R3+`
      scopes instead of local heuristics.
- [x] Gate fresh scoped provider narration to `R4-R5` only; lower rungs must
      stay cache or deterministic.
- [x] Make Radar default operational ordering, Registry ordering, and Atlas
      active-workstream promotion use the ladder instead of local urgency
      guesses.
- [x] Define provider-neutral budget classes for shell and downstream consumers
      so cost policy is not hardcoded to Codex naming.
- [x] Add the governed workstream, plan, Casebook memory, Atlas diagrams,
      component-spec updates, guidance, and browser proof so the contract does
      not live in code only.

## Should-Ship
- [x] Add one focused browser proof that low-signal scopes stay out of Compass
      selectors but still preserve deep links quietly.
- [x] Add one focused browser proof that Radar default focus continues to
      expose exhaustive backlog truth while promoting the higher ladder rungs.
- [x] Add one focused browser proof that Atlas active-workstream pills suppress
      low-rung scopes.
- [x] Keep Compass hot and cold paths at or below the current measured runtime
      envelope while the ladder ships.

## Defer
- [ ] User-facing ladder labels or operator toggles for "show suppressed
      background trace" are not needed in v1.
- [ ] Offline calibration or ML ranking can wait until deterministic rung
      traces have enough history to justify tuning.

## Success Criteria
- [x] Lone governance-file local change no longer promotes a scope above `R1`.
- [x] Broad fanout rows no longer advertise local Compass scope by themselves.
- [x] Generated-only churn is suppressed to `R0`.
- [x] Verified local movement reaches `R2` and becomes window-visible in
      Compass.
- [x] Real implementation or decision evidence reaches `R3` and becomes
      default-promoted in operational views.
- [x] Open warning or stale-authority posture reaches `R4`.
- [x] Proof-state blocker or unsafe closeout reaches `R5`.
- [x] `R0-R3` scopes do not trigger fresh provider or escalated reasoning work
      by default.
- [x] Browser proof catches cross-surface promotion drift.
- [x] Timeline Audit keeps the transaction's anchor workstream visible and
      first in the chip row instead of letting broader linked scopes bury it.

## Non-Goals
- [ ] Replacing Radar as the exhaustive workstream source of truth.
- [ ] Hiding detail or forensic evidence from deep-linked or detail views.
- [ ] Letting model-generated ranking replace deterministic product policy.

## Impacted Areas
- [x] `src/odylith/runtime/governance/delivery_intelligence_engine.py`
- [x] `src/odylith/runtime/governance/delivery/scope_signal_ladder.py`
- [x] `src/odylith/runtime/surfaces/compass_runtime_payload_runtime.py`
- [x] `src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py`
- [x] `src/odylith/runtime/surfaces/render_backlog_ui_html_runtime.py`
- [x] `src/odylith/runtime/surfaces/render_registry_dashboard.py`
- [x] `src/odylith/runtime/surfaces/render_mermaid_catalog.py`
- [x] `src/odylith/runtime/orchestration/odylith_chatter_delivery_runtime.py`
- [x] Compass, Radar, Delivery Intelligence, Dashboard, Proof State, Registry,
      and Atlas governed source/spec updates
- [x] Atlas diagrams `D-028` and `D-029`

## Rollout
1. Ship the shared ladder contract and integrate it into delivery snapshots.
2. Route Compass, Radar, Registry, Atlas, and shared consumer ordering or
   budget decisions through the ladder.
3. Refresh governed source, diagrams, and browser proof.
4. Tune runtime reuse and selection so the ladder does not cost Compass hot or
   cold budgets.

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_scope_signal_ladder.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_backlog_ui_payload_runtime.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_odylith_assist_closeout.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_scope_signal_ladder.py tests/unit/runtime/test_delivery_intelligence_engine.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_refresh_runtime.py tests/unit/runtime/test_compass_standup_brief_batch.py tests/unit/runtime/test_compass_window_update_index.py tests/unit/runtime/test_render_backlog_ui_payload_runtime.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_odylith_assist_closeout.py tests/unit/runtime/test_proof_state_runtime.py tests/unit/runtime/test_release_planning.py tests/unit/runtime/test_release_truth_runtime.py tests/unit/runtime/test_tooling_dashboard_surface_status.py tests/unit/runtime/test_workstream_progress.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
- [x] `PYTHONPATH=src python3 -m odylith.cli atlas render --repo-root .`
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --runtime-mode standalone --proceed-with-overlap`
- [x] `git diff --check`

## Outcome Snapshot
- The shared ladder now ships as product contract and rendered truth:
  Delivery Intelligence owns `scope_signal`, Compass window selectors/timelines
  require `R2+`, promoted focus uses `R3+`, and fresh scoped provider spend is
  reserved for `R4-R5`.
- Radar, Registry, Atlas, and shared delivery readouts now consume the same
  rung and budget-class policy instead of rebuilding urgency locally.
- Full browser proof is green after the rollout: `91 passed, 1 skipped`.
- The same ladder cleanup now reaches Timeline Audit prominence too: when a
  transaction headline or checkpoint anchors on a workstream such as `B-071`,
  the visible chip row keeps that same workstream first instead of trimming it
  behind broader linked scope lists.
- Compass budget note: the ladder itself did not worsen the current shell-safe
  runtime envelope, but Compass still remains above the founder target. The
  measured source-local shell-safe runs after this rollout were `real 2.03`
  on the first run and `real 1.25` on the immediate rerun, so the remaining
  budget gap still lives upstream of the ladder contract. The later
  maintained-global narration follow-on kept the live global windows on
  `cache exact` instead of dropping back to deterministic, so the ladder now
  rides on top of a bounded narrated-cache contract rather than paying or
  flattening the globals again.
- Release bar remains open after the next follow-on too. The current bounded
  hot exact-reuse lane is `0.3s` internal (`0.73s` wall), the current rebuilt
  cold shell-safe lane is `1.7s` internal (`2.18s` wall), and the ready-brief
  mix is now `35 cache / 0 deterministic`. The ladder rollout no longer shares
  a live-narration blocker with Compass; the remaining miss is cold wall-clock
  overhead upstream of the ladder contract.
