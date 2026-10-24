- Bug ID: CB-367

- Status: Open

- Created: 2026-10-24

- Severity: P1

- Reproducibility: Always

- Type: CI

- Description: Canonical candidate run 40111631851 at 6d249fbca9cd8c41d45e6e2e90a72745cd954ce6 passed owner, tag, clean-source and security-version checks, then refused governance sync-component-spec-requirements --check-only because actions/checkout retained the main branch. The wheel, signing and staging steps were skipped.

- Impact: The supported signed-candidate route cannot reach package creation from canonical main.

- Components Affected: release

- Environment(s): GitHub Actions Ubuntu 24.04, Python 3.13.16, release.yml candidate operation at canonical H.

- Detected By: First actual hosted candidate run after full source CI and benchmark gates.

- Failure Signature: Maintainer authoring on main is forbidden; Validate self-host release posture exits 2 before Build one wheel.

- Trigger Path: release.yml default actions/checkout -> governance sync-component-spec-requirements --check-only

- Ownership: Maintainer release workflow checkout and canonical source proof.

- Timeline: Captured 2026-10-24 through `odylith bug capture`.

- Blast Radius: Canonical hosted candidate preparation; no consumer package was built.

- SLO/SLA Impact: Production release blocked before packaging.

- Data Risk: No package bytes, signatures or committed consumer data were changed. The original failed run and empty reservation metadata are retained. Only draft 422845993 was retired after fresh verification that it was unpublished and had zero assets; the reserved tag was left to its normal owner.

- Security/Compliance: Keep canonical actor/ref/tag/hash checks and the main authoring guard unchanged.

- Invariant Violated: Canonical release proof must execute at the exact reserved commit in detached read-only posture.

- Root Cause: The workflow leaves actions/checkout ref implicit, so workflow_dispatch on main checks out that branch while invoking a guarded governance command.

- Solution: Pin the workflow checkout to inputs.expected_sha and prove the detached exact-commit contract without weakening authoring or custody guards.

- Verification: The real-Git regression fails on the original attached-main checkout and passes with the exact commit detached. All 89 focused self-host, custody and dispatch controls pass; independent review has no findings. Clean checkpoint 368e03d21 also passes both Casebook count controls and all eight empty, filtered and invalid-record browser states (99 tests total). Its explicit governance check passes Registry and Atlas but rejects the omitted delivery snapshot as stale. Regenerate that snapshot from the complete clean commit and include it before the next clean check. Actual hosted progression past self-host validation remains required.

- Prevention: Release checkout must explicitly bind the canonical expected commit.

- Agent Guardrails: Do not bypass guards, rebuild a candidate, move a reserved tag or delete its draft without the audited supported recovery contract.

- Related Incidents/Bugs: CB-320; CB-022; CB-347

- Code References: - .github/workflows/release.yml

- Runbook References: - odylith/MAINTAINER_RELEASE_RUNBOOK.md
