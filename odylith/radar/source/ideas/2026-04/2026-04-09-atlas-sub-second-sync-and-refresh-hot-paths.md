---
status: finished
idea_id: B-080
title: Atlas Sub-Second Sync and Refresh Hot Paths
date: 2026-04-09
priority: P0
commercial_value: 4
product_impact: 5
market_value: 3
impacted_parts: Atlas auto-update command path, Mermaid catalog render path, dashboard refresh routing, delivery-intelligence refresh helpers, CLI startup fan-in, generated refresh guards, and focused Atlas runtime proof
sizing: M
complexity: High
ordering_score: 100
ordering_rationale: Atlas had crossed from "a little slow" into operator-hostile. The real hot paths were paying for unrelated CLI imports, redundant refresh work, and broad read-model loads even when Atlas truth was already current. Until Atlas sync and refresh stayed sub-second on the actual command line, the Atlas surface itself kept slowing down the review loop it was meant to accelerate.
confidence: high
founder_override: no
promoted_to_plan: odylith/technical-plans/done/2026-04/2026-04-09-atlas-sub-second-sync-and-refresh-hot-paths.md
execution_model: standard
workstream_type: child
workstream_parent: B-025
workstream_children:
workstream_depends_on: B-023,B-025,B-059,B-067
workstream_blocks:
related_diagram_ids: D-002,D-020,D-025
workstream_reopens:
workstream_reopened_by: B-081
workstream_split_from:
workstream_split_into:
workstream_merged_into:
workstream_merged_from:
supersedes:
superseded_by:
---

## Closeout Note
This workstream closed on 2026-04-09 after Atlas sync and refresh moved back
under the sub-second budget on the real command paths without weakening the
freshness contract, and a same-day deeper wave then replaced watched-path mtime
heuristics with content fingerprints, taught Atlas auto-update to classify
review-only versus render-needed work before printing its plan, and repaired
the persistent Mermaid worker bootstrap for genuine render jobs. `atlas
auto-update` still runs in `0.226s-0.250s` on repeated cold guarded runs, the
Atlas dashboard refresh command dispatch itself still returns in
`0.380s-0.429s`, and the profiled in-process Atlas render body still measures
`0.325s` with `_load_catalog(...)` down to about `0.080s` after cached
repo-path resolution and cheaper backlog metadata reuse.

The remaining honest gap is the first genuine Mermaid render lane, not review
freshness correctness. The repaired persistent worker still measures around
`2.38s` for a cold real render, so the remaining cold-start render budget is
tracked separately in `CB-100` and follow-on workstream `B-081`.

## Problem
Atlas sync and refresh had accumulated too much incidental work. The command
paths were importing install, governance, benchmark, orchestration, and
surface modules that Atlas did not need; Atlas refresh still rebuilt or loaded
broader delivery context than the renderer actually consumed; and the
auto-update path paid an extra interpreter hop just to rerender Atlas after
touching review markers.

That made the surface feel sluggish in the exact operator loop where it should
be cheap: update one watched path, refresh the diagram truth, and move on.

## Customer
- Primary: Odylith operators and maintainers who use Atlas as a live topology
  surface while iterating on runtime and governance code.
- Secondary: maintainers who need Atlas freshness checks to stay strict
  without turning every no-op or review-marker sync into a multi-second wait.

## Opportunity
If Atlas keeps its correctness contract but stops paying for unrelated runtime
fan-in, then the product gets a much better operator feel without cheating on
freshness. The right win is not "hide work"; it is "stop doing work that Atlas
does not actually need."

## Proposed Solution
- add metadata-based generated refresh guards for delivery-intelligence and
  Atlas render hot paths
- route Atlas render and delivery refresh through lightweight wrappers that
  skip current rebuilds before importing the heavier engines
- stop Atlas dashboard refresh from eagerly rebuilding delivery intelligence
  when Atlas already has the current delivery artifact it needs
- load delivery and Registry inputs for Atlas render directly from their
  canonical artifacts instead of the broader projection-store path
- keep `odylith.cli` monkeypatch-compatible while moving unrelated command
  families behind lazy module proxies and targeted fast paths
- let Atlas auto-update rerender the catalog in-process for `auto` and
  `daemon` mode so the sync path no longer shells out to a second Python
  process
- use cheap local repo-shape detection plus memoized repo-path resolution so
  Atlas render stops paying repeated `Path.resolve()` and install-manager
  import costs on the cold path
- persist watched-path content fingerprints and render-semantic Mermaid source
  fingerprints so Atlas freshness stays strict without overreacting to mtime
  churn
- classify review-only versus render-needed diagrams before Atlas prints its
  mutation plan or chooses the render lane
- keep the persistent Mermaid worker correct by explicitly bootstrapping the
  browser globals it reuses

## Scope
- `src/odylith/runtime/common/diagram_freshness.py`
- `src/odylith/runtime/common/generated_refresh_guard.py`
- `src/odylith/runtime/common/repo_path_resolver.py`
- `src/odylith/runtime/governance/delivery_intelligence_engine.py`
- `src/odylith/runtime/governance/delivery_intelligence_refresh.py`
- `src/odylith/runtime/governance/sync_workstream_artifacts.py`
- `src/odylith/runtime/surfaces/assets/mermaid_cli_worker.mjs`
- `src/odylith/runtime/surfaces/render_mermaid_catalog.py`
- `src/odylith/runtime/surfaces/render_mermaid_catalog_refresh.py`
- `src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py`
- `src/odylith/cli.py`
- focused Atlas, refresh-guard, sync-compat, and CLI tests

