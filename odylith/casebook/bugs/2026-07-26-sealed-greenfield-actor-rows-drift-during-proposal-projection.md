- Bug ID: CB-292

- Status: Open

- Created: 2026-07-26

- Severity: P1

- Reproducibility: Always

- Type: Product

- Description: A typed Product Intent can contain a human actor row with terminal punctuation. The proposal compiler applies project-specific actor-row normalization after the Product Intent authority hash is sealed, removing the punctuation. The resulting proposal facts no longer match the sealed authority and Greenfield correctly refuses to show CONFIRM. This is a pre-confirm compiler defect, not a user-facing Product Intent failure.

- Impact: A normal EDIT that supplies a concrete first path can fail before preview even though no material product ambiguity remains.

- Components Affected: greenfield-governance

- Environment(s): Product-repo maintainer source-local proof

- Detected By: Transaction authority regression proof

- Failure Signature: ProductCreateTransaction proposal facts do not match its sealed Product Intent authority; rebuild the transaction before showing CONFIRM.

- Trigger Path: greenfield propose with a concrete edited first path whose derived human-actor row ends in punctuation

- Ownership: Greenfield typed-intent and proposal compiler boundary

- Timeline: Captured 2026-07-26 through `odylith bug capture`.

- Blast Radius: Any generated human actor row changed by projection normalization after authority sealing.

- SLO/SLA Impact: Blocks governed onboarding before the user can review a valid transaction.

- Data Risk: No committed-artifact loss; the mismatch fails closed before CONFIRM.

- Security/Compliance: Policy, privacy, accessibility, and safety assessment: no boundary changes; the failure is confined to pre-confirm in-memory compilation and no raw evidence or artifacts are committed.

- Invariant Violated: Every compiled artifact fact must derive exactly from the sealed typed Product Intent before CONFIRM.

- Root Cause: The same actor-row canonicalization is owned by the proposal projection but is absent from pre-seal typed-intent materialization.

- Solution: Reuse the canonical actor-row normalizer during typed-intent materialization before the authority envelope is built, and retain the hash binding as the guard against future projection drift.

- Rollback/Forward Fix: No rollback required because no writes occur; forward-fix the pre-seal normalization boundary.

- Verification: Regression proves the candidate actor rows and compiled proposal facts hash identically; focused CLI transaction proof passes.

- Prevention: Shared canonical actor-row normalization must run only before authority sealing; proposal rendering must consume sealed facts without semantic cleanup.

- Agent Guardrails: Do not weaken or bypass the intent-authority check to make proposal compilation pass.

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_proposal.py
- src/odylith/runtime/domain_intelligence/greenfield_create_transaction.py
