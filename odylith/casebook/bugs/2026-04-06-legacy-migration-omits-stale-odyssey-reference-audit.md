- Bug ID: CB-057

- Status: Open

- Created: 2026-04-06

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Legacy migration moves `odyssey/` and `.odyssey/` into the
  Odylith layout, but it does not audit or report stale `odyssey` references
  that still survive in tracked text files outside the managed tree.

- Impact: Operators can leave migration believing the repo is fully normalized
  even though governance Markdown, docs, or agent guidance still reference the
  old product name and paths.

- Components Affected: `src/odylith/install/manager.py`, migration summary and
  reporting, tracked-text audit policy.

- Environment(s): Legacy consumer repos migrated into modern Odylith layout.

- Root Cause: Migration only rewrites the managed tree and a few known JSON
  payloads. It does not scan the rest of tracked repo truth for stale legacy
  references.

- Solution: Add a non-destructive stale-reference audit that scans tracked text
  files outside managed runtime/cache trees, prints a compact summary, and
  persists a full report under `.odylith/state/migration/`.

- Verification: Migration tests should prove stale references are reported but
  not rewritten.

- Prevention: Migration should declare what it normalized and what still needs
  manual follow-up.

- Detected By: Real downstream migration on 2026-04-06 plus local inspection of
  Odylith source truth showing existing stale `odyssey` references in governed
  plan records.

- Failure Signature: Migration reports success, but tracked files such as
  plans, AGENTS docs, or maintainer docs still contain `odyssey`.

- Trigger Path: `odylith migrate-legacy-install`, `odylith install`, and
  `odylith reinstall` when legacy layout is present.

- Ownership: migration contract and operator reporting.

- Timeline: Earlier migration work correctly moved the managed tree, but it did
  not add a post-migration audit of surrounding repo truth.

- Blast Radius: Migration completeness, doc and governance truth hygiene, and
  operator trust in the migration summary.

- SLO/SLA Impact: Low direct runtime risk, medium migration-truth risk.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: Migration should not silently leave legacy product
  references unreported in tracked source truth.

- Workaround: Run manual grep after migration and fix references by hand.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Report stale references without auto-rewriting user-owned
  docs.

- Preflight Checks: Restrict the audit to tracked text files and exclude
  generated runtime/cache state.

- Regression Tests Added: Pending.

- Monitoring Updates: Track how often migration audits still report stale
  `odyssey` references after the bridge ships.

- Residual Risk: Some stale references may remain intentionally historical and
  should stay reported, not silently rewritten.

- Related Incidents/Bugs:
  [CB-024](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default migration path.

- Customer Comms: Odylith migration moved the managed layout correctly but did
  not previously tell operators where legacy `odyssey` references still needed
  manual cleanup.

- Code References: `src/odylith/install/manager.py`,
  `tests/integration/install/test_manager.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