## Non-Goals
- weakening `fail-on-stale` or lowering Atlas freshness requirements
- removing delivery-intelligence or Registry inputs from Atlas render
- hiding slow paths behind warm-only measurements or in-process-only claims
- redesigning Atlas visuals or changing diagram semantics

## Risks
- lazy CLI loading could regress monkeypatch-based tests or external callers
  if the old module-level surface disappears
- guard caches could skip real rebuilds if watched-path coverage is incomplete
- Atlas render could drift if the direct artifact readers diverge from the
  canonical delivery or Registry schemas
- the real Mermaid render lane could still miss the budget even after
  review-only sync becomes cheap, because browser startup is a different
  bottleneck

## Dependencies
- `B-023` established Atlas browser and query-state hardening; this slice keeps
  that surface fast enough to use
- `B-025` already owns cross-surface freshness and runtime refresh discipline
- `B-059` refreshed Atlas runtime topology and made the render path more
  central to everyday operator work
- `B-067` decomposed the Context Engine and made direct artifact reads a safer
  optimization target

## Success Metrics
- `atlas auto-update` stays below `1s` on cold guarded runs
- warmed `atlas auto-update` stays well below `0.5s`
- Atlas render body stays below `1s` after forced invalidation
- CLI startup no longer dominates Atlas command latency
- refresh correctness remains unchanged: current work skips, stale work still
  rebuilds or fails closed
- review-only stale work avoids fake SVG/PNG churn while real Mermaid source
  changes still rebuild

## Validation
- `PYTHONPATH=src python3 -m pytest -q tests/unit/test_cli.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py -k "cli or render_mermaid_catalog or atlas_auto_update or dashboard_refresh"`
  - `134 passed, 7 deselected`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_repo_path_resolver.py tests/unit/runtime/test_render_mermaid_catalog.py tests/unit/test_cli.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_sync_cli_compat.py`
  - `145 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_generated_refresh_guard.py tests/unit/runtime/test_delivery_intelligence_engine.py`
- `PYTHONPATH=src python3 -m pytest -q tests/unit/runtime/test_diagram_freshness.py tests/unit/runtime/test_auto_update_mermaid_diagrams.py tests/unit/runtime/test_render_mermaid_catalog.py`
  - `35 passed`
- `PYTHONPATH=src python3 -m odylith.cli atlas auto-update --repo-root . --changed-path src/odylith/install/release_assets.py`
  - cold guarded: `0.226s-0.250s`
  - warm: still comfortably below `0.5s`
- `PYTHONPATH=src python3 -m odylith.cli dashboard refresh --repo-root . --surfaces atlas`
  - command latency: `0.380s-0.429s`
  - current repo result: fails fast on the existing stale-diagram gate
- `PYTHONPATH=src python3 - <<'PY' ... cProfile(Profile).runcall(cli.main, ...) ... PY`
  - profiled in-process command path: `0.325s`
  - `render_mermaid_catalog._load_catalog(...)`: `~0.080s`
- `PYTHONPATH=src python3 - <<'PY' ... _MermaidWorkerSession(...).render_one(...) ... PY`
  - repaired cold real render worker path: `~2.38s`

## Rollout
1. Cut redundant Atlas work before touching the CLI shell.
2. Make the Atlas render body cheap enough that command-shell overhead becomes
   the next real bottleneck.
3. Lazy-load the CLI without breaking the historical monkeypatch surface.
4. Remove the nested Python subprocess from Atlas auto-update.
5. Prove the actual command paths, not just direct helper calls.

## Why Now
Atlas is a topology surface. If it takes multiple seconds to reflect the
change you just made, it stops being a live tool and turns into a chore.

## Product View
The honest version of performance work is not to bypass validation. It is to
make the correct path cheap enough that operators stop feeling pressure to cut
around the product.

## Impacted Components
- `atlas`
- `delivery-intelligence`
- `dashboard`
- `odylith-context-engine`
- `registry`

## Interface Changes
- no user-facing Atlas feature removal
- additive refresh-guard metadata under the existing local cache tree
- additive watched-path and render-source fingerprints inside the existing
  Atlas diagram catalog entries
- faster Atlas CLI routing through lazy module loading and targeted fast paths
- honest review-only planning and render classification without weakening the
  stale signal

## Migration/Compatibility
- keep the previous `odylith.cli` module-level names available through lazy
  compatibility proxies so existing tests and monkeypatch callers still work
- keep the Atlas stale gate strict; the command can become fast without
  becoming permissive
- keep review-only sync honest about what it changed; Atlas should not claim
  Mermaid regeneration when the assets were already current

## Test Strategy
- direct guard coverage for current-output skip behavior
- focused CLI coverage for lazy dispatch and compatibility proxies
- Atlas auto-update coverage for repeated identical syncs and review-only syncs
- review-only plan coverage so Atlas does not overstate render work
- render coverage for direct delivery/Registry artifact reads

## Open Questions
- whether Atlas should expose a dedicated non-failing inspect-only refresh mode
  separate from the existing stale gate for diagnostic workflows
