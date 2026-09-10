status: implementation

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

promoted_to_plan: odylith/technical-plans/in-progress/2026-07/2026-07-20-v0-1-15-guidance-and-browser-surface-migration-assessment.md

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
The clean candidate at `bbe312144e75bdde37d1fa93f569d9d27df06eb0` changes 809
consumer-sensitive paths relative to published v0.1.14 at
`fae446995e13e12409e50f944a336dbc846db90a`. CB-337 established that earlier
dirty-only checks could forget committed changes. This assessment is reopened:
its historical bindings do not qualify the current release-wide comparison.

Historical bindings from earlier snapshots, retained for traceability only:

The v0.1.15 release changes managed guidance, browser-rendered governance surfaces, and install-managed assets. Existing consumer installs need an explicit assessment before promotion. Evidence markers: `migration-observer:0.1.15:guidance-and-skills:1dbd05321562`; `migration-observer:0.1.15:guidance-and-skills:5cf1c66e46da`; `migration-observer:0.1.15:browser-surfaces:e400b39b824e`; `migration-observer:0.1.15:browser-surfaces:835aaa4f49de`; `migration-observer:0.1.15:browser-surfaces:9a4db93486ab`; `migration-observer:0.1.15:browser-surfaces:e64341855d69`; `migration-observer:0.1.15:browser-surfaces:28bfbc30ae65`; `migration-observer:0.1.15:browser-surfaces:068dac56194b`; `migration-observer:0.1.15:browser-surfaces:341c9fc14c4e`; `migration-observer:0.1.15:public-docs-and-release-guidance:b91b6c7e0995`; `migration-observer:0.1.15:install-managed-assets:352b7f58e4df`; `migration-observer:0.1.15:install-managed-assets:fae6b20b969f`; `migration-observer:0.1.15:install-managed-assets:46796f8138f3`; `migration-observer:0.1.15:install-managed-assets:87c9b491c829`.

## Customer
Odylith operators upgrading managed guidance, skill, Atlas, and Casebook browser surfaces.

## Opportunity
Make upgrade impact explicit, reversible, and traceable rather than relying on implicit regenerated assets.

## Proposed Solution
Compare the published predecessor and complete candidate trees, map each
classified path to its compatibility decision and proof, and exercise the actual
published runtime with populated governance. Bind final fingerprints only after
the assessment is complete; do not infer source preservation from an empty repo.

## Scope
- Managed guidance and skill surfaces.
- Browser-rendered Atlas, Casebook, Compass, Radar, and Registry surfaces.
- Install-managed project and bundle assets.
- Operator CLI contracts and public release guidance.

## Non-Goals
- Do not migrate or rewrite consumer-owned Radar, Registry, Atlas, Casebook, or Compass source records.
- Do not add a runtime migration where normal managed refresh is sufficient.

## Risks
- Domain/compliance/policy risk: Browser and guidance changes can alter operator-visible behavior and navigation; assessment must cover accessibility, migration compatibility, and no-data-loss posture.
- Security posture: No secrets or customer content. Run migration witnesses only
  in explicitly owned temporary consumers, preserving source bytes, modes and
  recovery evidence. Do not mutate user-owned consumer projects.

## Dependencies
- CB-337 release-comparison custody, CB-338 Atlas identity correction, and the
  populated published-predecessor witness. Greenfield semantic release proof
  remains independently required; historical campaign totals are not current proof.

## Success Metrics
Every final classified path has an explicit compatibility decision and current
evidence; the exact predecessor-bound migration gate passes; populated authored
source bytes and modes survive managed replacement; upgraded governance is
readable in the installed desktop/mobile dashboard. No required empty check passes.

## Validation

Current convergence checkpoint (2026-09-10): The complete derived current-source distribution installs successfully with full local memory. One current-protocol development package has five useful workstreams, five components and five diagrams; independent complete-package review finds no supported P0/P1, while participant inventory, repetitive detail and local verification remain P2/advisory. Exact sealed confirmation and canonical generation/readback checks pass, as does the per-case desktop/mobile browser state matrix with 48 retained screenshots. Startup plus proposal takes 63.56 seconds, so the fixed sixty-second gate remains failed. The bounded cache-invalidation-owner optimization is rejected: required Compass refresh still imports memory independently, and both cold-refresh controls fail. Its seven source-file changes are fully restored and its new test is removed, with private patch/test/results retained; no measured savings or product-code change remains. Do not chase the import cone, disable engines, raise budgets, repeat an unchanged live request for a better draw, or introduce another semantic/evaluator architecture. Full-history browser failure, successful internal repair, all-profile latency/generalization, actual populated-predecessor upgrade, current desktop automatic intervention and final untouched holdout remain open. Evidence: /private/tmp/odylith-current-distribution.LLibTP/, /private/tmp/odylith-compiler-profile.4SyP2l/OUTCOME.md and /private/tmp/odylith-cache-invalidation-proof.uEDfkM/OUTCOME.md.
- Run `odylith release migration-gate --repo-root . --target-version 0.1.15 --base-ref v0.1.14`
  against the clean final candidate, with the predecessor resolved from published metadata.
