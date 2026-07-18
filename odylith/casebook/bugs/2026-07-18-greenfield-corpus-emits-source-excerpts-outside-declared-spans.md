- Bug ID: CB-281

- Status: Open

- Created: 2026-07-18

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: A live source-provenanced corpus evaluation rejects two generated cases because their source excerpts are not present in the declared retained source span: release-healthcare-111-source and release-mobility-136-source. This invalidates the claimed prompt-to-evidence traceability.

- Impact: Release evidence can claim a prompt excerpt is grounded in a retained source span when the validator cannot reproduce that relationship.

- Components Affected: odylith

- Environment(s): Odylith product repo, maintainer source-local release-corpus evaluation

- Detected By: Live source-provenanced corpus evaluation

- Failure Signature: release-healthcare-111-source and release-mobility-136-source fail source_excerpt span containment

- Trigger Path: PYTHONPATH=src:scripts/release python3 evaluate_release_corpus

- Ownership: Greenfield release corpus builder and provenance boundary

- Timeline: Captured 2026-07-18 through `odylith bug capture`.

- Blast Radius: Operational release-proof risk across any generated case whose selected source field is not serialized into its declared source span

- SLO/SLA Impact: Operational delivery is blocked because structural corpus qualification fails before independent audit

- Data Risk: No production data impact; evidence custody and traceability are invalid

- Security/Compliance: No security boundary impact; provenance-integrity evidence is compliance-relevant

- Invariant Violated: Every generated source excerpt must be present in the declared retained source span and hash-bound to that exact evidence.

- Workaround: Do not approve or consume the candidate corpus.

- Root Cause: Undiagnosed builder or capture serialization mismatch in selected source fields.

- Solution: Identify the mismatch, preserve the selected field in the retained span, and prove clean rebuild evaluation.

- Rollback/Forward Fix: Discard the failed candidate corpus and rebuild from corrected retained artifacts.

- Verification: The 200-case evaluation reports no span-containment issues before independent-audit requirements are considered.

- Prevention: Add a generator-level regression that exercises each generated evidence field against its serialized source span.

- Agent Guardrails: Do not treat a derived prompt as traceable merely because its artifact hash exists; verify excerpt-to-span containment.

- Preflight Checks: Run the structural corpus evaluator before audit or release claims.

- Related Incidents/Bugs: CB-279, CB-280
