- Bug ID: CB-325

- Status: FixedPendingRelease

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

- Verification: Immutable dist-v14 from candidate `62bcdd8147e47874e984483b48fb1fb0a20ca413` passes the complete installed SIGKILL, operator-conflict, fsync-failure, rollback, recovery, same-hash retry, generation-readback, and public matrix gates.

- Prevention: Every runtime identity must distinguish semantic code bytes from deployment location and carry a relocation plus mutation regression.

- Agent Guardrails: Do not repair recovery proof by regenerating per-phase transactions, rewriting compiler receipts, or weakening the post-confirm drift guard.

- Preflight Checks: Require identical logical-file fingerprint across two roots, changed-byte inequality, prewrite drift rejection, and the unchanged installed crash-recovery proof.

- Regression Tests Added: test_compiler_identity_is_stable_across_identical_install_roots proves relocation stability and content-drift sensitivity.

- Version/Build: source candidate after 824cf48eb; compiler identity v5

- Related Incidents/Bugs: CB-303, CB-271, CB-273, B-142

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_commit_transaction.py
- src/odylith/runtime/domain_intelligence/greenfield_create_contract.py
- scripts/release/greenfield_commit_recovery_proof.py

- Exact Installed V10 Reopen (2026-09-02): Immutable clean candidate `f26925486` crossed model authoring and transaction staging, then its isolated SIGKILL phase failed closed before fault injection because compiler provenance still compared `repo_root_fingerprint` as the SHA-256 of the absolute checkout path. No governed write occurred. Identity v5 correctly removed absolute paths from the runtime-source fingerprint, but an adjacent provenance field retained the same location-dependent assumption. The repository write set already seals and verifies every managed before-fingerprint plus the active generation identity, so the path digest adds false location coupling without protecting repository state. Replace it with an explicit stable repository-context policy marker, retain the exact write-set and active-generation preconditions, bump compiler identity, and prove both relocation success and repository-content drift rejection before rerunning the installed fault phases. Do not regenerate the transaction per phase, rewrite receipts, or weaken preconditions.

- Repository-Context Source Resolution (2026-09-02): Compiler identity v6 removes the last absolute checkout digest from compiler provenance and records the stable `sealed_managed_fingerprints_and_active_generation_v1` repository-context policy instead. The transaction still seals the complete write-set hash, managed before-fingerprints, active generation, runtime source bytes, transaction bytes, and compiler receipt; changed repository content still rejects before writing. A copied sealed transaction now validates under a relocated repo root, while runtime mutation and managed-source drift controls remain fail-closed. Focused provenance, repository-write-set, and recovery tests pass `65/65`; complete Greenfield runtime and install suites pass `614/614` and `459/459`. Immutable installed SIGKILL, conflict, fsync rollback, same-hash retry, and readback proof remain required before closing CB-325.

- Exact Installed V13 Clone Reopen (2026-09-03): Clean immutable dist-v13 at
  `154d0730789829442e9776f2f8f855939e3def52` crossed authoring, staging, and
  the injected SIGKILL boundary, then the recovery invocation stopped because
  the cloned launcher classified its runtime as untrusted. The recovery harness
  used default `copytree` behavior, which dereferenced the seed's active-runtime
  symlink into a directory named `current`; the launcher therefore could not
  resolve the version-keyed trust record. This is a proof-clone defect, not a
  product-runtime or semantic-model defect. The phase-local clone now preserves
  symlinks, validates that the seed's active runtime is exactly one managed
  version, and rebinds `current` to the copied phase-local version before any
  fault execution. An external runtime target still fails closed. Focused
  recovery proof passes `20/20`, complete Greenfield runtime passes `618/618`,
  and install/release passes `460/460`. The corrected source harness reaches
  installed model authoring; immutable fault-phase proof remains required.

- Immutable Installed V14 Verification (2026-09-03): Clean dist-v14 from
  candidate `62bcdd8147e47874e984483b48fb1fb0a20ca413` passes the complete
  installed recovery proof with no issues. SIGKILL terminates the active commit
  at return code `-9` after a governed generation is present; its journal moves
  from `projecting` to `closed` on recovery, and both recovery and same-hash
  retry return `0`. The operator-conflict phase returns `2` with
  `post_confirm_commit_recovery_conflict`, preserves the operator mutation and
  recovery snapshot, keeps the recovery path bound, and does not begin
  rollback. The injected fsync failure returns `2` with the expected
  environment/I/O classification, records `aborted`, then closes on a retry
  that returns `0`; its same-hash retry also returns `0`. All three phases bind
  the identical Product Intent facts hash
  `5918a4652ea062abc0e73e8542d66cf891f032f35b7bddc5f3df2b0092ae8b50`,
  and the runtime is the phase-local managed `0.1.15` install. CB-325 is fixed
  pending release; receipt verification and fail-closed conflict behavior were
  not weakened.