- Verify the complete distribution, published-predecessor identity, nonzero
  authored source inventory, exact source preservation and installed readback.
- Inspect real desktop/mobile populated views; retain the broader normal,
  empty/fallback and degraded/error proof with its exact candidate boundaries.
- Run `git diff --check` before the release checkpoint.

## Rollout
- Qualify standard managed paths before release. The published v0.1.14 launcher
  may refuse a target migration it does not register; validate the hosted
  continuation on that same preserved consumer. Do not reset it or bypass the gate.

## Why Now
The release gate observed these consumer-visible changes in the current diff; the assessment must bind the exact final fingerprints before promotion.

## Product View
Assess the changed guidance and browser surfaces, record compatibility and rollback posture, and either complete the assessment or route concrete migration work before release.

## Impacted Components
- `odylith`

## Interface Changes
- Include the additive `component update-description` contract and distinguish
  consumer commands from maintainer-only release-comparison options. Current
  CONFIRM publishes a complete sealed package without generating or repairing it.

## Migration/Compatibility
- Consumer-owned source preservation is an invariant to prove, not an assumption
  inherited from older assessments. Managed runtime/guidance replacement and
  derived-view refresh have different ownership from authored records.
- Never roll back an already observed published package silently. Preserve an
  explicit recovery outcome when publication or readback cannot complete safely.
- Released v0.1.14 predates the later sealed-generation architecture. Do not add
  an unreleased development-journal converter to this actual predecessor assessment.

## Test Strategy
- The gate proves exact assessment binding, not compatibility by itself. Pair
  it with independently reviewed path coverage, installed migration witnesses,
  source/mode preservation and rendered readback. Keep semantic/SLA gates separate.

## Open Questions
- Does the actual published predecessor preserve populated authored records and
  deliver nonempty, readable upgraded surfaces through the supported continuation?
- Does each of the five current path classes have sufficient version-bound
  evidence, including current host guidance and recovery limitations?

## Current release-wide evidence (2026-09-09)

The frozen clean candidate comparison identifies guidance/skills (134 paths),
operator CLI (65), public docs (30), browser surfaces (577), and install-managed
assets (132). Classes overlap; 809 paths are distinct. All five assessments
remain incomplete. The full report and candidate distribution are retained in
`/private/tmp/odylith-populated-predecessor-proof.0JeIRw/`.

All twelve local distribution checksums pass; build provenance records clean
`bbe31214`, and all 3,204 frozen source inputs remain unchanged after the build.
This is a complete local unsigned candidate, not a published release or populated
upgrade proof. Current post-CB-338 source passes 5,058 runtime, 1,437 install,
180 CLI and 376 browser checks with one documented Radar fixture-state skip.
The earlier actual published-predecessor and same-version recovery witnesses
used empty governance sources; neither closes the populated migration gap.

Retain historical decisions below without treating their fingerprints or test
totals as approval of this reopened scope. No current completion markers have
been added. Greenfield quality, 60/90/120, current-desktop automatic delivery and
the protected final holdout remain open.

The coverage review found current, not historical, release-note references to
disabled Greenfield apply and post-apply refresh. CB-340 owns their correction;
two red controls precede matching authored/bundled copy and nine passing tests.
Rendered and independent proof remain pending. CB-339 separately records that
the existing reconciliation command skips a reopened plan missing from Active
Plans; its validator correctly fails. Repair that canonical owner instead of
hand-editing the index or treating zero reconciliation decisions as completion.

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

## 2026-09-09 Authored Radar Presentation Assessment

The Radar correction replaces prose rewriting with shared, non-executable
Markdown presentation, complete source projection, measured row heights and
resize-anchor preservation. It changes no consumer source schema or stored
data. Existing authored records remain owned by the consumer repository;
regenerating richer views does not require rewriting them. Both already
supported Markdown dependency majors pass the same 114 focused controls.

Managed upgrades continue to stage and verify runtime assets before atomic
activation. Normal Radar/dashboard refresh rebuilds derived views. If an older
launcher reports a failed refresh after successful activation, rerun
`odylith dashboard refresh --repo-root .` through the active repo-local launcher.
Rollback can restore a previously verified runtime; derived views can then be
regenerated without source-data conversion. The bundled security documentation
and browser copies describe and deliver this presentation contract. No new
migration, installer bypass or consumer source rewrite is required.

The frozen source passes 5,036 runtime, 1,168 install and 361 browser checks
with one existing browser fixture skip; three Greenfield root-CLI checks also
pass. Independent source, Markdown-safety, resize and physical-pointer controls
are accepted. All 3,194 selected inputs match before/mid/after. Evidence is at
`/private/tmp/odylith-radar-final-gate.ANcrqg/`; initial failures and focused
controls remain at `/private/tmp/odylith-radar-authored-proof.cEUc92/`.
This assessment covers presentation compatibility and recovery, not a fresh
installed Greenfield campaign, semantic quality acceptance or full release
readiness. Bind the observer's final fingerprints after governance refresh.

Completed bindings after the governed source and generated views settled:

- `migration-observer:0.1.15:browser-surfaces:87d800962b1a`
- `migration-observer:0.1.15:install-managed-assets:14febb0b2fab`
