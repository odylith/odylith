- Bug ID: CB-250

- Status: Open

- Created: 2026-07-15

- Severity: P1

- Reproducibility: Always

- Type: UX

- Description: A pre-confirm word-count fallback accepted longer noun-phrase prompts such as a repair booking workspace as complete Product Intent and staged inferred first-path facts without asking the user for a concrete user flow.

- Impact: Users can confirm a product whose first complete path was invented from a title-like request instead of receiving one focused clarification.

- Components Affected: odylith

- Environment(s): Odylith product repo, greenfield propose pre-confirm compilation

- Detected By: Adversarial transaction and consumer-utility review

- Failure Signature: A title-like prompt reached ProductCreateTransaction staging without a concrete multi-step first path.

- Trigger Path: odylith greenfield propose --prompt "Create a booking workspace for repairs and scheduling."

- Ownership: Greenfield prompt materialization and Product Intent materiality gate

- Timeline: Captured 2026-07-15 through `odylith bug capture`.

- Blast Radius: All prompt-only greenfield proposal flows across Codex, Claude, and other host-model adapters

- SLO/SLA Impact: Pre-confirm clarification quality and deterministic post-confirm success are degraded.

- Data Risk: No governed records are written before confirmation, but user intent can be misrepresented in staged artifacts.

- Security/Compliance: Privacy: no personal data is added or exposed by this gate. Accessibility: the one-sentence clarification is plain-language and avoids schema-shaped input. Compliance: no regulated decision is made before the required product path is supplied. Safety: the gate prevents an inferred path from claiming safe or complete behavior without evidence.

- Invariant Violated: A prompt-only transaction may stage only when evidence supplies a concrete multi-step first path or concrete device behavior.

- Root Cause: The materiality decision used a local six-word threshold after parsing, which mistook a product noun phrase for usable path evidence and allowed unrelated edit prose to mask the original path.

- Solution: Evaluate prompt and edit evidence independently; require at least two parsed steps, allow concrete device behavior, and preserve original path evidence when a headed edit only corrects the actor.

- Rollback/Forward Fix: Forward fix only; no accepted governed record was written by this defect.

- Verification: Focused materiality and CLI receipt tests pass, followed by the 265-test greenfield intent, transaction, compiled-write, and CLI boundary suite.

- Prevention: Keep title-like, concrete device, structured-edit, short actor-edit, and rehashed receipt regressions in the pre-confirm contract suite.

- Agent Guardrails: Do not replace semantic materiality with word-count heuristics; preserve valid prompt evidence when an EDIT changes only an actor.

- Regression Tests Added: test_thin_prompt_asks_one_first_path_question_without_staging_artifacts and test_greenfield_propose_cli_asks_one_product_question_for_a_title_like_path

- Related Incidents/Bugs: CB-235

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- tests/unit/runtime/test_greenfield_transaction_intent_authority.py
- tests/unit/runtime/test_greenfield_cli_paths.py
