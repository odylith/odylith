- Bug ID: CB-313

- Status: Open

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Test

- Description: The semantic final-holdout campaign passes sealed-input preflight but commit-recovery case selection still treats proof_tier=release as synonymous with source-provenanced audit evidence. It rejects the hash-bound semantic holdout before the one-shot ledger claim even though the downstream recovery runner already disables source-audit binding for semantic release.

- Impact: Blocks all final semantic holdout execution and release-readiness proof after the maintained installed matrix passes.

- Components Affected: greenfield-governance

- Environment(s): Odylith 0.1.15 final semantic holdout campaign at pushed commit 751b8f82a

- Detected By: First sealed campaign pre-execution attempt after CB-312

- Failure Signature: RuntimeError: release commit recovery proof requires an approved audit binding

- Trigger Path: Run the release-tier matrix with semantic annotations, frozen evaluation manifest, commit recovery enabled, no source-corpus audit, and a fresh one-shot ledger.

- Ownership: Greenfield commit-recovery case selection and matrix release evidence routing

- Timeline: Observed 2026-08-04 after sealed input validation and before before_product_execution; ledger absent and holdout SHA-256 unchanged.

- Blast Radius: All semantic final-holdout release campaigns; source-provenanced release campaigns and discovery recovery remain unaffected.

- SLO/SLA Impact: Prevents the final release-quality gate from starting any holdout case.

- Data Risk: No governed project writes and no holdout product executions occurred; the one-shot ledger remained absent.

- Security/Compliance: No security boundary changed; the fix must retain mandatory audited binding for source-provenanced release corpora.

- Invariant Violated: Commit recovery must select a case under the active release evidence class: source audit for source corpora, sealed semantic custody for a frozen holdout.

- Root Cause: select_recovery_case derives binding requirements only from proof_tier and cannot receive the semantic-release exception already used by run_installed_commit_recovery_proof.

- Solution: Compute one recovery binding policy from the active release evidence class and pass it consistently to both case selection and installed recovery execution.

- Rollback/Forward Fix: Forward fix in release proof only; do not skip commit recovery and do not fabricate source audit evidence.

- Verification: Add semantic selection and matrix-forwarding regressions while preserving all existing source-audit rejection tests; rerun campaign and recovery proof suites before another holdout attempt.

- Prevention: Keep one explicit recovery-binding policy shared by selection and execution.

- Agent Guardrails: Never turn off source-audit binding merely because a release run lacks audit data; require the complete semantic release contract.

- Preflight Checks: Confirm ledger /private/tmp/odylith-greenfield-final-holdout-ledger-751b8f82a.v1.json is absent and holdout SHA-256 remains 3558ab3ffe23a285303bdbdcca560cec31fb3eee261e0aa9bc610b9f04f5e2a.

- Regression Tests Added: Extend tests/unit/install/test_greenfield_preconfirm_matrix_proof_scope.py for semantic recovery selection and policy forwarding.

- Monitoring Updates: Campaign failures before ledger claim must remain distinguishable from consumed holdout outcomes.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15 commit 751b8f82a

- Config/Flags: Release tier, semantic annotations, frozen evaluation manifest, commit recovery enabled, no release audit.

- Customer Comms: Internal proof-harness failure; no consumer project affected.

- Related Incidents/Bugs: CB-312, CB-303, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - scripts/release/greenfield_commit_recovery_cases.py
- scripts/release/greenfield_preconfirm_matrix.py
- tests/unit/install/test_greenfield_preconfirm_matrix_proof_scope.py
