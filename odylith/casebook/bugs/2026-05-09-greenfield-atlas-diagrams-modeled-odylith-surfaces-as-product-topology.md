- Bug ID: CB-191

- Status: Open

- Created: 2026-05-09

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: Greenfield Atlas diagrams modeled Odylith surfaces as product topology

- Impact: Operational risk: Greenfield proposals could show Odylith bookkeeping surfaces as if they were product architecture nodes, confusing operators and steering host agents toward internal governance mechanics instead of the user's domain model.

- Components Affected: domain-intelligence-greenfield

- Environment(s): Odylith source-local maintainer lane and v0.1.15 greenfield proposal flow; observed in generated Atlas component ownership diagram screenshot on 2026-05-08.

- Detected By: Operator screenshot review of greenfield Atlas diagram.

- Failure Signature: Generated Mermaid contained nodes such as Compass Radar Registry Atlas and Odylith surfaces inside system overview, component ownership, sequence, validation/release, and robot-swarm specialized diagrams.

- Trigger Path: Run odylith greenfield propose/create for an empty greenfield repo, then open a generated architecture diagram such as the component ownership map.

- Ownership: Domain Intelligence greenfield proposal scaffold and specialized Atlas profile generators.

- Timeline: Captured 2026-05-09 through `odylith bug capture`.

- Blast Radius: Draft greenfield diagrams, rendered architecture review, proposal text, host handoff, and downstream first technical-plan reasoning.

- SLO/SLA Impact: First-run greenfield review loses clarity and forces operators to distinguish Odylith governance machinery from the proposed product architecture.

- Data Risk: Data risk: no direct data exposure, but domain model data boundaries can be obscured when governance surfaces appear as product components.

- Security/Compliance: Security/compliance posture: compliance and release gates can be misread as Odylith surface checks instead of domain-specific proof obligations.

- Invariant Violated: Greenfield architecture diagrams must model the user's project domain only; Odylith governance records may appear in apply metadata but not as product topology nodes.

- Root Cause: The deterministic proposal scaffold reused internal governance-refresh terminology inside user-facing Atlas Mermaid and project intelligence strings instead of separating Odylith recordkeeping from product architecture.

- Solution: Replace branded governance surface nodes and proposal strings with project-domain terms: workstreams, component specs, architecture diagrams, evidence bundle, progress view, release records, and governed project records. Add regression tests that forbid Radar/Registry/Atlas/Compass leakage in generated diagram sources and rendered proposal text.

- Verification: PYTHONPATH=src python3 -m pytest tests/unit/runtime/test_greenfield_atlas_contract.py tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_greenfield_merchant_lending_profile.py tests/unit/runtime/test_greenfield_host_routing.py -q (48 passed); generated proposal text leak check passed for generic, robot-swarm, and Shopify/DeFi merchant-lending prompts.

- Prevention: Keep Odylith governance naming out of greenfield product diagrams and proposal body; reserve product-owned labels for implementation records and CLI apply metadata only.

- Agent Guardrails: When reviewing greenfield UX, inspect rendered proposal text and Mermaid sources, not only JSON schema validity or dashboard refresh success.

- Regression Tests Added: tests/unit/runtime/test_greenfield_atlas_contract.py forbids Odylith/Radar/Registry/Compass/surface-refresh tokens in generated diagram sources and rendered proposal text.

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- src/odylith/runtime/domain_intelligence/robot_swarm_profile.py
- src/odylith/runtime/domain_intelligence/greenfield_project_intelligence.py
- tests/unit/runtime/test_greenfield_atlas_contract.py
