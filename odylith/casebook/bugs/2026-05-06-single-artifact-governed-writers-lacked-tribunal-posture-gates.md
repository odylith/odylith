- Bug ID: CB-175

- Status: FixedPendingRelease

- Created: 2026-05-06

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Single-artifact governed writers lacked Tribunal posture gates

- Impact: Operators could create Radar, Registry, Atlas, or Casebook truth through local validators and refreshes without a named Tribunal-grade posture gate, weakening the product promise that governed artifacts are adjudicated before mutation.

- Components Affected: governance authoring writers

- Environment(s): Odylith product repo maintainer mode during greenfield governance hardening on 2026-05-06.

- Detected By: Maintainer diagnosis of backlog_authoring, component_authoring, scaffold_mermaid_diagram, bug_authoring, and proposal_tribunal write paths.

- Failure Signature: Greenfield apply had run_greenfield_tribunal before writes, but backlog create, component register, atlas scaffold, and bug capture did not run a shared governed artifact Tribunal before source-truth mutation.

- Trigger Path: odylith backlog create, odylith component register, odylith atlas scaffold, and odylith bug capture with grounded but Tribunal-unlabeled payloads.

- Ownership: Governance authoring, Domain Intelligence greenfield apply, and artifact Tribunal contract.

- Timeline: Captured 2026-05-06 through `odylith bug capture`.

- Blast Radius: Consumer and product repos using routine governed authoring CLIs; affected Radar, Registry, Atlas, and Casebook source truth quality.

- SLO/SLA Impact: Governance accuracy and release-proof confidence degraded because artifact writes could bypass explicit adjudication while still refreshing dashboards.

- Data Risk: Low direct customer-data risk; high governed-memory data risk because AI-agent-authored governance truth could become durable without explicit Tribunal posture checks.

- Security/Compliance: Security/compliance posture: no credentials changed directly, but AI-agent assisted engineering risk includes unreviewed security, privacy, policy, accessibility, and compliance assumptions becoming durable governance memory.

- Invariant Violated: Every governed artifact mutation must pass a Tribunal-grade pre-write adjudication or explicitly stay draft/candidate with blocked promotion.

- Root Cause: The greenfield multi-surface apply path had a proposal Tribunal, while older single-artifact writers relied on per-surface validators and owned-surface refresh instead of a shared pre-write Tribunal contract.

- Solution: Add a zero-provider governed artifact Tribunal and wire it before backlog, component, Atlas, and Casebook writes; tighten greenfield proposal Tribunal to require explicit security/compliance posture.

- Verification: Targeted tests cover artifact Tribunal rejection/acceptance, greenfield proposal posture rejection, backlog create posture flags, component register posture fields, Atlas concrete component requirements, and bug capture Tribunal payloads.

- Prevention: Keep governed writer CLIs behind deterministic local Tribunal gates; require domain risk and security/compliance posture for durable workstream and component capture.

- Agent Guardrails: When creating governed truth, do not treat refresh success as adjudication; require posture fields and pre-write Tribunal pass before mutation.

- Regression Tests Added: tests/unit/runtime/test_governed_artifact_tribunal.py plus focused greenfield, backlog, component/atlas authoring, and bug capture tests.

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/governance/artifact_tribunal.py
- src/odylith/runtime/domain_intelligence/proposal_tribunal.py
- src/odylith/runtime/governance/backlog_authoring.py
- src/odylith/runtime/governance/component_authoring.py
- src/odylith/runtime/surfaces/scaffold_mermaid_diagram.py
- src/odylith/runtime/governance/bug_authoring.py
