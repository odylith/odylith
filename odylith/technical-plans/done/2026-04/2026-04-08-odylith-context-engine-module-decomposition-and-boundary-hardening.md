Status: Done

Created: 2026-04-08

Updated: 2026-04-09

Backlog: B-067

Goal: Split the oversized Context Engine helper modules into smaller owned
modules with direct import rewiring, no compatibility facades, and broad
regression proof across packets, benchmarks, and surfaces.

Assumptions:
- The Context Engine's current public behavior is mostly correct; the problem
  is structural coupling and red-zone file growth, not an immediate contract
  redesign.
- Direct imports into smaller modules are safer long term than preserving one
  giant compatibility layer.
- Existing regression suites already cover enough packet and surface behavior
  to prove a hard refactor if they are rerun broadly enough.

Constraints:
- Do not leave compatibility shims, alias wrappers, or deprecated module
  facades behind.
- Keep the refactor behavior-preserving at the public CLI and packet-contract
  level.
- Update the Context Engine component spec and any touched governance truth in
  the same change.

Reversibility: The new module layout is reversible by merging modules back
together, but this plan intentionally treats the split as a hard boundary
change rather than a soft migration layer.

Boundary Conditions:
- Scope includes direct module splits for projection-surface resolution,
  session-packet building, and hot-path packet compaction, plus direct import
  rewiring and regression coverage.
- Scope excludes new collaboration-memory features, packet schema changes, and
  broader public CLI redesign.

Related Bugs:
- no related bug found

## Learnings
- [x] The recent proof-state and release-planning work proved the Context
      Engine can support more product surface, but also showed that the same
      central files are absorbing too many unrelated responsibilities.
- [x] A real refactor needs direct rewiring, not one more layer of wrapper
      modules.

## Must-Ship
- [x] Split `odylith_context_engine_projection_surface_runtime.py` into
      smaller focused modules and update query/runtime imports directly.
- [x] Split `odylith_context_engine_session_packet_runtime.py` into smaller
      packet-summary and packet-builder modules with direct caller rewiring.
- [x] Split `odylith_context_engine_hot_path_packet_runtime.py` into smaller
      focused compaction modules and wire `odylith_context_engine_hot_path_runtime.py`
      directly to them.
- [x] Remove the superseded oversized modules or reduce them to normal
      coordinators rather than leaving compatibility facades behind.
- [x] Update the Context Engine component spec to describe the new boundaries.

## Should-Ship
- [x] Reduce the touched module sizes below the repo red-zone threshold.
- [x] Add direct unit coverage for the new module seams instead of relying
      only on inherited integration coverage.

## Defer
- [x] Deeper `odylith_context_engine_store.py` decomposition beyond the direct
      caller rewiring needed for this wave.
- [x] Collaboration-memory feature work from `B-002`.

## Success Criteria
- [x] The targeted oversized Context Engine helper modules are split into
      smaller owned modules with no compatibility shims.
- [x] Context Engine packet and query behavior still passes focused and broad
      regression suites.
- [x] The Context Engine spec and touched governance artifacts reflect the new
      module topology accurately.

## Non-Goals
- [x] Public CLI changes.
- [x] New packet fields or behavioral expansions unrelated to the refactor.
- [x] A repo-wide large-file rewrite outside this Context Engine slice.

## Open Questions
- [x] The next red-zone wave can choose between `odylith_context_engine_store.py`
      and collaboration-memory follow-ons as a separate scoped workstream.

## Impacted Areas
- [x] [2026-04-08-odylith-context-engine-module-decomposition-and-boundary-hardening.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-08-odylith-context-engine-module-decomposition-and-boundary-hardening.md)
- [x] [2026-04-08-odylith-context-engine-module-decomposition-and-boundary-hardening.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-08-odylith-context-engine-module-decomposition-and-boundary-hardening.md)
- [x] [CURRENT_SPEC.md](/Users/freedom/code/odylith/odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md)
- [x] [odylith_context_engine_projection_query_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_projection_query_runtime.py)
- [x] [odylith_context_engine_hot_path_runtime.py](/Users/freedom/code/odylith/src/odylith/runtime/context_engine/odylith_context_engine_hot_path_runtime.py)
- [x] Context Engine projection, session-packet, and hot-path packet runtime modules under [/Users/freedom/code/odylith/src/odylith/runtime/context_engine](/Users/freedom/code/odylith/src/odylith/runtime/context_engine)
- [x] Context Engine, benchmark, and surface regression tests under [/Users/freedom/code/odylith/tests](/Users/freedom/code/odylith/tests)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_context_engine_split_hardening.py tests/unit/runtime/test_context_engine_release_resolution.py tests/unit/runtime/test_context_engine_topology_contract.py tests/unit/runtime/test_context_engine_proof_packet_runtime.py tests/unit/runtime/test_tooling_context_packet_builder.py tests/unit/runtime/test_odylith_context_engine_store.py tests/unit/runtime/test_context_grounding_hardening.py tests/unit/runtime/test_odylith_benchmark_context_engine.py tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_render_compass_dashboard.py tests/unit/runtime/test_compass_standup_brief_batch.py tests/unit/runtime/test_compass_dashboard_shell.py tests/unit/runtime/test_render_tooling_dashboard.py`
      (`298 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/integration/runtime/test_surface_browser_smoke.py tests/integration/runtime/test_surface_browser_deep.py tests/integration/runtime/test_surface_browser_filter_audit.py tests/integration/runtime/test_surface_browser_layout_audit.py tests/integration/runtime/test_surface_browser_ux_audit.py tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py`
      (`76 passed, 1 skipped`)
- [x] `PYTHONPATH=src python3 -m odylith.cli sync --repo-root . --check-only --runtime-mode standalone`
      (passed)
- [x] `git diff --check`
      (passed)

## Current Outcome
- [x] `B-067` is closed for `v0.1.11`.
- [x] The red-zone Context Engine packet and projection monoliths were split
      into smaller owned modules with direct import rewiring and no
      compatibility shims.
- [x] Compass, Casebook, the shell, and the surrounding generated surfaces now
      reflect the refactor cleanly, including release-target layout, release
      labeling, scoped-brief selection, and synchronized case counts.
- [x] The final proof held across focused Context Engine regressions, full
      runtime browser integration, governed artifact freshness, and the
      fail-closed standalone sync gate.
