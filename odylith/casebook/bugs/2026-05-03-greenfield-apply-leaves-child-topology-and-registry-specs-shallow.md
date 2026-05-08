- Bug ID: CB-160

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-03

- Severity: P2

- Reproducibility: Always

- Type: UX

- Description: After a confirmed greenfield apply in v0.1.13, the umbrella backlog carried topology but child workstreams did not receive related Atlas diagram IDs, Atlas diagrams related only to the umbrella backlog, and planned Registry component specs were generic templates that ignored host-authored responsibility. Child workstream details also stayed close to core sections instead of carrying topology, validation, impacted components, dependencies, and interface expectations.

- Impact: Greenfield users see many generated governance records, but follow-on agent sessions cannot reliably navigate from child Radar workstreams to Atlas topology or from Registry components to useful planned ownership detail.

- Components Affected: domain-intelligence

- Environment(s): Installed Odylith v0.1.13 consumer repo using greenfield propose/apply, reproduced in product source tests.

- Detected By: Operator transcript from a cognitive memory AI research greenfield project after installing v0.1.13.

- Failure Signature: Confirmed apply wrote 1 umbrella plus child workstreams, planned components, and diagrams; child records lacked topology links, diagrams were not reciprocally connected to child backlogs, and component CURRENT_SPEC.md files remained generic and shallow.

- Follow-Up Evidence (2026-05-08 / v0.1.15 local greenfield): A DeFi Risk Sentinel App greenfield apply produced component specs whose visible Registry detail still read like a template: `Experience Boundary is a application component registered through odylith component register`, repeated the same planned-ownership structure across components, leaked raw risk metadata such as `R1.` / `odylith_assumption`, and used generic interface/dependency/proof language instead of DeFi-specific ownership, risk-signal, fixture, oracle, liquidity, wallet/protocol, or alert-state contracts.

- Trigger Path: odylith greenfield propose --repo-root . --prompt <greenfield project>; host saves confirmed proposal; odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release next

- Ownership: Domain Intelligence greenfield apply traceability, Radar topology metadata, Atlas related_backlog mapping, and Registry component spec seeding.

- Timeline: Captured 2026-05-03 through `odylith bug capture`.

- Blast Radius: Empty or thin consumer repos using greenfield apply across Codex, Claude, and host-agnostic proposal JSON paths.

- SLO/SLA Impact: No data loss; substantial onboarding and governance-trust degradation because generated records look complete while traceability and ownership depth are missing.

- Data Risk: None

- Security/Compliance: No direct security impact.

- Invariant Violated: Confirmed greenfield governance writes must create mutually traceable Radar, Registry, and Atlas records, and planned component specs must preserve the host-authored ownership reasoning instead of degrading to placeholders.

- Root Cause: Greenfield apply created Radar, Registry, and Atlas records as separate write phases: backlog creation knew only umbrella topology, Atlas scaffold related every diagram to the first backlog item, and component register received only umbrella workstream IDs with no responsibility, dependency, interface, validation, or diagram context.

- Follow-Up Root Cause (2026-05-08): The generic apply-ready scaffold still generated `Experience Boundary`, `Domain Core`, and `Verification Harness` for non-robot prompts, so greenfield component identity stayed domain-agnostic. The Registry spec renderer also lived inline inside component registration and wrapped all inputs in a single boilerplate markdown shape, while component risk extraction flattened proposal risk objects and leaked metadata tokens into prose.

- Solution: Add a greenfield traceability planner that maps proposal backlog rows, components, and diagrams onto generated workstream and diagram IDs; write related_diagram_ids and richer detail sections back into parent and child workstreams; pass related workstreams, diagrams, responsibility, boundary, dependencies, interfaces, validation, and risks into component registration; tighten proposal validation against shallow backlog metrics and component responsibility.

- Follow-Up Solution (2026-05-08): Extract Registry spec rendering into `component_spec_rendering`, render kind-specific component dossiers (application interaction, runtime contract, tooling proof harness), infer deterministic domain component profiles for generic greenfield prompts, add a DeFi risk profile that creates Risk Sentinel Console / Risk Signal Engine / Scenario Replay Harness components, and normalize inherited risk/security/compliance posture without leaking raw proposal metadata.

- Rollback/Forward Fix: Forward fix in domain_intelligence greenfield apply and governance component authoring; no rollback needed because existing generated records remain valid and future applies gain stronger traceability.

- Verification: Run focused unit tests for greenfield proposals and component authoring, plus Casebook validation and governed surface refresh/sync after the source change.

- Prevention: Keep regression tests asserting child related_diagram_ids, Atlas related_backlog child links, and non-placeholder component specs; reject host proposals with shallow child metrics or component responsibility.

- Agent Guardrails: Do not call greenfield apply complete when generated records exist but Radar child workstreams, Atlas diagrams, and Registry specs cannot navigate to each other.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py covers child topology metadata, Atlas related_backlog links, richer Registry specs, shallow proposal rejection, and bespoke DeFi risk component specs that reject generic Experience Boundary/template text and raw risk metadata. tests/unit/runtime/test_component_authoring.py covers responsibility-backed component specs and the extracted Registry spec renderer.

- Monitoring Updates: Watch fresh-install greenfield screenshots and generated component specs for topology-free child records or placeholder Registry sections.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py
  - src/odylith/runtime/domain_intelligence/greenfield_domain_profile.py
  - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
  - src/odylith/runtime/governance/component_spec_rendering.py
  - src/odylith/runtime/governance/component_authoring.py
