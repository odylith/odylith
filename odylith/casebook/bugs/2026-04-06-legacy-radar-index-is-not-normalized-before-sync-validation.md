- Bug ID: CB-058

- Status: Open

- Created: 2026-04-06

- Severity: P0

- Reproducibility: High

- Type: Product

- Description: `odylith sync` can fail immediately after migration because a
  legacy Radar `INDEX.md` still lacks the current required rationale bullets
  such as `why now`, `expected outcome`, `tradeoff`, `deferred for now`, and
  `ranking basis`.

- Impact: Odylith can migrate successfully enough to run, but still block the
  very next sync on a legacy source format it could normalize mechanically.

- Components Affected: `src/odylith/runtime/governance/validate_backlog_contract.py`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, Radar source
  upgrade bridge.

- Environment(s): Migrated repos with older Radar `INDEX.md` rationale format.

- Root Cause: Sync enforces the new backlog contract immediately, but migration
  and sync preflight do not attempt a one-time normalization of older rationale
  structure before validation.

- Solution: Add a legacy Radar normalizer that backfills only missing required
  bullets, preserves authored text, fills missing manual-override `ranking
  basis` plus review checkpoint data, and runs once before strict sync
  validation.

- Verification: Legacy `INDEX.md` fixtures should normalize once and then pass
  strict validation without manual edits.

- Prevention: Any stricter source contract needs an explicit upgrader when old
  repo truth is still expected to survive product upgrades.

- Detected By: Real downstream `odylith sync` and
  `odylith sync --force --impact-mode selective` failure on 2026-04-06.

- Failure Signature: Backlog contract validation errors on missing rationale
  bullets and missing `ranking basis` for legacy override entries.

- Trigger Path: sync preflight backlog contract validation.

- Ownership: Radar source contract and sync preflight.

- Timeline: Radar contract tightening landed, but the migration bridge for
  older rationale shapes did not.

- Blast Radius: Immediate post-migration sync usability and trust in governed
  repo bootstrap.

- SLO/SLA Impact: High sync-blocking maintenance impact.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: Odylith should not block sync on a mechanically
  normalizable legacy Radar format without first offering the bridge itself.

- Workaround: Manually edit `odylith/radar/source/INDEX.md` to add the missing
  rationale bullets.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Preserve authored rationale; only backfill missing
  contract-required bullets.

- Preflight Checks: Inspect the legacy rationale parser, backlog authoring
  defaults, and priority-override review checkpoint rules before normalizing.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch sync failures for legacy-rationale signatures after
  the normalizer ships.

- Residual Risk: Future Radar schema upgrades may still need explicit versioned
  bridges.

- Related Incidents/Bugs:
  [CB-024](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default sync and forced selective sync.

- Customer Comms: Odylith’s stricter Radar contract landed before the upgrade
  bridge; the fix lets migrated repos normalize once and then enter the new
  contract cleanly.

- Code References: `src/odylith/runtime/governance/validate_backlog_contract.py`,
  `src/odylith/runtime/governance/backlog_authoring.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`

- Runbook References: `odylith/radar/source/INDEX.md`,
  `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
