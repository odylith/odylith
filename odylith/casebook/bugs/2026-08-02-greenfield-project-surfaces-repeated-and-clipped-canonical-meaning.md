- Bug ID: CB-303

- Status: Open

- Created: 2026-08-02

- Severity: P1

- Reproducibility: Consistent

- Type: OperatorUX

- Description: A generated Greenfield Project view reused one completion sentence for first path, product boundary, owned capabilities, and proof, while other public sentences ended as clipped fragments. The package passed artifact-completeness checks even though the result was difficult to comprehend.

- Impact: First-time users receive a polished-looking workspace whose core product story is repetitive, incomplete, and not trustworthy enough to guide implementation.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith 0.1.15 Greenfield Project and generated governance surfaces

- Detected By: Operator review of a clean installed Greenfield project plus adversarial source and browser review

- Failure Signature: Distinct Product Story slots render identical completion copy; public outcome and contract sentences terminate in fragments or presentation wrappers.

- Trigger Path: Compile and confirm a domain-rich Greenfield prompt, open the generated Project view, and compare problem, first path, product boundary, owned capabilities, proof, and component contracts.

- Ownership: Greenfield pre-confirm canonical meaning and projection quality

- Timeline: Observed 2026-08-01 in a generated consumer project; fixed in the Phase 2 source checkpoint before release packaging.

- Blast Radius: Any Greenfield proposal whose semantic fallbacks collapse distinct slots or whose compactors cut public sentences.

- SLO/SLA Impact: Violates the hard user-comprehension and generated-copy quality gate before confirmation.

- Data Risk: No source-data loss, but semantic compression can misdirect all subsequently generated governance and implementation work.

- Security/Compliance: No direct security exposure; reviewability and audit confidence are degraded.

- Invariant Violated: Every visible semantic slot must project a complete, distinct, source-grounded claim from the sealed pre-confirm package.

- Root Cause: Canonical meaning was fragmented across fallback helpers, slot distinctness was not enforced, complete-sentence compactors could cut accepted clauses, internal patch ledgers entered public prose scans, and component visible-result wrappers could become artifact contracts.

- Solution: Centralize canonical semantic-slot ownership, preserve complete public sentences, reject cross-slot repetition and fragments before confirmation, exclude internal ledgers from public prose, and strip presentation wrappers before component contract projection.

- Rollback/Forward Fix: Forward fix only; EDIT rebuild remains the user correction path and post-confirm generation stays forbidden.

- Verification: Run proposal, CLI, artifact-quality, Project-browser, component-contract, anti-slop, and high-variance action suites; require normal, mobile, empty, and degraded browser proof in the release gate.

- Prevention: Keep atomic semantic-slot annotations, cross-surface repetition checks, complete-sentence checks, and browser layout assertions in the maintained Greenfield release corpus.

- Agent Guardrails: Do not repair rendered prose after confirmation, do not satisfy length limits by cutting sentences, and do not let one generic completion sentence stand in for multiple product contracts.

- Preflight Checks: Before release, prove the frozen corpus, unseen holdout, cross-host adapters, clean install, full browser matrix, and generated readback.

- Regression Tests Added: Added canonical-meaning, repetition, component-contract, Project-browser, transaction, source-casing, and high-variance first-path regressions.

- Monitoring Updates: Release scoring must report repetition, fragment, slot-coverage, comprehension, and browser-overflow findings separately.

- Version/Build: 0.1.15 branch 2026/freedom/v0.1.15

- Related Incidents/Bugs: CB-207, CB-214, CB-260, CB-261

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_canonical_meaning.py
- src/odylith/runtime/project_intelligence/product_story.py
- src/odylith/runtime/domain_intelligence/greenfield_component_contract_quality.py
