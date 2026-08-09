- Bug ID: CB-323

- Status: InProgress

- Created: 2026-08-06

- Severity: P0

- Reproducibility: Consistent

- Type: Product

- Description: The independently authored exact-distribution final holdout measured accepted_fact_custody at 0 of 136. The product seals custody for only five coarse fields while release truth annotates atomic actors, actions, states, outputs, constraints, dependencies, and non-goals. Directly supported atoms inside a larger field therefore cannot be proved, and persisted snapshots also dropped explicit prohibitions and named systems.

- Impact: Users can receive a polished pre-confirm package that cannot demonstrate which atomic product claims are directly supported, while critical source constraints and systems can disappear from canonical meaning.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 exact dist from aa51e5cf92da4daa79fd3aa40944d49a0211eb75; disclosed 24-case independent final holdout

- Detected By: Hash-bound one-shot semantic release proof plus independent adversarial review

- Failure Signature: The first disclosed holdout reported accepted_fact_custody=0/136, critical_constraint_recall=2/21, explicit_system_recall=2/7, and 24 P0 findings. A second disclosed 24-case holdout at 87e277d87 reported accepted_fact_custody=25/36, critical_constraint_recall=1/5, explicit_system_recall=1/4, and 7 P0 findings before scorer correction.

- Trigger Path: Run the sealed final-holdout release campaign against exact dist and score atomic annotations against preconfirm semantic snapshots

- Ownership: Greenfield canonical meaning, evidence custody, and semantic release scoring

- Timeline: Observed 2026-08-05 in one-shot revision-bound holdout; ledger terminal status failed and corpus retired to regression

- Blast Radius: Any Greenfield evidence with multiple accepted atomic facts, explicit systems, constraints, prohibitions, or non-goals

- SLO/SLA Impact: Blocks v0.1.15 release and invalidates semantic release-readiness claims

- Data Risk: No governed source data loss; semantic omission can misdirect every generated governance and implementation artifact

- Security/Compliance: Safety, authority, and compliance boundaries can be omitted or downgraded from accepted source facts

- Invariant Violated: Every accepted material fact must carry a valid source span, semantic entailment, polarity, custody state, and projection trace before confirmation

- Root Cause: Field-level material custody covered only product_story, state_object, first_path, proof_boundary, and human_actors; atomic categories had no sealed provenance ledger. After the ledger landed, natural-language external-boundary recovery still recognized only from/via/supplier forms, and mixed-polarity source sentences assigned prohibited polarity to positive sibling clauses. The release scorer also trusted transaction-provided custody structure without independently rebinding projection paths, source hashes, and entailment to the scored evidence.

- Solution: Seal one domain-neutral atomic fact ledger with category, polarity, normalized value, source-span IDs, custody, and projection links; recover external boundaries through bounded typed relation frames; split source custody into local polarity units; score the same units; preserve bounded_interpretation only for actual inference

- Rollback/Forward Fix: Forward fix only; no post-confirm semantic repair and no weakening of custody floors

- Verification: The source-local atom ledger, current and legacy envelope migration, authority sealing, scorer-forgery rejection, supporting-evidence exclusion, and transaction-body tamper tests pass. The disclosed 21-case retired commit corpus now preserves every annotated actor, action, state, output, dependency, and non-goal through prompt materialization and accepts every annotation in the sealed atom ledger; its dedicated cross-domain custody matrix passes 44 tests. The complete recovery, materiality, and requirement-boundary family passes 120 tests with no exclusions after repairing the two defects independently reproduced at the prior checkpoint: actor evidence in an edited First Complete Path no longer requires a redundant Human Actors section, and nominal list terms such as baseline routes and operator notes no longer become fabricated actions or actors. Atomic-ledger and Product Intent envelope proof passes 40 tests. Re-scoring the sealed 87e277d87 holdout outputs after clause-local polarity and category-bound recall correction raises critical_constraint_recall from 1/5 to 5/5 and reduces P0 findings from 7 to 3 without rerunning product behavior. The product now recovers the exact external-system set for all 11 disclosed commit cases and seals the four previously scoreable systems as accepted dependency facts, including a dependency adjacent to a prohibition. Two adversarial review rounds produced and closed counterexamples for comparison artifacts, conditional tails, modal supplier clauses, capitalization, people, device carriers, and product-title self-classification. Fresh proof passes 104 boundary/custody/scorer tests, 96 applicable retired-holdout tests with only five independently proven baseline title tests excluded, and the 193-test fast Greenfield gate. CB-323 remains P0 and in progress until all retired regressions pass from a rebuilt exact distribution, browser-state proof passes, and a fresh blind holdout meets the release floors.

- Prevention: Exercise real production semantic snapshots in scorer tests and reject 0-of-0 or synthetic accepted-fact fixtures as release proof

- Agent Guardrails: Do not add domain phrase lists, infer custody from generated-field adjacency, or make the scorer award accepted_fact without a source-entailment binding

- Preflight Checks: Retired regression corpus, cross-split leakage, all three profiles, all evidence styles, no-write clarification, browser, recovery, and exact distribution provenance

- Regression Tests Added: tests/fixtures/greenfield-release-corpus/retired-aa51-final-holdout-regressions.v1.json preserves the disclosed cases and atomic annotations; tests/unit/runtime/test_greenfield_prompt_workflow_custody.py binds the 21 commit-capable cases to canonical and atom-level custody expectations

- Monitoring Updates: Report extraction availability separately from package/render failure, and expose atomic custody denominators by category and profile

- Version/Build: 0.1.15 aa51e5cf92da4daa79fd3aa40944d49a0211eb75

- Related Incidents/Bugs: CB-302, CB-303, CB-315, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_sealed_product_intent_authority.py
- src/odylith/runtime/domain_intelligence/greenfield_product_intent_envelope.py
- src/odylith/runtime/domain_intelligence/greenfield_atomic_fact_ledger.py
- src/odylith/runtime/domain_intelligence/greenfield_confirmed_intent.py
- scripts/release/greenfield_matrix_transaction_evidence.py
- scripts/release/greenfield_semantic_release_score.py
