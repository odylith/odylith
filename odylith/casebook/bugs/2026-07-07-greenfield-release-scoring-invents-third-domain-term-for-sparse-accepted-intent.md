- Bug ID: CB-222

- Status: Open

- Created: 2026-07-07

- Severity: P1

- Reproducibility: Always

- Type: Test

- Description: Installed failed-subset replay after the next-step preservation fix completed post-confirm create with governed records written, but release-matrix scoring failed the domain-expert lens because the scorer required at least three domain term hits even though the case declared exactly two accepted required terms, grammar and lesson, and both were grounded across governed artifacts.

- Impact: Sparse but valid product intents can complete post-confirm writes and still score 0/10 in installed release proof, blocking release readiness despite all accepted required terms being preserved.

- Components Affected: domain-intelligence

- Environment(s): Maintainer installed local-release v0.1.15 dist eb284dd7 on 2026-07-07

- Detected By: Exact failed-subset replay under /private/tmp/odv120-eb284dd7-exact-replay

- Failure Signature: domain term coverage too low: expected at least 3, found 2; domain_expert release-matrix lens failed; governed records written radar=4 registry=3 atlas=6 trace_nodes=18

- Trigger Path: greenfield_matrix_campaign_runner.py failed-subset replay of hv-20260707-word-sense-mixed-tail-001 against local-release eb284dd7

- Ownership: Installed greenfield release-matrix scoring and auto-rescue domain-term coverage threshold

- Timeline: Captured 2026-07-07 through `odylith bug capture`.

- Blast Radius: Sparse, short, edited, or normalized accepted intents with fewer than three declared required terms but complete grounding of every accepted required term.

- SLO/SLA Impact: Blocks release readiness after post-confirm succeeds and risks misclassifying valid sparse projects as failed quality proof.

- Data Risk: No private-data exposure observed; risk is false release-proof failure and retained temporary evidence.

- Security/Compliance: No direct security exposure observed; scientific or regulated sparse intents can be blocked by invented scoring requirements.

- Invariant Violated: Release scoring must prove accepted required product terms survive; it must not require invented domain terms that were not accepted as product truth.

- Root Cause: The release-matrix domain-term threshold used max(3, required_domain_terms), mixing a generic depth guard with declared case-term preservation. Sparse cases with two declared required terms could never satisfy the invented third term even when both accepted terms were grounded.

- Solution: Require all declared required terms when required_domain_terms is positive; keep the three-term floor only when no required terms are declared, and route auto-rescue smoke through the shared threshold helper.

- Rollback/Forward Fix: Forward fix only. Do not mutate generated projects or add domain-specific vocabulary to make the sparse case pass.

- Verification: Focused scorer regressions plus exact installed failed-subset replay against a rebuilt local release, followed by the retained word-sense replay and broader volume proof.

- Prevention: Keep release scoring thresholds derived from accepted case facts, not arbitrary extra domain terms; add sparse declared-term regression coverage.

- Agent Guardrails: When a replay declares fewer than three required terms, do not synthesize additional terms for scoring; inspect whether all declared accepted terms are grounded.

- Preflight Checks: Run tests/unit/install/test_greenfield_post_confirm_matrix.py declared-domain-term regressions before rebuilding the dist.

- Regression Tests Added: tests/unit/install/test_greenfield_post_confirm_matrix.py::test_quality_verdict_accepts_sparse_case_when_all_declared_domain_terms_survive

- Monitoring Updates: Retain the exact failed-subset replay cluster domain.term.coverage.too.low.expected.least.found until the rebuilt dist passes.

- Version/Build: 0.1.15 local-release eb284dd7 failure; fixed by pending follow-up commit

- Config/Flags: Provider-free installed failed-subset replay; failed-subset max workers 1; stop after first failure

- Customer Comms: Internal maintainer evidence only until fixed release proof passes.

- Related Incidents/Bugs: CB-221, CB-209, B-142

- GitHub Status: needs_info

- Public Response: pending

- Code References: - scripts/release/greenfield_matrix_quality_scoring.py
- scripts/release/greenfield_rescue_smoke.py
- tests/unit/install/test_greenfield_post_confirm_matrix.py
