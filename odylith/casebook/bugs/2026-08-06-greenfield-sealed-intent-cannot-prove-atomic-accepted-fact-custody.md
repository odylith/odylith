- Bug ID: CB-323

- Status: Open

- Created: 2026-08-06

- Severity: P0

- Reproducibility: Consistent

- Type: Product

- Description: The independently authored exact-distribution final holdout measured accepted_fact_custody at 0 of 136. The product seals custody for only five coarse fields while release truth annotates atomic actors, actions, states, outputs, constraints, dependencies, and non-goals. Directly supported atoms inside a larger field therefore cannot be proved, and persisted snapshots also dropped explicit prohibitions and named systems.

- Impact: Users can receive a polished pre-confirm package that cannot demonstrate which atomic product claims are directly supported, while critical source constraints and systems can disappear from canonical meaning.

- Components Affected: domain-intelligence

- Environment(s): Odylith 0.1.15 exact dist from aa51e5cf92da4daa79fd3aa40944d49a0211eb75; disclosed 24-case independent final holdout

- Detected By: Hash-bound one-shot semantic release proof plus independent adversarial review

- Failure Signature: accepted_fact_custody=0/136; critical_constraint_recall=2/21; explicit_system_recall=2/7; 24 P0 semantic findings across all three profiles

- Trigger Path: Run the sealed final-holdout release campaign against exact dist and score atomic annotations against preconfirm semantic snapshots

- Ownership: Greenfield canonical meaning, evidence custody, and semantic release scoring

- Timeline: Observed 2026-08-05 in one-shot revision-bound holdout; ledger terminal status failed and corpus retired to regression

- Blast Radius: Any Greenfield evidence with multiple accepted atomic facts, explicit systems, constraints, prohibitions, or non-goals

- SLO/SLA Impact: Blocks v0.1.15 release and invalidates semantic release-readiness claims

- Data Risk: No governed source data loss; semantic omission can misdirect every generated governance and implementation artifact

- Security/Compliance: Safety, authority, and compliance boundaries can be omitted or downgraded from accepted source facts

- Invariant Violated: Every accepted material fact must carry a valid source span, semantic entailment, polarity, custody state, and projection trace before confirmation

- Root Cause: Field-level material custody covers only product_story, state_object, first_path, proof_boundary, and human_actors; atomic categories have no sealed provenance ledger, while the scorer requires accepted_fact custody per atom

- Solution: Seal one domain-neutral atomic fact ledger with category, polarity, normalized value, source-span IDs, custody, and projection links; score the same ledger and preserve bounded_interpretation only for actual inference

- Rollback/Forward Fix: Forward fix only; no post-confirm semantic repair and no weakening of custody floors

- Verification: Replay the retired 24-case corpus with 100 percent directly entailed atomic custody, critical-constraint and explicit-system recall; then run a fresh blind holdout against a rebuilt exact dist

- Prevention: Exercise real production semantic snapshots in scorer tests and reject 0-of-0 or synthetic accepted-fact fixtures as release proof

- Agent Guardrails: Do not add domain phrase lists, infer custody from generated-field adjacency, or make the scorer award accepted_fact without a source-entailment binding

- Preflight Checks: Retired regression corpus, cross-split leakage, all three profiles, all evidence styles, no-write clarification, browser, recovery, and exact distribution provenance

- Regression Tests Added: tests/fixtures/greenfield-release-corpus/retired-aa51-final-holdout-regressions.v1.json preserves the 24 disclosed cases and atomic annotations

- Monitoring Updates: Report extraction availability separately from package/render failure, and expose atomic custody denominators by category and profile

- Version/Build: 0.1.15 aa51e5cf92da4daa79fd3aa40944d49a0211eb75

- Related Incidents/Bugs: CB-302, CB-303, CB-315, B-142

- GitHub Status: confirmed

- Public Response: pending

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_sealed_product_intent_authority.py
- src/odylith/runtime/domain_intelligence/greenfield_product_intent_envelope.py
- scripts/release/greenfield_semantic_release_score.py
