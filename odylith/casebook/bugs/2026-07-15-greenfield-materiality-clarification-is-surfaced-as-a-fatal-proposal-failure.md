- Bug ID: CB-251

- Status: Open

- Created: 2026-07-15

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: A detailed but materially ambiguous prompt correctly requires one focused first-path question, but greenfield propose raises ValueError and exits as a fatal error. The installed matrix then treats that clarification as a failed product creation instead of a no-write clarification outcome.

- Impact: Users see a recoverable product-intent question as a failure, and installed campaign proof cannot distinguish valid clarification from broken compilation.

- Components Affected: odylith

- Environment(s): Fresh installed v0.1.15 greenfield matrix discovery

- Detected By: Fresh installed 240-case discovery campaign

- Failure Signature: cell-therapy-chain-of-identity exits code 2 with a one-question first-path prompt and no staged records.

- Trigger Path: ./bin/greenfield-matrix-campaign 0.1.15 /private/tmp/odylith-greenfield-release-0.1.15 with science-deeptech fixture

- Ownership: Greenfield proposal CLI, host adapters, and installed preconfirm matrix

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: All Codex, Claude, and host-neutral greenfield proposal flows with materially ambiguous but useful evidence.

- SLO/SLA Impact: Consumer utility and pre-confirm reliability evidence are degraded; no post-confirm write occurs.

- Data Risk: No governed records are written, but a valid user decision is misclassified as a platform error.

- Security/Compliance: The clarification preserves safety by refusing to invent a first complete path; the fix must preserve no-write semantics.

- Invariant Violated: Material uncertainty must render one plain-language clarification state, not a fatal Product Intent failure.

- Root Cause: The materiality gate communicates through ValueError rather than a typed clarification result, and the matrix has no accepted clarification outcome.

- Solution: Introduce a typed no-write clarification result through proposal CLI, Codex and Claude adapters, and the installed matrix; verify exactly one focused question, no transaction, and no writes.

- Rollback/Forward Fix: Forward fix only; no accepted package or governed consumer record was committed.

- Verification: Replay the exact failed subset against a fresh installed dist, then resume discovery only after it accepts clarification as a valid pre-confirm outcome.

- Prevention: Keep detailed ambiguous multi-role prompts in the installed corpus with explicit expected clarification assertions.

- Agent Guardrails: Never recover from material ambiguity by inventing a first path or converting the user question into an exception-shaped failure.

- Related Incidents/Bugs: CB-250

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- scripts/release/greenfield_preconfirm_matrix.py
