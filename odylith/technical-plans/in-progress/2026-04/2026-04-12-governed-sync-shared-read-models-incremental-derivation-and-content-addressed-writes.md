Status: In progress

Created: 2026-04-12

Updated: 2026-04-14

Backlog: B-091

Goal: Cut governed sync from a shared-nothing step runner into one session-hoisted
derivation engine that preserves the exact backlog, Registry, delivery-intelligence,
Atlas, Compass, Casebook, and shell outcomes while removing redundant read-model
rebuilds, path canonicalization loops, and unchanged-output rewrites.

Assumptions:
- The current sync correctness contract stays intact: same tracked source truth,
  same validation gates, same rendered bytes for identical repo state.
- Warm incremental syncs matter more than forced cold full rebuilds when judging
  operator UX, but the architecture must not make `--force --impact-mode full`
  less truthful.
- The fastest honest first wave is an in-process shared session because sync already
  dispatches hot steps in one Python process on the runtime fast path.

Constraints:
- Do not weaken Radar, Registry, Atlas, or Compass fail-closed validation to hit
  the latency target.
- Do not let filesystem stat metadata become the only freshness authority for
  cached results; content truth and generator versioning still own correctness.
- Keep standalone and check-only behavior valid even if the first optimization
  wave primarily accelerates the in-process runtime fast path.

Reversibility: The shared-session and content-addressed write layers are additive.
If any cache or invalidation rule proves unsound, the fallback is to bypass the
session-derived result and recompute from canonical source truth without needing to
rewrite Radar, Registry, Atlas, or Compass contracts.

Boundary Conditions:
- Scope includes `odylith sync`, read-model hoisting for backlog specs and Registry
  report reuse, path canonicalization dedupe, repo-root inference hoisting,
  content-addressed no-op write elision, and focused surface-render plumbing.
- Scope excludes a full persistent sync daemon, filesystem-watch-backed live index,
  and a full node-level reverse-dependency graph across every governed fact; those
  stay explicit follow-on work once the first end-to-end cut proves the model.

Related Bugs:
- [CB-066](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-sync-refresh-rewrites-unchanged-artifacts-and-stales-generated-timestamps.md)
- [CB-110](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-14-forwarded-cli-help-hides-backend-flags-and-selective-sync-stays-too-wide-for-gov.md)
  tracks the governed-memory upkeep follow-on: forwarded `bug capture` and
  `compass log` help hid backend flags, `bug capture` line-patched the live
  Casebook index instead of regenerating it from source, and selective sync
  still widened explicit bug/plan/spec memory updates into the broad render
  graph.
- [CB-112](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-14-routine-authoring-commands-can-leave-owned-surfaces-stale-and-selective-sync-can.md)
  tracks the next quick-update follow-on: routine authoring commands outside
  Casebook stopped after writing truth, and direct Radar/Registry/Atlas
  selective refreshes still needed a surface-local visibility contract so the
  shared projection bundle plus local LanceDB/Tantivy substrate stayed fresh
  without a full sync wave.

## Learnings
- [x] Full governed sync is paying mainly for repeated discovery, not inherently
      expensive validation or rendering.
- [x] The sync runner already has an in-process fast path, so a shared session can
      land meaningful wins before a persistent daemon exists.
- [x] Path normalization, consumer-profile reads, idea parsing, Registry report
      construction, and repo-root inference all need one shared ownership model or
      they multiply across validators and renderers.
- [x] Content-addressed no-op writes are part of correctness hygiene, not just
      performance, because unchanged outputs should not dirty git or trigger
      downstream invalidation.
- [x] Shared reuse without an explicit derivation-generation and provenance
      contract is too risky: it hides stale-state failures behind good wall
      clock numbers and makes debugging much harder than the old redundant path.

## Must-Ship
- [x] Add one explicit sync-session runtime that owns repo root, consumer profile,
      truth-root resolution, path normalization, parsed idea specs, and component
      Registry report reuse for the duration of a sync.
