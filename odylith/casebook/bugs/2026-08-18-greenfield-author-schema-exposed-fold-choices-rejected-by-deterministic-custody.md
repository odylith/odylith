- Bug ID: CB-347

- Status: Open

- Created: 2026-08-18

- Severity: P1

- Reproducibility: Consistent

- Type: Product

- Description: The candidate-adjudication provider schema first offered every locked workflow candidate against every visible-output and state target. The first correction removed pairwise citation and independent-relation conflicts, but a fresh cohort then proved that individually admissible folds could still jointly remove the sole workflow owner of a required `produces` or `changes` edge. Both forms let a one-shot author select schema-valid output that deterministic graph custody must reject.

- Impact: Fresh two-stage development evidence stops before a segment is written, consuming a one-shot assignment and preventing attributable convergence evidence.

- Components Affected: domain-intelligence

- Environment(s): Detached source-local Greenfield development cohorts at 7d37417cd5d0ccb01e26041d01f932b169e53643 and debffc88c28dfbc36fd4cf9437a4be0deabbde6d

- Detected By: Fresh revision-bound 24-case two-stage development cohort

- Failure Signature: `ValueError: Semantic workflow fold lacks shared exact source custody` in the first cohort; `ValueError: complete Semantic Intent IR lacks typed producing coverage for every visible output` in the replacement cohort

- Trigger Path: greenfield_semantic_host_execution.author_development_case -> select_semantic_source_claims -> require_semantic_source_candidate_adjudication

- Ownership: Semantic source-candidate adjudication schema and deterministic fold custody

- Timeline: Observed on 2026-08-18 after two clean cohort cases; the third assignment failed once and the wave stopped immediately. The pairwise correction then passed the former blocker and ten additional cases before `gfhi-012` failed once at the complete-graph boundary; cases 013-024 remained untouched.

- Blast Radius: Any prompt with multiple locked workflow, state, or visible-output candidates whose exact citations differ

- SLO/SLA Impact: Release-blocking development evidence failure; no customer write occurred

- Data Risk: No customer-data risk; failed evidence is preserved as failed and cannot be retried or reused

- Security/Compliance: Fail-closed custody held, but the provider contract exposed choices the safety verifier could never accept

- Invariant Violated: Every provider-exposed semantic decision must be admissible under the same deterministic custody contract that validates it

- Workaround: None; do not retry or weaken custody

- Root Cause: Provider schema constructed workflow fold choices independently while deterministic validation owns both pairwise custody and graph-wide completeness. The first repair shared only pairwise eligibility, so it did not account for combinations that remove the last typed producer or state-change owner.

- Solution: Use one graph-wide typed fold-eligibility owner for both provider schema construction and deterministic validation. Reserve one stable source workflow anchor for every required `produces` and `changes` target, then expose fold choices only for non-anchor candidates that also satisfy exact-source and independent-relation custody.

- Rollback/Forward Fix: Forward-fix the pre-confirm authoring contract and invalidate stale evidence plans and packets

- Verification: Positive shared-custody fold, positive non-anchor fold with two producers, negative sole-producer fold, negative citation-mismatch fold, negative independent-material-relation fold, authority/transaction/post-confirm/host/evaluator proof, deterministic laws, then fresh assignments from case one

- Prevention: Treat schema-verifier option-set divergence as a contract regression and prove both pairwise admissibility and whole-graph required-edge coverage before exposing provider choices

- Agent Guardrails: Do not add prompt rules, phrase vocabulary, regex inference, retries, or weakened citation custody; remove impossible choices at the typed contract boundary

- Preflight Checks: Frozen tree; fresh protocol identities; old plan and segments retained only as failed historical evidence; replacement holdout unopened

- Regression Tests Added: Provider schema exposes only exact-custody fold pairs, removes pairs that discard an independent material relation, reserves a sole typed producer, and permits only the non-anchor producer when multiple source owners cover one output

- Related Incidents/Bugs: CB-334

- Code References: - src/odylith/runtime/domain_intelligence/greenfield_semantic_source_candidate_adjudication.py
- tests/unit/runtime/test_greenfield_semantic_source_candidate_adjudication.py
