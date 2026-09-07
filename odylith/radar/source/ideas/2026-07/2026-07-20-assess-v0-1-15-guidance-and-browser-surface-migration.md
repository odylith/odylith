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
The v0.1.15 release changes managed guidance, browser-rendered governance surfaces, and install-managed assets. Existing consumer installs need an explicit assessment before promotion. Evidence markers: `migration-observer:0.1.15:guidance-and-skills:1dbd05321562`; `migration-observer:0.1.15:guidance-and-skills:5cf1c66e46da`; `migration-observer:0.1.15:browser-surfaces:e400b39b824e`; `migration-observer:0.1.15:browser-surfaces:835aaa4f49de`; `migration-observer:0.1.15:browser-surfaces:9a4db93486ab`; `migration-observer:0.1.15:browser-surfaces:e64341855d69`; `migration-observer:0.1.15:browser-surfaces:28bfbc30ae65`; `migration-observer:0.1.15:browser-surfaces:068dac56194b`; `migration-observer:0.1.15:browser-surfaces:341c9fc14c4e`; `migration-observer:0.1.15:public-docs-and-release-guidance:b91b6c7e0995`; `migration-observer:0.1.15:install-managed-assets:352b7f58e4df`; `migration-observer:0.1.15:install-managed-assets:fae6b20b969f`; `migration-observer:0.1.15:install-managed-assets:46796f8138f3`; `migration-observer:0.1.15:install-managed-assets:87c9b491c829`.

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
All final observer markers resolve to this finished assessment; `odylith release migration-gate --repo-root . --target-version 0.1.15` passes; consumer-owned source remains unchanged while managed runtime, guidance, and generated assets refresh through normal recovery paths.

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
- Existing consumer-owned governance source stays in place. The Greenfield
  profile documentation and regenerated governance views change no stored
  consumer schema or source truth. Managed guidance, runtime, public docs, and
  generated browser assets refresh normally; rollback returns the managed
  runtime and assets without source-data migration.

## Test Strategy
- The migration gate validates the completed marker binding. The installed Greenfield campaign validates the affected managed runtime and release assets end to end.

## Open Questions
- None. The final observed path set is assessed and does not require a source-data migration.

## 2026-09-06 Component Description Command Assessment

Assessment target: `0.1.15`.

Completed observer bindings:

- `migration-observer:0.1.15:guidance-and-skills:60b71660d9e2`
- `migration-observer:0.1.15:operator-cli-contracts:5b0adb1088a6`
- `migration-observer:0.1.15:public-docs-and-release-guidance:a7fb30006fce`
- `migration-observer:0.1.15:browser-surfaces:c62a1bfb74ab`
- `migration-observer:0.1.15:install-managed-assets:192ba5971da9`

The current operator change preserves `odylith component register` and adds the
explicit `odylith component update-description` command and help route. The new
command updates only `what_it_is` for one exact existing component when an
operator invokes it. It validates the Registry shape and unique component IDs,
refuses every symlink segment in the fixed lexical Registry path before reading
or writing, preserves the existing file mode, uses the shared atomic writer, and
then invokes the normal Registry refresh. It changes no Registry schema, source
parser, component identity, ownership field, or install-time source migration.

The related operator documentation and component-registry skill plus its managed
bundle mirror describe the additive command. Existing installs receive those
runtime and guidance changes through normal install, upgrade, reinstall, or
doctor refresh. Those paths continue to preserve consumer-owned Radar, Registry,
Atlas, Casebook, Compass, and plan source. Only an explicit description-update
invocation changes a consumer Registry source record, and that change remains an
ordinary reviewable repository edit.

The browser and install-managed fingerprints also bind the already assessed
current governance-source and generated-surface settlement. They require normal
dashboard/runtime refresh for derived views and managed bundle assets, not a
stored-data migration. Rollback may restore the prior managed runtime, guidance,
and generated assets without rewriting consumer-owned source. This assessment
does not claim release readiness or adoption; it closes only the migration impact
identified by the exact observer fingerprints above.

### Terminal selective-sync settlement

- `migration-observer:0.1.15:browser-surfaces:a1d51d35b860`

This terminal browser marker binds the selective-sync result after the same
source assessment and generated Atlas, Casebook, Compass, Radar, and Registry
views settled. It introduces no additional command, schema, source-data
migration, or runtime behavior. Existing consumer-owned governance source
remains preserved; normal Radar/dashboard refresh and managed-asset replacement
are sufficient for the derived surfaces represented by this fingerprint.
