status: queued

idea_id: B-006

title: Odylith Dark Theme and Adaptive Surface Tokens

date: 2026-03-27

priority: P1

commercial_value: 4

product_impact: 4

market_value: 4

impacted_lanes: both

impacted_parts: tooling shell theme contract, shared dashboard UI primitives, brand head/meta theme colors, Radar/Atlas/Compass/Registry/Casebook surface palettes, chart and diagram contrast, and local operator theme preference

sizing: XL

complexity: High

ordering_score: 67

ordering_rationale: Odylith's governed surfaces are now used as a real daily workspace, but the shell and child surfaces still skew light-only with hardcoded palette values. A first-class dark theme would materially improve operator comfort and product polish, but it is still less urgent than release proof and the collaboration architecture.

confidence: high

founder_override: no

promoted_to_plan:

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-001

workstream_blocks:

related_diagram_ids:

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Odylith's shell host and governed child surfaces are now rich enough to be used
for long operator sessions, but the visual system is still effectively
light-only. Shared UI primitives assume bright backgrounds, the brand head
publishes a single light `theme-color`, and multiple surface renderers still
embed light palette literals directly in their HTML and CSS output. That makes
night-time use less comfortable, weakens the product's public polish, and
creates avoidable inconsistency if any surface tries to go dark in isolation.

## Customer
- Primary: Odylith operators and maintainers who spend long stretches inside
  Radar, Compass, Registry, Atlas, Casebook, and the shell host.
- Secondary: downstream adopters evaluating whether Odylith feels like a
  modern, production-ready product rather than a light-only internal tool.
- Tertiary: future surface authors who need semantic tokens and a stable theme
  contract instead of copying hardcoded light palette values.

## Opportunity
By treating dark theme as a cross-surface contract instead of a one-off CSS
pass, Odylith can improve daily usability, reduce future styling churn, and
make new surfaces inherit a real appearance system by default.

## Proposed Solution
Introduce a product-wide appearance contract with semantic tokens, explicit
theme-mode selection, and surface-by-surface adoption across the governed UI.

### Wave 1: Shared appearance contract
- define semantic light/dark tokens for shell and governed surfaces instead of
  depending on light-only literals inside individual renderers
- extend brand/meta output so `theme-color`, color-scheme hints, and shared
  shell framing understand both light and dark presentation
- centralize reusable contrast tiers for text, panels, dividers, status chips,
  code blocks, charts, and diagram containers

### Wave 2: Theme-mode selection and propagation
- support `system`, `light`, and `dark` as the initial appearance modes
- persist the operator's choice locally without turning theme preference into
  tracked repo truth
- propagate the active mode cleanly from the shell to iframe-backed child
  surfaces so the product does not flash or drift across tabs

### Wave 3: Governed surface adoption
- update Radar, Registry, Atlas, Compass, Casebook, and the top-level shell to
  consume the shared tokens instead of per-surface light assumptions
- fix charts, legends, badges, tables, and diagram canvases so they remain
  legible and intentionally styled in dark mode
- keep surface-specific accents where useful, but normalize backgrounds, text
  hierarchy, focus rings, and panel depth

### Wave 4: Accessibility and rollout hardening
- add contrast and visual-regression checks around the shared appearance
  primitives and the major governed surfaces
- verify deep links, standalone views, screenshots, and print/export-adjacent
  flows still behave sensibly under the chosen mode
- document the appearance contract so later surface work extends the system
  instead of reintroducing light-only literals

## Scope
- shared semantic theme tokens for Odylith shell and governed surfaces
- local appearance preference contract with `system` / `light` / `dark`
- cross-surface propagation between shell host and iframe surfaces
- dark-mode adoption for Radar, Atlas, Compass, Registry, and Casebook
- contrast fixes for charts, pills, badges, tables, and code/diagram panels
- brand/meta theme-color updates and appearance documentation