- [x] Route the hottest governance helpers through that session so repeated step
      mains reuse one read model instead of reparsing and re-resolving.
- [x] Add content-addressed no-op write discipline to the first touched generated
      outputs so unchanged bytes do not rewrite tracked surfaces.
- [x] Keep the current sync plan and validation behavior externally compatible.
- [x] Add focused proof that the shared session is reused across sync steps and
      that unchanged writes stay quiet.
- [x] Make derivation generation, provenance, fail-closed reuse, and
      cache-explain evidence first-class product invariants rather than
      implementation folklore.
- [x] Stamp Compass, Radar, and Registry payloads with additive runtime
      provenance so operators can see what the surface was built from.

## Should-Ship
- [x] Hoist repo-root inference out of backlog parsing and promotion-link checks.
- [x] Replace repeated path-prefix normalization with session-interned canonical
      path tokens on the current sync hot paths.
- [x] Make the second Registry-spec sync effectively conditional on actual upstream
      mutations instead of unconditional repeated work when hashes already settled.
- [x] Skip the runtime governance-packet lane on forced/full syncs where impact is
      already all-surfaces, and make the direct sync projection warm authoritative
      for later runtime readers in the same process.
- [x] Re-harden the late Registry forensics reconciliation after shell-facing
      refresh steps so strict standalone proof does not drift red when later sync
      activity changes evidence consumed by component forensics.
- [x] Make source-bundle mirror artifacts inherit canonical generated/global
      policy where appropriate and collapse mirror/canonical aliases into one
      stable workspace-activity token so the final mirror step cannot reopen
      Registry forensics drift after a successful full sync.
- [x] Cache runtime warm and delivery-surface reads for one stable sync phase,
      then invalidate those sync-scoped caches exactly when repo-truth or
      delivery-artifact mutation steps change the phase.
- [x] Harden Atlas auto-update so `--all-stale` review-only refreshes never
      short-circuit on a cached guard hit while diagrams are still stale.
- [x] Let sync-planned generated-surface renders bypass their own refresh-guard
      tree scans when the sync planner has already decided the render must run,
      so full sync no longer pays a second watch-tree decision layer inside
      Radar, Registry, Casebook, and tooling-shell.
- [x] Narrow projection and runtime cache invalidation to the actual derivation
      inputs that can change projection truth, instead of clearing warm/runtime
      state after every generated HTML or JS write.
- [x] Reuse signature-scoped runtime projection rows for backlog, plan, bug,
      component-index, and Registry-snapshot readers so later surfaces do not
      reopen the same projection tables within one settled fingerprint.
- [x] Settle Atlas, Registry-truth, and delivery-intelligence mutations before
      the runtime-backed Compass, Radar, Registry, and shell renders so that
      one final warm serves the whole post-truth render phase instead of
      warming against an intermediate state and reopening the projection lane.
- [x] Make repo-scoped runtime invalidation clear projected-input fingerprint
      caches as well as warm verdicts, because generated derivation inputs like
      `odylith/radar/traceability-graph.v1.json` and
      `odylith/runtime/delivery_intelligence.v4.json` do not perturb the
      workspace-activity token on their own.
- [x] Memoize projection path-tree fingerprints per repo-state so compatible
      scope checks stop rescanning the same watched directories during one sync
      phase.
- [x] Make compiler and backend manifests carry explicit provenance tuples and
      reject reuse on generation or code-version mismatch instead of trusting
      fingerprint-only matches.
- [x] Persist a sync debug manifest under `.odylith/cache/odylith-context-engine/`
      that records invalidation events plus surface/cache decisions for the
      active run.
- [x] Reuse Compass live governance context inside the active sync generation
      so release/workstream/wave truth is built once per settled traceability
      signature instead of being re-derived on every Compass payload build.
- [x] Reuse Compass backlog-row projection results inside the active sync
      generation so Compass payload assembly does not reopen backlog table
      shaping after the first runtime-backed surface already built the rows.
