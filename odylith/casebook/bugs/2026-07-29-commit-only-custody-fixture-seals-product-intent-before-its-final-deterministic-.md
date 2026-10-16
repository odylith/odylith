- Bug ID: CB-297

- Status: Open

- Created: 2026-07-29

- Severity: P1

- Reproducibility: Consistent

- Type: Test

- Description: The completion-priority custody tests construct a compiled transaction from a proposal whose authority was sealed before final semantic projection. The strict hash binding correctly rejects the mismatch, preventing the tests from reaching their intended post-confirm assertions.

- Impact: Commit-only regression coverage is blocked by a stale fixture instead of proving that post-confirm skips quality and repair work.

- Components Affected: greenfield-commit-only-contract-tests

- Environment(s): Product-repo source-local verification

- Detected By: Completion-priority custody suite

- Failure Signature: proposal facts do not match its sealed Product Intent authority; rebuild the transaction before showing CONFIRM

- Trigger Path: completion-priority fixture -> compile transaction -> strict authority binding

- Ownership: Greenfield transaction test fixtures

- Timeline: Found after strict authority-binding was added and while rerunning the full custody suite.

- Blast Radius: Completion-priority custody tests that use the shared compiled proposal helper

- SLO/SLA Impact: Prevents validation of the post-confirm no-repair contract

- Data Risk: No governed write occurs; strict binding correctly blocks the invalid test transaction

- Security/Compliance: Receipt and audit policy require authority hashes to bind the final typed intent, including deterministic pre-confirm projection.

- Invariant Violated: A test transaction must seal the exact final typed Product Intent that its compiler consumes.

- Workaround: Use a compile-ready fixture that seals after deterministic pre-confirm completion.

- Root Cause: Fixture ordering sealed an earlier intent snapshot before normalisation and deterministic completion changed the typed intent.

- Solution: Move synthetic authority creation to the final test compiler boundary and preserve strict production validation.

- Rollback/Forward Fix: No rollback required; forward-fix test fixture ordering and keep production fail-closed.

- Verification: Run completion-priority custody tests and the complete prewrite, transaction-authority, and installed release matrices.

- Prevention: Shared fixture helpers must model the real proposal -> compile -> seal -> commit sequence.

- Agent Guardrails: Never weaken strict authority binding to accommodate a fixture; make the fixture describe the actual compiled transaction.

- Preflight Checks: Compare product_facts_sha256 to the final proposal intent before compile in shared test helpers.

- Regression Tests Added: Existing completion-priority tests will reach their intended post-confirm assertions after fixture correction.

- Monitoring Updates: Casebook record tracks the test-contract mismatch until matrix proof completes.

- Code References: - tests/unit/runtime/test_greenfield_completion_priority_custody.py
- tests/unit/runtime/greenfield_proposal_fixtures.py
