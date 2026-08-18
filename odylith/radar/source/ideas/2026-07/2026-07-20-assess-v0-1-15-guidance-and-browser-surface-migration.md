status: finished

idea_id: B-145

title: Assess v0.1.15 guidance and browser surface migration

date: 2026-07-20

priority: P1

commercial_value: 5

product_impact: 5

market_value: 5

impacted_parts: Release migration gate, guidance assets, operator CLI contracts, browser-rendered governance surfaces, install-managed assets

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
The v0.1.15 release changes managed guidance, operator CLI presentation contracts, browser-rendered governance surfaces, and install-managed assets. Existing consumer installs need an explicit assessment before promotion. The current graph-native cutover is bound to these exact evidence markers: `migration-observer:0.1.15:guidance-and-skills:d4f690f22f7e`; `migration-observer:0.1.15:operator-cli-contracts:00f2ed299d15`; `migration-observer:0.1.15:browser-surfaces:5630641b37af`; `migration-observer:0.1.15:browser-surfaces:011ecfc1d735`; `migration-observer:0.1.15:install-managed-assets:32bd860ec2a6`; `migration-observer:0.1.15:install-managed-assets:582eac588a61`. The additional markers cover the additive CB-347 failure record, its graph-wide candidate-adjudication mechanism evidence, and the corresponding rendered Casebook bundle. They change no installed browser schema and rewrite no consumer-owned governance source; ordinary surface and managed-asset refresh remains sufficient.

## Customer
Odylith operators upgrading managed guidance, skill, Atlas, and Casebook browser surfaces.

## Opportunity
Make upgrade impact explicit, reversible, and traceable rather than relying on implicit regenerated assets.

## Proposed Solution
Assess the final changed-path set, bind the exact fingerprints to this record, and verify that consumer-owned governance source remains untouched by upgrade, reinstall, doctor, and dashboard refresh.

## Scope
- Managed guidance and skill surfaces.
- Operator CLI and component-authoring presentation contracts.
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
All four final observer markers resolve to this finished assessment; `odylith release migration-gate --repo-root . --target-version 0.1.15` passes; consumer-owned source remains unchanged while managed runtime, guidance, operator presentation, and generated assets refresh through normal recovery paths.

## Validation
- Recalculate the migration gate against the final dirty path set.
- Confirm the guidance, browser, component-authoring, install, and canonical validation slices covering the changed paths pass before release proof.
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
- The graph-native Greenfield entrypoint uses the canonical `--semantic-intent-file` packet flag; component responsibility presentation preserves exact authored responsibility without prose inference. Existing managed refresh paths remain the installation interface.

## Migration/Compatibility
- Existing consumer-owned governance source stays in place. Managed guidance, runtime, and generated browser assets refresh normally; rollback returns the managed runtime and assets without source-data migration.

## Test Strategy
- The migration gate validates the completed marker binding. The installed Greenfield campaign validates the affected managed runtime and release assets end to end.

## Open Questions
- None. The final observed path set is assessed and does not require a source-data migration.