- [x] Make sync-side runtime invalidation change-aware from watched derivation
      outputs so byte-identical traceability or delivery artifacts do not clear
      compatible warm state or trigger superstitious follow-up reruns.
- [x] Delay in-process sync heartbeats until a step actually stays slow, so
      fast steps do not pay a steady-state polling lane or emit misleading
      chatter just to report a sub-second call.
- [x] During governed sync, let Compass reuse the already-settled Radar index
      directly for backlog rows instead of reopening the default projection
      warm just to recover active/execution backlog tables.
- [x] Keep in-process heartbeat wrapping on the truly long render modules only,
      so validators and lighter reconciliation steps run directly without
      paying thread/queue wait overhead in the runtime fast path.
- [x] Add a truth-only selective sync lane for explicit Casebook bug markdown,
      active-plan, and Registry living-spec edits so governed memory upkeep can
      validate and mirror the touched source truth without widening into Atlas,
      delivery-intelligence, or dashboard renders.
- [x] Make forwarded top-level help for `odylith bug capture` and
      `odylith compass log` resolve against the backend parser so operators can
      discover real flags without source spelunking.
- [x] Route routine authoring commands through one shared owned-surface refresh
      helper so `backlog create`, `component register`, `atlas scaffold`, and
      `compass log` mutate truth, refresh the smallest visible owned surface,
      and stop.
- [x] Let the selective governed-memory lane refresh owned Radar, Registry,
      Atlas, and Casebook surfaces directly from touched source truth while
      keeping the shared projection compiler and local LanceDB/Tantivy backend
      current through the same narrow render path.
- [x] Land the same owned-surface quick-refresh contract in repo-root guidance,
      consumer guidance, bundle docs, Codex shims, and Claude commands so dev,
      dogfood, and consumer lanes stop advertising a stale
      `dashboard refresh --surfaces <surface>` hop for routine single-surface
      visibility.
- [x] Short-circuit explicit truth-only selective sync before the runtime
      governance-packet planner and broad backlog preflight when the changed
      paths already determine the owned surfaces, while still keeping targeted
      Radar validation on plan/backlog slices.
- [x] Scope source-truth bundle mirroring to the explicit changed-path slice
      instead of rescanning repo-wide git state, and let single-surface
      Radar/Registry/Casebook refreshes stay on the in-process runtime fast
      lane when the shared LanceDB/Tantivy substrate is ready.

## Defer
- [ ] Persistent sync daemon with warm resident session state across commands.
- [ ] Full per-node reverse-dependency DAG and fixpoint scheduler across all
      governed facts and rendered surfaces.
- [ ] Filesystem watch integration for near-zero-cost startup change detection.

## Success Criteria
- [x] Warm incremental sync proves one shared session across the hot governance
      step chain rather than repeated read-model reconstruction.
- [x] Unchanged generated outputs stop rewriting bytes on the first landed
      content-addressed paths.
- [x] Focused profiling shows lower call counts for path normalization, repo-root
      inference, idea parsing, and Registry report construction on the optimized
      sync path.
- [x] `odylith sync --check-only --runtime-mode standalone` still proves the
      governed slice fail-closed.
- [x] Reused and cold-built substrate decisions are explainable from a local
      debug manifest instead of only from profiler receipts.
- [x] Explicit selective bug/plan/spec memory edits stay on a truth-only sync
      lane, and forwarded `bug capture` / `compass log` help surfaces expose
      the real backend flags at the top-level CLI.
- [x] Routine authoring writes and selective direct surface-truth edits become
      immediately visible on the owned surface without widening into the full
      governance sync DAG, while the shared projection/memory substrate stays
      fresh.
- [x] Dev guidance, dogfood bundle assets, consumer install guidance, Codex
      shims, and Claude helper commands all advertise the same owned-surface
      quick-refresh commands for Radar, Registry, Casebook, Atlas, and Compass.

## Non-Goals
- [ ] Claiming sub-second cold forced full sync from scratch in Python.
- [ ] Replacing the entire sync step graph with a daemon-only control plane in
      this first implementation wave.
