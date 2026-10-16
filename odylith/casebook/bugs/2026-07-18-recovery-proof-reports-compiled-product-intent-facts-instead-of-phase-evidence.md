- Bug ID: CB-285

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The installed Greenfield recovery proof populated operator-conflict and fsync Product Intent facts hashes from the compile result. The proof could pass even if the runtime error or durable recovery journal stopped retaining the sealed fact identity.

- Impact: Release evidence could falsely certify cross-phase Product Intent custody after confirmation.

- Components Affected: domain-intelligence

- Environment(s): Installed Greenfield recovery proof

- Detected By: Independent adversarial pre-commit review

- Failure Signature: Operator-conflict and fsync phase facts echo compiled.product_facts_hash instead of an observed runtime receipt or durable journal receipt.

- Trigger Path: greenfield installed pre-confirm matrix commit-recovery proof

- Ownership: Domain Intelligence release-proof boundary

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Every release assessment relying on installed recovery custody evidence

- SLO/SLA Impact: Blocks a truthful recovery-proof checkpoint and release claim.

- Data Risk: No repository data loss observed; audit and provenance evidence is unsound.

- Security/Compliance: No security boundary change; preserves confirmation custody evidence.

- Invariant Violated: Every recovery phase must derive sealed Product Intent identity from the executed runtime receipt or durable journal, not compiler memory.

- Workaround: Do not claim cross-phase custody until each phase reports an observed receipt-bound hash.

- Root Cause: Proof helpers returned compiled.product_facts_hash directly rather than validating phase-owned evidence.

- Solution: Read Product Intent identity from success receipts or the retained applying journal commit result, validate transaction and write-set binding, then compare against the compiled package.

- Rollback/Forward Fix: Forward-fix the proof and tests before commit; no runtime rollback required.

- Verification: Focused recovery proof tests plus fresh installed 14-case matrix with cross-phase observed hashes.

- Prevention: Require adversarial review of any proof field that is copied from compile-time state into a claimed runtime observation.

- Agent Guardrails: Never label a value as phase evidence when it has not crossed the runtime or durable-state boundary.

- Preflight Checks: Inspect each proof fact source and reject compile-memory echoes for runtime claims.

- Regression Tests Added: Journal-receipt and retry-receipt source tests; mismatch and missing-receipt failures.

- Monitoring Updates: Persist the observed per-phase source in the matrix proof receipt.

- Version/Build: 0.1.15 working tree

- Config/Flags: local installed release proof

- Customer Comms: Internal correctness fix; no customer notice required.

- Related Incidents/Bugs: CB-261, CB-276

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_commit_recovery_proof.py
- tests/unit/install/test_greenfield_commit_recovery_proof.py
