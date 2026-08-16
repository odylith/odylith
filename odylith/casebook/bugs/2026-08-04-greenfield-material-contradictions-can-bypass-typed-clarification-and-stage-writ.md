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

- Verification: Focused regressions passed field-specific contradiction and incomplete-path cases with exact required_fields and no `.odylith/runtime/greenfield` writes. An adversarial unresolved-ticket case also compiles without inventing a contradiction. The disclosed `cf41046a9` regressions now preserve all seven source-grounded material field sets, clarify before any Greenfield runtime write, and allow the five structured-evidence controls to reach candidate materialization. The broader materiality, sealed-intent, evaluator, and retired-holdout pack passed 253 tests in 294.85 seconds. Clean installed release proof remains pending.

- Prevention: Keep clarification annotation, runtime exception, per-case scorer, and semantic release scorer on one shared field contract

- Agent Guardrails: Do not collapse every ambiguity into first_path and do not stage files before materiality classification

- Related Incidents/Bugs: CB-251, CB-289, CB-303

- Fixed In: 0.1.15

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_prompt_intent_materialization.py
- scripts/release/greenfield_semantic_release_score.py

- Final Holdout Follow-Up (2026-08-05): The disclosed ba25 holdout exposed four ownership ambiguities that explicitly offered two first-approval owners and stated that the choice changed the initial path and proof record. The materiality gate now classifies that ownership decision before actor/path recovery and returns one focused question with `first_approval_actor`, `first_path`, and `proof_record_owner`. All four retired cases clarify with no `.odylith/runtime/greenfield` directory, candidate, or pending transaction written. Clean installed proof remains required before release closure.

- Actor Integrity Follow-Up (2026-08-05): Adversarial review found that a complete multi-step path could let explicit system actors such as sensors, cameras, or robots bypass clarification, while a real `service coordinator` could be rejected because the technical modifier outranked the role. Explicit unfamiliar actors now require a positive human role signal or person-marking grammar such as `who needs to`; profession morphology preserves conservators, horticulturists, specialists, archivists, and similar roles without treating arbitrary nouns as people. Machine cases return the focused `human_actors` and `first_path` question before any runtime write; vague EDIT evidence against an already complete human path continues to request only the missing correction.

- Independent Holdout Follow-Up (2026-08-08): The clean distribution at `87e277d87d90bc4efac43441c5f7fd3841af4d8e` failed all ten independently authored material-clarification cases. Six prompts returned write-free questions but collapsed the decision into generic `first_path` or `human_actors` fields; three returned `mode=error` after writing five candidate-evidence files; one compiled a transaction after seven staging writes. Material-question recall was `0/10`. The release harness only observed these writes and did not cause them. The call graph confirmed two competing owners: an early regex classifier and a later typed authority gate that runs after persistence. The disclosed 24-case corpus is retired unchanged as `retired-87e277-final-holdout-regressions.v1.json`. The repair must replace both paths with one pure typed materiality decision before any write, produce source-grounded decision fields, and hand only a passed sealed decision to staging.

- Independent Final Holdout Reopen (2026-08-06): All three authority-omission cases in the new exact-dist one-shot holdout failed the clarification no-write contract. Instead of returning one focused question, each compiled and persisted seven `.odylith/runtime/greenfield` staging records, including candidate evidence and a pending ProductCreateTransaction. No governed `odylith/` records were written and no post-confirm publish occurred. The missed fields were allocation policy ownership and triage standard, alert approval ownership and evacuation jurisdiction, and credentialing rule ownership and appeal process. The current contradiction and generic missing-field detectors do not represent these authority-specific omissions before candidate persistence. Release closure now requires a domain-neutral typed authority/materiality boundary that returns clarification before any candidate, subprocess, or pending-transaction write.

- Authority-Omission Fix (2026-08-06): The materiality gate now recognizes an explicitly declared missing decision authority or governing decision rule before candidate materialization. All three retired authority cases return one focused question with `decision_authority` and `governing_decision_rule`, and no `.odylith/runtime/greenfield` directory is created. A non-material omitted owner-filter control still compiles normally. The repository write-set validator also names the governed root when a sealed after-image fingerprint diverges, preserving a concrete integrity diagnosis without attempting repair. The complete focused regression files passed `89/89`; exact retired-corpus replay and clean-distribution proof remain required before this bug returns to `FixedPendingRelease`.

- Fresh Blind Holdout Reopen (2026-08-08): Exact dist `cf41046a9` failed the independently authored, frozen 24-case final holdout on both sides of the materiality boundary. All seven expected-clarification cases failed the annotation-bound no-write contract: five returned a question with the wrong material fields, while two traversed candidate persistence or subprocess work before failing. Five expected-commit cases instead stopped on an unnecessary material clarification. Material-question recall was `1/7` (`0.142857`, release floor `0.95`) and the clarification-required worst slice was `0/7`. The maintained 14-case matrix had passed because it did not cover this decision diversity. This corpus is now disclosed and retired; the repair must replace competing vocabulary-shaped exits with one pure, source-span-bound typed decision over the canonical material fields before any candidate persistence, and it must prove both question recall and unnecessary-question avoidance on the disclosed regressions before another blind release run.

- Fresh Blind Holdout Adjudication (2026-08-08): Replay against the exact runtime found that the five expected-commit clarifications were evaluator-induced: the case loader collapsed Markdown headings and line boundaries before invoking the product. The seven expected-clarification failures were product defects: two crossed the no-write boundary, four asked for the wrong semantic fields, and one was a display-label versus field-ID scoring mismatch. The loader now preserves block structure; one source-label materiality path retains compound decisions such as `priority rule between household use and crop use`; and release scorers share one field-ID canonicalizer without rewriting user-facing labels. The retired corpus remains regression evidence only and cannot be reused as a fresh release holdout.

- Replacement Blind Holdout Reopen (2026-08-16 UTC): All seven expected-clarification cases (`gfhi-005`, `gfhi-006`, `gfhi-013`, `gfhi-014`, `gfhi-020`, `gfhi-022`, and `gfhi-024`) failed the focused-question, zero-write release contract. Material-question recall was `0/7` and the clarification-required worst slice was `0/7`. Three expected-commit controls (`gfhi-010`, `gfhi-019`, and `gfhi-023`) were instead stopped by unnecessary material clarification. Independent full-run adjudication inspected the original prompts, annotations, runtime outputs, and write evidence and classified all ten failures as product-side P0 with no evaluator or oracle reversal. The disclosed corpus must be replayed only as regression evidence; repair remains owned by one pure, source-span-bound materiality decision before any candidate or pending-transaction persistence, with both required-field recall and unnecessary-question avoidance proved together.

- Disclosed Replacement Materiality Closure (2026-08-16): The pre-staging decision now distinguishes competing ownership and path choices, actorless state changes, absent visible results, presentation-only gaps, settled edits, and bounded non-material assumptions. A bare success or completion assertion is not visible proof; a source-grounded concrete badge, marker, receipt, result, state, or status may satisfy the outcome contract. Every retired clarification case returns one annotation-bound question before candidate, subprocess, or pending-transaction writes, while the expected-commit controls proceed. The focused materiality/envelope pack passed `68/68`, the final runtime matrix passed `396/396`, and independent closure found no P0/P1. CB-315 remains `InProgress` until exact installed proof and a new untouched holdout confirm both sides of the boundary.