- [ ] Inventing a new Registry component boundary before the implementation proves
      one is needed.

## Impacted Areas
- [x] [2026-04-12-sub-second-governed-sync-via-shared-read-models-incremental-derivation-and-content-addressed-surface-writes.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-12-sub-second-governed-sync-via-shared-read-models-incremental-derivation-and-content-addressed-surface-writes.md)
- [x] [2026-04-12-governed-sync-shared-read-models-incremental-derivation-and-content-addressed-writes.md](/Users/freedom/code/odylith/odylith/technical-plans/in-progress/2026-04/2026-04-12-governed-sync-shared-read-models-incremental-derivation-and-content-addressed-writes.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith/CURRENT_SPEC.md)
- [x] [diagrams.v1.json](/Users/freedom/code/odylith/odylith/atlas/source/catalog/diagrams.v1.json)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [generated_surface_refresh_guards.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/generated_surface_refresh_guards.py)
- [x] [workstream_inference.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/workstream_inference.py)
- [x] [validate_backlog_contract.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/validate_backlog_contract.py)
- [x] [component_registry_intelligence.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/component_registry_intelligence.py)
- [x] [consumer_profile.py](/Users/freedom/code/odylith/src/odylith/runtime/common/consumer_profile.py)
- [x] [derivation_provenance.py](/Users/freedom/code/odylith/src/odylith/runtime/common/derivation_provenance.py)
- [x] [sync_session.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_session.py)
- [x] [odylith_memory_backend.py](/Users/freedom/code/odylith/src/odylith/runtime/memory/odylith_memory_backend.py)
- [x] [render_compass_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_compass_dashboard.py)
- [x] [render_backlog_ui.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui.py)
- [x] [render_backlog_ui_payload_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_backlog_ui_payload_runtime.py)
- [x] [render_registry_dashboard.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_registry_dashboard.py)
- [x] [odylith_context_engine_projection_backlog_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_backlog_runtime.py)
- [x] [odylith_context_engine_projection_registry_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_registry_runtime.py)
- [x] [odylith_context_engine_projection_compiler_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_compiler_runtime.py)
- [x] [CONTEXT_ENGINE_OPERATIONS.md](/Users/freedom/code/odylith/odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md)
- [x] focused sync/runtime tests covering session reuse, path-cache behavior, no-op
      write elision, generation gating, and cache-explain evidence

## Rollout
1. Bind the workstream, plan, Registry dossier, and Atlas diagram so the
   architecture is explicit before code shifts.
2. Land the shared sync-session layer and route the current hot governance paths
   through it.
3. Add content-addressed no-op writes on the first governed render targets.
4. Re-profile, then decide whether the next justified wave is a broader DAG
   invalidation engine or a resident daemon.
