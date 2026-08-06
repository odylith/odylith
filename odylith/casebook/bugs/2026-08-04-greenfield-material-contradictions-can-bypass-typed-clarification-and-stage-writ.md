- Bug ID: CB-315

- Status: InProgress

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

- Final Holdout Follow-Up (2026-08-05): The disclosed ba25 holdout exposed four ownership ambiguities that explicitly offered two first-approval owners and stated that the choice changed the initial path and proof record. The materiality gate now classifies that ownership decision before actor/path recovery and returns one focused question with `first_approval_actor`, `first_path`, and `proof_record_owner`. All four retired cases clarify with no `.odylith/runtime/greenfield` directory, candidate, or pending transaction written. Clean installed proof remains required before release closure.

- Actor Integrity Follow-Up (2026-08-05): Adversarial review found that a complete multi-step path could let explicit system actors such as sensors, cameras, or robots bypass clarification, while a real `service coordinator` could be rejected because the technical modifier outranked the role. Explicit unfamiliar actors now require a positive human role signal or person-marking grammar such as `who needs to`; profession morphology preserves conservators, horticulturists, specialists, archivists, and similar roles without treating arbitrary nouns as people. Machine cases return the focused `human_actors` and `first_path` question before any runtime write; vague EDIT evidence against an already complete human path continues to request only the missing correction.

- Independent Final Holdout Reopen (2026-08-06): All three authority-omission cases in the new exact-dist one-shot holdout failed the clarification no-write contract. Instead of returning one focused question, each compiled and persisted seven `.odylith/runtime/greenfield` staging records, including candidate evidence and a pending ProductCreateTransaction. No governed `odylith/` records were written and no post-confirm publish occurred. The missed fields were allocation policy ownership and triage standard, alert approval ownership and evacuation jurisdiction, and credentialing rule ownership and appeal process. The current contradiction and generic missing-field detectors do not represent these authority-specific omissions before candidate persistence. Release closure now requires a domain-neutral typed authority/materiality boundary that returns clarification before any candidate, subprocess, or pending-transaction write.

- Authority-Omission Fix (2026-08-06): The materiality gate now recognizes an explicitly declared missing decision authority or governing decision rule before candidate materialization. All three retired authority cases return one focused question with `decision_authority` and `governing_decision_rule`, and no `.odylith/runtime/greenfield` directory is created. A non-material omitted owner-filter control still compiles normally. The repository write-set validator also names the governed root when a sealed after-image fingerprint diverges, preserving a concrete integrity diagnosis without attempting repair. The complete focused regression files passed `89/89`; exact retired-corpus replay and clean-distribution proof remain required before this bug returns to `FixedPendingRelease`.
