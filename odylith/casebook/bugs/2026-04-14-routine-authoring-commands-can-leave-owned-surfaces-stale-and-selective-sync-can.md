- Bug ID: CB-112

- Status: Open

- Created: 2026-04-14

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Routine authoring commands can leave owned surfaces stale and selective sync can skip direct surface visibility refresh

- Impact: Routine upkeep looked partially broken even when the source-truth write
  succeeded because `backlog create`, `component register`, `atlas scaffold`,
  and `compass log` could leave the owned surface stale until a second manual
  refresh, while selective sync for direct Radar/Registry/Atlas truth edits
  could still skip the visible surface update entirely. That made fast
  governance maintenance feel unreliable and forced operators back toward the
  slower full-sync lane just to see their own change reflected.

- Components Affected: odylith

- Environment(s): Product-repo maintainer mode and downstream repos using
  routine authoring commands or explicit `odylith sync --impact-mode selective`
  for small governed source-truth edits.

- Root Cause: Casebook had already grown the correct post-write contract
  (`capture -> rebuild index -> rerender owned surface`), but the other
  authoring commands still stopped after writing source truth. The selective
  sync planner also treated direct Registry-spec, Radar, and Atlas source edits
  as either a truth-only mirror lane with no visible render or a wider render
  graph, instead of routing them through the same owned-surface refresh engine
  that already warms the projection compiler and local LanceDB/Tantivy
  substrate truthfully.

- Solution: Add one shared owned-surface refresh helper, route `backlog
  create`, `component register`, `atlas scaffold`, and `compass log` through it
  by default, expose surface-local `radar refresh`, `registry refresh`,
  `casebook refresh`, and `atlas refresh` commands, and broaden the selective
  governed-memory lane so direct Casebook/Radar/Registry/Atlas source edits
  refresh only the touched owned surfaces while still reusing the shared
  projection/memory refresh path. Then land that same quick-update wording in
  repo-root guidance, consumer guidance, Codex shims, Claude commands, and
  shipped bundle docs so no host or lane still teaches a stale
  `dashboard refresh --surfaces <surface>` hop for routine single-surface
  visibility. Follow that with a second latency pass that short-circuits the
  truth-only selective sync entrypoint before the runtime governance-packet
  planner and broad backlog preflight, scopes source-truth bundle mirroring to
  the explicit changed paths instead of rescanning git, and lets single-surface
  Radar/Registry/Casebook refreshes stay on the in-process runtime fast lane
  when LanceDB/Tantivy are ready.

- Verification: `PYTHONPATH=src python3 -m pytest -q
  tests/unit/runtime/test_owned_surface_refresh_authoring.py
  tests/unit/test_cli.py -k 'dashboard_refresh_dispatches_selected_surfaces or
  dashboard_refresh_defaults_to_tooling_shell_radar_and_compass or
  radar_refresh_dispatches_owned_surface_lane or
  registry_refresh_dispatches_owned_surface_lane or
  casebook_refresh_dispatches_owned_surface_lane or
  atlas_refresh_dispatches_owned_surface_lane or
  bug_capture_help_forwards_backend_flags or
  compass_log_help_forwards_backend_flags or
  backlog_create_help_forwards_backend_flags or
  component_register_help_forwards_backend_flags or
  atlas_scaffold_help_forwards_backend_flags or
  atlas_render_help_forwards_backend_flags or
  atlas_auto_update_help_forwards_backend_flags or
  atlas_install_autosync_hook_help_forwards_backend_flags or
  bug_capture_rebuilds_multiline_casebook_index_from_source or
  bug_capture_raises_when_casebook_refresh_fails'` and `PYTHONPATH=src python3
  -m pytest -q tests/unit/runtime/test_sync_cli_compat.py -k
  'owned_surface_selective_lane_for_governance_memory_slice or
  refreshes_registry_for_spec_only_selective_slice or
  refreshes_atlas_for_catalog_only_selective_slice or
  requires_sync_treats_casebook_bug_markdown_as_sync_relevant or
  build_sync_execution_plan_runs_final_registry_reconcile_after_bundle_mirror'`
  plus `PYTHONPATH=src python3 -m pytest -q tests/unit/install/test_agents.py
  tests/integration/install/test_bundle.py::test_bundle_root_contains_installed_agents_entrypoint
  tests/integration/install/test_manager.py -k 'install_bundle_bootstraps_customer_owned_tree_without_copying_product_bundle or upgrade_install_resyncs_consumer_guidance_and_skills'`
  passed on 2026-04-14. A second 2026-04-14 proof wave also passed with
  `PYTHONPATH=src .venv/bin/python -m pytest -q
  tests/unit/runtime/test_sync_cli_compat.py
  tests/unit/runtime/test_owned_surface_refresh_authoring.py
  tests/unit/runtime/test_odylith_memory_backend.py
  tests/unit/runtime/test_generated_refresh_guard.py
  tests/unit/runtime/test_derivation_provenance.py` (`68 passed`), while
  source-local timings came back at `radar refresh: 1.78s` wall,
  `registry refresh: 5.03s` wall, `casebook refresh: 1.67s` warm wall,
  `atlas refresh --atlas-sync: 0.35s` wall, and
  `sync --impact-mode selective <casebook,plan,spec,atlas>`: `6.9s`
  sync-reported / `7.33s` wall with the local LanceDB/Tantivy substrate still
  reporting `ready: true`.

- Prevention: Every routine authoring command that mutates owned source truth
  must refresh its owned surface before returning success, and every narrow
  selective-sync lane must make its visible surface update explicit instead of
  relying on operators to remember a second `dashboard refresh` hop. Shared
  guidance, install assets, and host-specific helper surfaces must advertise
  the same owned-surface quick-refresh commands across Codex, Claude, dev,
  dogfood, and consumer lanes. When the caller already names the exact changed
  source-truth files, the quick lane must trust that slice and skip unrelated
  planner, git-scan, and broad-preflight work unless the touched owned surface
  itself still needs targeted validation.

- Detected By: `odylith show`

- Failure Signature: `odylith backlog create`, `odylith component register`,
  `odylith atlas scaffold`, or `odylith compass log` succeeded but the
  corresponding Radar/Registry/Atlas/Compass surface stayed stale until a
  second manual refresh, while direct `odylith sync --impact-mode selective`
  over Registry specs or Atlas catalog truth completed without making the owned
  surface visibly current.

- Trigger Path: `odylith backlog create`, `odylith component register`,
  `odylith atlas scaffold`, `odylith compass log`, and `odylith sync
  --repo-root . --impact-mode selective <CURRENT_SPEC.md|diagrams.v1.json|...>`.

- Ownership: owned-surface refresh contract, selective sync planner, and shared
  projection/memory refresh runtime.

- Timeline: Captured 2026-04-14 through `odylith bug capture`.

- Blast Radius: Radar, Registry, Atlas, Compass, Casebook consistency
  expectations, quick-update operator UX, and trust that shared projection
  caches plus local LanceDB/Tantivy stay fresh when source truth mutates.

- SLO/SLA Impact: Medium operator-latency and confidence impact on common
  maintenance paths.

- Data Risk: Low. The underlying source truth writes landed, but visible surface
  and derived-memory freshness could lag until another command refreshed them.

- Security/Compliance: No direct security impact; the fix reduces pressure to
  run broader write-heavy syncs for routine visibility updates.

- Invariant Violated: Mutating owned governance truth must refresh the smallest
  directly owned visible surface before reporting success, and narrow selective
  sync must keep projection/memory substrates fresh without widening into the
  full render-heavy DAG.
