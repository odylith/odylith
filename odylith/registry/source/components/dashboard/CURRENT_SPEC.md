# Dashboard
Last updated: 2026-04-16


Last updated (UTC): 2026-04-16

## Purpose
Dashboard is the shell host for Odylith. It provides the top-level tabbed,
deep-linkable parent surface that composes Radar, Atlas, Compass, Registry, and
Casebook into one navigable product entrypoint without flattening each child
surface into the shell renderer.

## Scope And Non-Goals
### Dashboard owns
- Shell-level routing and query-param deep links.
- The parent iframe composition model.
- Shared developer-note and cheatsheet drawers.
- Shared branding, favicon, manifest, and tab lockup behavior.
- Externalized shell asset bundling for the checked-in root surface.
- A hard product boundary that keeps internal telemetry, diagnostic spend
  evidence, recorder tapes, cockpit panels, charts, and status slabs out of the
  dashboard DOM.

### Dashboard does not own
- The underlying business logic of Radar, Atlas, Compass, Registry, or
  Casebook.
- Reinterpreting child-surface data contracts in the shell.
- Acting as a source of truth for governance state. It reads derived payloads.
- Rendering internal telemetry or diagnostic records as product chrome.

## Developer Mental Model
- The shell is intentionally thin.
- Child surfaces render their own HTML and JS bundles.
- The shell embeds those pages, routes between them, and adds shared
  navigation, brand framing, and deep-link translation.
- Shell link semantics are centralized so proof routes, scope routes, and tab
  links stay consistent across surfaces.
- Shared interactive `B-###` workstream buttons are centralized too: the
  compact non-Atlas workstream-button contract lives in
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`, and child
  surfaces must not locally re-size or re-pad those controls.
- Shared deep-link buttons are centralized there too: `Registry`, `Spec`,
  proof-reference, and `D-###` diagram buttons must consume the shared
  deep-link chip contract from
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py` instead of
  shipping surface-local button CSS forks.
- The same source file owns the shared governance KPI/stat-card contract.
  Compass, Radar, Registry, and Casebook top-line summary tiles must consume
  the shared KPI grid/card/label-value helpers instead of shipping local
  summary-card CSS forks.
- Shared interactive `B-###` workstream buttons also share one destination:
  Dashboard routes them to Radar's canonical workstream view. Child surfaces
  may keep their own local scope state, but they must not repurpose those
  shared buttons to open surface-local scoped views.
- The shell cheatsheet drawer must teach release planning and program/wave
  planning as distinct operator flows. Release planning answers "what release
  should this workstream ship in?", while program/wave planning answers "how
  should this umbrella execute across W1/W2/W3?" The same workstream may
  participate in both, so cheatsheet examples must keep the distinction
  explicit instead of blurring them into one planning lane.
- Compass `Release Targets` layout is not a free shell-level styling choice.
  Shared shell CSS must not reintroduce side-by-side or auto-fit multi-column
  release boards once the operator has chosen the stacked release format,
  unless that layout change is explicitly authorized.
- When a child surface owns source-generated shell assets, keep one canonical
  generator or loader path and require exact live-versus-bundle mirror
  equality. Operator-owned layout and compact workstream-button contracts need
  browser proof, not just static selector checks.
- Shared KPI/stat-card contracts need the same proof posture: browser audits
  must check computed card, label, and value styling plus release-card
  labeling across the affected governance surfaces.
- The shell must not render internal telemetry UI. Do not add a shell telemetry
  drawer, status presenter, recorder tape, cockpit grid, chart canvas, ECharts
  dependency, or `Telemetry Snapshot`-style status slab. Internal telemetry may
  remain in runtime artifacts and explicit diagnostics, but the top-level
  dashboard shell must not load, embed, or render internal delivery,
  evaluation, optimization, or memory snapshots. Browser tests must prove
  absence from both product DOM and the shell payload.

## Runtime Contract
### Owning modules
- `src/odylith/runtime/surfaces/render_tooling_dashboard.py`
  Root renderer for `odylith/index.html`.
- `src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py`
  Template context assembly for the thin shell, developer notes, and cheatsheet.
- `src/odylith/runtime/surfaces/dashboard_shell_links.py`
  Stable query and proof-link helpers.
- `src/odylith/runtime/surfaces/dashboard_template_runtime.py`
  Shared template rendering helpers.
- `src/odylith/runtime/surfaces/tooling_dashboard_frontend_contract.py`
  Source-owned tooling-shell frontend loader plus frozen header contract guard.
- `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`
  Shared layout, typography, chip, panel, and dashboard UI CSS primitives.
- `src/odylith/runtime/surfaces/brand_assets.py`
  Brand head injection, favicon, manifest, and lockup/icon asset plumbing.
