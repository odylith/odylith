Status: Done
Created: 2026-07-20
Updated: 2026-08-18
Backlog: B-145

# v0.1.15 Guidance And Browser Surface Migration Assessment

## Goal
Determine whether the v0.1.15 guidance, operator CLI presentation,
browser-surface, and install-managed asset changes require a consumer source
migration before release promotion.

## Assessed Scope
- Managed Codex and Claude guidance and skills.
- Operator CLI and component-authoring presentation contracts.
- Generated Atlas, Casebook, Compass, Radar, Registry, and Project surfaces.
- Install, upgrade, reinstall, doctor, and dashboard-refresh behavior.
- Consumer-owned governance source preservation and rollback posture.

## Decision
No consumer source migration is required. The changed files are managed
runtime, guidance, bundle, or generated browser assets that existing refresh
and recovery paths already own. Consumer-authored Radar, Registry, Atlas,
Casebook, and Compass source must remain unchanged during installation and
upgrade.

## Compatibility And Risk
- Existing consumer repositories remain compatible with the managed refresh
  contract; no schema rewrite or source-data backfill is required.
- Rollback restores the prior managed runtime and assets without rewriting
  consumer source.
- Browser and guidance changes remain release-sensitive because they affect
  navigation, accessibility, and host behavior, so the migration observer must
  bind the final changed-path fingerprints before promotion.
- No secrets or customer content are introduced by the assessed surfaces.

## Evidence
- The release migration observer fingerprints are recorded in B-145.
- The current assessment binds guidance `d4f690f22f7e`, operator CLI
  `00f2ed299d15`, browser `5630641b37af`, and install-managed asset
  `32bd860ec2a6` fingerprints.
- `D-023` describes the managed runtime release and install flow.
- `D-042` describes migration planning, application, ledger, and release-gate
  ownership.
- The installed Greenfield campaign and managed install tests exercise the
  affected runtime and generated browser surfaces without consumer source
  mutation.

## Validation
- `odylith release migration-gate --repo-root . --target-version 0.1.15`
  resolves every final observer fingerprint to B-145.
- Radar validation accepts the finished workstream, plan binding, and topology
  references.
- `odylith sync --repo-root . --check-only` passes before final refresh.
- `git diff --check` passes before the release checkpoint.

## Stop Condition
The assessment is complete when the migration gate recognizes the final
fingerprints, consumer-owned source is unchanged by managed refresh paths, and
the governed workstream and plan bindings validate.
