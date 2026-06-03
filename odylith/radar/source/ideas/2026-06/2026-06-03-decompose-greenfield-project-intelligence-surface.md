status: implementation

idea_id: B-143

title: Decompose greenfield project intelligence surface

date: 2026-06-03

priority: P1

commercial_value: 4

product_impact: 5

market_value: 3

impacted_parts: project-intelligence,greenfield-governance,dashboard,source-size-discipline

sizing: M

complexity: High

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: high

founder_override: no

promoted_to_plan:

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-142

workstream_blocks:

related_diagram_ids: D-043

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
Greenfield project intelligence now carries project story extraction, dashboard payload shaping, status text, first-path summaries, and card rendering in src/odylith/runtime/project_intelligence/greenfield.py, which is 2048 lines after the v0.1.15 semantic-render hardening checkpoint. That size makes future confirmed-greenfield changes harder to review and violates the product repo source-size discipline for a touched hand-maintained source file.

## Customer
Odylith maintainers working on confirmed greenfield governance and consumer-lane operators who rely on the project tab to review accepted product shape before implementation planning.

## Opportunity
Split the project-intelligence greenfield surface into focused owners with characterization coverage so project story facts, project-tab cards, status or CTA assembly, and payload rendering can evolve independently while preserving the existing project review UX.

## Proposed Solution
Extract the current project-intelligence greenfield renderer into named modules that own separate responsibilities: accepted project facts, card view models, first-path/status handoff text, and final dashboard payload assembly. Keep the current public payload contract stable while moving code behind characterization tests and project-tab browser proof.

## Scope
- Inventory the current public payload and browser-visible project-tab states before moving code.
- Extract one or two cohesive owners at a time instead of creating pass-through wrappers.
- Keep the main `greenfield.py` file below 1200 lines after the first decomposition slice.
- Preserve normal, fallback, and degraded project-tab behavior with unit and browser regression proof.

## Non-Goals
- Do not widen this workstream into unrelated product cleanup.

## Risks
- Domain/compliance/policy risk: Decomposition can accidentally change greenfield project-tab copy, hide readiness gates, or weaken first-path proof context. The slice must use characterization tests and browser proof before claiming parity.
- Security posture: No new trust boundary or provider call is allowed. The refactor must preserve accepted-intent provenance, avoid host-specific identity leakage, and keep generated operator guidance generic to Odylith-owned product behavior.

## Dependencies
- Depends on B-142 semantic-render hardening because the oversized file was touched while project-tab copy began consuming the confirmed first-path semantic helpers.

## Success Metrics
src/odylith/runtime/project_intelligence/greenfield.py drops below 1200 lines; extracted modules have clear ownership and no fake pass-through wrappers; tests/unit/runtime/test_project_intelligence.py and tests/integration/runtime/test_project_tab_browser.py pass; generated project dashboard surfaces show no wording or layout regression for normal, fallback, and degraded greenfield states.

## Validation
- Run `tests/unit/runtime/test_project_intelligence.py`.
- Run `tests/integration/runtime/test_project_tab_browser.py`.
- Run a focused generated-surface review for normal, fallback, and degraded project-tab states before claiming parity.

## Rollout
- Land focused extraction slices with unchanged public payload shape, then refresh Radar and Compass after source proof passes.

## Implementation Evidence
- 2026-06-03 first slice split `src/odylith/runtime/project_intelligence/greenfield.py` into focused owners for source/proposal helpers, project text, participant cards, job cards, and known/unknown/risk cards. The top-level greenfield adapter dropped from 2048 lines to 287 lines; extracted modules range from 219 to 706 lines and keep the public payload assembly path stable.
- The same pass fixed subject-plus-base-verb story rendering by reusing the shared prose grammar inflector, so accepted first-path narration preserves readable subject/verb agreement such as `the user taps Record`.

## Why Now
The file crossed the 2000-line threshold while active greenfield quality work was still touching the project-tab path. Future greenfield surface changes need this decomposition lane before more behavior lands in the same module.

## Product View
The project tab should keep showing the same accepted project lane, direction choices, readiness gates, wave status, and first-path handoff, but the implementation should make each rendering responsibility easy to inspect and test without reopening a 2000-line module.

## Impacted Components
- `odylith`
- `domain-intelligence`
- `dashboard`

## Interface Changes
- None decided yet; record interface changes once implementation is scoped.

## Migration/Compatibility
- No migration impact recorded yet.

## Test Strategy
- `.venv/bin/python -m pytest -q tests/unit/runtime/test_project_intelligence.py` (`32 passed`).
- `.venv/bin/python -m pytest -q tests/unit/runtime/test_greenfield_general_artifact_quality.py tests/unit/runtime/test_greenfield_component_spec_quality.py tests/unit/runtime/test_greenfield_post_confirm_slop_regressions.py tests/unit/runtime/test_greenfield_component_semantic_contract_quality.py tests/unit/runtime/test_greenfield_confirmed_repair.py tests/unit/runtime/test_greenfield_artifact_language_quality.py` (`67 passed`).
- `.venv/bin/python -m pytest -q tests/integration/runtime/test_project_tab_browser.py` (`2 passed`).

## Open Questions
- Whether a follow-up slice should split `greenfield_project_text.py` further once additional project-tab copy changes accumulate.
