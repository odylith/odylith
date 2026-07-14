- Bug ID: CB-243

- Status: Open

- Created: 2026-07-12

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: The initial Product Intent Confirmation renders CONFIRM as acceptance to begin compile and validation. This violates the product contract that CONFIRM must commit an already compiled, validated, hash-bound ProductCreateTransaction. The same command label currently names an intent-review transition and the final atomic write transition, forcing a second implicit confirmation and leaving post-confirm compilation work in the visible flow.

- Impact: Every greenfield operator can be asked to confirm before the complete governed package is compiled, so CONFIRM cannot honestly guarantee a deterministic commit-only path. The delivery risk is an acceptance workflow that still depends on product and projection work after a user command labeled CONFIRM.

- Components Affected: domain-intelligence

- Environment(s): Odylith product repo, source-local maintained runtime

- Detected By: Adversarial source review against the precompiled transaction boundary

- Failure Signature: Initial confirmation text says CONFIRM starts pre-confirm compile/validate and later presents a hash-ready commit-only gate.

- Trigger Path: odylith greenfield propose --repo-root . --prompt <request>

- Ownership: Domain Intelligence greenfield confirmation boundary

- Timeline: Observed during final release-boundary review after the full runtime suite passed. Source copies in intent_confirmation.py and proposal_review_card.py explicitly describe CONFIRM as beginning compilation.

- Blast Radius: All Codex and Claude greenfield proposal flows and their guidance mirrors

- SLO/SLA Impact: Blocks the post-confirm determinism release gate and introduces a duplicate confirmation decision.

- Data Risk: Data loss risk is low because no governed record is written at the first confirmation, but product-custody risk is high: an operator may believe a final decision has been accepted before the compiled package exists.

- Security/Compliance: No direct security vulnerability is known. The compliance and auditability risk is an inaccurate assertion that a confirmed decision is hash-bound when the transaction has not yet been built.

- Invariant Violated: CONFIRM means commit this already compiled, validated ProductCreateTransaction; it must not trigger product interpretation, artifact generation, semantic repair, quality repair, or projection work.

- Workaround: Do not treat the first Product Intent Confirmation CONFIRM as approval to create; compile in staging, inspect the hash-ready transaction view, and use only its final confirmation to write.

- Root Cause: The earlier intent-review UX was retained after the precompiled transaction kernel was added, so the same visible command now represents two distinct state transitions.

- Solution: Compile the full package in staging before any command-led confirmation. Render CONFIRM, EDIT, and REJECT only on the sealed transaction view. EDIT adds new evidence and rebuilds; material ambiguity uses a focused question rather than a failed confirmation.

- Rollback/Forward Fix: Forward fix only: preserve existing staged transaction safety, remove the earlier command-led confirmation transition, and add direct contract tests.

- Verification: A greenfield proposal from prompt evidence produces a sealed hash-ready transaction before it renders CONFIRM; post-confirm create only reads, verifies, writes sealed bytes, validates readback, and reports the result.

- Prevention: Enforce a single visible command state machine and fail tests when text or host guidance says CONFIRM starts compilation.

- Agent Guardrails: Never label an intent hypothesis acceptance as CONFIRM when the product contract reserves CONFIRM for the atomic commit of a sealed transaction.

- Preflight Checks: Run transaction-boundary tests, command rendering tests, cross-host visible intervention tests, bundle mirror tests, and a fresh installed greenfield campaign.

- Regression Tests Added: Replace the existing assertions in tests/unit/runtime/test_greenfield_proposals.py and add command-state coverage in tests/unit/runtime/test_greenfield_cli_paths.py so proposal text cannot pair CONFIRM with compile-transaction and transaction confirmation always includes the sealed hash.

- Monitoring Updates: Surface command-state and transaction-hash presence in release proof.

- Version/Build: 0.1.15 source-local pre-release tree

- Config/Flags: greenfield propose default and compile-transaction/create flow

- Customer Comms: No external communication required before release; use clear final confirmation text in product UX.

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/project_intelligence/intent_confirmation.py
- src/odylith/runtime/domain_intelligence/proposal_review_card.py
- src/odylith/runtime/domain_intelligence/greenfield_proposals_cli.py
