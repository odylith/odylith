status: finished

idea_id: B-145

title: Assess v0.1.15 guidance and browser surface migration

date: 2026-07-20

priority: P1

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Release migration gate, guidance assets, browser-rendered Atlas and Casebook surfaces

sizing: S

complexity: Medium

ordering_score: 100

ordering_rationale: Blocks the release migration gate for changed consumer-visible surfaces.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-07/2026-07-20-v0-1-15-guidance-and-browser-surface-migration-assessment.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on:

workstream_blocks:

related_diagram_ids: D-023,D-042

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
The v0.1.15 release changes managed guidance, browser-rendered governance surfaces, and install-managed assets. Existing consumer installs need an explicit assessment before promotion. Evidence markers: `migration-observer:0.1.15:guidance-and-skills:1dbd05321562`; `migration-observer:0.1.15:guidance-and-skills:5cf1c66e46da`; `migration-observer:0.1.15:browser-surfaces:e400b39b824e`; `migration-observer:0.1.15:browser-surfaces:835aaa4f49de`; `migration-observer:0.1.15:browser-surfaces:9a4db93486ab`; `migration-observer:0.1.15:browser-surfaces:e64341855d69`; `migration-observer:0.1.15:browser-surfaces:28bfbc30ae65`; `migration-observer:0.1.15:install-managed-assets:352b7f58e4df`; `migration-observer:0.1.15:install-managed-assets:fae6b20b969f`; `migration-observer:0.1.15:install-managed-assets:46796f8138f3`; `migration-observer:0.1.15:install-managed-assets:87c9b491c829`.

## Customer
Odylith operators upgrading managed guidance, skill, Atlas, and Casebook browser surfaces.

## Opportunity
Make upgrade impact explicit, reversible, and traceable rather than relying on implicit regenerated assets.

## Proposed Solution
Assess the final changed-path set, bind the exact fingerprints to this record, and verify that consumer-owned governance source remains untouched by upgrade, reinstall, doctor, and dashboard refresh.

## Scope
- Managed guidance and skill surfaces.
- Browser-rendered Atlas, Casebook, Compass, Radar, and Registry surfaces.
- Install-managed project and bundle assets.

## Non-Goals
- Do not migrate or rewrite consumer-owned Radar, Registry, Atlas, Casebook, or Compass source records.
- Do not add a runtime migration where normal managed refresh is sufficient.

## Risks
- Domain/compliance/policy risk: Browser and guidance changes can alter operator-visible behavior and navigation; assessment must cover accessibility, migration compatibility, and no-data-loss posture.
- Security posture: No secrets or customer content. Use only deterministic local inspection; do not mutate consumer repositories while assessing migration exposure.

## Dependencies
- Release migration gate and the completed installed Greenfield release campaign.

## Success Metrics
All three final observer markers resolve to this finished assessment; `odylith release migration-gate --repo-root . --target-version 0.1.15` passes; consumer-owned source remains unchanged while managed runtime, guidance, and generated assets refresh through normal recovery paths.

## Validation
- Recalculate the migration gate against the final dirty path set.
- Confirm the installed Greenfield campaign completed 200 of 200 cases with no product-path failures.
- Run `git diff --check` before the release checkpoint.

## Rollout
- Ship through the standard managed install, upgrade, reinstall, doctor, runtime-refresh, and dashboard-refresh paths. No consumer source migration is required.

## Why Now
The release gate observed these consumer-visible changes in the current diff; the assessment must bind the exact final fingerprints before promotion.

## Product View
Assess the changed guidance and browser surfaces, record compatibility and rollback posture, and either complete the assessment or route concrete migration work before release.

## Impacted Components
- `odylith`

## Interface Changes
- No new consumer command or source schema. Existing managed refresh paths remain the interface.

## Migration/Compatibility
- Existing consumer-owned governance source stays in place. The current Compass change only selects existing release-target language when no program lanes exist; it changes no stored schema or runtime state. Managed guidance, runtime, and generated browser assets refresh normally; rollback returns the managed runtime and assets without source-data migration.

## Test Strategy
- The migration gate validates the completed marker binding. The installed Greenfield campaign validates the affected managed runtime and release assets end to end.

## Open Questions
- None. The final observed path set is assessed and does not require a source-data migration.
