- Bug ID: CB-272

- Status: Open

- Created: 2026-07-17

- Severity: P1

- Reproducibility: Always

- Type: Tooling

- Description: The shipped Greenfield materiality module included the protected scenario term booking in its generic scope vocabulary, causing candidate-wheel platform-domain leakage failure before installed proof.

- Impact: Fresh candidate packages cannot pass domain-custody validation or reach installed consumer proof.

- Components Affected: domain-intelligence

- Environment(s): Local 0.1.15 release asset build from committed head af105e7e4.

- Detected By: Platform-domain leakage gate during local-release-assets.

- Failure Signature: platform domain leakage check failed: greenfield_prompt_intent_materiality.py leaked booking in source, wheel, and all runtime archives.

- Trigger Path: Build local-release-assets from the candidate source and run package leakage validation.

- Ownership: Domain Intelligence shipped heuristic vocabulary and release-custody gate.

- Timeline: Captured 2026-07-17 through `odylith bug capture`.

- Blast Radius: Any package built from this source; user behavior is unaffected because the rejected term is not required for the conservative materiality threshold.

- SLO/SLA Impact: Blocks candidate packaging and delays installed-runtime acceptance proof.

- Data Risk: No user data loss; package custody failure caught before distribution.

- Security/Compliance: No credential exposure; public product surface carries forbidden scenario vocabulary.

- Invariant Violated: Shipped Greenfield heuristics must use domain-neutral vocabulary and contain no protected scenario terms.

- Root Cause: A scenario-derived noun was retained in a generic scope term list instead of relying on neutral action and container terms.

- Solution: Remove the protected noun from shipped source and retain it only in test evidence where needed.

- Rollback/Forward Fix: Forward fix before rebuilding the candidate.

- Verification: Run materiality regressions and local-release-assets platform-domain leakage validation on the rebuilt wheel and runtime archives.

- Prevention: Treat release leakage findings as source-owner fixes; do not add domain exceptions or weaken the package-custody scan.

- Agent Guardrails: Never place evaluation scenario vocabulary in public Greenfield runtime heuristics.

- Preflight Checks: Run platform-domain leakage validation before counting installed matrix proof.

- Monitoring Updates: Candidate release proof records package leakage results by source, wheel, and runtime archive.

- Version/Build: 0.1.15 commit af105e7e4.

- Config/Flags: Default local-release-assets path.

- Customer Comms: None; caught before distribution.

- Related Incidents/Bugs: CB-220

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materiality.py
- scripts/release/platform_domain_leakage_check.py
