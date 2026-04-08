- Bug ID: CB-066

- Status: Open

- Created: 2026-04-07

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Some sync-owned JSON artifacts preserve a stable
  `generated_utc` when their semantic payload is unchanged, but the writer
  still rewrites the file on every run. That advances filesystem mtimes while
  keeping the embedded generation timestamp old, so operators see a file
  reported as refreshed even though its internal audit metadata predates the
  write.

- Impact: Auditability breaks down on successful sync runs. Operators cannot
  trust artifact mtimes, embedded timestamps, or refresh messaging to agree
  about when a traceability or delivery-intelligence artifact was last
  meaningfully regenerated.

- Components Affected:
  `src/odylith/runtime/governance/backfill_workstream_traceability.py`,
  `src/odylith/runtime/governance/delivery_intelligence_engine.py`,
  stable generated-timestamp handling, and sync-owned generated JSON artifacts.

- Environment(s): Successful sync runs where traceability autofix or delivery
  intelligence produce no semantic change but still rewrite their output file.

- Root Cause: Stable `generated_utc` helpers correctly preserve the old
  timestamp when payload content is unchanged, but some callers still write the
  rendered JSON unconditionally and print "wrote" messaging even for semantic
  no-op runs.

- Solution: Use write-if-changed semantics for these artifacts and print
  truthful "current" or "unchanged" messaging when sync rechecks a file without
  changing its payload.

- Verification: Unit tests should prove repeat no-op runs keep both file mtime
  intent and embedded `generated_utc` stable while changed payloads still write
  fresh timestamps.

- Prevention: No generated artifact should claim to be refreshed if the write
  path only reserialized an unchanged payload.

- Detected By: Real downstream `odylith sync --repo-root .` feedback on
  2026-04-07 from `/Users/freedom/code/dentoai-orion`, specifically
  `traceability-autofix-report.v1.json` and
  `delivery_intelligence.v4.json`.

- Failure Signature: Filesystem mtime advances on a sync run while embedded
  `generated_utc` stays older than the reported refresh.

- Trigger Path: Traceability-autofix report write and delivery-intelligence
  artifact write during sync.

- Ownership: Audit-fidelity contract for sync-owned generated artifacts.

- Timeline: Stable `generated_utc` preservation already existed, but the write
  layer still treated some semantic no-op renders as writes.

- Blast Radius: Operator trust in sync output, artifact audit trails, and any
  downstream tooling that reads both file mtimes and embedded timestamps.

- SLO/SLA Impact: Medium auditability impact on a core governance lifecycle.

- Data Risk: Low.

- Security/Compliance: Accurate generation metadata is part of trustworthy
  audit evidence.

- Invariant Violated: If sync reports or implies a generated artifact was
  refreshed, the file’s embedded generation metadata must match the write.

- Workaround: Compare payload content by hand and ignore mtime churn for these
  files, or inspect repeated runs to infer that the rewrite was a semantic no-op.

- Rollback/Forward Fix: Forward fix preferred.

- Agent Guardrails: Preserve stable `generated_utc` semantics for unchanged
  payloads; the fix is to stop rewriting no-op renders, not to force timestamps
  to rotate on every run.

- Preflight Checks: Inspect stable-timestamp helpers and every sync-owned JSON
  writer that still bypasses `write_if_changed` semantics.

- Regression Tests Added: Pending.

- Monitoring Updates: Watch sync output for truthful "current" messaging on
  repeated no-op runs and for disappearing timestamp mismatches in downstream
  feedback.

- Residual Risk: Other generated artifacts may still need the same no-op write
  audit later.

- Related Incidents/Bugs:
  [CB-065](/Users/freedom/code/odylith/odylith/casebook/bugs/2026-04-07-sync-operator-surface-hides-real-controls-and-long-running-progress.md)

- Version/Build: Odylith `0.1.9` observed on 2026-04-07 during downstream
  consumer sync on macOS Apple Silicon.

- Config/Flags: Default `odylith sync --repo-root .` path.

- Customer Comms: Sync kept the repo healthy, but some generated artifacts were
  pretending to be freshly rewritten when the payload was actually unchanged.
  The fix makes audit timestamps and write messaging tell the same truth.

- Code References:
  `src/odylith/runtime/governance/backfill_workstream_traceability.py`,
  `src/odylith/runtime/governance/delivery_intelligence_engine.py`,
  `src/odylith/runtime/common/stable_generated_utc.py`

- Runbook References: `odylith/INSTALL_AND_UPGRADE_RUNBOOK.md`

- Fix Commit/PR: Pending.
