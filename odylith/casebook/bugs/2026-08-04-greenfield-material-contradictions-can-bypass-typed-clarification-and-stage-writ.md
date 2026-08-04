- Bug ID: CB-315

- Status: FixedPendingRelease

- Created: 2026-08-04

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: Final holdout case fh-23 presented contradictory proof-boundary claims. Greenfield compiled and staged a ProductCreateTransaction instead of returning a focused proof_boundary clarification with zero writes.

- Impact: A user can be asked to confirm a transaction whose proof meaning was never resolved, while pre-confirm runtime state is mutated despite the clarification contract.

- Components Affected: domain-intelligence

- Environment(s): v0.1.15 final private holdout from clean dist 0aac74c63

- Detected By: Private final holdout semantic release proof

- Failure Signature: fh-23 expected proof_boundary clarification but observed product_create_transaction with seven changed records

- Trigger Path: odylith greenfield propose with contradictory material proof claims

- Ownership: Domain Intelligence materiality gate

- Timeline: Captured 2026-08-04 through `odylith bug capture`.

- Blast Radius: Greenfield prompts with explicit contradictory audience, outcome, dependency, transition, or proof claims

- SLO/SLA Impact: Delivery risk: blocks v0.1.15 release and deterministic pre-confirm UX

- Data Risk: Operational risk: no governed commit occurred, but pre-confirm candidate and pending transaction state was written

- Security/Compliance: Domain and safety risk: proof boundaries can be silently selected instead of clarified

- Invariant Violated: Material ambiguity must produce one typed focused question before any candidate, pending transaction, or governed write

- Root Cause: Pre-materialization checks only classify actor and first-path gaps; they do not classify explicit material contradictions by semantic field

- Solution: Introduce one typed material-ambiguity contract before materialization, with field-specific question and required_fields used by production and release scoring

- Verification: Focused regressions passed field-specific contradiction and incomplete-path cases with exact required_fields and no `.odylith/runtime/greenfield` writes. An adversarial unresolved-ticket case also compiles without inventing a contradiction. The combined anti-clipping, clarification, EDIT, and Registry pack passed 25 tests in 41.89 seconds. Clean installed release proof remains pending.

- Prevention: Keep clarification annotation, runtime exception, per-case scorer, and semantic release scorer on one shared field contract

- Agent Guardrails: Do not collapse every ambiguity into first_path and do not stage files before materiality classification

- Related Incidents/Bugs: CB-251, CB-289, CB-303

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- scripts/release/greenfield_semantic_release_score.py
