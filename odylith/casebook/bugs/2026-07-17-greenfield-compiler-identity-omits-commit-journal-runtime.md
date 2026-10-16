- Bug ID: CB-271

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The confirmed Greenfield commit path uses greenfield_commit_journal.py, but compiler provenance does not fingerprint that module. A changed installed runtime can therefore alter post-confirm recovery semantics without invalidating the transaction reviewed before confirmation.

- Impact: An accepted transaction can execute under altered recovery semantics after confirmation.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo, ProductCreateTransaction compiler provenance and commit-only executor.

- Detected By: Independent adversarial post-confirm runtime review.

- Failure Signature: compiler identity accepts a transaction when greenfield_commit_journal.py differs from the compiled runtime provenance set.

- Trigger Path: Compile a ProductCreateTransaction, modify only the commit-journal runtime module in the executor environment, then confirm the unchanged transaction.

- Ownership: Domain Intelligence transaction provenance and commit-only boundary.

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Any confirmed Greenfield create using journal-based recovery.

- SLO/SLA Impact: Weakens the guarantee that CONFIRM commits the exact validated runtime transaction.

- Data Risk: Recovery behavior could differ after confirmation; no observed data loss.

- Security/Compliance: No credential exposure observed; integrity and auditability boundary affected.

- Invariant Violated: Every runtime module capable of changing post-confirm behavior must be bound into compiler provenance before confirmation.

- Root Cause: The fixed compiler identity source-file list was not extended when the commit-journal module became part of the post-confirm executor.

- Solution: Add greenfield_commit_journal.py to the compiler identity inputs and assert all post-confirm modules are fingerprinted.

- Rollback/Forward Fix: Forward fix required before fresh installed-runtime proof.

- Verification: Mutate the commit-journal provenance input in a test and prove commit rejects the stale compiler identity before any write.

- Prevention: Maintain an explicit tested inventory of post-confirm module dependencies in compiler provenance.

- Agent Guardrails: Do not add a post-confirm dependency without adding it to the compiler identity and a provenance regression.

- Preflight Checks: Run transaction provenance and commit-journal suites before release.

- Monitoring Updates: Installed matrix proof records compiler provenance verification.

- Version/Build: 0.1.15 source-local maintainer build.

- Config/Flags: Default confirmed create path.

- Customer Comms: None; caught before release.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_create_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_create_commit.py
- src/odylith/runtime/domain_intelligence/greenfield_commit_journal.py
