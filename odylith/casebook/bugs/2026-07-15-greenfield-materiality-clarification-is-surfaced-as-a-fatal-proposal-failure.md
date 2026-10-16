- Bug ID: CB-251

- Status: FixedPendingRelease

- Fixed: Pending

- Fixed In: v0.1.15

- Created: 2026-07-15

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: A detailed but materially ambiguous prompt correctly requires one focused first-path question, but greenfield propose raises ValueError and exits as a fatal error. The installed matrix then treats that clarification as a failed product creation instead of a no-write clarification outcome.

- Impact: Users see a recoverable product-intent question as a failure, and installed campaign proof cannot distinguish valid clarification from broken compilation.

- Components Affected: odylith

- Environment(s): Fresh installed v0.1.15 greenfield matrix discovery

- Detected By: Fresh installed 240-case discovery campaign

- Failure Signature: The original cell-therapy-chain-of-identity replay exited code 2 with a first-path question and no staged records. After the typed-outcome and copy fixes, a fresh installed replay reached exit code 0, score 10/10, and no staged or governed writes. Its first campaign wrapper verdict was falsely failed by CB-253, a separate proof-runner defect.

- Trigger Path: ./bin/greenfield-matrix-campaign 0.1.15 /private/tmp/odylith-greenfield-release-0.1.15 with science-deeptech fixture

- Ownership: Greenfield proposal CLI, host adapters, and installed preconfirm matrix

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: All Codex, Claude, and host-neutral greenfield proposal flows with materially ambiguous but useful evidence.

- SLO/SLA Impact: Consumer utility and pre-confirm reliability evidence are degraded; no post-confirm write occurs.

- Data Risk: No governed records are written, but a valid user decision is misclassified as a platform error.

- Security/Compliance: The clarification preserves safety by refusing to invent a first complete path; the fix must preserve no-write semantics.

- Invariant Violated: Material uncertainty must render one plain-language clarification state, not a fatal Product Intent failure.

- Root Cause: The materiality gate communicated through ValueError rather than a typed clarification result, and the matrix had no accepted clarification outcome. The first typed implementation also put a reply instruction inside the structured `question` field, violating the single-question contract.

- Solution: Introduce a typed no-write clarification result through proposal CLI, Codex and Claude adapters, and the installed matrix. Keep the structured field to one focused question; render any reply guidance only outside that field. Verify no transaction and no writes.

- Rollback/Forward Fix: Forward fix only; no accepted package or governed consumer record was committed.

- Verification: The focused CLI, installed-matrix, materiality, and confirmation-command suite passed 170 tests. The exact fresh installed cell-therapy replay accepted the clarification as a valid no-write pre-confirm outcome with score 10/10. CB-253 separately governs campaign-wrapper classification.

- Prevention: Keep detailed ambiguous multi-role prompts in the installed corpus with explicit expected clarification assertions, including a check that the structured question has exactly one question mark and no trailing reply instruction.

- Agent Guardrails: Never recover from material ambiguity by inventing a first path or converting the user question into an exception-shaped failure.

- Related Incidents/Bugs: CB-250

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- scripts/release/greenfield_preconfirm_matrix.py
