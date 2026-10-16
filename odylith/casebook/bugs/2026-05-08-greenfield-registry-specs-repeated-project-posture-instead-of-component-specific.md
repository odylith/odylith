- Bug ID: CB-187

- Status: FixedPendingRelease

- Fixed: Pending

- Created: 2026-05-08

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield apply produced Registry component specs that looked polished but still carried shared template structure and project-level risk/security/compliance narrative across every component. Component dossiers must stay scoped to the component's own boundary, collaborators, failure modes, interfaces, and proof obligations.

- Impact: Operators reviewing a greenfield Registry saw repetitive component specs and had to re-learn which parts were project posture versus component contract, weakening the handoff into planning and implementation.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo greenfield create/apply path, source-local and shipped candidate runtime.

- Detected By: Operator feedback on generated external-domain Registry component specs.

- Failure Signature: Specs repeated project-level security/compliance/risk language and generic does-not-claim boilerplate; domain components could also inherit the first operator workflow as their implementation anchor.

- Trigger Path: odylith greenfield create --repo-root . --prompt '<greenfield app>' --release 0.0.1 --confirm, then open odylith/registry/source/components/*/CURRENT_SPEC.md

- Ownership: Domain Intelligence greenfield proposal/apply and Registry component spec rendering.

- Timeline: Captured 2026-05-08 through `odylith bug capture`.

- Blast Radius: All greenfield projects that rely on generated candidate Registry specs for project-first planning.

- SLO/SLA Impact: Release-quality greenfield UX degraded; agent handoff became repetitive and less trustworthy.

- Data Risk: No customer data loss; governance-truth quality risk in component dossiers.

- Security/Compliance: Security/compliance posture was not lost, but it was placed too broadly in component specs instead of scoped to each component boundary.

- Invariant Violated: Registry CURRENT_SPEC.md must be component-owned truth, not a copy of project-level narrative.

- Root Cause: greenfield_proposals._component_risk_lines inherited proposal-wide risk and security_compliance into every component, while component_spec_rendering used repeated generic outside-boundary/runway text.

- Solution: Keep project-wide posture in the project brief and Radar; generate component-local risk/security/policy guardrails, parse boundary exclusions into Outside Boundary bullets, and prefer the most specific child workstream for each component handoff.

- Rollback/Forward Fix: Forward fix in renderer and greenfield handoff selection; no data migration required for existing repos beyond regeneration on the next greenfield apply.

- Verification: PYTHONPATH=src pytest -q tests/unit/runtime/test_greenfield_proposals.py; source-local greenfield apply artifact inspection for external-domain component specs. Follow-up proof: `python3 -m pytest tests/unit/runtime/test_greenfield_atlas_contract.py tests/unit/runtime/test_greenfield_host_routing.py tests/unit/runtime/test_greenfield_intelligence_schema.py tests/unit/runtime/test_greenfield_proposals.py -q` passed (`49 passed`); fresh source-local `greenfield propose/create` for an external-domain fixture produced component-specific Registry dossiers with no old project-risk/security boilerplate.

- Prevention: Regression tests assert component specs omit project-wide phrases, contain component-named sections, and select component-specific workstream anchors.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py covers bespoke domain-profile Registry specs and component-specific handoff anchors.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_proposals.py
- src/odylith/runtime/governance/component_spec_rendering.py
- src/odylith/runtime/domain_intelligence/greenfield_experience.py
