- Bug ID: CB-174

- Status: Open

- Created: 2026-05-06

- Severity: P2

- Reproducibility: High

- Type: Tooling

- Description: Context exact code paths lose Registry owner in execution handshake

- Impact: Exact source-path context can resolve a code file but leave the Execution Engine handshake without the owning Registry component, weakening routed validation and operator trust during greenfield hardening.

- Components Affected: context-engine

- Environment(s): Odylith product repo maintainer lane on branch 2026/freedom/v0.1.15.

- Detected By: Manual engine-integrity pass for greenfield, Context Engine, and Execution Engine alignment.

- Failure Signature: odylith context --repo-root . src/odylith/runtime/domain_intelligence/greenfield_proposals.py returned related_entities={} and execution_engine_handshake.target_component_status=missing.

- Trigger Path: ./.odylith/bin/odylith context --repo-root . src/odylith/runtime/domain_intelligence/greenfield_proposals.py

- Ownership: Context Engine exact-path related-entity assembly and Execution Engine handshake target ownership.

- Timeline: Captured 2026-05-06 through `odylith bug capture`.

- Blast Radius: Registry path-prefix-owned code, docs, and runbooks can lose component ownership in context dossiers; greenfield/domain-intelligence debugging is the observed slice.

- SLO/SLA Impact: Low-latency path lookup still works, but execution targeting degrades from component-owned to missing until the operator re-anchors by component name.

- Data Risk: No application data loss; governance targeting and durable memory quality can degrade.

- Security/Compliance: No direct secret exposure; ownership loss can hide component-specific security, compliance, and validation obligations from routed execution.

- Invariant Violated: An exact repo-local source anchor under a Registry path_prefix must carry the owning component into related_entities and the Execution Engine handshake.

- Root Cause: _related_entities only followed explicit traceability rows and kind-specific component links; synthesized code/doc/runbook path entities did not map back through Registry path_prefix metadata.

- Solution: Add a path-owner component pass for code, doc, and runbook entities, matching their path against component spec_ref and path_prefix metadata before compaction attaches the execution handshake.

- Verification: Regression test test_code_path_context_carries_registry_owner_into_execution_handshake plus live CLI context proof now show domain-intelligence in related_entities and target_component_id.

- Prevention: Keep exact-path context, related_entities, and execution handshake assertions together for source files owned by Registry path_prefix metadata.

- Regression Tests Added: tests/unit/runtime/test_context_grounding_hardening.py::test_code_path_context_carries_registry_owner_into_execution_handshake

- Code References: - src/odylith/runtime/context_engine/odylith_context_engine_projection_entity_runtime.py
- tests/unit/runtime/test_context_grounding_hardening.py
