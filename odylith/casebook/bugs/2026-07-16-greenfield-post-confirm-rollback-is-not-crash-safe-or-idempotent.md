- Bug ID: CB-261

- Status: Open

- Created: 2026-07-16

- Severity: P0

- Reproducibility: Always

- Type: DataLoss

- Description: The confirmed Greenfield create path keeps its rollback snapshot only in a process-local temporary directory and has no durable commit journal or restart recovery. SIGKILL, power loss, or transport loss after a successful apply can leave partial governed writes or make the same hash-bound confirmation fail as repository drift.

- Impact: A user-confirmed create can leave partial governed source truth after hard process loss, and an ambiguous successful commit cannot be retried safely with the same transaction hash.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith product-repo Greenfield commit-only create path

- Detected By: Adversarial crash and retry audit

- Failure Signature: SIGKILL or power loss during sealed write-set apply leaves only a volatile tempfile snapshot; repeated create with the same transaction hash has no committed receipt and fails precondition drift.

- Trigger Path: Compile a ProductCreateTransaction, force process loss during greenfield create --confirm, then retry the same transaction-file and transaction-hash.

- Ownership: Greenfield precompiled create transaction kernel

- Timeline: Captured 2026-07-16 through `odylith bug capture`.

- Blast Radius: All Greenfield confirmation flows and every governed surface in their sealed write set.

- SLO/SLA Impact: Violates the non-negotiable deterministic post-confirm success and rollback guarantee.

- Data Risk: Partial Radar, Registry, Atlas, brief, prompt, or traceability writes can survive a hard process loss.

- Security/Compliance: Repository integrity and auditability control failure; no credential exposure is required for impact.

- Invariant Violated: Post-confirm must commit atomically or cleanly recover from true environment/IO failure with no partial governed writes, and the same confirmed transaction must be retry-safe.

- Root Cause: Rollback snapshots are created with tempfile.mkdtemp, only graceful signals are guarded, directory fsync errors are suppressed, and no hash-keyed journal records applying or committed state.

- Solution: Add a repo-local fsynced write-ahead journal with durable snapshots, restart recovery, committed receipt validation, and same-hash idempotent success before broadening the transaction architecture.

- Rollback/Forward Fix: Forward fix only; preserve current sealed write-set and pre-confirm quality boundaries.

- Verification: Kill a child process during the first sealed write, recover on the next create, verify no partial writes; retry an already committed transaction and require idempotent success; inject fsync failure and require environment/IO failure.

- Prevention: Release proof must include hard-crash recovery, exact same-hash retry, and fsync-failure tests in addition to graceful rollback proof.

- Agent Guardrails: Do not call a process-local snapshot atomic; do not claim retry safety from a fresh propose-and-create rerun.

- Preflight Checks: Before release readiness, prove journal recovery, committed receipt readback, exact same-hash retry, and failure-closed fsync behavior.

- Monitoring Updates: Persist journal phase, transaction hash, write-set hash, recovery outcome, and committed receipt in post-confirm proof.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- Related Incidents/Bugs: CB-229, CB-243, CB-249

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_create_commit.py
- src/odylith/install/fs.py

- Delete-Phase Rollback Verification (2026-07-17): The write-set and journal proof now cover the missing delete phase. A mixed transaction first replaces a governed file, deletes a prior governed file, then receives an injected directory-delete error; `GreenfieldApplyTransaction` restores the changed file, deleted file, and removed empty directory, and recovery preconditions match the complete pre-confirm state. A separate child-process proof performs one sealed write, deletes the first of two governed files, receives SIGKILL before the second deletion, and `GreenfieldCommitJournal` recovery restores the changed file plus both deleted files before retry. Focused repository write-set and journal proof passed `34` tests. This proves the controlled exception and partial-crash branches for delete operations; it is not yet installed release proof. Failed mechanisms to avoid: do not infer atomicity from write-only rollback tests; do not kill a test process after its final mutation and call the durable after-state a partial failure; do not accept a retry until recovery has read back the full pre-confirm fingerprint boundary.

- Snapshot-Integrity Verification (2026-08-02): Adversarial review found that
  rollback could report success after a snapshot file disappeared because the
  restore loop only visited files still present. The transaction guard now
  persists `.snapshot-manifest.v1.json` with the exact affected-path inventory,
  present/missing state, modes, and SHA-256 fingerprints. Recovery validates
  the complete manifest before changing the repository and validates restored
  readback afterward. Missing, unexpected, or corrupt snapshot material yields
  `rollback_failed` and retains the recovery directory. Rollback, journal, and
  write-boundary proof passed `45` tests. Hard-crash clean-install proof remains
  a release gate, so CB-261 stays open.
