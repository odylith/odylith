- Bug ID: CB-159

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-03

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: Greenfield Atlas drafts reuse generic star topology

- Impact: Greenfield consumer proposals can create multiple Atlas diagrams that look nearly identical, making system context, program waves, runtime, and validation views feel like low-value copies instead of useful architecture.

- Components Affected: domain-intelligence

- Environment(s): v0.1.13 source-local and local dist greenfield apply output viewed in Atlas dashboard.

- Detected By: Operator screenshots of ecommerce and quantum-information-science greenfield Atlas diagrams.

- Failure Signature: Every applied draft diagram rendered as the same hub-and-spoke flowchart with an owner node, component spokes, and a generic governance follow-up.

- Trigger Path: Run odylith greenfield propose/apply for a greenfield project, then open the generated Atlas diagrams.

- Ownership: Domain Intelligence greenfield Atlas source generation and Atlas scaffold starter-source boundary.

- Timeline: Captured 2026-05-03 through `odylith bug capture`.

- Blast Radius: Empty or thin consumer repos using greenfield proposal apply across Claude, Codex, and host-agnostic CLI paths.

- SLO/SLA Impact: No data loss; substantial onboarding UX and topology-trust degradation.

- Data Risk: None

- Security/Compliance: No direct security impact.

- Invariant Violated: Draft Atlas topology must communicate the actual diagram purpose and domain fit; program waves, system context, runtime, data, and validation diagrams must not collapse into one generic starter shape.

- Root Cause: Greenfield apply passed rich diagram intent to the generic Atlas scaffold, but scaffold only had one fallback Mermaid starter template.

- Solution: Move purpose-specific Mermaid source generation into domain_intelligence and let greenfield apply pass that source to the Atlas scaffold creation path.

- Rollback/Forward Fix: Forward fix in domain intelligence and the Atlas scaffold programmatic boundary; keep generic scaffold fallback for manual Atlas-first drafts.

- Verification: Run focused greenfield proposal/apply tests, Atlas scaffold tests, Casebook validation, Atlas refresh/render proof, and headless Atlas browser smoke.

- Prevention: Test that greenfield system-context, program-waves, runtime/data/validation diagrams produce distinct Mermaid shapes before release.

- Agent Guardrails: Do not call greenfield Atlas good enough when diagrams differ only by title and component labels.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py covers distinct Mermaid source profiles and applied ecommerce system-context versus program-wave files.

- Monitoring Updates: Watch consumer greenfield Atlas screenshots and local dist fresh installs for repeated generic star topology.

- Fixed In: 0.1.13
