- Bug ID: CB-197

- Status: Open

- Created: 2026-05-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield umbrella workstream described governance spine instead of business problem

- Impact: Greenfield Radar B-001 can lead with Odylith traceability mechanics instead of the actual product or business problem, making the first project record feel fake and misdirecting downstream workstreams, diagrams, components, and the Project tab.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo greenfield proposal/apply path; observed in an empty consumer repo after applying an external-domain greenfield proposal.

- Detected By: User screenshot of consumer Radar B-001 plus source inspection of proposal_scaffold umbrella row generation.

- Failure Signature: B-001 Problem said the project needs an accepted execution spine before source exists instead of explaining the business-domain problem, customer, risk, and proof path.

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

## V43 recurrence: every child workstream exposed generator mechanics (2026-09-27)

- Fresh Failure Signature: Independent product-manager review of five immutable
  public packages found that all twenty Radar workstreams used
  `Unimplemented assigned source-event support — Event …` as their Problem.
  The packages preserved actor, action, result, component, and risk meaning,
  but the most prominent workstream field described an internal generator gap
  and opaque event IDs instead of the user's local difficulty.
- Evidence: The finding reproduced across accessibility, civic-tech,
  education, mobility, and research packages. Product-manager review failed
  all five packages; bounded domain-expert review passed all five. This is a
  projection-ownership defect, not evidence that the canonical source facts
  or provisional component design were lost.
- Failed Mechanism: The earlier domain-profile remedy was not a durable
  ownership boundary. The current typed path later replaced vocabulary-based
  domain scaffolding, but its deterministic Radar projection reintroduced the
  same failure class by manufacturing a generic internal-status sentence from
  assigned event numbers.
- Required Correction: Make one model-authored provisional workstream field
  own a concise, consumer-facing local problem grounded in the accepted
  project problem and that workstream's typed source-event support. The
  independent candidate review must reject implementation-status copy,
  opaque event identifiers, deliverable negation, and duplicated workstream
  problems. The deterministic Radar projection must copy that reviewed field
  without reparsing or recomposing it.
- Guardrails: Do not add a domain vocabulary, phrase whitelist, regex, parser,
  problem synthesizer, retry, repair pass, fallback author, or second model
  ladder. Keep exact source events in the Source Event Support custody section
  and keep the local Problem distinct from Customer, Opportunity, Product View,
  and Proof.
- Verification Required: Schema and review-contract tests must require four to
  five distinct local problems; projection tests must prove exact reviewed-copy
  preservation, no generator/event-ID leakage, no project-problem fanout, and
  differentiated Radar fields across high-variance projects. A fresh immutable
  public package and independent product-manager review remain required before
  this recurrence is resolved.
- Current Code References: `src/odylith/runtime/domain_intelligence/greenfield_provisional_design.py`,
  `src/odylith/runtime/domain_intelligence/greenfield_participant_first_authoring.py`,
  `src/odylith/runtime/domain_intelligence/greenfield_candidate_review.py`, and
  `src/odylith/runtime/domain_intelligence/greenfield_provisional_package.py`.
