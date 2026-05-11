- Bug ID: CB-197

- Status: Open

- Created: 2026-05-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield umbrella workstream described governance spine instead of business problem

- Impact: Greenfield Radar B-001 can lead with Odylith traceability mechanics instead of the actual product or business problem, making the first project record feel fake and misdirecting downstream workstreams, diagrams, components, and the Project tab.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo greenfield proposal/apply path; observed in local consumer mockrepo after applying an SMB merchant-capital greenfield proposal.

- Detected By: User screenshot of mockrepo Radar B-001 plus source inspection of proposal_scaffold umbrella row generation.

- Failure Signature: B-001 Problem said the project needs an accepted execution spine before source exists instead of explaining the merchant funding problem, customer, risk, and proof path.

- Trigger Path: odylith greenfield create --repo-root <empty repo> --prompt '<greenfield project intent>' --release 0.0.1 --confirm, then open Radar B-001.

- Ownership: Domain Intelligence greenfield proposal scaffold and Radar projection boundary.

- Timeline: Captured 2026-05-11 through `odylith bug capture`.

- Blast Radius: Greenfield umbrella workstreams, Radar detail, Project tab accepted-project projection, component and diagram derivation story for proposal-first repos.

- SLO/SLA Impact: Trust and comprehension regression before first implementation; operators cannot rely on B-001 as the project spine until the umbrella row is domain-shaped.

- Data Risk: No production data loss; governance records may persist misleading project intent in consumer repos generated before the fix.

- Security/Compliance: No direct security breach; regulated-domain proposals can understate compliance, custody, loss-owner, and proof boundaries if the parent problem is generic.

- Invariant Violated: Greenfield project records must start from project intelligence and domain truth, not Odylith-internal governance mechanics.

- Root Cause: The umbrella B-001 row still used a generic governance bootstrap fallback while child workstreams used domain intelligence.

- Solution: Generate umbrella B-001 fields from domain-profile umbrella terms so the parent problem, customer, opportunity, product view, first slice, risks, validation, and interfaces are domain-shaped.

- Verification: pytest tests/unit/runtime/test_project_intelligence.py tests/unit/runtime/test_greenfield_proposals.py -q

- Prevention: Keep regression tests asserting B-001 does not contain generic governance-spine language or repeat the raw prompt, and that accepted greenfield projects feed Project tab from accepted-project plus Tribunal evidence.

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- tests/unit/runtime/test_project_intelligence.py
- tests/unit/runtime/test_greenfield_proposals.py
