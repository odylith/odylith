- Bug ID: CB-244

- Status: Open

- Created: 2026-07-12

- Severity: P1

- Reproducibility: Consistent

- Type: UX

- Description: The first Product Intent screen exposes CONFIRM as approval to begin pre-confirm compilation, while the transaction screen exposes CONFIRM as the hash-bound commit. This preserves a second confirmation and permits product compilation after a user-confirmed command.

- Impact: Operators cannot rely on CONFIRM as one deterministic commit-only command; misleading confirmation semantics can delay product delivery.

- Components Affected: domain-intelligence

- Environment(s): Product-repo maintainer source-local and installed greenfield host flow

- Detected By: Adversarial review

- Failure Signature: Initial confirmation describes CONFIRM as compile/validate; later transaction confirmation describes CONFIRM as commit.

- Trigger Path: greenfield propose, host confirmation, compile-transaction, greenfield create

- Ownership: Greenfield ProductCreateTransaction boundary

- Timeline: Captured 2026-07-12 through `odylith bug capture`.

- Blast Radius: Every new-project flow across supported host models

- SLO/SLA Impact: Breaks the deterministic post-confirm product-path contract and increases release delay risk.

- Data Risk: No committed data loss; accepted user intent can face an unexpected second decision.

- Security/Compliance: Safety and policy posture: user confirmation must not authorize hidden product generation or semantic repair.

- Invariant Violated: CONFIRM must commit one already compiled and validated transaction, never initiate product compilation.

- Root Cause: Product Intent presentation and transaction compilation remain separate user-confirmation stages.

- Solution: Compile the complete package before presenting the only CONFIRM rail; EDIT rebuilds and REJECT stops.

- Rollback/Forward Fix: Forward fix; do not restore post-confirm generation.

- Verification: Prove one visible command rail where CONFIRM invokes only hash verification, atomic sealed writes, readback, and surface refresh.

- Prevention: Reject any user-visible greenfield copy that describes CONFIRM as compile, validate, generate, or repair.

- Agent Guardrails: Do not claim deterministic post-confirm success until the first visible CONFIRM is hash-bound commit-only.

- Preflight Checks: Inspect the visible Product Intent rail and transaction command before release.

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/project_intelligence/intent_confirmation.py
- src/odylith/runtime/domain_intelligence/proposal_review_card.py
