- Bug ID: CB-227

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-07-10

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The recommended source-local greenfield create performance matrix found content regressions across pattern, child-agency, and GLP-1 intents: source-only whole-product prose survived in generated source truth, a mechanical Let Child Learner Create an Account title survived public output, and a Side-effect label failed expected title normalization. Final adversarial review found two adjacent paths: actorless dashboard-status prose could satisfy concise first-path completion, and terminal This flow works end to end prose could become a product claim.

- Impact: Consumers can receive awkward or source-contaminated project records even though schema, Tribunal, semantic-slop, dashboard, and latency gates report success.

- Components Affected: domain-intelligence

- Environment(s): Product-repo detached source-local posture on branch 2026/freedom/v0.1.15; tests/integration/runtime/test_greenfield_create_performance.py after CB-226 path-custody fix.

- Detected By: Recommended greenfield create performance integration gate; 76 tests passed and three content assertions failed.

- Failure Signature: Pattern generated source retained smallest version of the whole product as product_claim evidence; narrative payload retained Let Child Learner Create an Account; GLP-1 component label rendered Weight and Side-effect Tracking Service instead of Weight and Side Effect Tracking Service. The concise fallback also accepted The dashboard is working and shows project status, while terminal flow-proof prose was classified as product_claim.

- Trigger Path: PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_greenfield_create_performance.py

- Ownership: Domain Intelligence intent evidence classification, child workstream title projection, and component label normalization.

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Greenfield intents with source editorial framing, actor/action child titles, hyphenated mixed-case component labels, or concise first-path language that resembles system status or proof framing.

- SLO/SLA Impact: Latency remains within the 30-second integration threshold, but release readiness is blocked by public-copy and product-truth quality failures.

- Data Risk: No application data loss. Generated governance can persist non-authoritative source prose or low-quality labels as accepted project truth.

- Security/Compliance: No direct credential or regulated-data exposure observed; provenance misclassification can weaken audit clarity about evidence versus product truth.

- Invariant Violated: Untrusted source framing must remain evidence only. A concise first path must express an actor-led product action, and every human-visible generated title or component label must be grammatical, product-specific, and normalized before confirmation.

- Root Cause: Canonical source paragraphs bypassed normalized product-fact custody, so source-only editorial framing could become literal product-claim evidence. The original concise-path shortcut tested coordination without proving an actor-owned action, and the meta classifier missed finite works phrasing. Actor and action selection ran independently, and the incomplete selected actor set then propagated downstream into mechanical child titles. The generic title hyphen policy also had no contextual rule for tracking labels, leaving Side-effect unnormalized.

- Solution: Product intent custody now keeps source_span_ids separate from literal product_claim_span_ids and requires both for every material Markdown fact. Canonical source units remain claims unless the shared first-path meta-control classifier identifies whole-product, smallest-version, or terminal flow-proof framing before projection. The concise completion shortcut now requires an actor-led action in addition to coordinated actions. Actor/action event resolution is centralized, propagates the full actor set through downstream projections, and excludes qualified system subjects such as a routing engine from human workstream titles. Shared title normalization now applies contextual tracking-label normalization without adding domain-specific rendered-string repair.

- Rollback/Forward Fix: Forward fix completed in the current B-142 source-local execution wave; retain the strict copy, provenance, and no-write pre-confirm gates. Installed proof remains required before release closeout.

- Verification: Source-local proof passed the exact three replays, 3 tests in 141.48s; pattern and authority coverage, 26 tests in 69.48s; focused actor, envelope, text, and semantic coverage, 72 tests in 21.81s; the performance file, 13 tests in 876.57s; and the full slop, artifact, and render suite, 198 tests in 198.86s. Adversarial follow-up added literal claim-span authority, qualified-system ownership, actor-led concise-path, terminal-flow-proof, receipt, and atomic-write regressions. The final focused actor/envelope suite passed 30 tests in 13.31s, and the complete current-source performance matrix passed all 13 cases in 698.98s. Fresh installed dist `9606871db` then passed all 14 standard cases at 10/10 with zero issues, browser proof 14/14, platform-leakage and temporary-root cleanup proof, and synthetic/natural rescue. Standard create totals were 37.280-50.035s and commit-only apply was 0.106-0.120s.

- Prevention: Keep exact high-variance source and label fixtures in the performance gate, reject actorless status prose from concise-path completion, classify terminal proof loops as supporting evidence, and require generated source plus visible-surface scans, not only returned payload checks.

- Agent Guardrails: Do not delete evidence blindly, patch rendered files, add domain-specific word lists, or weaken banned-copy assertions. Repair classification and projection owners.

- Preflight Checks: Search CB-198, CB-215, CB-223, and current typed evidence contracts before implementation; rerun exact failing tests first.

- Monitoring Updates: Preserve the exact three-case replay and broader performance matrix as release gates; record a fresh installed dist replay before release readiness.

- Version/Build: 0.1.15 fresh installed dist built from commit 9606871db

- Config/Flags: Default source-local greenfield create path; no feature flag.

- Customer Comms: None before release; defects were caught in maintainer QA.

- Related Incidents/Bugs: CB-198, CB-215, CB-223, CB-226

- Fixed In: 0.1.15 release proof verified; shipment pending

- Code References: - tests/integration/runtime/test_greenfield_create_performance.py
- src/odylith/runtime/domain_intelligence
