- Bug ID: CB-290

- Status: Open

- Created: 2026-07-20

- Severity: P2

- Reproducibility: Consistent

- Type: Product

- Description: The 200-case installed Greenfield release corpus passed, but the real installed structured-patch-plan recovery smoke test failed its Atlas quality check because two generated diagrams rendered adjacent duplicate text: review review. This prevents a release-readiness claim.

- Impact: A confirmed Greenfield recovery package can contain visibly degraded Atlas prose, so the release-quality gate correctly rejects the package after compile.

- Components Affected: odylith

- Environment(s): Fresh installed 0.1.15 artifact, release-proof campaign

- Detected By: Installed 200-case release proof

- Failure Signature: Atlas Mermaid adjacent duplicate word review review in component-boundaries and system-context diagrams

- Trigger Path: bin/greenfield-matrix-campaign 0.1.15 /tmp/odylith-greenfield-v17-release-dist

- Ownership: Greenfield governed artifact compiler

- Timeline: Captured 2026-07-20 through `odylith bug capture`.

- Blast Radius: Structured patch-plan recovery flows that create Atlas labels with repeated review terms

- SLO/SLA Impact: Blocks Greenfield release-readiness until corrected

- Data Risk: No data loss; rejected before release claim

- Security/Compliance: Accessibility: duplicated Atlas label prose degrades diagram readability; no security, privacy, or policy breach observed.

- Invariant Violated: Generated governed Atlas prose must be artifact-quality clean before it can be sealed for confirmation

- Rollback/Forward Fix: Forward fix the label construction and rerun the installed release proof; do not hand-edit consumer artifacts

- Verification: Add a regression for repeated review label construction and rerun the installed structured-patch-plan recovery proof and release corpus

- Prevention: Normalize adjacent duplicate tokens in the single Atlas label construction path before quality validation

- Agent Guardrails: Treat full-corpus aggregate success as insufficient until ancillary recovery and rendered-artifact checks also pass

- Preflight Checks: Focused regression, runtime intent suites, installed recovery smoke, and release corpus

- Version/Build: 0.1.15 local release artifact

- Config/Flags: GREENFIELD_MATRIX_REQUIRE_HIGH_VARIANCE_STRESSORS=1

- Code References: - src/odylith/runtime/domain_intelligence
