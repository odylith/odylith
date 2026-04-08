# Dashboard
Last updated: 2026-04-08


Last updated (UTC): 2026-04-08

## Purpose
Dashboard is the shell host for Odylith. It provides the top-level tabbed,
deep-linkable parent surface that composes Radar, Atlas, Compass, Registry, and
Casebook into one navigable product entrypoint without flattening each child
surface into the shell renderer.

## Scope And Non-Goals
### Dashboard owns
- Shell-level routing and query-param deep links.
- The parent iframe composition model.
- Shared shell drawer and system-status summary.
- Shared branding, favicon, manifest, and tab lockup behavior.
- Externalized shell asset bundling for the checked-in root surface.

### Dashboard does not own
- The underlying business logic of Radar, Atlas, Compass, Registry, or
  Casebook.
- Reinterpreting child-surface data contracts in the shell.
- Acting as a source of truth for governance state. It reads derived payloads.

## Developer Mental Model
- The shell is intentionally thin.
- Child surfaces render their own HTML and JS bundles.
- The shell embeds those pages, routes between them, and adds shared
  navigation, brand framing, and deep-link translation.
- Shell link semantics are centralized so proof routes, scope routes, and tab
  links stay consistent across surfaces.

## Runtime Contract
### Owning modules
- `src/odylith/runtime/surfaces/render_tooling_dashboard.py`
  Root renderer for `odylith/index.html`.
- `src/odylith/runtime/surfaces/tooling_dashboard_shell_presenter.py`
  Template context assembly and shell drawer shaping.
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

The presenter then derives shell drawer content, case preview rows, and template
context before externalizing the bundle.

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

The same truth rule applies to explicit refresh: the shell may read Compass
runtime state and surface stale/failure posture, but it must not imply that
Compass rerendered unless the Compass child-runtime snapshot actually changed.

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
- 2026-03-31: Froze the dashboard header contract and made shell render fail closed if the source-owned header template or header CSS drifts. (Plan: [B-027](odylith/radar/radar.html?view=plan&workstream=B-027))
- 2026-04-01: Restored the compact runtime/version string inside the frozen header contract so pinned and detached maintainer lanes stay visibly distinguishable. (Plan: [B-027](odylith/radar/radar.html?view=plan&workstream=B-027))
- 2026-04-02: Added balanced, proof-frozen, and full-dev live-refresh policies so read-only runtime-backed tabs can stay current without background sync, provider-credit spend, or benchmark skew. (Plan: [B-025](odylith/radar/radar.html?view=plan&workstream=B-025))