- `src/odylith/runtime/surfaces/templates/tooling_dashboard/`
  Shell HTML/CSS/JS template assets.

### Source-owned shell inputs
- `odylith/runtime/source/tooling_shell.v1.json`
  Shell-maintainer notes and shell-level source metadata.
- Child governed surface outputs:
  `odylith/radar/radar.html`, `odylith/atlas/atlas.html`,
  `odylith/compass/compass.html`, `odylith/registry/registry.html`, and
  `odylith/casebook/casebook.html`

### Generated artifacts
- `odylith/index.html`
- `odylith/tooling-payload.v1.js`
- `odylith/tooling-app.v1.js`

## Shell Architecture
### Composition model
The shell is a parent document that embeds each governed surface in an iframe.
This is deliberate:
- child surfaces keep their own rendering/runtime contracts
- shell iteration does not require inlining every surface into one monolith
- deep links can target the shell while preserving surface-specific state

### Runtime payload
`render_tooling_dashboard.py` assembles shell payload from:
- `load_delivery_surface_payload(surface="shell", include_shell_snapshots=True)`
- relative hrefs for each child surface
- shell-source JSON from `tooling_shell.v1.json`
- self-host posture derived from Odylith install status
- brand payload from `brand_assets.tooling_shell_brand_payload(...)`

The presenter then derives maintainer-note and cheatsheet shell context before
externalizing the bundle. It must not derive or render shell telemetry payloads.

If the persisted Tribunal reasoning artifact is missing, shell refresh must
still build a deterministic `case_queue` from delivery scopes without waiting
on opportunistic provider-backed reasoning. Fast shell refresh is part of the
Dashboard contract, not a best-effort optimization.

### Dashboard refresh contract
`odylith dashboard refresh --repo-root .` is the shell-facing refresh entry
point. Its default surface set is `tooling_shell`, `radar`, and `compass`.
Dry-runs and real executions must print the included and excluded surfaces so
operators can see when Atlas, Registry, or Casebook were intentionally left
out. If Atlas is excluded while stale, the command must print the exact
follow-up Atlas refresh command instead of assuming the operator will discover
that gap from `--help`.

Shell-only refresh is wrapper-scoped, not a hidden child-surface rerender. If
`tooling_shell` runs without Compass, the operator contract must say that the
wrapper assets refreshed but Compass runtime truth did not. The shell must also
project current Compass freshness or failure posture when the Compass tab is
active so parent-surface success does not masquerade as a fresh child brief.
But if the Compass frame already carries the relevant stale or failed-refresh
warning, the shell must not restate the same warning above the iframe. The shell
also must not replace that dedupe rule with internal telemetry/status chrome.
Compass no longer carries a second deep-refresh contract. The shell may ask
Compass to refresh or wait for that refresh, but it must not invent or
advertise a minute-scale `full` rerender path the child surface no longer
supports.

### Live-refresh policy contract
Dashboard owns the shell-side policy that decides when a currently open tab may
reload against fresher local runtime state without mutating tracked Odylith
truth.

- `balanced`
  Consumer repos and detached `source-local` maintainer posture default here.
  Radar, Registry, Compass, and Casebook may auto-reload from the local runtime
  probe after a short idle debounce. Atlas stays explicit because `--atlas-sync`
  can mutate tracked diagram metadata.
- `proof_frozen`
  Pinned product-repo proof and benchmark posture must disable passive refresh
  entirely so browser proof, release validation, and benchmark measurements are
  not skewed by hidden background behavior.
- `full_dev`
  Explicit override for maintainer development. Uses the same read-only runtime
  probe with a faster cadence and may auto-reload Atlas only when refreshed
  outputs already exist. It still never runs background sync or provider-backed
  refresh.

Across all policies, the shell must keep three guardrails:
- no background `odylith sync`
- no background tracked-truth mutation under `odylith/`
- no background provider-backed Compass brief generation

The live-refresh policy is also change-driven, not timer-driven. When a shell
surface wants fresher Compass truth, it should reuse daemon change signals or
the same local watcher stack behind them before it falls back to coarse
polling. A tight heartbeat is not a normal Dashboard contract.

The same truth rule applies to explicit refresh: the shell may read Compass
runtime state and surface stale/failure posture, but it must not imply that
Compass rerendered unless the Compass child-runtime snapshot actually changed.

When the Compass child snapshot disagrees with the live traceability release
read model, Dashboard may disclose that the visible Compass snapshot is behind,
but it must use the same traceability-based drift contract as Compass itself.
The shell is not allowed to invent a second release-membership interpretation
from some other source of truth.

