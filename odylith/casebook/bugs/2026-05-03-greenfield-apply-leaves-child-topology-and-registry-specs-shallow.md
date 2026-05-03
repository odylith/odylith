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

- Trigger Path: odylith greenfield propose --repo-root . --prompt <greenfield project>; host saves confirmed proposal; odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release next

- Ownership: Domain Intelligence greenfield apply traceability, Radar topology metadata, Atlas related_backlog mapping, and Registry component spec seeding.

- Timeline: Captured 2026-05-03 through `odylith bug capture`.

- Blast Radius: Empty or thin consumer repos using greenfield apply across Codex, Claude, and host-agnostic proposal JSON paths.

- SLO/SLA Impact: No data loss; substantial onboarding and governance-trust degradation because generated records look complete while traceability and ownership depth are missing.

- Data Risk: None

- Security/Compliance: No direct security impact.

- Invariant Violated: Confirmed greenfield governance writes must create mutually traceable Radar, Registry, and Atlas records, and planned component specs must preserve the host-authored ownership reasoning instead of degrading to placeholders.

- Root Cause: Greenfield apply created Radar, Registry, and Atlas records as separate write phases: backlog creation knew only umbrella topology, Atlas scaffold related every diagram to the first backlog item, and component register received only umbrella workstream IDs with no responsibility, dependency, interface, validation, or diagram context.

- Solution: Add a greenfield traceability planner that maps proposal backlog rows, components, and diagrams onto generated workstream and diagram IDs; write related_diagram_ids and richer detail sections back into parent and child workstreams; pass related workstreams, diagrams, responsibility, boundary, dependencies, interfaces, validation, and risks into component registration; tighten proposal validation against shallow backlog metrics and component responsibility.

- Rollback/Forward Fix: Forward fix in domain_intelligence greenfield apply and governance component authoring; no rollback needed because existing generated records remain valid and future applies gain stronger traceability.

- Verification: Run focused unit tests for greenfield proposals and component authoring, plus Casebook validation and governed surface refresh/sync after the source change.

- Prevention: Keep regression tests asserting child related_diagram_ids, Atlas related_backlog child links, and non-placeholder component specs; reject host proposals with shallow child metrics or component responsibility.

- Agent Guardrails: Do not call greenfield apply complete when generated records exist but Radar child workstreams, Atlas diagrams, and Registry specs cannot navigate to each other.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py covers child topology metadata, Atlas related_backlog links, richer Registry specs, and shallow proposal rejection; tests/unit/runtime/test_component_authoring.py covers responsibility-backed component specs.

- Monitoring Updates: Watch fresh-install greenfield screenshots and generated component specs for topology-free child records or placeholder Registry sections.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py
