- Bug ID: CB-060

- Status: Open

- Created: 2026-04-06

- Severity: P2

- Reproducibility: High

- Type: Product

- Description: Install, reinstall, and sync lifecycle plans currently print
  the full `dirty_overlap` listing by default, which can flood the terminal
  with managed-runtime and generated-surface paths during migration and repair.

- Impact: Operators lose the high-signal lifecycle summary in the middle of a
  long path dump and have to visually filter expected generated changes by hand.

- Components Affected: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`, lifecycle-plan
  printers.

- Environment(s): Dirty worktrees with many generated or managed files.

- Root Cause: Lifecycle-plan output treats dirty overlap as a full listing
  problem instead of a summary problem.

- Solution: Collapse dirty overlap to counts plus a few representative paths by
  default and add `--verbose` for the full listing.

- Verification: CLI tests should prove default compact output and verbose full
  output separately.

- Prevention: Operator-summary views should optimize for signal first and keep
  enumerations behind explicit verbosity flags.

- Detected By: Real downstream migration logs on 2026-04-06.

- Failure Signature: Very large `dirty_overlap:` sections in install,
  reinstall, and sync plan output.

- Trigger Path: lifecycle-plan printing in CLI and sync helpers.

- Ownership: operator output contract.

- Timeline: Release-hardening waves improved lifecycle planning, but the plan
  printer still dumps too much raw overlap detail by default.

- Blast Radius: Terminal readability and operator confidence during lifecycle
  maintenance.

- SLO/SLA Impact: Low direct runtime risk, medium UX-noise impact.

- Data Risk: Low.

- Security/Compliance: No direct security impact.

- Invariant Violated: Lifecycle plans should summarize working-tree risk before
  enumerating every generated path.

- Workaround: Scroll past the dump or manually rerun with custom filtering.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Keep a representative sample in default output so the
  summary still shows what kind of paths are dirty.

- Preflight Checks: Inspect both CLI lifecycle-plan printers so install and
  sync stay aligned.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch for verbose dirty-overlap complaints after the
  compact default ships.

- Residual Risk: Operators may still need the full listing for rare debugging,
  so verbose mode must remain available.

- Related Incidents/Bugs: No older directly matching bug found.

- Version/Build: Odylith 0.1.7 observed on 2026-04-06 during downstream
  migration.

- Config/Flags: Default lifecycle-plan output.

- Customer Comms: Odylith’s lifecycle plans were too noisy by default; the fix
  keeps the summary readable and moves full overlap enumeration behind
  `--verbose`.

- Code References: `src/odylith/cli.py`,
  `src/odylith/runtime/governance/sync_workstream_artifacts.py`,
  `tests/unit/test_cli.py`,
  `tests/unit/runtime/test_sync_cli_compat.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