### Scope-budget policy
Dashboard and shared shell consumers must treat Delivery Intelligence
`scope_signal.budget_class` as the provider-neutral budget gate for expensive
reasoning or narration work:
- `none`
- `cache_only`
- `fast_simple`
- `escalated_reasoning`

Host adapters may map those classes to different concrete models or reasoning
settings for Codex, Claude, or future providers, but Dashboard must not encode
host-branded policy as the product contract. Cheap paths stay cheap because the
shared ladder says which scopes deserve compute, not because one host happened
to be configured locally.

These policies are posture switches over one shell/runtime implementation. They
must not fork Odylith into lane-specific codebases; source templates, generated
mirrors, and shipped bundle assets still converge back to the same checked-in
product code.

### Self-host posture payload
The shell payload now carries a `self_host` block with:
- `repo_role`
- `posture`
- `runtime_source`
- `release_eligible`
- `pinned_version`
- `active_version`

`runtime_source` must preserve the install/runtime layer distinction between a
verified staged runtime and a local wrapped runtime so the shell does not imply
that version alignment alone makes the product repo release-ready.

This is a readout surface, not the authority. The shell must display or forward
the derived self-host posture without recomputing it independently of the
install/runtime layer.

### Deep-link model
`dashboard_shell_links.py` owns the URL contract for:
- `tab`
- `workstream`
- `component`
- `diagram`
- `bug`
- `severity`
- `status`
- `view` for Radar-only workstream projections such as plan routes

It also normalizes scope-level routes from delivery-intelligence scopes and
renders proof-reference links consistently. This module is the single place to
change shell link semantics.

## Intent And UX Contract
The shell is meant to answer:
- which governed surface should the operator open first
- how to move between workstream, component, diagram, bug, and diagnosis views
- how to preserve one coherent Odylith brand/system frame while each child
  surface keeps its own runtime

The shell should not duplicate detailed business panels that already exist in
the child surfaces.

- When a child surface already explains its own stale-runtime or freshness
  posture in-frame, the shell must not add a second banner that repeats the
  same issue in wrapper language. The shell no longer has a general status
  presenter; wrapper-level notices must be explicit, narrow, and not telemetry
  or diagnostic cockpit UI.
- The bottom-right recovery dock is for global shell reopen actions such as the
  starter guide or upgrade spotlight. Do not add per-surface status reopen
  buttons there.
- Product dashboard DOM must not contain `system-status-shell`,
  `telemetry-stat-*`, `odylith-recorder-*`, `odylith-chart-*`, ECharts
  hydration, or legacy `odylith_drawer` rendering paths.
- Product shell payloads must not contain internal `memory_snapshot`,
  `optimization_snapshot`, or `evaluation_snapshot` data. Those artifacts stay
  outside the product shell unless a separately approved surface owns them.

### Shared Detail-Header Layout Contract
Dashboard owns the shared layout contract for child surfaces that use
Dashboard-owned header and card primitives.

- Detail headers must render their primary fact-card or KPI grid immediately
  after the headline block.
- The headline block means the identifier/kicker plus the title. Supporting
  prose, chips, action links, controls, and meters are secondary content and
  must render below the primary fact/KPI grid rather than between the title and
  that grid.
- Child surfaces must not reserve a desktop side gutter beside the primary
  fact/KPI grid for controls or links. If controls exist, they stack below the
  primary grid or move into another clearly secondary row.
- Shared changes to this ordering contract belong in
  `src/odylith/runtime/surfaces/dashboard_ui_primitives.py`, the governed
  child-surface renderers, and the cross-surface browser layout audits
  together.

The shell header is a frozen contract. The only version/status readout allowed
there is the existing compact `shell_version_label` string. Do not add
onboarding, release-note, maintainer-note, shell-polish, or other new UI
artifacts to that header.

## What To Change Together
- New child surface:
  add href generation, tab routing, brand/tab UI wiring, and shell-link support
  together.
- New deep-link parameter:
  update `dashboard_shell_links.py`, shell presenter defaults, and any proof
  route generators together.
- New shell source field:
  update `tooling_shell.v1.json`, presenter coercion, and template context at
  the same time.
- Brand changes:
  update `brand_assets.py` and template/presenter usage together rather than
  hardcoding assets in individual renderers.

## Failure And Recovery Posture
- The shell render fails if any child HTML surface is missing. That is
  intentional; the shell should not pretend the product is whole when one major
  governed surface failed to render.
- If the frozen header template or header CSS drifts, the shell render fails
  closed rather than shipping a silently mutated header to consumer installs.
- If shell-source JSON is missing or malformed, rendering degrades to safe
  defaults rather than failing.
- If Tribunal cache is absent, the shell must use deterministic Tribunal
  fallback rather than blocking on local provider timeouts.
- Deep-link logic is deterministic and local. It should never depend on live
  browser state to reconstruct core routes.

