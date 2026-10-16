- Bug ID: CB-233

- Status: Open

- Created: 2026-07-10

- Severity: P2

- Reproducibility: Always

- Type: Product

- Description: The visible Product Intent Confirmation emitted a proof-boundary sentence containing first-path language without a final period. The section parser reclassified that body sentence as a first-path heading, leaving proof_boundary derived without product-claim custody. compile-transaction correctly stopped before a transaction was sealed.

- Impact: Consumer-utility risk: a valid product confirmation can be rejected before the transaction-ready confirmation gate.

- Components Affected: odylith

- Environment(s): Fresh greenfield compile-transaction source replay and 240-case installed discovery campaign.

- Detected By: High-variance installed matrix campaign

- Failure Signature: ProductCreateTransaction confirmed Product Intent authority has unresolved material custody

- Trigger Path: greenfield propose -> persist visible confirmation -> greenfield compile-transaction

- Ownership: Domain Intelligence confirmed-intent parser

- Timeline: Captured 2026-07-10 through `odylith bug capture`.

- Blast Radius: Operational risk spans any visible confirmation whose unpunctuated prose repeats a canonical section phrase.

- SLO/SLA Impact: Delivery and operational risk: blocks pre-confirm transaction compilation; no post-confirm writes occur.

- Data Risk: No data loss or privacy risk: staging contains no durable product writes.

- Security/Compliance: No security, compliance, policy, accessibility, or safety impact; fail-closed custody validation remained intact.

- Invariant Violated: Every accepted material fact must retain visible product-claim span custody before ProductCreateTransaction sealing.

- Root Cause: confirmed_intent_heading_key treated a long body sentence containing first path as a heading when it lacked terminal punctuation.

- Solution: Treat long prose with sentence punctuation as body text regardless of terminal punctuation; preserve explicit Markdown heading handling.

- Rollback/Forward Fix: Forward fix only; custody gate remains fail-closed.

- Verification: The exact urban pavement case now compiles a ProductCreateTransaction hash from the visible confirmation.

- Prevention: Round-trip visible confirmation through the typed envelope and assert accepted material custody for every material field.

- Agent Guardrails: Never relax custody validation to accommodate generated confirmation prose; repair the parser attribution rule and replay the exact case.

- Preflight Checks: Run material-custody round-trip regression before packaging.

- Regression Tests Added: test_visible_confirmation_preserves_material_custody_when_proof_copy_has_no_final_period

- Monitoring Updates: 240-case campaign stops and emits failed-subset replay evidence on the first repeated cluster.

- Version/Build: 0.1.15

- Config/Flags: 240-case-discovery with cluster stop threshold 2

- Customer Comms: No customer communication required; the defect stopped before confirmation.

- GitHub Status: fixed_pending_release

- Fixed In: 0.1.15

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent_sections.py
- tests/unit/runtime/test_greenfield_confirmation_command_contract.py
