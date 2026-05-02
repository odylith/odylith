- Bug ID: CB-155

- Status: FixedPendingRelease

- Created: 2026-05-02

- Fixed: Pending

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Radar allowed topology-sensitive workstream to render without topology

- Impact: Topology-sensitive workstreams could render with no linked diagrams, hiding the Atlas, Registry, runtime, and engine surfaces that bound the work.

- Components Affected: radar

- Environment(s): Odylith product repo v0.1.13 dev-maintainer lane

- Detected By: Operator review of B-141 Radar topology surface

- Failure Signature: B-141 had empty related_diagram_ids and only top-level odylith component while spanning cross-host runtime and engine surfaces.

- Trigger Path: Open B-141 in Radar after cross-host latency implementation.

- Ownership: Radar backlog topology and backlog-contract validation

- Timeline: Captured 2026-05-02 through `odylith bug capture`.

- Blast Radius: Topology-sensitive product workstreams in active and release-bound Radar views

- SLO/SLA Impact: Product governance trust risk; no runtime SLO impact

- Data Risk: No customer data risk

- Security/Compliance: No direct security impact

- Invariant Violated: Topology-sensitive product work must show linked diagrams or an explicit no-topology rationale before it can pass governance validation.

- Root Cause: Backlog validation checked declared topology shape and parent-child reciprocity, but did not require topology for topology-sensitive implementation workstreams.

- Solution: Link B-141 to D-002, D-018, D-020, D-037, D-038, D-041, and D-042; broaden impacted components; add topology-sensitive backlog validation.

- Rollback/Forward Fix: Forward fix in v0.1.13 with validator enforcement and governed surface refresh.

- Verification: Run odylith validate backlog-contract --repo-root . and confirm generated Radar payload shows B-141 related_diagram_ids with linked_diagram_count 7.

- Prevention: Backlog contract rejects topology-sensitive implementation workstreams without related_diagram_ids or explicit topology rationale.

- Agent Guardrails: Do not close, promote, or release-bound cross-host, runtime, engine, migration, intervention, governance, or dashboard workstream records until topology fields are populated or explicitly waived.

- Preflight Checks: Inspect related_diagram_ids and Impacted Components before Radar refresh for topology-sensitive product work.

- Regression Tests Added: tests/unit/runtime/test_validate_backlog_contract.py::test_backlog_contract_rejects_topology_sensitive_workstream_without_diagram_or_rationale

- Version/Build: 0.1.13 target release

- Related Incidents/Bugs: B-141; CB-062

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.13