## Validation Playbook
### Shell
- `odylith sync --repo-root . --check-only`
- `PYTHONPATH=src python -m odylith.runtime.surfaces.render_tooling_dashboard --repo-root . --output odylith/index.html`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_brand_assets.py tests/unit/runtime/test_tooling_dashboard_frontend_contract.py`
- `PYTHONPATH=src python -m pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py::test_shell_never_renders_internal_telemetry_status_across_tabs`

## Requirements Trace
This section captures synchronized requirement and contract signals derived from component-linked timeline evidence.

<!-- registry-requirements:start -->
- **2026-03-23 · Decision:** Successor created: B-279 reopens B-278 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/dashboard/CURRENT_SPEC.md +3 more
- **2026-03-20 · Decision:** Successor created: B-258 reopens B-256 for active plan binding
  - Evidence: odylith/radar/source/INDEX.md, odylith/registry/source/components/dashboard/CURRENT_SPEC.md +1 more
- **2026-03-05 · Implementation:** Refreshed Radar, Atlas, Compass, Registry, Odylith, and the tooling shell; auto-synced the stale Mermaid diagrams; and fixed Odylith dashboard rendering so the workstream sync completes.
  - Evidence: odylith/compass/compass.html, odylith/index.html +2 more
- **2026-03-05 · Decision:** treat stale Atlas diagrams and Odylith render errors as fail-closed blockers before accepting a dashboard refresh.
  - Evidence: odylith/compass/compass.html, odylith/index.html +2 more
<!-- registry-requirements:end -->

## Feature History
- 2026-03-26: Bound the shell host to Odylith's own product-governance records so the public repo can render and audit its own surface boundary. (Plan: [B-001](odylith/radar/radar.html?view=plan&workstream=B-001))
- 2026-03-27: Added self-host posture payload fields so the shell can expose product-repo dogfood and release posture without inventing a second status model. (Plan: [B-004](odylith/radar/radar.html?view=plan&workstream=B-004))
- 2026-04-07: Clarified the shell freshness contract so Compass owns its normal stale-runtime disclosure in-frame, the shell reserves status cards for failure-only or cross-surface posture, and the recovery dock no longer carries per-surface `Show status` reopen buttons. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-08: Split compact `B-###` workstream buttons out of the broader identifier styling contract so Radar, Compass, and execution-wave stacks keep one centralized button size instead of drifting with unrelated identifier tweaks. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Removed the stale Compass release-board override from shared shell CSS and codified that shared Dashboard styling cannot change Compass release-target layout without explicit operator authorization. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Hardened shell mirror discipline by requiring one canonical source path, exact live-versus-bundle equality for mirrored surface artifacts, and browser proof for operator-owned workstream-button and release-layout contracts. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-080`)
- 2026-04-09: Collapsed Compass and Registry KPI/stat-card forks into the shared Dashboard KPI helpers and required browser proof for computed top-line card styling plus labeled current-release values across governance surfaces. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-085`)
- 2026-03-31: Froze the dashboard header contract and made shell render fail closed if the source-owned header template or header CSS drifts. (Plan: [B-027](odylith/radar/radar.html?view=plan&workstream=B-027))
- 2026-04-01: Restored the compact runtime/version string inside the frozen header contract so pinned and detached maintainer lanes stay visibly distinguishable. (Plan: [B-027](odylith/radar/radar.html?view=plan&workstream=B-027))
- 2026-04-02: Added balanced, proof-frozen, and full-dev live-refresh policies so read-only runtime-backed tabs can stay current without background sync, provider-credit spend, or benchmark skew. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Removed the old Compass `full` refresh idea from the shell contract too. Dashboard now treats Compass refresh as one bounded child-surface request and never advertises a second deep-refresh mode above the iframe. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-086`)
- 2026-04-08: Fixed the shell runtime-status bootstrap so Compass stale/failure disclosure survives first load and later runtime probes instead of being cleared by a probe payload that lacks shell-facing status records. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Reinstated shell-versus-child warning dedupe for Compass failures so the wrapper stays quiet when the Compass frame already explains the failed refresh. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
- 2026-04-09: Added provider-neutral scope-budget gating to the shared shell contract so Compass and sibling governance consumers can map cheap versus escalated compute policy through one host-agnostic ladder contract. (Plan: [B-071](odylith/radar/radar.html?view=plan&workstream=B-071))
- 2026-04-16: Deleted the shell telemetry/status presenter, ECharts dependency, recorder/chart CSS, and telemetry render path after CB-120 proved internal telemetry was leaking into dashboard product surfaces. Dashboard now treats any telemetry cockpit, recorder, chart, or status slab in the shell DOM as a regression. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025); Bug: `CB-120`)
