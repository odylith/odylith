- Bug ID: CB-198

- Status: Open

- Created: 2026-05-11

- Severity: P1

- Reproducibility: High

- Type: Product

- Description: Greenfield child artifacts failed product manager comprehension

- Impact: Confirmed greenfield child workstreams, Registry component IDs, and Atlas diagram slugs could read like governance preparation instead of the business/product work a project owner asked Odylith to create.

- Components Affected: domain-intelligence

- Environment(s): Odylith greenfield create/apply against empty consumer repo with merchant-capital prompt; observed in /Users/freedom/mock/mockrepo.

- Detected By: Operator screenshot review and source audit of mockrepo Radar B-002, Registry specs, Atlas slugs, and accepted-project state.

- Failure Signature: Radar B-002 used generic Decision Basis lines such as created as a new queued workstream and deeper scope decomposition waits; Registry and Atlas inherited the full prompt slug instead of a compact domain artifact identity.

- Trigger Path: odylith greenfield create --repo-root . --prompt <greenfield project intent> --release 0.0.1 --confirm, then open Radar B-002 and related Registry/Atlas artifacts.

- Ownership: Domain Intelligence greenfield projection, Radar backlog authoring, Registry component scaffolding, Atlas diagram scaffolding.

- Timeline: Captured 2026-05-11 through `odylith bug capture`.

- Blast Radius: Greenfield child workstreams, Radar INDEX rationale, component directories/specs, Atlas diagram slugs, accepted-project topology links, and Project tab source graph.

- SLO/SLA Impact: Breaks the first-read product-manager test before implementation planning starts.

- Data Risk: No production data loss; affected consumer repos may retain low-quality generated governance records until regenerated or repaired.

- Security/Compliance: In regulated domains, vague prep language and prompt-shaped IDs can obscure custody, loss, compliance, proof, and release-boundary responsibilities.

- Invariant Violated: A confirmed greenfield proposal must produce product-relevant artifacts shaped by project intelligence, not raw prompt repetition or generic governance preparation text.

- Root Cause: Greenfield rows carried product-specific content, but Radar authoring discarded product-specific rationale when rationale_lines crossed through the generic backlog create namespace; component and diagram slugs also inherited the raw project prompt.

- Solution: Preserve product-derived rationale through backlog authoring and use compact domain artifact slugs for generated Registry and Atlas artifacts.

- Rollback/Forward Fix: Forward fix in Domain Intelligence and Radar authoring; existing generated consumer repos should be regenerated or repaired from their accepted project source.

- Verification: pytest tests/unit/runtime/test_greenfield_proposals.py tests/unit/runtime/test_project_intelligence.py -q

- Prevention: Regression tests assert compact domain artifact IDs, no raw prompt slug in project payload, no generic queued-workstream rationale in greenfield Radar output, and Project tab projection from accepted-project and Tribunal state.

- Agent Guardrails: Before declaring a greenfield fix, inspect Radar child rows, Registry component IDs/specs, Atlas diagram IDs, accepted-project topology, and the Project tab story for product-owner readability.

- Preflight Checks: Run a product-manager comprehension audit on at least one greenfield fixture before local release packaging.

- Regression Tests Added: tests/unit/runtime/test_greenfield_proposals.py::test_greenfield_apply_feeds_project_tab_from_accepted_project_and_tribunal; tests/unit/runtime/test_project_intelligence.py::test_greenfield_workstream_body_does_not_repeat_full_project_title

- Code References: - src/odylith/runtime/domain_intelligence/proposal_scaffold.py
- src/odylith/runtime/domain_intelligence/greenfield_workstream_rows.py
- src/odylith/runtime/governance/backlog_authoring.py
