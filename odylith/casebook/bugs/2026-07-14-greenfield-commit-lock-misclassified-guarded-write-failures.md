- Bug ID: CB-246

- Status: Open

- Created: 2026-07-14

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: The commit-lock context manager caught OSError raised by the guarded compiled write body and rewrote it as a lock-acquisition failure. This hid the rollback outcome and reported not_started even though the rollback guard had entered.

- Impact: A true post-confirm IO failure could be misclassified, obscuring whether governed writes were rolled back.

- Components Affected: domain-intelligence

- Environment(s): source-local release candidate 0.1.15

- Detected By: full regression suite

- Failure Signature: test_commit_product_create_transaction_rolls_back_when_compiled_write_raises: expected rollback_status rolled_back, got not_started

- Trigger Path: greenfield confirmed create with injected compiled-write OSError

- Ownership: Greenfield commit-only transaction kernel

- Timeline: Captured 2026-07-14 through `odylith bug capture`.

- Blast Radius: All Greenfield commits that raise OSError inside the rollback-protected write body

- SLO/SLA Impact: Release gate blocked; rollback reporting becomes unreliable.

- Data Risk: No partial write observed in the regression, but incorrect rollback classification weakens recovery evidence.

- Security/Compliance: Privacy, accessibility, safety, policy, and compliance posture: no impact; the rollback guard remains required to preserve governed write integrity.

- Invariant Violated: Post-confirm environment failures must retain rollback outcome and true failure taxonomy.

- Root Cause: The lock helper wrapped the yield body in an outer OSError handler intended only for lock setup.

- Solution: Limit lock setup error handling to directory/open/flock operations; let body failures propagate through GreenfieldApplyTransaction rollback.

- Rollback/Forward Fix: Forward fix only; no persisted project data migration.

- Verification: tests/unit/runtime/test_greenfield_commit_rollback.py and tests/unit/runtime/test_greenfield_create_transaction.py: 47 passed after the repair; full suite replay required before release.

- Prevention: Keep lock-acquisition exception scopes structurally separate from the guarded write body.

- Agent Guardrails: Do not add broad exception handling around a contextmanager yield when body exception taxonomy is part of a transaction contract.

- Regression Tests Added: Existing rollback regression now covers the lock-wrapped path; contention regression covers repository-busy behavior.

- Version/Build: 0.1.15 candidate

- Related Incidents/Bugs: CB-245

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_commit.py
