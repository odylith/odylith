- Bug ID: CB-245

- Status: Open

- Created: 2026-07-14

- Severity: P2

- Reproducibility: Consistent

- Type: DataLoss

- Description: Two Greenfield create processes could validate the same pre-confirm repository state, then one overwrite the other's managed update during an unlocked write loop.

- Impact: Concurrent operators can lose a managed update even though both transactions passed their original preconditions.

- Components Affected: domain-intelligence

- Environment(s): Product-repo source-local and installed consumer repositories with concurrent Greenfield create commands.

- Detected By: Adversarial transaction review

- Failure Signature: A concurrent write after the precondition snapshot can be overwritten by a later sealed write without an explicit busy failure.

- Trigger Path: Compile two ProductCreateTransactions against one repo, then confirm both concurrently.

- Ownership: Greenfield ProductCreateTransaction commit boundary

- Timeline: Captured 2026-07-14 through `odylith bug capture`.

- Blast Radius: Every repository using concurrent Greenfield create commands.

- SLO/SLA Impact: Violates the atomic commit-only expectation under concurrent operator activity.

- Data Risk: A concurrent managed update can be silently lost; rollback cannot restore an update it never observed.

- Security/Compliance: Security posture: no privilege escalation; integrity and auditability are affected.

- Invariant Violated: A confirmed create must not overwrite a managed change made after its compiled precondition snapshot.

- Root Cause: The commit path checked preconditions before an unlocked multi-file materialization loop.

- Solution: Serialize cooperating Greenfield creates with a repository lock and recheck preconditions inside the lock before the rollback-protected write boundary.

- Rollback/Forward Fix: Forward fix; do not weaken post-confirm precondition checks.

- Verification: Unit coverage forces lock contention and proves the transaction fails before compiled writes.

- Prevention: Keep lock acquisition and precondition validation inside one commit-only boundary.

- Agent Guardrails: Treat concurrent writer review as required for any transaction that claims atomic post-confirm commit semantics.

- Preflight Checks: Run Greenfield commit contention and rollback tests before release.

- Regression Tests Added: test_commit_product_create_transaction_rejects_busy_repository_before_write

- Version/Build: 0.1.15 source release candidate

- Related Incidents/Bugs: CB-244

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_commit.py
- tests/unit/runtime/test_greenfield_create_transaction.py
