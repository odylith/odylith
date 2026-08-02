- Bug ID: CB-304

- Status: Open

- Created: 2026-08-02

- Severity: P0

- Reproducibility: Always

- Type: DataLoss

- Description: Greenfield host confirmation resolved bare CONFIRM through a mutable singleton transaction path. A second proposal could replace the staged bytes between review and decision, causing the host callback to commit a different hash than the package the operator saw.

- Impact: An operator could approve package A while Odylith committed package B; product-domain governance truth and release delivery would no longer match the reviewed decision.

- Components Affected: domain-intelligence

- Environment(s): Codex and Claude pre-model Greenfield confirmation adapters in v0.1.15 development

- Detected By: Adversarial transaction-boundary source review and concurrent A/B schedule analysis

- Failure Signature: propose(A); propose(B) overwrites singleton; bare CONFIRM rereads B receipt and commits B

- Trigger Path: odylith greenfield propose followed by a second proposal before bare host CONFIRM

- Ownership: Domain Intelligence Greenfield pending transaction and host confirmation boundary

- Timeline: Captured 2026-08-02 through `odylith bug capture`.

- Blast Radius: All supported Codex and Claude Greenfield confirmations using the singleton pending alias; release delivery blocked

- SLO/SLA Impact: P0 delivery and release-readiness blocker for reviewed-byte confirmation integrity

- Data Risk: High product-domain data integrity risk: coordinated Radar, Registry, Atlas, and Compass truth could differ from the user-reviewed package

- Security/Compliance: Security integrity and non-repudiation boundary violated. Compliance and policy approval evidence becomes unreliable. Privacy, accessibility, and safety scope are not directly changed, but their reviewed constraints could be replaced by different pending bytes.

- Invariant Violated: CONFIRM must commit the exact immutable transaction hash shown to the operator

- Root Cause: greenfield_proposals_cli._compile_prompt_evidence_transaction always wrote product-create-transaction.v1.json at one fixed runtime path, while greenfield_host_confirmation.maybe_handle_greenfield_decision accepted bare CONFIRM and reread the adjacent receipt from that fixed path instead of resolving the hash shown in chat.

- Solution: Store pending packages under pending/<transaction-hash>, render hash-bearing CONFIRM/EDIT/REJECT commands, resolve only that exact directory, and serialize CONFIRM with REJECT through one repository lock.

- Rollback/Forward Fix: Forward fix only; reject the retired bare-command and singleton path contract.

- Verification: Hash-bound Codex/Claude parity tests, A/B retarget regression, immutable pending-store tests, shared-lock contention tests, and real propose/create integration.

- Prevention: Require every approval command to carry immutable package identity and adversarially test concurrent replacement schedules before release.

- Agent Guardrails: Never infer confirmed bytes from a mutable current pointer; reviewers must trace the user-visible identifier to the exact read path.

- Preflight Checks: No singleton pending path; exact hash in all three commands; compiler receipt and transaction-address binding pass.

- Regression Tests Added: test_hash_bound_confirm_cannot_be_retargeted_by_a_newer_pending_proposal; pending store and lock suites

- Version/Build: 0.1.15 development

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_pending_transaction_store.py
- src/odylith/runtime/surfaces/greenfield_host_confirmation.py
