- Bug ID: CB-227

- Status: Open

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The recommended source-local greenfield create performance matrix completed every case under 30 seconds but found three content regressions across pattern, child-agency, and GLP-1 intents: source-only whole-product prose survived in generated source truth, a mechanical Let Child Learner Create an Account title survived public output, and a Side-effect label failed expected title normalization.

- Impact: Consumers can receive awkward or source-contaminated project records even though schema, Tribunal, semantic-slop, dashboard, and latency gates report success.

- Components Affected: domain-intelligence

- Environment(s): Product-repo detached source-local posture on branch 2026/freedom/v0.1.15; tests/integration/runtime/test_greenfield_create_performance.py after CB-226 path-custody fix.

- Detected By: Recommended greenfield create performance integration gate; 76 tests passed and three content assertions failed.

- Failure Signature: Pattern generated source retained smallest version of the whole product as product_claim evidence; narrative payload retained Let Child Learner Create an Account; GLP-1 component label rendered Weight and Side-effect Tracking Service instead of Weight and Side Effect Tracking Service.

- Trigger Path: PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_greenfield_create_performance.py

- Ownership: Domain Intelligence intent evidence classification, child workstream title projection, and component label normalization.

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Greenfield intents with source editorial framing, actor/action child titles, or hyphenated mixed-case component labels.

- SLO/SLA Impact: Latency remains within the 30-second integration threshold, but release readiness is blocked by public-copy and product-truth quality failures.

- Data Risk: No application data loss. Generated governance can persist non-authoritative source prose or low-quality labels as accepted project truth.

- Security/Compliance: No direct credential or regulated-data exposure observed; provenance misclassification can weaken audit clarity about evidence versus product truth.

- Invariant Violated: Untrusted source framing must remain evidence only, and every human-visible generated title or component label must be grammatical, product-specific, and normalized before confirmation.

- Root Cause: Investigation pending across typed evidence classification, child-title projection, and shared title-label normalization; the failures are deterministic and the strict gates did not catch them.

- Solution: Trace each escaped phrase to its typed owner, fix source semantics or shared label projection rather than rendered strings, add exact regressions, and replay the performance matrix without lowering copy gates.

- Rollback/Forward Fix: Forward fix in a separate B-142 execution wave; keep current strict tests and no-write pre-confirm posture.

- Verification: Exact failing tests are pattern placeholder/clause drift, narrative action/outcome normalization, and GLP-1 actor/state label drift; all three completed under 30 seconds before their quality assertions failed.

- Prevention: Keep exact high-variance source and label fixtures in the performance gate and require generated source plus visible-surface scans, not only returned payload checks.

- Agent Guardrails: Do not delete evidence blindly, patch rendered files, add domain-specific word lists, or weaken banned-copy assertions. Repair classification and projection owners.

- Preflight Checks: Search CB-198, CB-215, CB-223, and current typed evidence contracts before implementation; rerun exact failing tests first.

- Monitoring Updates: Track exact three-case replay, broader performance matrix, and installed dist replay before release readiness.

- Version/Build: 0.1.15 source-local branch 2026/freedom/v0.1.15 after commit 1b2072f0f

- Config/Flags: Default source-local greenfield create path; no feature flag.

- Customer Comms: None before release; defects were caught in maintainer QA.

- Related Incidents/Bugs: CB-198, CB-215, CB-223, CB-226

- Code References: - tests/integration/runtime/test_greenfield_create_performance.py
- src/odylith/runtime/domain_intelligence
