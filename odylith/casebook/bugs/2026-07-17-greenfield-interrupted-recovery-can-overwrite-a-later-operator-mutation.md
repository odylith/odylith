- Bug ID: CB-263

- Status: Open

- Created: 2026-07-17

- Severity: P0

- Reproducibility: Always

- Type: DataLoss

- Description: An applying Greenfield create journal treats every non-final repository state as safe to roll back. A later operator mutation to a managed write target is therefore restored over by the retained snapshot.

- Impact: A post-confirm recovery can overwrite a valid later operator edit in a governed managed path.

- Components Affected: odylith

- Environment(s): Product-repo maintainer runtime journal recovery

- Detected By: Adversarial recovery review with disposable reproduction

- Failure Signature: recover_or_return_committed restores a snapshot after a conflicting operator mutation

- Trigger Path: Interrupted applying journal followed by a later managed-file mutation and Greenfield recovery

- Ownership: Greenfield commit journal and repository write-set boundary

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Any Greenfield create transaction stranded in applying state

- SLO/SLA Impact: Recovery must fail closed rather than silently restore over unknown bytes.

- Data Risk: High: a valid operator mutation can be lost.

- Security/Compliance: Safety and integrity posture is affected because recovery can silently destroy a later approved governed-record mutation; no known authorization bypass.

- Invariant Violated: Automatic rollback may only restore a proved-safe interrupted write state and must preserve unknown concurrent mutations.

- Workaround: Do not run automatic recovery; preserve the journal and manually inspect the repository.

- Root Cause: The journal stores whole-tree before and after fingerprints but does not verify that the current partial state contains only sealed before or after bytes before restoring.

- Solution: Verify every snapshot-owned path is an allowed sealed before or after state before rollback; otherwise raise a typed recovery-conflict error without writes.

- Rollback/Forward Fix: Forward-fix with a focused regression test; no automated rollback is allowed for conflicting live bytes.

- Verification: Seed applying state, replace a managed target with distinct operator bytes, recover, and assert a typed conflict while those bytes remain unchanged.

- Prevention: Adversarial recovery tests must include third-party mutations, not only clean partial writes.

- Agent Guardrails: Never classify arbitrary non-final state as rollback-safe; prove the state is composed solely of sealed before or after values.

- Preflight Checks: Run the journal crash, retry, partial-apply, and conflict-preservation tests before release.

- Related Incidents/Bugs: CB-261

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_commit_journal.py
- src/odylith/runtime/domain_intelligence/greenfield_transaction.py
- tests/unit/runtime/test_greenfield_commit_journal.py
