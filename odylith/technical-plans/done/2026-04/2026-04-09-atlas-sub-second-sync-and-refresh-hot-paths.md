Status: Done

Created: 2026-04-09

Updated: 2026-04-09

Backlog: B-080

Goal: Cut Atlas sync and refresh below one second on the real command paths
without weakening freshness gates, dropping delivery inputs, or faking the
measurement with in-process-only proof.

Assumptions:
- Atlas correctness still depends on delivery-intelligence, Registry, Mermaid
  source truth, and the stale-diagram gate.
- The important budget is end-to-end command latency, not just helper runtime.
- Atlas hot paths are common enough that CLI fan-in and nested subprocesses
  count as product debt, not incidental noise.

Constraints:
- Do not relax `fail-on-stale` or remove watched-path coverage to hit the
  latency target.
- Keep `odylith.cli` externally monkeypatchable so the existing tests and
  helper callers remain stable.
- Preserve the Atlas render contract across `auto`, `daemon`, and
  `standalone`.

Reversibility: The guards, wrappers, direct artifact readers, and lazy-load
CLI routing are additive. Any one optimization can be backed out without
changing Atlas source truth or the freshness contract itself.

Boundary Conditions:
- Scope includes Atlas render, Atlas auto-update, delivery-intelligence
  refresh, dashboard Atlas refresh routing, CLI startup fan-in, and focused
  runtime or CLI proof.
- Scope excludes changing Atlas stale-diagram policy, redesigning Atlas UI, or
  doing a broad stale-diagram cleanup wave.

Related Bugs:
- `CB-097` Atlas watch freshness can mark diagrams stale on mtime-only churn.
- `CB-098` Atlas auto-update plan can claim render work for review-only sync.
- `CB-099` Atlas persistent Mermaid worker bootstrap can fail real render jobs.
- `CB-100` Atlas real render lane still misses sub-second bar after review-only fast path.

## Learnings
- [x] Atlas was slower because of command-shell fan-in and broad read paths
      more than because of Mermaid rendering itself.
- [x] Direct delivery and Registry artifact reads are much cheaper than
      projection-store fan-in for the Atlas render use case.
- [x] Lazy compatibility proxies let `odylith.cli` stay monkeypatch-stable
      while still removing eager imports from Atlas command startup.
- [x] Once the broad parser and import costs were gone, repeated path
      normalization inside Atlas render became the next real bottleneck; a
      memoized repo-path resolver was enough to cut that without obscuring the
      render code.
- [x] Replacing watched-path mtime comparisons with stored content fingerprints
      eliminated most false stale debt without weakening the stale signal.
- [x] Review-only Atlas sync needs its own explicit classification and plan
      surface; otherwise the command looks slower and heavier than it really
      is.
- [x] The remaining honest Atlas latency gap is cold real Mermaid render, not
      review-only refresh, and it needs to be tracked separately.

## Must-Ship
- [x] Add generated refresh guards for delivery-intelligence and Atlas render.
- [x] Route Atlas dashboard refresh through lightweight wrappers that skip
      current rebuilds before importing the heavier engines.
- [x] Stop Atlas dashboard refresh from rebuilding delivery-intelligence when
      Atlas already has the current artifact it needs.
- [x] Replace Atlas render's broader delivery and Registry load path with
      direct artifact reads.
- [x] Make `odylith.cli` lazy-load unrelated command families while preserving
      the historical module-level compatibility surface.
- [x] Remove the nested Python subprocess from Atlas auto-update for
      non-standalone catalog rerenders.
- [x] Replace repeated Atlas render `Path.resolve()` and repo-relative href
      churn with a reusable memoized repo-path resolver.
- [x] Replace watched-path freshness mtimes with content fingerprints and
      render-semantic Mermaid source fingerprints.
- [x] Make Atlas auto-update classify review-only versus render-needed
      diagrams before printing the plan or picking the render lane.
- [x] Repair the persistent Mermaid worker bootstrap so genuine render jobs
      work again on the optimized path.

## Should-Ship
- [x] Keep focused regressions for repeated identical sync, review-only sync,
      and Atlas CLI dispatch compatibility.
- [x] Measure both cold guarded and warm Atlas auto-update runs, not just the
      warm path.
- [x] Measure the render body directly after forced invalidation so the command
      shell and the render body are both proven under budget.

## Defer
- [x] Broad stale-diagram cleanup across the current Atlas catalog.
- [x] A separate inspect-only refresh mode that bypasses failure semantics
      while still reporting freshness debt.
- [x] Cold real Mermaid render latency beyond the review-only Atlas path.

## Success Criteria
- [x] `atlas auto-update` cold guarded runs stay below `1s`.
- [x] warmed `atlas auto-update` runs stay well below `0.5s`.
- [x] forced in-process Atlas render stays below `1s`.
- [x] Atlas CLI startup no longer drags in unrelated install, governance,
      benchmark, orchestration, and surface modules before Atlas work starts.

