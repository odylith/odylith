- Bug ID: CB-325

- Status: Open

- Created: 2026-09-02

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The installed recovery proof cloned one sealed transaction and its byte-identical runtime into isolated fault-phase repositories, but confirmation rejected the clone before fault injection because compiler identity included absolute source paths.

- Impact: The release gate could not exercise SIGKILL, operator-conflict, or fsync recovery against the frozen transaction, so transaction-safety completion evidence remained unavailable.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Immutable local distribution ced54a967; exact public v8 installed matrix; cloned recovery phase repositories.

- Detected By: Frozen public release matrix commit-recovery proof.

- Failure Signature: Create returned code 2 with ProductCreateTransaction post-confirm runtime changed after pre-confirm compilation instead of terminating at the injected SIGKILL boundary.

- Trigger Path: Compile in sealed-transaction-seed, copy the fully installed seed to sigkill-same-hash, then run installed greenfield create --confirm.

- Ownership: Greenfield post-confirm compiler identity and installed recovery release proof.

- Timeline: Captured 2026-09-02 through `odylith bug capture`.

- Blast Radius: Relocated byte-identical installed runtimes and the release recovery gate; ordinary same-path confirmation remains fail-closed.

- SLO/SLA Impact: No proposal budget breach, but the 60/90/120 release evidence package cannot pass while recovery aborts before fault injection.

- Data Risk: No governed data was written because the identity guard rejected before the write boundary.

- Security/Compliance: Security posture remains fail-closed with no secret or access exposure; compliance and audit integrity are preserved, but location-dependent code identity causes a false rejection.

- Invariant Violated: Byte-identical post-confirm runtimes must have one stable compiler identity across install roots, while any covered source-byte drift must invalidate confirmation.

- Root Cause: The shared source fingerprint included each resolved absolute filesystem path alongside its content digest.

- Solution: Hash the fixed logical post-confirm source names and their bytes, bump the identity contract to v5, and retain source-byte drift rejection.

- Rollback/Forward Fix: Forward-fix the identity calculation; do not weaken receipt verification or rewrite sealed receipts in the proof.

- Verification: Focused provenance and recovery tests pass 49/49; full Greenfield runtime passes 611 and full Greenfield install/release passes 459. Immutable installed recovery proof remains required.

- Prevention: Every runtime identity must distinguish semantic code bytes from deployment location and carry a relocation plus mutation regression.

- Agent Guardrails: Do not repair recovery proof by regenerating per-phase transactions, rewriting compiler receipts, or weakening the post-confirm drift guard.

- Preflight Checks: Require identical logical-file fingerprint across two roots, changed-byte inequality, prewrite drift rejection, and the unchanged installed crash-recovery proof.

- Regression Tests Added: test_compiler_identity_is_stable_across_identical_install_roots proves relocation stability and content-drift sensitivity.

- Version/Build: source candidate after 824cf48eb; compiler identity v5

- Related Incidents/Bugs: CB-303, CB-271, CB-273, B-142

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_commit_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_create_contract.py
- scripts/release/greenfield_commit_recovery_proof.py
