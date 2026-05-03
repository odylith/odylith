- Bug ID: CB-157

- Status: FixedPendingRelease

- Created: 2026-05-03

- Severity: P2

- Reproducibility: Consistent

- Type: UX

- Description: Compass Timeline Audit could capture a zero-file prompt-submit Observation string as an implementation event, rendering raw Odylith Observation chatter in the audit narrative and event card. Prompt-routing notes are not implementation history and should not appear as fake transaction work.

- Impact: Operators saw prompt-routing chatter presented as timeline implementation history, which polluted governance memory and made Compass less trustworthy.

- Components Affected: compass

- Environment(s): Odylith v0.1.13 development branch with prompt-submit observation routing and Compass transaction audit rendering.

- Detected By: Operator screenshot of Timeline Audit showing --- Odylith Observation as an implementation event with zero files.

- Failure Signature: Timeline Audit card title and audit narrative both rendered --- Odylith Observation: The request is asking for a governed capture, not just a branded aside; files count was zero.

- Trigger Path: Prompt-submit Observation emitted before a greenfield governance request, then Compass transaction history rendered the note as an implementation transaction.

- Ownership: compass transaction audit runtime

- Timeline: Captured 2026-05-03 through `odylith bug capture`.

- Blast Radius: Compass timeline audit, memory substrate, and operator trust for zero-file prompt-routing events.

- SLO/SLA Impact: Governance readout quality drops because non-work chatter is preserved as implementation history.

- Data Risk: Low application data risk; medium governance data hygiene risk because false transaction history can persist.

- Security/Compliance: No direct security impact.

- Invariant Violated: Compass timeline transactions must represent governed work or file-backed events, not zero-file prompt-routing narration.

- Root Cause: Prompt-intervention narration was not filtered before building prompt transactions.

- Solution: Filter zero-file prompt-intervention narration in compass_transaction_runtime before timeline transactions are grouped and rendered.

- Verification: Run the Compass transaction unit test that feeds a zero-file Odylith Observation event and expects no prompt transaction, then run Compass/Casebook browser proof after refresh.

- Prevention: Keep intervention UX and Compass timeline audit as separate surfaces; prompt-routing notes may stay hidden or visible in chat, but not as implementation transactions.

- Regression Tests Added: tests/unit/runtime/test_compass_transaction_runtime.py::test_build_prompt_transactions_drops_zero_file_intervention_chatter

- Fixed In: 0.1.13