## Non-Goals
- [x] Removing features to win the benchmark.
- [x] Reclassifying stale Atlas diagrams as fresh.
- [x] Replacing Atlas command proof with synthetic microbenchmarks only.

## Open Questions
- [x] Whether Atlas should later expose a non-failing inspect-only refresh mode
      for cases where operators want timing and freshness diagnostics without a
      hard failure exit.

## Impacted Areas
- [x] [2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md](/Users/freedom/code/odylith/odylith/radar/source/ideas/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md)
- [x] [2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md](/Users/freedom/code/odylith/odylith/technical-plans/done/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md)
- [x] [diagram_freshness.py](/Users/freedom/code/odylith/src/odylith/runtime/common/diagram_freshness.py)
- [x] [generated_refresh_guard.py](/Users/freedom/code/odylith/src/odylith/runtime/common/generated_refresh_guard.py)
- [x] [repo_path_resolver.py](/Users/freedom/code/odylith/src/odylith/runtime/common/repo_path_resolver.py)
- [x] [delivery_intelligence_engine.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/delivery_intelligence_engine.py)
- [x] [delivery_intelligence_refresh.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/delivery_intelligence_refresh.py)
- [x] [sync_workstream_artifacts.py](/Users/freedom/code/odylith/src/odylith/runtime/governance/sync_workstream_artifacts.py)
- [x] [mermaid_cli_worker.mjs](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs)
- [x] [render_mermaid_catalog.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog.py)
- [x] [render_mermaid_catalog_refresh.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/render_mermaid_catalog_refresh.py)
- [x] [auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py)
- [x] [cli.py](/Users/freedom/code/odylith/src/odylith/cli.py)
- [x] [test_cli.py](/Users/freedom/code/odylith/tests/unit/test_cli.py)
- [x] [test_generated_refresh_guard.py](/Users/freedom/code/odylith/tests/unit/runtime/test_generated_refresh_guard.py)
- [x] [test_delivery_intelligence_engine.py](/Users/freedom/code/odylith/tests/unit/runtime/test_delivery_intelligence_engine.py)
- [x] [test_diagram_freshness.py](/Users/freedom/code/odylith/tests/unit/runtime/test_diagram_freshness.py)
- [x] [test_render_mermaid_catalog.py](/Users/freedom/code/odylith/tests/unit/runtime/test_render_mermaid_catalog.py)
- [x] [test_repo_path_resolver.py](/Users/freedom/code/odylith/tests/unit/runtime/test_repo_path_resolver.py)
- [x] [test_auto_update_mermaid_diagrams.py](/Users/freedom/code/odylith/tests/unit/runtime/test_auto_update_mermaid_diagrams.py)
- [x] [test_sync_cli_compat.py](/Users/freedom/code/odylith/tests/unit/runtime/test_sync_cli_compat.py)

## Validation
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py -k "cli or render_mermaid_catalog or atlas_auto_update or dashboard_refresh"`
      (`134 passed, 7 deselected`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_repo_path_resolver.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/test_cli.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py`
      (`145 passed`)
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_generated_refresh_guard.py tests/unit/runtime/test_delivery_intelligence_engine.py`
- [x] `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_render_mermaid_catalog.py`
      (`35 passed`)
- [x] `PYTHONPATH=src python3 -m odylith.cli atlas auto-update --repo-root . --changed-path src/odylith/install/release_assets.py`
      (cold guarded `0.226s-0.250s`; still well below `0.5s` on warm runs)
- [x] `PYTHONPATH=src python3 -m odylith.cli dashboard refresh --repo-root . --surfaces atlas`
      (command latency `0.380s-0.429s`; current repo still exits on the stale
      gate because `21` diagrams are stale)
- [x] `PYTHONPATH=src python3 - <<'PY' ... cProfile(Profile).runcall(cli.main, ...) ... PY`
      (profiled in-process command path `0.325s`; `render_mermaid_catalog._load_catalog(...)` down to `~0.080s`)
- [x] `PYTHONPATH=src python3 - <<'PY' ... _MermaidWorkerSession(...).render_one(...) ... PY`
      (repaired cold real render worker path writes valid SVG and PNG, but still measures `~2.38s`)
- [x] `git diff --check`

## Current Outcome
- [x] Atlas sync now stays below one second even on cold guarded command runs.
- [x] Atlas sync now stays closer to one quarter second than one second on the
      measured cold guarded command path.
- [x] Atlas warm sync is comfortably sub-half-second.
- [x] Review-only stale Atlas refresh now avoids fake Mermaid asset work and
      reports that honestly in the command plan.
- [x] Atlas render itself no longer needs a broad delivery or Registry load
      path to stay correct.
- [x] `odylith.cli` no longer imports unrelated command families on the Atlas
      path, but the old monkeypatch surface still exists through lazy
      compatibility proxies.
- [x] Atlas render no longer spends a meaningful share of its budget on
      repeated repo-path normalization.
- [x] Atlas dashboard refresh itself is fast again; the remaining open
      performance debt is the cold real Mermaid render lane tracked by
      `CB-100`, not review-only freshness sync.