5. Keep latency work behind the new provenance/generation contract so later
   daemon or DAG waves cannot trade correctness for speed.

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_workstream_inference.py tests/unit/runtime/test_validate_backlog_contract.py tests/unit/runtime/test_component_registry_intelligence.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_context_grounding_hardening.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_casebook_dashboard.py tests/unit/runtime/test_render_backlog_ui.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_workstream_inference.py tests/unit/runtime/test_component_registry_intelligence.py tests/unit/runtime/test_sync_component_spec_requirements.py tests/unit/runtime/test_surface_projection_fingerprint.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_odylith_context_engine_store.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_generated_refresh_guard.py tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_odylith_context_engine_store.py` (`122 passed` on 2026-04-11 after the projection-invalidation tightening, sync-owned render-guard bypass, and signature-scoped projection-row reuse landed)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full` (`9.1s` elapsed / `10.44s` wall clock on 2026-04-11 after phase-scoped runtime warm reuse, delivery-surface session reuse, mutation-boundary cache invalidation, and the Atlas all-stale guard hardening; the same profile lane now shows `warm_projections()` down to `2` calls / `2.16s` cumulative and `load_delivery_surface_payload()` down to `0.48s` cumulative)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone` (passes serially after a full write-mode sync on 2026-04-11 in `5.1s`, with Atlas freshness and delivery-intelligence both green once the write-mode lane settles)
- [x] `/usr/bin/time -p env PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full` (`6.3s` sync-reported elapsed / `7.46s` wall clock on 2026-04-11 after sync-owned render-guard bypass and projection invalidation tightening)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone` (passes serially on 2026-04-11 in `4.6s` after the same write-mode lane, with the remaining proof warning isolated to Compass visible-runtime drift rather than a failing contract)
- [x] `python3 -m cProfile -o /tmp/b091-sync-latest.prof -m odylith.cli sync --repo-root . --force --impact-mode full` (`_warm_runtime_uncached` down to `2` calls / `3.88s` cumulative, `render_backlog_ui.main` down to `0.63s` cumulative, `render_tooling_dashboard.main` down to `0.39s`, `should_skip_surface_rebuild()` down to `0.009s`, and the remaining top CPU sites now concentrated in Compass runtime payload build, Registry snapshot shaping, and projection fingerprint trees)
- [x] `/usr/bin/time -p env PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full` (`5.4s` sync-reported elapsed / `6.26s` wall clock on 2026-04-12 once the tree had settled after the render-phase reorder, repo-scoped projection-fingerprint invalidation hardening, and per-repo-state path-tree fingerprint memoization landed)
- [x] `python3 -m cProfile -o /tmp/b091-latest-current.prof -m odylith.cli sync --repo-root . --force --impact-mode full` (`projection_input_fingerprint()` down to `1.33s` cumulative, `_compute_projected_input_fingerprints()` down to `1.21s`, `fingerprint_tree()` down to `0.98s`, and `warm_projections()` down to `2.26s`; the remaining dominant costs are now Compass runtime payload assembly at `3.94s` cumulative and Registry payload/snapshot shaping at `2.20s` / `1.87s`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_derivation_provenance.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_odylith_memory_backend.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_sync_cli_compat.py` (`113 passed` on 2026-04-12 after derivation-generation, provenance, surface-contract, and cache-explain coverage landed)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_base.py tests/unit/runtime/test_sync_cli_compat.py` (`45 passed` on 2026-04-12 after Compass backlog-row session reuse, change-aware sync invalidation, and thresholded heartbeat coverage landed)
- [x] `PYTHONPATH=src python3 -m cProfile -o /tmp/odylith_r8_full.prof -m odylith.cli sync --repo-root . --force --impact-mode full` (`7.7s` sync-reported elapsed / `9.96s` cProfile total on 2026-04-12 after Compass backlog-row reuse and watched-output invalidation gating landed; `load_backlog_rows()` fell to `0.19s`, `_build_runtime_payload()` fell to `1.69s`, `_warm_runtime_uncached` collapsed to `1` call, and `select.poll` dropped to `0.94s`)
- [x] `/usr/bin/time -p env PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full` (`5.8s` sync-reported elapsed / `6.87s` wall clock on 2026-04-12 after the source-local write-mode lane refreshed delivery intelligence truth against the new code path; only Compass crossed the `2s` heartbeat threshold)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone` (`5.1s` on 2026-04-12 after the source-local full sync settled, with Atlas freshness, Registry truth, and delivery intelligence all green in strict non-mutating proof)
- [x] `PYTHONPATH=src python3 -m cProfile -o /tmp/odylith_r8_final.prof -m odylith.cli sync --repo-root . --force --impact-mode full` (`9.7s` sync-reported elapsed / `11.56s` cProfile total on 2026-04-12; `render_compass_dashboard.main` is `3.69s`, `_build_runtime_payload()` is `3.18s`, `_warm_runtime_uncached` is `1.63s` across `1` call, `load_backlog_rows()` is `1.70s` across `2` total callers, and `select.poll` is `1.00s`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_compass_dashboard_base.py tests/unit/runtime/test_sync_cli_compat.py -k "backlog_rows or run_command_in_process or heartbeat"` (`6 passed` on 2026-04-12 after source-backed Compass backlog-row reuse and selective in-process heartbeat wrapping landed)
- [x] `/usr/bin/time -p env PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --force --impact-mode full` (`5.9s` sync-reported elapsed / `6.96s` wall clock on 2026-04-12 after Compass started reusing the settled Radar index for backlog rows during sync and short in-process steps stopped paying the heartbeat thread wrapper)
- [x] `PYTHONPATH=src python3 -m cProfile -o /tmp/odylith_latency_after.prof -m odylith.cli sync --repo-root . --force --impact-mode full` (`10.6s` sync-reported elapsed / `12.77s` cProfile total on 2026-04-12; `render_compass_dashboard.main` is `4.10s`, `_build_runtime_payload()` is `3.52s`, `load_backlog_rows()` collapsed to `0.034s`, `warm_projections()` is `1.048s`, `select.poll` is `1.066s`, and `normalize_repo_token()` is `0.968s`)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone` (`5.1s` on 2026-04-12 after the same source-backed Compass backlog-row and selective-heartbeat cut, with delivery intelligence current and the strict standalone lane still fail-closed)
- [x] `pytest -q tests/unit/test_cli.py::test_bug_capture_help_forwards_backend_flags tests/unit/test_cli.py::test_compass_log_help_forwards_backend_flags tests/unit/test_cli.py::test_bug_capture_rebuilds_multiline_casebook_index_from_source tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_uses_truth_only_selective_lane_for_governance_memory_slice tests/unit/runtime/test_casebook_bug_index.py tests/unit/runtime/test_odylith_memory_areas.py::test_load_bug_projection_handles_multiline_open_bug_rows` (`11 passed` on 2026-04-14 after forwarded-help exposure, Casebook-index regeneration, and truth-only selective sync landed)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_owned_surface_refresh_authoring.py tests/unit/test_cli.py -k 'dashboard_refresh_dispatches_selected_surfaces or dashboard_refresh_defaults_to_tooling_shell_radar_and_compass or radar_refresh_dispatches_owned_surface_lane or registry_refresh_dispatches_owned_surface_lane or casebook_refresh_dispatches_owned_surface_lane or atlas_refresh_dispatches_owned_surface_lane or bug_capture_help_forwards_backend_flags or compass_log_help_forwards_backend_flags or backlog_create_help_forwards_backend_flags or component_register_help_forwards_backend_flags or atlas_scaffold_help_forwards_backend_flags or atlas_render_help_forwards_backend_flags or atlas_auto_update_help_forwards_backend_flags or atlas_install_autosync_hook_help_forwards_backend_flags or bug_capture_rebuilds_multiline_casebook_index_from_source or bug_capture_raises_when_casebook_refresh_fails'` (`16 passed` on 2026-04-14 after the owned-surface authoring refresh helper plus `radar`/`registry`/`casebook`/`atlas refresh` entrypoints landed)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_sync_cli_compat.py -k 'owned_surface_selective_lane_for_governance_memory_slice or refreshes_registry_for_spec_only_selective_slice or refreshes_atlas_for_catalog_only_selective_slice or requires_sync_treats_casebook_bug_markdown_as_sync_relevant or build_sync_execution_plan_runs_final_registry_reconcile_after_bundle_mirror'` (`5 passed` on 2026-04-14 after selective sync started refreshing owned Radar/Registry/Atlas surfaces on the shared projection/memory lane)
- [x] `PYTHONPATH=src .venv/bin/python -m pytest -q tests/unit/runtime/test_sync_cli_compat.py tests/unit/runtime/test_owned_surface_refresh_authoring.py tests/unit/runtime/test_odylith_memory_backend.py tests/unit/runtime/test_generated_refresh_guard.py tests/unit/runtime/test_derivation_provenance.py` (`68 passed` on 2026-04-14 after the truth-only entrypoint short-circuit, explicit changed-path mirror scoping, and single-surface in-process refresh lane landed)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_agents.py tests/integration/install/test_bundle.py::test_bundle_root_contains_installed_agents_entrypoint tests/integration/install/test_manager.py -k 'install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle or upgrade_install_resyncs_consumer_guidance_and_skills'` (`5 passed` on 2026-04-14 after root guidance, consumer guidance, bundle docs, and Claude command shims all switched to the same owned-surface quick-refresh wording)
- [x] `/usr/bin/time -p env PYTHONPATH=src .venv/bin/python -m odylith.cli radar refresh --repo-root .` (`1.5s` sync-reported / `1.78s` wall on 2026-04-14 after single-surface refreshes started staying on the in-process fast lane)
- [x] `/usr/bin/time -p env PYTHONPATH=src .venv/bin/python -m odylith.cli registry refresh --repo-root .` (`4.8s` sync-reported / `5.03s` wall on 2026-04-14 with delivery-intelligence current and Registry rerendered on the narrow lane)
- [x] `/usr/bin/time -p env PYTHONPATH=src .venv/bin/python -m odylith.cli casebook refresh --repo-root .` (`1.5s` sync-reported / `1.67s` wall on the warmed 2026-04-14 proof lane after the owned-surface refresh used the in-process runtime path)
- [x] `/usr/bin/time -p env PYTHONPATH=src .venv/bin/python -m odylith.cli atlas refresh --repo-root . --atlas-sync` (`0.2s` sync-reported / `0.35s` wall on 2026-04-14 with `37 fresh / 0 stale`)
- [x] `/usr/bin/time -p env PYTHONPATH=src .venv/bin/python -m odylith.cli sync --repo-root . --impact-mode selective --registry-policy-mode advisory --proceed-with-overlap odylith/casebook/bugs/2026-04-14-routine-authoring-commands-can-leave-owned-surfaces-stale-and-selective-sync-can.md odylith/technical-plans/in-progress/2026-04/2026-04-12-governed-sync-shared-read-models-incremental-derivation-and-content-addressed-writes.md odylith/registry/source/components/odylith/CURRENT_SPEC.md odylith/atlas/source/catalog/diagrams.v1.json` (`6.9s` sync-reported / `7.33s` wall on 2026-04-14 while refreshing only Radar, Atlas, Registry, and Casebook)
- [x] `pytest -q tests/unit/runtime/test_sync_cli_compat.py::test_sync_changed_source_truth_bundle_mirrors_updates_changed_docs tests/unit/runtime/test_sync_cli_compat.py::test_sync_changed_source_truth_bundle_mirrors_updates_runtime_source_corpus tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_appends_source_bundle_mirror_step tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_runs_final_registry_reconcile_after_bundle_mirror tests/unit/runtime/test_sync_cli_compat.py::test_build_sync_execution_plan_final_registry_reconcile_triggers_delivery_stabilization` (`5 passed` on 2026-04-14 to prove the narrowed mirror scope did not regress the broader plan contract)
- [x] `git diff --check`

## Outcome Snapshot
- [x] Governed sync stops behaving like twenty loosely related tools that all
      rediscover the same repo state.
- [x] The first optimization wave makes one shared read model visible in code and
      in profiling data.
- [x] Unchanged generated surfaces begin to stay byte-stable across no-op syncs.
- [x] Heavy Radar, Registry, Casebook, and tooling-shell renders now fingerprint
      their watched input cone and skip payload rebuilds entirely when the emitted
      bundle set still matches.
- [x] Full-mode sync no longer spends a reasoning-scope runtime warmup on an
      impact planner it does not need, and a direct sync warm now prevents later
      surface readers from rebuilding the same default projection a second time.
- [x] Runtime-backed readers now reuse one sync-phase warm verdict and one
      delivery-surface load per stable mutation phase instead of re-deriving the
      same projection fingerprint chain on every surface access.
- [x] Sync-planned Radar, Registry, Casebook, and tooling-shell renders now
      trust the sync planner and skip redundant watch-tree refresh-guard scans,
      which removes that second rebuild-decision layer from the full sync lane.
- [x] Projection/runtime invalidation now follows derivation-input boundaries,
      so generated HTML and JS writes do not blow away warmed runtime state
      unless they actually changed a projection input like traceability or
      delivery-intelligence truth.
- [x] Runtime projection row readers now reuse one signature-scoped row payload
      for backlog, plans, bugs, component index, and Registry snapshot reads,
      which cuts duplicate table shaping across Compass, Radar, and Registry.
- [x] Compass backlog rows now ride that same sync-scoped reuse contract, which
      removes repeated backlog row shaping from later Compass payload builds in
      the same settled generation.
- [x] Compass backlog rows now short-circuit to the already-settled Radar
      index inside governed sync, which removes the expensive default-scope
      projection warm from the Compass render lane without weakening the
      source-truth contract.
- [x] Runtime-backed surfaces now render in one settled post-truth phase:
      Atlas review/catalog truth, Registry spec reconciliation, and delivery
      intelligence settle first, then Compass, Radar, Registry, Casebook, and
      shell reuse one final warm against that state.
- [x] Repo-scoped runtime invalidation now clears projected-input fingerprint
      caches as well as warm verdicts, which closes the stale-reuse hole for
      generated derivation inputs that do not change the workspace-activity
      token by themselves.
- [x] Projection path-tree fingerprints are now memoized per repo-state, which
      materially reduces repeated watched-tree scans across compatible scope
      checks inside one sync phase.
- [x] Sync-side runtime invalidation now checks the watched derivation outputs
      before clearing warm state, so byte-identical traceability and delivery
      writes no longer reopen the same projection warm or follow-up rerender
      lane by reflex.
- [x] The current full source-local sync lane now reaches one compatible
      runtime warm in profile, rather than the earlier double-warm pattern that
      reopened the same projection substrate during Compass and later surfaces.
- [x] Fast in-process sync steps now stay quiet until they cross a real
      heartbeat threshold, which trims the heartbeat polling tax and keeps
      sub-threshold steps from paying for operator progress noise.
- [x] Fast in-process sync steps now run directly while only the truly slow
      render modules keep heartbeat wrapping, which cuts the standing
      thread/queue wait tax from the runtime fast path without hiding real
      long-running progress.
- [x] Strict standalone proof stays fail-closed after the optimization wave
      because late Registry forensics reconciliation now accounts for shell-facing
      steps that can still change evidence after the first spec sync.
- [x] The final source-bundle mirror step no longer reopens strict Registry
      forensics drift because bundle-source aliases now collapse to one stable
      evidence token and inherit canonical generated/global policy where that
      mirror is only echoing derived/global truth.
- [x] Atlas all-stale review refreshes now bypass stale cached auto-update
      short-circuits, so full sync and strict standalone proof no longer diverge
      on review-only diagram freshness.
- [x] Explicit selective bug/plan/spec memory updates now stay on a truth-only
      lane that validates the touched plan slice, refreshes Casebook index
      truth, mirrors the touched bundle docs, and skips Atlas,
      delivery-intelligence, and dashboard renders.
- [x] Forwarded top-level help for `odylith bug capture` and
      `odylith compass log` now exposes the backend flags directly, and
      `bug capture` regenerates the Casebook index from markdown source instead
      of patching multiline table rows in place.
- [x] The remaining hot path is now much narrower and more honest: Compass
      runtime payload assembly, Registry snapshot shaping, and projection
      fingerprint trees dominate after the path storm and redundant surface
      guard scans were cut out of the full sync lane.
- [x] Shared sync/runtime reuse is now governed by hard invariants: derivation
      generation, content-addressed provenance, fail-closed reuse, additive
      surface provenance, and persisted cache-explain evidence all ship as part
      of the product contract instead of as undocumented implementation detail.
- [x] Compass no longer rebuilds the live release/workstream/wave governance
      context for every payload inside one sync generation; it reuses one
      generation-gated, traceability-scoped snapshot and falls back to a cold
      rebuild immediately when the sync generation advances.