## Non-Goals
- a full visual rebrand or layout redesign in the same slice
- arbitrary custom themes beyond the initial `system` / `light` / `dark`
  contract
- syncing per-user theme preference through hosted services or tracked repo
  files
- redesigning every diagram's information architecture just to support dark
  backgrounds

## Risks
- shell and child surfaces can drift if appearance state is propagated
  inconsistently across iframe boundaries
- contrast can regress quietly in charts, warning panels, and code/diagram
  containers even if the main backgrounds look correct
- hardcoded light palette values are spread across renderers today, so a
  partial rollout could leave Odylith feeling visually fragmented
- print, export, and screenshot flows can become awkward if dark defaults are
  applied without explicit fallbacks

## Dependencies
- `B-001` established Odylith's product-owned surface boundary and the local
  truth model the appearance contract now needs to span
- existing shell-brand plumbing and shared dashboard UI primitives provide the
  starting point, but they need to be upgraded from light-biased defaults to
  semantic tokens

## Success Metrics
- Odylith exposes an explicit appearance mode with `system`, `light`, and
  `dark`
- shell and child surfaces render in the same active mode without theme drift
  or startup flash
- Radar, Atlas, Compass, Registry, and Casebook all remain legible and
  visually intentional in dark mode
- major status chips, tables, charts, and diagram/code panels meet baseline
  contrast expectations
- new surface work can reuse the shared appearance tokens instead of
  introducing more light-only literals

## Validation
- `odylith sync --repo-root . --check-only`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_brand_assets.py tests/unit/runtime/test_render_tooling_dashboard.py tests/unit/runtime/test_render_backlog_ui.py tests/unit/runtime/test_render_registry_dashboard.py tests/unit/runtime/test_render_mermaid_catalog.py`
- `PYTHONPATH=src python -m pytest -q tests/unit/runtime/test_compass_dashboard_base.py tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_dashboard_shell.py`
- manual shell walkthrough across `odylith/index.html`, Radar, Atlas,
  Compass, Registry, and Casebook in light, dark, and system mode

## Rollout
Land the token and preference contract first, migrate the shell and highest-use
surfaces next, and only then tighten contrast and polish across the remaining
governed surfaces.

## Why Now
Odylith has moved past the stage where styling is throwaway scaffolding. The
product now has a real shell, multiple governed dashboards, and a public-facing
surface story. If dark theme stays ad hoc, each new surface or polish pass will
carry more light-only debt.

## Product View
Odylith should feel like a product people can actually live in, not a bright
tooling mockup that becomes unpleasant after sunset. The right move is one
coherent appearance contract, not a pile of isolated dark patches.

## Impacted Components
- `odylith`
- `dashboard`
- `radar`
- `atlas`
- `compass`
- `registry`
- `casebook`

## Interface Changes
- add a shared appearance contract for shell and governed surfaces
- add local operator preference for `system`, `light`, and `dark`
- update brand/meta output to emit dark-aware theme hints
- make generated surface styling consume semantic tokens rather than light-only
  palette literals

## Migration/Compatibility
- keep light mode available throughout migration so existing screenshots,
  habits, and docs do not break immediately
- treat theme preference as local runtime state, not tracked repo truth
- make the first rollout additive by mapping existing light defaults onto the
  new token system before switching surfaces one by one
- preserve stable deep-link and rendering contracts while appearance behavior
  changes underneath

## Test Strategy
- add unit coverage for brand/meta appearance output and theme-mode plumbing
- add renderer assertions for tokenized shell and governed surface CSS output
- add targeted regression coverage for dark-mode chart, badge, and panel
  contrast-sensitive regions
- run manual visual checks across the shell and each governed surface in all
  three initial modes

## Open Questions
- should Odylith default to `system` immediately, or keep `light` as the
  initial default until dark mode is proven across all governed surfaces
- should Atlas diagram rendering adapt diagram canvases automatically in dark
  mode, or keep light canvases inside dark surrounding chrome for the first
  iteration
