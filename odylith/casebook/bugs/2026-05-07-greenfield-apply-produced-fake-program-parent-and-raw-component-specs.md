- Bug ID: CB-176

- Status: Open

- Created: 2026-05-07

- Severity: P1

- Reproducibility: Always

- Type: OperatorUX

- Description: Local v0.1.15 greenfield apply for a CRISPR Ethics review app accepted a proposal whose first child workstream became the execution-wave program, Registry component specs rendered nested security/compliance lists as raw list literals, and the apply closeout did not tell the operator which workstream starts coding or how to verify the first slice.

- Impact: Operators cannot understand the generated program, component ownership, or next implementation step after accepting a greenfield proposal; release testing shows the experience is not release-ready.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo local release v0.1.15 installed into empty consumer repo /Users/freedom/mock/mockrepo, exercised from Claude Code on May 6, 2026.

- Detected By: Operator manual release testing with screenshots and Claude CLI trace.

- Failure Signature: Compass execution waves card used 'Identity, sessions, and COI-aware authorization (B-001)' as the program; Registry Risks And Open Questions rendered Python-style list literals; apply required repeated schema repairs and ended without coding/verification sequence.

- Trigger Path: odylith greenfield propose/apply for a CRISPR Ethics review app with waves referencing WS-* proposal-local workstream IDs.

- Ownership: Domain Intelligence greenfield proposal normalization, apply output, execution-wave materialization, and component spec authoring.

- Timeline: 2026-05-06: operator installed local v0.1.15 release, proposed CRISPR Ethics app, confirmed single-institution/no-PHI/TypeScript, applied after repeated schema repairs, then inspected Registry and Compass screenshots showing unreadable specs and fake program identity.

- Blast Radius: Any empty-repo greenfield proposal where the host omits the umbrella parent, uses proposal-local WS IDs, or supplies nested security/compliance posture.

- SLO/SLA Impact: Blocks release-readiness for the greenfield project creation flow because accepted governance objects are confusing and unactionable.

- Data Risk: No user data loss, but governed Registry/Radar/Compass source truth can become misleading and require manual cleanup.

- Security/Compliance: Safety-sensitive or regulated greenfield domains can hide access-control, compliance, and verification posture inside unreadable specs.

- Invariant Violated: Accepted greenfield governance must materialize a real umbrella program, readable component specs, resolvable wave/release targets, and an explicit next coding plus validation sequence.

- Root Cause: Greenfield apply assumed backlog[0] was already the umbrella parent, did not resolve proposal-local workstream IDs against created B-* IDs, flattened nested posture values with str(), and returned only artifact counts instead of an implementation handoff.

- Solution: Normalize host proposals by synthesizing a Govern <Project> umbrella when needed, preserve proposal IDs for wave/release/traceability resolution, recursively flatten nested posture text, upgrade component spec template sections, and return start-workstream plus verification gates in apply output.

- Rollback/Forward Fix: Forward fix in the greenfield runtime and generated skill mirror; no runtime rollback is useful because the issue is generated governance quality.

- Verification: Unit regression for CRISPR no-parent proposal, component authoring tests, program wave/view-model tests, Compass/Registry browser smoke, install bundle/lifecycle tests, and local dist rebuild.

- Prevention: Keep Tribunal plus normalization tests covering parent synthesis, proposal ID mapping, nested posture flattening, and post-apply next steps.

- Agent Guardrails: Hosts should still author an explicit WS-00 parent, but apply must not trust that every host did; never hand-repair generated specs after apply when normalization can prevent the bad state.

- Preflight Checks: Before release, run greenfield apply regressions and browser proof for Compass and Registry against a no-source greenfield proposal.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_synthesizes_parent_and_polishes_component_specs plus component/spec and wave suites.

- Related Incidents/Bugs: CB-160, CB-167, CB-173

- Code References: - src/odylith/runtime/domain_intelligence/proposal_normalization.py
- src/odylith/runtime/domain_intelligence/greenfield_programs.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- src/odylith/runtime/governance/component_authoring.py
