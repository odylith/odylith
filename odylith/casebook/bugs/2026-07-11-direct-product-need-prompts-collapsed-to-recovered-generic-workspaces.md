- Bug ID: CB-241

- Status: Open

- Created: 2026-07-11

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: High-variance fresh-install prompts beginning with a user or organization need instead of Create/Build could lose their product title, first path, actor, and domain contract. A mining allocation prompt became Recovered Product Workspace with a representative user; a proteomics method-transfer prompt preserved only some evidence and dropped collision energy.

- Impact: Users who provide clear, ordinary product needs can receive generic confirmation and lose material product evidence without being asked an unnecessary clarification.

- Components Affected: domain-intelligence

- Environment(s): Maintainer local-release v0.1.15 95e787539, 240-case installed discovery

- Detected By: Fresh installed 240-case campaign

- Failure Signature: domain term coverage too low: expected at least 4, found 0 for critical spare parts allocation; expected at least 4, found 3 for mass-spec method transfer

- Trigger Path: Prompt-only Product Intent Confirmation recovery for direct declarative needs and gerund-led product paths

- Ownership: Greenfield direct prompt recovery, evidence anchors, and semantic first-path admission

- Timeline: Captured 2026-07-11 through `odylith bug capture`.

- Blast Radius: Any direct declarative user need with non-whitelisted actions, coordinated actor evidence, or conditional domain constraints.

- SLO/SLA Impact: Blocks release readiness and creates a consumer utility failure before the user can receive a credible confirmation.

- Data Risk: No private-data exposure observed; product facts and traceability can be dropped from the accepted package.

- Security/Compliance: No direct security exposure observed; scientific and asset-maintenance product constraints can be lost.

- Invariant Violated: Odylith must productize clear user evidence without forcing users to rephrase; direct need context, actors, and material terms must survive pre-confirm compilation.

- Root Cause: Prompt recovery prioritized command-led patterns and a narrow action whitelist. Direct actor-led needs could fall through to a trailing proof clause or generic fallback; evidence extraction omitted coordinated actor actions and conditional constraints.

- Solution: Recover direct actor-led needs before trailing proof clauses, derive product titles from their action objects, preserve coordinated action objects and conditional differences as bounded evidence anchors, and admit semantic material actions beyond the legacy action whitelist.

- Rollback/Forward Fix: Forward fix only. Do not add fixture-specific titles or mutate generated consumer projects.

- Verification: Direct mining allocation and proteomics method-transfer package regressions, broad live package suite, recovery suite, and exact fresh installed failed-subset replay.

- Prevention: Keep direct declarative need and gerund-led product paths in the high-variance corpus with required domain-term distribution checks.

- Agent Guardrails: Do not ask the user to convert a clear declarative need into a command. Do not use generic Recovered Product Workspace when the prompt names a concrete product object.

- Preflight Checks: Run direct-product recovery regressions before resuming 240-case discovery.

- Regression Tests Added: test_direct_product_need_recovery_preserves_domain_contract

- Monitoring Updates: Retain domain.term.coverage.too.low.expected.least.found until the rebuilt direct-prompt subset passes.

- Version/Build: 0.1.15 local-release 95e787539

- Config/Flags: 240-case discovery, six workers, cluster threshold 2

- Customer Comms: Internal maintainer evidence only until fresh installed proof passes.

- Related Incidents/Bugs: CB-239, CB-240

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_prompt_source.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_recovery.py
- src/odylith/runtime/domain_intelligence/greenfield_evaluation_semantics.py
- tests/unit/runtime/test_greenfield_live_simulation_regressions.py
