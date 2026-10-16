- Bug ID: CB-277

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: The release matrix allocated natural rescue repositories under odylith-greenfield-natural-rescue-* but the aggregate temporary-root cleanup proof did not inspect that namespace. A release proof could report cleanup passed while leaving those repositories on disk.

- Impact: Release-proof cleanup could falsely pass while temporary installed project repositories remain on the operator machine.

- Components Affected: release

- Environment(s): Maintainer local release matrix

- Detected By: Adversarial installed-proof audit

- Failure Signature: temp_cleanup_proof returned passed with an odylith-greenfield-natural-rescue-* root present.

- Trigger Path: Run natural rescue proof, then aggregate temporary-root cleanup validation.

- Ownership: Release proof and Greenfield matrix

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Every release matrix run that exercises natural rescue.

- SLO/SLA Impact: Invalid cleanup evidence can block trustworthy release readiness and consume local disk.

- Data Risk: Temporary governed project content may persist beyond the proof run.

- Security/Compliance: No external exposure; retention of temporary project content violates cleanup expectations.

- Invariant Violated: Every Odylith-created proof root must be detected by aggregate cleanup validation.

- Root Cause: TEMP_CLEANUP_PATTERNS omitted the natural rescue allocation prefix.

- Solution: Add the exact natural rescue prefix to the authoritative cleanup patterns and a regression that creates a leftover root.

- Rollback/Forward Fix: Forward fix only; stale temporary roots are removable after verification.

- Verification: .venv/bin/python -m pytest -q tests/unit/install/test_greenfield_preconfirm_matrix_proof_scope.py -k temp_cleanup_proof

- Prevention: Require each proof allocator namespace to have an aggregate cleanup detection regression.

- Agent Guardrails: Do not accept cleanup proof from a manually maintained pattern list without comparing every allocator prefix.

- Preflight Checks: Run aggregate cleanup regression and an installed release proof before release claims.

- Regression Tests Added: test_temp_cleanup_proof_finds_natural_rescue_leftovers

- Monitoring Updates: Release proof payload now includes the natural rescue pattern in cleanup scope.

- Version/Build: 0.1.15 unreleased

- Config/Flags: No flags

- Customer Comms: None; maintainer-only release proof defect.

- Related Incidents/Bugs: CB-275

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Code References: - scripts/release/greenfield_matrix_proof_scope.py
- tests/unit/install/test_greenfield_preconfirm_matrix_proof_scope.py
