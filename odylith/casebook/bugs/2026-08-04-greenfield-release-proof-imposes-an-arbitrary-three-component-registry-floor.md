- Bug ID: CB-317

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P2

- Reproducibility: Consistent

- Type: Test

- Description: Final holdout case fh-15 compiled and committed a transaction with two declared internal systems and two matching Registry component specs. Independent readback failed only because multiple release-harness paths require at least three components.

- Impact: Valid focused projects are scored as incomplete, encouraging synthetic components and unnecessary first-user cognitive load.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 final private holdout from clean dist 0aac74c63

- Detected By: Adversarial holdout readback review

- Failure Signature: fh-15 commit passed with two accepted component contracts, but release readback reported expected at least 3

- Trigger Path: Greenfield matrix package evidence and quality scoring for a two-component accepted transaction

- Ownership: Release proof governed readback

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: Greenfield projects whose accepted topology has one or two real components

- SLO/SLA Impact: Delivery risk: false-negative release evidence and needless architecture inflation

- Data Risk: Operational risk: no data loss; test incentives can produce synthetic governance records

- Security/Compliance: Domain risk: misleading topology records weaken ownership and audit meaning

- Invariant Violated: Registry proof must validate exact accepted topology coverage, not an unrelated static count

- Root Cause: Release readback, package evidence, and quality scoring duplicate a hardcoded minimum of three components

- Solution: Derive the expected component set from the sealed transaction and require exact preview, spec, contract, and readback coverage

- Verification: Dynamic Registry count regressions passed for accepted two-component topology and continued to reject mismatched coverage. Independent semantic coverage regressions reject a component package that drops an accepted internal-system responsibility while allowing one cohesive component to own multiple accepted responsibilities. The combined anti-clipping, clarification, EDIT, and Registry pack passed 25 tests in 41.89 seconds. Clean installed release proof remains pending.

- Prevention: Do not use universal artifact-count floors where the transaction declares the expected identity set

- Agent Guardrails: Never add synthetic components to satisfy a quality score

- Related Incidents/Bugs: CB-303

- Fixed In: 0.1.15

- Code References: - scripts/release/greenfield_matrix_package_evidence.py
- scripts/release/greenfield_matrix_quality_scoring.py
