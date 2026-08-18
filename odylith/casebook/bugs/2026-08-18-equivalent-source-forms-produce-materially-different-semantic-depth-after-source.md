- Bug ID: CB-335

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: The source-claim lock plus bounded graph extension preserves exact source custody, but disclosed equivalent cases gfhi-001 and gfhi-002 seal different workflow and component depth. One form treats seeing the declared receipt as a separate workflow action and introduces a supporting roster adapter; the other keeps the receipt only as a visible output and projects two components.

- Impact: Equivalent user intents can produce materially different Radar, Registry, Atlas, and package depth despite correct source facts and outcomes.

- Components Affected: domain-intelligence

- Environment(s): Greenfield Semantic Intent bounded-extension development pilot at revision bf982b0eda9659dca34be5ab54b845ece4b27afa

- Detected By: Fresh disclosed equivalent-source pilot under source-claim extension plan v4

- Failure Signature: gfhi-001 and gfhi-002 preserve the same actor, state, output, dependency, and prohibition but diverge at 3 versus 2 workflow steps and 3 versus 2 components; semantic meaning hashes differ.

- Trigger Path: prompt-only source critic -> locked source claims -> bounded extension author -> deterministic graph assembly -> projection plan

- Ownership: Semantic evidence-role authority and deterministic source-graph assembly

- Timeline: Captured 2026-08-18 through `odylith bug capture`.

- Blast Radius: Equivalent or paraphrased prompts where a visible outcome is also described as observed, received, or displayed, or where dependency depth is expressed at different surface granularity.

- SLO/SLA Impact: Release blocking; equivalent-source convergence is a fixed completion gate.

- Data Risk: No byte loss; governance-truth drift and inconsistent package scope.

- Security/Compliance: Compliance and safety posture: prohibition custody remains intact and no direct security, privacy, policy, or accessibility bypass is observed, but inconsistent governed scope is release blocking.

- Invariant Violated: Equivalent source meaning must produce materially equivalent canonical intent and governance depth without phrase-specific normalization.

- Root Cause: The critic locks final graph-shaped source facts directly, so surface granularity choices become canonical authority before semantic roles such as workflow action, visible-result evidence, dependency, and discarded context are adjudicated.

- Solution: Compare a typed source evidence-role authority that locks cited semantic roles and endpoints, then deterministically assembles source graph facts and relations. Retire the direct source-graph authority if the replacement converges without losing fidelity. Do not add regex, phrase rules, or a third reviewer.

- Verification: gfhi-001 and gfhi-002 must converge on material graph and package depth while gfhi-005 still clarifies, gfhi-011 remains specific, and negative controls preserve real observe or receive actions. Full development evidence must show zero P0/P1 before holdout.

- Prevention: Require equivalent-source development pairs in every mechanism comparison and treat graph-depth divergence as an ownership failure rather than a presentation defect.

- Agent Guardrails: No regex or token stacks, no fixture vocabulary, no phrase patching, no validator-guided repair, and no extra challenger cascade.

- Preflight Checks: Preserve current failure artifacts, use disclosed development cases only, and do not access the protected holdout.

- Related Incidents/Bugs: CB-334

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_semantic_source_claims.py; src/odylith/runtime/domain_intelligence/greenfield_semantic_graph_extension.py
