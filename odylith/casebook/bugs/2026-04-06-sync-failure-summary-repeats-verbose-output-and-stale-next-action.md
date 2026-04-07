- Bug ID: CB-059

- Status: Open

- Created: 2026-04-06

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: When sync fails, Odylith can dump a long repetitive validation
  trace and then recommend rerunning the same forced command that already
  failed with the same blocker.

- Impact: Operators have to manually deduplicate the failure cause and ignore a
  misleading next step instead of getting a compact actionable summary.

- Components Affected: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, sync error
  presentation and next-action routing.

- Environment(s): Any repo where sync validation fails, especially legacy Radar
  migration cases.

- Root Cause: Sync failure handling exposes raw validator output directly and
  uses static retry guidance instead of routing next steps by failure class.

- Solution: Collapse duplicate errors into a top-N summary with counts, keep a
  representative file anchor, and recommend a distinct next action based on the
  actual failure class.

- Verification: CLI tests should prove sync failure output is deduped and that
  next actions differ across normalization, remaining-contract, and repair
  failure classes.

- Prevention: Operator-facing failure summaries should route by classified error
  type instead of reusing one generic retry string.

- Detected By: Real downstream sync failure review on 2026-04-06.

- Failure Signature: Hundreds of lines of validation output followed by a retry
  recommendation for the same failed forced sync command.

- Trigger Path: sync failure handling in CLI and workstream-artifact execution.

- Ownership: sync operator UX.

- Timeline: Earlier sync polish improved some surface diagnostics, but the main
  validation-failure summary still stayed too raw.

- Blast Radius: Sync usability, operator trust in CLI guidance, and time to
  recover from real contract failures.

- SLO/SLA Impact: Medium operator-time impact.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: Sync failure guidance should point to the next different
  action, not tell the operator to repeat the same failed command.

- Workaround: Manually inspect the raw validation output and choose the next
  action without trusting the CLI summary.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Keep representative file anchors in the compact summary so
  deduping does not become hand-wavy.

- Preflight Checks: Inspect current sync failure text and validator outputs
  before designing the compact summary shape.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch sync failures for repeated-command guidance after
  the summary router ships.

- Residual Risk: Very large failure sets may still need a saved full report in
  a later wave.

- Related Incidents/Bugs:
  [CB-024](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-03-31-radar-backlog-index-uses-absolute-workstation-links-and-breaks-clean-checkout-proof.md)

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default sync and forced selective sync.

- Customer Comms: Odylith was too verbose and too repetitive about sync
  failures; the fix makes the summary compact and routes the next real action.

- Code References: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `tests/unit/test_cli.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
