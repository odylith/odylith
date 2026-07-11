- Bug ID: CB-239

- Status: Open

- Created: 2026-07-11

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: The installed wedding-weekend case correctly selected the guest RSVP first path but dropped the setup term rehearsal dinner from accepted evidence. Separately, proposal compilation reread the raw CLI prompt for evidence anchors after confirmation, allowing stale prompt context to change a sealed creation package.

- Impact: A valid user request can lose material context before confirmation, and edits can be overridden by stale raw prompt evidence during compile.

- Components Affected: domain-intelligence

- Environment(s): Maintainer fresh local-release v0.1.15 8a154da6b on 2026-07-10

- Detected By: Exact installed failed-subset replay for wedding-weekend-guest-guide

- Failure Signature: domain term coverage too low: expected at least 4, found 3; missing rehearsal dinner

- Trigger Path: greenfield-matrix-campaign failed-subset replay using /private/tmp/failed-subset-replay/failed-subset-001.cases.json

- Ownership: Greenfield Product Intent Confirmation evidence custody and confirmed proposal compiler

- Timeline: Captured 2026-07-11 through `odylith bug capture`.

- Blast Radius: Any command-led product request with material setup nouns before its first action, especially after an EDIT narrows accepted evidence.

- SLO/SLA Impact: Blocks release readiness and weakens the guarantee that post-confirm behavior only commits accepted, validated bytes.

- Data Risk: No private-data exposure observed; stale evidence could appear in governed output against operator intent.

- Security/Compliance: No direct security exposure observed; the custody failure is relevant to safety, compliance, and regulated product evidence.

- Invariant Violated: Material setup evidence must be selected and accepted before confirmation; compilation must not reread raw prompt evidence after confirmation.

- Root Cause: Prompt recovery narrowed context to the first path and only extracted control-style evidence anchors. The confirmed proposal compiler then called evidence_anchor_phrases with the raw prompt after confirmation.

- Solution: Extract bounded command-led setup nouns into visible pre-confirm evidence requirements, preserve them through accepted intent spans, and compile evidence requirements only from accepted intent facts.

- Rollback/Forward Fix: Forward fix only. Do not mutate generated consumer projects or restore evidence from stale raw prompts after confirmation.

- Verification: Focused context-anchor, edited-intent custody, transaction authority, and fresh installed failed-subset replay against a rebuilt local release.

- Prevention: Keep context extraction pre-confirm and require tests that prove edited confirmation takes precedence over original prompt context.

- Agent Guardrails: Do not widen the first path with setup prose. Do not use CLI prompt text as a post-confirm semantic input. Preserve only concise accepted evidence anchors, never full source sentences.

- Preflight Checks: Run confirmation custody tests and the exact failed-subset replay before resuming volume discovery.

- Regression Tests Added: test_evidence_anchors_keep_command_context_nouns_without_source_prose; test_wedding_context_phrase_does_not_become_the_first_path_actor; test_confirmed_proposal_uses_edited_intent_not_stale_prompt_terms

- Monitoring Updates: Retain domain.term.coverage.too.low.expected.least.found until the rebuilt exact replay passes.

- Version/Build: 0.1.15 local-release 8a154da6b

- Config/Flags: failed-subset max workers 2; stop after first failure

- Customer Comms: Internal maintainer evidence only until fresh installed proof passes.

- Related Incidents/Bugs: CB-222, CB-236, CB-237, CB-238

- GitHub Status: fixed_pending_release

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_evaluation_semantics.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_proposal.py
- tests/unit/runtime/test_greenfield_live_simulation_regressions.py
- tests/unit/runtime/test_greenfield_confirmation_command_contract.py
