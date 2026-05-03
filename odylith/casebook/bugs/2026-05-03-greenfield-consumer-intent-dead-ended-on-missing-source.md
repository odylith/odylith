- Bug ID: CB-156

- Status: FixedPendingRelease

- Created: 2026-05-03

- Severity: P1

- Reproducibility: Consistent

- Type: UX

- Description: An empty consumer repo prompt such as Odylith, build an ecommerce site for me could receive a refusal-style response because Odylith treated missing app source as the only admissible path. The correct consumer-lane behavior is proposal-first: generate concrete backlog, program waves, release plan, planned Registry components, draft Atlas topology, assumptions, risks, validation, and confirmation-gated apply commands without claiming source evidence.

- Impact: New consumer-lane operators could not get useful governed project planning from vague but valid greenfield intent, so Odylith appeared rigid instead of intelligent.

- Components Affected: domain-intelligence

- Environment(s): Odylith v0.1.13 development branch in an empty or thin consumer repo posture.

- Detected By: Operator transcript where Odylith show reported no app source and a follow-up ecommerce backlog/Registry/Atlas request was blocked.

- Failure Signature: Agent response said it could not run backlog create, component register, or atlas scaffold against an ecommerce site because no application source existed, without producing a proposal.

- Trigger Path: Odylith, build an ecommerce site; Create a backlog for building an ecommerce site and create all component registry and atlas diagrams.

- Ownership: domain intelligence consumer-lane proposal flow

- Timeline: Captured 2026-05-03 through `odylith bug capture`.

- Blast Radius: Empty and thin consumer repos across Claude, Codex, and future host adapters.

- SLO/SLA Impact: First-session onboarding quality drops because useful governance starts require manual fully formed fields.

- Data Risk: Low source-data risk because writes were blocked; high governed-memory and UX risk because intent was not captured.

- Security/Compliance: No direct security impact; evidence separation must remain intact.

- Invariant Violated: Greenfield user intent is valid proposal evidence, but source-backed governance claims require observed source or confirmation.

- Root Cause: No provider-free domain-intelligence proposal path existed between strict source-backed governance and generic host narration.

- Solution: Add odylith greenfield propose/apply under runtime domain_intelligence as a host-reasoning contract with Odylith-owned evidence separation, proposal validation, program formation, program waves, release plan, user_intent evidence, durable Compass memory on accepted proposals, required host-authored Atlas Mermaid sources, duplicate-topology rejection, and confirmation-gated owned-surface writes.

- Verification: Run greenfield proposal fixtures for ecommerce, science/math, cloud/infra, security/compliance, IoT/instrumentation, CLI/library, acronym-safe simulation prompts, program-formation output, accepted-proposal Compass memory, required host-authored Atlas topology, duplicate-diagram rejection, and provider-free CLI JSON output; run host routing tests proving greenfield prompts avoid noisy raw Observation chatter.

- Prevention: Keep open-world project authorship with the active host model until a real curated domain marketplace exists; keep Odylith responsible for evidence tiers, schema validation, confirmation gates, topology hygiene, owned-surface writes, Compass memory, and regression tests for every newly supported greenfield contract.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py and tests/unit/runtime/test_greenfield_host_routing.py

- Fixed In: 0.1.13
