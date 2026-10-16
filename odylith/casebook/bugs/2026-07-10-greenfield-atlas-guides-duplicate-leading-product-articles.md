- Bug ID: CB-234

- Status: Open

- Created: 2026-07-10

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: Atlas state and release guides prefixed the product label with the even when the normalized product title already began with The. The quality gate correctly stopped transaction compilation before a ProductCreateTransaction was sealed.

- Impact: Consumer-utility risk: a valid product confirmation can be blocked by generated visible copy before the transaction-ready confirmation gate.

- Components Affected: atlas

- Environment(s): Fresh greenfield compile-transaction source replay after material-custody repair.

- Detected By: Exact failed-subset source replay

- Failure Signature: compiled Atlas catalog rows leaked adjacent duplicate word prose

- Trigger Path: greenfield propose -> persist visible confirmation -> greenfield compile-transaction -> Atlas catalog prewrite quality gate

- Ownership: Atlas confirmed-diagram renderer

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Operational risk spans product titles with a leading article in state and release guide projections.

- SLO/SLA Impact: Delivery and operational risk: blocks pre-confirm transaction compilation; no post-confirm writes occur.

- Data Risk: No data loss or privacy risk: staging contains no durable product writes.

- Security/Compliance: No security, compliance, policy, accessibility, or safety impact; the visible-copy gate remained fail-closed.

- Invariant Violated: Pre-confirm Atlas catalog copy must be grammatical and free of adjacent duplicate words before a transaction can be confirmed.

- Root Cause: confirmed_diagrams used Read this as the plus a sentence label retaining the leading article.

- Solution: Drop the leading article once for mid-sentence Atlas references and rewrite affected state and release summaries.

- Rollback/Forward Fix: Forward fix only; generated-copy quality gate remains enabled.

- Verification: The exact urban pavement case now compiles a ProductCreateTransaction hash after catalog copy repair.

- Prevention: Regression test renders a title beginning with The and asserts catalog guide copy has no adjacent duplicate article.

- Agent Guardrails: Do not bypass copy quality gates; repair the producer and replay the failed consumer case.

- Preflight Checks: Run Atlas diagram copy regression and exact source replay before packaging.

- Regression Tests Added: test_diagram_guides_do_not_repeat_articles_for_product_titles

- Monitoring Updates: 240-case campaign stops and emits failed-subset replay evidence on repeated pre-confirm clusters.

- Version/Build: 0.1.15

- Config/Flags: 240-case-discovery with cluster stop threshold 2

- Customer Comms: No customer communication required; the defect stopped before confirmation.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_diagrams.py
- tests/unit/runtime/test_greenfield_confirmed_diagrams.py
