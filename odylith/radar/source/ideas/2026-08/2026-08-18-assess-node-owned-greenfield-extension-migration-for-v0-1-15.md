status: finished

idea_id: B-146

title: Assess node-owned Greenfield extension migration for v0.1.15

date: 2026-08-18

priority: P1

commercial_value: 3

product_impact: 4

market_value: 3

impacted_parts: Greenfield Semantic Intent, release migration gate, managed runtime activation, Casebook and governance browser refresh

sizing: XS

complexity: Low

ordering_score: 100

ordering_rationale: Queued through `odylith backlog create` from the current maintainer lane.

confidence: High

founder_override: no

promoted_to_plan: odylith/technical-plans/done/2026-08/2026-08-26-v0-1-15-node-owned-greenfield-extension-migration-assessment.md

execution_model: standard

workstream_type: standalone

workstream_parent:

workstream_children:

workstream_depends_on: B-142

workstream_blocks:

related_diagram_ids: D-045

workstream_reopens:

workstream_reopened_by:

workstream_split_from:

workstream_split_into:

workstream_merged_into:

workstream_merged_from:

supersedes:

superseded_by:

## Problem
The node-owned Semantic Intent extension contract changes managed runtime and regenerated governance-browser bytes. Existing installs must not mix the new packet and authority versions with an older runtime or retain stale generated surfaces.

- `migration-observer:0.1.15:browser-surfaces:65a03bfb343d`
- `migration-observer:0.1.15:browser-surfaces:2b55ba920808`
- `migration-observer:0.1.15:browser-surfaces:9cee09d117c8`
- `migration-observer:0.1.15:browser-surfaces:21d87c2da5ef`
- `migration-observer:0.1.15:install-managed-assets:6aad0d78490e`
- `migration-observer:0.1.15:install-managed-assets:3d76b3df0543`
- `migration-observer:0.1.15:browser-surfaces:96039a953cd7`
- `migration-observer:0.1.15:install-managed-assets:13d6f64a015b`
- `migration-observer:0.1.15:browser-surfaces:3fee2d4c478e`
- `migration-observer:0.1.15:install-managed-assets:b45cab51875d`

## Customer
Odylith maintainers and operators upgrading existing consumer repositories that use Greenfield proposals and browser-rendered governance surfaces.

## Opportunity
Prove that the new typed edge contract requires only verified runtime activation and deterministic surface refresh, while repo-owned Casebook, Radar, Registry, and Atlas source truth remains unchanged and recoverable.

## Proposed Solution
Treat semantic-source-meaning graph v16, Semantic Intent IR v23, packet v35, Product Intent authority v40, and compiler identity v33 as one fail-closed runtime boundary. Existing installations adopt the change only through verified atomic runtime activation. Derived browser and bundle surfaces are regenerated from preserved governance source truth; no consumer data is transformed.

## Scope
- Assess the new semantic protocol and generated-surface bytes against existing consumer-install contracts.
- Bind the exact browser and install-managed fingerprints to this reviewed assessment.
- Verify obsolete packets reject before confirmation, activation remains atomic, and governed source truth remains preserved.

## Non-Goals
- Do not widen this queued workstream into unrelated product cleanup.

## Risks
- Domain/compliance/policy risk: Primary risk is a stale runtime rendering or confirming bytes from the newer semantic protocol. The release gate must remain fail-closed, and existing governed source records must never be rewritten as migration output.
- Security posture: Keep packet, authority, compiler-identity, and transaction hashes version-bound; preserve exact sealed-byte verification; perform no post-confirm semantic work; retain rollback and symlink protections for managed activation.

## Dependencies
- B-142 Universal greenfield domain intelligence.
- CB-348 Greenfield graph extension exposes boundary subjects rejected by bounded assembly.

## Success Metrics
The exact migration-observer fingerprint is registered; release migration-gate passes; obsolete Semantic Intent packets remain rejected; managed runtime activation remains atomic; generated browser surfaces refresh from preserved source truth; no destructive consumer-data migration is introduced.

## Validation
- The current one-call Greenfield source-meaning path completed its 24-case disclosed cohort with every expected terminal under the strict standard 60-second ceiling; the slowest case took 32.848 seconds.
- Greenfield runtime and install proof passed 463 tests; all seven revision-bound deterministic transaction laws passed.
- Fresh local v0.1.15 release assets completed the disposable clean-install, upgrade, stale-residue, and browser normal/empty/fallback/degraded/error matrix with exit status 0.
- The two current browser and install-managed fingerprints above are the release migration-gate assessment evidence; the gate must be rerun after this record is refreshed.

## Rollout
- Ship through the normal verified runtime release and activation path.
- Refresh derived governance surfaces after activation; preserve Radar, Registry, Atlas, and Casebook source records byte-for-byte except for intentional governed updates.

## Why Now
This slice is active enough that it should exist as explicit backlog truth now.

## Product View
Treat Semantic Intent v12 and authority v18 as a fail-closed runtime boundary. Existing consumer installs upgrade through atomic verified activation, reject obsolete packets before confirmation, preserve repo-owned governance truth, and regenerate derived browser surfaces from current source.

## Impacted Components
- `odylith`

## Interface Changes
- Semantic-source-meaning graph v16 owns node-bound entities, effects, dependencies, and policy boundaries.
- Semantic Intent IR v23, packet v35, authority v40, and compiler identity v33 form one fail-closed protocol boundary.

## Migration/Compatibility
- No destructive consumer-data migration is required.
- Earlier Semantic Intent packets and Product Intent authorities remain historical bytes and are rejected on the v23/v35/v40 execution path; the operator must rebuild from source evidence before confirmation.
- Existing generated browser surfaces are replaceable projections and refresh from preserved governed source truth.

## Test Strategy
- Require the exact migration gate, focused protocol/version tests, atomic activation coverage, the revision-bound deterministic laws, and the full development validator before release evidence is generated.

## Open Questions
- Independent review, host parity, lower-capability safety, and the untouched final holdout remain release gates; none may be replaced by this migration assessment.
